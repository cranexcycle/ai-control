#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import threading
import math
import time
import socket
import json


from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from std_msgs.msg import String


# ===== UDP CONFIG (ห้ามแก้) =====
PI_IP = "10.0.0.2"
PI_PORT = 5001
LISTEN_PORT = 5001


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


# ===== DIGITAL TWIN CONFIG =====
INVERT_TWIN_ROTATION = True  # 🔥 กลับด้านการหมุนของโมเดล 3D ให้ตรงกับของจริง


# ===== ขยายขอบเขตการทำงาน (Extended Boundaries ตามภาพ) =====
ENCODER_MIN = 0
ENCODER_MAX = 61


# 🔥 ขยายลิมิตให้กว้างขึ้น
GAZEBO_RAD_MIN = -1.60  # ประมาณ -91.6 องศา
GAZEBO_RAD_MAX = 1.60   # ประมาณ 91.6 องศา


SLOT_TARGETS = {
    1: 7,
    2: 31,
    3: 54,
}


CYCLE_TRAVEL_TIME = 11.0
BANG_BANG_HZ = 20        
BANG_BANG_DT = 1.0 / BANG_BANG_HZ
HOMING_TIMEOUT = 30.0    


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
        # 🔥 เพิ่ม Queue size เป็น 10 เพื่อความต่อเนื่องของข้อมูล
        self.gz_publisher = self.create_publisher(JointTrajectory, '/arm_group_controller/joint_trajectory', 10)
        self.status_pub = self.create_publisher(String, '/crane_status', 10)
        self.create_subscription(String, '/web_control_topic', self.web_control_callback, 10)


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


        self.target_e1_from_cam = None
        self.cam_target_event = threading.Event()


        self._ls1_count_1 = 0
        self._ls1_count_0 = 0
        self._ls2_count_1 = 0
        self._ls2_count_0 = 0
        self.DEBOUNCE_LIMIT = 1  
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


        threading.Thread(target=self.udp_monitor, daemon=True).start()


        self.get_logger().info("🔥 CRANE FAST-TWIN SYSTEM READY (NO MOVEIT - WAITING PI START)")


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


    def calculate_mapping(self, enc_pos_0_max):
        enc_pos_0_max = max(ENCODER_MIN, min(ENCODER_MAX, enc_pos_0_max))
        ratio = float(enc_pos_0_max - ENCODER_MIN) / (ENCODER_MAX - ENCODER_MIN)
       
        if INVERT_TWIN_ROTATION:
            ratio = 1.0 - ratio
           
        raw_target = GAZEBO_RAD_MIN + ratio * (GAZEBO_RAD_MAX - GAZEBO_RAD_MIN)
        self.smooth_pos = (self.alpha * raw_target) + ((1 - self.alpha) * self.smooth_pos)
        return max(GAZEBO_RAD_MIN, min(GAZEBO_RAD_MAX, self.smooth_pos))


    def publish_to_gazebo(self, rad, sec=0.1):
        # 🔥 ปรับ sec เริ่มต้นเป็น 0.1 เพื่อให้ตอบสนองไวขึ้นมาก
        traj_msg = JointTrajectory()
        traj_msg.joint_names = ['headcrane_Link', 'armcrane_Link']
        point = JointTrajectoryPoint()
        point.positions = [float(rad), float(self.last_bungkee_pos)]
        point.time_from_start.sec = int(sec)
        point.time_from_start.nanosec = int((sec - int(sec)) * 1e9)
        traj_msg.points.append(point)
        self.gz_publisher.publish(traj_msg)


    def encoder_to_rad(self, enc_pos):
        enc_pos = max(0, min(ENCODER_MAX, enc_pos))
        ratio = float(enc_pos) / ENCODER_MAX
       
        if INVERT_TWIN_ROTATION:
            ratio = 1.0 - ratio
           
        rad = GAZEBO_RAD_MIN + ratio * (GAZEBO_RAD_MAX - GAZEBO_RAD_MIN)
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


    def do_bungkee_task(self):
        self.get_logger().info("⚙️ [BUNGKEE] เริ่ม Task: ลงโกย...")
        self.send_udp("DOWN_ON"); self.send_udp("UP_OFF")
        self.bungkee_cmd = "DOWN"
        self.brake_triggered = False
        timeout_start = time.time()
        while rclpy.ok() and self.is_system_ready:
            # 🔥 ขยายลิมิตยืดแขนให้ไกลขึ้นเป็น -0.99
            if self.last_bungkee_pos <= -0.98 or (time.time() - timeout_start) > 15.0:
                break
            time.sleep(0.05)
        time.sleep(1.0)
       
        self.get_logger().info("⚙️ [BUNGKEE] ขึ้นกลับ...")
        self.send_udp("UP_ON"); self.send_udp("DOWN_OFF")
        self.bungkee_cmd = "UP"
        self.brake_triggered = False
        timeout_start = time.time()
        while rclpy.ok() and self.is_system_ready:
            if self.last_bungkee_pos >= -0.02 or (time.time() - timeout_start) > 15.0:
                break
            time.sleep(0.05)
        time.sleep(1.0)
       
        self.send_udp("UP_OFF"); self.send_udp("DOWN_OFF")
        self.bungkee_cmd = None
        self.get_logger().info("✅ [BUNGKEE] Task เสร็จสิ้น")


    def run_cycle(self, slot_number):
        if not self.is_system_ready or self.cycle_running:
            return False
       
        self.cycle_running = True
        target_enc = SLOT_TARGETS.get(slot_number, 6)
        try:
            if not self.do_homing(label="PRE-HOME"): return False
            time.sleep(0.3)
           
            self.get_logger().info(f"🚀 [MOVE] ไปยัง Slot {slot_number} (Enc: {target_enc})")
            self.move_to_enc(target_enc, 0.0)
           
            time.sleep(0.3)
            self.do_bungkee_task()
            return True
        finally:
            self.cycle_running = False


    def run_target_mode(self, slot_number):
        if not self.is_system_ready or self.cycle_running:
            return False
       
        self.cycle_running = True
        try:
            self.get_logger().info(f"🎯 [TARGET MODE] เริ่มต้นทำงาน ไปช่องที่ {slot_number}")
           
            if not self.do_homing(label="T-MODE-HOME"): return False
            time.sleep(0.5)
           
            center_enc = SLOT_TARGETS.get(slot_number, 6)
            self.get_logger().info(f"🚀 เคลื่อนที่ไปจุดกึ่งกลางช่อง {slot_number} (E1: {center_enc})")
            self.move_to_enc(center_enc, 0.0)
           
            self.get_logger().info("⏳ รอ 2 วินาที เพื่อให้กล้องนิ่ง...")
            time.sleep(2.0)
           
            self.get_logger().info(f"📸 ส่งคำสั่งแคปภาพช่อง {slot_number} ไปยัง Pi5")
            self.cam_target_event.clear()
            self.send_udp(str(slot_number))
           
            self.get_logger().info("⏳ รอรับพิกัดเป้าหมายจากกล้อง (Timeout 10s)...")
           
            if self.cam_target_event.wait(timeout=10.0):
                target_e1 = self.target_e1_from_cam
                self.get_logger().info(f"🚀 เคลื่อนที่ไปยังเป้าหมายที่กล้องพบ E1: {target_e1}")
               
                self.move_to_enc(target_e1, 0.0)
                time.sleep(0.5)
               
                self.do_bungkee_task()
            else:
                self.get_logger().error("❌ หมดเวลารอรับข้อมูลจากกล้อง (10 วินาที)")
                self.do_homing(label="T-MODE-TIMEOUT")


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


            for p_val, slot, enc_list in [(self.p1, 1, [6, 0, 6, 13]), (self.p2, 2, [31, 22, 31, 40]), (self.p3, 3, [54, 50, 54, 59])]:
                if p_val == 0:
                    self.get_logger().info(f"🚀 [AUTO] ช่อง {slot} ว่าง -> โกยทั่วช่อง")
                    for enc in enc_list:
                        if not self.is_system_ready: break
                        self.move_to_enc(enc, 0.0)
                        self.do_bungkee_task()
                else:
                    self.get_logger().info(f"⏭️ [AUTO] ช่อง {slot} เต็ม -> ข้าม")


            self.get_logger().info("✅ [FULL AUTO] จบรอบการทำงานอัตโนมัติ")
            return True
        finally:
            self.cycle_running = False


    def web_control_callback(self, msg):
        cmd = msg.data.lower()
        self.get_logger().info(f"📨 [WEB_CMD] Received: {cmd}")
        print(f"WEB_CMD: {cmd}")
        self.execute_command(cmd)


    def execute_command(self, cmd):
        if cmd == '1':
            threading.Thread(target=self.run_generic_sequence, args=([SLOT_TARGETS[1]],), daemon=True).start()
        elif cmd == '2':
            threading.Thread(target=self.run_generic_sequence, args=([SLOT_TARGETS[2]],), daemon=True).start()
        elif cmd == '3':
            threading.Thread(target=self.run_generic_sequence, args=([SLOT_TARGETS[3]],), daemon=True).start()

        elif cmd.startswith('c') and len(cmd) > 1 and cmd[1].isdigit():
            slot = int(cmd[1])
            threading.Thread(target=self.run_cycle, args=(slot,), daemon=True).start()

        elif cmd.startswith('t') and len(cmd) > 1 and cmd[1].isdigit():
            slot = int(cmd[1])
            threading.Thread(target=self.run_target_mode, args=(slot,), daemon=True).start()

        elif cmd == 'a':
            threading.Thread(target=self.run_full_auto, daemon=True).start()

        elif cmd == 'm':
            self.get_logger().info("Manual mode via web not fully supported (needs coordinates)")

        elif cmd == 'ready':
            self.get_logger().info("✅ Manual System Ready (Web Override)")
            self.reset_state()
            self.is_system_ready = True

        elif cmd == 'q' or cmd == 'stop':
            self.emergency_shutdown()


    def udp_monitor(self):
        while rclpy.ok():
            try:
                data, addr = self.listen_sock.recvfrom(1024)
                raw_msg = data.decode(errors='ignore').strip()
                msg = raw_msg.replace("FROM STM32:", "").strip()


                try:
                    msg_json = json.loads(msg) if msg.startswith('{') else {}
                    if not msg_json:
                        clean_text = msg.replace("|", " ")
                        for item in clean_text.split():
                            if ":" in item:
                                k, v = item.split(":", 1)
                                try: msg_json[k.upper()] = int(''.join(c for c in v if c.isdigit() or c == '-'))
                                except: pass
                   
                    if "TARGET_E1" in msg_json:
                        self.target_e1_from_cam = int(msg_json["TARGET_E1"])
                        self.cam_target_event.set()
                        self.get_logger().info(f"🎯 [VISION] ได้รับเป้าหมาย E1: {self.target_e1_from_cam}")


                    with self._sensor_lock:
                        if "E1" in msg_json: self.e1_raw = int(msg_json["E1"])
                        if "LS1" in msg_json: self.ls1_state = int(msg_json["LS1"])
                        if "LS2" in msg_json: self.ls2_state = int(msg_json["LS2"])
                        self.p1 = int(msg_json.get("P1", self.p1))
                        self.p2 = int(msg_json.get("P2", self.p2))
                        self.p3 = int(msg_json.get("P3", self.p3))


                    # --- Publish status to Web App ---
                    status_msg = String()
                    status_data = {
                        "p1": self.p1,
                        "p2": self.p2,
                        "p3": self.p3,
                        "is_system_ready": self.is_system_ready,
                        "is_moving": self.is_moving,
                        "cycle_running": self.cycle_running,
                        "last_bungkee_pos": float(self.last_bungkee_pos),
                        "current_head_deg": float(self.current_head_deg)
                    }
                    status_msg.data = json.dumps(status_data)
                    self.status_pub.publish(status_msg)


                    if msg_json.get("START") == 1:
                        self.reset_state()
                        self.is_system_ready = True
                    if msg_json.get("STOP") == 1:
                        self.emergency_shutdown()


                    if self.is_system_ready and not self.is_moving:
                        l1, l2 = self.ls1_state, self.ls2_state
                       
                        # 🔥 บังคับให้ Digital Twin หมุนสุดขอบทันทีที่ชน LS (Hard-Sync)
                        if l1 == 1 and self._ls1_last == 0:
                            with self._sensor_lock: self.e1_offset = self.e1_raw if self.e1_raw is not None else self.e1_offset
                            self.smooth_pos = GAZEBO_RAD_MAX if INVERT_TWIN_ROTATION else GAZEBO_RAD_MIN
                            self.publish_to_gazebo(self.smooth_pos, sec=0.1)
                            self.get_logger().info("🚩 LS1 Active: Jumping Model to LIMIT")
                        elif l2 == 1 and self._ls2_last == 0:
                            with self._sensor_lock: self.e1_offset = (self.e1_raw - ENCODER_MAX) if self.e1_raw is not None else self.e1_offset
                            self.smooth_pos = GAZEBO_RAD_MIN if INVERT_TWIN_ROTATION else GAZEBO_RAD_MAX
                            self.publish_to_gazebo(self.smooth_pos, sec=0.1)
                            self.get_logger().info("🚩 LS2 Active: Jumping Model to LIMIT")
                        elif self.e1_raw is not None:
                            current_pos = self.e1_raw - self.e1_offset
                            target_rad = self.calculate_mapping(current_pos)
                            self.publish_to_gazebo(target_rad, sec=0.04)
                            self.last_sent_pos = target_rad


                        self._ls1_last, self._ls2_last = l1, l2


                except: pass
            except socket.timeout: continue
            except Exception as e: print(f"UDP Error: {e}")


    def send_udp(self, cmd, bypass_safety=False):
        try:
            sock.sendto(cmd.encode(), (PI_IP, PI_PORT))
        except: pass


    def emergency_shutdown(self):
        self.is_system_ready = False; self.reset_state(); self.cycle_running = False
        for c in ["STOP", "MAG1_OFF", "MAG2_OFF", "UP_OFF", "DOWN_OFF", "B1_OFF", "B2_OFF"]:
            self.send_udp(c)
        self.get_logger().warn("🛑 EMERGENCY STOP")


    def trigger_dual_brake_at_bottom(self):
        self.is_braking_now = True
        self.send_udp("B1_ON"); self.send_udp("B2_ON")
        time.sleep(0.8)
        self.send_udp("B1_OFF"); self.send_udp("B2_OFF")
        self.brake_off_timestamp = time.time(); self.is_braking_now = False


    def trigger_single_brake_at_top_and_resume(self):
        self.is_braking_now = True
        self.send_udp("B1_ON"); time.sleep(0.8); self.send_udp("B1_OFF")
        if self.bungkee_cmd == "UP": self.send_udp("UP_ON")
        self.brake_off_timestamp = time.time(); self.is_braking_now = False


    def joint_callback(self, msg):
        try:
            idx = msg.name.index('headcrane_Link')
            new_deg = math.degrees(msg.position[idx])
            idx2 = msg.name.index('armcrane_Link')
            bungkee_pos = msg.position[idx2]


            if not self.system_started or not self.is_moving or not self.is_system_ready or self.is_braking_now:
                self.current_head_deg = new_deg
                self.last_bungkee_pos = bungkee_pos
                return
           
            diff = new_deg - self.current_head_deg
            if INVERT_TWIN_ROTATION: diff = -diff
               
            if abs(diff) > 0.05 and (time.time() - self.brake_off_timestamp) >= 0.8:
                if diff > 0.1:
                    if self.last_cmd != "MAG2": self.send_udp("MAG2_ON"); self.send_udp("MAG1_OFF"); self.last_cmd = "MAG2"
                elif diff < -0.1:
                    if self.last_cmd != "MAG1": self.send_udp("MAG1_ON"); self.send_udp("MAG2_OFF"); self.last_cmd = "MAG1"
                self.current_head_deg = new_deg


            diff_b = bungkee_pos - self.last_bungkee_pos
            cur_dir = "UP" if diff_b > 0.001 else "DOWN" if diff_b < -0.001 else None


            if cur_dir and cur_dir != self.bungkee_cmd and (time.time() - self.cmd_timestamp) > 0.1:
                self.send_udp(f"{cur_dir}_ON")
                self.send_udp(f"{'UP' if cur_dir=='DOWN' else 'DOWN'}_OFF")
                self.bungkee_cmd = cur_dir; self.cmd_timestamp = time.time()


            # 🔥 ขยายลิมิตแขนให้เบรกที่ -0.99
            if bungkee_pos >= -0.01 and self.bungkee_cmd == "UP" and not self.brake_triggered:
                self.send_udp("UP_OFF"); self.brake_triggered = True
            elif bungkee_pos <= -0.99 and self.bungkee_cmd == "DOWN" and not self.brake_triggered:
                self.send_udp("DOWN_OFF"); threading.Thread(target=self.trigger_dual_brake_at_bottom, daemon=True).start(); self.brake_triggered = True
            self.last_bungkee_pos = bungkee_pos
        except: pass


    def move(self, head_deg, bungkee=0.0):
        if not self.is_system_ready: return
        self.is_moving = True
       
        diff_deg = head_deg - self.current_head_deg
        if INVERT_TWIN_ROTATION: diff_deg = -diff_deg
           
        self.bungkee_active = (bungkee != 0.0)
        self.last_bungkee_pos = float(bungkee)


        target_rad = math.radians(head_deg)
        dist_rad = abs(target_rad - math.radians(self.current_head_deg))
        # 🔥 เร่งสปีด travel_sec ให้เร็วขึ้น
        travel_sec = max(0.4, dist_rad * 0.5)


        self.publish_to_gazebo(target_rad, sec=travel_sec)
        time.sleep(travel_sec)
       
        self.is_moving = False
        self.send_udp("MAG1_OFF"); self.send_udp("MAG2_OFF")


    def enc_to_deg(self, enc_pos):
        rad = self.encoder_to_rad(enc_pos)
        return math.degrees(rad)


    def move_to_enc(self, enc_target, bungkee=0.0):
        self.move(self.enc_to_deg(enc_target), bungkee)
        self.get_logger().info(f"🔄 [SYNC] E1: {enc_target}...")
        timeout_start = time.time()
        while rclpy.ok() and self.is_system_ready:
            if abs(enc_target - self.get_e1_position()) <= 0 or (time.time() - timeout_start) > 12.0:
                break
            diff = enc_target - self.get_e1_position()
            self.send_udp("MAG2_ON" if diff > 0 else "MAG1_ON")
            self.send_udp("MAG1_OFF" if diff > 0 else "MAG2_OFF")
            time.sleep(0.02)
           
        self.send_udp("MAG1_OFF"); self.send_udp("MAG2_OFF"); self.last_cmd = "STOP"


    def run_generic_sequence(self, enc_positions, name="SEQ"):
        for enc in enc_positions:
            if not self.is_system_ready: break
            self.move_to_enc(enc, 0.0); time.sleep(0.4)
            self.move_to_enc(enc, -0.99); self.move_to_enc(enc, 0.0); time.sleep(0.4)


def main():
    rclpy.init()
    node = CraneIntegratedSystem()
    threading.Thread(target=rclpy.spin, args=(node,), daemon=True).start()
    try:
        while rclpy.ok():
            if not node.is_system_ready:
                print("\r⏳ Waiting START from Pi...", end=""); time.sleep(0.5); continue
            print(f"\n--- TWIN SYNC PRO --- [P1:{node.p1} P2:{node.p2} P3:{node.p3}]")
            print("[1-3] Run Seq | [c1-c3] Cycle | [a] Full Auto | [t1-t3] Target Mode | [m] Manual | [q] Quit")
            cmd = input("เลือกคำสั่ง: ").lower()
            node.execute_command(cmd)
            if cmd == 'q': break
    except KeyboardInterrupt: pass
    node.destroy_node(); rclpy.shutdown()


if __name__ == '__main__': main()
