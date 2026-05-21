#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import threading
import math
import time
import socket
import json
import cv2
import numpy as np
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from std_msgs.msg import String
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("⚠️  ultralytics ไม่ได้ติดตั้ง — YOLO safety check ถูกปิดการใช้งาน")

PI_IP = "10.0.0.2"
PI_PORT = 5001
LISTEN_PORT = 5001
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

INVERT_TWIN_ROTATION = True
ENCODER_MIN = 0
ENCODER_MAX = 61
GAZEBO_RAD_MIN = -1.60
GAZEBO_RAD_MAX = 1.60
SLOT_TARGETS = {1: 7, 2: 32, 3: 54}
CYCLE_TRAVEL_TIME = 11.0
BANG_BANG_HZ = 20
BANG_BANG_DT = 1.0 / BANG_BANG_HZ
HOMING_TIMEOUT = 30.0
E2_MIN = 0
E2_MAX = 325
ARM_RAD_AT_E2_MIN = -0.52
ARM_RAD_AT_E2_MAX = 0.0

def e2_to_arm_rad(e2_val):
    e2_clamped = max(E2_MIN, min(E2_MAX, e2_val))
    ratio = float(e2_clamped - E2_MIN) / (E2_MAX - E2_MIN)
    return ARM_RAD_AT_E2_MIN + ratio * (ARM_RAD_AT_E2_MAX - ARM_RAD_AT_E2_MIN)

VALVE_REPEAT_CMDS = {"UP_ON", "DOWN_ON"}
VALVE_REPEAT_INTERVAL = 1.0
VALVE_REPEAT_DURATION = 13.0
P4_TIMEOUT = 60.0
E2_DOWN_THRESHOLD = 280
CAMERA_STREAM_URL = "http://10.0.0.2:5002/video_feed"
YOLO_MODEL_PATH = "yolov8n.pt"
YOLO_DANGER_CLASSES = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle",
    5: "bus",  7: "truck", 14: "bird", 15: "cat",
    16: "dog", 17: "horse",  19: "cow",
}
YOLO_CONFIDENCE = 0.35
YOLO_DANGER_TIMEOUT = 120.0
YOLO_CHECK_INTERVAL = 0.25
YOLO_CLEAR_COUNTDOWN = 3.0
YOLO_STABLE_BEFORE_COUNTDOWN = 2.0
YOLO_ROI = {"top": 0.15, "bottom": 0.85, "left": 0.10, "right": 0.90}
YOLO_DEBOUNCE_SEC = 2.0

XCYCLE_CAPTURE_ROUNDS = [
    {"round": 1, "pct": 100, "label": "1st (100%)"},
    {"round": 2, "pct": 65,  "label": "2nd (65%)"},
    {"round": 3, "pct": 50,  "label": "3rd (50%)"},
]
XCYCLE_CAM_TIMEOUT = 10.0
XCYCLE_MAX_PASSES = 20


class YoloSafetyMonitor:
    WINDOW_NAME = "🔍 YOLO Safety Monitor — Crane System"

    def __init__(self, stream_url, model_path, logger=None):
        self._url = stream_url
        self._model_path = model_path
        self._logger = logger
        self._model = None
        self._lock = threading.Lock()
        self._danger = False
        self._raw_detected = False
        self._detect_since = None
        self._DEBOUNCE = YOLO_DEBOUNCE_SEC
        self._last_frame = None
        self._running = False
        self._thread = None
        self._display_thread = None
        self._last_labels: list = []
        self._grab_lock  = threading.Lock()
        self._grab_event = threading.Event()
        self._raw_frame  = None
        self._grab_thread = None

    def _log(self, msg):
        if self._logger:
            self._logger.info(msg)
        else:
            print(msg)

    def start(self):
        if not YOLO_AVAILABLE:
            self._log("⚠️  [YOLO] ultralytics ไม่พร้อม — ข้าม")
            return
        try:
            self._log(f"🔍 [YOLO] โหลด model: {self._model_path}")
            self._model = YOLO(self._model_path)
            self._log("✅ [YOLO] โหลด model สำเร็จ")
        except Exception as e:
            self._log(f"❌ [YOLO] โหลด model ล้มเหลว: {e}")
            return
        self._running = True
        self._grab_thread = threading.Thread(target=self._grab_loop, daemon=True)
        self._grab_thread.start()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self._display_thread.start()
        self._log(f"▶️  [YOLO] เริ่ม stream จาก {self._url}")

    def stop(self):
        self._running = False
        try:
            cv2.destroyWindow(self.WINDOW_NAME)
        except Exception:
            pass

    @property
    def is_danger(self):
        with self._lock:
            return self._danger

    def _draw_overlay(self, frame, danger, labels):
        h, w = frame.shape[:2]
        bar_color = (0, 0, 220) if danger else (0, 180, 0)
        cv2.rectangle(frame, (0, 0), (w, 40), bar_color, -1)
        status_text = f"DANGER: {', '.join(labels)}" if danger else "SAFE"
        cv2.putText(frame, status_text, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
        ts = time.strftime("%H:%M:%S")
        cv2.putText(frame, ts, (w - 90, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)
        return frame

    def _grab_loop(self):
        cap = None
        while self._running:
            try:
                if cap is None or not cap.isOpened():
                    self._log(f"📷 [GRAB] เชื่อมต่อ stream: {self._url}")
                    cap = cv2.VideoCapture(self._url)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)
                    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000)
                    if not cap.isOpened():
                        placeholder = np.zeros((240, 320, 3), dtype=np.uint8)
                        cv2.putText(placeholder, "Connecting to camera...", (10, 120),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 255), 2)
                        with self._grab_lock:
                            self._raw_frame = placeholder
                        self._grab_event.set()
                        time.sleep(2.0)
                        cap = None
                        continue
                ret, frame = cap.read()
                if not ret:
                    cap.release(); cap = None
                    time.sleep(0.5)
                    continue
                with self._grab_lock:
                    self._raw_frame = frame
                self._grab_event.set()
            except Exception as e:
                self._log(f"❌ [GRAB] error: {e}")
                if cap:
                    cap.release()
                cap = None
                time.sleep(1.0)
        if cap:
            cap.release()

    def _run_loop(self):
        while self._running:
            try:
                if not self._grab_event.wait(timeout=1.0):
                    continue
                self._grab_event.clear()
                with self._grab_lock:
                    frame = self._raw_frame
                if frame is None:
                    continue
                h, w = frame.shape[:2]
                roi_t = int(h * YOLO_ROI["top"])
                roi_b = int(h * YOLO_ROI["bottom"])
                roi_l = int(w * YOLO_ROI["left"])
                roi_r = int(w * YOLO_ROI["right"])
                roi_frame = frame[roi_t:roi_b, roi_l:roi_r]
                results = self._model(roi_frame, conf=YOLO_CONFIDENCE,
                                      classes=list(YOLO_DANGER_CLASSES.keys()), verbose=False)
                detected = False
                labels_found = []
                for r in results:
                    for box in r.boxes:
                        cls_id = int(box.cls[0])
                        if cls_id not in YOLO_DANGER_CLASSES:
                            continue
                        detected = True
                        label = YOLO_DANGER_CLASSES[cls_id]
                        conf = float(box.conf[0])
                        labels_found.append(f"{label}({conf:.2f})")
                now = time.time()
                with self._lock:
                    if detected:
                        if self._detect_since is None:
                            self._detect_since = now
                            self._raw_detected = True
                        elif (now - self._detect_since) >= self._DEBOUNCE:
                            if not self._danger:
                                self._danger = True
                                self._log(f"🚨 [YOLO] DANGER ยืนยัน ({self._DEBOUNCE}s): {', '.join(labels_found)}")
                    else:
                        if self._danger:
                            self._log("✅ [YOLO] พื้นที่ปลอดภัยแล้ว")
                        self._danger = False
                        self._raw_detected = False
                        self._detect_since = None
                    self._last_labels = labels_found if detected else []
            except Exception as e:
                self._log(f"❌ [YOLO] loop error: {e}")
                time.sleep(0.5)

    def _display_loop(self):
        cv2.namedWindow(self.WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.WINDOW_NAME, 800, 480)
        while self._running:
            with self._grab_lock:
                raw = self._raw_frame
            if raw is None:
                cv2.waitKey(10)
                continue
            frame = raw.copy()
            with self._lock:
                danger_now = self._danger
                labels_now = list(getattr(self, '_last_labels', []))
            frame = self._draw_overlay(frame, danger_now, labels_now)
            cv2.imshow(self.WINDOW_NAME, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
        cv2.destroyWindow(self.WINDOW_NAME)


class CraneIntegratedSystem(Node):
    def __init__(self):
        super().__init__('crane_integrated_system')
        self.current_head_deg = 0.0
        self.last_cmd = None
        self.system_started = False
        self.is_moving = False
        self.bungkee_active = False
        self.rotation_dir = None
        self.last_bungkee_time = 0
        self.last_bungkee_pos = 0.0
        self.bungkee_cmd = None
        self.bungkee_debounce_duration = 0.15
        self.pending_bungkee_cmd = None
        self.cmd_timestamp = 0
        self.brake_triggered = False
        self.is_braking_now = False
        self.brake_off_timestamp = 0
        self.e1_offset = 0
        self.smooth_pos = GAZEBO_RAD_MIN
        self.alpha = 0.85
        self.last_sent_pos = GAZEBO_RAD_MIN
        self.gz_publisher = self.create_publisher(
            JointTrajectory, '/arm_group_controller/joint_trajectory', 10)
        self.status_pub = self.create_publisher(String, '/crane_status', 10)
        self.create_subscription(String, '/web_control_topic', self.web_control_callback, 10)
        self.e1_raw = None
        self.e2_raw = None
        self.ls1_state = 0
        self.ls2_state = 0
        self.p1 = 0
        self.p2 = 0
        self.p3 = 0
        self.p4 = 0
        self.e1_position = 0
        self.is_homed = False
        self._sensor_lock = threading.Lock()
        self.cycle_running = False
        self.target_e1_from_cam = None
        self.cam_target_event = threading.Event()
        self._ls1_count_1 = 0
        self._ls1_count_0 = 0
        self._ls2_count_1 = 0
        self._ls2_count_0 = 0
        self.DEBOUNCE_LIMIT = 1
        self._ls1_last = 0
        self._ls2_last = 0
        self._valve_repeat_lock = threading.Lock()
        self._valve_repeat_active = {}
        self.listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listen_sock.bind(("0.0.0.0", LISTEN_PORT))
        self.listen_sock.settimeout(0.1)
        self.is_system_ready = False
        self.create_subscription(JointState, '/joint_states', self.joint_callback, 10)
        self._safety_paused = False
        self._safety_lock = threading.Lock()
        self._danger_start = 0.0
        self._pi_emergency = False
        self._pi_emergency_lock = threading.Lock()
        self._xcycle_capture_round = {1: 0, 2: 0, 3: 0}
        self._xcycle_round_lock = threading.Lock()
        self._manual_homed = False
        self._manual_lock = threading.Lock()
        self._manual_moving = False
        self._bungkee_yolo_brake_lock = threading.Lock()
        self._rotation_yolo_brake_lock = threading.Lock()
        self._press_lost = False
        self._press_lost_lock = threading.Lock()

        self.yolo_monitor = YoloSafetyMonitor(
            stream_url=CAMERA_STREAM_URL,
            model_path=YOLO_MODEL_PATH,
            logger=self.get_logger(),
        )
        self.yolo_monitor.start()
        threading.Thread(target=self.udp_monitor,       daemon=True).start()
        threading.Thread(target=self._safety_watchdog,  daemon=True).start()
        self.get_logger().info("🔥 CRANE FAST-TWIN SYSTEM READY (NO MOVEIT - WAITING PI START)")

    # =========================================================
    # ── NEW HELPER: publish_summary_to_web ──────────────────
    # =========================================================
    def publish_summary_to_web(self, summary_text: str):
        msg = String()
        with self._press_lost_lock:
            press_lost_now = self._press_lost
        payload = {
            "summary": summary_text,
            "p1": self.p1,
            "p2": self.p2,
            "p3": self.p3,
            "is_system_ready":  self.is_system_ready,
            "is_moving":        self.is_moving,
            "cycle_running":    self.cycle_running,
            "last_bungkee_pos": float(self.last_bungkee_pos),
            "current_head_deg": float(self.current_head_deg),
            "yolo_danger":      self.yolo_monitor.is_danger,
            "pi_emergency":     self._pi_emergency,
            "press_lost":       press_lost_now,
        }
        msg.data = json.dumps(payload)
        self.status_pub.publish(msg)

    # =========================================================
    # reset_state
    # =========================================================
    def reset_state(self):
        self.is_moving = False
        self.system_started = False
        self.rotation_dir = None
        self.last_cmd = None
        self.bungkee_active = False
        self.bungkee_cmd = None
        self.pending_bungkee_cmd = None
        self.brake_triggered = False
        self.is_braking_now = False
        self.brake_off_timestamp = 0
        self.cam_target_event.set()
        self._stop_all_valve_repeat()
        with self._press_lost_lock:
            self._press_lost = False

    # =========================================================
    # _handle_pi_emergency  (GPIO16)
    # =========================================================
    def _handle_pi_emergency(self, state):
        with self._pi_emergency_lock:
            prev = self._pi_emergency
            self._pi_emergency = bool(state)
        if state == 1 and not prev:
            self.get_logger().error(
                "🚨 [PI EMERGENCY] GPIO16 กด Emergency — EMERGENCY SHUTDOWN ทันที!")
            self.emergency_shutdown()
        elif state == 0 and prev:
            self.get_logger().info(
                "✅ [PI EMERGENCY] GPIO16 ปล่อยแล้ว — รอ START ใหม่จาก Pi")

    # =========================================================
    # _handle_press_stop  (GPIO22)
    # =========================================================
    def _handle_press_stop(self, reason: str = "GPIO22_LOST_WHILE_RUNNING"):
        with self._press_lost_lock:
            already = self._press_lost
            self._press_lost = True
        if already:
            return
        self.get_logger().error(
            f"🛑 [PRESS STOP] Pi รายงาน GPIO22 หลุดขณะทำงาน "
            f"(reason={reason}) — EMERGENCY SHUTDOWN!"
        )
        print(f"\n🛑 [PRESS STOP] GPIO22 lost while running ({reason}) — stopping all systems\n")
        self.emergency_shutdown()

    # =========================================================
    # _safety_watchdog
    # =========================================================
    def _safety_watchdog(self):
        while rclpy.ok():
            time.sleep(0.1)
            if not self.is_system_ready:
                continue
            if not self.yolo_monitor.is_danger:
                with self._safety_lock:
                    if self._safety_paused:
                        pass
                    else:
                        continue
                stable_start = time.time()
                stable_ok = True
                self.get_logger().info(
                    f"👁️  [WATCHDOG] พื้นที่ปลอดภัย — รอ stable {YOLO_STABLE_BEFORE_COUNTDOWN:.0f}s...")
                while time.time() - stable_start < YOLO_STABLE_BEFORE_COUNTDOWN:
                    time.sleep(0.1)
                    if self.yolo_monitor.is_danger:
                        stable_ok = False
                        break
                if not stable_ok:
                    continue
                self.get_logger().info(
                    f"⏳ [WATCHDOG] นับถอยหลัง {YOLO_CLEAR_COUNTDOWN:.0f}s ก่อน resume...")
                countdown_ok = True
                for remaining in range(int(YOLO_CLEAR_COUNTDOWN), 0, -1):
                    self.get_logger().info(f"⏳ [WATCHDOG] resume ใน {remaining}s...")
                    time.sleep(1.0)
                    if self.yolo_monitor.is_danger:
                        countdown_ok = False
                        break
                if countdown_ok:
                    with self._safety_lock:
                        self._safety_paused = False
                    self.get_logger().info("✅ [WATCHDOG] ครบ countdown — resume การทำงาน")
                    self.send_udp("DANGER_OFF", bypass_safety=True)
                continue

            with self._safety_lock:
                already_paused = self._safety_paused
                if not already_paused:
                    self._safety_paused = True
                    self._danger_start = time.time()
                    self.get_logger().warn(
                        f"🚨 [WATCHDOG] พบสิ่งกีดขวาง — หยุด process ทันที (max {YOLO_DANGER_TIMEOUT:.0f}s)")
                    self.send_udp("DANGER_ON",  bypass_safety=True)
                    self.send_udp("MAG1_OFF",   bypass_safety=True)
                    self.send_udp("MAG2_OFF",   bypass_safety=True)
                    self.send_udp("UP_OFF",     bypass_safety=True)
                    self.send_udp("DOWN_OFF",   bypass_safety=True)
                    self._stop_all_valve_repeat()
            with self._safety_lock:
                elapsed = time.time() - self._danger_start
            if elapsed >= YOLO_DANGER_TIMEOUT:
                self.get_logger().error(
                    f"🛑 [WATCHDOG] ครบ {YOLO_DANGER_TIMEOUT:.0f}s ยังเจอสิ่งกีดขวาง — EMERGENCY STOP!")
                self.send_udp("DANGER_OFF", bypass_safety=True)
                self.emergency_shutdown()

    def _wait_if_paused(self, label=""):
        if not self._safety_paused:
            return True
        self.get_logger().info(
            f"⏸️  [{label}] process หยุดค้าง — รอพื้นที่ปลอดภัย + countdown {YOLO_CLEAR_COUNTDOWN:.0f}s...")
        while rclpy.ok() and self.is_system_ready:
            with self._safety_lock:
                if not self._safety_paused:
                    self.get_logger().info(f"▶️  [{label}] countdown ครบ — resume ต่อ")
                    cmd = self.bungkee_cmd
                    if cmd == "UP":
                        self.send_udp("DOWN_OFF", bypass_safety=True)
                        self.send_udp("UP_ON",   bypass_safety=True)
                    elif cmd == "DOWN":
                        self.send_udp("UP_OFF",   bypass_safety=True)
                        self.send_udp("DOWN_ON",  bypass_safety=True)
                    return True
            time.sleep(0.1)
        return False

    def yolo_safety_check(self, label=""):
        if not YOLO_AVAILABLE or self._model_is_off():
            return True
        if not self.yolo_monitor.is_danger:
            return True
        tag = f"YOLO-SAFETY{'['+label+']' if label else ''}"
        self.get_logger().warn(
            f"🚨 [{tag}] พบสิ่งกีดขวาง → หยุดรอ (max {YOLO_DANGER_TIMEOUT:.0f}s)")
        deadline = time.time() + YOLO_DANGER_TIMEOUT + YOLO_CLEAR_COUNTDOWN + 5.0
        while rclpy.ok() and self.is_system_ready:
            if time.time() > deadline:
                break
            with self._safety_lock:
                if not self._safety_paused:
                    self.get_logger().info(f"✅ [{tag}] ปลอดภัยแล้ว — ทำงานต่อ")
                    return True
            time.sleep(0.1)
        self.get_logger().error(f"🛑 [{tag}] หมดเวลารอ — EMERGENCY STOP!")
        self.emergency_shutdown()
        return False

    def _model_is_off(self):
        return self.yolo_monitor._model is None

    # =========================================================
    # _rotation_yolo_monitor
    # =========================================================
    def _rotation_yolo_monitor(self, stop_event, current_mag_cmd_ref):
        mag_stopped = False
        while not stop_event.is_set():
            danger_now = (self.yolo_monitor.is_danger
                          if YOLO_AVAILABLE and not self._model_is_off() else False)
            if danger_now and not mag_stopped:
                with self._rotation_yolo_brake_lock:
                    self.get_logger().warn(
                        "🚨 [ROTATE-YOLO] พบสิ่งกีดขวางระหว่างหมุน → MAG1_OFF + MAG2_OFF")
                    self.send_udp("MAG1_OFF", bypass_safety=True)
                    self.send_udp("MAG2_OFF", bypass_safety=True)
                    self.last_cmd = "STOP"
                    mag_stopped = True
            elif not danger_now and mag_stopped:
                stable_ok = True
                stable_start = time.time()
                while time.time() - stable_start < YOLO_STABLE_BEFORE_COUNTDOWN:
                    if stop_event.is_set():
                        break
                    if (self.yolo_monitor.is_danger
                            if YOLO_AVAILABLE and not self._model_is_off() else False):
                        stable_ok = False
                        break
                    time.sleep(0.1)
                if not stable_ok or stop_event.is_set():
                    continue
                countdown_ok = True
                for remaining in range(int(YOLO_CLEAR_COUNTDOWN), 0, -1):
                    if stop_event.is_set():
                        countdown_ok = False
                        break
                    time.sleep(1.0)
                    if (self.yolo_monitor.is_danger
                            if YOLO_AVAILABLE and not self._model_is_off() else False):
                        countdown_ok = False
                        break
                if not countdown_ok or stop_event.is_set():
                    continue
                with self._rotation_yolo_brake_lock:
                    resume_cmd = current_mag_cmd_ref[0]
                    if resume_cmd and not stop_event.is_set():
                        if resume_cmd == "MAG1":
                            self.send_udp("MAG2_OFF", bypass_safety=True)
                            self.send_udp("MAG1_ON",  bypass_safety=True)
                        elif resume_cmd == "MAG2":
                            self.send_udp("MAG1_OFF", bypass_safety=True)
                            self.send_udp("MAG2_ON",  bypass_safety=True)
                        self.last_cmd = resume_cmd
                    mag_stopped = False
            time.sleep(YOLO_CHECK_INTERVAL)
        if mag_stopped:
            with self._rotation_yolo_brake_lock:
                self.send_udp("MAG1_OFF", bypass_safety=True)
                self.send_udp("MAG2_OFF", bypass_safety=True)

    # =========================================================
    # _bungkee_yolo_brake_monitor
    # =========================================================
    def _bungkee_yolo_brake_monitor(self, phase, stop_event):
        if phase == "DOWN":
            motion_off    = "DOWN_OFF"
            motion_on     = "DOWN_ON"
            brake_cmd_on  = "B1_ON"
            brake_cmd_off = "B1_OFF"
        else:
            motion_off    = "UP_OFF"
            motion_on     = "UP_ON"
            brake_cmd_on  = "B2_ON"
            brake_cmd_off = "B2_OFF"
        brake_active = False
        while not stop_event.is_set():
            danger_now = (self.yolo_monitor.is_danger
                          if YOLO_AVAILABLE and not self._model_is_off() else False)
            if danger_now and not brake_active:
                with self._bungkee_yolo_brake_lock:
                    self.get_logger().warn(
                        f"🚨 [BUNGKEE-YOLO-{phase}] พบสิ่งกีดขวาง → {motion_off} + {brake_cmd_on}")
                    self.send_udp(motion_off, bypass_safety=True)
                    self._stop_valve_repeat(motion_on)
                    self.send_udp(brake_cmd_on, bypass_safety=True)
                    brake_active = True
            elif not danger_now and brake_active:
                stable_ok = True
                stable_start = time.time()
                while time.time() - stable_start < YOLO_STABLE_BEFORE_COUNTDOWN:
                    if stop_event.is_set():
                        break
                    if (self.yolo_monitor.is_danger
                            if YOLO_AVAILABLE and not self._model_is_off() else False):
                        stable_ok = False
                        break
                    time.sleep(0.1)
                if not stable_ok or stop_event.is_set():
                    continue
                countdown_ok = True
                for remaining in range(int(YOLO_CLEAR_COUNTDOWN), 0, -1):
                    if stop_event.is_set():
                        countdown_ok = False
                        break
                    time.sleep(1.0)
                    if (self.yolo_monitor.is_danger
                            if YOLO_AVAILABLE and not self._model_is_off() else False):
                        countdown_ok = False
                        break
                if not countdown_ok or stop_event.is_set():
                    continue
                with self._bungkee_yolo_brake_lock:
                    self.get_logger().info(
                        f"✅ [BUNGKEE-YOLO-{phase}] countdown ครบ → {brake_cmd_off} แล้ว resume {motion_on}")
                    self.send_udp(brake_cmd_off, bypass_safety=True)
                    if not stop_event.is_set():
                        self.send_udp(motion_on, bypass_safety=True)
                        if motion_on in VALVE_REPEAT_CMDS:
                            self._start_valve_repeat(motion_on)
                    brake_active = False
            time.sleep(YOLO_CHECK_INTERVAL)
        if brake_active:
            with self._bungkee_yolo_brake_lock:
                self.send_udp(brake_cmd_off, bypass_safety=True)

    # =========================================================
    # Helpers
    # =========================================================
    def calculate_mapping(self, enc_pos_0_max):
        enc_pos_0_max = max(ENCODER_MIN, min(ENCODER_MAX, enc_pos_0_max))
        ratio = float(enc_pos_0_max - ENCODER_MIN) / (ENCODER_MAX - ENCODER_MIN)
        if INVERT_TWIN_ROTATION:
            ratio = 1.0 - ratio
        raw_target = GAZEBO_RAD_MIN + ratio * (GAZEBO_RAD_MAX - GAZEBO_RAD_MIN)
        self.smooth_pos = (self.alpha * raw_target) + ((1 - self.alpha) * self.smooth_pos)
        return max(GAZEBO_RAD_MIN, min(GAZEBO_RAD_MAX, self.smooth_pos))

    def publish_to_gazebo(self, rad, sec=0.1, arm_rad=None):
        traj_msg = JointTrajectory()
        traj_msg.joint_names = ['headcrane_Link', 'armcrane_Link']
        point = JointTrajectoryPoint()
        arm_val = float(arm_rad) if arm_rad is not None else float(self.last_bungkee_pos)
        point.positions = [float(rad), arm_val]
        point.time_from_start.sec = int(sec)
        point.time_from_start.nanosec = int((sec - int(sec)) * 1e9)
        traj_msg.points.append(point)
        self.gz_publisher.publish(traj_msg)

    def encoder_to_rad(self, enc_pos):
        enc_pos = max(0, min(ENCODER_MAX, enc_pos))
        ratio = float(enc_pos) / ENCODER_MAX
        if INVERT_TWIN_ROTATION:
            ratio = 1.0 - ratio
        return GAZEBO_RAD_MIN + ratio * (GAZEBO_RAD_MAX - GAZEBO_RAD_MIN)

    def get_e1_position(self):
        with self._sensor_lock:
            if self.e1_raw is None:
                return 0
            enc_pos = self.e1_raw - self.e1_offset
            return max(0, min(ENCODER_MAX, enc_pos))

    def _valve_repeat_worker(self, cmd, stop_event):
        deadline = time.time() + VALVE_REPEAT_DURATION
        while not stop_event.is_set() and time.time() < deadline:
            try:
                sock.sendto(cmd.encode(), (PI_IP, PI_PORT))
            except Exception as e:
                print(f"Valve repeat send error: {e}")
            stop_event.wait(timeout=VALVE_REPEAT_INTERVAL)
        with self._valve_repeat_lock:
            self._valve_repeat_active.pop(cmd, None)

    def _start_valve_repeat(self, cmd):
        self._stop_valve_repeat(cmd)
        stop_event = threading.Event()
        with self._valve_repeat_lock:
            self._valve_repeat_active[cmd] = stop_event
        t = threading.Thread(target=self._valve_repeat_worker, args=(cmd, stop_event), daemon=True)
        t.start()

    def _stop_valve_repeat(self, cmd):
        with self._valve_repeat_lock:
            ev = self._valve_repeat_active.pop(cmd, None)
        if ev:
            ev.set()

    def _stop_all_valve_repeat(self):
        with self._valve_repeat_lock:
            events = list(self._valve_repeat_active.values())
            self._valve_repeat_active.clear()
        for ev in events:
            ev.set()

    def send_udp(self, cmd, bypass_safety=False):
        try:
            sock.sendto(cmd.encode(), (PI_IP, PI_PORT))
            if cmd in VALVE_REPEAT_CMDS:
                self._start_valve_repeat(cmd)
            elif cmd == "UP_OFF":
                self._stop_valve_repeat("UP_ON")
            elif cmd == "DOWN_OFF":
                self._stop_valve_repeat("DOWN_ON")
        except Exception as e:
            print(f"send_udp error: {e}")

    def _wait_for_p4(self, timeout=P4_TIMEOUT, label=""):
        self.get_logger().info(f"⏳ [{label}] รอ P4=1 (timeout {timeout}s)...")
        t_start = time.time()
        while rclpy.ok() and self.is_system_ready:
            with self._sensor_lock:
                p4 = self.p4
            if p4 == 1:
                self.get_logger().info(f"✅ [{label}] P4=1 ยืนยันแล้ว")
                return True
            if (time.time() - t_start) > timeout:
                self.get_logger().error(f"❌ [{label}] P4 TIMEOUT ({timeout}s) — หยุดการทำงาน!")
                return False
            time.sleep(0.05)
        return False

    def initial_arm_lift(self):
        self.get_logger().info("⬆️ [ARM LIFT] UP_ON (13s) ...")
        self.send_udp("DOWN_OFF", bypass_safety=True)
        self.send_udp("UP_ON", bypass_safety=True)
        time.sleep(VALVE_REPEAT_DURATION)
        self.send_udp("UP_OFF", bypass_safety=True)
        if not self._wait_for_p4(timeout=P4_TIMEOUT, label="ARM LIFT"):
            self.get_logger().error("🚫 [ARM LIFT] P4 ไม่ทำงาน — ยกเลิกการทำงานทั้งหมด!")
            self.emergency_shutdown()
            return False
        time.sleep(0.3)
        return True

    def _wait_for_sensor_data(self, timeout=5.0, label=""):
        t_start = time.time()
        while rclpy.ok() and self.is_system_ready:
            with self._sensor_lock:
                got_data = self.e1_raw is not None
            if got_data:
                return True
            if (time.time() - t_start) > timeout:
                return False
            time.sleep(0.05)
        return False

    def do_homing(self, label="HOMING"):
        if not self.system_started:
            self.send_udp("ARM"); time.sleep(0.2); self.send_udp("START")
            self.system_started = True
        self._wait_for_sensor_data(timeout=5.0, label=label)
        with self._sensor_lock:
            p4_now = self.p4
        if p4_now == 1:
            self.get_logger().info("✅ [HOMING] P4=1 แขนอยู่ตำแหน่งบนแล้ว — เริ่ม MAG1_ON ทันที")
        else:
            self.send_udp("DOWN_OFF", bypass_safety=True)
            self.send_udp("UP_ON",   bypass_safety=True)
            homing_up_start = time.time()
            while rclpy.ok() and self.is_system_ready:
                with self._sensor_lock:
                    e2_now = self.e2_raw
                if e2_now is not None and e2_now <= self.E2_UP_THRESHOLD:
                    break
                if (time.time() - homing_up_start) > (VALVE_REPEAT_DURATION + P4_TIMEOUT):
                    break
                time.sleep(0.02)
            self.send_udp("UP_OFF", bypass_safety=True)
            if not self._wait_for_p4(timeout=P4_TIMEOUT, label=f"{label}-WAIT-P4"):
                self.get_logger().error(f"🚫 [{label}] P4 ไม่ทำงานหลัง UP_OFF — ยกเลิก Homing!")
                self.emergency_shutdown()
                return False
        self.is_homed = False
        self.send_udp("MAG1_ON", bypass_safety=True)
        self.send_udp("MAG2_OFF", bypass_safety=True)
        start_time = time.time()
        while rclpy.ok() and self.is_system_ready:
            if self._safety_paused:
                if not self._wait_if_paused(f"{label}-HOMING-LOOP"):
                    return False
                self.send_udp("MAG2_OFF", bypass_safety=True)
                self.send_udp("MAG1_ON",  bypass_safety=True)
            with self._sensor_lock:
                ls1 = self.ls1_state
            if ls1 == 1:
                self.send_udp("MAG1_OFF")
                self.send_udp("MAG2_OFF")
                with self._sensor_lock:
                    self.e1_offset = self.e1_raw if self.e1_raw is not None else 0
                    self.smooth_pos = GAZEBO_RAD_MAX if INVERT_TWIN_ROTATION else GAZEBO_RAD_MIN
                    self.last_sent_pos = self.smooth_pos
                self.is_homed = True
                self.publish_to_gazebo(self.smooth_pos, sec=0.2)
                self.get_logger().info(f"✅ [{label}] Homing สำเร็จ! e1_offset={self.e1_offset}")
                return True
            if (time.time() - start_time) > HOMING_TIMEOUT:
                self.send_udp("MAG1_OFF")
                self.send_udp("MAG2_OFF")
                self.get_logger().error(f"❌ [{label}] Homing Timeout!")
                return False
            time.sleep(0.05)
        return False

    E2_UP_THRESHOLD = -160

    def do_bungkee_task(self):
        if not self.yolo_safety_check(label="BUNGKEE-PRE"):
            return False
        self.get_logger().info(
            f"⚙️ [BUNGKEE] DOWN_ON — รอจนกว่า E2 ≥ {E2_DOWN_THRESHOLD}...")
        self.send_udp("UP_OFF")
        self.send_udp("DOWN_ON")
        self.bungkee_cmd = "DOWN"
        self.brake_triggered = False
        down_stop_event = threading.Event()
        down_monitor_thread = threading.Thread(
            target=self._bungkee_yolo_brake_monitor,
            args=("DOWN", down_stop_event), daemon=True)
        down_monitor_thread.start()
        try:
            while rclpy.ok() and self.is_system_ready:
                if not self._wait_if_paused("BUNGKEE-DOWN"):
                    break
                with self._sensor_lock:
                    e2 = self.e2_raw if self.e2_raw is not None else 0
                if e2 >= E2_DOWN_THRESHOLD:
                    break
                time.sleep(0.02)
        finally:
            down_stop_event.set()
            down_monitor_thread.join(timeout=3.0)
        self.send_udp("DOWN_OFF")
        self.get_logger().info("⚙️ [BUNGKEE] DOWN_OFF แล้ว — รอ 12 วินาที...")
        wait_start = time.time()
        while time.time() - wait_start < 12.0:
            if not self._wait_if_paused("BUNGKEE-WAIT12"):
                break
            time.sleep(0.1)
        self.get_logger().info("⚙️ [BUNGKEE] B1_ON (1.1s) ก่อนยกขึ้น...")
        self.send_udp("B1_ON"); time.sleep(1.1); self.send_udp("B1_OFF")
        self.get_logger().info("⚙️ [BUNGKEE] UP_ON — รอจนกว่า E2 ≤ threshold...")
        self.send_udp("DOWN_OFF"); self.send_udp("UP_ON")
        self.bungkee_cmd = "UP"
        self.brake_triggered = False
        up_stop_event = threading.Event()
        up_monitor_thread = threading.Thread(
            target=self._bungkee_yolo_brake_monitor,
            args=("UP", up_stop_event), daemon=True)
        up_monitor_thread.start()
        try:
            while rclpy.ok() and self.is_system_ready:
                if not self._wait_if_paused("BUNGKEE-UP"):
                    break
                with self._sensor_lock:
                    e2 = self.e2_raw if self.e2_raw is not None else 9999
                if e2 <= self.E2_UP_THRESHOLD:
                    break
                time.sleep(0.02)
        finally:
            up_stop_event.set()
            up_monitor_thread.join(timeout=3.0)
        self.send_udp("UP_OFF")
        if not self._wait_for_p4(timeout=P4_TIMEOUT, label="BUNGKEE UP"):
            self.get_logger().error("🚫 [BUNGKEE] P4 ไม่ทำงาน — ยกเลิก!")
            self.emergency_shutdown()
            return False
        time.sleep(1.0)
        self.send_udp("B1_ON"); self.send_udp("B2_ON")
        time.sleep(1.1)
        self.send_udp("B1_OFF"); self.send_udp("B2_OFF")
        self.bungkee_cmd = None
        self.get_logger().info("✅ [BUNGKEE] Task เสร็จสิ้น")
        return True

    # =========================================================
    # run_cycle  (c1 / c2 / c3)
    # =========================================================
    def run_cycle(self, slot_number):
        if not self.is_system_ready or self.cycle_running:
            return False
        self.cycle_running = True
        slot = slot_number
        center_enc = SLOT_TARGETS.get(slot, 6)
        cycle_start = time.time()
        total_scoops = 0
        try:
            if not self.do_homing(label=f"CYCLE{slot}-HOME"):
                return False
            time.sleep(0.5)
            self._xcycle_reset_round(slot)
            pass_num = 0
            while rclpy.ok() and self.is_system_ready:
                if self._is_slot_full(slot):
                    break
                pass_num += 1
                if pass_num > XCYCLE_MAX_PASSES:
                    break
                self.move_to_enc(center_enc, 0.0)
                if self._is_slot_full(slot):
                    break
                wait_start = time.time()
                while time.time() - wait_start < 2.0:
                    if not self._wait_if_paused(f"CYCLE{slot}-CAM-WAIT"):
                        break
                    time.sleep(0.1)
                if self._is_slot_full(slot):
                    break
                with self._xcycle_round_lock:
                    cur_round_idx = self._xcycle_capture_round[slot]
                target_e1 = self._xcycle_request_capture(
                    slot=slot, round_idx=cur_round_idx,
                    label=f"CYCLE-S{slot}-P{pass_num}")
                if target_e1 is None:
                    self._xcycle_advance_round(slot)
                    continue
                if self._is_slot_full(slot):
                    break
                self.move_to_enc(target_e1, 0.0)
                time.sleep(0.5)
                if self._is_slot_full(slot):
                    break
                total_scoops += 1
                if not self.do_bungkee_task():
                    return False
                self._xcycle_advance_round(slot)

            elapsed = time.time() - cycle_start
            full_tag = "เต็ม ✅" if self._is_slot_full(slot) else "ยังไม่เต็ม ⚠️"
            self.get_logger().info(
                f"📊 [CYCLE-{slot}] จบ | โกย {total_scoops} ครั้ง | "
                f"{self._fmt_seconds(elapsed)} | {full_tag}")

            summary_lines = [
                f"╔══ CYCLE {slot} — สรุปผลการทำงาน ══╗",
                f"  ช่อง {slot}  : {self._fmt_seconds(elapsed)}",
                f"  โกย       : {total_scoops} ครั้ง",
                f"  สถานะ     : {full_tag}",
                f"╚{'═' * 30}╝",
            ]
            self.publish_summary_to_web("\n".join(summary_lines))
            return True
        finally:
            self.cycle_running = False

    @staticmethod
    def _fmt_seconds(secs):
        if secs >= 60:
            m = int(secs) // 60
            s = secs - m * 60
            return f"{m}m {s:.1f}s"
        return f"{secs:.1f}s"

    def _is_slot_full(self, slot):
        with self._sensor_lock:
            return {1: self.p1, 2: self.p2, 3: self.p3}.get(slot, 0) == 1

    def _xcycle_request_capture(self, slot, round_idx, label=""):
        rnd_info = XCYCLE_CAPTURE_ROUNDS[round_idx]
        cmd_payload = json.dumps({
            "XCAP": 1, "SLOT": slot,
            "ROUND": rnd_info["round"], "PCT": rnd_info["pct"],
        })
        self.cam_target_event.clear()
        self.target_e1_from_cam = None
        try:
            sock.sendto(cmd_payload.encode(), (PI_IP, PI_PORT))
        except Exception as e:
            self.get_logger().error(f"❌ [{label}] ส่ง XCAP ล้มเหลว: {e}")
            return None
        got = self.cam_target_event.wait(timeout=XCYCLE_CAM_TIMEOUT)
        if got and self.target_e1_from_cam is not None:
            return self.target_e1_from_cam
        return None

    def _xcycle_advance_round(self, slot):
        with self._xcycle_round_lock:
            current = self._xcycle_capture_round[slot]
            nxt = (current + 1) % len(XCYCLE_CAPTURE_ROUNDS)
            self._xcycle_capture_round[slot] = nxt
            return nxt

    def _xcycle_reset_round(self, slot):
        with self._xcycle_round_lock:
            self._xcycle_capture_round[slot] = 0

    # =========================================================
    # run_x_cycle  (AUTO command)
    # =========================================================
    def run_x_cycle(self):
        if not self.is_system_ready or self.cycle_running:
            return False
        self.cycle_running = True
        total_start = time.time()
        slot_results = {
            s: {"time": 0.0, "scoops": 0, "passes": 0, "pass_log": []}
            for s in [1, 2, 3]
        }
        try:
            if not self.do_homing(label="AUTO-PROCESS-HOME"):
                return False
            time.sleep(0.5)
            for slot in [1, 2, 3]:
                self._xcycle_reset_round(slot)
            outer_pass = 0
            while rclpy.ok() and self.is_system_ready:
                slots_not_full = [s for s in [1, 2, 3] if not self._is_slot_full(s)]
                if not slots_not_full:
                    break
                outer_pass += 1
                slot = slots_not_full[0]
                center_enc = SLOT_TARGETS.get(slot, 6)
                slot_pass_start = time.time()
                slot_results[slot]["passes"] += 1
                current_pass_num = slot_results[slot]["passes"]
                pass_scoops_before = slot_results[slot]["scoops"]
                while rclpy.ok() and self.is_system_ready:
                    if self._is_slot_full(slot):
                        break
                    if slot_results[slot]["passes"] > XCYCLE_MAX_PASSES:
                        break
                    self.move_to_enc(center_enc, 0.0)
                    if self._is_slot_full(slot):
                        break
                    wait_start = time.time()
                    while time.time() - wait_start < 2.0:
                        if not self._wait_if_paused("AUTO-PROCESS-CAM-WAIT"):
                            break
                        time.sleep(0.1)
                    if self._is_slot_full(slot):
                        break
                    with self._xcycle_round_lock:
                        cur_round_idx = self._xcycle_capture_round[slot]
                    target_e1 = self._xcycle_request_capture(
                        slot=slot, round_idx=cur_round_idx,
                        label=f"AUTO-PROCESS-S{slot}-P{current_pass_num}")
                    if target_e1 is None:
                        self._xcycle_advance_round(slot)
                        continue
                    if self._is_slot_full(slot):
                        break
                    self.move_to_enc(target_e1, 0.0)
                    time.sleep(0.5)
                    if self._is_slot_full(slot):
                        break
                    slot_results[slot]["scoops"] += 1
                    if not self.do_bungkee_task():
                        pass_elapsed = time.time() - slot_pass_start
                        slot_results[slot]["time"] += pass_elapsed
                        slot_results[slot]["pass_log"].append({
                            "pass":   current_pass_num,
                            "scoops": slot_results[slot]["scoops"] - pass_scoops_before,
                            "time":   pass_elapsed,
                        })
                        return False
                    self._xcycle_advance_round(slot)
                    if self._is_slot_full(slot):
                        break
                pass_elapsed = time.time() - slot_pass_start
                slot_results[slot]["time"] += pass_elapsed
                scoops_this_pass = slot_results[slot]["scoops"] - pass_scoops_before
                slot_results[slot]["pass_log"].append({
                    "pass":   current_pass_num,
                    "scoops": scoops_this_pass,
                    "time":   pass_elapsed,
                })
            self.do_homing(label="AUTO-PROCESS-END-HOME")
            total_elapsed  = time.time() - total_start
            total_scoops   = sum(r["scoops"] for r in slot_results.values())
            total_passes   = sum(r["passes"] for r in slot_results.values())

            sep = "=" * 62
            self.get_logger().info(sep)
            self.get_logger().info("📊 [AUTO PROCESS] สรุปผลการทำงาน")
            for slot in [1, 2, 3]:
                r = slot_results[slot]
                full_tag = "✅ เต็ม" if self._is_slot_full(slot) else "⚠️ ยังไม่เต็ม"
                self.get_logger().info(
                    f"   ช่อง {slot} : {self._fmt_seconds(r['time'])} | "
                    f"โกย {r['scoops']} ครั้ง | {r['passes']} รอบ | {full_tag}")
            self.get_logger().info(
                f"   รวม : {self._fmt_seconds(total_elapsed)} | "
                f"โกย {total_scoops} ครั้ง | {total_passes} รอบ")
            self.get_logger().info(sep)

            summary_lines = ["╔══ AUTO PROCESS — สรุปผลการทำงาน ══╗"]
            for slot in [1, 2, 3]:
                r = slot_results[slot]
                full_tag = "✅ เต็ม" if self._is_slot_full(slot) else "⚠️ ยังไม่เต็ม"
                summary_lines.append(
                    f"  ช่อง {slot}  : {self._fmt_seconds(r['time'])} | "
                    f"โกย {r['scoops']} ครั้ง | {r['passes']} รอบ | {full_tag}"
                )
            summary_lines.append(
                f"  รวม    : {self._fmt_seconds(total_elapsed)} | "
                f"โกย {total_scoops} ครั้ง | {total_passes} รอบ"
            )
            summary_lines.append(f"╚{'═' * 36}╝")
            self.publish_summary_to_web("\n".join(summary_lines))
            return True
        finally:
            self.cycle_running = False

    def run_homing_manual(self):
        if not self.is_system_ready or self.cycle_running:
            return False
        ok = self.do_homing(label="MANUAL-HOME")
        if ok:
            self._manual_homed = True
        return ok

    def run_manual(self, enc_target):
        if not self.is_system_ready or self.cycle_running:
            return False
        if not self._manual_lock.acquire(blocking=False):
            return False
        try:
            enc_target = max(ENCODER_MIN, min(ENCODER_MAX, int(enc_target)))
            if not self._manual_homed:
                ok = self.do_homing(label="MANUAL-AUTO-HOME")
                if not ok:
                    return False
                self._manual_homed = True
                time.sleep(0.3)
            self._manual_moving = True
            self.move_to_enc(enc_target, 0.0)
            self._manual_moving = False
            return True
        finally:
            self._manual_moving = False
            self._manual_lock.release()

    def web_control_callback(self, msg):
        cmd = msg.data.lower()
        self.get_logger().info(f"📨 [WEB_CMD] Received: {cmd}")
        self.execute_command(cmd)

    def execute_command(self, cmd):
        if cmd.startswith('c') and len(cmd) > 1 and cmd[1].isdigit():
            slot = int(cmd[1])
            threading.Thread(target=self.run_cycle, args=(slot,), daemon=True).start()
        elif cmd == 'x':
            threading.Thread(target=self.run_x_cycle, daemon=True).start()
        elif cmd == 'h':
            threading.Thread(target=self.run_homing_manual, daemon=True).start()
        elif cmd.startswith('m'):
            parts = cmd[1:].strip()
            if parts.lstrip('-').isdigit():
                enc = int(parts)
                threading.Thread(target=self.run_manual, args=(enc,), daemon=True).start()
        elif cmd == 'reset_manual':
            self._manual_homed = False
        elif cmd == 'ready':
            self.reset_state()
            self._manual_homed = False
            self.is_system_ready = True
        elif cmd in ('q', 'stop'):
            self.emergency_shutdown()

    # =========================================================
    # udp_monitor
    # =========================================================
    def udp_monitor(self):
        while rclpy.ok():
            try:
                data, addr = self.listen_sock.recvfrom(1024)
                raw_msg = data.decode(errors='ignore').strip()
                msg = raw_msg.replace("FROM STM32:", "").strip()
                try:
                    msg_json = json.loads(msg) if msg.startswith('{') else {}
                    if not msg_json:
                        clean_text = msg.replace("DBG", "").replace("|", " ")
                        for item in clean_text.split():
                            item = item.strip()
                            if ":" in item:
                                k, v = item.split(":", 1)
                                k = k.strip().upper(); v = v.strip()
                                try:
                                    digits = ''.join(c for c in v if c.isdigit() or c == '-')
                                    if digits:
                                        msg_json[k] = int(digits)
                                except:
                                    pass

                    if "EMERGENCY" in msg_json:
                        emerg_val = int(msg_json["EMERGENCY"])
                        threading.Thread(
                            target=self._handle_pi_emergency,
                            args=(emerg_val,), daemon=True).start()

                    if msg_json.get("PRESS_STOP") == 1:
                        reason = msg_json.get("REASON", "GPIO22_LOST_WHILE_RUNNING")
                        threading.Thread(
                            target=self._handle_press_stop,
                            args=(reason,), daemon=True).start()

                    if "TARGET_E1" in msg_json:
                        self.target_e1_from_cam = int(msg_json["TARGET_E1"])
                        self.cam_target_event.set()
                        self.get_logger().info(
                            f"🎯 [VISION] E1={self.target_e1_from_cam} "
                            f"(ROUND={msg_json.get('ROUND','?')} "
                            f"PCT={msg_json.get('PEAK_PCT','?')}%)")

                    with self._sensor_lock:
                        if "E1"  in msg_json: self.e1_raw    = int(msg_json["E1"])
                        if "E2"  in msg_json: self.e2_raw    = int(msg_json["E2"])
                        if "LS1" in msg_json: self.ls1_state = int(msg_json["LS1"])
                        if "LS2" in msg_json: self.ls2_state = int(msg_json["LS2"])
                        self.p1 = int(msg_json.get("P1", self.p1))
                        self.p2 = int(msg_json.get("P2", self.p2))
                        self.p3 = int(msg_json.get("P3", self.p3))
                        self.p4 = int(msg_json.get("P4", self.p4))

                    with self._sensor_lock:
                        e2_val = self.e2_raw

                    status_msg = String()
                    with self._press_lost_lock:
                        press_lost_now = self._press_lost
                    status_data = {
                        "p1": self.p1, "p2": self.p2, "p3": self.p3,
                        "is_system_ready":   self.is_system_ready,
                        "is_moving":         self.is_moving,
                        "cycle_running":     self.cycle_running,
                        "last_bungkee_pos":  float(self.last_bungkee_pos),
                        "current_head_deg":  float(self.current_head_deg),
                        "yolo_danger":       self.yolo_monitor.is_danger,
                        "pi_emergency":      self._pi_emergency,
                        "press_lost":        press_lost_now,
                    }
                    status_msg.data = json.dumps(status_data)
                    self.status_pub.publish(status_msg)

                    if msg_json.get("START") == 1:
                        with self._pi_emergency_lock:
                            emerg_on = self._pi_emergency
                        if emerg_on:
                            self.get_logger().warn(
                                "🚨 [UDP] START ถูกบล็อก — Pi Emergency ยังทำงานอยู่!")
                        else:
                            self.reset_state()
                            self.is_system_ready = True
                    if msg_json.get("STOP") == 1:
                        self.emergency_shutdown()

                    if msg_json.get("START_BLOCKED") == 1:
                        blocked_reason = msg_json.get("REASON", "UNKNOWN")
                        self.get_logger().warn(
                            f"🚫 [UDP] Pi บล็อก START: reason={blocked_reason}")
                        if blocked_reason == "PRESS_SENSOR_NOT_ACTIVE":
                            self.get_logger().warn(
                                "⚠️  [UDP] GPIO22 (PRESS) ไม่ active — "
                                "กรุณากดสวิตช์ PRESS ก่อน START")

                    if self.is_system_ready and not self.is_moving:
                        l1, l2 = self.ls1_state, self.ls2_state
                        arm_rad_from_e2 = (e2_to_arm_rad(e2_val)
                                           if e2_val is not None else self.last_bungkee_pos)
                        if l1 == 1 and self._ls1_last == 0:
                            with self._sensor_lock:
                                self.e1_offset = (self.e1_raw if self.e1_raw is not None
                                                  else self.e1_offset)
                            self.smooth_pos = (GAZEBO_RAD_MAX if INVERT_TWIN_ROTATION
                                               else GAZEBO_RAD_MIN)
                            self.publish_to_gazebo(self.smooth_pos, sec=0.1,
                                                   arm_rad=arm_rad_from_e2)
                        elif l2 == 1 and self._ls2_last == 0:
                            with self._sensor_lock:
                                self.e1_offset = ((self.e1_raw - ENCODER_MAX)
                                                  if self.e1_raw is not None
                                                  else self.e1_offset)
                            self.smooth_pos = (GAZEBO_RAD_MIN if INVERT_TWIN_ROTATION
                                               else GAZEBO_RAD_MAX)
                            self.publish_to_gazebo(self.smooth_pos, sec=0.1,
                                                   arm_rad=arm_rad_from_e2)
                        elif self.e1_raw is not None:
                            current_pos = self.e1_raw - self.e1_offset
                            target_rad  = self.calculate_mapping(current_pos)
                            self.publish_to_gazebo(target_rad, sec=0.04,
                                                   arm_rad=arm_rad_from_e2)
                            self.last_sent_pos = target_rad
                        self._ls1_last, self._ls2_last = l1, l2
                except Exception:
                    pass
            except socket.timeout:
                continue
            except Exception as e:
                print(f"UDP Error: {e}")

    def emergency_shutdown(self):
        self.is_system_ready = False
        self.reset_state()
        self.cycle_running = False
        for c in ["STOP", "MAG1_OFF", "MAG2_OFF", "UP_OFF", "DOWN_OFF", "B1_OFF", "B2_OFF"]:
            try:
                sock.sendto(c.encode(), (PI_IP, PI_PORT))
            except:
                pass
        self._stop_all_valve_repeat()
        self.get_logger().warn("🛑 EMERGENCY STOP")

    def trigger_dual_brake_at_bottom(self):
        self.is_braking_now = True
        self.send_udp("B1_ON"); self.send_udp("B2_ON")
        time.sleep(0.8)
        self.send_udp("B1_OFF"); self.send_udp("B2_OFF")
        self.brake_off_timestamp = time.time()
        self.is_braking_now = False

    def trigger_single_brake_at_top_and_resume(self):
        self.is_braking_now = True
        self.send_udp("B1_ON"); time.sleep(0.8); self.send_udp("B1_OFF")
        if self.bungkee_cmd == "UP":
            self.send_udp("UP_ON")
        self.brake_off_timestamp = time.time()
        self.is_braking_now = False

    def joint_callback(self, msg):
        try:
            idx     = msg.name.index('headcrane_Link')
            new_deg = math.degrees(msg.position[idx])
            idx2    = msg.name.index('armcrane_Link')
            bungkee_pos = msg.position[idx2]
            if (not self.system_started or not self.is_moving
                    or not self.is_system_ready or self.is_braking_now):
                self.current_head_deg = new_deg
                self.last_bungkee_pos = bungkee_pos
                return
            diff = new_deg - self.current_head_deg
            if INVERT_TWIN_ROTATION:
                diff = -diff
            if abs(diff) > 0.05 and (time.time() - self.brake_off_timestamp) >= 0.8:
                if diff > 0.1:
                    if self.last_cmd != "MAG2":
                        self.send_udp("MAG2_ON"); self.send_udp("MAG1_OFF"); self.last_cmd = "MAG2"
                elif diff < -0.1:
                    if self.last_cmd != "MAG1":
                        self.send_udp("MAG1_ON"); self.send_udp("MAG2_OFF"); self.last_cmd = "MAG1"
                self.current_head_deg = new_deg
            diff_b  = bungkee_pos - self.last_bungkee_pos
            cur_dir = "UP" if diff_b > 0.001 else "DOWN" if diff_b < -0.001 else None
            if cur_dir and cur_dir != self.bungkee_cmd and (time.time() - self.cmd_timestamp) > 0.1:
                self.send_udp(f"{cur_dir}_ON")
                self.send_udp(f"{'UP' if cur_dir=='DOWN' else 'DOWN'}_OFF")
                self.bungkee_cmd = cur_dir
                self.cmd_timestamp = time.time()
            if bungkee_pos >= -0.01 and self.bungkee_cmd == "UP" and not self.brake_triggered:
                self.send_udp("UP_OFF"); self.brake_triggered = True
            elif bungkee_pos <= -0.99 and self.bungkee_cmd == "DOWN" and not self.brake_triggered:
                self.send_udp("DOWN_OFF")
                threading.Thread(target=self.trigger_dual_brake_at_bottom, daemon=True).start()
                self.brake_triggered = True
            self.last_bungkee_pos = bungkee_pos
        except:
            pass

    def move(self, head_deg, bungkee=0.0):
        if not self.is_system_ready:
            return
        self.is_moving = True
        self.bungkee_active   = (bungkee != 0.0)
        self.last_bungkee_pos = float(bungkee)
        target_rad  = math.radians(head_deg)
        dist_rad    = abs(target_rad - math.radians(self.current_head_deg))
        travel_sec  = max(0.4, dist_rad * 0.5)
        self.publish_to_gazebo(target_rad, sec=travel_sec)
        time.sleep(travel_sec)
        self.is_moving = False
        self.send_udp("MAG1_OFF"); self.send_udp("MAG2_OFF")

    def enc_to_deg(self, enc_pos):
        return math.degrees(self.encoder_to_rad(enc_pos))

    def move_to_enc(self, enc_target, bungkee=0.0):
        self.move(self.enc_to_deg(enc_target), bungkee)
        current_mag_cmd_ref = [""]
        rotate_stop_event = threading.Event()
        rotate_monitor_thread = threading.Thread(
            target=self._rotation_yolo_monitor,
            args=(rotate_stop_event, current_mag_cmd_ref), daemon=True)
        rotate_monitor_thread.start()
        timeout_start = time.time()
        try:
            while rclpy.ok() and self.is_system_ready:
                # ── บันทึกสถานะก่อนเรียก _wait_if_paused ──────────────
                was_paused = self._safety_paused

                if not self._wait_if_paused("MOVE_TO_ENC"):
                    break

                # ── เพิ่งกลับมาจาก pause → ให้ _rotation_yolo_monitor
                #    resume MAG ก่อน แล้ว main loop ค่อยทำงาน
                #    (ป้องกัน MAG ชนกันทำให้กระตุก) ──────────────────
                if was_paused and not self._safety_paused:
                    time.sleep(0.4)
                    # iteration นี้ข้ามการส่ง MAG — monitor thread จัดการแทน
                    time.sleep(0.02)
                    continue

                current_e1 = self.get_e1_position()
                if abs(enc_target - current_e1) <= 0 or (time.time() - timeout_start) > 12.0:
                    break

                with self._safety_lock:
                    paused_now = self._safety_paused
                if not paused_now:
                    diff = enc_target - current_e1
                    if diff > 0:
                        with self._rotation_yolo_brake_lock:
                            self.send_udp("MAG2_ON")
                            self.send_udp("MAG1_OFF")
                        current_mag_cmd_ref[0] = "MAG2"
                    else:
                        with self._rotation_yolo_brake_lock:
                            self.send_udp("MAG1_ON")
                            self.send_udp("MAG2_OFF")
                        current_mag_cmd_ref[0] = "MAG1"
                time.sleep(0.02)
        finally:
            current_mag_cmd_ref[0] = ""
            rotate_stop_event.set()
            rotate_monitor_thread.join(timeout=2.0)
        self.send_udp("MAG1_OFF")
        self.send_udp("MAG2_OFF")
        self.last_cmd = "STOP"


def main():
    rclpy.init()
    node = CraneIntegratedSystem()
    threading.Thread(target=rclpy.spin, args=(node,), daemon=True).start()
    try:
        while rclpy.ok():
            if not node.is_system_ready:
                with node._pi_emergency_lock:
                    emerg_on = node._pi_emergency
                with node._press_lost_lock:
                    press_lost = node._press_lost
                if emerg_on:
                    print("\r🚨 Pi EMERGENCY active — รอ GPIO16 ปล่อยก่อน...", end="")
                elif press_lost:
                    print("\r🛑 PRESS STOP (GPIO22 หลุด) — กด START ใหม่อีกครั้ง...", end="")
                else:
                    print("\r⏳ Waiting START from Pi...", end="")
                time.sleep(0.5)
                continue

            print(f"\n--- TWIN SYNC PRO --- [P1:{node.p1} P2:{node.p2} P3:{node.p3}]")
            print("[c1-c3] Cycle | [x] Auto Process")
            print("[h] Home  |  [m <E1>] Manual move  (เช่น m25 หรือ m 25)")
            print("[reset_manual] รีเซ็ต home flag  |  [q] Quit")
            raw = input("เลือกคำสั่ง: ").strip().lower()

            if raw.startswith('m ') and raw[2:].strip().lstrip('-').isdigit():
                cmd = 'm' + raw[2:].strip()
            elif raw == 'm':
                try:
                    enc_str = input(
                        f"  ระบุพิกัด E1 ({ENCODER_MIN}–{ENCODER_MAX}): ").strip()
                    if enc_str.lstrip('-').isdigit():
                        cmd = 'm' + enc_str
                    else:
                        print("  ❌ พิกัดไม่ถูกต้อง")
                        continue
                except (EOFError, KeyboardInterrupt):
                    continue
            else:
                cmd = raw

            node.execute_command(cmd)
            if cmd == 'q':
                break
    except KeyboardInterrupt:
        pass
    node.yolo_monitor.stop()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
