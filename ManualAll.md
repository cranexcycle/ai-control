# CraneAI Extreme — คู่มือระบบฉบับสมบูรณ์

**ROS2 Humble | Gazebo | YOLOv8 | ONNX | RealSense D435 | Raspberry Pi 5 | STM32F103**

---

## ข้อมูลเวอร์ชันและส่วนประกอบระบบ

| รายการ | ค่า |
|---|---|
| ROS2 | Humble (Ubuntu 22.04 LTS) |
| Simulator | Gazebo Classic (gazebo_ros2_control) |
| โมเดล AI | YOLOv8n + ONNX Runtime (Model_Fix.onnx) |
| กล้อง | Intel RealSense D435 |
| ตัวควบคุม | Raspberry Pi 5 (RAM 8GB) |
| เฟิร์มแวร์ | STM32F103C8T6 (Arduino) |
| เว็บ Frontend | Node.js v18+ + rosbridge WebSocket |
| ข้อต่อ URDF | headcrane_Link (revolute) + armcrane_Link (prismatic) |
| ซอฟต์แวร์ CAD | SolidWorks + sw2urdf exporter |

---

## 1. ภาพรวมระบบ (System Overview)

ระบบ CraneAI Extreme เป็นระบบควบคุมเครนอัตโนมัติที่ผสานการทำงานของ ROS2, Gazebo Simulator, AI (YOLOv8 + ONNX), กล้อง Intel RealSense D435 และฮาร์ดแวร์จริง (Raspberry Pi 5 + STM32F103) เข้าด้วยกัน รองรับโหมดการทำงาน Full-Auto, Semi-Auto และ Manual ผ่าน Web Dashboard หรือ CLI

ระบบทำงานโดยใช้กล้องตรวจจับตำแหน่งกองทราย แล้วควบคุมเครนให้เคลื่อนที่และตักทรายใส่ช่องปลายทางโดยอัตโนมัติ สั่งงานผ่านหน้าเว็บที่เชื่อมต่อผ่าน rosbridge WebSocket

### โครงสร้างการทำงาน

```
หน้าเว็บ Dashboard
       ↕ คำสั่ง / สถานะ
ROS2 (mainROS.py)  ←→  Gazebo (Digital Twin)
       ↕ UDP
Raspberry Pi 5 (mainPI.py)
       ↕ Serial
STM32 → มอเตอร์ / วาล์ว / เซนเซอร์
```

### การไหลของข้อมูล

| ทิศทาง | โปรโตคอล | รายละเอียด |
|---|---|---|
| STM32 → Pi | Serial UART 115200 | ส่ง E1, E2, P1–P4, LS1–LS2 ทุก 20ms |
| Pi → ROS PC | UDP Port 5000 | ส่งสถานะ JSON + ผล Vision (TARGET_E1) |
| ROS PC → Pi | UDP Port 5001 | ส่งคำสั่ง MAG/VALVE/STM32 + XCAP request |
| Pi → STM32 | Serial UART 115200 | ส่งคำสั่ง ARM/START/MAG_ON/VALVE ฯลฯ |
| Web UI → ROS | WebSocket :9090 | ส่งคำสั่ง c1/c2/c3/x/h ผ่าน rosbridge |
| ROS → Gazebo | Topic JointTrajectory | sync กับโมเดลเสมือน |

---

## 2. ข้อกำหนดของระบบ (System Requirements)

### 2.1 PC / Notebook (ROS PC)

| รายการ | ข้อกำหนดขั้นต่ำ | ที่แนะนำ | หมายเหตุ |
|---|---|---|---|
| OS | Windows 10/11 (64-bit) + WSL2 Ubuntu 22.04 LTS | — | เปิดใช้งาน Virtualization ใน BIOS |
| CPU | Intel Core i5 / AMD Ryzen 5 | Core i7 / Ryzen 7 | สำหรับรัน ROS2 + Gazebo |
| RAM | 8 GB | 16 GB | — |
| GPU | (ไม่จำเป็น) | NVIDIA GTX 1060 ขึ้นไป | เพิ่มความเร็ว YOLO inference |
| Storage | พื้นที่ว่าง 20 GB | SSD 50 GB ขึ้นไป | WSL2 + ROS2 + Dataset |
| Network | LAN หรือ Wi-Fi | Gigabit LAN (สาย) | Latency < 10 ms แนะนำ |

### 2.2 Raspberry Pi 5

| รายการ | ขั้นต่ำ | แนะนำ |
|---|---|---|
| RAM | 4 GB | 8 GB |
| microSD | 32 GB | 64 GB (A2) |
| OS | Ubuntu 22.04 LTS (64-bit) หรือ Raspberry Pi OS (64-bit) | — |
| Python | 3.10 ขึ้นไป | — |

### 2.3 ซอฟต์แวร์ที่ต้องใช้ทั้งหมด

| โปรแกรม / Package | Version | ติดตั้งบน | หมายเหตุ |
|---|---|---|---|
| Windows 10/11 | 64-bit | PC | — |
| WSL2 (Ubuntu 22.04) | 22.04 LTS | PC | รัน ROS2 ใน Windows |
| ROS2 Humble | Humble Hawksbill | WSL2 + Pi | เวอร์ชัน LTS รองรับถึงปี 2027 |
| Gazebo Classic | 11.x | WSL2 | Simulation ของเครน |
| Python | 3.10+ | PC + Pi | ต้องตรงกันทั้งสองฝั่ง |
| Node.js | v18+ | Ubuntu (WSL2) | สำหรับ Web Frontend |
| ultralytics (YOLO) | 8.x | PC + Pi | Object detection |
| pyrealsense2 | 2.x | Pi | Intel RealSense SDK |
| OpenCV | 4.x | PC + Pi | Image processing |
| onnxruntime | 1.x | Pi | รัน ONNX model |
| Flask | 3.x | Pi | Video stream server |
| gpiozero | 2.x | Pi | GPIO control |
| pyserial | 3.x | Pi | Serial comm กับ STM32 |
| rosbridge-suite | Humble | WSL2 | WebSocket bridge |
| Radmin VPN | — | Windows | สำหรับผ่านอินเทอร์เน็ต (ถ้าไม่มี LAN) |
| Git | — | Ubuntu (WSL2) + Pi | `sudo apt install git` |

---

## 3. ขั้นตอนการติดตั้ง

> ⚠️ **รีสตาร์ท Windows 1 ครั้งในส่วน WSL2 — บันทึกงานทั้งหมดก่อนเริ่ม**

### 3.1 ติดตั้ง WSL2 + Ubuntu 22.04 บน Windows

เปิด PowerShell ในฐานะ Administrator แล้วรันคำสั่งต่อไปนี้

```powershell
# คลิกขวา Start Menu → Windows PowerShell (Admin)
wsl --install
wsl --set-default-version 2

# รีสตาร์ท Windows จากนั้นเปิด PowerShell ใหม่
wsl --install -d Ubuntu-22.04

# ตรวจสอบ
wsl --list --verbose
# ผลที่ต้องได้: Ubuntu-22.04 Running 2
```

หลังจากติดตั้งเสร็จ Ubuntu จะขอให้ตั้ง username/password จากนั้นรัน

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl gnupg2 lsb-release build-essential git
```

สำหรับ Python บน Windows (สำหรับ `udp_bridge.py`) ให้ดาวน์โหลดจาก https://python.org/downloads และติ๊ก **"Add Python to PATH"** ระหว่างติดตั้ง จากนั้นตรวจสอบ

```cmd
python --version
```

---

### 3.2 ติดตั้ง ROS2 Humble (Ubuntu 22.04 / WSL2)

> 📌 ดำเนินการใน **Ubuntu Terminal (WSL2)** — เปิดโดยพิมพ์ `Ubuntu` ใน Windows Search

ตั้งค่า Locale ก่อน

```bash
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
```

เพิ่ม ROS2 apt repository

```bash
sudo apt update && sudo apt install -y curl gnupg lsb-release

sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) \
  signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
  http://packages.ros.org/ros2/ubuntu \
  $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

sudo apt update
```

ติดตั้ง ROS2 Humble Desktop

```bash
sudo apt install -y ros-humble-desktop-full

# เพิ่ม source ใน .bashrc (ทำครั้งเดียว)
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc

# ตรวจสอบ
ros2 --version   # ผลที่ต้องได้: ros2 distro: humble
```

ติดตั้ง Gazebo และแพ็คเกจ ROS2 ที่จำเป็น

```bash
sudo apt install -y \
  ros-humble-gazebo-ros-pkgs \
  ros-humble-gazebo-ros2-control \
  ros-humble-joint-trajectory-controller \
  ros-humble-joint-state-broadcaster \
  ros-humble-controller-manager \
  ros-humble-robot-state-publisher \
  ros-humble-joint-state-publisher-gui \
  ros-humble-rviz2 \
  ros-humble-rosbridge-suite \
  ros-humble-xacro
```

ติดตั้ง Python Libraries สำหรับ Ubuntu WSL2

```bash
pip install ultralytics opencv-python numpy
pip install flask onnxruntime

# ตรวจสอบ ONNX
python3 -c "import onnxruntime; print(onnxruntime.__version__)"
```

---

### 3.3 สร้าง ROS2 Workspace และ Copy โปรแกรม

สร้าง Workspace

```bash
mkdir -p ~/dev_ws/ros2_ws/src
cd ~/dev_ws/ros2_ws
colcon build --symlink-install
source install/setup.bash
echo "source ~/dev_ws/ros2_ws/install/setup.bash" >> ~/.bashrc
```

คัดลอกโฟลเดอร์ `crane_motor` ไปยัง `~/dev_ws/ros2_ws/src/crane_motor/` โดยโครงสร้างโฟลเดอร์ที่ต้องมีคือ

```
src/crane_motor/
├── scripts/
│   ├── mainROS.py
│   └── teleop_crane_motor.py
├── urdf/
│   └── cranemotor.urdf
├── config/
│   └── controllers.yaml
├── launch/
│   └── display.launch.py
├── CMakeLists.txt
└── package.xml
```

Build แพ็คเกจ

```bash
cd ~/dev_ws/ros2_ws
colcon build --symlink-install
source install/setup.bash

# ตรวจสอบ
ros2 pkg list | grep crane   # ผลที่ต้องได้: crane_motor
```

---

### 3.4 ติดตั้งโปรแกรมบน Raspberry Pi 5

ก่อนอื่นให้ flash microSD card ด้วย **Ubuntu 22.04 LTS (64-bit)** หรือ **Raspberry Pi OS (64-bit)** โดยใช้ Raspberry Pi Imager จากนั้นติดตั้ง ROS2 Humble บน Pi โดยทำขั้นตอนเดียวกับหัวข้อ 3.2 บน Pi Terminal

ติดตั้ง Python Libraries บน Pi

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

# ตรวจสอบ RealSense
python3 -c "import pyrealsense2; print('RealSense OK')"
```

สร้าง Workspace บน Pi โดยไฟล์ที่ต้องมีในโฟลเดอร์ `~/dev_ws/` คือ

```
~/dev_ws/
├── mainPI.py
├── simPI.py
└── Model_Fix.onnx
```

ตั้งค่าสิทธิ์ Serial (ทำครั้งเดียว)

```bash
sudo usermod -aG dialout $USER
sudo reboot

# ตรวจสอบหลัง reboot
ls /dev/ttyUSB*   # ผลที่ต้องได้: /dev/ttyUSB0
```

ติดตั้ง Intel RealSense SDK

```bash
sudo apt-key adv --keyserver keyserver.ubuntu.com \
  --recv-key F6E65AC044F831AC80A06380C8B3A55A6F3EFCDE

sudo add-apt-repository "deb https://librealsense.intel.com/Debian/apt-repo \
  $(lsb_release -cs) main" -u

sudo apt install -y librealsense2-dkms librealsense2-utils \
  librealsense2-dev librealsense2-dbg

# ตรวจสอบ (เสียบกล้องก่อน)
realsense-viewer
```

คัดลอก `Model_Fix.onnx` ไปยัง Pi (เลือกวิธีใดวิธีหนึ่ง)

```bash
# วิธีที่ 1: ใช้ SCP จาก PC
scp Model_Fix.onnx pi@<PI_IP>:~/dev_ws/

# วิธีที่ 2: ใช้ USB Flash Drive
# Copy ไฟล์ใส่ USB → เสียบ Pi → cp /media/.../Model_Fix.onnx ~/dev_ws/
```

---

### 3.5 ติดตั้ง STM32

ดาวน์โหลด Arduino IDE จาก https://www.arduino.cc/en/software จากนั้นเพิ่ม Board Support สำหรับ STM32 โดยไปที่ `File → Preferences → Additional boards manager URLs` แล้วเพิ่ม URL ต่อไปนี้

```
https://github.com/stm32duino/BoardManagerFiles/raw/main/package_stmicroelectronics_index.json
```

ไปที่ `Tools → Board → Boards Manager` ค้นหา `STM32` แล้วติดตั้ง จากนั้นตั้งค่า Board ดังนี้

```
Board       : Generic STM32F1 series
Upload Method: STLink
```

เปิดไฟล์ `stm32.ino` แล้วกด Upload ตรวจสอบ Serial Monitor ที่ `115200 baud` ควรเห็น `READY`

---

### 3.6 ตั้งค่าเครือข่าย (Network Configuration)

| อุปกรณ์ | IP Address |
|---|---|
| PC (Notebook ROS) | 10.0.0.1 (Static IP) |
| Raspberry Pi 5 | 10.0.0.2 (Static IP) |

ตั้ง IP แบบคงที่บน Windows โดยไปที่ การตั้งค่า → เครือข่ายและอินเทอร์เน็ต → Ethernet → การกำหนด IP → แก้ไข → กำหนดเอง แล้วกรอก IPv4: `10.0.0.1`, Subnet: `255.255.255.0`

ตั้ง Static IP บน Raspberry Pi

```bash
sudo nano /etc/dhcpcd.conf

# เพิ่มบรรทัดต่อไปนี้ที่ท้ายไฟล์:
interface eth0
static ip_address=10.0.0.2/24
static routers=10.0.0.1
static domain_name_servers=8.8.8.8

# บันทึกและ reboot
sudo reboot

# ทดสอบ ping จาก PC
ping 10.0.0.2
```

แก้ไข IP ใน `udp_bridge.py` บน Windows

```python
LISTEN_IP  = "0.0.0.0"
WSL_IP     = "172.29.199.88"   # ← IP ของ WSL2 (ตรวจสอบด้วย ip addr)
TARGET_IP  = "10.0.0.2"        # IP ของ Raspberry Pi
TARGET_PORT = 5001
```

> **หมายเหตุ:** IP ของ WSL2 จะเปลี่ยนทุกครั้งที่รีสตาร์ท Windows ให้ตรวจสอบใหม่ทุกครั้งด้วย `ip addr show eth0 | grep "inet "`

แก้ไข IP ใน `mainROS.py` บน Ubuntu

```python
PI_IP = "10.0.0.2"
PI_PORT = 5001
LISTEN_PORT = 5001
CAMERA_STREAM_URL = "http://10.0.0.2:5002/video_feed"
```

---

### 3.7 ติดตั้ง Web Frontend (craneaiextreme)

ติดตั้ง Node.js ใน Ubuntu (WSL2)

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
node --version   # ต้องได้ >= 18
```

ติดตั้ง Dependencies และรัน

```bash
cd craneaiextreme
cp .env.example .env

# แก้ไข .env — ใส่ GEMINI_API_KEY จริง
nano .env

npm install
npm run dev   # Web UI พร้อมใช้งานที่ http://localhost:3000
```

---

### 3.8 Verification Checklist

```bash
# 1. ตรวจสอบ ROS2
ros2 --version
# ผลที่ต้องได้: ros2 distro: humble

# 2. ตรวจสอบ package
ros2 pkg list | grep crane
# ผลที่ต้องได้: crane_motor

# 3. ตรวจสอบ ONNX (Ubuntu)
python3 -c "import onnxruntime; print('OK')"

# 4. ตรวจสอบ RealSense (Pi)
python3 -c "import pyrealsense2; print('OK')"

# 5. ทดสอบ ping (จาก PC)
ping 10.0.0.2
# ผลที่ต้องได้: Reply from 10.0.0.2

# 6. ตรวจสอบ Serial (Pi)
ls /dev/ttyUSB*
# ผลที่ต้องได้: /dev/ttyUSB0

# 7. ตรวจสอบ Node.js (Ubuntu)
node --version
# ผลที่ต้องได้: >= v18.x.x

# 8. ตรวจสอบ WSL2 IP
ip addr show eth0 | grep "inet "

# 9. ตรวจสอบ Model
ls ~/dev_ws/Model_Fix.onnx
# ผลที่ต้องได้: พบไฟล์
```

---

## 4. 3D Model, URDF และ XACRO

### 4.1 ขั้นตอนการออกแบบ

| ขั้น | เครื่องมือ | ผลลัพธ์ |
|---|---|---|
| 1. ออกแบบโมเดล 3D | SolidWorks | CAD แยกเป็น Link/Joint |
| 2. ส่งออก URDF | sw2urdf exporter | cranemotor.urdf + meshes/*.stl |
| 3. แปลงเป็น XACRO | xacro tool (ROS2) | cranemotor.xacro (นำกลับมาใช้ใหม่ได้) |

### 4.2 หลักการออกแบบ 3D สำหรับ ROS2

| ชื่อ Link | ลักษณะ | หมายเหตุ |
|---|---|---|
| base_link | ฐาน | คงที่ — ไม่เคลื่อนที่ |
| head_Link | หัวเครน | Revolute — หมุนรอบแกน Z (±90°) |
| arm_Link | แขน | Prismatic — เลื่อนขึ้น-ลงตามแกน Z |

กฎสำคัญที่ต้องปฏิบัติ ได้แก่ แยกชิ้นงานให้ชัดเจน (ฐาน หัว แขน เป็นคนละไฟล์), กำหนด Coordinate Frame ตาม ROS REP-103 (X=ไปข้างหน้า, Y=ซ้าย, Z=ขึ้น), บันทึกจุด Joint Center ที่กึ่งกลางชิ้นงาน, สร้าง Collision Mesh แยกจาก Visual Mesh และส่งออก mesh ในหน่วย **Meter**

### 4.3 การตั้งค่า Joint ใน sw2urdf

| Joint | Type | ขีดจำกัด |
|---|---|---|
| headcrane_Link | revolute | axis=Z, limit=±1.5708 rad |
| armcrane_Link | prismatic | axis=Z, limit=-0.52 ถึง 0.0 m |

### 4.4 ส่งออก STL แบบ Manual

```bash
# ใน SolidWorks:
# File → Save As → STL (.stl)
#   → Options → Unit: Meters
#   → Resolution: Fine
# ทำซ้ำสำหรับทุก Part: base.stl, head.stl, arm.stl
```

```bash
# ตรวจสอบ mesh ด้วย MeshLab:
# Filters → Cleaning → Remove Duplicated Vertex
# Filters → Cleaning → Remove Non Manifold Edge
```

โครงสร้างโฟลเดอร์ meshes ที่ต้องมี

```
src/crane_motor/
├── meshes/
│   ├── base.stl
│   ├── head.stl
│   └── arm.stl
├── urdf/
│   └── cranemotor.urdf
├── config/
│   └── controllers.yaml
└── launch/
    └── display.launch.py
```

### 4.5 cranemotor.urdf ฉบับสมบูรณ์

บันทึกไฟล์นี้ที่ `src/crane_motor/urdf/cranemotor.urdf`

```xml
<?xml version="1.0"?>
<robot name="crane_motor">

  <!-- ===== BASE LINK (ติดกับพื้น) ===== -->
  <link name="base_link">
    <visual>
      <geometry>
        <mesh filename="package://crane_motor/meshes/base.stl"/>
      </geometry>
    </visual>
    <collision>
      <geometry><box size="0.5 0.5 0.3"/></geometry>
    </collision>
    <inertial>
      <mass value="10.0"/>
      <inertia ixx="0.1" ixy="0" ixz="0"
               iyy="0.1" iyz="0" izz="0.1"/>
    </inertial>
  </link>

  <!-- ===== HEAD LINK (หัวเครน) ===== -->
  <link name="head_Link">
    <visual>
      <geometry>
        <mesh filename="package://crane_motor/meshes/head.stl"/>
      </geometry>
    </visual>
    <collision>
      <geometry><cylinder radius="0.1" length="0.3"/></geometry>
    </collision>
    <inertial>
      <mass value="3.0"/>
      <inertia ixx="0.05" ixy="0" ixz="0"
               iyy="0.05" iyz="0" izz="0.02"/>
    </inertial>
  </link>

  <!-- ===== ARM LINK (แขนบังกี้) ===== -->
  <link name="arm_Link">
    <visual>
      <geometry>
        <mesh filename="package://crane_motor/meshes/arm.stl"/>
      </geometry>
    </visual>
    <collision>
      <geometry><box size="0.05 0.05 0.6"/></geometry>
    </collision>
    <inertial>
      <mass value="1.5"/>
      <inertia ixx="0.02" ixy="0" ixz="0"
               iyy="0.02" iyz="0" izz="0.001"/>
    </inertial>
  </link>

  <!-- ===== REVOLUTE JOINT (หัวเครนหมุน) ===== -->
  <joint name="headcrane_Link" type="revolute">
    <parent link="base_link"/>
    <child link="head_Link"/>
    <origin xyz="0 0 0.5" rpy="0 0 0"/>
    <axis xyz="0 0 1"/>
    <limit lower="-1.5708" upper="1.5708"
           effort="10" velocity="1.0"/>
  </joint>

  <!-- ===== PRISMATIC JOINT (แขนบังกี้เลื่อน) ===== -->
  <joint name="armcrane_Link" type="prismatic">
    <parent link="head_Link"/>
    <child link="arm_Link"/>
    <origin xyz="0 0 0" rpy="0 0 0"/>
    <axis xyz="0 0 1"/>
    <limit lower="-0.52" upper="0.0"
           effort="100" velocity="0.5"/>
  </joint>

  <!-- ===== ROS2 CONTROL ===== -->
  <ros2_control name="crane" type="system">
    <hardware>
      <plugin>gazebo_ros2_control/GazeboSystem</plugin>
    </hardware>
    <joint name="headcrane_Link">
      <command_interface name="position"/>
      <state_interface name="position"/>
      <state_interface name="velocity"/>
    </joint>
    <joint name="armcrane_Link">
      <command_interface name="position"/>
      <state_interface name="position"/>
      <state_interface name="velocity"/>
    </joint>
  </ros2_control>

</robot>
```

### 4.6 cranemotor.xacro ฉบับสมบูรณ์

บันทึกไฟล์นี้ที่ `src/crane_motor/urdf/cranemotor.xacro`

```xml
<?xml version="1.0"?>
<robot xmlns:xacro="http://www.ros.org/wiki/xacro"
       name="crane_motor">

  <!-- ===== PARAMETERS ===== -->
  <xacro:property name="head_limit"     value="1.5708"/>
  <xacro:property name="arm_limit_down" value="-0.52"/>
  <xacro:property name="arm_limit_up"   value="0.0"/>
  <xacro:property name="base_mass"      value="10.0"/>
  <xacro:property name="head_mass"      value="3.0"/>
  <xacro:property name="arm_mass"       value="1.5"/>

  <!-- ===== MACRO: สร้าง inertial ===== -->
  <xacro:macro name="simple_inertial" params="mass ixx iyy izz">
    <inertial>
      <mass value="${mass}"/>
      <inertia ixx="${ixx}" ixy="0" ixz="0"
               iyy="${iyy}" iyz="0" izz="${izz}"/>
    </inertial>
  </xacro:macro>

  <!-- ===== BASE LINK ===== -->
  <link name="base_link">
    <visual>
      <geometry>
        <mesh filename="package://crane_motor/meshes/base.stl"/>
      </geometry>
    </visual>
    <collision>
      <geometry><box size="0.5 0.5 0.3"/></geometry>
    </collision>
    <xacro:simple_inertial mass="${base_mass}"
                           ixx="0.1" iyy="0.1" izz="0.1"/>
  </link>

  <!-- ===== HEAD LINK ===== -->
  <link name="head_Link">
    <visual>
      <geometry>
        <mesh filename="package://crane_motor/meshes/head.stl"/>
      </geometry>
    </visual>
    <collision>
      <geometry><cylinder radius="0.1" length="0.3"/></geometry>
    </collision>
    <xacro:simple_inertial mass="${head_mass}"
                           ixx="0.05" iyy="0.05" izz="0.02"/>
  </link>

  <!-- ===== ARM LINK ===== -->
  <link name="arm_Link">
    <visual>
      <geometry>
        <mesh filename="package://crane_motor/meshes/arm.stl"/>
      </geometry>
    </visual>
    <collision>
      <geometry><box size="0.05 0.05 0.6"/></geometry>
    </collision>
    <xacro:simple_inertial mass="${arm_mass}"
                           ixx="0.02" iyy="0.02" izz="0.001"/>
  </link>

  <!-- ===== REVOLUTE JOINT ===== -->
  <joint name="headcrane_Link" type="revolute">
    <parent link="base_link"/>
    <child link="head_Link"/>
    <origin xyz="0 0 0.5" rpy="0 0 0"/>
    <axis xyz="0 0 1"/>
    <limit lower="-${head_limit}" upper="${head_limit}"
           effort="10" velocity="1.0"/>
  </joint>

  <!-- ===== PRISMATIC JOINT ===== -->
  <joint name="armcrane_Link" type="prismatic">
    <parent link="head_Link"/>
    <child link="arm_Link"/>
    <origin xyz="0 0 0" rpy="0 0 0"/>
    <axis xyz="0 0 1"/>
    <limit lower="${arm_limit_down}" upper="${arm_limit_up}"
           effort="100" velocity="0.5"/>
  </joint>

  <!-- ===== ROS2 CONTROL ===== -->
  <ros2_control name="crane" type="system">
    <hardware>
      <plugin>gazebo_ros2_control/GazeboSystem</plugin>
    </hardware>
    <joint name="headcrane_Link">
      <command_interface name="position"/>
      <state_interface name="position"/>
      <state_interface name="velocity"/>
    </joint>
    <joint name="armcrane_Link">
      <command_interface name="position"/>
      <state_interface name="position"/>
      <state_interface name="velocity"/>
    </joint>
  </ros2_control>

</robot>
```

### 4.7 แปลง XACRO เป็น URDF

```bash
# ติดตั้ง xacro
sudo apt install ros-humble-xacro

# ไปที่ urdf folder
cd ~/dev_ws/ros2_ws/src/crane_motor/urdf/

# แปลง XACRO → URDF
xacro cranemotor.xacro > cranemotor.urdf

# ตรวจสอบผลลัพธ์
check_urdf cranemotor.urdf
# ผลที่ต้องได้:
# robot name is: crane_motor
# ---------- Successfully Parsed XML ---------------

# ดู tree structure
urdf_to_graphviz cranemotor.urdf
```

### 4.8 Encoder ↔ Joint Mapping

| พารามิเตอร์ | ค่า | หมายเหตุ |
|---|---|---|
| ENCODER_MIN | 0 | ซ้ายสุด (Limit Switch 1 กด) |
| ENCODER_MAX | 61 | ขวาสุด (Limit Switch 2 กด) |
| GAZEBO_RAD_MIN | -1.60 rad | mapping จาก encoder 0 |
| GAZEBO_RAD_MAX | +1.60 rad | mapping จาก encoder 61 |
| E2_MIN / E2_MAX | 0 / 325 | แขนล่างสุด / บนสุด |
| ARM_RAD_AT_E2_MIN | -0.52 rad | joint armcrane แขนลงสุด |
| ARM_RAD_AT_E2_MAX | 0.0 rad | joint armcrane แขนขึ้นสุด |

---

## 5. ลำดับการเปิดระบบ (Startup Sequence)

> ⚠️ **เปิดตามลำดับ 1→8 — หากเปิดผิดลำดับ: Controller ไม่โหลดหรือ Gazebo crash**

### 5.1 ขั้นตอนเปิดระบบ

**ขั้นที่ 1 — เปิด UDP Bridge (Windows CMD)**

```bash
cd Desktop
python udp_bridge1.py
```

**ขั้นที่ 2 — เปิด ROSBridge (WSL2 / Ubuntu)**

```bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

**ขั้นที่ 3 — เปิด Gazebo (WSL2 / Ubuntu)**

รอจน Gazebo เปิดสมบูรณ์ก่อนไปขั้นถัดไป

```bash
source /opt/ros/humble/setup.bash
gazebo --verbose \
  -s libgazebo_ros_init.so \
  -s libgazebo_ros_factory.so
```

**ขั้นที่ 4 — โหลด URDF Model (WSL2 / Ubuntu)**

```bash
source /opt/ros/humble/setup.bash
ros2 run robot_state_publisher robot_state_publisher \
  ~/dev_ws/ros2_ws/src/crane_motor/urdf/cranemotor.urdf
```

**ขั้นที่ 5 — Spawn Model เข้า Gazebo (WSL2 / Ubuntu)**

```bash
source /opt/ros/humble/setup.bash
ros2 run gazebo_ros spawn_entity.py -entity crane_motor -topic robot_description
```

**ขั้นที่ 6 — โหลด Joint Controllers (WSL2 / Ubuntu)**

```bash
source /opt/ros/humble/setup.bash
ros2 control load_controller --set-state active joint_state_broadcaster
ros2 control load_controller --set-state active arm_group_controller
```

**ขั้นที่ 7 — เปิด Main Program ROS (WSL2 / Ubuntu)**

รอ Pi ส่ง START ก่อนจึงจะเริ่มทำงาน

```bash
python3 ~/dev_ws/ros2_ws/src/crane_motor/scripts/mainROS.py
```

**ขั้นที่ 8 — เปิด Main Program Pi (Raspberry Pi 5)**

```bash
cd ~/dev_ws
python3 mainPI.py
```

### 5.2 Checklist ก่อนเปิดระบบ

| รายการ | วิธีตรวจสอบ | ผลที่ต้องการ |
|---|---|---|
| STM32 เชื่อมต่อ Pi | `ls /dev/ttyUSB0` | มี `/dev/ttyUSB0` |
| RealSense เชื่อมต่อ | `realsense-viewer` | กล้องแสดงภาพได้ |
| Pi → PC ping ได้ | `ping 10.0.0.1` | reply ต่อเนื่อง |
| PC → Pi ping ได้ | `ping 10.0.0.2` | reply ต่อเนื่อง |
| WSL2 IP ถูกต้อง | `ip addr show eth0` | ตรงกับ `WSL_IP` ในไฟล์ bridge |
| ROS2 พร้อมใช้ | `ros2 topic list` | แสดง topic list ได้ |
| Model_Fix.onnx อยู่ใน path | `ls ~/dev_ws/Model_Fix.onnx` | พบไฟล์ |

### 5.3 ตรวจสอบหลังเปิดระบบ

```bash
ros2 topic list                    # ดู topic ทั้งหมด — ต้องเห็น /joint_states
ros2 topic echo /joint_states      # ดู joint position realtime
ros2 control list_controllers      # ต้องเห็น active ทั้ง 2 controller
ros2 topic echo /crane_status      # ดูสถานะเครนรวม
```

### 5.4 GPIO ฮาร์ดแวร์บน Raspberry Pi 5

| ปุ่ม/เซ็นเซอร์ | GPIO | ผล |
|---|---|---|
| ปุ่ม Start | GPIO 17 | ส่ง ARM → START ไปยัง STM32 → ไฟเขียวติด |
| ปุ่ม Stop | GPIO 27 | STOP + DISARM → ระบบหยุดทันที → ไฟแดงติด |
| Emergency | GPIO 16 | ปิดฉุกเฉินทันที → ไฟแดงไม่หยุด |
| Pressure Sensor | GPIO 22 | ต้องกดก่อนเริ่มได้ |

| ไฟ LED | สถานะ | ความหมาย |
|---|---|---|
| 🔴 แดง ติดค้าง | ระบบพร้อม รอ START | ปกติ รอคำสั่ง |
| 🟢 เขียว ติดค้าง | ระบบกำลังทำงาน | เครนกำลังเคลื่อนที่ |
| 🔵 น้ำเงิน ติดค้าง | Pressure กด | GPIO22 active |
| 🔴 แดง กะพริบ | Emergency! | GPIO16 ถูกกด หรือสัญญาณหาย |

---

## 6. คู่มือการใช้งาน (User Guide)

### 6.1 การใช้งานผ่านหน้าเว็บ Dashboard

เปิดเบราว์เซอร์แล้วไปที่

```
http://10.0.0.1:9090
```

ปุ่มควบคุมหลักบน Dashboard

| ปุ่ม / คำสั่ง | ความหมาย |
|---|---|
| READY | รีเซ็ตสถานะ เตรียมพร้อมรับคำสั่งใหม่ |
| START (Pi) | กดปุ่ม GPIO17 บน Pi หรือส่งคำสั่ง START |
| STOP | หยุดการทำงานทุกอย่างทันที |
| HOME (h) | สั่ง Homing — เครนวิ่งกลับจุดเริ่มต้น |
| Cycle 1 (c1) | ทำงานอัตโนมัติช่องที่ 1 |
| Cycle 2 (c2) | ทำงานอัตโนมัติช่องที่ 2 |
| Cycle 3 (c3) | ทำงานอัตโนมัติช่องที่ 3 |
| Auto Process (x) | ทำงานอัตโนมัติทุกช่องเรียงลำดับ (1→2→3) |
| Manual (m xx) | ขยับเครนไปตำแหน่ง E1 ที่ระบุ เช่น `m25` |

### 6.2 ขั้นตอนการทำงานปกติ

การเริ่มต้นระบบ ให้ตรวจสอบว่าเปิดโปรแกรมทุกตัวครบตามลำดับในหัวข้อ 5 แล้ว จากนั้นกด Pressure Sensor (GPIO22) ค้างไว้หรือยึดให้อยู่ในตำแหน่ง ไฟน้ำเงินจะติดแสดงว่า Pressure พร้อม แล้วกดปุ่ม START บน Pi (GPIO17) หรือจากหน้าเว็บ ไฟเขียวจะติดและไฟแดงดับ แสดงว่าระบบพร้อมทำงาน

สำหรับ Auto Process ให้กด READY เพื่อเคลียร์สถานะเก่า จากนั้นกด Auto Process (x) ระบบจะ Homing ก่อนเสมอ แล้ววิ่งไปยังช่อง 1, 2, 3 ตามลำดับ สแกนหาตำแหน่ง peak ด้วยกล้อง ตักทรายจนช่องเต็ม (Photo Sensor = 1) และสรุปผลแสดงบนหน้าเว็บ

### 6.3 คำสั่งหลัก (mainROS.py CLI)

| คำสั่ง | หน้าที่ |
|---|---|
| `c1` | รอบ → ช่องที่ 1 (E1=7) |
| `c2` | รอบ → ช่องที่ 2 (E1=32) |
| `c3` | รอบ → ช่องที่ 3 (E1=54) |
| `x` | Full Auto Loop ทุก Slot (1→2→3) |
| `h` | Homing → ยกแขน → ขยับไป LS1 → รีเซ็ต E1=0 |
| `m <E1>` | ขยับหัวไปตำแหน่ง encoder ที่กำหนด (เช่น `m25`) |
| `reset_manual` | Force Homing ก่อน Manual ครั้งถัดไป |
| `q` / `stop` | Emergency_shutdown() ทันที |

### 6.4 Keyboard Teleop (teleop_crane_motor.py)

| ปุ่ม | การกระทำ |
|---|---|
| `q` | head_Link + (+0.1 rad) — หัวขวา |
| `a` | head_Link - (-0.1 rad) — หัวซ้าย |
| `w` | arm_Link + (+0.05 m) — ยืดแขน |
| `s` | arm_Link - (-0.05 m) — หดแขน |
| `Space` | รีเซ็ต joint ทั้งหมดเป็น 0 |
| `Ctrl+C` | หยุดโหนด teleop |

### 6.5 Debug Keys (mainPI.py)

| ปุ่ม | หน้าที่ |
|---|---|
| `1` / `2` / `3` | เลือก Station (ROI) วิเคราะห์ |
| `d` | สลับโหมด Debug — แสดง/ซ่อนตาราง 4 แผง |
| `r` | รีเซ็ตรอบการจับกลับเป็นรอบที่ 1 |
| `Space` | Trigger การจับภาพ/วิเคราะห์ด้วยตนเอง |
| `q` | ออกจากโปรแกรม |

### 6.6 Encoder และตำแหน่งเครน

| ค่า E1 | ตำแหน่ง |
|---|---|
| 0 | LS1 (Limit Switch ซ้าย — จุด Home) |
| 7 | ช่องที่ 1 (กึ่งกลาง) |
| 32 | ช่องที่ 2 (กึ่งกลาง) |
| 54 | ช่องที่ 3 (กึ่งกลาง) |
| 61 | ขอบขวาสุด |

> ค่า E1 สามารถเปลี่ยนได้ใน `mainROS.py` บรรทัด `SLOT_TARGETS`

### 6.7 Capture Round — การตักทรายหลายรอบ

| รอบ | % Peak | ความหมาย |
|---|---|---|
| 1st | 100% | ตักจุดสูงสุด (กองใหญ่) |
| 2nd | 65% | ตักจุดความสูง 65% |
| 3rd | 50% | ตักจุดความสูง 50% (กองที่เหลือ) |

### 6.8 Event Log บนหน้าเว็บ

| สี | ประเภท Event | ตัวอย่าง |
|---|---|---|
| 🟢 เขียว | การทำงานปกติ | HOME_OK, SCOOP_OK, AT_POS, SCAN_OK, DELIVER_OK |
| 🔴 แดง | ข้อผิดพลาด / คำเตือน | ERR_EMERGENCY, ERR_P4_TIMEOUT, ERR_STOP, WARN_YOLO |

### 6.9 การหยุดระบบ

หยุดปกติโดยรอให้ Cycle ปัจจุบันทำงานเสร็จ แล้วกด STOP หรือกดปุ่ม STOP บน Pi (GPIO27) ไฟแดงจะติดแสดงว่าระบบพร้อมสั่งใหม่

หยุดฉุกเฉินโดยกดปุ่ม Emergency (GPIO16) ทันที ระบบทุกอย่างจะหยุดพร้อมกัน วาล์วและมอเตอร์ทุกตัวปิดหมด ต้องปล่อย GPIO16 ก่อนจึงจะ START ใหม่ได้

ปิดโปรแกรมทั้งหมดโดยกด `Ctrl+C` ในแต่ละ Terminal ตามลำดับย้อนหลัง (8 → 1)

---

## 7. ระบบความปลอดภัย

### 7.1 Pressure Sensor (GPIO22)

ต้องกด Pressure Sensor ค้างไว้ตลอดการทำงาน ถ้าปล่อยระหว่างที่ระบบทำงานจะ AUTO STOP ทันที และต้อง START ใหม่

### 7.2 YOLO Safety

กล้องตรวจจับคนหรือสิ่งกีดขวางตลอดเวลา ถ้าพบจะระบบหยุดและรอ 3 วินาทีหลังพื้นที่ปลอดภัยแล้วค่อย resume ถ้าพบสิ่งกีดขวางนานเกิน 120 วินาทีจะ Emergency Stop อัตโนมัติ

| พารามิเตอร์ | ค่า |
|---|---|
| Model | YOLOv8 nano (yolov8n.pt) |
| Confidence Threshold | 0.35 (เพิ่มเป็น 0.5 ถ้า false positive บ่อย) |
| ช่วงตรวจสอบ | 0.25 วินาที (4 FPS) |
| Debounce อันตราย | 2.0 วินาที |
| Countdown ล้าง | 3.0 วินาที |
| Max Danger Timeout | 120.0 วินาที → Emergency_shutdown() |
| ROI | บน 15%, ล่าง 85%, ซ้าย 10%, ขวา 90% |
| Risk Classes | person, bicycle, car, motorcycle, bus, truck, cat, dog, horse, cow, bird |
| รอบลงคะแนน (Pi XCAP) | 3 รอบ × 1.1s → majority ≥2/3 = อันตราย |

---

## 8. ระบบกล้องและ AI (Vision & ONNX)

### 8.1 ขั้นตอนการวิเคราะห์ภาพ

| # | ขั้น | รายละเอียด | น้ำหนัก |
|---|---|---|---|
| 1 | Mask ROI | พื้นที่นอก ROI (erode 55px) | — |
| 2 | Depth Prominence Map | หา peak จากแผนที่ความลึก (Top-Hat 3 ขนาด) | 45% |
| 3 | Refraction Map | วิเคราะห์ความแตกต่างแสงผ่าน surface normals | 20% |
| 4 | Specular Map | หาจุดสว่าง specular ผ่าน LAB color space | 15% |
| 5 | Diffuse Gradient Map | วิเคราะห์การไล่ระดับสีจาก log-illumination | 10% |
| 6 | Curvature (Sobel) | ขอบและโค้งของพื้นผิวจาก Sobel depth gradient | 10% |
| 7 | ONNX Prediction | ทำนายตำแหน่ง (x,y) จาก RGB 224×224 | backup |
| 8 | Multi-Peak | หาจุดสูงสุด 3 จุด ระยะขั้นต่ำ 60px | — |
| 9 | E1 Mapping | ตำแหน่ง x ใน ROI → ค่า encoder E1 | — |

### 8.2 การตั้งค่ากล้อง (Intel RealSense D435)

| พารามิเตอร์ | ค่า |
|---|---|
| Depth Stream | 640×480 px, Z16, 30 FPS |
| Color Stream | 640×480 px, BGR8, 30 FPS |
| Spatial Filter | size=3, alpha=0.55, delta=20 |
| Temporal Filter | เปิดใช้งาน |
| มุมกล้อง | 45° |
| ความสูงอ้างอิงกอง | 180 mm |
| วิเคราะห์ทุก | 3 วินาที/ครั้ง |
| ONNX Input | 224×224×3 (RGB, CHW) |
| ONNX Output | พิกัด normalize (x, y) ช่วง 0–1 |
| Flask Stream URL | `http://<Pi_IP>:5002/video_feed` (JPEG quality 65) |

### 8.3 สถานี ROI

| Station | จุด ROI (pixel) | ช่วง E1 | Clamp E1 Output |
|---|---|---|---|
| 1 | (202,199),(601,177),(535,424),(265,424) | -4 ถึง 19 | 0–12 |
| 2 | (73,319),(636,262),(558,427),(196,459) | 13 ถึง 50 | 24–38 |
| 3 | (186,203),(542,174),(500,425),(260,433) | 46 ถึง 61 | 48–61 |

### 8.4 Photo Sensor — ตรวจสอบช่องเต็ม

| Sensor | ตรวจสอบ |
|---|---|
| P1 | ช่องที่ 1 เต็ม |
| P2 | ช่องที่ 2 เต็ม |
| P3 | ช่องที่ 3 เต็ม |
| P4 | แขนเครนอยู่ตำแหน่งบนสุด |

Photo Sensor จะยืนยันสถานะหลังจากสัญญาณค้าง 2 วินาที จึงจะนับว่าเต็ม

---

## 9. แผนผัง Hardware

### 9.1 STM32F103C8T6 — Input Pins

| Pin | สัญญาณ | Mode | หมายเหตุ |
|---|---|---|---|
| PA0 | ENC_A | INPUT_PULLUP | Encoder 1 Channel A (หัวเครน) — Interrupt CHANGE |
| PA1 | ENC_B | INPUT_PULLUP | Encoder 1 Channel B |
| PB6 | ENC2_A | INPUT_PULLUP | Encoder 2 Channel A (แขนบังกี้) — Interrupt CHANGE |
| PB7 | ENC2_B | INPUT_PULLUP | Encoder 2 Channel B |
| PB0 | LIMIT1 | INPUT_PULLUP | Limit Switch 1 — LOW=กด → รีเซ็ต E1=0 |
| PB1 | LIMIT2 | INPUT_PULLUP | Limit Switch 2 — LOW=กด → รีเซ็ต E1=-ENC_SCALE |
| PB12 | PHOTO1 | INPUT_PULLUP | Photo Sensor 1 (กดค้าง 2 วินาที → ยืนยัน P1) |
| PA4 | PHOTO2 | INPUT_PULLUP | Photo Sensor 2 |
| PA6 | PHOTO3 | INPUT_PULLUP | Photo Sensor 3 |
| PA7 | PHOTO4 | INPUT_PULLUP | Photo Sensor 4 — P4=1 → force E2=0 |
| A9 (RX) | STM32 RX | UART | รับคำสั่งจาก Pi (GPIO14) |
| A10 (TX) | STM32 TX | UART | ส่งไปยัง Pi (GPIO15) |

### 9.2 STM32F103C8T6 — Output Pins

| Pin | สัญญาณ | SSR | หมายเหตุ |
|---|---|---|---|
| PB10 | MAG1 | SSR 4-1 | มอเตอร์ทิศทาง 1 (ซ้าย) — LOW=ON |
| PB9 | MAG2 | SSR 4-2 | มอเตอร์ทิศทาง 2 (ขวา) — LOW=ON |
| PA5 | VALVE_UP | SSR 1-2 | Valve UP (ยกแขนบังกี้) — LOW=ON |
| PB14 | VALVE_DOWN | SSR 1-3 | Valve DOWN (ลดแขนบังกี้) — LOW=ON |
| PB13 | VALVE_BRAKE1 | SSR 1-4 | Brake 1 — LOW=ON |
| PB8 | VALVE_BRAKE2 | SSR 1-5 | Brake 2 — LOW=ON |
| PA2 | DIR_VALVE | — | วาล์วควบคุมทิศทาง — LOW=เปิด |

### 9.3 Raspberry Pi 5 — GPIO

| GPIO | สัญญาณ | ทิศทาง | หมายเหตุ |
|---|---|---|---|
| GPIO 14 | STM32 TX (A10) | TX→STM32 | Serial UART ส่งคำสั่ง |
| GPIO 15 | STM32 RX (A9) | RX←STM32 | Serial UART รับสัญญาณ |
| GPIO 17 | Start Button | Input | pull_up=True |
| GPIO 27 | Stop Button | Input | → reset_all_systems() |
| GPIO 22 | Pressure Sensor | Input | False → block start |
| GPIO 16 | Emergency Button | Input | is_active=False (LOW=active) |
| GPIO 23 | Green LED (SSR 2-2) | Output | ON = ระบบทำงาน |
| GPIO 24 | Red LED (SSR 2-3) | Output | ON = Error / Emergency |
| GPIO 25 | Blue LED (SSR 2-4) | Output | ON = AI ประมวลผล |

---

## 10. UDP และ Serial Protocol

### 10.1 คำสั่งที่ ROS PC ส่งไปยัง Pi (Port 5001)

| คำสั่ง | หมายเหตุ |
|---|---|
| `MAG1_ON` / `MAG1_OFF` | เปิด/ปิดมอเตอร์ทิศทางที่ 1 (ซ้าย) |
| `MAG2_ON` / `MAG2_OFF` | เปิด/ปิดมอเตอร์ทิศทางที่ 2 (ขวา) |
| `UP_ON` / `UP_OFF` | ยก/หยุดยกแขนบังกี้ (ทำซ้ำวาล์วทุก 1 วินาที นาน 13 วินาที) |
| `DOWN_ON` / `DOWN_OFF` | ลด/หยุดลดแขนบังกี้ |
| `B1_ON` / `B1_OFF` | เปิด/ปิด Brake 1 |
| `B2_ON` / `B2_OFF` | เปิด/ปิด Brake 2 |
| `ARM` | ต่อ ARM ก่อน START |
| `START` | เริ่มระบบ STM32 |
| `DISARM` | ปิดระบบ STM32 |
| `STOP` | หยุดฉุกเฉินทันที |
| `{"XCAP":1,"SLOT":1,"ROUND":1,"PCT":100}` | ขอให้ Pi วิเคราะห์ตำแหน่ง → ตอบกลับด้วย TARGET_E1 |

### 10.2 Pi ส่งกลับ → ROS (Port 5000)

| รูปแบบ | หมายเหตุ |
|---|---|
| `E1:<value>` | Encoder 1 — ตำแหน่งหัวเครน (count/10) realtime |
| `E2:<value>` | Encoder 2 — ตำแหน่งแขนบังกี้ (count/10) realtime |
| `LS1:1` / `LS2:1` | Limit Switch กด → รีเซ็ต E1=0 หรือ E1=-10 |
| `P1-P4:<0/1>` | ยืนยัน Photo Sensor (กดค้าง 2 วินาที) |
| `{"TARGET_E1":25,...}` | ผลวิเคราะห์ตำแหน่งจากกล้อง |
| `{"PRESS_STOP":1,...}` | Pi auto stop เพราะ pressure sensor หลุด |
| `{"START_BLOCKED":1,...}` | Pi Block START เพราะ emergency |

### 10.3 Serial STM32 Messages

| รูปแบบ | ตัวอย่าง | หมายเหตุ |
|---|---|---|
| `E1:<value>` | `E1:32` | Encoder 1 = encoderCount/10 |
| `E2:<value>` | `E2:150` | Encoder 2 = encoder2Count/10 |
| `READY` | `READY` | ส่งครั้งเดียวตอน boot |
| `ARMED` / `DISARMED` | `ARMED` | ตอบคำสั่ง ARM/DISARM |
| `SYSTEM:ON` / `SYSTEM:OFF` | `SYSTEM:ON` | ตอบคำสั่ง START/STOP |
| `ERROR: Not Armed` | `ERROR: Not Armed` | ส่ง START ก่อน ARM |
| `DBG \| E1:... E2:...` | `DBG \| E1:5 E2:10 \| LS1:0...` | Debug report เมื่อค่าเปลี่ยน |

---

## 11. ROS2 Topics Reference

| Topic | Message Type | Publisher | Subscriber |
|---|---|---|---|
| `/arm_group_controller/joint_trajectory` | JointTrajectory | crane_integrated_system | arm_group_controller |
| `/joint_states` | JointState | joint_state_broadcaster | crane_integrated_system |
| `/crane_status` | std_msgs/String (JSON) | crane_integrated_system | Web UI / Monitor |
| `/web_control_topic` | std_msgs/String (JSON) | Web UI (rosbridge) | crane_integrated_system |
| `/robot_description` | std_msgs/String (URDF) | robot_state_publisher | nodes |
| `/tf` / `/tf_static` | TF messages | robot_state_publisher | nodes |

---

## 12. พารามิเตอร์การกำหนดค่าระบบ

| พารามิเตอร์ | ค่า | หมายเหตุ |
|---|---|---|
| Update Rate | 1000 Hz | ros2_control |
| use_sim_time | true | จาก Gazebo |
| headcrane_Link PID | 10000.0 / 0.1 / 100.0 | Revolute joint |
| armcrane_Link PID | 10000.0 / 0.1 / 100.0 | Prismatic joint |
| PI_IP | 10.0.0.2 | Raspberry Pi (LAN) |
| PI_PORT | 5001 | UDP Port ของ Pi |
| Bang-Bang Hz | 20 Hz | Bang-Bang Control Loop |
| CYCLE_TRAVEL_TIME | 11.0 วินาที | ระยะเวลา 1 รอบ |
| HOMING_TIMEOUT | 30.0 วินาที | timeout สำหรับ homing |
| VALVE_REPEAT_INTERVAL | 1.0 วินาที | ส่ง UP/DOWN_ON ซ้ำทุก 1 วินาที |
| VALVE_REPEAT_DURATION | 13.0 วินาที | ส่งซ้ำนาน 13 วินาที |
| P4_TIMEOUT | 60.0 วินาที | timeout P4=1 |
| XCYCLE_CAM_TIMEOUT | 10.0 วินาที | timeout รอ TARGET_E1 |
| XCYCLE_MAX_PASSES | 20 | จำนวนผ่านสูงสุดต่อ slot |
| PHOTO_HOLD_MS (STM32) | 2000 ms | Photo Sensor hold 2 วินาที |
| MIN_PEAK_DISTANCE | 60 px | ระยะขั้นต่ำระหว่าง 2 จุด |
| SERIAL_PORT | /dev/ttyUSB0 | Serial port STM32 |
| SERIAL_BAUD | 115200 | Baud rate |

### Slot เป้าหมาย

| Slot | Encoder เป้าหมาย (E1) | Station ROI | Clamp E1 Output |
|---|---|---|---|
| 1 | 7 | 10–12 | — |
| 2 | 32 | 24–38 | — |
| 3 | 54 | 48–61 | — |

---

## 13. การแก้ไขปัญหา (Troubleshooting)

| อาการ | สาเหตุ | วิธีแก้ไข |
|---|---|---|
| `ERROR: Not Armed` | ยังไม่ได้ส่งคำสั่ง ARM | ส่ง ARM ก่อน START |
| Gazebo ไม่รับ Trajectory | Controller ไม่ทำงาน | `ros2 control list_controllers` → ตรวจ status |
| Gazebo ไม่แสดงโมเดล | source setup.bash ยังไม่ได้รัน | รัน `source /opt/ros/humble/setup.bash` |
| E1 ไม่อัปเดต | UDP bridge ไม่ทำงานหรือ IP ผิด | ตรวจ `udp_bridge.py` และ WSL2 IP (เปลี่ยนทุก reboot) |
| UDP ไม่ส่งข้อมูล | WSL2 IP เปลี่ยน | ตรวจสอบ IP ใหม่ด้วย `ip addr` |
| YOLO หยุดระบบบ่อย | YOLO_CONFIDENCE ต่ำ หรือแสงไม่พอ | ปรับ YOLO_CONFIDENCE (0.35 → 0.5) |
| YOLO ไม่พบ model | ไม่มีไฟล์ `yolov8n.pt` | ultralytics จะ download อัตโนมัติครั้งแรก |
| Photo Sensor ไม่ยืนยัน | ต้องค้างไว้ 2 วินาที | รอ 2 วินาทีหลังวัตถุถึงตำแหน่ง |
| Serial ไม่เชื่อมต่อ | `/dev/ttyUSB0` ไม่พบหรือสิทธิ์ไม่พอ | `sudo usermod -aG dialout $USER` → reboot |
| `No module named 'pyrealsense2'` | ยังไม่ได้ติดตั้ง SDK | `pip install pyrealsense2 --break-system-packages` |
| TARGET_E1 ไม่กลับมา | Pi ไม่รับ XCAP หรือวิเคราะห์ไม่ได้ | ตรวจ Model_Fix.onnx และ RealSense USB 3.0 |
| `ONNX model not found` | ไม่มีไฟล์ `Model_Fix.onnx` | วางไฟล์ใน `~/dev_ws/` |
| START ถูก Block | GPIO22 ไม่ทำงาน | กด Pressure Sensor ก่อน START |
| P4 timeout | ไม่ขึ้นถึงตำแหน่งบน | ตรวจ Photo Sensor 4 และ Valve UP |
| กล้องไม่เปิด | RealSense ขัดข้องหรือ port 5002 block | ตรวจ USB 3.0 และ firewall port 5002 |
| Emergency ติดตลอด | GPIO16 ลัดวงจรหรือสายขาด | ตรวจฮาร์ดแวร์ GPIO16 |
| rosbridge ไม่ต่อ | Port 9090 block | `sudo ufw allow 9090` |
| Pi ไม่สามารถ ping PC ได้ | IP ไม่ตรงหรือ Firewall | ตรวจสอบ Static IP และปิด Firewall ชั่วคราว |
| GPIO permission denied | ยังไม่ได้เพิ่ม group | `sudo usermod -a -G gpio $USER` แล้ว logout/login |
| STM32 ไม่ตอบสนอง | Serial port ผิด | ตรวจสอบด้วย `ls /dev/ttyUSB*` |

### คำสั่ง Debug

```bash
ros2 topic echo /crane_status        # สถานะเครน realtime
ros2 topic echo /joint_states        # joint position
ros2 control list_controllers        # controller status
screen /dev/ttyUSB0 115200           # serial output STM32 โดยตรง (Pi)
python3 -c "import onnxruntime; print(onnxruntime.__version__)"
python3 -c "import pyrealsense2; print('RealSense OK')"
```

---

*CraneAI Extreme | ROS2 Humble • Gazebo • YOLOv8 • ONNX • RealSense D435 • Raspberry Pi 5 • STM32F103*
