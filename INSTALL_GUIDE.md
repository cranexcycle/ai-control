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
เปิด PowerShell ในฐานะ Administrator จากนั้นพิมพ์คำสั่งดังนี้เพื่อเปิดใช้งานและติดตั้งระบบ:

```bash
wsl --install
wsl --set-default-version 2
