import cv2
import numpy as np
import pyrealsense2 as rs
from ultralytics import YOLO
import math
import socket
import json
import serial
import threading
import time
import collections
from gpiozero import InputDevice, OutputDevice
from flask import Flask, Response
import onnxruntime as ort
import os


# =========================================================
# 1. CONFIGURATION & NETWORK SETUP
# =========================================================
NOTEBOOK_IP = "10.0.0.1"
NOTEBOOK_PORT = 5000
PI_PORT = 5001

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(("0.0.0.0", PI_PORT))

try:
    ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
except Exception as e:
    print(f"Serial Error: {e}. Check Connection!")


# =========================================================
# 2. HARDWARE SETUP (GPIO & LAMPS)
# =========================================================
btn_start  = InputDevice(17, pull_up=True)
btn_stop   = InputDevice(27, pull_up=True)
press_sens = InputDevice(22, pull_up=True)

# GPIO16: Emergency input - 0V (active LOW) = safe/normal
emerg_sens = InputDevice(16, pull_up=True)

lamp_green = OutputDevice(23, active_high=False, initial_value=False)
lamp_red   = OutputDevice(24, active_high=False, initial_value=True)
lamp_blue  = OutputDevice(25, active_high=False, initial_value=False)

is_running           = 0
current_station      = '1'
auto_capture_trigger = False

# =========================================================
# 2b. EMERGENCY STATE
# =========================================================
emergency_active      = False
emergency_lock        = threading.Lock()
_blink_thread_started = False

last_state = {
    "START": 0,
    "STOP":  int(btn_stop.is_active),
    "PRESS": int(press_sens.is_active)
}

stm32_status = {
    "P1": 0, "P2": 0, "P3": 0, "P4": 0,
    "E1": 0, "E2": 0, "LS1": 0, "LS2": 0
}
stm32_status_lock = threading.Lock()

last_captured_frame = None
stream_lock         = threading.Lock()

# =========================================================
# 2c. X-CYCLE CAPTURE STATE
# =========================================================
xcap_lock            = threading.Lock()
xcap_pending         = None
xcap_trigger_event   = threading.Event()

CAPTURE_ROUND_CONFIGS = [
    {"round": 1, "pct": 100, "label": "1st (100%)"},
    {"round": 2, "pct": 65,  "label": "2nd (65%)"},
    {"round": 3, "pct": 50,  "label": "3rd (50%)"},
]

CAPTURE_ROUND_THRESHOLDS = {1: 1.00, 2: 0.65, 3: 0.50}
CAPTURE_ROUND_LABELS     = ["1st (100%)", "2nd (65%)", "3rd (50%)"]
capture_round      = 0
capture_round_lock = threading.Lock()

multi_peaks_cache = []
multi_peaks_lock  = threading.Lock()


# =========================================================
# YOLO CLASS NAMES (COCO)
# =========================================================
YOLO_CLASS_NAMES = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle",
    4: "airplane", 5: "bus", 6: "train", 7: "truck",
    8: "boat", 9: "traffic light", 10: "fire hydrant",
    11: "stop sign", 12: "parking meter", 13: "bench",
    14: "bird", 15: "cat", 16: "dog", 17: "horse",
    18: "sheep", 19: "cow", 20: "elephant", 21: "bear",
    22: "zebra", 23: "giraffe", 24: "backpack", 25: "umbrella",
    26: "handbag", 27: "tie", 28: "suitcase", 29: "frisbee",
    30: "skis", 31: "snowboard", 32: "sports ball", 33: "kite",
    34: "baseball bat", 35: "baseball glove", 36: "skateboard",
    37: "surfboard", 38: "tennis racket", 39: "bottle",
    40: "wine glass", 41: "cup", 42: "fork", 43: "knife",
    44: "spoon", 45: "bowl", 46: "banana", 47: "apple",
    48: "sandwich", 49: "orange", 50: "broccoli", 51: "carrot",
    52: "hot dog", 53: "pizza", 54: "donut", 55: "cake",
    56: "chair", 57: "couch", 58: "potted plant", 59: "bed",
    60: "dining table", 61: "toilet", 62: "tv", 63: "laptop",
    64: "mouse", 65: "remote", 66: "keyboard", 67: "cell phone",
    68: "microwave", 69: "oven", 70: "toaster", 71: "sink",
    72: "refrigerator", 73: "book", 74: "clock", 75: "vase",
    76: "scissors", 77: "teddy bear", 78: "hair drier", 79: "toothbrush"
}

DANGER_CLASSES = {0, 1, 2, 3, 5, 7, 15, 16}

YOLO_DELAY_SEC   = 1.1
YOLO_VOTE_ROUNDS = 3
YOLO_VOTE_CONF   = 0.5


# =========================================================
# 3. EMERGENCY MONITOR & BLINK
# =========================================================
def _red_blink_loop():
    while True:
        with emergency_lock:
            active = emergency_active
        if active:
            lamp_green.off(); lamp_blue.off()
            lamp_red.on();  time.sleep(0.3)
            lamp_green.off(); lamp_blue.off()
            lamp_red.off(); time.sleep(0.3)
        else:
            time.sleep(0.05)


def emergency_monitor():
    global emergency_active, is_running
    prev_emerg = None
    while True:
        current_emerg = not emerg_sens.is_active
        if current_emerg != prev_emerg:
            if current_emerg:
                print("๐จ [EMERGENCY] GPIO16 signal lost! Emergency mode activated.")
                with emergency_lock:
                    emergency_active = True
                if is_running:
                    reset_all_systems(from_emergency=True)
                lamp_green.off(); lamp_blue.off(); lamp_red.off()
            else:
                print("โ… [EMERGENCY] GPIO16 signal restored. System ready.")
                with emergency_lock:
                    emergency_active = False
                lamp_red.on(); lamp_green.off(); lamp_blue.off()
            prev_emerg = current_emerg
        time.sleep(0.05)


# =========================================================
# 4. BRIDGE FUNCTIONS
# =========================================================
def reset_all_systems(from_emergency=False):
    global is_running
    print("!!! STOP PRESSED: RESETTING ALL SYSTEMS !!!")
    is_running = 0
    with emergency_lock:
        emerg = emergency_active
    if not emerg and not from_emergency:
        lamp_red.on(); lamp_green.off()
    if not from_emergency:
        try:
            ser.write(b"STOP\n"); ser.write(b"DISARM\n")
            ser.write(b"MAG1_OFF\n"); ser.write(b"MAG2_OFF\n")
        except Exception as e:
            print("Serial Reset Err:", e)


def send_full_status():
    try:
        curr_press = int(press_sens.is_active)
        with stm32_status_lock:
            p1=stm32_status["P1"]; p2=stm32_status["P2"]
            p3=stm32_status["P3"]; p4=stm32_status["P4"]
            e1=stm32_status["E1"]; e2=stm32_status["E2"]
            ls1=stm32_status["LS1"]; ls2=stm32_status["LS2"]
        with emergency_lock:
            emerg = int(emergency_active)
        status = json.dumps({
            "START": is_running, "STOP": int(btn_stop.is_active),
            "PRESS": curr_press,
            "P1": p1, "P2": p2, "P3": p3, "P4": p4,
            "E1": e1, "E2": e2, "LS1": ls1, "LS2": ls2,
            "EMERGENCY": emerg,
            "TIME": time.time()
        })
        sock.sendto((status + "\n").encode(), (NOTEBOOK_IP, NOTEBOOK_PORT))
        print(f"๐“ก [FULL STATUS RESEND] Sent: {status}")
    except Exception as e:
        print(f"send_full_status error: {e}")


# =========================================================
# 4b. X-CYCLE CAPTURE HANDLER
# =========================================================
def handle_xcap_command(xcap_data: dict):
    global current_station, auto_capture_trigger

    slot      = int(xcap_data.get("SLOT", 1))
    round_num = int(xcap_data.get("ROUND", 1))
    pct       = int(xcap_data.get("PCT", 100))
    current_station = str(slot)
    print(f"\n๐“ธ [XCAP] เนเธ”เนเธฃเธฑเธเธเธณเธชเธฑเนเธเธ–เนเธฒเธขเธฃเธนเธ: slot={slot} round={round_num} pct={pct}%")
    with xcap_lock:
        global xcap_pending
        xcap_pending = {"slot": slot, "round_num": round_num, "pct": pct}
    xcap_trigger_event.set()


def recv_cmd():
    global is_running, current_station, auto_capture_trigger
    while True:
        try:
            data, _ = sock.recvfrom(4096)
            c = data.decode(errors='ignore')
            for cmd_raw in c.split("\n"):
                cmd_str = cmd_raw.strip()
                if not cmd_str:
                    continue

                if cmd_str.startswith('{'):
                    try:
                        msg_json = json.loads(cmd_str)
                    except json.JSONDecodeError:
                        msg_json = {}

                    if msg_json.get("XCAP") == 1:
                        threading.Thread(
                            target=handle_xcap_command,
                            args=(msg_json,), daemon=True
                        ).start()
                        continue

                    if "DANGER_ON" in cmd_str or msg_json.get("DANGER_ON"):
                        print("๐จ [PI] DANGER_ON received from ROS")
                        continue
                    if "DANGER_OFF" in cmd_str or msg_json.get("DANGER_OFF"):
                        print("โ… [PI] DANGER_OFF received from ROS")
                        continue
                    continue

                cmd = cmd_str
                if cmd in ["1", "2", "3"]:
                    current_station      = cmd
                    auto_capture_trigger = True
                    print(f"\nโ… [RECV] Target Station {cmd} -> Capture Flag Set!\n")
                elif cmd == "START":
                    with emergency_lock:
                        emerg = emergency_active
                    if emerg:
                        print("๐จ [RECV] START rejected โ€” Emergency!")
                        try:
                            payload = json.dumps({
                                "START_BLOCKED": 1, "REASON": "EMERGENCY",
                                "TIME": time.time()
                            })
                            sock.sendto((payload + "\n").encode(), (NOTEBOOK_IP, NOTEBOOK_PORT))
                        except:
                            pass
                    else:
                        is_running = 1
                        ser.write(b"START\n")
                        lamp_green.on(); lamp_red.off()
                        threading.Thread(target=_delayed_full_status_resend, daemon=True).start()
                elif cmd == "STOP":
                    reset_all_systems()
                elif cmd == "ARM":
                    ser.write(b"ARM\n")
                elif cmd == "DISARM":
                    ser.write(b"DISARM\n")
                elif cmd == "G:1":   lamp_green.off()
                elif cmd == "G:0":   lamp_green.on()
                elif cmd == "R:1":   lamp_red.off()
                elif cmd == "R:0":   lamp_red.on()
                elif cmd == "B:1":   lamp_blue.off()
                elif cmd == "B:0":   lamp_blue.on()
                elif cmd == "DANGER_ON":
                    print("๐จ [PI] DANGER_ON received")
                elif cmd == "DANGER_OFF":
                    print("โ… [PI] DANGER_OFF received")
                else:
                    ser.write((cmd + "\n").encode())
        except Exception as e:
            print("RECV ERR:", e)


def _delayed_full_status_resend():
    time.sleep(0.3)
    for i in range(3):
        send_full_status(); time.sleep(0.2)


def _parse_stm32_line(line):
    try:
        clean = line.replace("DBG", "").replace("|", " ")
        parsed = {}
        for item in clean.split():
            item = item.strip()
            if ":" in item:
                k, v = item.split(":", 1)
                k = k.strip().upper(); v = v.strip()
                digits = "".join(c for c in v if c.isdigit() or c == "-")
                if digits: parsed[k] = int(digits)
        keys = ["P1", "P2", "P3", "P4", "E1", "E2", "LS1", "LS2"]
        updated = {k: parsed[k] for k in keys if k in parsed}
        if updated:
            with stm32_status_lock:
                stm32_status.update(updated)
    except:
        pass


def read_ser():
    while True:
        try:
            line = ser.readline().decode(errors='ignore').strip()
            if line:
                print("FROM STM32:", line)
                _parse_stm32_line(line)
                sock.sendto((line + "\n").encode(), (NOTEBOOK_IP, NOTEBOOK_PORT))
        except:
            pass


def gpio_monitor():
    global is_running
    prev_press = None
    while True:
        try:
            curr_btn_start = int(btn_start.is_active)
            curr_btn_stop  = int(btn_stop.is_active)
            curr_press     = int(press_sens.is_active)

            with emergency_lock:
                emerg = emergency_active

            if not emerg:
                if press_sens.is_active and not lamp_blue.is_active:
                    lamp_blue.on()
                elif not press_sens.is_active and lamp_blue.is_active:
                    lamp_blue.off()

            if curr_btn_start == 1 and is_running == 0:
                if emerg:
                    print("๐จ [GPIO] START button pressed but EMERGENCY active โ€” blocked!")
                else:
                    is_running = 1; ser.write(b"START\n")
                    lamp_green.on(); lamp_red.off()
                    threading.Thread(target=_delayed_full_status_resend, daemon=True).start()

            if curr_btn_stop == 1:
                if is_running == 1 or last_state["STOP"] == 0:
                    reset_all_systems()

            curr_input_state = (
                curr_btn_start, curr_btn_stop, curr_press,
                int(not emerg_sens.is_active)
            )
            if not hasattr(gpio_monitor, '_last_input'):
                gpio_monitor._last_input = (None, None, None, None)
            if curr_input_state != gpio_monitor._last_input:
                gpio_monitor._last_input = curr_input_state
                s, st, p, e = curr_input_state
                print(
                    f"\n[PI INPUTS]  "
                    f"GPIO17-START:{'ON ' if s  else 'OFF'}  "
                    f"GPIO27-STOP:{'ON ' if st else 'OFF'}  "
                    f"GPIO22-PRESS:{'ON ' if p  else 'OFF'}  "
                    f"GPIO16-EMERG:{'ON ' if e  else 'OFF'}"
                )

            if (is_running != last_state["START"] or
                    curr_btn_stop != last_state["STOP"] or
                    curr_press != last_state["PRESS"]):
                last_state["START"] = is_running
                last_state["STOP"]  = curr_btn_stop
                last_state["PRESS"] = curr_press
                emerg_int = int(emerg)
                status = json.dumps({
                    "START": is_running, "STOP": curr_btn_stop,
                    "PRESS": curr_press, "EMERGENCY": emerg_int,
                    "TIME": time.time()
                })
                sock.sendto((status + "\n").encode(), (NOTEBOOK_IP, NOTEBOOK_PORT))
            time.sleep(0.01)
        except:
            pass


# =========================================================
# 5. VISION SYSTEM SETUP
# =========================================================
print("Initializing Vision System...")
yolo_guard = YOLO('yolov8n.pt')

model_path = "Model_Fix.onnx"
if not os.path.exists(model_path):
    print(f"โ Model file not found: {model_path}"); exit()

opts = ort.SessionOptions()
opts.intra_op_num_threads = 2
session    = ort.InferenceSession(model_path, sess_options=opts)
input_name = session.get_inputs()[0].name

rois = {
    '1': np.array([[(173,196),(547,170),(502,424),(238,407)]], dtype=np.int32),
    '2': np.array([[(47,305),(635,270),(521,453),(208,468)]], dtype=np.int32),
    '3': np.array([[(165,204),(508,177),(471,439),(248,438)]], dtype=np.int32)
}
e1_ranges = {'1': (-4,18), '2': (14,44), '3': (40,63)}

CAMERA_ANGLE_DEG = 45.0
PILE_HEIGHT_MM   = 180.0
COS_ANGLE        = np.cos(np.deg2rad(CAMERA_ANGLE_DEG))
ANALYSIS_SECONDS = 3

pipeline = rs.pipeline()
config   = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16,  30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
profile  = pipeline.start(config)
align    = rs.align(rs.stream.color)
intr     = profile.get_stream(rs.stream.color).as_video_stream_profile().get_intrinsics()

spatial  = rs.spatial_filter()
temporal = rs.temporal_filter()
spatial.set_option(rs.option.filter_magnitude,    3)
spatial.set_option(rs.option.filter_smooth_alpha, 0.55)
spatial.set_option(rs.option.filter_smooth_delta, 20)


# =========================================================
# 6. ADVANCED ANALYSIS FUNCTIONS
# =========================================================
class SharedState:
    def __init__(self):
        self.lock                = threading.Lock()
        self.peak_xy             = None
        self.ai_xy               = None
        self.e1_val              = 0
        self.dist_mm             = 0.0
        self.heat_overlay        = None
        self.debug_grid          = None
        self.processing          = False
        self.snap_img            = None
        self.snap_depth          = None
        self.frozen              = False
        self.peak_history        = collections.deque(maxlen=8)
        self.latest_img          = None
        self.latest_depth        = None
        self.do_analysis         = False
        self.analysis_until      = 0.0
        self.bump_map            = None
        self.analysis_done_flag  = False
        self.multi_peaks_display = []
        self.xcap_meta           = None


state = SharedState()


def compute_bump_map(depth_f32, mask_safe):
    valid = (depth_f32 > 0) & (mask_safe > 0)
    if np.count_nonzero(valid) < 20:
        return np.zeros_like(depth_f32), None
    vert   = depth_f32 * COS_ANGLE
    h, w   = depth_f32.shape
    ys, xs = np.mgrid[0:h, 0:w]
    xv = xs[valid].astype(np.float64); yv = ys[valid].astype(np.float64); zv = vert[valid].astype(np.float64)
    A  = np.column_stack([xv, yv, np.ones_like(xv)])
    coeffs, _, _, _ = np.linalg.lstsq(A, zv, rcond=None)
    a, b, c = coeffs
    plane    = (a*xs + b*ys + c).astype(np.float32)
    bump_raw = vert - plane; bump_raw[~valid] = 0.0
    bump     = cv2.GaussianBlur(bump_raw, (15,15), 0); bump[~valid] = 0.0
    b_valid  = bump[valid]; peak_v = float(np.percentile(b_valid, 98))
    if abs(peak_v) > 1.0:
        scale = PILE_HEIGHT_MM / peak_v; bump = bump*scale; bump[~valid] = 0.0
    return bump, (a, b, c)


def compute_specular_map(bgr, mask_safe):
    lab   = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    L     = lab[:,:,0].astype(np.float32)
    local = cv2.GaussianBlur(L, (61,61), 0)
    spec  = np.clip(L - local, 0, None); spec[mask_safe==0] = 0
    spec  = cv2.GaussianBlur(spec, (31,31), 0)
    return cv2.normalize(spec, None, 0, 255, cv2.NORM_MINMAX).astype(np.float32)


def compute_diffuse_gradient_map(bgr, mask_safe):
    gray  = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    log_g = np.log1p(gray); illum = cv2.GaussianBlur(log_g, (91,91), 0); reflc = log_g - illum
    gx    = cv2.Sobel(illum, cv2.CV_32F, 1, 0, ksize=7); gy = cv2.Sobel(illum, cv2.CV_32F, 0, 1, ksize=7)
    ig    = cv2.magnitude(gx, gy)
    rx    = cv2.Sobel(reflc, cv2.CV_32F, 1, 0, ksize=5); ry = cv2.Sobel(reflc, cv2.CV_32F, 0, 1, ksize=5)
    rg    = cv2.magnitude(rx, ry)
    dm    = np.clip(cv2.GaussianBlur(ig,(51,51),0) - rg*0.3, 0, None); dm[mask_safe==0] = 0
    return cv2.normalize(dm, None, 0, 255, cv2.NORM_MINMAX).astype(np.float32)


def compute_light_refraction_map(bgr, depth_f32, mask_safe):
    dz_dx = cv2.Sobel(depth_f32, cv2.CV_32F, 1, 0, ksize=7)
    dz_dy = cv2.Sobel(depth_f32, cv2.CV_32F, 0, 1, ksize=7)
    mag   = np.sqrt(dz_dx**2 + dz_dy**2 + 1.0)
    nx    = -dz_dx/(mag+1e-6); ny = -dz_dy/(mag+1e-6); nz = 1.0/(mag+1e-6)
    Lx, Ly, Lz = -0.5/0.866, -0.5/0.866, 0.707/0.866
    exp_s = cv2.normalize(np.clip(nx*Lx+ny*Ly+nz*Lz,0,1), None, 0, 255, cv2.NORM_MINMAX).astype(np.float32)
    gray  = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    act_s = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    res   = np.clip(act_s - exp_s*0.7, 0, None); res[mask_safe==0] = 0
    res   = cv2.GaussianBlur(res, (41,41), 0)
    return cv2.normalize(res, None, 0, 255, cv2.NORM_MINMAX).astype(np.float32)


def build_depth_prominence_map(depth_f32, mask_safe):
    invalid = (depth_f32==0)|(mask_safe==0)
    valid_v = depth_f32[~invalid]
    if len(valid_v)==0: return np.zeros_like(depth_f32)
    p5, p95 = float(np.percentile(valid_v,5)), float(np.percentile(valid_v,95))
    dc = np.clip(depth_f32, p5, p95); dc[mask_safe==0] = p95
    di = p95 - dc; di[mask_safe==0] = 0
    def tophat(src, ks):
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(ks,ks))
        return cv2.morphologyEx(src.astype(np.uint8), cv2.MORPH_TOPHAT, k).astype(np.float32)
    s  = cv2.GaussianBlur(di,(21,21),0); m = cv2.GaussianBlur(di,(61,61),0); lg = cv2.GaussianBlur(di,(121,121),0)
    c  = tophat(s,60)*0.20 + tophat(m,100)*0.35 + tophat(lg,140)*0.45; c[mask_safe==0] = 0
    return cv2.normalize(c, None, 0, 255, cv2.NORM_MINMAX).astype(np.float32)


MIN_PEAK_DISTANCE = 60


def find_multi_peaks(score_map, depth_f32, mask_safe, num_peaks=3, min_dist=MIN_PEAK_DISTANCE):
    blurred = cv2.GaussianBlur(score_map, (51,51), 0); blurred[mask_safe==0] = 0
    work_map = blurred.copy(); peaks = []
    for _ in range(num_peaks):
        _, max_val, _, max_loc = cv2.minMaxLoc(work_map)
        if max_val < 1e-3: break
        px, py = max_loc
        r  = min_dist // 2
        x1 = max(0, px-r); x2 = min(work_map.shape[1], px+r)
        y1 = max(0, py-r); y2 = min(work_map.shape[0], py+r)
        region = work_map[y1:y2, x1:x2]; total = np.sum(region)
        if total > 1e-6:
            ys_r, xs_r = np.mgrid[y1:y2, x1:x2]
            cx = int(np.sum(xs_r*region)/total); cy = int(np.sum(ys_r*region)/total)
        else:
            cx, cy = px, py
        peaks.append((float(max_val), (cx, cy)))
        cv2.circle(work_map, (cx, cy), min_dist, 0, -1)
    return peaks


def e1_from_xy(tx, active_roi, st_key):
    pts_x          = active_roi[0,:,0]
    x_min, x_max   = np.min(pts_x), np.max(pts_x)
    e1_min, e1_max = e1_ranges[st_key]
    return int(np.clip(e1_min + (tx-x_min)*(e1_max-e1_min)/(x_max-x_min), e1_min, e1_max))


def full_analysis(snap_img, snap_depth, active_roi, st_key):
    mask      = np.zeros((480,640), dtype=np.uint8)
    cv2.fillPoly(mask, active_roi, 255)
    mask_safe = cv2.erode(mask, np.ones((55,55), np.uint8), iterations=1)

    specular   = compute_specular_map(snap_img, mask_safe)
    diffuse    = compute_diffuse_gradient_map(snap_img, mask_safe)
    refract    = compute_light_refraction_map(snap_img, snap_depth, mask_safe)
    depth_prom = build_depth_prominence_map(snap_depth, mask_safe)

    ds   = cv2.GaussianBlur(snap_depth,(15,15),0)
    gx   = cv2.Sobel(ds, cv2.CV_32F, 1, 0, ksize=5); gy = cv2.Sobel(ds, cv2.CV_32F, 0, 1, ksize=5)
    curv = cv2.normalize(cv2.magnitude(gx,gy), None, 0, 255, cv2.NORM_MINMAX).astype(np.float32)
    curv[mask_safe==0] = 0

    fusion    = (depth_prom*0.45 + refract*0.20 + specular*0.15 + diffuse*0.10 + curv*0.10)
    fusion[mask_safe==0] = 0
    final_map = cv2.GaussianBlur(fusion,(51,51),0); final_map[mask_safe==0] = 0

    raw_peaks  = find_multi_peaks(final_map, snap_depth, mask_safe, num_peaks=3)
    top_score  = raw_peaks[0][0] if raw_peaks else 1.0
    multi_peaks = []
    for score, (px, py) in raw_peaks:
        pct = score/top_score if top_score > 1e-6 else 0.0
        e1v = e1_from_xy(px, active_roi, st_key)
        multi_peaks.append({
            "xy": (px, py), "score": score, "pct": pct,
            "e1": e1v, "dist": float(snap_depth[py, px])
        })

    primary = multi_peaks[0] if multi_peaks else {"xy":(320,240), "pct":1.0, "e1":0, "dist":0.0}
    tx, ty  = primary["xy"]

    img_in = cv2.resize(cv2.cvtColor(snap_img, cv2.COLOR_BGR2RGB),(224,224)).astype(np.float32)
    img_in = np.expand_dims(np.transpose(img_in,(2,0,1)), 0)
    out    = session.run(None, {input_name: img_in})
    ai_tx, ai_ty = int(out[0][0][0]*640), int(out[0][0][1]*480)

    heat      = cv2.applyColorMap(cv2.normalize(final_map, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8), cv2.COLORMAP_INFERNO)
    heat_masked = np.zeros((480,640,3), dtype=np.uint8); heat_masked[mask_safe>0] = heat[mask_safe>0]

    def norm8(m): return cv2.normalize(m, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    def lbl(img, t):
        o = img.copy(); cv2.putText(o, t, (8,22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1); return o
    c1 = lbl(cv2.applyColorMap(norm8(depth_prom), cv2.COLORMAP_BONE),   "Depth Prom")
    c2 = lbl(cv2.applyColorMap(norm8(specular),   cv2.COLORMAP_HOT),    "Specular")
    c3 = lbl(cv2.applyColorMap(norm8(diffuse),    cv2.COLORMAP_OCEAN),  "Diffuse")
    c4 = lbl(cv2.applyColorMap(norm8(refract),    cv2.COLORMAP_PLASMA), "Refraction")
    debug_grid = cv2.resize(np.vstack([np.hstack([c1,c2]), np.hstack([c3,c4])]), (640,480))

    bump_map, _ = compute_bump_map(snap_depth, mask_safe)

    return dict(
        peak_xy      = (tx, ty),
        ai_xy        = (ai_tx, ai_ty),
        e1_val       = primary["e1"],
        dist_mm      = primary["dist"],
        heat_overlay = heat_masked,
        debug_grid   = debug_grid,
        bump_map     = bump_map,
        multi_peaks  = multi_peaks,
        mask_safe    = mask_safe,
    )


stop_event = threading.Event()


def analysis_worker():
    while not stop_event.is_set():
        with state.lock:
            active   = state.do_analysis
            deadline = state.analysis_until
            img      = state.snap_img
            depth    = state.snap_depth
            st       = current_station
        if not active or img is None or depth is None:
            time.sleep(0.02); continue
        if time.time() > deadline:
            with state.lock:
                if state.do_analysis: state.analysis_done_flag = True
                state.do_analysis = False; state.frozen = False; state.processing = False
            continue
        with state.lock: state.processing = True
        try:
            res = full_analysis(img, depth, rois[st], st)
        except Exception as e:
            print(f"โ ๏ธ {e}")
            with state.lock: state.processing = False
            continue
        with state.lock:
            state.peak_history.append(res['peak_xy'])
            sx = int(np.mean([p[0] for p in state.peak_history]))
            sy = int(np.mean([p[1] for p in state.peak_history]))
            state.peak_xy             = (sx, sy)
            state.ai_xy               = res['ai_xy']
            state.e1_val              = res['e1_val']
            state.dist_mm             = res['dist_mm']
            state.heat_overlay        = res['heat_overlay']
            state.debug_grid          = res['debug_grid']
            state.bump_map            = res['bump_map']
            state.multi_peaks_display = res['multi_peaks']
            state.processing          = False
        with multi_peaks_lock:
            global multi_peaks_cache
            multi_peaks_cache = res['multi_peaks']


# =========================================================
# 7. RESULT SENDER
# =========================================================
def _pick_peak_by_pct(multi_peaks: list, target_pct_float: float) -> dict:
    if not multi_peaks:
        return {"xy": (320, 240), "pct": 1.0, "e1": 0, "dist": 0.0}
    if target_pct_float >= 1.0:
        return multi_peaks[0]
    return min(multi_peaks, key=lambda p: abs(p["pct"] - target_pct_float))


def send_result_for_xcap(multi_peaks: list, xcap_meta: dict):
    if not multi_peaks:
        print("โ ๏ธ [XCAP RESULT] เนเธกเนเธเธ peaks โ€” เธชเนเธ TARGET_E1=-1")
        payload = json.dumps({
            "TARGET_E1": -1,
            "STATION":   xcap_meta.get("slot", 1),
            "ROUND":     xcap_meta.get("round_num", 1),
            "PEAK_PCT":  0.0,
        })
        sock.sendto((payload + "\n").encode(), (NOTEBOOK_IP, NOTEBOOK_PORT))
        return

    slot      = xcap_meta.get("slot", 1)
    round_num = xcap_meta.get("round_num", 1)
    pct       = xcap_meta.get("pct", 100)

    target_pct_float = pct / 100.0
    chosen   = _pick_peak_by_pct(multi_peaks, target_pct_float)
    e1_out   = chosen["e1"]
    xy_out   = chosen["xy"]
    pct_out  = chosen["pct"]

    payload = json.dumps({
        "TARGET_E1": int(e1_out),
        "STATION":   int(slot),
        "ROUND":     int(round_num),
        "PEAK_PCT":  round(pct_out * 100, 1),
        "PEAK_XY":   list(xy_out),
    })
    sock.sendto((payload + "\n").encode(), (NOTEBOOK_IP, NOTEBOOK_PORT))
    print(
        f"๐“ก [XCAP RESULT] เธชเนเธเธเธฅ: slot={slot} round={round_num} "
        f"pct_req={pct}% โ’ E1={e1_out} (peak_pct={round(pct_out*100,1)}%) "
        f"xy={xy_out}"
    )


def send_result_for_round(multi_peaks, station, rnd):
    global capture_round
    if not multi_peaks:
        print("โ ๏ธ No peaks available, skipping send."); return
    threshold = [1.00, 0.65, 0.50][rnd] if rnd < 3 else 1.00
    label     = CAPTURE_ROUND_LABELS[rnd] if rnd < 3 else "?"
    chosen    = _pick_peak_by_pct(multi_peaks, threshold)
    e1_out    = chosen["e1"]; xy_out = chosen["xy"]; pct_out = chosen["pct"]
    payload = json.dumps({
        "TARGET_E1": int(e1_out), "STATION": int(station),
        "ROUND": rnd+1, "PEAK_PCT": round(pct_out*100, 1), "PEAK_XY": list(xy_out)
    })
    sock.sendto((payload+"\n").encode(), (NOTEBOOK_IP, NOTEBOOK_PORT))
    print(f"๐“ก UDP Result Sent [{label}]: {payload}")
    with capture_round_lock:
        capture_round = (rnd+1) % 3


# =========================================================
# 8. FLASK WEB SERVER
# =========================================================
app = Flask(__name__)


def generate_frame():
    global last_captured_frame
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 65]
    while True:
        time.sleep(0.03)
        with stream_lock:
            if last_captured_frame is None:
                dummy = np.zeros((480,640,3), dtype=np.uint8)
                cv2.putText(dummy, "Live Camera Feed Starting...", (40,240),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
                _, encoded_image = cv2.imencode('.jpg', dummy, encode_param)
            else:
                _, encoded_image = cv2.imencode('.jpg', last_captured_frame, encode_param)
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n'
               + encoded_image.tobytes() + b'\r\n')


@app.route('/video_feed')
def video_feed():
    return Response(generate_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')


def start_flask():
    app.run(host='0.0.0.0', port=5002, threaded=True, debug=False, use_reloader=False)


# =========================================================
# 9. YOLO GUARD WITH DELAY + MAJORITY VOTE
# =========================================================
def yolo_check_with_delay(get_frame_func, delay_sec=YOLO_DELAY_SEC,
                          rounds=YOLO_VOTE_ROUNDS, conf=YOLO_VOTE_CONF):
    print(f"โณ [YOLO] Waiting {delay_sec}s before scan...")
    time.sleep(delay_sec)

    snap = get_frame_func()
    vote_danger  = 0
    all_detected = {}
    annotated    = snap.copy()
    majority_needed = rounds // 2 + 1

    for rnd in range(rounds):
        frame = get_frame_func()
        results = yolo_guard(frame, conf=conf, verbose=False)
        found_danger_this_round = False
        for r in results:
            for box in r.boxes:
                cls_id   = int(box.cls[0])
                cls_name = YOLO_CLASS_NAMES.get(cls_id, f"class_{cls_id}")
                all_detected[cls_name] = all_detected.get(cls_name, 0) + 1
                if cls_id in DANGER_CLASSES:
                    found_danger_this_round = True
                    b = box.xyxy[0].cpu().numpy()
                    cv2.rectangle(annotated,
                                  (int(b[0]), int(b[1])), (int(b[2]), int(b[3])),
                                  (0, 0, 255), 3)
                    label_txt = f"{cls_name} {float(box.conf[0]):.2f}"
                    cv2.putText(annotated, label_txt,
                                (int(b[0]), max(int(b[1])-8, 12)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
        if found_danger_this_round:
            vote_danger += 1
        print(f"   [YOLO] Round {rnd+1}/{rounds}: "
              f"{'DANGER' if found_danger_this_round else 'SAFE'} "
              f"| votes so far: {vote_danger}/{majority_needed}")

    is_danger = vote_danger >= majority_needed
    danger_names = [
        name for name, cnt in all_detected.items()
        if any(name == YOLO_CLASS_NAMES.get(c, '') for c in DANGER_CLASSES)
    ]

    if is_danger:
        print(f"๐จ [YOLO] DANGER confirmed ({vote_danger}/{rounds} votes) | Classes: {danger_names}")
    else:
        print(f"โ… [YOLO] SAFE ({vote_danger}/{rounds} danger votes, need {majority_needed})")

    return is_danger, danger_names, annotated


# =========================================================
# 9b. X-CYCLE CAPTURE WORKER THREAD
# =========================================================
def xcap_worker():
    while True:
        triggered = xcap_trigger_event.wait(timeout=1.0)
        if not triggered:
            continue
        xcap_trigger_event.clear()

        with xcap_lock:
            meta = xcap_pending
        if meta is None:
            continue

        slot      = meta["slot"]
        round_num = meta["round_num"]
        pct       = meta["pct"]

        print(f"\n๐” [XCAP WORKER] เน€เธฃเธดเนเธกเธเธฃเธฐเธเธงเธเธเธฒเธฃเธ–เนเธฒเธขเธฃเธนเธ slot={slot} round={round_num} pct={pct}%")

        with emergency_lock:
            emerg = emergency_active
        if emerg:
            print("๐จ [XCAP WORKER] Emergency active โ€” เธขเธเน€เธฅเธดเธ")
            payload = json.dumps({
                "TARGET_E1": -1, "STATION": slot,
                "ROUND": round_num, "PEAK_PCT": 0.0, "REASON": "EMERGENCY",
            })
            sock.sendto((payload + "\n").encode(), (NOTEBOOK_IP, NOTEBOOK_PORT))
            continue

        def get_latest_frame():
            with state.lock:
                f = state.latest_img
            return f.copy() if f is not None else np.zeros((480, 640, 3), dtype=np.uint8)

        with state.lock:
            snap_depth = state.latest_depth.copy() if state.latest_depth is not None else None

        if snap_depth is None:
            print("โ ๏ธ [XCAP WORKER] เนเธกเนเธกเธต depth frame โ€” เธชเนเธ TARGET_E1=-1")
            payload = json.dumps({
                "TARGET_E1": -1, "STATION": slot, "ROUND": round_num, "PEAK_PCT": 0.0,
            })
            sock.sendto((payload + "\n").encode(), (NOTEBOOK_IP, NOTEBOOK_PORT))
            continue

        danger, danger_classes, annotated_img = yolo_check_with_delay(get_latest_frame)

        if danger:
            class_str = ", ".join(danger_classes) if danger_classes else "unknown"
            print(f"๐จ [XCAP WORKER] DANGER detected [{class_str}] โ€” เธชเนเธ TARGET_E1=-1")
            payload = json.dumps({
                "TARGET_E1": -1, "STATION": slot, "ROUND": round_num,
                "DANGER_CLASSES": danger_classes,
            })
            sock.sendto((payload + "\n").encode(), (NOTEBOOK_IP, NOTEBOOK_PORT))
            with stream_lock:
                last_captured_frame = annotated_img.copy()
            continue

        snap_img = get_latest_frame()

        with state.lock:
            state.snap_img           = snap_img
            state.snap_depth         = snap_depth
            state.frozen             = True
            state.do_analysis        = True
            state.analysis_until     = time.time() + ANALYSIS_SECONDS
            state.peak_history.clear()
            state.analysis_done_flag = False
            state.xcap_meta          = meta.copy()

        print(f"โ… [XCAP WORKER] เน€เธฃเธดเนเธก analysis {ANALYSIS_SECONDS}s [slot={slot} round={round_num} pct={pct}%]")

        deadline = time.time() + ANALYSIS_SECONDS + 2.0
        while time.time() < deadline:
            with state.lock:
                done = state.analysis_done_flag
            if done:
                break
            time.sleep(0.05)

        with multi_peaks_lock:
            peaks_now = list(multi_peaks_cache)
        with state.lock:
            xcap_meta_now = state.xcap_meta

        if xcap_meta_now:
            send_result_for_xcap(peaks_now, xcap_meta_now)
        else:
            print("โ ๏ธ [XCAP WORKER] เนเธกเนเธเธ xcap_meta โ€” เธเนเธฒเธก")


# =========================================================
# 10. MAIN EXECUTION
# =========================================================
threading.Thread(target=recv_cmd,          daemon=True).start()
threading.Thread(target=read_ser,          daemon=True).start()
threading.Thread(target=gpio_monitor,      daemon=True).start()
threading.Thread(target=start_flask,       daemon=True).start()
threading.Thread(target=analysis_worker,   daemon=True).start()
threading.Thread(target=emergency_monitor, daemon=True).start()
threading.Thread(target=_red_blink_loop,   daemon=True).start()
threading.Thread(target=xcap_worker,       daemon=True).start()

print("Pi Bridge & Advanced Vision system is running...")
cv2.namedWindow("Live Camera", cv2.WINDOW_NORMAL)

show_debug  = False
debug_open  = False
fps_times   = collections.deque(maxlen=30)
_last_out_state = (None, None, None, None, None)

PEAK_COLORS = [(0,255,255), (0,255,128), (0,165,255)]
PEAK_RADIUS = [22, 18, 14]

try:
    while True:
        frames  = pipeline.wait_for_frames()
        aligned = align.process(frames)

        raw_df = aligned.get_depth_frame()
        cf     = aligned.get_color_frame()
        if not raw_df or not cf: continue

        img_live   = np.asanyarray(cf.get_data())
        depth_live = np.asanyarray(raw_df.get_data())

        with state.lock:
            frozen              = state.frozen
            countdown           = max(0.0, state.analysis_until - time.time())
            peak_xy             = state.peak_xy
            ai_xy               = state.ai_xy
            e1_val              = state.e1_val
            dist_mm             = state.dist_mm
            heat_ov             = state.heat_overlay
            dbg_grid            = state.debug_grid
            bump_map            = state.bump_map
            processing          = state.processing
            snap_disp           = state.snap_img
            multi_peaks_display = list(state.multi_peaks_display)

        if frozen and snap_disp is not None:
            display = snap_disp.copy()
            cv2.rectangle(display, (2,2), (638,478), (0,0,220), 3)
        else:
            display = img_live.copy()
            with state.lock:
                state.latest_img   = img_live.copy()
                state.latest_depth = depth_live.astype(np.float32)

        with capture_round_lock:
            cur_rnd = capture_round

        with emergency_lock:
            emerg_now = emergency_active

        # EMERGENCY OVERLAY
        if emerg_now:
            red_overlay = np.zeros_like(display)
            red_overlay[:] = (0, 0, 80)
            display = cv2.addWeighted(display, 0.75, red_overlay, 0.25, 0)
            if int(time.time() * 2) % 2 == 0:
                cv2.putText(display, "           !! EMERGENCY !! ",
                            (60, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)
                cv2.putText(display, "                  START DISABLED ",
                            (80, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 100, 255), 2)

        # XCAP STATUS OVERLAY
        with xcap_lock:
            xcap_now = xcap_pending
        if xcap_now and frozen:
            xcap_txt = (
                f"[X-CYCLE] slot={xcap_now['slot']} "
                f"round={xcap_now['round_num']} pct={xcap_now['pct']}%"
            )
            cv2.putText(display, xcap_txt, (20, 420),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 2)

        # DEBUG MODE (เธเธ” d)
        if show_debug:
            if heat_ov is not None:
                display = cv2.addWeighted(display, 0.60, heat_ov, 0.40, 0)
            cv2.polylines(display, [rois[current_station]], True, (255,0,255), 2)
            for i, pk in enumerate(multi_peaks_display):
                px, py  = pk["xy"]
                pct_val = pk["pct"]
                e1v     = pk["e1"]
                color   = PEAK_COLORS[i] if i < len(PEAK_COLORS) else (200,200,200)
                radius  = PEAK_RADIUS[i] if i < len(PEAK_RADIUS) else 10
                thr_pct = int([100, 65, 50][i]) if i < 3 else 0
                cv2.circle(display, (px,py), radius, color, 2)
                cv2.drawMarker(display, (px,py), color, cv2.MARKER_CROSS, 30, 2)
                label_txt = f"#{i+1} {int(pct_val*100)}% E1:{e1v}"
                cv2.putText(display, label_txt, (px+25,py+5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
                if i == cur_rnd:
                    cv2.circle(display, (px,py), radius+6, (255,255,255), 1)
                    cv2.putText(display, f"NEXT({thr_pct}%)", (px+25,py+20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255,255,255), 1)
            if peak_xy and bump_map is not None:
                tx, ty = peak_xy; bh = float(bump_map[ty, tx])
                cv2.putText(display, f"bump:{bh:+.1f}mm", (tx+28,ty+30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,255), 1)
            if ai_xy:
                cv2.circle(display, ai_xy, 14, (0,255,0), 2)
                cv2.putText(display, "AI", (ai_xy[0]+16,ai_xy[1]+6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0,255,0), 1)

            # โ”€โ”€ HUD DEBUG โ”€โ”€ เน€เธฅเธทเนเธญเธ y เธฅเธเธกเธฒเนเธซเนเธเนเธ FPS bar (y=30)
            cv2.putText(display, f"E1: {int(e1_val)}",     (20,60),  2, 0.8, (0,255,255), 2)
            cv2.putText(display, f"Dist: {dist_mm:.1f}mm", (20,95),  2, 0.7, (255,255,255), 2)
            cv2.putText(display, f"ST:{current_station}",  (20,130), 2, 0.6, (200,200,200), 1)
            rnd_label = CAPTURE_ROUND_LABELS[cur_rnd] if cur_rnd < 3 else "?"
            cv2.putText(display, f"Round: {rnd_label}",    (20,160),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255,200,0), 1)
            emerg_txt = "EMERG:ON" if emerg_now else "EMERG:OFF"
            emerg_col = (0,0,255) if emerg_now else (0,255,0)
            cv2.putText(display, emerg_txt, (20,190),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, emerg_col, 1)

        # CLEAN MODE (default)
        else:
            if multi_peaks_display and cur_rnd < len(multi_peaks_display):
                pk     = multi_peaks_display[cur_rnd]
                px, py = pk["xy"]
                color  = PEAK_COLORS[cur_rnd] if cur_rnd < len(PEAK_COLORS) else (0,255,255)
                radius = PEAK_RADIUS[cur_rnd] if cur_rnd < len(PEAK_RADIUS) else 22
                cv2.circle(display, (px,py), radius, color, 3)
                cv2.drawMarker(display, (px,py), color, cv2.MARKER_CROSS, 40, 2)

        # HUD
        fps_times.append(cv2.getTickCount())
        fps = ((len(fps_times)-1) * cv2.getTickFrequency() / (fps_times[-1]-fps_times[0])
               if len(fps_times) >= 2 else 0)
        cv2.putText(display, f"ST:{current_station} {fps:.1f}FPS",
                    (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 1)

        if frozen:
            pct_bar = countdown / ANALYSIS_SECONDS
            bar_w   = int(600 * pct_bar)
            cv2.rectangle(display, (20,460), (620,475), (50,50,50), -1)
            cv2.rectangle(display, (20,460), (20+bar_w,475), (0,220,255), -1)
            cv2.putText(display, f"Analyzing... {countdown:.1f}s",
                        (20,455), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,220,255), 2)
        else:
            mode_txt = "[DEBUG]" if show_debug else "[CLEAN]"
            cv2.putText(display, f"{mode_txt}  [d] Toggle Debug | [Space] Capture",
                        (20,455), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (180,180,180), 1)

        cv2.circle(display, (620,20), 8,
                   (0,165,255) if processing else (0,255,0), -1)
        emerg_dot_color = (0, 0, 255) if emerg_now else (100, 100, 100)
        cv2.circle(display, (600, 20), 8, emerg_dot_color, -1)
        cv2.putText(display, "E", (594, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255,255,255), 1)

        # GPIO OUTPUT STATUS
        _cur_out_state = (
            lamp_green.is_active, lamp_red.is_active, lamp_blue.is_active,
            bool(is_running), emerg_now
        )
        if _cur_out_state != _last_out_state:
            _last_out_state = _cur_out_state
            g_on, r_on, b_on, run_on, emg_on = _cur_out_state
            print(
                f"\n[PI OUTPUTS] "
                f"GPIO23-GREEN:{'ON ' if g_on  else 'OFF'}  "
                f"GPIO24-RED:{'ON ' if r_on  else 'OFF'}  "
                f"GPIO25-BLUE:{'ON ' if b_on  else 'OFF'}  "
                f"RUNNING:{'ON ' if run_on else 'OFF'}  "
                f"EMERGENCY:{'ON ' if emg_on else 'OFF'}"
            )

        with stream_lock:
            last_captured_frame = display.copy()

        cv2.imshow('Live Camera', display)

        if show_debug and dbg_grid is not None:
            cv2.imshow('Light Analysis Debug', dbg_grid)
            debug_open = True
        elif not show_debug and debug_open:
            try: cv2.destroyWindow('Light Analysis Debug')
            except: pass
            debug_open = False

        # เธ•เธฃเธงเธเธงเนเธฒ analysis เน€เธชเธฃเนเธ (manual / compat เน€เธ”เธดเธก)
        just_finished  = False
        xcap_meta_done = None
        with state.lock:
            if state.analysis_done_flag:
                just_finished            = True
                state.analysis_done_flag = False
                final_st                 = current_station
                xcap_meta_done           = state.xcap_meta
                state.xcap_meta          = None

        if just_finished:
            with multi_peaks_lock:
                peaks_now = list(multi_peaks_cache)
            if xcap_meta_done:
                send_result_for_xcap(peaks_now, xcap_meta_done)
            else:
                with capture_round_lock:
                    rnd_now = capture_round
                send_result_for_round(peaks_now, final_st, rnd_now)

        # Keyboard & Auto Trigger
        key        = cv2.waitKey(1) & 0xFF
        do_capture = False

        if auto_capture_trigger:
            do_capture           = True
            auto_capture_trigger = False
            print("\n๐“ธ [CAMERA] Auto capture triggered...")
        elif key == ord(' '):
            do_capture = True
            print("\n๐“ธ [CAMERA] Manual capture triggered...")

        if   key in [ord('1'), ord('2'), ord('3')]: current_station = chr(key)
        elif key == ord('d'): show_debug = not show_debug
        elif key == ord('r'):
            with capture_round_lock: capture_round = 0
            print("๐” Round reset to 1st (100%)")
        elif key == ord('q'): break

        if do_capture:
            with emergency_lock:
                emerg = emergency_active
            if emerg:
                print("๐จ [CAMERA] Capture blocked โ€” Emergency active!")
            else:
                snap_img_pre = img_live.copy()
                filtered_df  = spatial.process(raw_df)
                filtered_df  = temporal.process(filtered_df)
                snap_depth   = np.asanyarray(filtered_df.get_data()).astype(np.float32)

                def get_latest_frame():
                    with state.lock:
                        f = state.latest_img
                    return f.copy() if f is not None else snap_img_pre.copy()

                danger, danger_classes, annotated_img = yolo_check_with_delay(get_latest_frame)

                if danger:
                    class_str = ", ".join(danger_classes) if danger_classes else "unknown"
                    print(f"๐จ DANGER DETECTED! Classes: [{class_str}] โ€” Canceling payload")
                    payload = json.dumps({
                        "TARGET_E1": -1,
                        "STATION":   int(current_station),
                        "DANGER_CLASSES": danger_classes
                    })
                    sock.sendto((payload+"\n").encode(), (NOTEBOOK_IP, NOTEBOOK_PORT))
                    with stream_lock: last_captured_frame = annotated_img.copy()
                else:
                    snap_img = get_latest_frame()
                    with state.lock:
                        state.snap_img           = snap_img
                        state.snap_depth         = snap_depth
                        state.frozen             = True
                        state.do_analysis        = True
                        state.analysis_until     = time.time() + ANALYSIS_SECONDS
                        state.peak_history.clear()
                        state.analysis_done_flag = False
                        state.xcap_meta          = None
                    print(
                        f"โ… Safe! Image captured after YOLO check, "
                        f"starting analysis for {ANALYSIS_SECONDS}s "
                        f"[Round: {CAPTURE_ROUND_LABELS[capture_round]}]"
                    )

finally:
    stop_event.set()
    pipeline.stop()
    cv2.destroyAllWindows()


