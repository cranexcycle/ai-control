# Ai-control


https://github.com/user-attachments/assets/91cf147a-84f3-49de-bd83-a24be2cd6cba


# 🏗️ ระบบควบคุมเครื่องโกยหินทรายสำหรับการผสมคอนกรีตด้วยปัญญาประดิษฐ์
> **AI-Powered Aggregate Scraper Control System for Concrete Batching Plants**

โปรเจกต์พัฒนาระบบอัตโนมัติเพื่อควบคุมเครื่องโกยหินและทรายในโรงงานผลิตคอนกรีตผสมเสร็จ โดยการผสานเทคโนโลยีการประมวลผลภาพ 3 มิติ (Computer Vision) และปัญญาประดิษฐ์ (Deep Learning) เพื่อทดแทนการทำงานแบบกึ่งอัตโนมัติ (Semi-Auto) และยกระดับสู่อุตสาหกรรม 4.0

---

## 🎯 วัตถุประสงค์และเป้าหมาย (Objectives)
* **🤖 ระบบอัตโนมัติ 100%:** ลดการพึ่งพาแรงงานมนุษย์ในการประเมินและควบคุมเครื่องโกย
* **📊 แม่นยำและปลอดภัย:** คำนวณปริมาตรและพิกัดการโกยหิน-ทรายได้อย่างเที่ยงตรง ลดความผิดพลาดในกระบวนการผลิต
* **⚡ เพิ่มประสิทธิภาพ:** ลดระยะเวลาการทำงาน (Cycle Time) และบริหารจัดการวัตถุดิบในสต็อกได้อย่างมีประสิทธิภาพ

---

## 🛠️ สถาปัตยกรรมระบบ (System Architecture)

ระบบแบ่งการทำงานออกเป็น 3 ส่วนหลัก (ตามโครงสร้างโค้ดใน Repository นี้):

┌───────────────────────────┐
│  Intel RealSense D435i    │
└─────────────┬─────────────┘
              │ (Depth Data & RGB Video)
              ▼
┌───────────────────────────┐         ┌───────────────────────────┐
│  Main Processing (Pi/ROS) │────────►│     STM32 Controller      │
│  - Object Detection (YOLO)│         │ (Motor & Actuator Control)│
│  - 3D Height Map          │         └───────────────────────────┘
└─────────────▲─────────────┘
              │ (Control & State Data)
              ▼
┌───────────────────────────┐
│      Web Application      │
│   (Flask / Monitoring)    │
└───────────────────────────┘
  
1. **Vision & AI Processing (`Main_pi.py`, `Main_ros.py`)**
   * รับข้อมูลภาพและระยะลึก (Depth) จากกล้อง **Intel RealSense D435i**
   * ใช้ **YOLO (Deep Learning)** ในการตรวจจับและจำแนกประเภทกองวัตถุดิบ (หิน/ทราย)
   * ประมวลผลสร้างแผนที่ความสูง 3 มิติ (3D Height Map) เพื่อคำนวณพิกัดจุดที่สูงที่สุดและปริมาตร

2. **Hardware Control (`stm32.py`)**
   * แปลงพิกัดทางกายภาพ (X, Y, Z) ที่ได้จาก AI ไปเป็นคำสั่งควบคุมมอเตอร์และระบบกลไกของเครื่องโกยหินทราย

3. **User Interface (`web_crane.py`)**
   * https://ais-pre-5gx6sfdolsljil3rgsh5lb-199159180132.asia-southeast1.run.app/
   * เว็บแอปพลิเคชันสำหรับแสดงผลการทำงานแบบ Real-time (Monitoring) ตรวจสอบสถานะระบบ และสั่งการทำงานในโหมด Manual ผ่านหน้าเว็บ

---
<img width="803" height="593" alt="image" src="https://github.com/user-attachments/assets/82e6f589-3f14-432b-acc6-134e30c1c943" /> 
<img width="859" height="464" alt="image" src="https://github.com/user-attachments/assets/5db50fc3-2d06-44b7-83f2-ee6720a74442" />



## 🚀 ฟีเจอร์เด่น (Key Features)
* **Real-time 3D Mapping:** ตรวจจับรูปทรงของกองวัตถุดิบที่เปลี่ยนแปลงตลอดเวลาได้อย่างแม่นยำ
* **Intelligent Path Planning:** คำนวณพิกัดการลงจอบโกยหิน-ทรายโดยอัตโนมัติจากจุดที่เหมาะสมที่สุด
* **Cross-Platform Integration:** เชื่อมโยงการทำงานระหว่าง Python, ROS (Robot Operating System), STM32 และ Web Interface อย่างไร้รอยต่อ

---

## 🗂️ โครงสร้างโค้ดในโปรเจกต์ (Repository Structure)
* `Main_pi.py` : โค้ดประมวลผลหลักบน Raspberry Pi (การรับค่าจากกล้องและ AI)
* `Main_ros.py` : ระบบควบคุมและจัดการโหนดการสื่อสารด้วย ROS
* `stm32.py` : ส่วนเชื่อมต่อและส่งคำสั่งระดับ Low-level ไปยังบอร์ด STM32
* `web_crane.py` : ระบบ Web Server (Flask/Dashboard) สำหรับมอนิเตอร์และควบคุมระยะไกล

---
💡 *พัฒนาโดยนักศึกษาคณะวิศวกรรมศาสตร์ มหาวิทยาลัยเทคโนโลยีพระจอมเกล้าพระนครเหนือ (KMUTNB)*
