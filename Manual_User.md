# Manual_User.md — cranexcycle/ai-control
# ระบบควบคุมเครื่องโกยหินทรายสำหรับการผสมคอนกรีตด้วยปัญญาประดิษฐ์
# AI-Controlled Sand and Stone Preparing Machine for Concrete Batching System

---

## Table of Contents / สารบัญ

1. [System Overview / ภาพรวมระบบ](#1-system-overview--ภาพรวมระบบ)
2. [Hardware Requirements / อุปกรณ์ที่ต้องใช้](#2-hardware-requirements--อุปกรณ์ที่ต้องใช้)
3. [Network Configuration / การตั้งค่าเครือข่าย](#3-network-configuration--การตั้งค่าเครือข่าย)
4. [Raspberry Pi Bridge — `Main_pi.py`](#4-raspberry-pi-bridge--main_pipy)
5. [STM32 Firmware — `stm32.ino`](#5-stm32-firmware--stm32ino)
6. [Web Interface — `web_crane.py`](#6-web-interface--web_cranepy)
7. [GPIO Pin Reference / ตารางขา GPIO](#7-gpio-pin-reference--ตารางขา-gpio)
8. [Serial Commands / คำสั่ง Serial](#8-serial-commands--คำสั่ง-serial)
9. [UDP Message Format / รูปแบบข้อความ UDP](#9-udp-message-format--รูปแบบข้อความ-udp)
10. [Startup Procedure / ขั้นตอนเริ่มต้นระบบ](#10-startup-procedure--ขั้นตอนเริ่มต้นระบบ)
11. [Emergency & Safety Logic / ระบบความปลอดภัย](#11-emergency--safety-logic--ระบบความปลอดภัย)
12. [Troubleshooting / การแก้ไขปัญหา](#12-troubleshooting--การแก้ไขปัญหา)

---

## 1. System Overview / ภาพรวมระบบ

ระบบนี้ใช้ **Raspberry Pi 5** เป็นตัวกลางเชื่อมต่อระหว่างกล้อง RealSense, STM32, และ Notebook ควบคุม
โดยมีโมดูล AI วิเคราะห์ตำแหน่งกองหิน/ทรายผ่าน Depth Camera และส่งพิกัดเป้าหมายให้ STM32 ขับมอเตอร์แขนกล

```
[Notebook / Web UI]
        │  UDP (port 5000 ↔ 5001)
        ▼
[Raspberry Pi 5]  ←→  RealSense D4xx  (YOLO + ONNX Vision)
        │  Serial USB (115200 baud)
        ▼
[STM32]  →  Magnet / Valve / Encoder / Photo Sensor / Limit Switch
```

ไฟล์หลักในระบบ:

| File | Role |
|------|------|
| `Main_pi.py` | Pi Bridge — รับ/ส่ง UDP, อ่านกล้อง, วิเคราะห์ AI, ควบคุม GPIO |
| `stm32.ino` | STM32 Firmware — อ่าน Encoder, Sensor, รับคำสั่ง Serial |
| `Main_ros.py` | ROS2 Node — Digital Twin + ควบคุม Gazebo (แยกเล่ม) |
| `web_crane.py` | Web Interface — หน้าควบคุมผ่านเบราว์เซอร์ |

---

## 2. Hardware Requirements / อุปกรณ์ที่ต้องใช้

| อุปกรณ์ | รายละเอียด |
|---------|-----------|
| Raspberry Pi 5 | RAM ≥ 4GB, OS: Raspberry Pi OS 64-bit |
| Intel RealSense D4xx | เชื่อมต่อ USB 3.0 |
| STM32 (BluePill/Nucleo) | Flash ด้วย `stm32.ino`, เชื่อมต่อ `/dev/ttyUSB0` |
| Notebook/PC | Python 3.10+, เชื่อมต่อ LAN เดียวกัน |
| ไฟแสดงสถานะ (LED) | GPIO 23 (เขียว), 24 (แดง), 25 (น้ำเงิน) |

ติดตั้ง Python Dependencies บน Pi:

```bash
pip install opencv-python numpy pyrealsense2 ultralytics \
            onnxruntime flask pyserial gpiozero
```

---

## 3. Network Configuration / การตั้งค่าเครือข่าย

ทั้ง Pi และ Notebook ต้องอยู่ใน **subnet เดียวกัน** และตั้งค่า IP แบบ Static

| อุปกรณ์ | IP ที่ใช้ | Port |
|---------|----------|------|
| Notebook | `10.0.0.1` | 5000 (รับ) |
| Raspberry Pi | `10.0.0.2` | 5001 (รับ) |
| Flask Stream | Pi | 5002 (`/video_feed`) |

หากต้องการเปลี่ยน IP ให้แก้ไขในไฟล์ `Main_pi.py`:

```python
NOTEBOOK_IP   = "10.0.0.1"
NOTEBOOK_PORT = 5000
PI_PORT       = 5001
```

---

## 4. Raspberry Pi Bridge — `Main_pi.py`

### 4.1 การเริ่มต้นโปรแกรม

```bash
cd ~/ai-control
python3 Main_pi.py
```

โปรแกรมจะเปิดหน้าต่าง **"Live Camera"** และเริ่มรอคำสั่งจาก Notebook อัตโนมัติ

### 4.2 Keyboard Shortcuts (หน้าต่างกล้อง)

| ปุ่ม | ฟังก์ชัน |
|-----|---------|
| `Space` | จับภาพและเริ่มวิเคราะห์ตำแหน่ง AI |
| `d` | สลับโหมด Debug / Clean display |
| `1` / `2` / `3` | เลือก Station เป้าหมาย |
| `r` | รีเซ็ต Capture Round กลับ Round 1 |
| `q` | ออกจากโปรแกรม |

### 4.3 Capture Round System

ระบบวิเคราะห์ตำแหน่งกองแบ่งเป็น 3 รอบ เพื่อโกยจากจุดสูงสุดไปหาจุดที่เหลือ:

| Round | เกณฑ์ % ของยอดสูงสุด | หมายเหตุ |
|-------|---------------------|---------|
| 1st | 100% | จุดสูงที่สุด |
| 2nd | 65% | จุดรอง |
| 3rd | 50% | จุดที่เหลือ |

### 4.4 YOLO Safety Guard

ก่อนทุกการจับภาพวิเคราะห์ ระบบจะรัน YOLOv8n ตรวจสอบสิ่งกีดขวาง (คน, รถ, สัตว์) จำนวน 3 รอบ Vote
หากพบสิ่งกีดขวาง ≥ 2 ใน 3 รอบ จะหยุดกระบวนการและส่งสัญญาณเตือนทันที

Danger Classes ที่ตรวจจับ: person, bicycle, car, motorcycle, bus, truck, cat, dog

### 4.5 Flask Video Stream

ดู Live Feed ผ่านเบราว์เซอร์ได้ที่ `http://10.0.0.2:5002/video_feed`

---

## 5. STM32 Firmware — `stm32.ino`

### 5.1 การ Flash และเชื่อมต่อ

1. เปิด `stm32.ino` ใน Arduino IDE หรือ PlatformIO
2. Flash ลง STM32 Board
3. เชื่อมต่อ USB เข้า Pi ที่พอร์ต `/dev/ttyUSB0` Baud Rate 115200

### 5.2 Pin Assignment

| Pin | ฟังก์ชัน |
|-----|---------|
| `PA0` | Encoder 1 — Channel A |
| `PA1` | Encoder 1 — Channel B |
| `PB6` | Encoder 2 — Channel A |
| `PB7` | Encoder 2 — Channel B |
| `PB0` | Limit Switch 1 (LS1) |
| `PB1` | Limit Switch 2 (LS2) |
| `PB12` | Photo Sensor 1 (P1) |
| `PA4` | Photo Sensor 2 (P2) |
| `PA6` | Photo Sensor 3 (P3) |
| `PA7` | Photo Sensor 4 (P4) |
| `PB10` | Magnet 1 (MAG1) |
| `PB9` | Magnet 2 (MAG2) |
| `PA5` | Valve UP |
| `PB11` | Valve DOWN |
| `PB13` | Valve Brake 1 |
| `PB8` | Valve Brake 2 |
| `PA2` | Dir Valve |

> Output ทุกตัวเป็น **Active LOW** — LOW = เปิด, HIGH = ปิด

### 5.3 State Machine ของ STM32

STM32 มีลำดับการ Enable ดังนี้ — ต้องส่ง `ARM` ก่อนเสมอ มิฉะนั้น STM32 จะตอบ `ERR:NOT_ARMED`

```
DISARMED → [ARM] → ARMED → [START] → ENABLED (ทำงานได้)
                                ↓
                          [STOP / DISARM] → DISARMED
```

### 5.4 Photo Sensor Hold Logic

Photo Sensor ทุกตัวใช้ 2-Stage Debounce เพื่อป้องกัน false trigger:

Stage 1 (Fast) — นับสัญญาณซ้ำกัน 3 ครั้งติดต่อกัน ทุก 20ms จึงอัปเดต raw state
Stage 2 (Hold) — raw ต้องค้างเป็น 1 นาน ≥ 2 วินาที จึงยืนยัน confirmed = 1
หาก raw กลับเป็น 0 → confirmed = 0 ทันที โดยไม่ต้องรอ

---

## 6. Web Interface — `web_crane.py`

### 6.1 การรันและเข้าถึง

```bash
python3 web_crane.py
```

จากนั้นเปิดเบราว์เซอร์ไปที่ `http://10.0.0.1:PORT` ตามที่กำหนดในไฟล์

### 6.2 คำสั่งที่รองรับ (ผ่าน Web Topic)

| คำสั่ง | ผลลัพธ์ |
|-------|--------|
| `1` / `2` / `3` | สั่งโกย Slot 1/2/3 แบบ Sequence |
| `c1` / `c2` / `c3` | Run Cycle (Home → Move → Scoop) |
| `t1` / `t2` / `t3` | Target Mode (Home → Center → รอกล้อง → โกย) |
| `a` | Full Auto Mode (สแกนทุก Slot อัตโนมัติ) |
| `ready` | ปลดล็อค Manual Override |
| `stop` / `q` | Emergency Stop |

---

## 7. GPIO Pin Reference / ตารางขา GPIO

| GPIO (BCM) | ทิศทาง | ฟังก์ชัน |
|-----------|--------|---------|
| 17 | Input (Pull-up) | ปุ่ม START |
| 27 | Input (Pull-up) | ปุ่ม STOP |
| 22 | Input (Pull-up) | Press Sensor (ต้อง Active ก่อน START ได้) |
| 16 | Input (Pull-up) | Emergency Sensor (Active LOW = ฉุกเฉิน) |
| 23 | Output (Active LOW) | ไฟเขียว — ระบบทำงาน |
| 24 | Output (Active LOW) | ไฟแดง — หยุด / พร้อม |
| 25 | Output (Active LOW) | ไฟน้ำเงิน — Press Sensor Active |

---

## 8. Serial Commands / คำสั่ง Serial

Pi ส่งคำสั่งไปยัง STM32 ผ่าน Serial ที่ 115200 baud ลงท้ายทุกคำสั่งด้วย `\n`

| คำสั่ง | ฟังก์ชัน |
|-------|---------|
| `ARM` | เตรียมพร้อมระบบ |
| `DISARM` | ยกเลิกความพร้อม + ปิด Output ทั้งหมด |
| `START` | เริ่มระบบ (ต้อง ARM ก่อน) |
| `STOP` | หยุดระบบ + ปิด Output ทั้งหมด |
| `MAG1_ON` / `MAG1_OFF` | ควบคุมแม่เหล็กไฟฟ้า 1 |
| `MAG2_ON` / `MAG2_OFF` | ควบคุมแม่เหล็กไฟฟ้า 2 |
| `UP_ON` / `UP_OFF` | วาล์วยกขึ้น |
| `DOWN_ON` / `DOWN_OFF` | วาล์วกดลง |
| `B1_ON` / `B1_OFF` | เบรก 1 |
| `B2_ON` / `B2_OFF` | เบรก 2 |
| `DIR_ON` / `DIR_OFF` | วาล์วทิศทาง |

Serial Output ที่ STM32 ส่งกลับมา (Pi รับแล้วส่งต่อ UDP ไปยัง Notebook):

```
DBG | E1:12 E2:0 | LS1:0 LS2:1 | P1:0 P2:0 P3:1 P4:0
E1:12
LS1:1
P3:1
```

---

## 9. UDP Message Format / รูปแบบข้อความ UDP

### Pi → Notebook

สถานะปกติ:
```json
{"START":1,"STOP":0,"PRESS":1,"P1":0,"P2":0,"P3":1,"P4":0,
 "E1":12,"E2":0,"LS1":0,"LS2":0,"EMERGENCY":0,"TIME":1234567890.0}
```

ผลการวิเคราะห์ตำแหน่งเป้าหมาย:
```json
{"TARGET_E1":25,"STATION":2,"ROUND":1,"PEAK_PCT":100.0,"PEAK_XY":[320,240]}
```

YOLO พบสิ่งกีดขวาง:
```json
{"TARGET_E1":-1,"STATION":2,"ROUND":1,"DANGER_CLASSES":["person(0.87)"]}
```

Press Sensor หลุดระหว่างทำงาน:
```json
{"PRESS_STOP":1,"REASON":"GPIO22_LOST_WHILE_RUNNING","TIME":1234567890.0}
```

### Notebook → Pi

สั่ง X-Cycle Capture:
```json
{"XCAP":1,"SLOT":2,"ROUND":1,"PCT":100}
```

ส่งสถานะ YOLO จาก ROS กลับมา Pi:
```json
{"YOLO_DANGER":1,"CLASSES":["person(0.87)"]}
{"YOLO_DANGER":0}
```

Plain Text Commands ที่รองรับ:

| คำสั่ง | ความหมาย |
|-------|---------|
| `START` / `STOP` | เริ่ม / หยุดระบบ |
| `ARM` / `DISARM` | เตรียม / ยกเลิก STM32 |
| `1` / `2` / `3` | เลือก Station + trigger capture |
| `G:0` `G:1` `R:0` `R:1` `B:0` `B:1` | ควบคุมไฟ LED โดยตรง |

---

## 10. Startup Procedure / ขั้นตอนเริ่มต้นระบบ

1. เปิดไฟ STM32 และ Raspberry Pi
2. รอ Pi บูตเสร็จ ประมาณ 30 วินาที
3. รัน `Main_pi.py` บน Pi → ไฟแดงติด = ระบบพร้อมรอ START
4. ตรวจสอบ Press Sensor (GPIO22) ให้ Active → ไฟน้ำเงินติด = OK
5. กดปุ่ม START (GPIO17) หรือส่งคำสั่ง `START` จาก Notebook → ไฟเขียวติด = ระบบทำงาน
6. ใช้งานผ่าน Web Interface หรือส่งคำสั่ง UDP จาก Notebook ได้ตามปกติ

> ⚠️ หาก Press Sensor ไม่ Active → START จะถูกบล็อก
> ⚠️ หาก Emergency Sensor (GPIO16) หลุด → ระบบหยุดทันที ไฟแดงกะพริบ

---

## 11. Emergency & Safety Logic / ระบบความปลอดภัย

### Emergency Sensor (GPIO16)

สัญญาณ LOW (Active) = ปกติ
สัญญาณ HIGH (Inactive / หลุด) = ฉุกเฉิน → หยุดระบบทันที, ไฟแดงกะพริบ, บล็อก START
เมื่อสัญญาณกลับมาเป็น LOW → พร้อมรับ START ใหม่ได้

### Press Sensor (GPIO22)

ต้อง Active ตลอดเวลาขณะระบบ Running
หากสัญญาณหลุดระหว่าง Running → Auto Stop และส่ง `PRESS_STOP` ไปยัง Notebook ทันที

### YOLO Guard

ตรวจสอบก่อนทุกครั้งที่มีการ Capture หรือ Analyze
ใช้ Voting 3 รอบ Majority (≥ 2/3) → ยกเลิก Capture รอบนั้น
ไม่ได้หยุดการเคลื่อนที่ของแขนกล เพียงแค่ยกเลิกการวิเคราะห์

### STM32 Safety

ต้อง ARM ก่อน START เสมอ
คำสั่ง Output (MAG, Valve) จะทำงานเฉพาะเมื่อ `systemEnable && systemArmed` เท่านั้น
STOP หรือ DISARM → ปิด Output ทั้งหมดทันที

---

## 12. Troubleshooting / การแก้ไขปัญหา

| อาการ | สาเหตุที่เป็นไปได้ | วิธีแก้ |
|------|-------------------|--------|
| ไฟแดงกะพริบตั้งแต่เปิด | Emergency Sensor (GPIO16) ไม่ได้ต่อ หรือสายหลุด | ตรวจสอบ Wiring GPIO16 |
| กด START แล้วไม่มีอะไรเกิดขึ้น | Press Sensor ไม่ Active หรือ Emergency Active | ตรวจ GPIO22 และ GPIO16 |
| Serial Error / ไม่เจอ STM32 | `/dev/ttyUSB0` ผิด หรือไม่ได้ให้สิทธิ์ | รัน `sudo chmod 666 /dev/ttyUSB0` หรือแก้ `SERIAL_PORT` ในโค้ด |
| STM32 ตอบ `ERR:NOT_ARMED` | ส่ง `START` โดยไม่ได้ส่ง `ARM` ก่อน | ส่ง `ARM` ก่อนเสมอ |
| กล้องไม่เจอ / RealSense Error | USB ไม่ได้เสียบ USB 3.0 หรือ librealsense ไม่ถูก install | ตรวจสอบ USB Port และรัน `pip install pyrealsense2` |
| YOLO หยุดการทำงานตลอด | Object ค้างในเฟรม หรือ Confidence สูงเกินไป | ตรวจสอบพื้นที่ทำงาน หรือปรับค่า `YOLO_VOTE_CONF` ในโค้ด |
| Video Feed ไม่ขึ้น | Flask ยังไม่ Start หรือ Firewall บล็อก port 5002 | รอ 5 วินาทีแล้วลองใหม่ หรือตรวจ Firewall |
| ค่า E1 ไม่ตรงตำแหน่ง | Encoder offset ผิด | ให้ระบบชน Limit Switch LS1 เพื่อ Home ก่อนใช้งาน |

---

*cranexcycle / ai-control — Manual_User.md*
*AI-Controlled Sand and Stone Preparing Machine for Concrete Batching System*
