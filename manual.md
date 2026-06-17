CRANEAI EXTREME — แพ็คเกจ ROS2 สำหรับมอเตอร์เครน

ฉบับสมบูรณ์ | คู่มืออ้างอิงและการติดตั้งฉบับสมบูรณ์

เวอร์ชัน 3.0 | พฤษภาคม 2026


ส่วนประกอบเวอร์ชัน / ข้อมูลจำเพาะROS2Humble (Ubuntu 22.04 LTS)ศาลาคลาสสิก (gazebo_ros2_control)โมเดล AIYOLOv8n + ONNX Runtime (Model_Fix.onnx)กล้องอินเทล เรียลเซนส์ ดี435ตัวควบคุมRaspberry Pi 5 (RAM 8GB)เฟิร์มแวร์STM32F103C8T6 (Arduino)เว็บฟรอนต์เอนด์Node.js เวอร์ชัน 18 ขึ้นไป + rosbridge WebSocketข้อต่อ URDFheadcrane_Link (revolute) + armcrane_Link (prismatic)ซอฟต์แวร์ CADSolidWorks + ตัวส่งออก sw2urdf


1. ระบบต่างๆ (ภาพรวมระบบ)

ระบบ CraneAI Extreme เป็นระบบควบคุมอัตโนมัติที่มีอยู่ใน ROS2, Gazebo Simulator, AI (YOLOv8 + ONNX), กล้อง Intel RealSense D435 และฮาร์ดแวร์จริง (Raspberry Pi 5 + STM32F103) รองรับโหมดการทำงาน Full-Auto, Semi-Auto และ Manual ผ่าน Web UI หรือ CLI

1.1 การไหลของข้อมูล

ทิศทางนั่นรายละเอียดSTM32 → Piซีเรียล UART 115200ส่ง E1, E2, P1–P4, LS1–LS2 ทุก 20msPi → ROS PCพอร์ต UDP 5000ส่งสถานะ JSON + ผล Vision (TARGET_E1)ROS PC → Piพอร์ต UDP 5001ส่งคำสั่ง MAG/VALVE/STM32 + XCAP ขอPi → STM32ซีเรียล UART 115200ส่งคำสั่ง ARM/START/MAG_ON/VALVE ฯลฯเว็บ UI → ROSเว็บซ็อกเก็ต:9090ส่งคำสั่ง c1/c2/c3/x/h ผ่าน rosbridgeROS → ศาลาพักผ่อนหัวข้อ JointTrajectoryซิงค์กับโมเดลเสมือน

1.2 ภาพรวมของโปรโตคอล

ชั้นโปรโตคอลพอร์ต/บอดใช้ระหว่างซีเรียล UARTยูอาร์ที115200 บอดRaspberry Pi 5 ↔ STM32F103UDP (Pi→PC)ยูดีพีพอร์ต 5000Pi ส่งข้อมูลเซ็นเซอร์ + ผลการมองเห็น → ROS PCUDP (พีซี→Pi)ยูดีพีพอร์ต 5001ROS PC ส่งคำสั่ง control → Pi → STM32เว็บซ็อกเก็ตเว็บซ็อกเก็ตพอร์ต 9090ส่วนติดต่อผู้ใช้บนเว็บ ↔ ROS2 (rosbridge_server)ทศนิยมเอ็มเจเจจี เอชทีพอร์ต 5002Pi Flask → YOLO Monitor + เว็บ UIหัวข้อ ROS2ดีดีเอส/อาร์ทีพีเอส—ภายใต้ระบบนิเวศ ROS2


2. ขอระบบ (System Requirements)

2.1 คอมพิวเตอร์พีซี/โน้ตบุ๊ก (ROS PC)

รายชื่อเชโอเอสWindows 10/11 (64 บิต) + WSL2 Ubuntu 22.04 LTSซีพียูIntel Core i5 / AMD Ryzen 5 หรือดีกว่าแรมขั้นต่ำ 8 GB (แนะนำ 16 GB)การ์ดจอ (ไม่จำเป็น)สำหรับ YOLO inference อย่างต่อเนื่องเครือข่ายพอร์ต LAN หรือ Wi-Fi โดยประมาณ Raspberry Pi

2.2 ราสเบอร์รี่ พีอี 5


Raspberry Pi 5 (RAM 8 GB โปรโมชั่น)
Ubuntu 22.04 LTS (64-bit) เบาะบน microSD ≥ 32 GB
Intel RealSense D435 ส่วน USB 3.0
Python 3.10 ขึ้นไป


2.3 ซอฟต์แวร์ที่ต้องใช้ทั้งหมด

โปรแกรมสิ่งที่หมายเหตุไพธอน 3.xวินโดวส์ + ปี่ดาวน์โหลดจาก python.orgราดมิน VPNวินโดวส์สำหรับผ่านอินเทอร์เน็ต (ถ้าไม่มี LAN)WSL2 + Ubuntu 22.04วินโดวส์จากนั้นผ่าน PowerShellROS2 HumbleUbuntu (WSL2) + Piรองรับผ่าน aptNode.js เวอร์ชัน 18 ขึ้นไปอูบุนตู (WSL2)สำหรับส่วนหน้าของเว็บกิตUbuntu (WSL2) + Pisudo apt install gitIntel RealSense SDKราสเบอร์รี่ พีลิเบรียลเซนส์2YOLOv8 (ultralytics)Pi + Ubuntupip install ultralyticsONNX RuntimePi + Ubuntupip install onnxruntime


3. ขั้นตอนลงโปรแกรมทีละขั้นตอน


⚠️ รีสตาร์ท Windows 1 อีกครั้งในส่วนนี้ WSL2 — บันทึกงานทั้งหมดก่อนเริ่ม



3.1 ติดตั้ง WSL2 + Ubuntu 22.04 บน Windows

ขั้นตอนที่ 1 — ระบบ WSL2 (PowerShell ผู้ดูแลระบบ)

พาวเวอร์เชลล์# คลิกขวา Start Menu → Windows PowerShell (Admin)
wsl --install
wsl --set-default-version 2

# รีสตาร์ท Windows จากนั้นเปิด PowerShell ใหม่
wsl --install -d Ubuntu-22.04

# ตรวจสอบ
wsl --list --verbose
# ผลที่ต้องได้: Ubuntu-22.04 Running 2

ขั้นตอนที่ 2 — ติดตั้ง Ubuntu ครั้งแรก

หลังจากติดตั้งเสร็จ Ubuntu จะต้องขอให้ผู้ใช้ติดตามและติดตามรัน:

ทุบตีsudo apt update && sudo apt upgrade -y
sudo apt install -y curl gnupg2 lsb-release build-essential git

ขั้นตอนที่ 3 — ติดตั้ง Python บน Windows (สำหรับ udp_bridge.py)


ดาวน์โหลด Python 3.x จากhttps://python.org/downloads
ติ๊ก'Add Python to PATH'เพิ่มเติมในการติดตั้ง
การตัด CMD:


คำสั่งpython --version


3.2 ติดตั้ง ROS2 Humble (Ubuntu 22.04 / WSL2)


📌 ดำเนินการในUbuntu Terminal (WSL2) — เปิดโดยพิมพ์ 'Ubuntu' ใน Windows Search



ขั้นตอนที่ 4 — ตั้งค่า Locale

ทุบตีsudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

ขั้นตอนที่ 5 — รวมถึงพื้นที่เก็บข้อมูล ROS2

ทุบตีsudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) \
  signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
  http://packages.ros.org/ros2/ubuntu jammy main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

sudo apt update

ขั้นตอนที่ 6 — ติดตั้ง ROS2 Humble Desktop

ทุบตีsudo apt install -y ros-humble-desktop-full

# เพิ่ม source ใน .bashrc (ทำครั้งเดียว)
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc

# ตรวจสอบ
ros2 --version   # ผลที่ต้องได้: ros2 distro: humble

ขั้นตอนที่ 7 — ติดตั้งแพ็คเกจ ROS2 เพิ่มเติม

ทุบตีsudo apt update && sudo apt install -y \
  ros-humble-ros2-control \
  ros-humble-gazebo-ros2-control \
  ros-humble-joint-trajectory-controller \
  ros-humble-joint-state-broadcaster \
  ros-humble-controller-manager \
  ros-humble-robot-state-publisher \
  ros-humble-joint-state-publisher-gui \
  ros-humble-rviz2 \
  ros-humble-rosbridge-suite

ขั้นตอนที่ 8 — ติดตั้ง Python Libraries (Ubuntu WSL2)

ทุบตีpip install ultralytics opencv-python numpy
pip install flask onnxruntime

# ตรวจสอบ ONNX
python3 -c "import onnxruntime; print(onnxruntime.__version__)"


3.3 สร้าง ROS2 Workspace และ Copy โปรแกรม

ขั้นตอนที่ 9 — สร้างพื้นที่ทำงาน

ทุบตีmkdir -p ~/dev_ws/ros2_ws/src
cd ~/dev_ws/ros2_ws
colcon build --symlink-install
source install/setup.bash
echo "source ~/dev_ws/ros2_ws/install/setup.bash" >> ~/.bashrc

ขั้นตอนที่ 10 — คัดลอกแพ็คเกจ crane_motor

สำเนาcrane_motorที่ได้รับมาเยี่ยมชม~/dev_ws/ros2_ws/src/crane_motor/

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

ขั้นตอนที่ 11 — สร้างแพ็คเกจ

ทุบตีcd ~/dev_ws/ros2_ws
colcon build --symlink-install
source install/setup.bash

# ตรวจสอบ
ros2 pkg list | grep crane   # ผลที่ต้องได้: crane_motor


3.4 โปรแกรมบน Raspberry Pi 5

ขั้นตอนที่ 12 — ติดตั้ง ROS2 Humble บน Pi

ทำขั้นตอนเดียวกับส่วนที่ 3.2 (ขั้นตอนที่ 4–7) บน Pi Terminal

ขั้นตอนที่ 13 — ติดตั้ง Python Libraries บน Pi

ทุบตีpip install ultralytics opencv-python numpy
pip install pyrealsense2 flask onnxruntime gpiozero

# ตรวจสอบ RealSense
python3 -c "import pyrealsense2; print('RealSense OK')"

ขั้นตอนที่ 14 — สร้างพื้นที่ทำงานบน Pi

ทุบตีmkdir -p ~/dev_ws
cd ~/dev_ws
# ไฟล์ที่ต้องมี:
# - mainPI.py
# - Model_Fix.onnx

ขั้นตอนที่ 15 — ตั้งค่าการอนุญาตแบบอนุกรม

ทุบตี# ให้สิทธิ์ user เข้าถึง USB Serial (ทำครั้งเดียว)
sudo usermod -aG dialout $USER
sudo reboot

# ตรวจสอบหลัง reboot
ls /dev/ttyUSB*   # ผลที่ต้องได้: /dev/ttyUSB0

ขั้นตอนที่ 16 — ติดตั้ง Intel RealSense SDK

ทุบตีsudo apt-key adv --keyserver keyserver.ubuntu.com --recv-key F6E65AC044F831AC
sudo add-apt-repository "deb https://librealsense.intel.com/Debian/apt-repo $(lsb_release -cs) main"
sudo apt update
sudo apt install -y librealsense2-dkms librealsense2-utils librealsense2-dev

# ตรวจสอบ (เสียบกล้องก่อน)
realsense-viewer

ขั้นตอนที่ 17 — คัดลอก Model_Fix.onnx ในส่วนของ Pi

ทุบตี# วิธีที่ 1: ใช้ SCP จาก PC
scp Model_Fix.onnx pi@<PI_IP>:~/dev_ws/

# วิธีที่ 2: ใช้ USB Flash Drive
# Copy ไฟล์ใส่ USB → เสียบ Pi → cp /media/.../Model_Fix.onnx ~/dev_ws/


3.5 ตั้งค่าเครือข่าย (Network Configuration)

อาจารย์ที่อยู่ IPพีซี (โน้ตบุ๊ก ROS)10.0.0.1 (IP แบบคงที่)ราสเบอร์รี่ พีอี 510.0.0.2 (IP แบบคงที่)

ขั้นตอนที่ 18 — ตั้ง IP แบบคงที่บน Windows


เปิด การตั้งค่า → เครือข่ายและอินเทอร์เน็ต → อีเธอร์เน็ต
คลิก การกำหนด IP → แก้ไข → กำหนดเอง
IPv4: เปิด → IP: 10.0.0.1, ซับเน็ต:255.255.255.0


ขั้นตอนที่ 19 — ตั้ง Static IP บน Raspberry Pi

ทุบตีsudo nano /etc/dhcpcd.conf

# เพิ่มบรรทัดต่อไปนี้ที่ท้ายไฟล์:
interface eth0
static ip_address=10.0.0.2/24
static routers=10.0.0.1

# บันทึกและ reboot
sudo reboot

# ทดสอบ ping จาก PC
ping 10.0.0.2

ขั้นตอนที่ 20 — การแสดง IP ใน udp_bridge.py (Windows)

ไพธอนTARGET_IP = "10.0.0.2"   # IP ของ Raspberry Pi
TARGET_PORT = 5001

ขั้นตอนที่ 21 — เผยแพร่ IP ใน mainROS.py (Ubuntu)

ไพธอนPI_IP = "10.0.0.2"
PI_PORT = 5001
LISTEN_PORT = 5001
CAMERA_STREAM_URL = "http://10.0.0.2:5002/video_feed"


3.6 ติดตั้ง Web Frontend (craneaiiextreme)

ขั้นตอนที่ 22 — ติดตั้ง Node.js

ทุบตี# ใน Ubuntu (WSL2)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
node --version   # ต้องได้ >= 18

ขั้นตอนที่ 23 — ติดตั้งการพึ่งพาและรัน

ทุบตีcd craneaiextreme
cp .env.example .env

# แก้ไข .env — ใส่ GEMINI_API_KEY จริง
nano .env

npm install
npm run dev   # Web UI พร้อมใช้งานที่ http://localhost:3000


3.7 การตัดการเชื่อมต่อ (Verification Checklist)

ทุบตี# 1. ตรวจสอบ ROS2
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


4. สูงสุด 3D Model, URDF และ XACRO

มันเครื่องมือผลลัพธ์1. ออกแบบโมเดล 3 มิติโซลิดเวิร์คส์CAD แยกเป็น Link/Joint2. ส่งออกและสร้าง URDFผู้ส่งออก sw2urdfcranemotor.urdf + meshes/*.stl3. แปลงเป็น XACROเครื่องมือ xacro (ROS2)cranemotor.xacro (นำกลับมาใช้ใหม่ได้)

4.1 ตรวจสอบให้แน่ใจว่าสำหรับ 3D Modeling

ซอฟต์แวร์รูปแบบที่ส่งออกได้หมายเหตุโซลิดเวิร์คส์.STL, .STEP, .DAEโปรโมชั่นสำหรับการออกแบบทางกลฟิวชั่น 360.STL, .OBJ, .DAEฟรีสำหรับการศึกษาแบบคลาวด์เครื่องปั่น.DAE, .OBJ, .STLฟรี ไม่ใช่ Visual Meshฟรีแคด.STL, .STEPโอเพ่นซอร์สมีปลั๊กอิน ROS URDF

4.2 ขั้นตอนที่ 1 — ออกแบบโมเดล 3 มิติใน SolidWorks

4.2.1 หลักการออกแบบสำหรับ ROS2

ชื่อลิงก์โรงละครเกี่ยวกับเรื่องนี้ฐานลิงก์ฐานชุดชั้นใน (เพราะว่าพื้น)คงที่ — ไม่เคลื่อนที่ลิงก์หัวشحصหมุนรอบ — หมุนรอบแกน Z (±90°)arm_Linkแกะกล่องPrismatic — เลื่อนขึ้น-ลงตามแกน Z

กฎสำคัญที่ต้องปฏิบัติตามเสมอ:


แยกเป็นส่วนแยกกันให้ชัดเจน — ฐาน หัว แขน เป็นส่วนหนึ่งคนละไฟล์
กำหนด Coordinate Frame ให้ถูกต้อง — X = ไปข้างหน้า, Y = ซ้าย, Z = ขึ้น ROS REP-103
ตั้ง ที่มาของส่วน บันทึกจุด Joint Center — นี่คือกึ่งกลางชิ้นงาน
สร้าง Collision Mesh แยกจาก Visual Mesh — ใช้รูปร่างที่เรียบง่าย (กล่อง/กระบอกสูบ) เพื่อประสิทธิภาพในการชนกัน
ส่งออกนั้น mesh ในหน่วยMeter อย่างไรก็ตามคือ mm หรือนิ้ว


4.2.2 ซอฟต์แวร์ SolidWorks-to-URDF Exporter (sw2urdf)

ขั้นตอนรายละเอียดขั้นตอนที่ 1 — ดาวน์โหลดไปที่http://wiki.ros.org/sw_urdf_exporterจากนั้นเชื่อ .msi อาจใช้เวลานานสำหรับ SolidWorksขั้นตอนที่ 2 — ปลั๊กอินติดตั้งคลิกไฟล์ .msi จากนั้นจึงเปิด SolidWorks อีกครั้งขั้นตอนที่ 3 — การตัดไปที่เมนู Tools → คุณจะเห็น "ส่งออกเป็น URDF" สำเร็จในการติดตั้ง

4.2.3 ส่งออกด้วย sw2urdf

ขั้นตอนรายละเอียดขั้นตอนที่ 4 — เปิดผู้ส่งออก URDFเครื่องมือ → ส่งออกเป็น URDF → พื้นหลัง URDF Exporter เปิดขึ้นขั้นตอนที่ 5 — กำหนดแผนผังลิงก์base_link เป็นรูท → head_Link เป็นลูก → arm_Link เป็นลูกของ head_Linkขั้นตอนที่ 6 — ตั้งค่า Jointheadcrane_Link: type=revolute, axis=Z, limit=±1.5708 rad / armcrane_Link: type=prismatic, axis=Z, limit=-0.52 ถึง 0.0 mขั้นตอนที่ 7 — กำหนดมวลและความเฉื่อยใส่มวลและความเฉื่อยของลิงค์ (SolidWorks คำนวณให้อัตโนมัติ)ขั้นตอนที่ 8 — การส่งออกคลิก ส่งออก → เลือกโฟลเดอร์ → ได้ไฟล์ .urdf + ติดตาม meshes/ พร้อมไฟล์ .stl

4.2.4 Export STL แบบ Manual (กรณีไม่ใช้ sw2urdf)

# ใน SolidWorks:
File → Save As → STL (.stl)
  → Options → Unit: Meters
  → Resolution: Fine

# ทำซ้ำสำหรับทุก Part: base.stl, head.stl, arm.stl

ทุบตี# ตรวจสอบ mesh ด้วย MeshLab:
# Filters → Cleaning → Remove Duplicated Vertex
# Filters → Cleaning → Remove Non Manifold Edge

โฟลเดอร์เทศกาลที่ต้องมี:

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


4.3 ขั้นตอนที่ 2 — สร้างไฟล์ URDF

4.3.1 สนุกสนาน URDF

ส่วนประกอบจั๊มตัวอย่าง<link>ให้เห็นที่มองเห็น (visual + collision + inertial)base_link, head_Link, arm_Link<joint>ถัดไปที่เชื่อมลิงก์สองชิ้นพร้อมระบุชนิดอื่นๆheadcrane_Link (แบบหมุน), armcrane_Link (แบบเลื่อน)<ros2_control>กำหนดอินเทอร์เฟซฮาร์ดแวร์สำหรับ ros2_controlตำแหน่ง command/state สำหรับทั้ง 2 joint

4.3.2 เอกสารอ้างอิงร่วม

ชื่อร่วมพิมพ์ผู้ปกครอง → บุตรขีดจำกัดความพยายามลิงค์เครนหัวหมุนbase_link → head_Link-1.5708 ถึง +1.5708 เรเดียน10 นิวตันเมตรเครนแขน_ลิงก์ปริซึมhead_Link → arm_Link-0.52 ถึง 0.0 ม.100 นิวตัน

4.3.3 พร้อม cranemotor.urdf ฉบับสมบูรณ์


📌 จะต้องไฟล์นี้อย่างแน่นอนsrc/crane_motor/urdf/cranemotor.urdf



เอ็กซ์เอ็มแอล<?xml version="1.0"?>
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
    <axis xyz="0 0 1"/>   <!-- หมุนรอบแกน Z -->
    <limit lower="-1.5708" upper="1.5708"
           effort="10" velocity="1.0"/>
  </joint>

  <!-- ===== PRISMATIC JOINT (แขนบังกี้เลื่อน) ===== -->
  <joint name="armcrane_Link" type="prismatic">
    <parent link="head_Link"/>
    <child link="arm_Link"/>
    <origin xyz="0 0 0" rpy="0 0 0"/>
    <axis xyz="0 0 1"/>   <!-- เลื่อนในแนวแกน Z -->
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

4.3.4 ตัวเข้ารหัส ↔ การแมปข้อต่อ

พารามิเตอร์ค่าจั๊มตัวเข้ารหัส_ขั้นต่ำ0เลือกซ้ายสุด (Limit Switch 1 กด)ตัวเข้ารหัสสูงสุด61ตำแหน่งที่ถูกต้องสุด (Limit Switch 2 กด)GAZEBO_RAD_MIN-1.60 เรเดียนการทำแผนที่จาก encoder 0 → joint headcraneGAZEBO_RAD_MAX+1.60 เรเดียนการทำแผนที่จาก encoder 61 → joint headcraneการหมุนกลับด้านคู่จริงกลับทิศทางตัวเข้ารหัสในการติดตั้งฮาร์ดแวร์E2_MIN / E2_MAX0 / 325ขาออกบังกี้ล่างสุด / บนสุดARM_RAD_AT_E2_MIN-0.52 เรเดียนJoint Armcrane ช่วงแขนลงสุดอาร์เอ็มอาร์อาร์เอทีอี2แม็กซ์0.0 เรเดียนข้อต่ออาร์มเครนตอนแขนขึ้นสุด

4.3.5 การตัด URDF

ทุบตี# ติดตั้ง tools ตรวจสอบ
sudo apt install liburdfdom-tools

# ตรวจสอบ URDF syntax
check_urdf cranemotor.urdf
# ผลที่ต้องได้:
# robot name is: crane_motor
# ---------- Successfully Parsed XML ---------------
# root Link: base_link has 1 child(ren)

# ดู kinematic tree แบบ graph
urdf_to_graphviz cranemotor.urdf
# สร้างไฟล์ crane_motor.pdf แสดง link/joint tree


4.4 ขั้นตอนที่ 3 — แปลงเป็น XACRO

4.4.1 URDF เทียบกับ XACRO

โปรURDFเอ็กซ์เอซีโรเวลา / พารามิเตอร์❌ไม่มี — หัวเตียง hardcode ทุกค่า✅ ใช้ xacro :property ได้Macro / จำเป็นต้องซ้ำ❌ ต้องคัดลอกและวาง✅ ใช้ xacro :macro เรียกซ้ำได้มีเงื่อนไข❌ไม่รองรับ✅ รองรับ xacro :if / xacro :unlessสูง❌แก้บนทุกจุด✅แก้คุณสมบัติเดียวกระจายอัตโนมัติอยู่ใน ROS2✅ใช้ได้โดยตรง✅ แปลงเป็น URDF ก่อน (1 คำสั่ง)

4.4.2 พร้อม cranemotor.xacro ฉบับสมบูรณ์


📌 จะต้องไฟล์นี้อย่างแน่นอนsrc/crane_motor/urdf/cranemotor.xacro



เอ็กซ์เอ็มแอล<?xml version="1.0"?>
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

4.4.3 แปลง XACRO เป็น URDF ตะวันออก

ทุบตี# ติดตั้ง xacro
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

4.5 ยังคงเป็นทั้งหมด

มันเครื่องมือผลลัพธ์คำสั่งสำคัญ1. ออกแบบ 3 มิติโซลิดเวิร์คส์ไฟล์ชิ้นส่วน (.SLDPRT)ฐาน/หัว/แขน2. ปลั๊กอินตกแต่งsw2urdf (.msi)ปลั๊กอินในเมนูเครื่องมือเครื่องมือ → ส่งออกเป็น URDF3. ส่งออกไฟล์ STLบันทึกเป็นไฟล์ SolidWorksmeshes/*.stl (เมตร)ไฟล์ → บันทึกเป็น → STL → ตัวเลือก → เมตร4. หรือ URDFsw2urdf / เขียนมือเครนมอเตอร์.urdfcheck_urdf cranemotor.urdf5. สร้าง XACROโปรแกรมแก้ไขข้อความเครนมอเตอร์.xacroแทนฮาร์ดโค้ดด้วย ${property}6. โรงภาพยนตร์ XACROเครื่องมือ xacrocranemotor.urdf (final)xacro cranemotor.xacro > cranemotor.urdf7. สร้างและดำเนินการคอลคอน + ROS2ระบบพร้อมใช้งานcolcon build --symlink-install


5. รายละเอียดไฟล์ทั้งหมด (ไฟล์อ้างอิง)

5.1 มากมายไฟล์แพ็คเกจ crane_motor

ได้ / เป็นที่หน้าที่scripts/mainROS.pyการสร้างหลัก ROS2 node — พื้นฐาน crane, X-Cycle, YOLO safetyscripts/teleop_crane_motor.pyโหนดควบคุมระยะไกลด้วยแป้นพิมพ์ (q/a/w/s/SPACE)urdf/cranemotor.urdfโมเดล URDF ของเครน — ข้อต่อหัวเครน_Link (แบบหมุน) + ข้อต่อแขนเครน_Link (แบบเลื่อน)config/controllers.yamlตั้งค่า ros2_control: JointStateBroadcaster + JointTrajectoryControllerlaunch/display.launch.pyไฟล์เรียกใช้สำหรับการสร้างภาพ RVizCMakeLists.txt / package.xmlการกำหนดค่า build สำหรับ Colcon build~/dev_ws/mainPI.py (Pi)การเริ่มต้นหลัก Raspberry Pi 5~/dev_ws/Model_Fix.onnx (Pi)AI ONNX Model สำหรับนักวิเคราะห์ตำแหน่งกองDesktop/udp_bridge.py (Windows)การส่งต่อ UDP จาก STM32 ไปยัง Raspberry Pi

5.2 mainPI.py — การอัพเดตหลัก Raspberry Pi 5

โมดูล / ฟังก์ชันหน้าที่การกำหนดค่าNOTEBOOK_IP=10.0.0.1, PI_PORT=5001, SERIAL_PORT=/dev/ttyUSB0 @115200การติดตั้งฮาร์ดแวร์อุปกรณ์อินพุต GPIO: btn_start(17), btn_stop(27), press_sens(22), emerg_sens(16)_open_serial()/dev/ttyUSB0 @ 115200 baud พร้อมลองใหม่อัตโนมัติทุก 3 วินาทีมอนิเตอร์ฉุกเฉิน()GPIO16 ทุก 50ms — โดม active → Emergency_active=Truerecv_cmd()รับคำสั่ง UDP จาก ROS PC (พอร์ต 5001) แล้วส่งต่อ STM32 ทางซีเรียลอ่าน_ser()อ่าน STM32 ผ่านอนุกรมและส่งต่อ ROS PC ผ่าน UDPxcap_worker()รอ XCAP ร้องขอจาก ROS → yolo_check → full_analysis → ส่ง TARGET_E1 กลับstart_flask()เปิด Flask server ที่ http://<Pi_IP> :5002 /video_feed สำหรับสตรีม MJPEGการวิเคราะห์เต็มรูปแบบ()ไปป์ไลน์หลักวิเคราะห์ ROI → หา multi-peak (3 จุด) → คำ x-coord เป็นเป้าหมาย E1yolo_check_with_delay()ถ่ายภาพ 3 รอบ ห่าง 1.1s — คะแนนเสียงข้างมาก ≥2/3 = อันตราย → ส่ง TARGET_E1=-1

5.3 Python Libraries สำหรับ mainPI.py

ห้องสมุดนำเข้าหน้าที่โอเพ่นซีวีนำเข้า cv2การประมวลผลภาพ การแสดงผล การเข้ารหัส MJPEGนัมปี้import numpy as npคณิตศาสตร์อาร์เรย์สำหรับการวิเคราะห์ความลึก/ภาพไพเรียลเซนส์2import pyrealsense2 as rsIntel RealSense D435 SDKอัลตร้าไลติกส์จาก Ultralytics นำเข้า YOLOYOLOv8 การตรวจจับวัตถุเพื่อตรวจสอบความปลอดภัยonnxruntimeimport onnxruntime as ortการอนุมาน ONNX สำหรับ Model_Fix.onnxจีพีโอเซโรจากการนำเข้าของ gpiozero ...GPIO input/output สำหรับปุ่ม, หลอดไฟ, เซ็นเซอร์ขวดแก้วจากการนำเข้า Flask, Responseเซิร์ฟเวอร์ HTTP สำหรับพอร์ตสตรีมกล้อง 5002ซ็อกเก็ตนำเข้าซ็อกเก็ตการสื่อสาร UDP กับ ROS PCซีเรียลนำเข้าซีเรียลการสื่อสารแบบอนุกรม UART กับ STM32การร้อยด้ายนำเข้าเธรดมัลติเธรด: recv_cmd, read_ser, gpio_monitor, xcap_worker

5.4 mainROS.py — การอัพเดตหลัก ROS2 Node

วิธีการ / ฟังก์ชันหน้าที่เริ่มต้น ()ตั้งค่าผู้เผยแพร่ ผู้รับข้อมูล ซ็อกเก็ต UDP ตัวตรวจสอบ YOLO ตัวแปรสถานะudp_monitor()thread รับข้อมูล realtime จาก Pi: parse E1/E2/P1-P4/LS1-LS2/TARGET_E1เรียกกลับร่วม()สมัครสมาชิก /joint_states → ซิงค์ Gazebo ↔ ฮาร์ดแวร์ + การควบคุมมอเตอร์แบบ Bang-bangweb_control_callback()รับคำสั่งจาก /web_control_topic ที่ส่งมาจาก Web UI ผ่าน rosbridgeexecute_command()แยกวิเคราะห์และส่งคำสั่ง: c1-c3, x, h, m, reset_manual, qรันไซเคิล (สล็อต)รองเท้า 1 รอบไป slot ที่กำหนด: homing → loop(XCAP → move → bungkee)run_x_cycle()นาฬิกา full auto loop ทุก slot (1→2→3) สล็อตอัตโนมัติเมื่อเต็มdo_homing()ยกแขน (UP_ON) → ขยับหัววิคตอเรียไป LS1 → รีเซ็ตตัวเข้ารหัสออฟเซ็ต E1=0do_bunkee_task()DOWN_ON → รอ E2≥280 → รอ 12 วินาที → UP_ON → รอ P4=1 → เบรก B1+B2_xcycle_request_capture()ส่ง XCAP JSON เช่นกัน Pi และรอรับ TARGET_E1 ส่วนภายใน 10 วินาทีmove_to_enc(target)ขยับหัวบัลเล่ต์ไปยังเป้าหมายตัวเข้ารหัส พร้อมเธรดการตรวจสอบความปลอดภัย YOLOการปิดระบบฉุกเฉิน()ทุกอย่างทันที: ส่ง STOP + ปิด actuator ทุกตัวคลาส YoloSafetyMonitorเธรดพื้นหลัง ดึง MJPEG สตรีมจาก Pi Flask → การอนุมาน YOLOv8


6. โหนด ROS2 และหัวข้อ

6.1 โหนด ROS2 และอื่นๆ

ชื่อโหนดไฟล์ต้นฉบับหน้าที่ระบบเครนแบบบูรณาการmainROS.pyระบบหลักรับคำสั่งจาก Web/Socket + UDP + Bangbang controlมอเตอร์เครนแบบเทเลออปโหนดteleop_crane_motor.pyรับคำสั่งคีย์บอร์ด (q/a/w/s) บังคับร่วมแบบเรียลไทม์ตัวควบคุม_ผู้จัดการros2_control (ปลั๊กอิน)การจัดการ controller ในส่วนนี้ ros2_controlผู้แพร่ภาพกระจายเสียงร่วมของรัฐสถานีวิทยุร่วมรัฐออกอากาศสถานะ joint อีกครั้ง /joint_states ทุกลูปตัวควบคุมกลุ่มแขนตัวควบคุมวิถีร่วมรับ JointTrajectory ขั้นที่ 2 ข้อต่อผู้เผยแพร่สถานะหุ่นยนต์(เปิดใช้งาน / คำสั่ง)เผยแพร่ URDF และ TF frames ของ robot

6.2 หัวข้อ ROS2 ทั้งหมด

ชื่อหัวข้อประเภทข้อความสำนักพิมพ์สมาชิก/ตัวควบคุมกลุ่มแขน/วิถีข้อต่อวิถีร่วมระบบเครนแบบบูรณาการตัวควบคุมกลุ่มแขน/รัฐร่วมจอยท์สเตทผู้แพร่ภาพกระจายเสียงร่วมของรัฐระบบเครนแบบบูรณาการ/สถานะเครนstd_msgs/String (JSON)ระบบเครนแบบบูรณาการส่วนติดต่อผู้ใช้บนเว็บ / จอภาพ/หัวข้อเว็บควบคุมstd_msgs/String (JSON)ส่วนติดต่อผู้ใช้บนเว็บ (rosbridge)ระบบเครนแบบบูรณาการ/คำอธิบายหุ่นยนต์std_msgs/String (URDF)ผู้เผยแพร่สถานะหุ่นยนต์โหนด/tf / /tf_staticข้อความ TFผู้เผยแพร่สถานะหุ่นยนต์โหนด

6.3 เป้าหมายสล็อต

สล็อตเป้าหมายตัวเข้ารหัส (E1)สถานี ROIเอาต์พุตคีย์ E1แคลมป์ช่องที่ 1710 – 12—ช่อง 232224 – 38—ช่องที่ 354348 – 61—


7. ทำอะไรไม่ได้เลยระบบ (Startup Sequence)


⚠️ เปิดในเวลา 1 → 8 อีกครั้ง — หากเปิดผิดอีกครั้ง: Controller ไม่สามารถโหลดหรือ Gazebo crash



เร็วเปิดบนคำสั่ง + หน้าที่1Windows CMDcd Desktop && python udp_bridge.py← เปิดก่อนทุกอย่าง2อูบุนตูน ดับเบิลยูเอสแอล2ros2 launch rosbridge_server rosbridge_websocket_launch.xml3อูบุนตูน ดับเบิลยูเอสแอล2source /opt/ros/humble/setup.bash && gazebo --verbose -s libgazebo_ros_init.so -s libgazebo_ros_factory.so(รอจน กาเซโบ เปิด!)4อูบุนตูน ดับเบิลยูเอสแอล2ros2 run robot_state_publisher robot_state_publisher ~/dev_ws/ros2_ws/src/crane_motor/urdf/cranemotor.urdf5อูบุนตูน ดับเบิลยูเอสแอล2ros2 run gazebo_ros spawn_entity.py -entity crane_motor -topic robot_description6อูบุนตูน ดับเบิลยูเอสแอล2ros2 control load_controller --set-state active joint_state_broadcaster && ros2 control load_controller --set-state active arm_group_controller7อูบุนตูน ดับเบิลยูเอสแอล2python3 ~/dev_ws/ros2_ws/src/crane_motor/scripts/mainROS.py(รอ Pi ส่ง START)8ราสเบอร์รี่ พีcd ~/dev_ws && python3 mainPI.py(กดปุ่ม Start เพื่อเริ่ม)

7.1 การตัดหลังเปิดระบบ

ทุบตีros2 topic list                    # ดู topic ทั้งหมด — ต้องเห็น /joint_states
ros2 topic echo /joint_states      # ดู joint position realtime
ros2 control list_controllers      # ต้องเห็น active ทั้ง 2 controller
ros2 topic echo /crane_status      # ดูสถานะเครนรวม

7.2 ระบบ ARM ฮาร์ดแวร์

ต้อง / ทำอย่างไรจีพีไอโอผลลัพธ์ปุ่มเริ่มต้นจีพีไอโอ 17ส่ง ARM → START ไฟล์ STM32 → ไฟเขียวติดปุ่มหยุดจีพีไอโอ 27STOP + DISARM → ระบบหยุดทันที → ไฟแดงติดภาวะฉุกเฉินจีพีไอโอ 16การปิดเครื่องฉุกเฉินทันที → ไฟแดงไม่หยุดเซ็นเซอร์ความดันจีพีไอโอ 22เปิดใช้งานก่อนกดเริ่มได้

แสงไฟจั๊มของเขียวระบบทำงาน (is_running=1)เตาแดงการรักษา / Error / เหตุฉุกเฉินแดงต่อไปเหตุฉุกเฉินกำลังทำงานต่อประมวลผล AI


8. คำสั่งควบคุม (อ้างอิงคำสั่ง)

8.1 คำสั่งหลัก (mainROS.py CLI)

ลุงจั๊มรายละเอียดซี1รอบ → ช่องที่ 1ขยับหัวบัลเล่ต์ไป E1=7, ดู XCAP loop ช่องที่ 1 ตรงซี2รอบ → ช่อง 2ย้ายหัวบัลเล่ต์ไป E1=32, นัด XCAP ลูปช่องที่ 2 ตรงซี3รอบ → ช่อง 3ย้ายหัวบัลเล่ต์ไป E1=54, นัด XCAP ลูปช่องที่ 3 ตรงxกระบวนการอัตโนมัตินาฬิกาทุก Slot (1→2→3) อัตโนมัติเมื่อช่องเต็มชม.กลับบ้านกลับหน้าแรก → ยกแขน → ขยับไป LS1 → รีเซ็ต E1=0ม <E1>เคลื่อนย้ายด้วยตนเองขยับหัวแพทย์ไปตำแหน่งตัวเข้ารหัสที่กำหนด (เช่น m25)รีเซ็ตด้วยตนเองรีเซ็ตตำแหน่งเริ่มต้นบังคับ Homing เทคก่อนคู่มือการเข้าชมถัดไปq / หยุดปุ่มหยุดฉุกเฉินEmergency_shutdown() ทันที — สารคดีทุก actuator

8.2 แป้นพิมพ์ควบคุมระยะไกล (teleop_crane_motor.py)

สำคัญการกระทำหมายเหตุqข้อต่อหัว + (+0.1 เรเดียน)ขยับหัวบัลเล่ต์ไปทางขวาเอข้อต่อหัว - (-0.1 เรเดียน)ขยับหัวบัลเล่ต์ไปทางซ้ายวข้อต่อแขน + (+0.05 ม.)ยืดแขนบัลเล่ต์ออกสข้อต่อแขน - (-0.05 ม.)บีบแขนบัลเล่ต์เข้าช่องว่างรีเซ็ตข้อต่อทั้งหมดเป็น 0กลับตำแหน่งบ้านCtrl+Cหยุดโหนดควบคุมระยะไกลคีย์บอร์ด

8.3 ปุ่มดีบักกล้อง (หน้าต่างแสดงผลแบบเรียลไทม์ mainPI.py)

สำคัญจั๊ม1 / 2 / 3นรก Station (ROI) ใช้วิเคราะห์ — ช่องที่ 1/2/3งสลับโหมดดีบัก — แสดง/ซ่อน ตารางดีบักการวิเคราะห์ 4 แผงรรีเซ็ตรอบการจับกลับเป็นรอบที่ 1 (100%)ช่องว่างการจับภาพและการวิเคราะห์ทริกเกอร์ด้วยตนเองทันทีqออกจากโปรแกรม


9. ระบบกล้องและ AI วิเคราะห์ตำแหน่ง (Vision & ONNX)

9.1 กระบวนการวิเคราะห์ภาพ

#จั๊มเยี่ยมชมต่อ1หน้ากาก ROIพื้นที่นอก ROI อีกครั้ง (กัดกร่อน 55px สำหรับอัตราความปลอดภัย)—2แผนที่แสดงความโดดเด่นของความลึกรักษายอดนูนจากแผนที่ความลึกด้วยสัณฐานวิทยาหมวกทรงสูง 3 ขนาด45%3แผนที่การหักเหของแสงวิเคราะห์ความแตกต่างระหว่างแสงที่คาดหวัง กับที่เกิดขึ้นจริงผ่านพื้นผิวปกติ20%4แผนที่สะท้อนแสงหาจุดสว่างจากแสง specular ผ่าน LAB color space15%5แผนที่ไล่ระดับสีแบบกระจายวิเคราะห์การไล่ระดับสีของแสงกระจายจาก log-illumination10%6ความโค้ง (โซเบล)ขอบและโค้งของพื้นผิว จาก Sobel การไล่ระดับสีของความลึก10%7การทำนายผล ONNXทำนายตำแหน่ง (x,y) จากภาพ RGB 224×224 — AI backup/crosscheckสำรองข้อมูล8ยอดหลายยอดหาจุดสูงสุด 3 จุดที่เหลือขั้นต่ำระยะทาง 60px—9การแมป E1ตำแหน่ง x ใน ROI → ค่าตัวเข้ารหัส E1 ต้องการ—

9.2 การกำหนดค่ากล้อง (Intel RealSense D435)

พารามิเตอร์ค่ากระแสน้ำลึก640×480 พิกเซล, รูปแบบ Z16, 30 เฟรมต่อวินาทีกระแสสี640×480 พิกเซล, รูปแบบ BGR8, 30 เฟรมต่อวินาทีตัวกรองเชิงพื้นที่ขนาด = 3, ค่าความเรียบอัลฟา = 0.55, ค่าความเรียบเดลต้า = 20ตัวกรองเวลาเปิดใช้งานจัดเรียงจัดแนวให้ตรงกับกระแสสีมุมกล้อง45° (ใช้คอมโพเนนต์ความลึกแนวตั้งคำนวณ)ความสูงของกอง (มม.)180 มม. (ความสูงอ้างอิงของกอง)วินาทีวิเคราะห์3 /จับภาพขนาดอินพุต ONNX224×224×3 (รูปแบบ RGB, CHW)เอาต์พุต ONNXพิกัดปกติ (x, y) 0-1URL ของ Flask Streamhttp://<Pi_IP> :5002 /video_feed (JPEG quality 65)

9.3 สถานี ROI

สถานีคะแนน ROI (พิกเซล)ช่วง E1แคลมป์เอาต์พุต E11(202,199), (601,177), (535,424), (265,424)(-4, 19)(0, 12)2(73,319), (636,262), (558,427), (196,459)(13, 50)(24, 38)3(186,203), (542,174), (500,425), (260,433)(46, 61)(48, 61)

9.4 ระบบความปลอดภัย YOLO

พารามิเตอร์ค่า / ความหมายแบบอย่างYOLOv8 nano (yolov8n.pt)เกณฑ์ความเชื่อมั่น0.35 (เพิ่มเป็น 0.5 ถ้าผลบวกลวงบ่อย)ช่วงเวลาตรวจสอบ0.25 วินาที (4 FPS)ดีบาวซ์อันตราย2.0 วินาที (ต้องตรวจสอบนาน 2 วินาทีถือว่าถือว่าอันตราย)นับถอยหลังล้าง3.0 วินาที (ปลอดภัย 2 วินาที + นับถอยหลัง 3 วินาที ก่อนดำเนินการต่อ)แม็กซ์ แดนเจอร์ ไทม์เอาท์120.0 วินาที → Emergency_shutdown() อัตโนมัติผลตอบแทนจากการลงทุนบน: 15 %, ล่าง: 85 %, ซ้าย: 10 %, ขวา: 90 %ระดับความเสี่ยงคน, จักรยาน, รถยนต์, รถจักรยานยนต์, รถบัส, รถบรรทุก, แมว, สุนัข, ม้า, วัว, นกรอบการลงคะแนน (XCPAP ฝั่ง Pi)3 รอบ × 1.1s → เสียงข้างมาก ≥2/3 = อันตราย


10. แผนผังขาต่อฮาร์ดแวร์

10.1 STM32F103C8T6 — อินพุต

เข็มหมุดสัญญาณโหมดหมายเหตุพีเอ0เอ็นซี_เออินพุต_พูลอัพEncoder 1 Channel A (หัวบัลเล่ต์) — Interrupt CHANGEพีเอ1อีเอ็นซี_บีอินพุต_พูลอัพตัวเข้ารหัส 1 ช่อง Bพีบี6อีเอ็นซี2_เออินพุต_พูลอัพตัวเข้ารหัส 2 ช่อง A (แขนบังกี้) — ขัดจังหวะ CHANGEพีบี7อีเอ็นซี2_บีอินพุต_พูลอัพตัวเข้ารหัส 2 ช่อง BพีบีโอLIMIT1อินพุต_พูลอัพลิมิตสวิตช์ 1 — ต่ำ=กด → รีเซ็ต E1=0พีบี1LIMIT2อินพุต_พูลอัพสวิตช์จำกัด 2 — LOW = กด → รีเซ็ต E1 = -ENC_SCALEพีบี12ภาพที่ 1อินพุต_พูลอัพเซ็นเซอร์รับภาพ 1 (กดค้างไว้ 2 วินาที → ยืนยัน P1 แล้ว)พีเอ4ภาพที่ 2อินพุต_พูลอัพเซ็นเซอร์รับภาพ 2พีเอ6ภาพที่ 3อินพุต_พูลอัพเซ็นเซอร์รับภาพ 3พีเอ7ภาพที่ 4อินพุต_พูลอัพเซ็นเซอร์แสง 4 — P4=1 → แรง E2=0เอ9 (RX)STM32 RXยูอาร์ทีรับคำสั่งจาก Pi (GPIO14)เอ10 (เท็กซัส)STM32 TXยูอาร์ทีต่อไปยัง Pi (GPIO15)

10.2 STM32F103C8T6 — เอาต์พุต

เข็มหมุดสัญญาณเอสเอสอาร์จั๊มพีบี10แม็ก1เอสเอสอาร์ 4-1มอเตอร์แม่เหล็ก 1 (ด้านซ้าย) — LOW=ON (active-low)พีบี9แม็ก2เอสเอสอาร์ 4-2มอเตอร์แม่เหล็ก 2 (ทิศทางขวา) — LOW=ONพีเอ5วาล์วอัพเอสเอสอาร์ 1-2Valve UP (ยกแขนบังกี้) — LOW=ONพีบี14วาล์วลงSSR 1-3Valve DOWN (ลดแขนบังกี้) — LOW=ONพีบี13วาล์วเบรก1SSR 1-4เบรก 1 — LOW=ONพีบี8วาล์วเบรก2SSR 1-5เบรก 2 — LOW=ONพีเอ2ไดร์_วาล์ว—วาล์วควบคุมทิศทาง — ต่ำ = เปิด

10.3 Raspberry Pi 5 — GPIO

จีพีไอโอสัญญาณทิศทางหมายเหตุจีพีไอโอ 14STM32 TX (A10)TX→STM32Serial UART ส่งคำสั่งไปยัง STM32จีพีไอโอ 15STM32 RX (A9)RX←STM32Serial UART รับสัญญาณ STM32จีพีไอโอ 17ปุ่มเริ่มต้นป้อนข้อมูลpull_up=True — is_active=True = กดจีพีไอโอ 27ปุ่มหยุดป้อนข้อมูล→ รีเซ็ต_all_systems()จีพีไอโอ 22เซ็นเซอร์ความดันป้อนข้อมูลเท็จ → บล็อกเริ่มต้น โดมกำลังวิ่ง → หยุดอัตโนมัติจีพีไอโอ 16ปุ่มฉุกเฉินป้อนข้อมูลis_active=False (LOW=active) → emergency_active=Trueจีพีไอโอ 23สีเขียวอ่อน (SSR 2-2)เอาต์พุตเปิด = ระบบกำลังทำงานจีพีไอโอ 24สีแดงหลอดไฟ (SSR 2-3)เอาต์พุตON = กรณี / Error / เหตุฉุกเฉิน (0.3 วินาที)GPIO 25สีน้ำเงินโคมไฟ (SSR 2-4)เอาต์พุตON = โปรดดู AI


11. คำสั่ง UDP และคำสั่งอนุกรม STM32

11.1 คำสั่งที่ ROS PC ส่งไปยัง Pi (พอร์ต 5001)

สั่งการจั๊มหมายเหตุMAG1_ON / MAG1_OFFเปิด/ปิด มอเตอร์ทิศทางที่ 1 (ซ้าย)ใช้แคนนอน_LinkMAG2_ON / MAG2_OFFเปิด/ปิด มอเตอร์ทิศทางที่ 2 (ขวา)ใช้แคนนอน_Linkเปิด / ปิดยก/หยุดยกพื้นที่บังกี้ทำซ้ำวาล์วทุก 1 วินาทีนาน 13 วินาทีดาวน์เปิด / ดาวน์ปิดลด/หยุดลดช่องทางบังกี้ทำซ้ำวาล์วทุก 1 วินาทีนาน 13 วินาทีB1_เปิด / B1_ปิดเปิด/ปิด เบรค 1ใช้หลังแขนตำแหน่งB2_เปิด / B2_ปิดเปิด/ปิด เบรค 2สเปค B1แขนยังมีระบบ STM32ต่อ ARM ก่อน STARTเริ่มเริ่มระบบ STM32อาร์มต่อส่งก่อนปลดอาวุธปิดระบบ STM32ปิดตัวกระตุ้นทุกตัวหยุดหยุดฉุกเฉินทันทีมีทุกแอคชูเอเตอร์{"XCAP":1,"SLOT":1,"ROUND":1,"PCT":100}ขอให้ Pi ถ่ายภาพและวิเคราะห์ตำแหน่งพี่ตอบกลับด้วย TARGET_E1

11.2 ต้อนรับ Pi ส่งกลับ → ROS (พอร์ต 5000)

รูปแบบจั๊มE1:<ค่า>Encoder 1 — ตำแหน่งหัววิคตอเรีย (count/10) เรียลไทม์E2:<ค่า>Encoder 2 — ตำแหน่งแขนบังกี้ (count/10) เรียลไทม์LS1 :1 / LS2 :1ลิมิตสวิตช์ กด → รีเซ็ต E1=0 หรือ E1=-10P1-P4:<0/1>ยืนยัน Photo Sensor แล้ว (กดค้าง 2 วินาที){"TARGET_E1":25,...}ตารางการแสดงสินค้าจากกล้อง{"PRESS_STOP":1,...}Pi ส่ง auto stop เนื่องจากเซ็นเซอร์ความดันหลุด{"START_BLOCKED":1,...}Pi Block START เพราะเปิดทำงานฉุกเฉิน

11.3 ข้อความอนุกรม STM32

รูปแบบตัวอย่างจั๊มE1:<ค่า>E1 :32ตัวเข้ารหัส 1 (หัวบัลเล่ต์) = encoderCount/10E2:<ค่า>E2 :150ตัวเข้ารหัส 2 (แขนบังกี้) = encoder2Count/10พร้อมพร้อมส่งบูตครั้งเดียวมีอาวุธ / ไม่มีอาวุธติดอาวุธตอบคำสั่ง ARM / DISARMระบบเปิด/ ระบบปิดระบบ:เปิดตอบคำสั่ง START / STOPข้อผิดพลาด: ไม่ได้เปิดใช้งานข้อผิดพลาด: ไม่ได้เปิดใช้งานส่ง START โดยยังไม่มี ARMดีบีจี | อี1:... อี2:...DBG | E1 :5 E2 :10 | LS1 :0 ...รายงานสถานะการดีบักเมื่อค่าเปลี่ยน


12. พารามิเตอร์การกำหนดค่าระบบ

พารามิเตอร์ค่าหมายเหตุอัตราการอัปเดต1000 เฮิรตซ์อัตราการอัปเดต ros2_controlใช้ซิมไทม์จริงพบกับจาก GazeboPID ของ headcrane_Link10000.0 / 0.1 / 100.0ตัวควบคุมการหมุนข้อต่อarmcrane_Link PID10000.0 / 0.1 / 100.0ตัวควบคุมปริซึมร่วมPI_IP10.0.0.2Raspberry Pi (LAN) ที่ใช้ IPPI_PORT5001พอร์ต UDP ของ Piแบงแบงเอชเอช20 เฮิรตซ์ระบบ Bang-Bang Control Loopเวลาเดินทางด้วยจักรยาน11.0 วินาทีระยะเวลาเดินทาง 1 รอบหมดเวลาการกลับไปยังจุดเริ่มต้น30.0 วินาทีหมดเวลาสำหรับการกลับบ้านVALVE_REPEAT_INTERVAL1.0 วินาทีส่ง UP/DOWN_ON ซ้ำทุก 1 วินาทีระยะเวลาการทำซ้ำวาล์ว13.0 วินาทีส่ง UP/DOWN_ON ซ้ำนาน 13 วินาทีP4_หมดเวลา60.0 วินาทีหมดเวลา P4=1XCYCLE_CAM_TIMEOUT10.0 วินาทีหมดเวลารอ TARGET_E1 จาก PiXCYCLE_MAX_PASSES20จำนวนผ่านสูงสุดต่อสล็อตPHOTO_HOLD_MS (STM32)2000 มิลลิวินาทีเซ็นเซอร์รับภาพและอาหารแช่แข็ง 2 วินาทีระยะห่างสูงสุดขั้นต่ำ60 พิกเซลระยะระหว่างจุดต่ำสุดที่ 2 จุด


13. เท่าที่ (การแก้ไขปัญหา)

เธอสาเหตุที่ทำให้วิธีแก้ไขข้อผิดพลาด: ไม่ได้เปิดใช้งานยังไม่ได้ส่งคำสั่ง ARMส่ง ARM ก่อนอีกเลย STARTศาลาไม่รับวิถีตัวควบคุมไม่ทำงานros2 control list_controllers→ สถานะการตัดE1 ไม่อัปเดตสะพาน UDP ไม่ทำงานหรือ IP ผิดคำสั่ง udp_bridge.py TARGET_IPYOLO นำเสนอระบบบ่อยครั้งYOLO_CONFIDENCE ต่ำ หรือ แสงไม่พอYOLO_CONFIDENCE (0.35 → 0.5)เซ็นเซอร์รับภาพไม่กลัวค้างคืนเป็นเวลา 2 วินาทีรอบ 2 วินาทีหลังวัตถุถึงตำแหน่งอนุกรมไม่ได้เกี่ยวข้อง/dev/ttyUSB0 ไม่พบหรือมีสิทธิ์ไม่เพียงพอsudo usermod -aG dialout $USER→ รีบูตTARGET_E1 ไม่กลับมาPi ไม่รับ XCAP หรือการวิเคราะห์ใดๆโปรแกรมตัดต่อ Model_Fix.onnx และ RealSense USB 3.0สตาร์ทบล็อกบล็อก (PRESS)GPIO22 ไม่ทำงานกดกดกดก่อน STARTP4 หมดเวลาไม่ขึ้นถึงตำแหน่งบนภาพตัดต่อ Photo Sensor 4 และ Valve UPกล้องไม่เปิดRealSense ดำเนินการต่อหรือพอร์ต 5002 บล็อกบล็อกตัด USB 3.0 และพอร์ตไฟร์วอลล์ 5002ฉุกเฉินใช้งานอยู่ตลอดเวลาGPIO16 ลัดวงจรหรือสายไฟขาดตัดฮาร์ดแวร์ GPIO16 และเดินสายไฟโรสบริดจ์ไม่ได้อยู่ข้างๆท่าเรือ 9090 บล็อกsudo ufw allow 9090

13.1 คำสั่งดีบัก

ทุบตีros2 topic echo /crane_status        # สถานะเครน realtime
ros2 topic echo /joint_states        # joint position
ros2 control list_controllers        # controller status
screen /dev/ttyUSB0 115200           # serial output STM32 โดยตรง (Pi)
python3 -c "import onnxruntime; print(onnxruntime.__version__)"
python3 -c "import pyrealsense2; print('RealSense OK')"


CraneAI Extreme | ROS2 Humble • Gazebo • YOLOv8 • ONNX • RealSense D435 • Raspberry Pi 5 • STM32F103
