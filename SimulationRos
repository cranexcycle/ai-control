import socket
import struct
import numpy as np
import zlib
import threading
import math
from collections import deque
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField, JointState
from std_msgs.msg import Header
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped

# ── CONFIG ───────────────────────────────────────────────────────────────────
SIM_STATION     = '2'        # ← เปลี่ยนได้ตอน runtime ด้วยกด 1/2/3
MIN_PEAK_DIST_M = 0.06

E1_RANGES       = {'1': (-4, 19), '2': (13, 50), '3': (46, 61)}
E1_OUTPUT_CLAMP = {'1': (0, 12),  '2': (24, 38), '3': (48, 61)}
ROI_X_RANGE     = {'1': (151, 382), '2': (119, 419), '3': (151, 326)}

CAPTURE_ROUND_LABELS     = ["1st (100%)", "2nd (65%)", "3rd (50%)"]
CAPTURE_ROUND_THRESHOLDS = [1.00, 0.65, 0.50]

# ── HEIGHT CALIBRATION ───────────────────────────────────────────────────────
# Model (all stations): height_cm = C0 + C1*dist_mm + C2*pv  (3-term)
# Coefficients solved exactly from 3 measured peaks per station (err=0.00cm)

CALIB_PTS = {
    '1': [
        (307, 213, 601.0, 18.0),
        (313, 182, 605.0, 17.5),
        (313, 152, 620.0, 16.0),
    ],
    '2': [
        (248, 222, 637.5, 18.0),   # avg peak#1 (run1+run2)
        (242, 193, 632.5, 17.5),   # avg peak#2 (run1+run2)
        (376, 158, 640.5, 13.0),   # avg peak#3 (run1+run2)
    ],
    '3': [
        (303, 223, 634.0, 18.0),
        (310, 193, 644.0, 17.0),
        (320, 144, 650.0, 16.0),
    ],
}

STATION_COEFFS: dict = {}

# ─────────────────────────────────────────────────────────────────────────────

def _fit_station_coeffs(st, calib_points):
    A = np.array([[1.0, d, float(py)]
                  for _, py, d, _ in calib_points], dtype=np.float64)
    b = np.array([h for *_, h in calib_points], dtype=np.float64)
    if len(calib_points) == 3:
        coeffs = np.linalg.solve(A, b)
    else:
        coeffs, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
    return tuple(float(c) for c in coeffs)


def _init_all_station_coeffs():
    for st, pts in CALIB_PTS.items():
        coeffs = _fit_station_coeffs(st, pts)
        STATION_COEFFS[st] = coeffs
        c0, c1, c2 = coeffs
        print(f"[CALIB] ST:{st}  C0={c0:.4f}  C1={c1:.6f}  C2={c2:.6f}")
        for i, (px, py, dist_mm, true_h) in enumerate(pts):
            pred = _predict_height(px, py, dist_mm, st)
            print(f"  [CHECK] ST:{st} #{i+1} px=({px},{py}) dist={dist_mm:.0f}  "
                  f"pred={pred:.2f}cm  true={true_h:.2f}cm  err={pred - true_h:+.2f}cm")


def _predict_height(pu: int, pv: int, dist_mm: float, station: str) -> float:
    coeffs = STATION_COEFFS.get(station, STATION_COEFFS.get('2'))
    c0, c1, c2 = coeffs
    return c0 + c1 * dist_mm + c2 * float(pv)


_init_all_station_coeffs()


def pixel_dist_to_height_cm(pu: int, pv: int, dist_mm: float,
                             station: str = '2') -> float:
    if dist_mm <= 0:
        return 0.0
    return _predict_height(pu, pv, dist_mm, str(station))


def e1_from_pixel_x(px: float, st_key: str) -> int:
    x_min, x_max   = ROI_X_RANGE[st_key]
    e1_min, e1_max = E1_RANGES[st_key]
    lo, hi         = E1_OUTPUT_CLAMP[st_key]
    raw = e1_min + (px - x_min) * (e1_max - e1_min) / (x_max - x_min)
    return int(np.clip(raw, lo, hi))


class PointCloudReceiver(Node):
    def __init__(self):
        super().__init__('pointcloud_receiver')
        self.pub = self.create_publisher(PointCloud2, '/camera/pointcloud', 10)
        self.tf_br = TransformBroadcaster(self)

        self.current_head_rad = 0.0
        self.current_arm_pos  = 0.0
        self._head_lock = threading.Lock()
        self.create_subscription(JointState, '/joint_states', self._joint_cb, 10)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 16777216)
        self.sock.bind(('0.0.0.0', 5002))
        self.sock.setblocking(False)

        self.chunks       = {}
        self.raw_queue    = deque(maxlen=2)
        self.msg_queue    = deque(maxlen=2)
        self.xyzrgb_queue = deque(maxlen=2)
        self.lock_raw = threading.Lock()
        self.lock_msg = threading.Lock()
        self.lock_xyz = threading.Lock()

        self._print_flag   = False
        self._flag_lock    = threading.Lock()
        self.capture_round = 0

        # ── station state (thread-safe) ──────────────────────────────────────
        self._station      = SIM_STATION
        self._station_lock = threading.Lock()

        threading.Thread(target=self._keyboard_loop, daemon=True).start()
        threading.Thread(target=self.recv_loop,      daemon=True).start()
        threading.Thread(target=self.decode_loop,    daemon=True).start()
        threading.Thread(target=self.publish_loop,   daemon=True).start()

        self.get_logger().info(
            "UDP:5002 -> /camera/pointcloud  |  "
            "กด 1/2/3 = เปลี่ยน station  |  "
            "กด Enter = print peaks  |  "
            "กด r = reset round"
        )

    @property
    def station(self):
        with self._station_lock:
            return self._station

    @station.setter
    def station(self, val):
        with self._station_lock:
            self._station = val

    def _joint_cb(self, msg):
        for attr, joint in [('current_head_rad', 'headcrane_Link'),
                             ('current_arm_pos',  'armcrane_Link')]:
            try:
                idx = msg.name.index(joint)
                with self._head_lock:
                    setattr(self, attr, msg.position[idx])
            except (ValueError, IndexError):
                pass

    def _make_quat(self, roll, pitch, yaw):
        cy = math.cos(yaw * 0.5);  sy = math.sin(yaw * 0.5)
        cp = math.cos(pitch * 0.5); sp = math.sin(pitch * 0.5)
        cr = math.cos(roll * 0.5);  sr = math.sin(roll * 0.5)
        return (cr*cp*cy + sr*sp*sy, sr*cp*cy - cr*sp*sy,
                cr*sp*cy + sr*cp*sy, cr*cp*sy - sr*sp*cy)

    def _broadcast_tf(self, stamp):
        with self._head_lock:
            head_rad = self.current_head_rad
            arm_pos  = self.current_arm_pos

        t1 = TransformStamped()
        t1.header.stamp    = stamp
        t1.header.frame_id = 'world'
        t1.child_frame_id  = 'head_Link'
        t1.transform.translation.x = 0.001
        t1.transform.translation.y = 0.190
        t1.transform.translation.z = 0.320
        w, x, y, z = self._make_quat(math.radians(-90.0), 0.0,
                                      math.radians(-91.264) + head_rad)
        t1.transform.rotation.w = w; t1.transform.rotation.x = x
        t1.transform.rotation.y = y; t1.transform.rotation.z = z
        self.tf_br.sendTransform(t1)

        a37 = math.radians(37.0)
        t2  = TransformStamped()
        t2.header.stamp    = stamp
        t2.header.frame_id = 'head_Link'
        t2.child_frame_id  = 'arm_Link'
        t2.transform.translation.x = -0.558963616568696 + arm_pos * (-math.cos(a37))
        t2.transform.translation.y =  0.286046637096899 + arm_pos *   math.sin(a37)
        t2.transform.translation.z =  0.003102061971664
        w2, x2, y2, z2 = self._make_quat(math.radians(-180.0), 0.0, -a37)
        t2.transform.rotation.w = w2; t2.transform.rotation.x = x2
        t2.transform.rotation.y = y2; t2.transform.rotation.z = z2
        self.tf_br.sendTransform(t2)

    def _find_peaks(self, data, num_peaks=3):
        if len(data) == 0:
            return []

        st    = self.station
        ncols = data.shape[1]
        pts   = data[:, :3]

        if ncols >= 7:
            u_px = data[:, 6]
        else:
            u_px = np.full(len(data), 212.0, dtype=np.float32)

        if ncols >= 9:
            v_px      = data[:, 7]
            depth_raw = data[:, 8]
        elif ncols == 8:
            v_px      = data[:, 7]
            depth_raw = np.abs(pts[:, 2]) * 1000.0
            self.get_logger().warn(
                "Pi ส่ง 8 cols — depth ประมาณจาก camera-Z col 2",
                throttle_duration_sec=10.0
            )
        else:
            _roi_center_pv = {'1': 150.0, '2': 170.0, '3': 150.0}
            v_px      = np.full(len(data), _roi_center_pv.get(st, 160.0), dtype=np.float32)
            depth_raw = np.abs(pts[:, 2]) * 1000.0
            self.get_logger().warn(
                "Point cloud มีแค่ 6 cols — กรุณาอัปเดต pi_bridge.py ให้ส่ง 9 cols",
                throttle_duration_sec=10.0
            )

        used  = np.zeros(len(pts), dtype=bool)
        top_y = None
        peaks = []

        x_min_roi, x_max_roi = ROI_X_RANGE[st]

        for _ in range(num_peaks):
            y_tmp = np.where(used, np.inf, pts[:, 1])
            idx   = int(np.argmin(y_tmp))
            if y_tmp[idx] == np.inf:
                break

            px_m, py_m, pz_m = pts[idx]

            if top_y is None:
                top_y = py_m

            pct = (abs(top_y) / abs(py_m) * 100.0) if py_m != 0 else 100.0

            pu = int(u_px[idx])
            pv = int(v_px[idx])

            if not (x_min_roi <= pu <= x_max_roi):
                self.get_logger().warn(
                    f"Peak u={pu} outside ROI {x_min_roi}–{x_max_roi} "
                    f"for ST:{st} — E1 clamped",
                    throttle_duration_sec=5.0
                )

            e1v       = e1_from_pixel_x(pu, st)
            dist_mm   = float(depth_raw[idx])
            height_cm = pixel_dist_to_height_cm(pu, pv, dist_mm, station=st)

            peaks.append({
                "xy":        (pu, pv),
                "pct":       pct,
                "e1":        e1v,
                "dist_mm":   dist_mm,
                "height_cm": height_cm,
            })

            dists = np.sqrt((pts[:, 0] - px_m)**2 + (pts[:, 1] - py_m)**2)
            used[dists < MIN_PEAK_DIST_M] = True

        return peaks

    def _pick_peak_by_pct(self, peaks, target_pct_float):
        if not peaks:
            return None
        if target_pct_float >= 1.0:
            return peaks[0]
        return min(peaks, key=lambda p: abs(p["pct"] - target_pct_float * 100.0))

    def _keyboard_loop(self):
        while True:
            line = input()
            stripped = line.strip().lower()

            if stripped in ('1', '2', '3'):
                self.station       = stripped
                self.capture_round = 0
                print(f"[STATION] → ST:{stripped}  "
                      f"(capture_round reset → 1st (100%))", flush=True)

            elif stripped == 'r':
                self.capture_round = 0
                print("Round reset -> 1st (100%)", flush=True)

            else:
                with self._flag_lock:
                    self._print_flag = True
                print("[ENTER] printing peaks...", flush=True)

    def recv_loop(self):
        import select
        while True:
            try:
                ready, _, _ = select.select([self.sock], [], [], 0.05)
                if not ready:
                    continue
                while True:
                    try:
                        data, _ = self.sock.recvfrom(65535)
                    except BlockingIOError:
                        break
                    chunk_idx    = data[0]
                    total_chunks = data[1]
                    frame_id     = struct.unpack('H', data[2:4])[0]
                    payload      = data[4:]
                    frame_key = (frame_id, total_chunks)
                    if frame_key not in self.chunks:
                        self.chunks[frame_key] = {}
                    self.chunks[frame_key][chunk_idx] = payload
                    if len(self.chunks[frame_key]) == total_chunks:
                        full = b''.join(
                            self.chunks[frame_key][i] for i in range(total_chunks)
                        )
                        del self.chunks[frame_key]
                        with self.lock_raw:
                            self.raw_queue.append(full)
                if len(self.chunks) > 10:
                    for k in sorted(self.chunks.keys())[:-3]:
                        del self.chunks[k]
            except Exception:
                pass

    def decode_loop(self):
        import time
        while True:
            raw = None
            with self.lock_raw:
                if self.raw_queue:
                    raw = self.raw_queue.pop()
                    self.raw_queue.clear()
            if raw is None:
                time.sleep(0.001)
                continue
            try:
                n, compressed_size = struct.unpack('II', raw[:8])
                compressed = raw[8:8 + compressed_size]
                data_bytes = zlib.decompress(compressed)

                total_floats = len(data_bytes) // 4
                cols = total_floats // n if n > 0 else 9
                xyzrgb = np.frombuffer(data_bytes, dtype=np.float32).reshape(-1, cols)

                if len(xyzrgb) == 0:
                    continue

                self.get_logger().info(
                    f"Decoded point cloud: {len(xyzrgb)} pts, {cols} cols",
                    throttle_duration_sec=5.0
                )

                fields = [
                    PointField(name='x', offset=0,  datatype=PointField.FLOAT32, count=1),
                    PointField(name='y', offset=4,  datatype=PointField.FLOAT32, count=1),
                    PointField(name='z', offset=8,  datatype=PointField.FLOAT32, count=1),
                    PointField(name='r', offset=12, datatype=PointField.FLOAT32, count=1),
                    PointField(name='g', offset=16, datatype=PointField.FLOAT32, count=1),
                    PointField(name='b', offset=20, datatype=PointField.FLOAT32, count=1),
                ]
                header = Header()
                header.stamp    = self.get_clock().now().to_msg()
                header.frame_id = 'head_Link'

                msg = PointCloud2()
                msg.header       = header
                msg.height       = 1
                msg.width        = len(xyzrgb)
                msg.fields       = fields
                msg.is_bigendian = False
                msg.point_step   = 24
                msg.row_step     = msg.point_step * msg.width
                msg.data         = xyzrgb[:, :6].astype(np.float32).tobytes()
                msg.is_dense     = True

                with self.lock_xyz:
                    self.xyzrgb_queue.append(xyzrgb)
                with self.lock_msg:
                    self.msg_queue.append(msg)

            except Exception as e:
                self.get_logger().warn(f"Decode error: {e}")

    def publish_loop(self):
        import time
        while True:
            msg = None
            with self.lock_msg:
                if self.msg_queue:
                    msg = self.msg_queue.pop()
                    self.msg_queue.clear()

            if msg is not None:
                self._broadcast_tf(msg.header.stamp)
                self.pub.publish(msg)
                self.get_logger().info(
                    f"Published {msg.width} points  ST:{self.station}",
                    throttle_duration_sec=2.0
                )

                do_print = False
                with self._flag_lock:
                    if self._print_flag:
                        do_print = True
                        self._print_flag = False

                if do_print:
                    xyzrgb = None
                    with self.lock_xyz:
                        if self.xyzrgb_queue:
                            xyzrgb = self.xyzrgb_queue[-1]

                    if xyzrgb is not None and len(xyzrgb) > 0:
                        st    = self.station
                        peaks = self._find_peaks(xyzrgb, num_peaks=3)
                        rnd   = self.capture_round
                        lbl   = CAPTURE_ROUND_LABELS[rnd]

                        print(f"[PEAKS] round={lbl}  ST:{st}  ({len(peaks)} peaks)", flush=True)
                        for i, pk in enumerate(peaks):
                            pu, pv    = pk["xy"]
                            pct       = pk["pct"]
                            e1v       = pk["e1"]
                            dist_mm   = pk["dist_mm"]
                            height_cm = pk["height_cm"]
                            print(f"  #{i+1}  xy=({pu}, {pv})  pct={pct:.0f}%  E1={e1v:3d}"
                                  f"  dist={dist_mm:.1f}mm  height={height_cm:.2f}cm", flush=True)

                        if peaks:
                            thr    = CAPTURE_ROUND_THRESHOLDS[rnd]
                            chosen = self._pick_peak_by_pct(peaks, thr)
                            cu, cv = chosen["xy"]
                            print(f"[UDP Result] [{lbl}] CHOSEN xy=({cu}, {cv})  "
                                  f"pct={chosen['pct']:.0f}%  E1={chosen['e1']}"
                                  f"  dist={chosen['dist_mm']:.1f}mm"
                                  f"  height={chosen['height_cm']:.2f}cm", flush=True)

                            self.capture_round = (rnd + 1) % 3
                            print(f"capture_round -> {self.capture_round} "
                                  f"({CAPTURE_ROUND_LABELS[self.capture_round]})", flush=True)
            else:
                time.sleep(0.001)


def main():
    rclpy.init()
    node = PointCloudReceiver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
