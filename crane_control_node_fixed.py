#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
import threading
import math
import time
import socket
import json

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
# เพิ่มเติม: นำเข้า String สำหรับรับคำสั่งจากเว็บ
from std_msgs.msg import String

# ===== UDP CONFIG =====
PI_IP = "10.0.0.2"
PI_PORT = 5001
LISTEN_PORT = 5001

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# ===== CYCLE WORKFLOW CONFIG =====
ENCODER_MIN = 0
ENCODER_MAX = 295
GAZEBO_RAD_MIN = -1.623
GAZEBO_RAD_MAX = 1.431

SLOT_TARGETS = {
    1: 27,
    2: 146,
    3: 257,
}

CYCLE_TRAVEL_TIME = 11.0
BANG_BANG_HZ = 20
BANG_BANG_DT = 1.0 / BANG_BANG_HZ
HOMING_TIMEOUT = 30.0

class CraneIntegratedSystem(Node):
    def __init__(self):
        super().__init__('crane_integrated_system')

        self.action_client = ActionClient(self, MoveGroup, '/move_action')
        self.goal_done_event = threading.Event()

        self.current_head_deg = 0.0
        self.last_cmd = None

        self.system_started = False
        self.is_moving = False

        self.bungkee_active = False
        self.rotation_dir = None
        self.last_bungkee_time = 0

        self.last_bungkee_pos = 0.32
        self.bungkee_cmd = None
       
        self.bungkee_debounce_duration = 0.15
        self.pending_bungkee_cmd = None
        self.cmd_timestamp = 0

        self.brake_triggered = False
        self.is_braking_now = False
        self.brake_off_timestamp = 0

        self.e1_offset = 0
        self.smooth_pos = GAZEBO_RAD_MIN
        self.alpha = 0.8
        self.last_sent_pos = GAZEBO_RAD_MIN
        self.gz_publisher = self.create_publisher(JointTrajectory, '/arm_group_controller/joint_trajectory', 1)

        self.e1_raw = None
        self.ls1_state = 0
        self.ls2_state = 0
       
        self.p1 = 0
        self.p2 = 0
        self.p3 = 0
       
        self.e1_position = 0
        self.is_homed = False
        self._sensor_lock = threading.Lock()
        self.cycle_running = False

        self._ls1_count_1 = 0
        self._ls1_count_0 = 0
        self._ls2_count_1 = 0
        self._ls2_count_0 = 0
        self.DEBOUNCE_LIMIT = 4
        self._ls1_last = 0  
        self._ls2_last = 0

        self.listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listen_sock.bind(("0.0.0.0", LISTEN_PORT))
        self.listen_sock.settimeout(0.1)

        self.is_system_ready = False

        self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_callback,
            10)

        # ✅ เพิ่มจุดเชื่อมต่อสำหรับรับคำสั่งจาก Dashboard (Web)
        self.create_subscription(
            String,
            '/web_control_topic',
            self.web_control_callback,
            10)

        # ✅ เพิ่ม Status Publisher สำหรับส่งข้อมูลกลับไปยังหน้าเว็บ
        self.status_publisher = self.create_publisher(String, '/crane_status', 10)
        self.create_timer(0.5, self.publish_status_timer)

        threading.Thread(target=self.udp_monitor, daemon=True).start()

        self.get_logger().info("🔥 CRANE SYSTEM READY (WAITING PI START & WEB COMMANDS)")

    def publish_status_timer(self):
        # รวบรวมสถานะส่งเป็น JSON
        status_data = {
            "p1": self.p1,
            "p2": self.p2,
            "p3": self.p3,
            "is_system_ready": self.is_system_ready,
            "is_moving": self.is_moving,
            "cycle_running": self.cycle_running,
            "last_bungkee_pos": self.last_bungkee_pos,
            "current_head_deg": self.current_head_deg
        }
        msg = String()
        msg.data = json.dumps(status_data)
        self.status_publisher.publish(msg)

    def web_control_callback(self, msg):
        cmd = msg.data.lower().strip()
        self.get_logger().info(f"🌐 [WEB] Received command: '{cmd}' | is_system_ready={self.is_system_ready} | cycle_running={self.cycle_running}")
        self.execute_command(cmd)

    def execute_command(self, cmd):
        # ── Force-ready override (ไม่ต้องรอ Pi ถ้าต้องการ bypass) ──────────────
        if cmd in ('ready', 'start'):
            self.get_logger().info("✅ [WEB] Force system READY (web override)")
            self.reset_state()
            self.is_system_ready = True
            return

        # ── ตรวจก่อนทุกคำสั่ง ────────────────────────────────────────────────
        if not self.is_system_ready:
            self.get_logger().warn(
                f"⚠️ [WEB] CMD '{cmd}' rejected — is_system_ready=False. "
                "กด FORCE READY บน Web ก่อน หรือรอสัญญาณ START จาก Pi"
            )
            return

        if cmd == 'stop' or cmd == 'q':
            self.get_logger().info("🛑 web control: STOP (Emergency)")
            self.emergency_shutdown()

        elif cmd == 'a' or cmd == 'auto':
            if self.cycle_running:
                self.get_logger().warn("⚠️ [WEB] cycle_running=True ยังทำงานอยู่ ข้ามคำสั่ง")
                return
            self.get_logger().info("🤖 web control: RUN FULL AUTO")
            threading.Thread(target=self.run_full_auto, daemon=True).start()

        elif cmd in ('1', '2', '3'):
            slot = int(cmd)
            if self.cycle_running:
                self.get_logger().warn(f"⚠️ [WEB] cycle_running=True ข้ามคำสั่ง slot {slot}")
                return
            self.get_logger().info(f"🚀 [WEB] RUN GENERIC SEQ slot {slot}")
            targets = {1: [SLOT_TARGETS[1]], 2: [SLOT_TARGETS[2]], 3: [SLOT_TARGETS[3]]}
            threading.Thread(target=self.run_generic_sequence, args=(targets[slot], f"Slot{slot}"), daemon=True).start()

        elif cmd.startswith('c') and len(cmd) > 1 and cmd[1].isdigit():
            slot = int(cmd[1])
            if self.cycle_running:
                self.get_logger().warn(f"⚠️ [WEB] cycle_running=True ข้ามคำสั่ง c{slot}")
                return
            self.get_logger().info(f"⚙️ web control: RUN CYCLE SLOT {slot}")
            threading.Thread(target=self.run_cycle, args=(slot,), daemon=True).start()

        elif cmd.startswith('t') and len(cmd) > 1 and cmd[1].isdigit():
            slot = int(cmd[1])
            if self.cycle_running:
                self.get_logger().warn(f"⚠️ [WEB] cycle_running=True ข้ามคำสั่ง t{slot}")
                return
            self.get_logger().info(f"🎯 web control: TARGET MODE SLOT {slot}")
            threading.Thread(target=self.run_target_mode, args=(slot,), daemon=True).start()

        else:
            self.get_logger().warn(f"❓ [WEB] Unknown command: '{cmd}'")

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
        self.goal_done_event.set()

    def calculate_mapping(self, enc_pos_0_295):
        enc_pos_0_295 = max(ENCODER_MIN, min(ENCODER_MAX, enc_pos_0_295))
        raw_target = GAZEBO_RAD_MIN + (float(enc_pos_0_295 - ENCODER_MIN) / (ENCODER_MAX - ENCODER_MIN)) * (GAZEBO_RAD_MAX - GAZEBO_RAD_MIN)
        self.smooth_pos = (self.alpha * raw_target) + ((1 - self.alpha) * self.smooth_pos)
        return max(GAZEBO_RAD_MIN, min(GAZEBO_RAD_MAX, self.smooth_pos))

    def publish_to_gazebo(self, rad):
        traj_msg = JointTrajectory()
        traj_msg.joint_names = ['head_joint', 'bungkee_joint']
        point = JointTrajectoryPoint()
        point.positions = [float(rad), float(self.last_bungkee_pos)]
        point.time_from_start.nanosec = 20000000
        traj_msg.points.append(point)
        self.gz_publisher.publish(traj_msg)

    def encoder_to_rad(self, enc_pos):
        enc_pos = max(ENCODER_MIN, min(ENCODER_MAX, enc_pos))
        rad = GAZEBO_RAD_MIN + (float(enc_pos - ENCODER_MIN) / (ENCODER_MAX - ENCODER_MIN)) * (GAZEBO_RAD_MAX - GAZEBO_RAD_MIN)
        return rad

    def get_e1_position(self):
        with self._sensor_lock:
            if self.e1_raw is None:
                return 0
            enc_pos = self.e1_raw - self.e1_offset
            return max(0, min(ENCODER_MAX, enc_pos))

    def do_homing(self, label="HOMING"):
        if not self.system_started:
            self.send_udp("ARM"); time.sleep(0.2); self.send_udp("START")
            self.system_started = True

        self.get_logger().info(f"🏠 [{label}] เริ่ม Homing ไปทางซ้าย (รอ LS1 นิ่ง)...")
        self.is_homed = False
       
        self.send_udp("MAG1_ON", bypass_safety=True)
        self.send_udp("MAG2_OFF", bypass_safety=True)

        start_time = time.time()
        while rclpy.ok() and self.is_system_ready:
            with self._sensor_lock:
                ls1 = self.ls1_state
           
            if ls1 == 1:
                self.send_udp("MAG1_OFF")
                self.send_udp("MAG2_OFF")
                with self._sensor_lock:
                    self.e1_offset = self.e1_raw if self.e1_raw is not None else 0
                    self.smooth_pos = GAZEBO_RAD_MIN
                    self.last_sent_pos = GAZEBO_RAD_MIN
                self.is_homed = True
                self.publish_to_gazebo(GAZEBO_RAD_MIN)
                self.get_logger().info(f"✅ [{label}] Homing สำเร็จ! e1_offset={self.e1_offset}")
                return True

            if (time.time() - start_time) > HOMING_TIMEOUT:
                self.send_udp("MAG1_OFF")
                self.send_udp("MAG2_OFF")
                self.get_logger().error(f"❌ [{label}] Homing Timeout!")
                return False
            time.sleep(0.05)
        return False

    def do_bungkee_task(self):
        self.get_logger().info("⚙️ [BUNGKEE] เริ่ม Task: ลงโกย...")
        self.send_udp("DOWN_ON"); self.send_udp("UP_OFF")
        self.bungkee_cmd = "DOWN"
        self.brake_triggered = False
        timeout_start = time.time()
        while rclpy.ok() and self.is_system_ready:
            if self.last_bungkee_pos <= 0.02 or (time.time() - timeout_start) > 15.0:
                break
            time.sleep(0.1)
        time.sleep(1.5)
       
        self.get_logger().info("⚙️ [BUNGKEE] ขึ้นกลับ...")
        self.send_udp("UP_ON"); self.send_udp("DOWN_OFF")
        self.bungkee_cmd = "UP"
        self.brake_triggered = False
        timeout_start = time.time()
        while rclpy.ok() and self.is_system_ready:
            if self.last_bungkee_pos >= 0.30 or (time.time() - timeout_start) > 15.0:
                break
            time.sleep(0.1)
        time.sleep(1.5)
       
        self.send_udp("UP_OFF"); self.send_udp("DOWN_OFF")
        self.bungkee_cmd = None
        self.get_logger().info("✅ [BUNGKEE] Task เสร็จสิ้น")

    def run_cycle(self, slot_number):
        if not self.is_system_ready or self.cycle_running:
            return False
       
        self.cycle_running = True
        target_enc = SLOT_TARGETS.get(slot_number, 27)
        try:
            if not self.do_homing(label="PRE-HOME"): return False
            time.sleep(0.5)
           
            self.get_logger().info(f"🚀 [MOVE] ไปยัง Slot {slot_number} (Enc: {target_enc})")
            self.move_to_enc(target_enc, 0.32)
           
            time.sleep(0.5)
            self.do_bungkee_task()
            time.sleep(0.5)
            self.do_homing(label="POST-HOME")
            return True
        finally:
            self.cycle_running = False

    def run_full_auto(self):
        if not self.is_system_ready or self.cycle_running:
            return False
           
        self.cycle_running = True
        try:
            self.get_logger().info("🤖 [FULL AUTO] เริ่มระบบโกยอัตโนมัติ")
            if not self.do_homing(label="AUTO-PRE-HOME"): return False
            time.sleep(0.5)

            if self.p1 == 0:
                self.get_logger().info("🚀 [AUTO] ช่อง 1 ว่าง (P1=0) -> โกยทั่วช่อง")
                for target_enc in [27, 0, 27, 54]:
                    if not self.is_system_ready: break
                    self.move_to_enc(target_enc, 0.32)
                    time.sleep(0.5)
                    self.do_bungkee_task()
                    time.sleep(0.5)
                self.do_homing(label="AUTO-HOME-1")

            if self.p2 == 0:
                self.get_logger().info("🚀 [AUTO] ช่อง 2 ว่าง (P2=0) -> โกยทั่วช่อง")
                for target_enc in [154, 126, 154, 182]:
                    if not self.is_system_ready: break
                    self.move_to_enc(target_enc, 0.32)
                    time.sleep(0.5)
                    self.do_bungkee_task()
                    time.sleep(0.5)
                self.do_homing(label="AUTO-HOME-2")

            if self.p3 == 0:
                self.get_logger().info("🚀 [AUTO] ช่อง 3 ว่าง (P3=0) -> โกยทั่วช่อง")
                for target_enc in [257, 237, 257, 278]:
                    if not self.is_system_ready: break
                    self.move_to_enc(target_enc, 0.32)
                    time.sleep(0.5)
                    self.do_bungkee_task()
                    time.sleep(0.5)
                self.do_homing(label="AUTO-HOME-3")

            self.get_logger().info("✅ [FULL AUTO] จบรอบการทำงานอัตโนมัติ")
            return True
        finally:
            self.cycle_running = False

    def udp_monitor(self):
        while rclpy.ok():
            try:
                data, addr = self.listen_sock.recvfrom(1024)
                raw_msg = data.decode(errors='ignore').strip()
                msg = raw_msg.replace("FROM STM32:", "").strip()

                try:
                    if msg.startswith('{'):
                        msg_json = json.loads(msg)
                    else:
                        msg_json = {}
                        clean_text = msg.replace("|", " ")
                        for item in clean_text.split():
                            if ":" in item:
                                k, v = item.split(":", 1)
                                try: msg_json[k.upper()] = int(''.join(c for c in v if c.isdigit() or c == '-'))
                                except: pass

                    start_val = int(msg_json.get("START", 0))
                    stop_val = int(msg_json.get("STOP", 0))
                    e1_raw = msg_json.get("E1", msg_json.get("e1", None))
                    ls1_raw = msg_json.get("LS1", msg_json.get("ls1", None))
                    ls2_raw = msg_json.get("LS2", msg_json.get("ls2", None))
                    p1_raw = msg_json.get("P1", msg_json.get("p1", None))
                    p2_raw = msg_json.get("P2", msg_json.get("p2", None))
                    p3_raw = msg_json.get("P3", msg_json.get("p3", None))

                    confirmed_ls1 = None
                    if ls1_raw == 1:
                        self._ls1_count_1 += 1
                        self._ls1_count_0 = 0  
                        if self._ls1_count_1 >= self.DEBOUNCE_LIMIT: confirmed_ls1 = 1
                    elif ls1_raw == 0:
                        self._ls1_count_0 += 1
                        self._ls1_count_1 = 0  
                        if self._ls1_count_0 >= self.DEBOUNCE_LIMIT: confirmed_ls1 = 0

                    confirmed_ls2 = None
                    if ls2_raw == 1:
                        self._ls2_count_1 += 1
                        self._ls2_count_0 = 0
                        if self._ls2_count_1 >= self.DEBOUNCE_LIMIT: confirmed_ls2 = 1
                    elif ls2_raw == 0:
                        self._ls2_count_0 += 1
                        self._ls2_count_1 = 0
                        if self._ls2_count_0 >= self.DEBOUNCE_LIMIT: confirmed_ls2 = 0

                    with self._sensor_lock:
                        if e1_raw is not None: self.e1_raw = int(e1_raw)
                        if confirmed_ls1 is not None: self.ls1_state = confirmed_ls1
                        if confirmed_ls2 is not None: self.ls2_state = confirmed_ls2
                        if p1_raw is not None: self.p1 = int(p1_raw)
                        if p2_raw is not None: self.p2 = int(p2_raw)
                        if p3_raw is not None: self.p3 = int(p3_raw)

                    if start_val == 1:
                        self.reset_state()
                        self.is_system_ready = True
                    if stop_val == 1:
                        self.emergency_shutdown()

                    if self.is_system_ready and not self.is_moving:
                        with self._sensor_lock:
                            l1 = self.ls1_state
                            l2 = self.ls2_state
                        ls1_rising = (l1 == 1 and self._ls1_last == 0)
                        ls2_rising = (l2 == 1 and self._ls2_last == 0)

                        if ls1_rising:
                            with self._sensor_lock: self.e1_offset = self.e1_raw if self.e1_raw is not None else self.e1_offset
                            self.smooth_pos = GAZEBO_RAD_MIN
                            self.publish_to_gazebo(GAZEBO_RAD_MIN)
                        elif ls2_rising:
                            with self._sensor_lock: self.e1_offset = (self.e1_raw - ENCODER_MAX) if self.e1_raw is not None else self.e1_offset
                            self.smooth_pos = GAZEBO_RAD_MAX
                            self.publish_to_gazebo(GAZEBO_RAD_MAX)
                        elif e1_raw is not None:
                            current_pos = max(0, min(ENCODER_MAX, self.e1_raw - self.e1_offset))
                            target_rad = self.calculate_mapping(current_pos)
                            self.publish_to_gazebo(target_rad)
                            self.last_sent_pos = target_rad

                        self._ls1_last = l1
                        self._ls2_last = l2
                except: pass
            except socket.timeout: continue
            except Exception as e: print(f"UDP Error: {e}")

    def go_home_sequence(self):
        self.move(-85.0, 0.32)

    def send_udp(self, cmd, bypass_safety=False):
        bypass_ready = ["ARM", "START", "STOP", "MAG1_OFF", "MAG2_OFF", "UP_OFF", "DOWN_OFF", "B1_OFF", "B2_OFF"]
        if not self.is_system_ready and cmd not in bypass_ready:
            return
        try:
            if not bypass_safety and ("MAG1_ON" in cmd or "MAG2_ON" in cmd):
                if self.bungkee_active or self.bungkee_cmd == "DOWN":
                    return
            sock.sendto(cmd.encode(), (PI_IP, PI_PORT))
            print(f"SEND: {cmd}")
        except Exception as e:
            print(f"UDP ERR: {e}")

    def emergency_shutdown(self):
        self.is_system_ready = False
        self.reset_state()
        self.cycle_running = False
        cmds = ["STOP", "MAG1_OFF", "MAG2_OFF", "UP_OFF", "DOWN_OFF", "B1_OFF", "B2_OFF"]
        for c in cmds:
            try: sock.sendto(c.encode(), (PI_IP, PI_PORT))
            except: pass
        self.get_logger().warn("🛑 EMERGENCY STOP")

    def trigger_dual_brake_at_bottom(self):
        self.is_braking_now = True
        self.send_udp("MAG1_OFF"); self.send_udp("MAG2_OFF")
        self.send_udp("B1_ON"); self.send_udp("B2_ON")
        time.sleep(1.0)
        self.send_udp("B1_OFF"); self.send_udp("B2_OFF")
        self.brake_off_timestamp = time.time(); self.is_braking_now = False

    def trigger_single_brake_at_top_and_resume(self):
        self.is_braking_now = True
        self.send_udp("MAG1_OFF"); self.send_udp("MAG2_OFF")
        self.send_udp("B1_ON"); time.sleep(1.0); self.send_udp("B1_OFF")
        if self.bungkee_cmd == "UP": self.send_udp("UP_ON")
        self.brake_off_timestamp = time.time(); self.is_braking_now = False

    def joint_callback(self, msg):
        try:
            idx = msg.name.index('head_joint')
            new_deg = math.degrees(msg.position[idx])
            idx2 = msg.name.index('bungkee_joint')
            bungkee_pos = msg.position[idx2]

            if not self.system_started or not self.is_moving or not self.is_system_ready or self.is_braking_now:
                self.current_head_deg = new_deg
                self.last_bungkee_pos = bungkee_pos
                return
           
            can_rotate = (time.time() - self.brake_off_timestamp) >= 1.0
           
            if self.bungkee_active:
                if self.last_cmd != "STOP" and not self.bungkee_cmd:
                    self.send_udp("MAG1_OFF"); self.send_udp("MAG2_OFF"); self.last_cmd = "STOP"

            if can_rotate:
                diff = new_deg - self.current_head_deg
                if abs(diff) > 0.05:
                    if self.rotation_dir is None:
                        if diff > 0.2:
                            self.rotation_dir = "RIGHT"
                            if self.last_cmd != "MAG2":
                                self.send_udp("MAG2_ON"); self.send_udp("MAG1_OFF")
                                self.last_cmd = "MAG2"
                        elif diff < -0.2:
                            self.rotation_dir = "LEFT"
                            if self.last_cmd != "MAG1":
                                self.send_udp("MAG1_ON"); self.send_udp("MAG2_OFF")
                                self.last_cmd = "MAG1"
                    else:
                        if self.rotation_dir == "RIGHT" and self.last_cmd != "MAG2":
                            self.send_udp("MAG2_ON"); self.send_udp("MAG1_OFF"); self.last_cmd = "MAG2"
                        elif self.rotation_dir == "LEFT" and self.last_cmd != "MAG1":
                            self.send_udp("MAG1_ON"); self.send_udp("MAG2_OFF"); self.last_cmd = "MAG1"
                self.current_head_deg = new_deg

            diff_b = bungkee_pos - self.last_bungkee_pos
            cur_dir = "UP" if diff_b > 0.0001 else "DOWN" if diff_b < -0.0001 else None
            if cur_dir and cur_dir != self.bungkee_cmd:
                if (time.time() - self.cmd_timestamp) > self.bungkee_debounce_duration:
                    if cur_dir == "DOWN": self.send_udp("DOWN_ON"); self.send_udp("UP_OFF")
                    else: self.send_udp("UP_ON"); self.send_udp("DOWN_OFF")
                    self.bungkee_cmd = cur_dir; self.cmd_timestamp = time.time()

            if bungkee_pos >= 0.31 and self.bungkee_cmd == "UP" and not self.brake_triggered:
                self.send_udp("UP_OFF"); threading.Thread(target=self.trigger_single_brake_at_top_and_resume, daemon=True).start()
                self.brake_triggered = True
            elif bungkee_pos <= 0.01 and self.bungkee_cmd == "DOWN" and not self.brake_triggered:
                self.send_udp("DOWN_OFF"); threading.Thread(target=self.trigger_dual_brake_at_bottom, daemon=True).start()
                self.brake_triggered = True
            self.last_bungkee_pos = bungkee_pos
        except: pass

    def move(self, head_deg, bungkee=0.32):
        if not self.is_system_ready: return
        if not self.system_started:
            self.send_udp("ARM"); time.sleep(0.2); self.send_udp("START")
            self.system_started = True
        self.is_moving = True
        if head_deg > self.current_head_deg + 0.5: self.rotation_dir = "RIGHT"
        elif head_deg < self.current_head_deg - 0.5: self.rotation_dir = "LEFT"
        else: self.rotation_dir = None
        self.last_cmd = None
        self.bungkee_active = (bungkee != 0.32)
        goal = MoveGroup.Goal()
        goal.request.group_name = 'all_crane_group'
        jc1 = JointConstraint(joint_name='head_joint', position=math.radians(head_deg))
        jc2 = JointConstraint(joint_name='bungkee_joint', position=float(bungkee))
        goal.request.goal_constraints.append(Constraints(joint_constraints=[jc1, jc2]))
        self.goal_done_event.clear()
        self.action_client.send_goal_async(goal).add_done_callback(self.goal_response)
        self.goal_done_event.wait()
        self.is_moving = False
        self.send_udp("MAG1_OFF"); self.send_udp("MAG2_OFF")

    def enc_to_deg(self, enc_pos):
        rad = GAZEBO_RAD_MIN + (float(enc_pos) / ENCODER_MAX) * (GAZEBO_RAD_MAX - GAZEBO_RAD_MIN)
        return math.degrees(rad)

    def move_to_enc(self, enc_target, bungkee=0.32):
        self.move(self.enc_to_deg(enc_target), bungkee)
        self.get_logger().info(f"🔄 [SYNC] รอ E1: {enc_target}...")
        timeout_start = time.time()
        tolerance = 2  
        while rclpy.ok() and self.is_system_ready:
            if (time.time() - timeout_start) > 20.0: break
            current_e1 = self.get_e1_position()
            diff = enc_target - current_e1
            if abs(diff) <= tolerance: break  
            if diff > 0:
                if self.last_cmd != "MAG2_SYNC":
                    self.send_udp("MAG2_ON"); self.send_udp("MAG1_OFF"); self.last_cmd = "MAG2_SYNC"
            else:
                if self.last_cmd != "MAG1_SYNC":
                    self.send_udp("MAG1_ON"); self.send_udp("MAG2_OFF"); self.last_cmd = "MAG1_SYNC"
            time.sleep(0.05)
        self.send_udp("MAG1_OFF"); self.send_udp("MAG2_OFF")
        self.last_cmd = "STOP"

    def run_generic_sequence(self, enc_positions, name="SEQ"):
        if not self.is_system_ready or self.cycle_running:
            self.get_logger().warn(f"⚠️ [{name}] blocked — ready={self.is_system_ready} cycle={self.cycle_running}")
            return
        self.cycle_running = True
        try:
            if not self.do_homing(label=f"{name}-HOME"):
                return
            time.sleep(0.3)
            for enc in enc_positions:
                if not self.is_system_ready: break
                self.move_to_enc(enc, 0.32); time.sleep(1.5)
                self.move_to_enc(enc, 0.0); self.move_to_enc(enc, 0.32); time.sleep(1.2)
        finally:
            self.cycle_running = False

    def goal_response(self, future):
        handle = future.result()
        if handle.accepted: handle.get_result_async().add_done_callback(lambda f: self.goal_done_event.set())
        else: self.goal_done_event.set()

def main():
    rclpy.init()
    node = CraneIntegratedSystem()
    threading.Thread(target=rclpy.spin, args=(node,), daemon=True).start()
    try:
        while rclpy.ok():
            if not node.is_system_ready:
                print("\r⏳ Waiting START from Pi or Web...", end=""); time.sleep(0.5); continue
            print(f"\n--- ระบบควบคุมปั้นจั่น --- [P1:{node.p1} P2:{node.p2} P3:{node.p3}]")
            print("[1-3] Run Seq | [c1-c3] Cycle | [a] Full Auto | [m] Manual | [q] Quit")
            cmd = input("เลือกคำสั่ง: ").lower()
            if cmd == '1': node.run_generic_sequence([27], "Slot 1")
            elif cmd == '2': node.run_generic_sequence([149], "Slot 2")
            elif cmd == '3': node.run_generic_sequence([257], "Slot 3")
            elif cmd.startswith('c'):
                slot = int(cmd[1]) if len(cmd)>1 and cmd[1].isdigit() else 1
                threading.Thread(target=node.run_cycle, args=(slot,), daemon=True).start()
            elif cmd == 'a':
                threading.Thread(target=node.run_full_auto, daemon=True).start()
            elif cmd == 'm':
                try: enc = int(input("ใส่พิกัด Encoder (0-295): ")); node.move_to_enc(enc, 0.32)
                except: print("❌ input ผิด")
            elif cmd == 'q': break
    except KeyboardInterrupt: pass
    node.destroy_node(); rclpy.shutdown()

if __name__ == '__main__': main()
