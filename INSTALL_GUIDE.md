# 📖 ภาคผนวก ง: คู่มือการลงโปรแกรมและการตั้งค่าระบบ

---

## ง.1 ข้อกำหนดของระบบ (System Requirements)
ก่อนเริ่มต้นการติดตั้ง ตรวจสอบว่าอุปกรณ์ทุกชิ้นมีคุณสมบัติตามข้อกำหนดขั้นต่ำดังต่อไปนี้

### ตารางที่ ง.1: ข้อกำหนดคุณสมบัติของอุปกรณ์ (Hardware Requirements)

| อุปกรณ์ | ข้อกำหนดขั้นต่ำ | ที่แนะนำ | หมายเหตุ |
| :--- | :--- | :--- | :--- |
| **PC / Notebook** | Core i5 / Ryzen 5, RAM 8 GB | Core i7 / Ryzen 7, RAM 16 GB | สำหรับรัน ROS2 + Gazebo |
| **Raspberry Pi 5** | RAM 4 GB, microSD 32 GB | RAM 8 GB, microSD 64 GB (A2) | Ubuntu 22.04 LTS (64-bit) |
| **GPU (optional)** | — | NVIDIA GTX 1060 ขึ้นไป | เพิ่มความเร็ว YOLO inference |
| **Network** | Wi-Fi หรือ LAN | Gigabit LAN (สาย) | Latency < 10 ms แนะนำ |
| **Storage (PC)** | พื้นที่ว่าง 20 GB | SSD 50 GB ขึ้นไป | WSL2 + ROS2 + Dataset |

### ง.1.1 Software ที่ต้องการทั้งหมด

| โปรแกรม / Package | Version | ติดตั้งบน | หมายเหตุ |
| :--- | :--- | :--- | :--- |
| **Windows 10/11** | 64-bit | PC | เปิดใช้ Virtualization ใน BIOS |
| **WSL2 + Ubuntu 22.04 LTS** | 22.04 | PC | ผ่าน Microsoft Store หรือ PowerShell |
| **Python 3.x** | >= 3.10 | PC + Pi | python.org — ติ๊ก Add to PATH |
| **ROS2 Humble Hawksbill** | Humble | WSL2 + Pi | LTS support จนถึงปี 2027 |
| **Gazebo Classic** | 11.x | WSL2 | gazebo_ros2_control |
| **Node.js** | >= 18 LTS | WSL2 | สำหรับ Web Frontend |
| **Git** | latest | WSL2 + Pi | `sudo apt install git` |
| **Intel RealSense SDK 2.0** | 2.x | Pi | librealsense2 |
| **MATLAB (Train AI)** | R2023a+ | PC (Windows) | สำหรับ Train + Export .onnx |

### ง.1.2 Python Libraries ทั้งหมด

| Library | Version | ติดตั้งบน | หน้าที่ |
| :--- | :--- | :--- | :--- |
| **ultralytics** | >= 8.0 | Pi + WSL2 | YOLOv8 object detection (Safety Guard) |
| **onnxruntime** | >= 1.16 | Pi + WSL2 | รัน `Model_Fix.onnx` สำหรับ Peak Detection |
| **opencv-python** | >= 4.8 | Pi + WSL2 | Image processing, ROI, visualization |
| **numpy** | >= 1.24 | Pi + WSL2 | Array math, Depth map calculation |
| **pyrealsense2** | >= 2.54 | Pi | Intel RealSense D435i SDK |
| **flask** | >= 3.0 | Pi | MJPEG stream server port 5002 |
| **gpiozero** | >= 2.0 | Pi | GPIO: Button, LED, Sensor |
| **pyserial** | >= 3.5 | Pi | Serial UART to STM32 via FT232 |
| **scipy** | >= 1.11 | Pi + WSL2 | `find_peaks()`, signal processing |
| **rclpy** | (ROS2 built-in) | Pi + WSL2 | ROS2 Python client library |
| **std_msgs** | (ROS2 built-in) | Pi + WSL2 | ROS2 standard message types |
| **sensor_msgs** | (ROS2 built-in) | Pi + WSL2 | ROS2 image, joint state messages |

---

## ง.2 การติดตั้งโปรแกรมบน PC (Windows 10/11 + WSL2)

> ⚠️ **หมายเหตุ:** ต้องทำการ Restart Windows 1 ครั้ง หลังเปิดใช้ WSL2 กรุณาบันทึกงานทั้งหมดก่อนเริ่มขั้นตอน

### ง.2.1 ขั้นตอนที่ 1 — เปิดใช้งาน WSL2 บน Windows
เปิด PowerShell ในฐานะ Administrator จากนั้นพิมพ์คำสั่งดังนี้:

```bash
# ขั้นตอนที่ 1.1 — เปิดใช้งาน WSL2
wsl --install
wsl --set-default-version 2

# >>> ให้ทำการ Restart Windows แล้วเปิด PowerShell ใหม่ <<<

# ขั้นตอนที่ 1.2 — ติดตั้ง Ubuntu 22.04
wsl --install -d Ubuntu-22.04

# ขั้นตอนที่ 1.3 — ตรวจสอบผล (ต้องเห็น VERSION = 2)
wsl --list --verbose
ง.2.2 ขั้นตอนที่ 2 — ตั้งค่า Ubuntu ครั้งแรกหลังการติดตั้ง Ubuntu ให้รันคำสั่งต่อไปนี้ใน Ubuntu Terminal เพื่ออัปเดตระบบ:Bashsudo apt update && sudo apt upgrade -y
sudo apt install -y curl gnupg2 lsb-release build-essential git wget
ง.2.3 ขั้นตอนที่ 3 — ติดตั้ง Python 3.x บน Windows (สำหรับ udp_bridge.py)ดาวน์โหลด Python 3.x จาก python.org/downloadsสำคัญ: ต้องติ๊กเลือกที่ช่อง "Add Python to PATH" ก่อนกด Installตรวจสอบใน Command Prompt (CMD): python --versionง.2.4 ขั้นตอนที่ 4 — ติดตั้ง ROS2 Humble (ใน Ubuntu WSL2)ℹ️ ข้อควรระวัง: ทำใน Ubuntu Terminal เท่านั้น ไม่ใช่ Windows CMDBash# 4.1 ตั้งค่า Locale
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# 4.2 เพิ่ม ROS2 Repository
sudo curl -sSL [https://raw.githubusercontent.com/ros/rosdistro/master/ros.key](https://raw.githubusercontent.com/ros/rosdistro/master/ros.key) -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] [http://packages.ros.org/ros2/ubuntu](http://packages.ros.org/ros2/ubuntu) jammy main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt update

# 4.3 ติดตั้ง ROS2 Humble Desktop Full
sudo apt install -y ros-humble-desktop-full

# 4.4 เพิ่ม source ใน .bashrc
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc

# 4.5 ตรวจสอบ
ros2 --version
ง.2.5 ขั้นตอนที่ 5 — ติดตั้ง ROS2 Packages เพิ่มเติมBashsudo apt update && sudo apt install -y \
 ros-humble-ros2-control \
 ros-humble-gazebo-ros2-control \
 ros-humble-joint-trajectory-controller \
 ros-humble-joint-state-broadcaster \
 ros-humble-controller-manager \
 ros-humble-robot-state-publisher \
 ros-humble-joint-state-publisher-gui \
 ros-humble-rviz2 \
 ros-humble-rosbridge-suite \
 ros-humble-xacro \
 liburdfdom-tools
ง.2.6 ขั้นตอนที่ 6 — ติดตั้ง Python Libraries (Ubuntu WSL2)Bashpip install ultralytics opencv-python numpy scipy flask onnxruntime pyserial
ง.2.7 ขั้นตอนที่ 7 — สร้าง ROS2 Workspace และคัดลอกระบบควบคุมBashmkdir -p ~/dev_ws/ros2_ws/src
cd ~/dev_ws/ros2_ws
colcon build --symlink-install
source install/setup.bash

echo "source ~/dev_ws/ros2_ws/install/setup.bash" >> ~/.bashrc

# นำโฟลเดอร์แพ็กเกจระบบควบคุมรถเครน (crane_motor) ไปไว้ที่ ~/dev_ws/ros2_ws/src/
# จากนั้นสั่ง Build ใหม่
cd ~/dev_ws/ros2_ws
colcon build --symlink-install
ง.2.8 ขั้นตอนที่ 8 — ติดตั้ง Node.js สำหรับ Web FrontendBashcurl -fsSL [https://deb.nodesource.com/setup_18.x](https://deb.nodesource.com/setup_18.x) | sudo -E bash -
sudo apt install -y nodejs

# การรันระบบเว็บอินเตอร์เฟสควบคุม
cd ~/dev_ws/ai-control
npm install
npm run dev
ง.3 การติดตั้งโปรแกรมบน Raspberry Pi 5ทำบนฮาร์ดแวร์ Raspberry Pi 5 ที่ติดตั้งระบบปฏิบัติการ Ubuntu 22.04 LTS (64-bit) เรียบร้อยแล้วง.3.1 ติดตั้ง ROS2 Humble บน Raspberry Pi 5ให้รันชุดคำสั่งสำหรับติดตั้งตามขั้นตอนเดียวกับข้อ ง.2.4 บน Terminal ของตัว Piง.3.2 ติดตั้ง Python Libraries บน PiBashpip install ultralytics opencv-python numpy scipy pyrealsense2 flask onnxruntime gpiozero pyserial
ง.3.3 ติดตั้ง Intel RealSense SDK (librealsense2)Bashsudo apt-key adv --keyserver keyserver.ubuntu.com --recv-key F6E65AC044F831AC
sudo add-apt-repository "deb [https://librealsense.intel.com/Debian/apt-repo](https://librealsense.intel.com/Debian/apt-repo) $(lsb_release -cs) main"
sudo apt update
sudo apt install -y librealsense2-dkms librealsense2-utils librealsense2-dev
ง.3.4 ตั้งค่า Serial Permission สำหรับบอร์ดคอนโทรลเลอร์Bashsudo usermod -aG dialout $USER
sudo reboot
# หลังระบบรีบูต ตรวจสอบพอร์ตเชื่อมต่อด้วยคำสั่ง: ls /dev/ttyUSB*
ง.3.5 วิธีคัดลอกไฟล์โมเดล AI (.onnx) ไปยัง Piรันคำสั่งนี้บน Windows PowerShell หรือ Ubuntu PC เพื่อส่งไฟล์โมเดลไปยังบอร์ดผ่านโปรโตคอล SCP:Bashscp Model_Fix.onnx pi@10.0.0.2:~/dev_ws/
ง.4 การตั้งค่าเครือข่าย (Network Configuration)การสื่อสารส่งพิกัดและคำสั่งระหว่างสคริปต์ Main_ros.py (PC) และ Main_pi.py (Pi 5) ทำงานผ่านโปรโตคอล UDP จำเป็นต้องฟิกซ์หมายเลข Static IP ดังต่อไปนี้:ตารางที่ ง.2: การจัดสรรหมายเลข IP ภายในระบบอุปกรณ์IP AddressSubnet MaskหมายเหตุPC / Notebook (ROS PC)10.0.0.1255.255.255.0Static IP บนพอร์ต LANRaspberry Pi 510.0.0.2255.255.255.0Static IP บนอินเตอร์เฟส eth0ง.4.1 การแมปพอร์ตและตัวแปรในโค้ดโปรแกรมตรวจสอบพารามิเตอร์ภายในไฟล์สคริปต์ Python เพื่อให้แน่ใจว่าค่าเครือข่ายเชื่อมโยงหากันได้อย่างถูกต้อง:ไฟล์โปรแกรมตัวแปรค่าพารามิเตอร์ความหมายMain_ros.pyPI_IP'10.0.0.2'ชี้เป้าไปที่ IP ของบอร์ด Raspberry PiMain_ros.pyPI_PORT5001พอร์ตส่งข้อมูลคำสั่งไปยัง PiMain_ros.pyLISTEN_PORT5000พอร์ตรอรับสตรีมสถานะกลับจาก PiMain_pi.pyNOTEBOOK_IP'10.0.0.1'ชี้เป้ากลับมาที่ IP ของเครื่องคอมพิวเตอร์หลักง.5 รายการตรวจสอบการติดตั้ง (Verification Checklist)ลำดับทดสอบบนอุปกรณ์คำสั่งในการตรวจสอบผลลัพธ์ที่คาดหวังสถานะ (✓)1PC (WSL2)ros2 --versionros2 distro: humble[ ]2PC (WSL2)python3 -c "import onnxruntime; print('OK')"OK[ ]3PC (Windows CMD)ping 10.0.0.2ปรากฏข้อความ Reply from 10.0.0.2[ ]4Raspberry Pipython3 -c "import pyrealsense2; print('OK')"OK[ ]5Raspberry Pils /dev/ttyUSB*ปรากฏตำแหน่งไฟล์พอร์ต /dev/ttyUSB0[ ]
