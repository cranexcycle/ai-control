import socket
import threading

LISTEN_IP = "0.0.0.0"
WSL_IP = "172.29.199.88"

def bridge_sensor():
    sock_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # เพิ่ม buffer
    sock_in.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4194304)
    sock_out.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4194304)
    
    sock_in.bind((LISTEN_IP, 5000))
    print(f"STEP 1: Listening on Port 5000")
    print(f"STEP 2: Forwarding to WSL2 @ {WSL_IP}:5001")
    print(f"--------------------------------")

    while True:
        try:
            data, addr = sock_in.recvfrom(1024)
            raw_msg = data.decode(errors='ignore').strip()
            print(f"[RECV] from {addr}: {raw_msg}")
            sock_out.sendto(data, (WSL_IP, 5001))
            print(f"  >>> [FORWARDED] to {WSL_IP}:5001")
        except Exception as e:
            print(f"[SENSOR ERROR] {e}")

def bridge_pointcloud():
    sock_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # ✅ เพิ่ม buffer ใหญ่ขึ้น
    sock_in.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8388608)  # 8MB
    sock_out.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 8388608) # 8MB
    
    sock_in.bind((LISTEN_IP, 5002))
    print(f"[POINTCLOUD] Listening Port 5002 → {WSL_IP}:5002")

    while True:
        try:
            data, addr = sock_in.recvfrom(65535)
            sock_out.sendto(data, (WSL_IP, 5002))
        except OSError as e:
            # ✅ ถ้า buffer เต็ม — skip frame นั้นแล้วไปต่อ
            print(f"[SKIP FRAME] buffer full: {e}")
            continue
        except Exception as e:
            print(f"[POINTCLOUD ERROR] {e}")

# --- MAIN ---
print(f"================================")
print(f"   UDP BRIDGE IS NOW ACTIVE")
print(f"================================")

t1 = threading.Thread(target=bridge_sensor, daemon=True)
t2 = threading.Thread(target=bridge_pointcloud, daemon=True)

t1.start()
t2.start()

try:
    threading.Event().wait()
except KeyboardInterrupt:
    print("\nBridge stopped by user.")
