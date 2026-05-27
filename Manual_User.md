Manual_User.md — cranexcycle/ai-control
ระบบควบคุมเครื่องโกยหินทรายสำหรับการผสมคอนกรีตด้วยปัญญาประดิษฐ์
AI-Controlled Sand and Stone Preparing Machine for Concrete Batching System

Table of Contents / สารบัญ

System Overview / ภาพรวมระบบ
Hardware Requirements / อุปกรณ์ที่ต้องใช้
Network Configuration / การตั้งค่าเครือข่าย
Raspberry Pi Bridge — Main_pi.py
STM32 Firmware — stm32.ino
Web Interface — web_crane.py
GPIO Pin Reference / ตารางขา GPIO
Serial Commands / คำสั่ง Serial
UDP Message Format / รูปแบบข้อความ UDP
Startup Procedure / ขั้นตอนเริ่มต้นระบบ
Emergency & Safety Logic / ระบบความปลอดภัย
Troubleshooting / การแก้ไขปัญหา


1. System Overview / ภาพรวมระบบ
ระบบนี้ใช้ Raspberry Pi 5 เป็นตัวกลางเชื่อมต่อระหว่างกล้อง RealSense, STM32, และ Notebook ควบคุม
โดยมีโมดูล AI วิเคราะห์ตำแหน่งกองหิน/ทรายผ่าน Depth Camera และส่งพิกัดเป้าหมายให้ STM32 ขับมอเตอร์แขนกล
[Notebook / Web UI]
        │  UDP (port 5000 ↔ 5001)
        ▼
[Raspberry Pi 5]  ←→  RealSense D4xx  (YOLO + ONNX Vision)
        │  Serial USB (115200 baud)
        ▼
[STM32]  →  Magnet / Valve / Encoder / Photo Sensor / Limit Switch
ไฟล์หลักในระบบ:
FileRoleMain_pi.pyPi Bridge — รับ/ส่ง UDP, อ่านกล้อง, วิเคราะห์ AI, ควบคุม GPIOstm32.inoSTM32 Firmware — อ่าน Encoder, Sensor, รับคำสั่ง SerialMain_ros.pyROS2 Node — Digital Twin + ควบคุม Gazebo (แยกเล่ม)web_crane.pyWeb Interface — หน้าควบคุมผ่านเบราว์เซอร์

2. Hardware Requirements / อุปกรณ์ที่ต้องใช้
อุปกรณ์รายละเอียดRaspberry Pi 5RAM ≥ 4GB, OS: Raspberry Pi OS 64-bitIntel RealSense D4xxเชื่อมต่อ USB 3.0STM32 (BluePill/Nucleo)Flash ด้วย stm32.ino, เชื่อมต่อ /dev/ttyUSB0Notebook/PCPython 3.10+, เชื่อมต่อ LAN เดียวกันไฟแสดงสถานะ (LED)GPIO 23 (เขียว), 24 (แดง), 25 (น้ำเงิน)
ติดตั้ง Python Dependencies บน Pi:
bashpip install opencv-python numpy pyrealsense2 ultralytics \
            onnxruntime flask pyserial gpiozero

3. Network Configuration / การตั้งค่าเครือข่าย
ทั้ง Pi และ Notebook ต้องอยู่ใน subnet เดียวกัน และตั้งค่า IP แบบ Static
อุปกรณ์IP ที่ใช้PortNotebook10.0.0.15000 (รับ)Raspberry Pi10.0.0.25001 (รับ)Flask StreamPi5002 (/video_feed)
หากต้องการเปลี่ยน IP ให้แก้ไขในไฟล์ Main_pi.py:
pythonNOTEBOOK_IP   = "10.0.0.1"
NOTEBOOK_PORT = 5000
PI_PORT       = 5001

4. Raspberry Pi Bridge — Main_pi.py
4.1 การเริ่มต้นโปรแกรม
bashcd ~/ai-control
python3 Main_pi.py
โปรแกรมจะเปิดหน้าต่าง "Live Camera" และเริ่มรอคำสั่งจาก Notebook อัตโนมัติ
4.2 Keyboard Shortcuts (หน้าต่างกล้อง)
ปุ่มฟังก์ชันSpaceจับภาพและเริ่มวิเคราะห์ตำแหน่ง AIdสลับโหมด Debug / Clean display1 / 2 / 3เลือก Station เป้าหมายrรีเซ็ต Capture Round กลับ Round 1qออกจากโปรแกรม
4.3 Capture Round System
ระบบวิเคราะห์ตำแหน่งกองแบ่งเป็น 3 รอบ เพื่อโกยจากจุดสูงสุดไปหาจุดที่เหลือ:
Roundเกณฑ์ % ของยอดสูงสุดหมายเหตุ1st100%จุดสูงที่สุด2nd65%จุดรอง3rd50%จุดที่เหลือ
4.4 YOLO Safety Guard
ก่อนทุกการจับภาพวิเคราะห์ ระบบจะรัน YOLOv8n ตรวจสอบสิ่งกีดขวาง (คน, รถ, สัตว์) จำนวน 3 รอบ Vote
หากพบสิ่งกีดขวาง ≥ 2 ใน 3 รอบ จะหยุดกระบวนการและส่งสัญญาณเตือนทันที
Danger Classes ที่ตรวจจับ: person, bicycle, car, motorcycle, bus, truck, cat, dog
4.5 Flask Video Stream
ดู Live Feed ผ่านเบราว์เซอร์ได้ที่ http://10.0.0.2:5002/video_feed

5. STM32 Firmware — stm32.ino
5.1 การ Flash และเชื่อมต่อ

เปิด stm32.ino ใน Arduino IDE หรือ PlatformIO
Flash ลง STM32 Board
เชื่อมต่อ USB เข้า Pi ที่พอร์ต /dev/ttyUSB0 Baud Rate 115200

5.2 Pin Assignment
Pinฟังก์ชันPA0Encoder 1 — Channel APA1Encoder 1 — Channel BPB6Encoder 2 — Channel APB7Encoder 2 — Channel BPB0Limit Switch 1 (LS1)PB1Limit Switch 2 (LS2)PB12Photo Sensor 1 (P1)PA4Photo Sensor 2 (P2)PA6Photo Sensor 3 (P3)PA7Photo Sensor 4 (P4)PB10Magnet 1 (MAG1)PB9Magnet 2 (MAG2)PA5Valve UPPB11Valve DOWNPB13Valve Brake 1PB8Valve Brake 2PA2Dir Valve

Output ทุกตัวเป็น Active LOW — LOW = เปิด, HIGH = ปิด

5.3 State Machine ของ STM32
STM32 มีลำดับการ Enable ดังนี้ — ต้องส่ง ARM ก่อนเสมอ มิฉะนั้น STM32 จะตอบ ERR:NOT_ARMED
DISARMED → [ARM] → ARMED → [START] → ENABLED (ทำงานได้)
                                ↓
                          [STOP / DISARM] → DISARMED
5.4 Photo Sensor Hold Logic
Photo Sensor ทุกตัวใช้ 2-Stage Debounce เพื่อป้องกัน false trigger:
Stage 1 (Fast) — นับสัญญาณซ้ำกัน 3 ครั้งติดต่อกัน ทุก 20ms จึงอัปเดต raw state
Stage 2 (Hold) — raw ต้องค้างเป็น 1 นาน ≥ 2 วินาที จึงยืนยัน confirmed = 1
หาก raw กลับเป็น 0 → confirmed = 0 ทันที โดยไม่ต้องรอ

6. Web Interface — web_crane.py
6.1 การรันและเข้าถึง
bashpython3 web_crane.py
จากนั้นเปิดเบราว์เซอร์ไปที่ http://10.0.0.1:PORT ตามที่กำหนดในไฟล์
6.2 คำสั่งที่รองรับ (ผ่าน Web Topic)
คำสั่งผลลัพธ์1 / 2 / 3สั่งโกย Slot 1/2/3 แบบ Sequencec1 / c2 / c3Run Cycle (Home → Move → Scoop)t1 / t2 / t3Target Mode (Home → Center → รอกล้อง → โกย)aFull Auto Mode (สแกนทุก Slot อัตโนมัติ)readyปลดล็อค Manual Overridestop / qEmergency Stop

7. GPIO Pin Reference / ตารางขา GPIO
GPIO (BCM)ทิศทางฟังก์ชัน17Input (Pull-up)ปุ่ม START27Input (Pull-up)ปุ่ม STOP22Input (Pull-up)Press Sensor (ต้อง Active ก่อน START ได้)16Input (Pull-up)Emergency Sensor (Active LOW = ฉุกเฉิน)23Output (Active LOW)ไฟเขียว — ระบบทำงาน24Output (Active LOW)ไฟแดง — หยุด / พร้อม25Output (Active LOW)ไฟน้ำเงิน — Press Sensor Active

8. Serial Commands / คำสั่ง Serial
Pi ส่งคำสั่งไปยัง STM32 ผ่าน Serial ที่ 115200 baud ลงท้ายทุกคำสั่งด้วย \n
คำสั่งฟังก์ชันARMเตรียมพร้อมระบบDISARMยกเลิกความพร้อม + ปิด Output ทั้งหมดSTARTเริ่มระบบ (ต้อง ARM ก่อน)STOPหยุดระบบ + ปิด Output ทั้งหมดMAG1_ON / MAG1_OFFควบคุมแม่เหล็กไฟฟ้า 1MAG2_ON / MAG2_OFFควบคุมแม่เหล็กไฟฟ้า 2UP_ON / UP_OFFวาล์วยกขึ้นDOWN_ON / DOWN_OFFวาล์วกดลงB1_ON / B1_OFFเบรก 1B2_ON / B2_OFFเบรก 2DIR_ON / DIR_OFFวาล์วทิศทาง
Serial Output ที่ STM32 ส่งกลับมา (Pi รับแล้วส่งต่อ UDP ไปยัง Notebook):
DBG | E1:12 E2:0 | LS1:0 LS2:1 | P1:0 P2:0 P3:1 P4:0
E1:12
LS1:1
P3:1

9. UDP Message Format / รูปแบบข้อความ UDP
Pi → Notebook
สถานะปกติ:
json{"START":1,"STOP":0,"PRESS":1,"P1":0,"P2":0,"P3":1,"P4":0,
 "E1":12,"E2":0,"LS1":0,"LS2":0,"EMERGENCY":0,"TIME":1234567890.0}
ผลการวิเคราะห์ตำแหน่งเป้าหมาย:
json{"TARGET_E1":25,"STATION":2,"ROUND":1,"PEAK_PCT":100.0,"PEAK_XY":[320,240]}
YOLO พบสิ่งกีดขวาง:
json{"TARGET_E1":-1,"STATION":2,"ROUND":1,"DANGER_CLASSES":["person(0.87)"]}
Press Sensor หลุดระหว่างทำงาน:
json{"PRESS_STOP":1,"REASON":"GPIO22_LOST_WHILE_RUNNING","TIME":1234567890.0}
Notebook → Pi
สั่ง X-Cycle Capture:
json{"XCAP":1,"SLOT":2,"ROUND":1,"PCT":100}
ส่งสถานะ YOLO จาก ROS กลับมา Pi:
json{"YOLO_DANGER":1,"CLASSES":["person(0.87)"]}
{"YOLO_DANGER":0}
Plain Text Commands ที่รองรับ:
คำสั่งความหมายSTART / STOPเริ่ม / หยุดระบบARM / DISARMเตรียม / ยกเลิก STM321 / 2 / 3เลือก Station + trigger captureG:0 G:1 R:0 R:1 B:0 B:1ควบคุมไฟ LED โดยตรง

10. Startup Procedure / ขั้นตอนเริ่มต้นระบบ

เปิดไฟ STM32 และ Raspberry Pi
รอ Pi บูตเสร็จ ประมาณ 30 วินาที
รัน Main_pi.py บน Pi → ไฟแดงติด = ระบบพร้อมรอ START
ตรวจสอบ Press Sensor (GPIO22) ให้ Active → ไฟน้ำเงินติด = OK
กดปุ่ม START (GPIO17) หรือส่งคำสั่ง START จาก Notebook → ไฟเขียวติด = ระบบทำงาน
ใช้งานผ่าน Web Interface หรือส่งคำสั่ง UDP จาก Notebook ได้ตามปกติ


⚠️ หาก Press Sensor ไม่ Active → START จะถูกบล็อก
⚠️ หาก Emergency Sensor (GPIO16) หลุด → ระบบหยุดทันที ไฟแดงกะพริบ


11. Emergency & Safety Logic / ระบบความปลอดภัย
Emergency Sensor (GPIO16)
สัญญาณ LOW (Active) = ปกติ
สัญญาณ HIGH (Inactive / หลุด) = ฉุกเฉิน → หยุดระบบทันที, ไฟแดงกะพริบ, บล็อก START
เมื่อสัญญาณกลับมาเป็น LOW → พร้อมรับ START ใหม่ได้
Press Sensor (GPIO22)
ต้อง Active ตลอดเวลาขณะระบบ Running
หากสัญญาณหลุดระหว่าง Running → Auto Stop และส่ง PRESS_STOP ไปยัง Notebook ทันที
YOLO Guard
ตรวจสอบก่อนทุกครั้งที่มีการ Capture หรือ Analyze
ใช้ Voting 3 รอบ Majority (≥ 2/3) → ยกเลิก Capture รอบนั้น
ไม่ได้หยุดการเคลื่อนที่ของแขนกล เพียงแค่ยกเลิกการวิเคราะห์
STM32 Safety
ต้อง ARM ก่อน START เสมอ
คำสั่ง Output (MAG, Valve) จะทำงานเฉพาะเมื่อ systemEnable && systemArmed เท่านั้น
STOP หรือ DISARM → ปิด Output ทั้งหมดทันที

12. Troubleshooting / การแก้ไขปัญหา
อาการสาเหตุที่เป็นไปได้วิธีแก้ไฟแดงกะพริบตั้งแต่เปิดEmergency Sensor (GPIO16) ไม่ได้ต่อ หรือสายหลุดตรวจสอบ Wiring GPIO16กด START แล้วไม่มีอะไรเกิดขึ้นPress Sensor ไม่ Active หรือ Emergency Activeตรวจ GPIO22 และ GPIO16Serial Error / ไม่เจอ STM32/dev/ttyUSB0 ผิด หรือไม่ได้ให้สิทธิ์รัน sudo chmod 666 /dev/ttyUSB0 หรือแก้ SERIAL_PORT ในโค้ดSTM32 ตอบ ERR:NOT_ARMEDส่ง START โดยไม่ได้ส่ง ARM ก่อนส่ง ARM ก่อนเสมอกล้องไม่เจอ / RealSense ErrorUSB ไม่ได้เสียบ USB 3.0 หรือ librealsense ไม่ถูก installตรวจสอบ USB Port และรัน pip install pyrealsense2YOLO หยุดการทำงานตลอดObject ค้างในเฟรม หรือ Confidence สูงเกินไปตรวจสอบพื้นที่ทำงาน หรือปรับค่า YOLO_VOTE_CONF ในโค้ดVideo Feed ไม่ขึ้นFlask ยังไม่ Start หรือ Firewall บล็อก port 5002รอ 5 วินาทีแล้วลองใหม่ หรือตรวจ Firewallค่า E1 ไม่ตรงตำแหน่งEncoder offset ผิดให้ระบบชน Limit Switch LS1 เพื่อ Home ก่อนใช้งาน

cranexcycle / ai-control — Manual_User.md
AI-Controlled Sand and Stone Preparing Machine for Concrete Batching System
