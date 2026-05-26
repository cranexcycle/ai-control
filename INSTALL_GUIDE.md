markdown# 📖 คู่มือการลงโปรแกรมและการตั้งค่าระบบ

---

## ข้อกำหนดของระบบ (System Requirements)

ก่อนเริ่มต้นการติดตั้ง ตรวจสอบว่าอุปกรณ์ทุกชิ้นมีคุณสมบัติตามข้อกำหนดขั้นต่ำดังต่อไปนี้

### ตารางที่ ข้อกำหนดคุณสมบัติของอุปกรณ์ (Hardware Requirements)

| อุปกรณ์ | ข้อกำหนดขั้นต่ำ | ที่แนะนำ | หมายเหตุ |
| :--- | :--- | :--- | :--- |
| **PC / Notebook** | Core i5 / Ryzen 5, RAM 8 GB | Core i7 / Ryzen 7, RAM 16 GB | สำหรับรัน ROS2 + Gazebo |
| **Raspberry Pi 5** | RAM 4 GB, microSD 32 GB | RAM 8 GB, microSD 64 GB (A2) | Ubuntu 22.04 LTS (64-bit) |
| **GPU (optional)** | — | NVIDIA GTX 1060 ขึ้นไป | เพิ่มความเร็ว YOLO inference |
| **Network** | Wi-Fi หรือ LAN | Gigabit LAN (สาย) | Latency < 10 ms แนะนำ |
| **Storage (PC)** | พื้นที่ว่าง 20 GB | SSD 50 GB ขึ้นไป | WSL2 + ROS2 + Dataset |

### Software ที่ต้องการทั้งหมด

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

### Python Libraries ทั้งหมด

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

## การติดตั้งโปรแกรมบน PC (Windows 10/11 + WSL2)

> ⚠️ **หมายเหตุ:** ต้องทำการ Restart Windows 1 ครั้ง หลังเปิดใช้ WSL2 กรุณาบันทึกงานทั้งหมดก่อนเริ่มขั้นตอน

---

### ขั้นตอนที่ 1 — เปิดใช้งาน WSL2 บน Windows

เปิด PowerShell ในฐานะ **Administrator** จากนั้นพิมพ์คำสั่งดังนี้เพื่อเปิดใช้งานและติดตั้งระบบ:

```bash
wsl --install
wsl --set-default-version 2
```

หลังจากนั้นให้ทำการ **Restart Windows 1 ครั้ง** แล้วเปิด PowerShell ขึ้นมาอีกรอบเพื่อติดตั้ง Ubuntu 22.04:

```bash
wsl --install -d Ubuntu-22.04
```

เมื่อติดตั้งเสร็จ สามารถตรวจสอบเวอร์ชันของ WSL ได้ด้วยคำสั่งนี้ (ต้องแสดงเป็นเวอร์ชัน 2):

```bash
wsl --list --verbose
```

---

### ขั้นตอนที่ 2 — ตั้งค่า Ubuntu ครั้งแรก

หลังเปิดเข้าใช้งาน Ubuntu Terminal ครั้งแรก ให้สั่งอัปเดตระบบหลัก:

```bash
sudo apt update && sudo apt upgrade -y
```

จากนั้นพิมพ์คำสั่งนี้เพื่อลงแพ็กเกจเครื่องมือพื้นฐาน:

```bash
sudo apt install -y curl gnupg2 lsb-release build-essential git wget
```

---

### ขั้นตอนที่ 3 — ติดตั้ง Python 3.x บน Windows

ดาวน์โหลดตัวติดตั้งจากหน้าเว็บ [python.org/downloads](https://python.org/downloads)

> **สำคัญมาก:** ตอนกดติดตั้งต้องติ๊กถูกที่ช่อง **"Add Python to PATH"**

ตรวจสอบสถานะการติดตั้งใน Command Prompt (CMD) ของ Windows ด้วยคำสั่งนี้:

```bash
python --version
```

---

### ขั้นตอนที่ 4 — ติดตั้ง ROS2 Humble (ทำใน Ubuntu Terminal ของ WSL2)

ตั้งค่าโครงสร้างภาษาและ Locale ของระบบหลัก:

```bash
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
```

เพิ่มสิทธิ์และชุดจัดเก็บข้อมูล (Repository) ของ ROS2 เข้าสู่ระบบ:

```bash
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu jammy main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt update
```

สั่งติดตั้งแพ็กเกจ ROS2 Humble แบบตัวเต็ม (Desktop Full):

```bash
sudo apt install -y ros-humble-desktop-full
```

ตั้งค่าผูกสคริปต์สภาพแวดล้อมให้ทำงานอัตโนมัติทุกครั้งเมื่อเปิด Terminal:

```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

ทดสอบเรียกดูเวอร์ชันเพื่อยืนยันความถูกต้อง:

```bash
ros2 --version
```

---

### ขั้นตอนที่ 5 — ติดตั้ง ROS2 Packages เสริมที่จำเป็น

ติดตั้งเครื่องมือจำลอง Gazebo ระบบควบคุมมอเตอร์ Joint และเครื่องมือสร้างหุ่นยนต์:

```bash
sudo apt update && sudo apt install -y \
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
```

---

### ขั้นตอนที่ 6 — ติดตั้ง Python Libraries เสริมบน PC

ใช้ pip ติดตั้งโมดูล AI และส่วนประมวลผลข้อมูลลงใน Ubuntu WSL2:

```bash
pip install ultralytics opencv-python numpy scipy flask onnxruntime pyserial
```

---

### ขั้นตอนที่ 7 — สร้าง ROS2 Workspace และคอมไพล์แพ็กเกจควบคุมเครน

สร้างโฟลเดอร์สำหรับพัฒนาและสั่งทดสอบโครงสร้าง Workspace เริ่มต้น:

```bash
mkdir -p ~/dev_ws/ros2_ws/src
cd ~/dev_ws/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

เพิ่มสคริปต์ Workspace ให้โหลดอัตโนมัติในไฟล์ `.bashrc`:

```bash
echo "source ~/dev_ws/ros2_ws/install/setup.bash" >> ~/.bashrc
```

> 💡 **คำแนะนำ:** นำโฟลเดอร์แพ็กเกจการควบคุมเครน (`crane_motor`) ไปวางไว้ที่ `~/dev_ws/ros2_ws/src/` จากนั้นสั่ง Build ระบบใหม่อีกครั้ง:

```bash
cd ~/dev_ws/ros2_ws
colcon build --symlink-install
```

---

### ขั้นตอนที่ 8 — ติดตั้ง Node.js และเปิดใช้งานระบบ Web Frontend

ดาวน์โหลดและติดตั้งระบบรันไทม์ Node.js เวอร์ชัน 18:

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

เข้าไปยังโฟลเดอร์โครงการเพื่อดาวน์โหลดโมดูลและเริ่มทำงานเว็บมอนิเตอร์:

```bash
cd ~/dev_ws/ai-control
npm install
npm run dev
```

---

## การติดตั้งโปรแกรมบนบอร์ดเดี่ยว Raspberry Pi 5

ทำงานบนชุดคำสั่งคอมมานด์ไลน์ภายในตัวบอร์ด Raspberry Pi 5 (ระบบปฏิบัติการ Ubuntu 22.04 LTS)

---

### การลงระบบ ROS2 Humble

สำหรับบนบอร์ด Pi ให้รันชุดคำสั่งเพื่อติดตั้งตามลำดับแบบเดียวกับข้อ **ง.2.4** ทั้งหมดทุกขั้นตอน

---

### ติดตั้ง Python Libraries เสริมบนบอร์ดตัวรับ

สั่งติดตั้ง Library ทั้งหมด รวมถึงชุดคุมโมดูลกล้อง RealSense และขาเชื่อมต่อดิจิทัล (GPIO):

```bash
pip install ultralytics opencv-python numpy scipy pyrealsense2 flask onnxruntime gpiozero pyserial
```

---

### การติดตั้งคลังไลบรารีกล้อง Intel RealSense SDK

ทำการลงทะเบียนคีย์ความปลอดภัยและดึงคลังซอฟต์แวร์ของ Intel เข้าสู่ระบบ:

```bash
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-key F6E65AC044F831AC
sudo add-apt-repository "deb https://librealsense.intel.com/Debian/apt-repo $(lsb_release -cs) main"
sudo apt update
```

สั่งลงโปรแกรมอินเตอร์เฟสและไดรเวอร์ขับฮาร์ดแวร์ของกล้อง D435i:

```bash
sudo apt install -y librealsense2-dkms librealsense2-utils librealsense2-dev
```

---

### เปิดสิทธิ์การเข้าถึงพอร์ตเชื่อมต่อ Serial ขาออก

เพิ่มสิทธิ์ผู้ใช้งานให้สามารถรับส่งสัญญาณร่วมกับบอร์ด STM32 ได้:

```bash
sudo usermod -aG dialout $USER
sudo reboot
```

หลังระบบเปิดขึ้นมาใหม่ สามารถตรวจสอบพอร์ตสัญญาณที่เชื่อมต่อได้ด้วยคำสั่ง:

```bash
ls /dev/ttyUSB*
```

---

### การคัดลอกโมเดล AI ข้ามอุปกรณ์ผ่าน Network

เปิดใช้คำสั่งโอนย้ายไฟล์ผ่านเครือข่าย (SCP) บนเครื่อง PC หลักเพื่อโยนโมเดลไปที่บอร์ด Pi:

```bash
scp Model_Fix.onnx pi@10.0.0.2:~/dev_ws/
```

---

##การตั้งค่าเครือข่ายระบบ (Network Configuration)

### ตารางที่ การจัดสรรหมายเลขเครือข่ายภายในระบบ

| อุปกรณ์ | IP Address | Subnet Mask | หมายเหตุ |
| :--- | :--- | :--- | :--- |
| **PC / Notebook (ROS PC)** | 10.0.0.1 | 255.255.255.0 | กำหนดค่าแบบคงที่บนอุปกรณ์สาย LAN |
| **Raspberry Pi 5** | 10.0.0.2 | 255.255.255.0 | กำหนดค่าแบบคงที่บนพอร์ตอินเตอร์เฟส eth0 |

### ตารางตรวจสอบความสัมพันธ์ของตัวแปรเครือข่ายในโปรแกรม

| ไฟล์ซอร์สโค้ด | ตัวแปรภายใน | ค่าพารามิเตอร์ | วัตถุประสงค์การทำงาน |
| :--- | :--- | :--- | :--- |
| `Main_ros.py` | `PI_IP` | `'10.0.0.2'` | ชี้เป้าหมายเครือข่ายไปที่เครื่อง Raspberry Pi 5 |
| `Main_ros.py` | `PI_PORT` | `5001` | กำหนดพอร์ตรับสัญญาณปลายทางของตัว Pi |
| `Main_ros.py` | `LISTEN_PORT` | `5000` | กำหนดพอร์ตสำหรับดักฟังการตอบรับจากตัวเครน |
| `Main_pi.py` | `NOTEBOOK_IP` | `'10.0.0.1'` | ชี้พิกัดกลับมายังเครื่องประมวลผล PC หลัก |

---

## รายการตรวจสอบความพร้อมใช้งาน (Verification Checklist)

| ลำดับ | ตำแหน่งอุปกรณ์ | ชุดคำสั่งตรวจสอบ | ผลลัพธ์ที่ถูกต้อง | สถานะ (✓) |
| :---: | :--- | :--- | :--- | :---: |
| 1 | PC (WSL2) | `ros2 --version` | ros2 distro: humble | [ ] |
| 2 | PC (WSL2) | `python3 -c "import onnxruntime; print('OK')"` | OK | [ ] |
| 3 | PC (Windows CMD) | `ping 10.0.0.2` | มีการตอบรับสัญญาณจากไอพี 10.0.0.2 | [ ] |
| 4 | Raspberry Pi | `python3 -c "import pyrealsense2; print('OK')"` | OK | [ ] |
| 5 | Raspberry Pi | `ls /dev/ttyUSB*` | ระบบตรวจพบไฟล์พอร์ตอุปกรณ์ /dev/ttyUSB0 | [ ] |
