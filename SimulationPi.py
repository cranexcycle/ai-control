import pyrealsense2 as rs
import numpy as np
import socket, struct, zlib
import cv2
import sys
import termios
import tty
import threading

TARGET_IP   = '10.0.0.1'
TARGET_PORT = 5002
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4194304)

pipeline = rs.pipeline()
config   = rs.config()
config.enable_stream(rs.stream.depth, 480, 270, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 424, 240, rs.format.bgr8, 30)
pc    = rs.pointcloud()
align = rs.align(rs.stream.color)
pipeline.start(config)

intr2 = pipeline.get_active_profile().get_stream(rs.stream.color)\
               .as_video_stream_profile().get_intrinsics()
print(f"[PC INTRINSICS] fx={intr2.fx:.4f} fy={intr2.fy:.4f} "
      f"cx={intr2.ppx:.4f} cy={intr2.ppy:.4f}")
print(f"D435i PointCloud (xyzrgbuvd) â†’ {TARGET_IP}:{TARGET_PORT}")

KEEP      = 50000
DEPTH_MIN =   100.0
DEPTH_MAX =  1200.0

IMG_W, IMG_H = 424, 240

# â”€â”€ OFFSET / ROTATE (à¹€à¸«à¸¡à¸·à¸­à¸™à¸à¸±à¸™à¸—à¸¸à¸ station) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
OFFSET_X = -0.557200
OFFSET_Y = -0.441300
OFFSET_Z = -0.124600

ROTATE_X =  80.0
ROTATE_Y = 450.0
ROTATE_Z = 340.0

ax = np.radians(ROTATE_X)
ay = np.radians(ROTATE_Y)
az = np.radians(ROTATE_Z)
Rx = np.array([[1,0,0],[0,np.cos(ax),-np.sin(ax)],[0,np.sin(ax),np.cos(ax)]], dtype=np.float32)
Ry = np.array([[np.cos(ay),0,np.sin(ay)],[0,1,0],[-np.sin(ay),0,np.cos(ay)]], dtype=np.float32)
Rz = np.array([[np.cos(az),-np.sin(az),0],[np.sin(az),np.cos(az),0],[0,0,1]], dtype=np.float32)
R  = Rz @ Ry @ Rx

# â”€â”€ POLYGON à¹à¸•à¹ˆà¸¥à¸° station â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
POLYGONS = {
    '1': np.array([
        (182, 92),(219,218),(352,210),(382, 97),(183, 93),
    ], dtype=np.int32),

    '2': np.array([
        (119,142),(189,227),(353,218),(419,151),
        (416,103),(370, 65),(298, 67),(231, 71),
        (206, 83),(171, 92),(119,142),
    ], dtype=np.int32),

    '3': np.array([
        (151,112),(202,221),(304,223),(326,112),(151,112),
    ], dtype=np.int32),
}

# â”€â”€ State â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
current_station = '2'
station_lock    = threading.Lock()

def _build_mask(poly):
    mask = np.zeros((IMG_H, IMG_W), dtype=np.uint8)
    cv2.fillPoly(mask, [poly], 255)
    return mask

poly_masks = {k: _build_mask(v) for k, v in POLYGONS.items()}

# â”€â”€ Keyboard thread (à¸à¸” 1/2/3 à¸šà¸™ Pi) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def keyboard_loop():
    global current_station
    fd  = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch in ('1', '2', '3'):
                with station_lock:
                    current_station = ch
                print(f"\r[STATION] â†’ ST:{ch}  polygon updated          ", flush=True)
            elif ch in ('q', '\x03'):   # q à¸«à¸£à¸·à¸­ Ctrl+C
                print("\r[EXIT]", flush=True)
                import os; os.kill(os.getpid(), 2)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

threading.Thread(target=keyboard_loop, daemon=True).start()

print("=" * 50)
print("à¸à¸” 1 / 2 / 3  à¹€à¸žà¸·à¹ˆà¸­à¹€à¸›à¸¥à¸µà¹ˆà¸¢à¸™ station")
print(f"Station à¹€à¸£à¸´à¹ˆà¸¡à¸•à¹‰à¸™: {current_station}")
print("à¸à¸” q à¸«à¸£à¸·à¸­ Ctrl+C à¹€à¸žà¸·à¹ˆà¸­à¸­à¸­à¸")
print("=" * 50)

frame_count = 0

try:
    while True:
        frames = pipeline.wait_for_frames()
        frame_count += 1
        aligned     = align.process(frames)
        depth_frame = aligned.get_depth_frame()
        color_frame = aligned.get_color_frame()
        if not depth_frame or not color_frame:
            continue

        # snapshot station
        with station_lock:
            st = current_station

        poly      = POLYGONS[st]
        poly_mask = poly_masks[st]

        color_img = np.asanyarray(color_frame.get_data())

        display = color_img.copy()
        cv2.polylines(display, [poly], True, (0, 255, 0), 2)
        cv2.putText(display, f"ST:{st}  frame:{frame_count}  [1/2/3]=switch  [q]=quit",
                    (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        cv2.imshow("D435i - Scan Area", display)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        pc.map_to(color_frame)
        points  = pc.calculate(depth_frame)
        vtx     = np.asanyarray(points.get_vertices())
        xyz     = vtx.view(np.float32).reshape(-1, 3)

        tex     = np.asanyarray(points.get_texture_coordinates())
        tex_uv  = tex.view(np.float32).reshape(-1, 2)
        u_px    = np.clip((tex_uv[:, 0] * IMG_W).astype(np.int32), 0, IMG_W - 1)
        v_px    = np.clip((tex_uv[:, 1] * IMG_H).astype(np.int32), 0, IMG_H - 1)
        in_poly = poly_mask[v_px, u_px] > 0

        colors       = color_img.reshape(-1, 3).astype(np.float32) / 255.0
        depth_mm_all = (xyz[:, 2] * 1000.0).astype(np.float32)

        depth_ok = (depth_mm_all >= DEPTH_MIN) & (depth_mm_all <= DEPTH_MAX)
        mask     = depth_ok & in_poly

        xyz      = xyz[mask]
        colors   = colors[mask]
        u_keep   = u_px[mask].astype(np.float32)
        v_keep   = v_px[mask].astype(np.float32)
        depth_mm = depth_mm_all[mask]

        # transform
        xyz[:, 2] = -xyz[:, 2]
        xyz[:, 0] = -xyz[:, 0]
        xyz        = (R @ xyz.T).T
        xyz[:, 0] += OFFSET_X
        xyz[:, 1] += OFFSET_Y
        xyz[:, 2] += OFFSET_Z

        # downsample
        if len(xyz) > KEEP:
            idx      = np.random.choice(len(xyz), KEEP, replace=False)
            xyz      = xyz[idx]
            colors   = colors[idx]
            u_keep   = u_keep[idx]
            v_keep   = v_keep[idx]
            depth_mm = depth_mm[idx]

        n = len(xyz)

        # 9 cols: (x,y,z, r,g,b, u,v, depth_mm)
        xyzrgbuvd = np.hstack([
            xyz,
            colors,
            u_keep.reshape(-1, 1),
            v_keep.reshape(-1, 1),
            depth_mm.reshape(-1, 1),
        ]).astype(np.float32)

        compressed = zlib.compress(xyzrgbuvd.tobytes(), level=1)
        header     = struct.pack('II', n, len(compressed))
        payload    = header + compressed

        CHUNK  = 60000
        chunks = [payload[i:i+CHUNK] for i in range(0, len(payload), CHUNK)]
        fid    = frame_count % 65536
        for i, chunk in enumerate(chunks):
            prefix = struct.pack('BBH', i, len(chunks), fid)
            sock.sendto(prefix + chunk, (TARGET_IP, TARGET_PORT))

        if frame_count % 30 == 0:
            print(f"[OK] ST:{st}  frame:{frame_count}  pts:{n}  "
                  f"{len(compressed)//1024}KB", flush=True)

except KeyboardInterrupt:
    print("\nâœ… à¸«à¸¢à¸¸à¸”à¹à¸¥à¹‰à¸§")
finally:
    pipeline.stop()
    sock.close()
    cv2.destroyAllWindows()


