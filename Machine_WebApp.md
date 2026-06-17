# CraneAI — AI-Controlled Sand/Stone Machine
### เอกสารสรุปโครงสร้างและการใช้งาน Web App

**Stack:** Google AI Studio · React + Vite · ROS2 · Gemini API

---

## 1. ภาพรวมโครงการ (Project Overview)

CraneAI คือระบบควบคุมเครนแบบอัตโนมัติสำหรับการเตรียมหิน/ทรายในกระบวนการผลิตคอนกรีต พัฒนาด้วย Google AI Studio โดยใช้ AI (Gemini) ช่วยตรวจจับจุดตักวัสดุผ่านกล้อง Depth Camera แบบ Real-time

ระบบแบ่งออกเป็น 2 ส่วนหลัก:

- **Frontend (Web App)** — React + Vite + Tailwind CSS แสดงผลใน Browser
- **Backend (ROS2 Node)** — Python ควบคุม Hardware จริง (เครน + Encoder + Sensor)

---

## 2. ไฟล์ในโครงการ (Project Files)

| ชื่อไฟล์ | ประเภท | หน้าที่ |
|---|---|---|
| `src/App.tsx` | Frontend / React | ไฟล์หลักของ Web App — UI ทั้งหมด 7 หน้า, เชื่อม ROS2, รับ-ส่งคำสั่งเครน |
| `src/main.tsx` | Frontend | Entry point ของ React — mount `App.tsx` เข้า `index.html` |
| `src/index.css` | Frontend | Tailwind CSS base styles |
| `src/lib/utils.ts` | Frontend | Helper function สำหรับ className (`cn` utility) |
| `index.html` | Frontend | HTML root template — โหลด React และ ROSLIB script |
| `app.py` | Backend / ROS2 | ROS2 Node หลัก — รับคำสั่งจาก Web ผ่าน UDP, ควบคุม Encoder + Limit Switch + Digital Twin (Gazebo) |
| `crane_control_node.py` | Backend / ROS2 | ROS2 Node ควบคุมเครนเวอร์ชันแรก — BangBang Control, Homing, Cycle Auto |
| `crane_control_node_fixed.py` | Backend / ROS2 | เวอร์ชันแก้ไข/เสถียรกว่า — ปรับ Debounce, Limit Switch และ Brake logic |
| `vite.config.ts` | Config | ตั้งค่า Vite — inject `GEMINI_API_KEY`, alias path `@/` |
| `tsconfig.json` | Config | ตั้งค่า TypeScript compiler |
| `package.json` | Config | รายการ dependencies (React, Recharts, Roslib, Gemini SDK, Motion) |
| `.env.example` | Config | ตัวอย่างตั้งค่า `GEMINI_API_KEY` และ `APP_URL` |
| `metadata.json` | AI Studio | ข้อมูลโปรเจกต์สำหรับ Google AI Studio |
| `public/logo/` | Assets | โลโก้ KMUTNB และโลโก้โครงการ (`logo.png`, `logo2.png`) |
| `public/GALLERY/` | Assets | รูปภาพเครนจริง ~47 ภาพ แสดงในหน้า Gallery |
| `public/person/` | Assets | รูปสมาชิกทีม 7 คน (`person0`–`person6`) แสดงในหน้า Developers |

---

## 3. หน้าของ Web App (7 หน้า)

Web App มีทั้งหมด 7 หน้า เปลี่ยนด้วย Sidebar เมนูซ้ายมือ

| หน้า (View) | ชื่อเมนู | ทำอะไรได้บ้าง |
|---|---|---|
| `main` | OPERATION | หน้าหลักควบคุมเครน — ดูภาพจากกล้อง, กด Slot 1/2/3, Start/Stop, ดู Encoder & Sensor แบบ Real-time |
| `result` | RESULT | สถิติการทำงาน — ดู Log สำเร็จ/ล้มเหลว, กราฟ Sensor, นับ cycle, แสดงเวลาแบบ Real-time |
| `status` | STATUS | ตารางสถานะอุปกรณ์ทั้งหมด — Encoder 1/2, Photo Sensor 1-4, Limit Switch, Camera, Pressure |
| `info` | INFO | ข้อมูลโครงการ — อ่านรายละเอียด Vision, Feature Cards, ปุ่มไปหน้า Developers |
| `gallery` | GALLERY | แกลเลอรีภาพเครนจริง ~47 ภาพ — คลิกขยายภาพ, เลื่อนดูทั้งหมด |
| `3d` | 3D POINT CLOUD | แผนที่ความสูง Height Map แบบ Real-time — แสดง Point Cloud 3D จาก RealSense, Color Gradient ตามความสูงวัสดุ, RViz-style ใน Browser |
| `dev` | DEVELOPERS | หน้าทีมพัฒนา — รูปและชื่อสมาชิก 7 คน |

### รายละเอียดแต่ละหน้า

**หน้า 1 — OPERATION (main)**
- แสดง Video Stream จากกล้อง Intel RealSense (กรอก URL ใน Settings)
- แสดง Encoder Position, Sensor สถานะ (Photo 1-3) แบบ Live
- ปุ่ม SLOT 1 / SLOT 2 / SLOT 3 — ส่งคำสั่งไปยัง ROS2 ให้เครนเคลื่อนที่
- ปุ่ม HOME — เรียก Homing Sequence
- ปุ่ม START / STOP — เริ่ม/หยุดระบบ
- ปุ่ม Settings — ตั้งค่า WebSocket URL และ Camera URL
- รองรับภาษาไทย/อังกฤษ (toggle TH/EN)

**หน้า 2 — RESULT**
- Log รายการ Cycle สำเร็จ พร้อมเวลา
- Log รายการ Error/ล้มเหลว พร้อม Error Code
- นับ Cycle ทั้งหมด, Latency, เวลาระบบ

**หน้า 3 — STATUS**
- ตารางอุปกรณ์ 10 รายการ: Encoder1, Encoder2, Photo1-4, Limit Switch1-2, Camera, Pressure
- แสดง ON/OFF หรือค่าตัวเลขตาม Real-time data จาก ROS2
- บอกสถานะว่า Online/Offline แต่ละตัว

**หน้า 4 — INFO**
- อธิบาย Vision ของโครงการ (ปัญหาที่แก้, แนวทาง AI + Computer Vision)
- Feature Cards: Smart Vision, Automated Batching, Real-time Monitoring, Safety
- ปุ่มไปดูทีมพัฒนา

**หน้า 5 — GALLERY**
- กริดรูปภาพเครนจริงประมาณ 47 ภาพ
- คลิกที่รูปเพื่อขยายดู Fullscreen

**หน้า 6 — 3D POINT CLOUD (/3d)**
- แสดง Height Map แบบ 3D Point Cloud Real-time จากกล้อง Intel RealSense D435
- Color Gradient ตามระดับความสูงวัสดุ (น้ำเงิน = ต่ำ → แดง = สูง)
- รับข้อมูล Depth Grid ผ่าน WebSocket จาก Pi Bridge (`app.py`) — อัปเดตทุก ~50ms
- แสดงผล RViz-style ใน Browser — ใช้ข้อมูลชุดเดียวกับ RViz เพื่อ debug ได้พร้อมกัน
- รองรับ per-station calibration — สลับสถานี 1/2/3 เพื่อโหลดค่า height offset ที่ถูกต้องของแต่ละกอง

**หน้า 7 — DEVELOPERS**
- แสดงรูปและชื่อสมาชิกทีม 7 คน

---

## 4. Features ของ Web App

| Feature | รายละเอียด |
|---|---|
| ควบคุมเครนผ่านเว็บ | กดปุ่ม Slot / Home / Start / Stop — ส่งคำสั่งไป ROS2 แบบ Realtime ผ่าน WebSocket |
| ดูภาพกล้อง Live | แสดง Video Stream จาก Intel RealSense Depth Camera บนหน้าหลัก |
| Monitor Sensor | Encoder Position, Photo Sensor, Limit Switch, Pressure อัปเดตทุก ~50ms |
| ดู Log & สถิติ | บันทึก Cycle สำเร็จ/ล้มเหลว, กราฟ History, Latency, นับรอบการทำงาน |
| รองรับ 2 ภาษา | สลับไทย/อังกฤษได้ทุกหน้า ทุกข้อความ |
| ปรับ URL ได้ | ตั้งค่า ROSBridge WebSocket URL และ Camera Stream URL ผ่านหน้า Settings |
| Responsive Design | รองรับทั้ง Desktop (Sidebar ซ้าย) และ Mobile (Sidebar ซ่อน/เปิดได้) |
| Animation | ใช้ Framer Motion (motion library) ทำ Page Transition และ Fade-in Effect |
| Gallery ภาพเครนจริง | รูปภาพงานจริง 47 ภาพ คลิกดูแบบ Fullscreen ได้ |

---

## 5. วิธีใช้งาน Web App

### 5.1 เตรียมก่อนใช้

ต้องรัน **ROS2 + ROSBridge** บนเครื่องที่เชื่อมต่อกับเครนก่อนเริ่มใช้งาน

---

### 5.2 รันด้วย Antigravity IDE (Google AI-Native IDE)

Antigravity คือ IDE ของ Google ที่สร้างมาสำหรับ AI-assisted development โดยเฉพาะ — หน้าตาคล้าย VS Code แต่มี AI Agent (Gemini 3) ทำงานให้อัตโนมัติ สามารถใช้รันโปรเจกต์ CraneAI ได้โดยตรง

**ขั้นตอนการรัน CraneAI ใน Antigravity:**

1. เปิด Antigravity IDE — ดาวน์โหลดจาก `antigravity.google/download` แล้วติดตั้ง
2. กด **Open Folder** แล้วเลือก folder ที่แตก ZIP โปรเจกต์ CraneAI ไว้
3. เปิด Terminal ใน Antigravity (`Ctrl + ` ` หรือ View > Terminal) แล้วรัน:

```bash
npm install
```

4. พิมพ์ใน Terminal แล้วกด Enter — Antigravity จะเปิด Browser Preview อัตโนมัติ:

```bash
npm run dev
```

5. ถ้า Browser ไม่เปิดเอง ให้เปิดด้วยตนเองที่:

```
http://localhost:3000
```

6. ใช้ Agent Chat ใน Antigravity พิมพ์คำสั่งเป็นภาษาธรรมดา เช่น

```
แก้ไขสีปุ่ม SLOT ให้เป็นสีแดง
```

— Agent จะแก้ Code ให้อัตโนมัติ

**เคล็ดลับการใช้ Antigravity กับ CraneAI:**

- ใช้ Agent Chat ถามเกี่ยวกับ Code ได้เลย เช่น `"ไฟล์ App.tsx ทำอะไร?"` หรือ `"เพิ่ม Slot 4 ให้ด้วย"`
- Antigravity อ่านไฟล์ทั้งโปรเจกต์ได้ในครั้งเดียว (2M token context) — เหมาะสำหรับ Debug
- มี Browser Preview built-in — ทดสอบ UI ได้ทันทีโดยไม่ต้องออกจาก IDE
- รองรับ Multi-agent: ให้ Agent หนึ่งแก้ Frontend ขณะที่อีกตัวดู ROS2 Node

---

### 5.3 รันบน Google AI Studio (ออนไลน์ ไม่ต้องติดตั้งอะไร)

Google AI Studio คือแพลตฟอร์ม online ที่ใช้สร้างโปรเจกต์นี้ สามารถรัน Web App ได้ทันทีโดยไม่ต้องติดตั้ง Node.js หรือตั้งค่า API Key เอง

**ขั้นตอนการรัน CraneAI บน Google AI Studio:**

1. เปิด `aistudio.google.com` แล้วล็อกอินด้วย Google Account
2. กด **Import Project** แล้วอัปโหลดไฟล์ ZIP โปรเจกต์ CraneAI
3. AI Studio จะติดตั้ง dependencies และ inject `GEMINI_API_KEY` ให้อัตโนมัติ — ไม่ต้องตั้งค่าอะไรเพิ่ม
4. กดปุ่ม **Run** — Web App จะเปิดใน Preview panel ทางขวา
5. กด **Settings** ใน Web App ตั้ง WebSocket URL ของ ROSBridge แล้วกด **CONNECT**

**ข้อดีของการรันบน AI Studio:**

- ไม่ต้องติดตั้ง Node.js หรือ npm บนเครื่อง
- ไม่ต้องสร้างหรือจัดการ `GEMINI_API_KEY` เอง — inject อัตโนมัติ
- แก้ Code และเห็นผลได้ใน Preview แบบ Real-time
- สามารถ Deploy เป็น Public URL ให้คนอื่นเข้าได้ทันทีผ่านปุ่ม **Deploy**

---

## 6. Tools & Concepts ที่ใช้สร้าง Web App

| Tool / Library | หมวด | ใช้ทำอะไรในโปรเจกต์นี้ |
|---|---|---|
| React 19 | Frontend Framework | สร้าง UI ทั้งหมด แบ่งเป็น Component, จัดการ State ด้วย `useState`/`useRef`/`useMemo` |
| TypeScript | ภาษา | Type-safe code ป้องกัน bug จาก data type ผิดพลาด |
| Vite | Build Tool | Dev server รันเร็ว, Build production, inject ENV variable |
| Tailwind CSS 4 | CSS Framework | Styling ทั้งหมดผ่าน utility class โดยไม่เขียน CSS แยก |
| Framer Motion (`motion`) | Animation | Page transition, Fade-in, `AnimatePresence` เปลี่ยนหน้าแบบ smooth |
| ROSLIB.js | ROS Connector | เชื่อม Browser กับ ROS2 ผ่าน WebSocket (ROSBridge) — publish/subscribe topic |
| Lucide React | Icons | ไอคอน UI ทั้งหมด (Home, Settings, Users, BarChart ฯลฯ) |
| `@google/genai` (Gemini) | AI SDK | Gemini API — ติดตั้งไว้ใน `package.json` พร้อมใช้งาน (inject ผ่าน `vite.config`) |
| Google AI Studio | Dev Platform | แพลตฟอร์มที่ใช้สร้างและ Deploy โปรเจกต์นี้ (AI Studio App) |
| ROS2 | Robot OS Middleware | ควบคุม Hardware — Node รับ topic `/web_control_topic` จาก Web |
| Python 3 (`rclpy`) | Backend | เขียน ROS2 Node ใน Python — ควบคุม Motor, Encoder, Limit Switch ผ่าน UDP |
| UDP Socket | Network | ส่งคำสั่งจาก ROS2 Node ไปยัง Raspberry Pi ที่ต่อกับ Hardware |
| Gazebo (Digital Twin) | Simulation | จำลองโมเดล 3D เครนใน Gazebo ให้ขยับตาม Encoder จริง |
| Intel RealSense | Hardware | กล้อง Depth Camera ตรวจจับพิกัดจุดตักวัสดุด้วย AI |

---

## 7. โครงสร้างระบบ (Architecture)

| Layer | ส่วนประกอบ | สื่อสารผ่าน |
|---|---|---|
| User (Browser) | React Web App (`localhost:3000`) | กด UI → WebSocket |
| ROS2 Bridge | ROSBridge Server (`:9090`) | WebSocket → ROS2 Topic |
| ROS2 Node | `app.py` / `crane_control_node.py` | ROS Topic → UDP packet |
| Hardware | Raspberry Pi + Motor + Encoder | GPIO / Serial |
| Simulation | Gazebo Digital Twin | JointTrajectory topic |

```
Browser (React)
   │  WebSocket
   ▼
ROSBridge Server (:9090)
   │  ROS2 Topic
   ▼
ROS2 Node (app.py / crane_control_node.py)
   │  UDP packet
   ▼
Raspberry Pi → Motor + Encoder (GPIO / Serial)
   │
   └─→ Gazebo Digital Twin (JointTrajectory topic)
```

---

## 8. Height Map (ระบบแผนที่ความสูงวัสดุ)

### 8.1 ภาพรวม (Overview)

Height Map คือระบบสร้างแผนที่ความสูงแบบ Real-time ของกองหิน/ทรายในแต่ละสถานี โดยใช้ข้อมูล Point Cloud จากกล้อง Intel RealSense D435 แปลงเป็น 2D Grid แสดงระดับความลึก/ความสูงของวัสดุ ช่วยให้ระบบ AI เลือกจุดตักที่เหมาะสมที่สุดได้อัตโนมัติ

ข้อมูล Point Cloud ถูกส่งผ่าน UDP จาก `pointcloud_sender.py` บน ROS2 ไปยัง `pointcloud_receiver_v3.py` แล้วส่งต่อเป็น Depth Grid ไปยัง `app.py` (Pi Bridge) เพื่อแสดงผลบน Web App หน้า `/3d`

### 8.2 ไฟล์และการไหลของข้อมูล (Files & Data Flow)

| ไฟล์ | ตำแหน่ง | หน้าที่ |
|---|---|---|
| `pointcloud_sender.py` | ROS2 (PC) | Subscribe `/camera/depth/color/points` (PointCloud2), แปลงเป็น world-frame XYZ แล้ว project เป็น Depth Grid ส่งผ่าน UDP ไปยัง Pi Bridge |
| `pointcloud_receiver_v3.py` | ROS2 (PC) | รับ UDP Depth Grid จาก sender, คำนวณ per-station height calibration (`CALIB_PTS` / `STATION_COEFFS`), แปลงค่า Z-depth (`pz_m × 1000` mm) เป็น height map พร้อม fallback intrinsic กล้อง (424×240, fx/fy=380) |
| `app.py` (Pi Bridge) | Raspberry Pi | รับ Depth Grid ผ่าน `pc_recv_worker` thread (UDP), เก็บใน shared memory, broadcast ไปยัง Web App ผ่าน WebSocket (`/3d` endpoint) |
| Web App `/3d` View | Browser (React) | รับ Depth Grid ผ่าน WebSocket แสดงผลเป็น 3D Point Cloud / Height Map แบบ Real-time พร้อม Color Mapping ตามระดับความสูง |

### 8.3 Per-Station Height Calibration

แต่ละสถานี (Station 1–3) มีค่า Calibration แยกกัน เนื่องจากตำแหน่งติดตั้งกล้องและระยะห่างจากพื้นไม่เท่ากัน ระบบใช้ Polynomial Regression ปรับ offset ระหว่าง Raw Z-depth กับความสูงวัสดุจริง

| Parameter | Station 1 (ทราย) | Station 2 (หินเล็ก) | Station 3 (หินใหญ่) |
|---|---|---|---|
| กล้อง Resolution | 424 × 240 px | 424 × 240 px | 424 × 240 px |
| Focal Length (fx/fy) | 380 px (fallback) | 380 px (fallback) | 380 px (fallback) |
| Principal Point (cx, cy) | cx=212, cy=120 | cx=212, cy=120 | cx=212, cy=120 |
| Depth Method | `pz_m * 1000` (Z-depth โดยตรง ไม่ใช้ Euclidean distance) | เหมือนกัน | เหมือนกัน |

### 8.4 ขั้นตอนการประมวลผล (Processing Pipeline)

| Step | ขั้นตอน | รายละเอียด |
|---|---|---|
| 1 | Capture PointCloud2 | RealSense D435 publish `/camera/depth/color/points` ที่ 424×240 px ความถี่ ~30 fps |
| 2 | Project to World Frame XYZ | `pointcloud_sender_patched.py` แปลง camera frame → world frame แล้ว project XYZ ลงบน Depth Grid (2D array) |
| 3 | UDP Transmission | ส่ง Depth Grid แบบ binary packet ผ่าน UDP (low latency) จาก ROS2 PC ไปยัง Raspberry Pi |
| 4 | Height Calibration Apply | `pi_recv_worker` รับ packet, ใช้ `STATION_COEFFS` ของสถานีปัจจุบัน (สลับด้วย keyboard 1/2/3) ปรับค่าความสูงตาม `CALIB_PTS` polynomial |
| 5 | WebSocket Broadcast | `app.py` ส่ง Height Map (JSON หรือ binary) ผ่าน WebSocket ไปยัง Web App ทุก ~50ms |
| 6 | 3D Visualization (`/3d`) | Web App render Height Map เป็น 3D Point Cloud พร้อม Color Gradient (น้ำเงิน=ต่ำ, แดง=สูง) แสดง RViz-style ใน Browser |

### 8.5 หมายเหตุสำคัญ (Key Notes)

- **Depth Calculation:** ใช้ `pz_m * 1000` (Z-depth โดยตรงในหน่วย mm) ไม่ใช้ Euclidean distance เพื่อให้ค่าสอดคล้องกับระบบพิกัดกล้อง
- **Fallback Intrinsics:** หาก Point Cloud ไม่มีคอลัมน์ pixel u,v ระบบ fallback ไปใช้ค่า intrinsic ของ RealSense D435 ที่ 424×240 (fx=fy=380, cx=212, cy=120) เพื่อป้องกัน `IndexError`
- **Station Switching:** กด keyboard 1 / 2 / 3 ใน `pointcloud_receiver_v3.py` เพื่อสลับสถานีและโหลด `STATION_COEFFS` ชุดใหม่ โดยไม่ต้องรีสตาร์ท node
- **Thread Safety:** `pc_recv_worker` ทำงานใน background thread แยกต่างหาก ข้อมูลถูกเขียนลง shared buffer ก่อน WebSocket loop อ่านและ broadcast เพื่อป้องกัน race condition
- **RViz Parity:** หน้า `/3d` ของ Web App ออกแบบให้แสดงผล Point Cloud ตรงกับที่เห็นใน RViz โดยใช้ข้อมูล Depth Grid ชุดเดียวกัน ทำให้ทีมสามารถ debug ได้ทั้งจาก RViz และ Browser พร้อมกัน
