📋 Manual_Software.md
markdown# 💻 คู่มือการลงโปรแกรมและการตั้งค่าระบบ

---

## ข้อกำหนดของระบบ (System Requirements)

ก่อนเริ่มต้นการติดตั้ง ตรวจสอบว่าอุปกรณ์ทุกชิ้นมีคุณสมบัติตามข้อกำหนดขั้นต่ำดังต่อไปนี้

### ตารางที่ 1 ข้อกำหนดคุณสมบัติของอุปกรณ์ (Hardware Requirements)

| อุปกรณ์ | ข้อกำหนดขั้นต่ำ | ที่แนะนำ | หมายเหตุ |
|---|---|---|---|
| PC / Notebook | Core i5 / Ryzen 5, RAM 8 GB | Core i7 / Ryzen 7, RAM 16 GB | สำหรับรัน ROS2 + Gazebo |
| Raspberry Pi 5 | RAM 4 GB, microSD 32 GB | RAM 8 GB, microSD 64 GB (A2) | Ubuntu 22.04 LTS (64-bit) |
| GPU (optional) | — | NVIDIA GTX 1060 ขึ้นไป | เพิ่มความเร็ว YOLO inference |
| Network | Wi-Fi หรือ LAN | Gigabit LAN (สาย) | Latency < 10 ms แนะนำ |
| Storage (PC) | พื้นที่ว่าง 20 GB | SSD 50 GB ขึ้นไป | WSL2 + ROS2 + Dataset |

---

## Software ที่ต้องการทั้งหมด

### ตารางที่ 2 รายการ Software

| โปรแกรม / Package | Version | ติดตั้งบน | หมายเหตุ |
|---|---|---|---|
| Windows 10/11 | 64-bit | PC | เปิดใช้งาน Virtualization ใน BIOS |
| WSL2 (Ubuntu 22.04) | 22.04 LTS | PC | รัน ROS2 ใน Windows |
| ROS2 Humble | Humble Hawksbill | WSL2 | เวอร์ชัน LTS รองรับถึงปี 2027 |
| Gazebo Classic | 11.x | WSL2 | Simulation ของเครน |
| Python | 3.10+ | PC + Pi | ต้องตรงกันทั้งสองฝั่ง |
| ultralytics (YOLO) | 8.x | PC + Pi | Object detection |
| pyrealsense2 | 2.x | Pi | Intel RealSense SDK |
| OpenCV | 4.x | PC + Pi | Image processing |
| onnxruntime | 1.x | Pi | รัน ONNX model |
| Flask | 3.x | Pi | Video stream server |
| gpiozero | 2.x | Pi | GPIO control |
| pyserial | 3.x | Pi | Serial comm กับ STM32 |
| rosbridge-suite | Humble | WSL2 | WebSocket bridge |

---

## ส่วนที่ 1 — การตั้งค่า PC (Windows + WSL2)

### 1.1 เปิดใช้งาน WSL2

เปิด PowerShell ในฐานะ Administrator แล้วรันคำสั่งต่อไปนี้

```powershell
wsl --install -d Ubuntu-22.04
```

รีสตาร์ทเครื่อง จากนั้นตั้งค่า username และ password สำหรับ Ubuntu

ตรวจสอบเวอร์ชัน WSL ที่ติดตั้ง

```powershell
wsl --list --verbose
```

ผลลัพธ์ที่ต้องการ
NAME            STATE           VERSION

Ubuntu-22.04    Running         2


---

### 1.2 ติดตั้ง ROS2 Humble ใน WSL2

เปิด Ubuntu 22.04 Terminal แล้วรันตามลำดับ

**เพิ่ม ROS2 apt repository**

```bash
sudo apt update && sudo apt install -y curl gnupg lsb-release

sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) \
  signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
  http://packages.ros.org/ros2/ubuntu \
  $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
```

**ติดตั้ง ROS2 Humble Desktop**

```bash
sudo apt update
sudo apt install -y ros-humble-desktop
```

**เพิ่ม source ใน .bashrc (ทำครั้งเดียว)**

```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

---

### 1.3 ติดตั้ง Gazebo และ ROS2 Packages ที่จำเป็น

```bash
sudo apt install -y \
  ros-humble-gazebo-ros-pkgs \
  ros-humble-gazebo-ros2-control \
  ros-humble-joint-state-publisher-gui \
  ros-humble-robot-state-publisher \
  ros-humble-ros2-control \
  ros-humble-ros2-controllers \
  ros-humble-rosbridge-server \
  ros-humble-xacro
```

---

### 1.4 ติดตั้ง Python Packages บน PC / WSL2

```bash
pip install ultralytics opencv-python numpy
```

---

### 1.5 ตั้งค่า Workspace ROS2

```bash
mkdir -p ~/dev_ws/ros2_ws/src
cd ~/dev_ws/ros2_ws
colcon build
source install/setup.bash
```

**เพิ่ม workspace ใน .bashrc**

```bash
echo "source ~/dev_ws/ros2_ws/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

---

### 1.6 คัดลอกไฟล์โปรเจกต์

วาง folder `crane_motor` ไว้ใน path ดังนี้
~/dev_ws/ros2_ws/src/crane_motor/
├── urdf/
│   └── cranemotor.urdf
├── scripts/
│   ├── mainROS.py
│   └── simROS.py
└── ...

Build workspace อีกครั้ง

```bash
cd ~/dev_ws/ros2_ws
colcon build
source install/setup.bash
```

---

### 1.7 ตั้งค่า WSL2 IP (สำหรับ UDP Bridge)

ตรวจสอบ IP ของ WSL2

```bash
ip addr show eth0 | grep "inet "
```

บันทึก IP ที่ได้ (เช่น `172.29.199.88`) ไปใส่ในไฟล์ `udp_bridge1.py` บรรทัด

```python
WSL_IP = "172.29.199.88"   # ← แก้ให้ตรงกับ WSL2 IP จริง
```

> **หมายเหตุ:** IP ของ WSL2 จะเปลี่ยนทุกครั้งที่รีสตาร์ท Windows ให้ตรวจสอบใหม่ทุกครั้ง

---

## ส่วนที่ 2 — การตั้งค่า Raspberry Pi 5

### 2.1 ติดตั้ง OS

ใช้ **Raspberry Pi Imager** flash microSD card ด้วย **Ubuntu 22.04 LTS (64-bit)** หรือ **Raspberry Pi OS (64-bit)**

---

### 2.2 ตั้งค่า Network

กำหนด Static IP ให้ Pi เป็น `10.0.0.2` และ PC เป็น `10.0.0.1` โดยใช้สาย LAN เชื่อมตรงระหว่างกัน (Direct Connection)

แก้ไขไฟล์ `/etc/dhcpcd.conf`

```bash
sudo nano /etc/dhcpcd.conf
```

เพิ่มบรรทัดต่อไปนี้ที่ท้ายไฟล์
interface eth0
static ip_address=10.0.0.2/24
static routers=10.0.0.1
static domain_name_servers=8.8.8.8

---

### 2.3 ติดตั้ง Python Packages บน Pi

```bash
pip install \
  pyrealsense2 \
  opencv-python \
  ultralytics \
  onnxruntime \
  numpy \
  flask \
  gpiozero \
  pyserial \
  --break-system-packages
```

---

### 2.4 ติดตั้ง Intel RealSense SDK (librealsense)

```bash
sudo apt-key adv --keyserver keyserver.ubuntu.com \
  --recv-key F6E65AC044F831AC80A06380C8B3A55A6F3EFCDE

sudo add-apt-repository "deb https://librealsense.intel.com/Debian/apt-repo \
  $(lsb_release -cs) main" -u

sudo apt install -y librealsense2-dkms librealsense2-utils \
  librealsense2-dev librealsense2-dbg
```

ทดสอบกล้อง

```bash
realsense-viewer
```

---

### 2.5 วางไฟล์โปรแกรมบน Pi
~/dev_ws/
├── mainPI.py
├── simPI.py
└── Model_Fix.onnx

ตรวจสอบว่าไฟล์ `Model_Fix.onnx` อยู่ใน path เดียวกับ `mainPI.py`

---

### 2.6 ตั้งค่า Serial Port สำหรับ STM32

ตรวจสอบ port ที่ STM32 เชื่อมต่ออยู่

```bash
ls /dev/ttyUSB*
```

ถ้าเห็น `/dev/ttyUSB0` แสดงว่าพร้อมใช้งาน

เพิ่มสิทธิ์ให้ user เข้าถึง serial port (ทำครั้งเดียว)

```bash
sudo usermod -a -G dialout $USER
```

ค่า Serial ในโปรแกรม `mainPI.py`

```python
SERIAL_PORT = '/dev/ttyUSB0'
SERIAL_BAUD = 115200
```

---

## ส่วนที่ 3 — การตั้งค่า STM32

### 3.1 ติดตั้ง Arduino IDE / PlatformIO

ดาวน์โหลด Arduino IDE จาก [https://www.arduino.cc/en/software](https://www.arduino.cc/en/software)

ติดตั้ง Board Support สำหรับ STM32

ใน Arduino IDE ไปที่ `File → Preferences → Additional boards manager URLs` แล้วเพิ่ม
https://github.com/stm32duino/BoardManagerFiles/raw/main/package_stmicroelectronics_index.json

จากนั้นไปที่ `Tools → Board → Boards Manager` และค้นหา `STM32` แล้วติดตั้ง

---

### 3.2 ตั้งค่า Board
Board       : Generic STM32F1 series (หรือตามรุ่นที่ใช้)
Upload Method: STLink

---

### 3.3 Upload โปรแกรม

เปิดไฟล์ `stm32.ino` แล้วกด Upload

ตรวจสอบ Serial Monitor ที่ `115200 baud` ควรเห็นข้อความ
READY

---

## ส่วนที่ 4 — การตั้งค่า udp_bridge1.py (Windows)

ไฟล์ `udp_bridge1.py` รันบน Windows (CMD ธรรมดา ไม่ใช่ WSL2)

แก้ไข IP ให้ตรงกับระบบ

```python
LISTEN_IP = "0.0.0.0"
WSL_IP    = "172.29.199.88"   # ← IP ของ WSL2 (ตรวจสอบด้วย ip addr)
```

ตรวจสอบว่า Python ติดตั้งบน Windows แล้ว

```powershell
python --version
```

---

## ส่วนที่ 5 — การตรวจสอบระบบก่อนใช้งาน

### Checklist ก่อนเปิดระบบ

| รายการ | วิธีตรวจสอบ | ผลที่ต้องการ |
|---|---|---|
| STM32 เชื่อมต่อ Pi | `ls /dev/ttyUSB0` | มี `/dev/ttyUSB0` |
| RealSense เชื่อมต่อ | `realsense-viewer` | กล้องแสดงภาพได้ |
| Pi → PC ping ได้ | `ping 10.0.0.1` | reply ต่อเนื่อง |
| PC → Pi ping ได้ | `ping 10.0.0.2` | reply ต่อเนื่อง |
| WSL2 IP ถูกต้อง | `ip addr show eth0` | ตรงกับ `WSL_IP` ในไฟล์ bridge |
| ROS2 พร้อมใช้ | `ros2 topic list` | แสดง topic list ได้ |
| Model_Fix.onnx อยู่ใน path | `ls ~/dev_ws/Model_Fix.onnx` | พบไฟล์ |

---

## ส่วนที่ 6 — ขั้นตอนเปิดระบบ (Quick Start)

เปิดตามลำดับดังนี้

**ขั้นที่ 1** — เปิด UDP Bridge (Windows CMD)

```bash
cd Desktop
python udp_bridge1.py
```

**ขั้นที่ 2** — เปิด ROSBridge (WSL2 / Ubuntu)

```bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

**ขั้นที่ 3** — เปิด Gazebo (WSL2 / Ubuntu)

```bash
source /opt/ros/humble/setup.bash
gazebo --verbose \
  -s libgazebo_ros_init.so \
  -s libgazebo_ros_factory.so
```

**ขั้นที่ 4** — โหลด URDF Model (WSL2 / Ubuntu)

```bash
source /opt/ros/humble/setup.bash
ros2 run robot_state_publisher robot_state_publisher \
  ~/dev_ws/ros2_ws/src/crane_motor/urdf/cranemotor.urdf
```

**ขั้นที่ 5** — Spawn Model เข้า Gazebo (WSL2 / Ubuntu)

```bash
source /opt/ros/humble/setup.bash
ros2 run gazebo_ros spawn_entity.py -entity crane_motor -topic robot_description
```

**ขั้นที่ 6** — โหลด Joint Controllers (WSL2 / Ubuntu)

```bash
source /opt/ros/humble/setup.bash
ros2 control load_controller --set-state active joint_state_broadcaster
ros2 control load_controller --set-state active arm_group_controller
```

**ขั้นที่ 7** — เปิด Main Program ROS (WSL2 / Ubuntu)

```bash
python3 ~/dev_ws/ros2_ws/src/crane_motor/scripts/mainROS.py
```

**ขั้นที่ 8** — เปิด Main Program Pi (Raspberry Pi 5)

```bash
cd ~/dev_ws
python3 mainPI.py
```

---

## ส่วนที่ 7 — การแก้ปัญหาเบื้องต้น (Troubleshooting)

| ปัญหา | สาเหตุที่พบบ่อย | วิธีแก้ไข |
|---|---|---|
| `No module named 'pyrealsense2'` | ยังไม่ได้ติดตั้ง SDK | รัน `pip install pyrealsense2 --break-system-packages` |
| STM32 ไม่ตอบสนอง | Serial port ผิด | ตรวจสอบด้วย `ls /dev/ttyUSB*` |
| UDP ไม่ส่งข้อมูล | WSL2 IP เปลี่ยน | ตรวจสอบ IP ใหม่ด้วย `ip addr` |
| Gazebo ไม่แสดงโมเดล | source setup.bash ยังไม่ได้รัน | รัน `source /opt/ros/humble/setup.bash` |
| YOLO ไม่พบ model | ไม่มีไฟล์ `yolov8n.pt` | ultralytics จะ download อัตโนมัติครั้งแรก |
| `ONNX model not found` | ไม่มีไฟล์ `Model_Fix.onnx` | วางไฟล์ใน `~/dev_ws/` |
| Pi ไม่สามารถ ping PC ได้ | IP ไม่ตรงหรือ Firewall | ตรวจสอบ Static IP และปิด Firewall ชั่วคราว |
| GPIO permission denied | ยังไม่ได้เพิ่ม group | รัน `sudo usermod -a -G gpio $USER` แล้ว logout/login |


📋 Manual_User.md
markdown# 📖 คู่มือการใช้งานระบบเครนอัตโนมัติ

---

## ภาพรวมระบบ

ระบบเครนอัตโนมัติ Crane AI ทำงานโดยใช้กล้อง Intel RealSense D435i ตรวจจับตำแหน่งกองทราย
แล้วควบคุมเครนให้เคลื่อนที่และตักทรายใส่ช่องปลายทางโดยอัตโนมัติ ผ่านการสั่งงานจากหน้าเว็บ

### โครงสร้างการทำงาน
หน้าเว็บ Dashboard
↕ คำสั่ง / สถานะ
ROS2 (mainROS.py)  ←→  Gazebo (Digital Twin)
↕ UDP
Raspberry Pi 5 (mainPI.py)
↕ Serial
STM32 → มอเตอร์ / วาล์ว / เซนเซอร์

---

## อุปกรณ์ควบคุมบน Raspberry Pi 5

| GPIO | อุปกรณ์ | หน้าที่ |
|---|---|---|
| GPIO17 | ปุ่ม START | เริ่มการทำงาน |
| GPIO27 | ปุ่ม STOP | หยุดการทำงานทันที |
| GPIO22 | Pressure Sensor | ต้องกดค้างตลอดการทำงาน |
| GPIO16 | Emergency Switch | หยุดฉุกเฉิน |
| GPIO23 | ไฟ LED เขียว | ระบบทำงานอยู่ |
| GPIO24 | ไฟ LED แดง | ระบบหยุด / พร้อมใช้งาน |
| GPIO25 | ไฟ LED น้ำเงิน | Pressure Sensor กด |

---

## สถานะไฟ LED

| ไฟ LED | สถานะ | ความหมาย |
|---|---|---|
| 🔴 แดง ติดค้าง | ระบบพร้อม รอ START | ปกติ รอคำสั่ง |
| 🟢 เขียว ติดค้าง | ระบบกำลังทำงาน | เครนกำลังเคลื่อนที่ |
| 🔵 น้ำเงิน ติดค้าง | Pressure กด | GPIO22 active |
| 🔴 แดง กะพริบ | Emergency! | GPIO16 ถูกกด หรือสัญญาณหาย |

---

## การใช้งานผ่านหน้าเว็บ Dashboard

### เปิดหน้า Dashboard

เปิดเบราว์เซอร์แล้วไปที่ IP ของ PC ที่รัน ROSBridge พร้อม port 9090
http://10.0.0.1:9090

---

### ปุ่มควบคุมหลัก

| ปุ่ม / คำสั่ง | ความหมาย |
|---|---|
| **READY** | รีเซ็ตสถานะ เตรียมพร้อมรับคำสั่งใหม่ |
| **START (Pi)** | กดปุ่ม GPIO17 บน Pi หรือส่งคำสั่ง START |
| **STOP** | หยุดการทำงานทุกอย่างทันที |
| **HOME (h)** | สั่ง Homing — เครนวิ่งกลับจุดเริ่มต้น |
| **Cycle 1 (c1)** | ทำงานอัตโนมัติช่องที่ 1 |
| **Cycle 2 (c2)** | ทำงานอัตโนมัติช่องที่ 2 |
| **Cycle 3 (c3)** | ทำงานอัตโนมัติช่องที่ 3 |
| **Auto Process (x)** | ทำงานอัตโนมัติทุกช่องเรียงลำดับ (1→2→3) |
| **Manual (m xx)** | ขยับเครนไปตำแหน่ง E1 ที่ระบุ เช่น `m25` |

---

## ขั้นตอนการทำงานปกติ

### การเริ่มต้นระบบ

1. ตรวจสอบว่าเปิดโปรแกรมทุกตัวครบตามลำดับใน Manual_Software แล้ว
2. กด **Pressure Sensor** (GPIO22) ค้างไว้ หรือยึดให้อยู่ในตำแหน่ง
3. ไฟ **น้ำเงิน** จะติด แสดงว่า Pressure พร้อม
4. กดปุ่ม **START** บน Pi (GPIO17) หรือกด START จากหน้าเว็บ
5. ไฟ **เขียว** ติด / ไฟ **แดง** ดับ — ระบบพร้อมทำงาน

### การสั่ง Auto Process

1. กด **READY** เพื่อเคลียร์สถานะเก่า
2. กด **Auto Process (x)** — ระบบจะ:
   - Homing ก่อนเสมอ
   - วิ่งไปยังช่อง 1, 2, 3 ตามลำดับ
   - สแกนหาตำแหน่ง peak ด้วยกล้อง
   - ตักทรายจนช่องเต็ม (Photo Sensor = 1)
   - สรุปผลและแสดงบนหน้าเว็บ

### การสั่ง Cycle เดี่ยว

1. กด **READY**
2. กด **Cycle 1** (หรือ 2 หรือ 3)
3. ระบบจะทำงานเฉพาะช่องนั้นจนเต็มแล้วหยุด

---

## ระบบความปลอดภัย

### Emergency Stop

กดปุ่ม Emergency (GPIO16) หรือสัญญาณ GPIO16 หาย → ระบบหยุดทันที

- ไฟ **แดง กะพริบ**
- วาล์วและมอเตอร์ทุกตัวปิดหมด
- ต้องปล่อย GPIO16 ก่อน จึงจะ START ใหม่ได้

### Pressure Sensor (GPIO22)

- ต้องกด Pressure Sensor ค้างไว้ตลอดการทำงาน
- ถ้าปล่อยระหว่างที่ระบบทำงาน → **AUTO STOP ทันที**
- ต้อง START ใหม่

### YOLO Safety

- กล้องตรวจจับคนหรือสิ่งกีดขวางตลอดเวลา
- ถ้าพบ → ระบบ **หยุด + รอ 3 วินาที** หลังพื้นที่ปลอดภัยแล้วค่อย resume
- ถ้าพบสิ่งกีดขวางนาน **เกิน 120 วินาที** → Emergency Stop อัตโนมัติ

---

## Encoder และตำแหน่งเครน

| ค่า E1 | ตำแหน่ง |
|---|---|
| 0 | LS1 (Limit Switch ซ้าย — จุด Home) |
| 7 | ช่องที่ 1 (กึ่งกลาง) |
| 32 | ช่องที่ 2 (กึ่งกลาง) |
| 54 | ช่องที่ 3 (กึ่งกลาง) |
| 61 | ขอบขวาสุด |

> **หมายเหตุ:** ค่า E1 สามารถเปลี่ยนได้ใน `mainROS.py` บรรทัด `SLOT_TARGETS`

---

## Photo Sensor — ตรวจสอบช่องเต็ม

| Sensor | ตรวจสอบ |
|---|---|
| P1 | ช่องที่ 1 เต็ม |
| P2 | ช่องที่ 2 เต็ม |
| P3 | ช่องที่ 3 เต็ม |
| P4 | แขนเครนอยู่ตำแหน่งบนสุด |

Photo Sensor จะยืนยันสถานะหลังจากสัญญาณค้าง **2 วินาที** จึงจะนับว่าเต็ม

---

## Capture Round — การตักทรายหลายรอบ

ระบบตักทรายแต่ละช่อง 3 รอบ โดยเลือก peak ต่างระดับ

| รอบ | % Peak | ความหมาย |
|---|---|---|
| 1st | 100% | ตักจุดสูงสุด (กองใหญ่) |
| 2nd | 65% | ตักจุดความสูง 65% |
| 3rd | 50% | ตักจุดความสูง 50% (กองที่เหลือ) |

---

## การใช้งาน Manual Mode

สำหรับการทดสอบหรือปรับตำแหน่งด้วยตนเอง

**ขั้นตอน**

1. กด **READY**
2. พิมพ์คำสั่ง `m` ตามด้วยค่า E1 ที่ต้องการ เช่น `m25`
3. ระบบจะ Homing ก่อน (ครั้งแรก) แล้วขยับไปยังตำแหน่งที่ระบุ
4. ถ้าต้องการ Homing ใหม่ ให้พิมพ์ `reset_manual` ก่อน

---

## การดู Event Log บนหน้าเว็บ

หน้า Dashboard แสดง Event Log แบบ Real-time แบ่งเป็น 2 ฝั่ง

| สี | ประเภท Event | ตัวอย่าง |
|---|---|---|
| 🟢 เขียว | การทำงานปกติ | HOME_OK, SCOOP_OK, AT_POS, SCAN_OK, DELIVER_OK |
| 🔴 แดง | ข้อผิดพลาด / คำเตือน | ERR_EMERGENCY, ERR_P4_TIMEOUT, ERR_STOP, WARN_YOLO |

---

## การหยุดระบบ

### หยุดปกติ

1. รอให้ Cycle ปัจจุบันทำงานเสร็จ
2. กด **STOP** หรือกดปุ่ม STOP บน Pi (GPIO27)
3. ไฟ **แดง** ติด — ระบบพร้อมสั่งใหม่

### หยุดฉุกเฉิน

กดปุ่ม **Emergency** (GPIO16) ทันที — ระบบทุกอย่างหยุดพร้อมกัน

### ปิดโปรแกรมทั้งหมด

กด `Ctrl+C` ในแต่ละ Terminal ตามลำดับย้อนหลัง (8 → 1)

---

## คำถามที่พบบ่อย

**Q: กด START แล้วไม่มีอะไรเกิดขึ้น**
A: ตรวจสอบว่า Pressure Sensor (GPIO22) ถูกกดอยู่ และไม่มี Emergency active (ไฟแดงกะพริบ)

**Q: เครนหมุนแล้วหยุดเองกลางทาง**
A: YOLO ตรวจพบสิ่งกีดขวาง รอ 3 วินาทีหลังพื้นที่โล่ง ระบบจะ resume เอง

**Q: P4 Timeout**
A: แขนเครนไม่ขึ้นถึงตำแหน่งบนภายใน 60 วินาที ตรวจสอบวาล์ว UP และแรงดันไฮดรอลิก

**Q: Serial ไม่เจอ STM32**
A: รัน `ls /dev/ttyUSB*` ถ้าไม่มี ให้ตรวจสาย USB และ driver ของ STM32

**Q: UDP Bridge แจ้ง forward แต่ ROS ไม่ได้รับ**
A: ตรวจสอบ `WSL_IP` ในไฟล์ `udp_bridge1.py` ให้ตรงกับ `ip addr show eth0` ใน WSL2
