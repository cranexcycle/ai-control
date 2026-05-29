import React, { useEffect, useState, useRef, useMemo } from 'react';
import * as ROSLIB from 'roslib';
import { cn } from './lib/utils';
import { Wifi, WifiOff, AlertCircle, Activity, PlugZap, Users, ChevronLeft, Home, Layout, FileText, Plus, Search, Play, Image, Menu, Cpu, CheckCircle, XCircle, Clock, Timer, AlertTriangle, Sliders } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ReferenceLine,
  AreaChart,
  Area
} from 'recharts';

interface CraneStatus {
  p1: number;
  p2: number;
  p3: number;
  p4: number;           // เพิ่ม
  is_system_ready: boolean;
  is_moving: boolean;
  cycle_running: boolean;
  last_bungkee_pos: number;
  current_head_deg: number;
  yolo_danger: boolean;     // เพิ่ม
  pi_emergency: boolean;    // เพิ่ม
  press_lost: boolean;      // เพิ่ม
  limit1: number;           // เพิ่ม
  limit2: number;           // เพิ่ม
  pressure: number;         // เพิ่ม
  [key: string]: any;
}

export default function App() {
  const [ros, setRos] = useState<ROSLIB.Ros | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDesktop, setIsDesktop] = useState(window.innerWidth >= 1280);

  useEffect(() => {
    const handleResize = () => setIsDesktop(window.innerWidth >= 1280);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  const [wsUrl, setWsUrl] = useState('ws://localhost:9090');
  const [videoUrl, setVideoUrl] = useState(() => {
    const saved = localStorage.getItem('crane_video_url');
    if (!saved || saved.includes('1.102') || saved.includes('1.109')) return 'http://192.168.1.115:5002/video_feed';
    return saved;
  });
  const [showSettings, setShowSettings] = useState(false);
  const [view, setView] = useState<'main' | 'info' | 'result' | 'status' | 'gallery' | 'dev'>('main');
  const [lang, setLang] = useState<'th' | 'en'>('en');
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  // Successful operations logs
  const [successLogs, setSuccessLogs] = useState<{ id: number; time: string; msgTh: string; msgEn: string }[]>([]);

  // Failed/Error/Timer states
  const [failedLogs, setFailedLogs] = useState<{ id: number; time: string; msgTh: string; msgEn: string; code: string }[]>([]);

  const labels = {
    th: {
      status: "สถานะ",
      project_info: "ข้อมูลโครงการ",
      back: "กลับ",
      change_lang: "เปลี่ยนภาษา",
      connect: "เชื่อมต่อ",
      disconnect: "ตัดการเชื่อมต่อ",
      ready: "ระบบพร้อม",
      not_ready: "รอดำเนินการ",
      moving: "กำลังเคลื่อนที่",
      idle: "หยุด",
      full: "เต็ม",
      empty: "ว่าง",
      text_alarm: "ข้อความ / แจ้งเตือน",
      vision: "ความคาดหวังของโครงการ",
      vision_desc: "ในอุตสาหกรรมการผลิตปูนซีเมนต์หรือคอนกรีตสำเร็จรูป กระบวนการจัดการและควบคุมการขนย้ายวัตถุดิบจำพวกหินและทรายเข้าสู่ระบบผสม ถือเป็นขั้นตอนวิกฤตที่มีผลโดยตรงต่อความแม่นยำของสูตรผสมและคุณภาพของผลิตภัณฑ์ปลายทาง ปัจจุบันสถานประกอบการส่วนใหญ่ยังคงอาศัยแรงงานมนุษย์ในการควบคุมเครื่องจักรแบบแมนนวล (Manual Control) ซึ่งมักประสบปัญหาด้านความคลาดเคลื่อนของปริมาณวัตถุดิบ ความไม่สม่ำเสมอในการปฏิบัติงานอันเกิดจากความเหนื่อยล้า รวมถึงความเสี่ยงต่ออุบัติเหตุในพื้นที่ปฏิบัติงาน\n\nด้วยเหตุนี้ การนำเทคโนโลยีปัญญาประดิษฐ์ (Artificial Intelligence: AI) ร่วมกับระบบวิสัยทัศน์คอมพิวเตอร์ (Computer Vision) เข้ามาประยุกต์ใช้จึงเป็นแนวทางสำคัญในการเปลี่ยนผ่านสู่ระบบอุตสาหกรรมอัจฉริยะ โดยการใช้กล้องตรวจจับความลึก (Depth Camera) ร่วมกับอัลกอริทึมการเรียนรู้เชิงลึก (Deep Learning) จะช่วยให้ระบบสามารถวิเคราะห์สภาพแวดล้อมได้แบบเรียลไทม์ สามารถคำนวณจุดตักวัสดุที่เหมาะสมที่สุด (Peak Detection) และตรวจจับสิ่งกีดขวางเพื่อความปลอดภัย ซึ่งไม่เพียงแต่ช่วยเพิ่มประสิทธิภาพและแผนการทำงานที่แม่นยำ แต่ยังช่วยลดต้นทุนด้านแรงงานและยกระดับมาตรฐานความปลอดภัยในพื้นที่ทำงานได้อย่างยั่งยืน",
      features: "คุณสมบัติเด่น",
      team: "ทีมผู้พัฒนา",
      return: "กลับหน้าหลัก",
      display: "จอแสดงผล",
      waiting_signal: "กำลังรอสัญญาณภาพ...",
      architecture: "สถาปัตยกรรมระบบ",
      dev_label: "นักพัฒนา",
      inst_label: "สถาบัน",
      inst_value: "วิศวกรรมระบบอุตสาหกรรม มจพ.",
      version: "เวอร์ชัน",
      gallery: "บรรยากาศหน้างาน",
      search_similar: "ค้นหาสิ่งที่คล้ายกัน",
      developer_page: "คณะผู้ร่วมอุดมการณ์"
    },
    en: {
      status: "STATUS",
      project_info: "Information",
      back: "Back",
      change_lang: "Change Language",
      connect: "CONNECT",
      disconnect: "DISCONNECT",
      ready: "System Ready",
      not_ready: "Pending",
      moving: "Moving",
      idle: "Idle",
      full: "FULL",
      empty: "EMPTY",
      text_alarm: "TEXT / ALARM",
      vision: "The Vision",
      vision_desc: "In the cement and precast concrete manufacturing industry, managing and controlling the transport of raw materials like stone and sand into mixing systems is a critical process affecting mixture accuracy and product quality. Currently, most facilities rely on human labor for manual control, leading to potential inaccuracies, operational inconsistencies due to fatigue, and safety risks.\n\nApplying Artificial Intelligence (AI) and Computer Vision is key to transitioning toward smart industry. Using Depth Cameras with Deep Learning algorithms enables real-time environment analysis, optimal scoop point calculation (Peak Detection), and obstacle detection. This enhances efficiency, ensures precision, reduces labor costs, and sustainably elevates workplace safety standards.",
      features: "Key Features",
      team: "Development Team",
      return: "HOME",
      display: "DISPLAY",
      waiting_signal: "Waiting for camera signal...",
      architecture: "System Architecture",
      dev_label: "Developer",
      inst_label: "Institution",
      inst_value: "King Mongkut's University of Technology North Bangkok",
      version: "Version",
      gallery: "Field Gallery",
      search_similar: "Search Similar",
      developer_page: "DEVELOPERS"
    }
  } as const;

  const t = labels[lang];

  const [currentTime, setCurrentTime] = useState(new Date().toLocaleString('en-US'));
  
  const [craneState, setCraneState] = useState<CraneStatus>({
    p1: 0, p2: 0, p3: 0, p4: 0,
    is_system_ready: false,
    is_moving: false,
    cycle_running: false,
    last_bungkee_pos: 0.0,
    current_head_deg: 0.0,
    yolo_danger: false,
    pi_emergency: false,
    press_lost: false,
    limit1: 0,
    limit2: 0,
    pressure: 0,
  });

  const [lastSent, setLastSent] = useState<string | null>(null);
  const [lastReceived, setLastReceived] = useState<string | null>(null);
  const [lastReceivedTime, setLastReceivedTime] = useState<number | null>(null);
  const [latency, setLatency] = useState<number | null>(null);
  const [posHistory, setPosHistory] = useState<{ x: number, y: number, time: number }[]>([]);

  // ── NEW: summary state ──────────────────────────────────────────────
  const [lastSummary, setLastSummary] = useState<string | null>(null);
  const [showSummary, setShowSummary] = useState(false);

  const webControlTopic = useRef<ROSLIB.Topic | null>(null);
  // ── จุดที่ 1: counter สำหรับ ID ของ log ที่รับจาก ROS ──────────────
  const logIdCounter = useRef(100);

  useEffect(() => {
    document.title = "AI-Controlled Sand/Stone Machine";
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      const locale = view === 'main' ? 'en-US' : (lang === 'th' ? 'th-TH' : 'en-US');
      setCurrentTime(new Date().toLocaleString(locale, { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
      }));
    }, 1000);
    return () => clearInterval(timer);
  }, [view, lang]);

  // Persist settings
  useEffect(() => {
    localStorage.setItem('crane_ws_url', wsUrl);
  }, [wsUrl]);

  useEffect(() => {
    localStorage.setItem('crane_video_url', videoUrl);
  }, [videoUrl]);

  // No auto-connect on load - user must click CONNECT manually to start telemetry

  // Clear state when disconnected
  const resetState = () => {
    setCraneState({
      p1: 0, p2: 0, p3: 0, p4: 0,
      is_system_ready: false,
      is_moving: false,
      cycle_running: false,
      last_bungkee_pos: 0.0,
      current_head_deg: 0.0,
      yolo_danger: false,
      pi_emergency: false,
      press_lost: false,
      limit1: 0,
      limit2: 0,
      pressure: 0,
    });
    setLastReceived('NO DATA INCOMING...');
    setLastReceivedTime(null);
  };

  // Get real-time device values dynamically from actual topic stream
  const getDeviceValue = (key: string) => {
    if (!connected) return '--- N/A ---';
    switch(key) {
      case 'encoder1': {
        // ดึง E1 raw ticks โดยตรง (Python ส่งมาเป็น key "e1" หลัง normalize)
        const ticks = craneState.e1 ?? craneState.encoder1 ?? craneState.current_head_deg ?? 0;
        return `${Math.round(ticks)} ticks`;
      }
      case 'encoder2': {
        const ticks = craneState.e2 ?? craneState.encoder2 ?? craneState.last_bungkee_pos ?? 0;
        return `${Math.round(ticks)} ticks`;
      }
      case 'photo1': {
        const isHigh = craneState.photo1 === 1 || craneState.p1 === 1 || craneState.photo1 === true || craneState.p1 === true;
        return isHigh ? 'HIGH (Blocked)' : 'LOW (Clear)';
      }
      case 'photo2': {
        const isHigh = craneState.photo2 === 1 || craneState.p2 === 1 || craneState.photo2 === true || craneState.p2 === true;
        return isHigh ? 'HIGH (Blocked)' : 'LOW (Clear)';
      }
      case 'photo3': {
        const isHigh = craneState.photo3 === 1 || craneState.p3 === 1 || craneState.photo3 === true || craneState.p3 === true;
        return isHigh ? 'HIGH (Blocked)' : 'LOW (Clear)';
      }
      case 'photo4': {
        const isHigh = craneState.photo4 === 1 || craneState.p4 === 1 || craneState.photo4 === true || craneState.p4 === true;
        return isHigh ? 'HIGH (Blocked)' : 'LOW (Clear)';
      }
      case 'limit1': {
        const isTrig = craneState.limit1 === 1 || craneState.limit1 === true;
        return isTrig ? 'TRIGGERED (Stop)' : 'NORMAL (Open)';
      }
      case 'limit2': {
        const isTrig = craneState.limit2 === 1 || craneState.limit2 === true;
        return isTrig ? 'TRIGGERED (Stop)' : 'NORMAL (Open)';
      }
      case 'pressure': {
        const val = craneState.pressure !== undefined ? craneState.pressure : 2.40;
        return `${Number(val).toFixed(2)} Bar`;
      }
      case 'camera': {
        return 'Active | 30 FPS';
      }
      default:
        return String(craneState[key] ?? 'N/A');
    }
  };

  // Get tabular, simplified device values for the status table (as requested by user)
  const getTableValue = (key: string, isOnline: boolean) => {
    if (!isOnline) {
      if (key === 'encoder1' || key === 'encoder2') {
        return '0';
      }
      return 'inactive';
    }
    switch(key) {
      case 'encoder1': {
        const val = craneState.e1 ?? craneState.encoder1 ?? craneState.current_head_deg ?? 0;
        return Math.round(val).toString();
      }
      case 'encoder2': {
        const val = craneState.e2 ?? craneState.encoder2 ?? craneState.last_bungkee_pos ?? 0;
        return Math.round(val).toString();
      }
      case 'photo1':
      case 'photo2':
      case 'photo3':
      case 'photo4': {
        const isHigh = craneState[key] === 1 || craneState[key] === true || craneState[key] === '1' ||
          craneState[key === 'photo1' ? 'p1' : key === 'photo2' ? 'p2' : key === 'photo3' ? 'p3' : key === 'photo4' ? 'p4' : ''] === 1 ||
          craneState[key === 'photo1' ? 'p1' : key === 'photo2' ? 'p2' : key === 'photo3' ? 'p3' : key === 'photo4' ? 'p4' : ''] === true;
        return isHigh ? 'active' : 'inactive';
      }
      case 'limit1':
      case 'limit2': {
        const isTrig = craneState[key] === 1 || craneState[key] === true || craneState[key] === '1';
        return isTrig ? 'active' : 'inactive';
      }
      case 'pressure': {
        const isTrig = craneState.pressure === 1 || craneState.pressure === true || craneState.pressure === '1' || (typeof craneState.pressure === 'number' && craneState.pressure > 0);
        return isTrig ? 'active' : 'inactive';
      }
      case 'camera': {
        return 'active';
      }
      default:
        return 'inactive';
    }
  };

  // Helper to find ROSLIB classes (Ros, Topic, Message) across different bundle types
  const getRosLibClass = (name: string) => {
    // Try directly on ROSLIB object
    if ((ROSLIB as any)[name]) return (ROSLIB as any)[name];
    // Try on .default if it exists
    if ((ROSLIB as any).default && (ROSLIB as any).default[name]) return (ROSLIB as any).default[name];
    // Fallback to global window.ROSLIB if it leaked there
    if ((window as any).ROSLIB && (window as any).ROSLIB[name]) return (window as any).ROSLIB[name];
    
    console.warn(`ROSLIB.${name} not found in current context. Available keys:`, Object.keys(ROSLIB));
    return null;
  };

  const connect = () => {
    if (ros) ros.close();
    resetState();
    setError(null);
    console.log("Attempting to connect to:", wsUrl);
    
    try {
      const RosClass = getRosLibClass('Ros');
      if (!RosClass) {
        setError("ROSLIB.Ros is undefined");
        return;
      }
      
      const rb = new RosClass({ url: wsUrl });

      rb.on('connection', () => {
        console.log("✅ ROSBridge Connected");
        setConnected(true);
        setError(null);
        setRos(rb);

        const TopicClass = getRosLibClass('Topic');
        if (!TopicClass) {
          console.error("ROSLIB.Topic is undefined");
          return;
        }

        // Advertise the control topic
        webControlTopic.current = new TopicClass({
          ros: rb,
          name: '/web_control_topic',
          messageType: 'std_msgs/String',
        });
        webControlTopic.current.advertise();
      });

      rb.on('error', (err) => {
        console.error("❌ ROSBridge Error:", err);
        setConnected(false);
        if (wsUrl.includes('localhost')) {
          setError('Localhost connection failed. If you are on mobile, use the computer IP instead.');
        } else {
          setError('Connection failed. Is ROSBridge running?');
        }
      });

      rb.on('close', () => {
        console.log("🔌 ROSBridge Closed");
        setConnected(false);
        setRos(null);
        resetState();
      });
    } catch (e) {
      setError('Invalid WebSocket URL format');
    }
  };

  // Subscribe to raw status from Python node
  useEffect(() => {
    if (!ros || !connected) return;

    const TopicClass = getRosLibClass('Topic');
    if (!TopicClass) {
      console.error("ROSLIB.Topic is undefined for subscription");
      return;
    }

    const statusTopic = new TopicClass({
      ros: ros,
      name: '/crane_status',
      messageType: 'std_msgs/String'
    });

    console.log("Subscribing to /crane_status...");
    statusTopic.subscribe((message: any) => {
      try {
        const now = Date.now();
        setLastReceivedTime(now);
        
        let raw = "";
        if (typeof message.data === 'string') {
          raw = message.data;
        } else if (message.data && typeof message.data.toString === 'function') {
          raw = message.data.toString();
        }

        setLastReceived(raw);
        
        // ✅ DEBUG: ดูว่า raw มาถึง React จริงไหม
        console.log("RAW RECEIVED:", raw);

        let data: any = {};

        // ✅ JSON parse ก่อน (format ใหม่จาก hardware)
        try {
          const trimmed = raw.trim();
          if (trimmed.startsWith('{')) {
            data = JSON.parse(trimmed);
          }
        } catch (e) {}

        // ✅ Fallback regex สำหรับ format เก่า เช่น "DBG | E1:48 E2:0 | LS1:0"
        if (Object.keys(data).length === 0) {
          const matches = raw.matchAll(/\b([A-Za-z][A-Za-z0-9]{0,9}):(-?[\d.]+)\b/g);
          for (const m of matches) {
            data[m[1]] = parseFloat(m[2]);
          }
        }

        // ── ดักรับ summary field
        if (data.summary && typeof data.summary === 'string') {
          setLastSummary(data.summary);
          setShowSummary(true);
        }

        // ── จุดที่ 2: ดักรับ event field แล้ว route ไป success/error logs ──
        if (data.event && typeof data.event === 'object') {
          const ev = data.event as { type: string; msg: string; time: string };
          const isError = ev.type.startsWith('ERR_') || ev.type.startsWith('WARN_');
          const id = ++logIdCounter.current;

          if (isError) {
            setFailedLogs(prev => [{
              id,
              time: ev.time,
              msgTh: ev.msg,
              msgEn: ev.msg,
              code: ev.type
            }, ...prev].slice(0, 50));
          } else {
            setSuccessLogs(prev => [{
              id,
              time: ev.time,
              msgTh: ev.msg,
              msgEn: ev.msg
            }, ...prev].slice(0, 50));
          }
        }
        
        const normalized: any = {};
        
        Object.keys(data).forEach(key => {
          const val = data[key];
          const lowKey = key.toLowerCase().trim();
          
          const numVal = parseFloat(String(val));
          const isNum = !isNaN(numVal);
          // บูลีนจาก JSON จะเป็น true/false โดยตรง
          const boolVal = typeof val === 'boolean' ? val : (val === 1 || val === '1' || val === 'true');

          // ✅ E1 = Azimuth (ticks)
          if (lowKey === 'e1' || lowKey === 'encoder1' || lowKey === 'azim' || lowKey === 'azimuth') {
            if (isNum) {
              normalized.encoder1 = numVal;
              normalized.e1 = numVal;
              if (data.current_head_deg === undefined) {
                normalized.current_head_deg = numVal;
              }
            }
          }
          else if (lowKey === 'current_head_deg') {
            if (isNum) {
              normalized.current_head_deg = numVal;
            }
          }
          // ✅ E2 = Boom extension (ticks)
          else if (lowKey === 'e2' || lowKey === 'encoder2' || lowKey === 'boom' || lowKey === 'dist' || lowKey === 'distance') {
            if (isNum) {
              normalized.encoder2 = numVal;
              normalized.e2 = numVal;
              if (data.last_bungkee_pos === undefined) {
                normalized.last_bungkee_pos = numVal;
              }
            }
          }
          else if (lowKey === 'last_bungkee_pos') {
            if (isNum) {
              normalized.last_bungkee_pos = numVal;
            }
          }
          // ✅ P1–P4 Photo sensors
          else if (lowKey === 'p1') {
            const v = isNum ? numVal : (boolVal ? 1 : 0);
            normalized.p1 = v; normalized.photo1 = v;
          }
          else if (lowKey === 'p2') {
            const v = isNum ? numVal : (boolVal ? 1 : 0);
            normalized.p2 = v; normalized.photo2 = v;
          }
          else if (lowKey === 'p3') {
            const v = isNum ? numVal : (boolVal ? 1 : 0);
            normalized.p3 = v; normalized.photo3 = v;
          }
          else if (lowKey === 'p4') {
            const v = isNum ? numVal : (boolVal ? 1 : 0);
            normalized.p4 = v; normalized.photo4 = v;
          }
          // ✅ LS1, LS2 Limit switches
          else if (lowKey === 'ls1' || lowKey === 'limit1') {
            normalized.limit1 = isNum ? numVal : (boolVal ? 1 : 0);
          }
          else if (lowKey === 'ls2' || lowKey === 'limit2') {
            normalized.limit2 = isNum ? numVal : (boolVal ? 1 : 0);
          }
          // ✅ PRESS = pressure sensor
          else if (lowKey === 'press' || lowKey === 'pressure') {
            if (isNum) normalized.pressure = numVal;
          }
          // ✅ START → is_system_ready
          else if (lowKey === 'start') {
            normalized.is_system_ready = numVal === 1 || val === true;
          }
          // ✅ STOP → is_moving (0=not stopped=moving)
          else if (lowKey === 'stop') {
            normalized.is_moving = numVal === 0 && normalized.is_system_ready;
          }
          // ✅ EMERGENCY
          else if (lowKey === 'emergency') {
            normalized.emergency = numVal === 1 || val === true;
          }
          else if (lowKey === 'camera' || lowKey === 'cam') {
            normalized.camera = boolVal;
          }

          // save generic lowKey เสมอ
          if (isNum) {
            normalized[lowKey] = numVal;
          } else if (typeof val === 'boolean') {
            normalized[lowKey] = val;
          } else if (val === 'true') {
            normalized[lowKey] = true;
          } else if (val === false || val === 'false') {
            normalized[lowKey] = false;
          } else {
            normalized[lowKey] = val;
          }
        });

        if (Object.keys(normalized).length > 0) {
          setCraneState(prev => ({
            ...prev,
            ...normalized
          }));
        }

        // Update Position History for Chart
        if (normalized.last_bungkee_pos !== undefined || normalized.current_head_deg !== undefined) {
          setPosHistory(prev => {
            const newPos = {
              x: normalized.current_head_deg !== undefined ? normalized.current_head_deg : (prev[prev.length - 1]?.x ?? 0),
              y: normalized.last_bungkee_pos !== undefined ? normalized.last_bungkee_pos : (prev[prev.length - 1]?.y ?? 0),
              time: now
            };
            
            if (prev.length > 0) {
              const last = prev[prev.length - 1];
              if (Math.abs(last.x - newPos.x) < 0.01 && Math.abs(last.y - newPos.y) < 0.01) return prev;
            }
            
            return [...prev, newPos].slice(-40);
          });
        }
      } catch (e) {
        console.error("Status parse error:", e);
      }
    });

    return () => {
      console.log("Unsubscribing from /crane_status");
      statusTopic.unsubscribe();
    };
  }, [ros, connected]);

  const sendCommand = (cmd: string) => {
    // Generate operation log anyway!
    const timeStr = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    let msgTh = 'ส่งคำสั่งทั่วไป';
    let msgEn = 'Sent generic command';

    switch (cmd) {
      case 'q':
        msgTh = 'ส่งคำสั่งสั่งหยุดเครื่องจักรชั่วคราว (STOP [Q]) สำเร็จ';
        msgEn = 'Sent command to halt machine (STOP [Q]) successfully';
        setCraneState(prev => ({ ...prev, is_system_ready: false, cycle_running: false }));
        break;
      case 'x':
        msgTh = 'ส่งคำสั่งทำงานอัตโนมัติ (AUTO [X]) สำเร็จ';
        msgEn = 'Sent command to run automatic mode (AUTO [X]) successfully';
        setCraneState(prev => ({ ...prev, is_system_ready: true, cycle_running: true }));
        break;
      case 'h':
        msgTh = 'ส่งคำสั่งหมุนกลับจุดเริ่มต้น (HOME [H]) สำเร็จ';
        msgEn = 'Sent command to return machine to home coordinates (HOME [H]) successfully';
        setCraneState(prev => ({ ...prev, is_system_ready: true }));
        break;
      case 'c1':
        msgTh = 'ส่งคำสั่งเริ่มแผนงาน Program 1: ตักผสมพารามิเตอร์ทราย สำเร็จ';
        msgEn = 'Sent command to start Program 1: aggregate sand parameters successfully';
        setCraneState(prev => ({ ...prev, is_system_ready: true, cycle_running: true }));
        break;
      case 'c2':
        msgTh = 'ส่งคำสั่งเริ่มแผนงาน Program 2: ตักผสมและบันทึกปริมาณหิน สำเร็จ';
        msgEn = 'Sent command to start Program 2: scoop & record stone batch successfully';
        setCraneState(prev => ({ ...prev, is_system_ready: true, cycle_running: true }));
        break;
      case 'c3':
        msgTh = 'ส่งคำสั่งเริ่มแผนงาน Program 3: ทดสอบเซนเซอร์และพิกัดลิมิต สำเร็จ';
        msgEn = 'Sent command to start Program 3: test sensors & border limits successfully';
        setCraneState(prev => ({ ...prev, is_system_ready: true, cycle_running: true }));
        break;
      default:
        msgTh = `ส่งคำสั่งควบคุมระบบ ${cmd.toUpperCase()} สำเร็จ`;
        msgEn = `Sent control command ${cmd.toUpperCase()} successfully`;
    }

    const newLogId = ++logIdCounter.current;
    
    // Check if we are connected to ROS to add prefix
    const prefixTh = connected ? '[ROS] ' : '[จำลอง] ';
    const prefixEn = connected ? '[ROS] ' : '[SIM] ';
    
    setSuccessLogs(prev => [
      { 
        id: newLogId, 
        time: timeStr, 
        msgTh: prefixTh + msgTh, 
        msgEn: prefixEn + msgEn 
      },
      ...prev
    ].slice(0, 50));

    if (!connected || !webControlTopic.current) {
      console.warn("Command skipped: Not connected to ROS");
      return;
    }
    
    console.log(">>> Sending Command:", cmd);
    setLastSent(cmd);

    // Use plain object structure as ROSBridge accepts it directly
    const msg = { data: cmd }; 
    
    try {
      webControlTopic.current.publish(msg as any);
    } catch (e) {
      console.error("Failed to publish message:", e);
    }
  };

  const isFull = (p: any) => {
    if (p === undefined || p === null) return false;
    // Handle Boolean
    if (typeof p === 'boolean') return p;
    // Handle Number or String Number
    const val = Number(p);
    return val >= 1 || val > 500 || p === "true"; 
  };

  // Mock static profile data matching the user's image style
  const profileData = useMemo(() => {
    const data = [];
    for (let i = 0; i <= 20; i += 2) {
      // Create a nice profile curve
      let y = 10;
      if (i > 5) y = 10 - (i - 5) * 0.5;
      data.push({ x: i, y: Math.max(2, y) });
    }
    return data;
  }, []);

  return (
    <div className="min-h-screen liquid-bg font-sans text-black selection:bg-black selection:text-white overflow-x-hidden flex">
      {/* Side Navigation Menu (Liquid Glass) */}
      <motion.nav 
        initial={false}
        animate={isDesktop ? {
          width: '256px',
          height: 'auto',
          borderRadius: '40px',
          top: '16px',
          left: '16px',
          bottom: '16px',
          padding: '24px'
        } : {
          width: isSidebarOpen ? '210px' : '64px',
          height: isSidebarOpen ? '480px' : '64px',
          borderRadius: isSidebarOpen ? '32px' : '32px',
          top: '12px',
          left: '12px',
          padding: isSidebarOpen ? '16px' : '8px'
        }}
        transition={{ type: "spring", stiffness: 350, damping: 35 }}
        className={cn(
          "fixed z-[100] glass-dark shadow-2xl flex flex-col items-center xl:items-stretch overflow-hidden",
          !isDesktop && !isSidebarOpen && "cursor-pointer hover:scale-110 active:scale-95 group/bubble",
          !isDesktop && isSidebarOpen && "gap-4 sm:gap-6"
        )}
        onClick={() => {
          if (!isDesktop && !isSidebarOpen) setIsSidebarOpen(true);
        }}
      >
        {/* Logo Section */}
        <div 
          className={cn(
            "flex items-center gap-3 cursor-pointer mb-2 xl:mb-0 w-full shrink-0",
            !isDesktop && !isSidebarOpen && "justify-center h-full"
          )} 
          onClick={() => {
            if (isDesktop || isSidebarOpen) {
              setView('main');
              if (!isDesktop) setIsSidebarOpen(false);
            }
          }}
        >
           {!isDesktop && !isSidebarOpen ? (
             <motion.div 
               initial={{ opacity: 0, scale: 0.8 }}
               animate={{ opacity: 1, scale: 1 }}
               className="text-white/80"
             >
               <Menu size={24} strokeWidth={3} />
             </motion.div>
           ) : (
             <div className="w-10 h-10 lg:w-12 lg:h-12 flex items-center justify-center p-1 bg-white rounded-xl lg:rounded-2xl shadow-sm border border-black/5 shrink-0">
               <img src="/logo/logo.png" alt="Logo" className="w-full h-full object-contain" />
             </div>
           )}
           {(isDesktop || isSidebarOpen) && (
             <motion.div 
               initial={{ opacity: 0, x: -10 }}
               animate={{ opacity: 1, x: 0 }}
               className="flex flex-col"
             >
               <h1 className="text-xl font-black tracking-tighter leading-none">CraneAI</h1>

             </motion.div>
           )}
        </div>

        {/* Navigation Items - Visible when expanded or on desktop */}
        <AnimatePresence mode="wait">
          {(isSidebarOpen || isDesktop) && (
            <motion.div 
              key="nav-items"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="flex-1 flex flex-col gap-1.5 sm:gap-2.5 xl:gap-4 w-full mt-4 xl:mt-12 overflow-y-auto custom-scrollbar pr-1"
            >
              {[
                { id: 'main', icon: Home, label: lang === 'th' ? 'หน้าหลัก' : 'OPERATION', desc: 'Control Center' },
                { id: 'result', icon: FileText, label: lang === 'th' ? 'ประวัติงาน' : 'RESULT', desc: 'Operation Logs' },
                { id: 'status', icon: Sliders, label: lang === 'th' ? 'สถานะอุปกรณ์' : 'STATUS', desc: 'IO Diagnostics' },
                { id: 'info', icon: Layout, label: lang === 'th' ? t.project_info : 'INFORMATION', desc: 'Field & Info' },
                { id: 'gallery', icon: Image, label: lang === 'th' ? t.gallery : 'GALLERY', desc: 'Field Photos' },
                { id: 'dev', icon: Users, label: lang === 'th' ? t.developer_page : 'DEVELOPERS', desc: 'Our Team' }
              ].map((item) => (
                <button
                  key={item.id}
                  onClick={(e) => {
                    e.stopPropagation();
                    setView(item.id as any);
                    if (!isDesktop) setIsSidebarOpen(false);
                  }}
                  className={cn(
                    "flex items-center gap-1.5 p-2.5 xl:p-4 rounded-2xl xl:rounded-3xl transition-all relative group/item w-full shrink-0",
                    view === item.id 
                      ? "bg-black text-white shadow-lg xl:shadow-xl" 
                      : "bg-transparent text-gray-400 hover:bg-black/5 hover:text-black"
                  )}
                >
                  <item.icon size={20} className={cn("shrink-0 transition-transform xl:w-6 xl:h-6", view === item.id ? "scale-110" : "group-hover/item:scale-110")} />
                  <div className={cn("flex flex-col items-start leading-none gap-0.5")}>
                    <span className="font-black text-[11px] xl:text-xs uppercase tracking-widest leading-none">{item.label}</span>
                  </div>
                </button>
              ))}

              <div className="mt-auto pt-4 flex flex-col gap-2 sm:gap-3 shrink-0">
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    setLang(lang === 'th' ? 'en' : 'th');
                  }}
                  className="w-full xl:px-4 py-3 rounded-2xl lg:rounded-3xl border border-black/5 bg-white shadow-sm flex items-center justify-center xl:justify-start gap-3 hover:border-black transition-all active:scale-95 group/lang"
                >
                  <div className="w-6 h-6 flex items-center justify-center font-black text-[10px] border border-black/10 rounded-lg bg-zinc-50 group-hover/lang:bg-black group-hover/lang:text-white transition-colors">{lang.toUpperCase()}</div>
                  <div className={cn("flex flex-col items-start leading-none")}>
                    <span className="font-black text-[10px] uppercase tracking-widest leading-none">{t.change_lang}</span>
                  </div>
                </button>

                {(isDesktop || isSidebarOpen) && (
                  <div className={cn("flex items-center gap-3 p-3 sm:p-4 bg-black/5 rounded-[24px] border border-black/5")}>
                    <div className={cn("w-2 h-2 rounded-full", connected ? "bg-emerald-500 animate-pulse" : "bg-gray-300")} />
                    <div className="flex flex-col leading-none">
                      <span className="text-[8px] font-bold text-gray-400 uppercase">Status</span>
                      <span className="text-[10px] font-black uppercase mt-1 leading-none">{connected ? "Connected" : "Offline"}</span>
                    </div>
                  </div>
                )}

                {!isDesktop && isSidebarOpen && (
                  <button 
                    onClick={(e) => {
                      e.stopPropagation();
                      setIsSidebarOpen(false);
                    }}
                    className="w-full py-3 bg-white/5 hover:bg-white/10 rounded-2xl flex items-center justify-center text-gray-400 transition-colors"
                  >
                    <ChevronLeft size={20} />
                  </button>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.nav>

      {/* Main Content Wrap */}
      <div className={cn(
        "flex-1 transition-all duration-500 bg-transparent h-screen overflow-y-auto overflow-x-hidden",
        isDesktop ? "ml-64" : "ml-0",
        (!isDesktop && isSidebarOpen) ? "blur-sm" : ""
      )}>
        <div className="max-w-7xl mx-auto p-3 sm:p-10 xl:p-14 pt-20 sm:pt-24 xl:pt-14 flex flex-col min-h-full items-stretch shrink-0">
          
          {view === 'result' ? (
          <motion.div 
            initial={{ opacity: 0, scale: 0.98, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 120 }}
            className="flex-1 flex flex-col pt-10"
          >
            <div className="flex items-center gap-6 mb-12">
              <div className="flex gap-4">
                <div className="w-16 h-16 sm:w-20 sm:h-20 flex items-center justify-center bg-transparent p-1">
                  <img src="/logo/logo.png" alt="KMUTNB" className="w-full h-full object-contain" />
                </div>
                <div className="w-16 h-16 sm:w-20 sm:h-20 flex items-center justify-center bg-transparent p-1">
                  <img src="/logo/logo2.png" alt="Logo 2" className="w-full h-full object-contain" />
                </div>
              </div>
              <div>
                <h1 className="text-2xl sm:text-4xl md:text-6xl font-black tracking-tighter leading-none mb-2">
                  {lang === 'th' ? 'ประวัติงาน & ผลลัพธ์' : 'OPERATION RESULTS'}
                </h1>
                <p className="text-[8px] sm:text-xs font-bold text-gray-400 tracking-tight sm:tracking-[0.2em] uppercase leading-tight">
                  {lang === 'th' ? 'ข้อมูลทางสถิติการดำเนินงานและตัวจับเวลาแบบเรียลไทม์' : 'Operational success audit log, active chronometer, and system failure metrics'}
                </p>
              </div>
            </div>

            {/* 50/50 Layout Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-stretch mb-12">
              
              {/* Left Side: Successful Operations */}
              <div className="border-[4px] border-black bg-white p-6 sm:p-8 rounded-sm shadow-[10px_10px_0px_0px_rgba(0,0,0,1)] flex flex-col min-h-[550px]">
                <div className="flex items-center justify-between border-b-2 border-black pb-4 mb-6">
                  <div className="flex items-center gap-3">
                    <CheckCircle className="text-emerald-500 w-6 h-6 shrink-0" strokeWidth={3} />
                    <h2 className="text-lg sm:text-xl font-black uppercase tracking-widest text-black">
                      {lang === 'th' ? 'การทำงาน' : 'OPERATIONS'}
                    </h2>
                  </div>
                  <span className="bg-emerald-100 text-emerald-800 text-[10px] sm:text-xs font-black px-3 py-1 rounded-full uppercase tracking-wider">
                    {lang === 'th' ? 'เสถียร' : 'STABLE'}
                  </span>
                </div>



                <p className="text-xs font-semibold text-gray-500 mb-4 uppercase tracking-wider">
                  {lang === 'th' ? 'บันทึกความสำเร็จล่าสุด' : 'Recent Success Stream'}
                </p>

                {/* Operations logs list */}
                <div className="flex-1 space-y-3 max-h-[450px] overflow-y-auto custom-scrollbar pr-1 flex flex-col justify-start">
                  {successLogs.length === 0 ? (
                    <div className="text-center py-20 text-gray-400 font-medium my-auto">
                      <CheckCircle className="mx-auto w-12 h-12 text-gray-200 mb-2 stroke-[1.5]" />
                      <p className="text-sm">
                        {lang === 'th' ? 'ไม่มีบันทึกการทำงาน' : 'No operational logs'}
                      </p>
                      <p className="text-[10px] uppercase tracking-widest text-gray-400/80 mt-1">
                        {lang === 'th' ? 'กำลังรอสัญญาณจริง...' : 'Waiting for real-time stream...'}
                      </p>
                    </div>
                  ) : (
                    successLogs.map((log) => (
                      <div key={log.id} className="p-3.5 bg-zinc-50 border border-zinc-200 hover:border-black rounded-xl transition-all flex items-start gap-3">
                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-mono text-[9px] font-black text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded leading-none">{log.time}</span>
                            <span className="font-mono text-[8px] font-bold text-gray-400">ID: #{log.id}</span>
                          </div>
                          <p className="text-xs font-semibold text-gray-700 leading-relaxed break-words font-medium">
                            {lang === 'th' ? log.msgTh : log.msgEn}
                          </p>
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {/* Real-time Broadcast Status deleted */}
              </div>

              {/* Right Side: Failed Operations and Alarms */}
              <div className="border-[4px] border-black bg-white p-6 sm:p-8 rounded-sm shadow-[10px_10px_0px_0px_rgba(0,0,0,1)] flex flex-col min-h-[550px]">
                <div className="flex items-center justify-between border-b-2 border-black pb-4 mb-6">
                  <div className="flex items-center gap-3">
                    <XCircle className="text-rose-500 w-6 h-6 shrink-0" strokeWidth={3} />
                    <h2 className="text-lg sm:text-xl font-black uppercase tracking-widest text-black">
                      {lang === 'th' ? 'ข้อผิดพลาด / สัญญาณเตือน' : 'ERRORS / ALARM'}
                    </h2>
                  </div>
                  <span className="bg-rose-100 text-rose-800 text-[10px] sm:text-xs font-black px-3 py-1 rounded-full uppercase tracking-wider animate-pulse">
                    {lang === 'th' ? 'สัญญาณเตือนใช้งาน' : 'ALARM ACTIVE'}
                  </span>
                </div>

                <p className="text-xs font-semibold text-gray-500 mb-4 uppercase tracking-wider">
                  {lang === 'th' ? 'รายงานค่าผิดพลาดและสัญญาณเตือน' : 'Security Fallback & Warning Log'}
                </p>

                {/* Failed/Error logs list */}
                <div className="flex-1 space-y-3 max-h-[450px] overflow-y-auto custom-scrollbar pr-1 flex flex-col justify-start">
                  {failedLogs.length === 0 ? (
                    <div className="text-center py-20 text-gray-400 font-medium my-auto">
                      <AlertCircle className="mx-auto w-12 h-12 text-gray-200 mb-2 stroke-[1.5]" />
                      <p className="text-sm">
                        {lang === 'th' ? 'ไม่มีสัญญาณเตือนภัย' : 'No alarms or errors'}
                      </p>
                      <p className="text-[10px] uppercase tracking-widest text-gray-400/80 mt-1">
                        {lang === 'th' ? 'ระบบเฝ้าระวังปกติ...' : 'System status normal...'}
                      </p>
                    </div>
                  ) : (
                    failedLogs.map((log) => (
                      <div key={log.id} className="p-3.5 bg-rose-50/20 border border-rose-100 hover:border-rose-300 rounded-xl transition-all flex items-start gap-3">
                        <AlertTriangle className="text-rose-500 w-4 h-4 mt-0.5 shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-mono text-[9px] font-black text-rose-700 bg-rose-100/60 px-2 py-0.5 rounded leading-none">{log.code}</span>
                            <span className="font-mono text-[8px] font-bold text-gray-400">{log.time}</span>
                          </div>
                          <p className="text-xs font-medium text-gray-705 leading-relaxed break-words">
                            {lang === 'th' ? log.msgTh : log.msgEn}
                          </p>
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {/* Real-time Alarm Monitor Broadcast deleted */}
              </div>

            </div>
          </motion.div>
        ) : view === 'status' ? (
          <motion.div 
            initial={{ opacity: 0, scale: 0.98, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 120 }}
            className="flex-1 flex flex-col pt-10"
          >
            {/* Title with logos */}
            <div className="flex items-center gap-6 mb-12">
              <div className="flex gap-4">
                <div className="w-16 h-16 sm:w-20 sm:h-20 flex items-center justify-center bg-transparent p-1">
                  <img src="/logo/logo.png" alt="KMUTNB" className="w-full h-full object-contain" />
                </div>
                <div className="w-16 h-16 sm:w-20 sm:h-20 flex items-center justify-center bg-transparent p-1">
                  <img src="/logo/logo2.png" alt="Logo 2" className="w-full h-full object-contain" />
                </div>
              </div>
              <div>
                <h1 className="text-2xl sm:text-4xl md:text-6xl font-black tracking-tighter leading-none mb-2">
                  {lang === 'th' ? 'สถานะเครื่องมือเซนเซอร์' : 'DEVICE STATUS'}
                </h1>
                <p className="text-[8px] sm:text-xs font-bold text-gray-400 tracking-tight sm:tracking-[0.2em] uppercase leading-tight">
                  {lang === 'th' ? 'ระบบแสดงการทำงานเพื่อทดสอบเชื่อมต่อสัญญาณ IO บอร์ดไมโครคอนโทรลเลอร์' : 'Real-time online/offline indicators for core sand/stone preparing components'}
                </p>
              </div>
            </div>

            {/* Real-time communication node status */}
            <div className="w-full p-6 border-[3px] border-black bg-zinc-50 rounded-sm mb-8 flex flex-col sm:flex-row justify-between items-center gap-4 shadow-sm">
               <div className="flex flex-col items-center sm:items-start text-center sm:text-left">
                  <span className="font-black text-sm sm:text-base uppercase text-black tracking-tight">{lang === 'th' ? 'สถานะเครือข่ายเชื่อมต่อบอร์ดสัญญาณจริง' : 'PHYSICAL HARDWARE NODE STATUS'}</span>
                  <span className="text-xs text-gray-500 font-semibold mt-1">
                    {lang === 'th' 
                      ? `กำลังเฝ้าอ่านค่าจริงด้วยช่องสตรีมของ ROSBridge WebSocket: ${wsUrl}` 
                      : `Actively printing physical values from high-speed ROSBridge node at ${wsUrl}`}
                  </span>
               </div>
               <div className="flex gap-4 shrink-0 font-mono">
                  {connected ? (
                    <div className="flex items-center gap-3 bg-emerald-50 px-4 py-2 border-2 border-emerald-500 rounded text-emerald-800 text-xs font-black">
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                      CONNECTED
                    </div>
                  ) : (
                    <div className="flex items-center gap-3 bg-rose-50 px-4 py-2 border-2 border-rose-500 rounded text-rose-800 text-xs font-black">
                      <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping" />
                      DISCONNECTED
                    </div>
                  )}
               </div>
            </div>

            {/* Structured responsive table of the 10 device items */}
            <div className="w-full border-[3px] border-black bg-white shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] rounded-sm mb-12 overflow-hidden">
               <div className="overflow-x-auto">
                 <table className="w-full text-left border-collapse text-xs sm:text-sm">
                   <thead>
                     <tr className="border-b-[3px] border-black bg-zinc-100">
                       <th className="px-4 py-3.5 font-black uppercase text-black border-r-[3px] border-black w-14 sm:w-20 text-center select-none">
                         on
                       </th>
                       <th className="px-4 py-3.5 font-black text-black border-r-[3px] border-black">
                         {lang === 'th' ? 'ชื่อ' : 'ชื่ออุปกรณ์ / Device Name'}
                       </th>
                       <th className="px-4 py-3.5 font-black text-black w-28 sm:w-40 text-center select-none">
                         {lang === 'th' ? 'ค่า' : 'ค่า / Value'}
                       </th>
                     </tr>
                   </thead>
                   <tbody>
                     {[
                       { key: 'encoder1', nameTh: 'encoder 1', nameEn: 'encoder 1', thDesc: 'position base', enDesc: 'position base' },
                       { key: 'encoder2', nameTh: 'encoder 2', nameEn: 'encoder 2', thDesc: 'position bungkee', enDesc: 'position bungkee' },
                       { key: 'photo1', nameTh: 'photo sensor 1', nameEn: 'photo sensor 1', thDesc: 'stone level limit 1', enDesc: 'stone level limit 1' },
                       { key: 'photo2', nameTh: 'photo sensor 2', nameEn: 'photo sensor 2', thDesc: 'stone level limit 2', enDesc: 'stone level limit 2' },
                       { key: 'photo3', nameTh: 'photo sensor 3', nameEn: 'photo sensor 3', thDesc: 'sand level limit', enDesc: 'sand level limit' },
                       { key: 'photo4', nameTh: 'photo sensor 4', nameEn: 'photo sensor 4', thDesc: 'bungkee position', enDesc: 'bungkee position' },
                       { key: 'limit1', nameTh: 'limit sensor 1', nameEn: 'limit sensor 1', thDesc: 'สวิตช์ชนเพลทซ้ายสุดทาง', enDesc: 'Left Margin Brake' },
                       { key: 'limit2', nameTh: 'limit sensor 2', nameEn: 'limit sensor 2', thDesc: 'สวิตช์ชนเพลทขวาสุดทาง', enDesc: 'Right Margin Brake' },
                       { key: 'pressure', nameTh: 'pressure sensor', nameEn: 'pressure sensor', thDesc: 'เซ็นเซอร์วัดแรงดันไฮโดรลิก', enDesc: 'Hydraulic Valve' },
                       { key: 'camera', nameTh: 'intel realsense camera', nameEn: 'intel realsense camera', thDesc: 'กล้องวิเคราะห์พิกัดจุดตัก', enDesc: 'AI Depth Camera' }
                     ].map((dev, index) => {
                       const isOnline = connected && (craneState[dev.key + '_ok'] !== false);
                       const tableVal = getTableValue(dev.key, isOnline);
                       
                       return (
                         <tr key={dev.key} className="border-b-[3px] border-black last:border-b-0 hover:bg-zinc-50/50 transition-colors">
                           {/* ON column (Row serial number) */}
                           <td className="px-4 py-3.5 sm:py-4 font-black font-mono text-center border-r-[3px] border-black bg-zinc-50/50 select-none text-black">
                             {index + 1}
                           </td>
                           
                           {/* NAME column (Device identifier and tech subtext) */}
                           <td className="px-4 py-3.5 sm:py-4 border-r-[3px] border-black">
                             <div className="flex flex-col gap-0.5">
                               <span className="font-bold text-black text-xs sm:text-sm lowercase tracking-tight">
                                 {lang === 'th' ? dev.nameTh : dev.nameEn}
                                </span>
                               <span className="text-[10px] sm:text-xs text-gray-400 font-medium">
                                 {lang === 'th' ? dev.thDesc : dev.enDesc}
                               </span>
                             </div>
                           </td>
                           
                           {/* VALUE column */}
                           <td className="px-4 py-3.5 sm:py-4 text-center select-none font-mono text-xs sm:text-sm font-black text-black">
                             <span className={cn(
                               "px-2.5 py-1 rounded-md border",
                               tableVal === 'active' && "bg-emerald-50 text-emerald-700 border-emerald-200",
                               tableVal === 'inactive' && "bg-zinc-50 text-gray-500 border-zinc-200 opacity-60",
                               tableVal !== 'active' && tableVal !== 'inactive' && "bg-cyan-50 text-cyan-800 border-cyan-200"
                             )}>
                               {tableVal}
                             </span>
                           </td>
                         </tr>
                       );
                     })}
                   </tbody>
                 </table>
               </div>
            </div>
          </motion.div>
        ) : view === 'info' ? (
          <motion.div 
            initial={{ opacity: 0, scale: 0.98, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 120 }}
            className="flex-1 flex flex-col pt-10"
          >
            <div className="flex items-center gap-6 mb-12">
              <div className="flex gap-4">
                <div className="w-16 h-16 sm:w-20 sm:h-20 flex items-center justify-center bg-transparent p-1">
                  <img 
                    src="/logo/logo.png" 
                    alt="KMUTNB" 
                    className="w-full h-full object-contain"
                  />
                </div>
                <div className="w-16 h-16 sm:w-20 sm:h-20 flex items-center justify-center bg-transparent p-1">
                  <img 
                    src="/logo/logo2.png" 
                    alt="Logo 2" 
                    className="w-full h-full object-contain"
                  />
                </div>
              </div>
              <div>
                <h1 className="text-2xl sm:text-4xl md:text-6xl font-black tracking-tighter leading-none mb-2">{lang === 'th' ? 'รายละเอียดโครงการ' : 'INFORMATION'}</h1>
                <p className="text-[8px] sm:text-xs font-bold text-gray-400 tracking-tight sm:tracking-[0.2em] uppercase leading-tight">AI-Controlled Sand and Stone Preparing Machine for Concrete Batching System</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
              <div className="space-y-8">
                <section>
                  <h2 className="text-xl font-black uppercase tracking-widest border-b-2 border-black pb-2 mb-4">{t.vision}</h2>
                  <p className="text-sm leading-relaxed text-gray-600 font-medium whitespace-pre-line">
                    {t.vision_desc}
                  </p>
                </section>

                <section>
                  <h2 className="text-xl font-black uppercase tracking-widest border-b-2 border-black pb-2 mb-4">{t.features}</h2>
                  <ul className="space-y-4">
                    {[
                      { title: lang === 'th' ? 'ระบบโทรมาตรแบบเรียลไทม์' : 'Real-time Telemetry', desc: lang === 'th' ? 'การสตรีมข้อมูลผ่าน ROSBridge (WebSockets) ที่ความหน่วงต่ำ' : 'Latency-optimized data streaming via ROSBridge (WebSockets).' },
                      { title: lang === 'th' ? 'ระบบภาพอัจฉริยะ' : 'Smart Vision', desc: lang === 'th' ? 'การตรวจจับวัตถุด้วย AI เพื่อความแม่นยำในการยก' : 'AI-powered object detection for precision payload handling.' },
                      { title: lang === 'th' ? 'Digital Twin' : 'Digital Twin Sync', desc: lang === 'th' ? 'การซิงโครไนซ์ระหว่างฮาร์ดแวร์จริงและโมเดลจำลอง' : 'Seamless synchronization between physical hardware and virtual simulation.' },
                      { title: lang === 'th' ? 'ระบบความปลอดภัย' : 'Safety Protocols', desc: lang === 'th' ? 'สวิตช์จำกัดระยะและระบบเบรกฉุกเฉิน' : 'Hard-sync Limit Switches and Emergency Brake systems.' }
                    ].map((feature, i) => (
                      <li key={i} className="flex gap-4">
                        <div className="w-2 h-2 rounded-full bg-black mt-2 shrink-0" />
                        <div>
                          <h3 className="font-black text-sm uppercase">{feature.title}</h3>
                          <p className="text-xs text-gray-500">{feature.desc}</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                </section>
              </div>

              <div className="space-y-8">
                 <div className="border-[4px] border-black p-8 glass relative overflow-hidden group">
                   <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                     <Activity size={120} />
                   </div>
                   <h2 className="text-2xl font-black uppercase tracking-tighter mb-4 relative z-10">{t.architecture}</h2>
                   <div className="space-y-4 font-mono text-xs text-gray-500 relative z-10">
                     <div className="flex justify-between border-b border-black/5 pb-2 uppercase">
                        <span>Framework</span>
                        <span className="text-black font-bold">React + Vite + ROS2</span>
                     </div>
                     <div className="flex justify-between border-b border-black/5 pb-2 uppercase">
                        <span>Communication</span>
                        <span className="text-black font-bold">UDP/WebSocket (9090)</span>
                     </div>
                     <div className="flex justify-between border-b border-black/5 pb-2 uppercase">
                        <span>Hardware</span>
                        <span className="text-black font-bold">Raspberry Pi + STM32</span>
                     </div>
                     <div className="flex justify-between border-b border-black/5 pb-2 uppercase">
                        <span>Video Stream</span>
                        <span className="text-black font-bold">MJPEG HTTP (5002)</span>
                     </div>
                   </div>
                 </div>

                 <div className="p-8 border-[4px] border-black glass">
                    <h2 className="text-xl font-black uppercase tracking-widest mb-6">project CraneAI</h2>
                    <p className="text-[10px] font-bold text-gray-400 mb-4 uppercase">AI-Controlled Sand and Stone Preparing Machine for Concrete Batching System</p>
                    <div className="space-y-6">
                      <div className="flex flex-col">
                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">{t.inst_label}</span>
                        <span className="font-bold text-[10px] leading-tight">{t.inst_value}</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">{t.version}</span>
                        <span className="font-bold">v0.01-beta</span>
                      </div>
                      <div className="pt-4 mt-4 border-t border-black/5">
                         <button 
                           onClick={() => setView('dev')}
                           className="w-full py-4 bg-black text-white font-black uppercase text-[10px] tracking-widest hover:scale-[1.02] active:scale-95 transition-all shadow-xl"
                         >
                           VIEW ALL DEVELOPERS
                         </button>
                      </div>
                    </div>
                 </div>
              </div>
            </div>
            
          </motion.div>
        ) : view === 'dev' ? (
          <motion.div 
            initial={{ opacity: 0, scale: 0.98, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 120 }}
            className="flex-1 flex flex-col pt-10"
          >
            <div className="flex items-center gap-6 mb-12">
              <div className="flex gap-4">
                <div className="w-16 h-16 sm:w-20 sm:h-20 flex items-center justify-center bg-transparent p-1">
                  <img 
                    src="/logo/logo.png" 
                    alt="KMUTNB" 
                    className="w-full h-full object-contain"
                  />
                </div>
                <div className="w-16 h-16 sm:w-20 sm:h-20 flex items-center justify-center bg-transparent p-1">
                  <img 
                    src="/logo/logo2.png" 
                    alt="Logo 2" 
                    className="w-full h-full object-contain"
                  />
                </div>
              </div>
              <div>
                <h1 className="text-2xl sm:text-4xl md:text-6xl font-black tracking-tighter leading-none mb-2">{t.team}</h1>
                <p className="text-[8px] sm:text-xs font-bold text-gray-400 tracking-tight sm:tracking-[0.1em] uppercase leading-tight">King Mongkut's University of Technology North Bangkok</p>
              </div>
            </div>

            <div className="max-w-4xl mx-auto w-full px-2 sm:px-0">
               <div className="p-6 sm:p-14 border-[6px] sm:border-[10px] border-black bg-black/90 backdrop-blur-xl text-white shadow-[15px_15px_0px_0px_rgba(0,0,0,0.1)] sm:shadow-[30px_30px_0px_0px_rgba(0,0,0,0.1)] rounded-sm">
                  {/* Advisor Section */}
                  <div className="flex flex-col items-center mb-16 pb-16 border-b border-white/10">
                      <div className="w-32 h-32 sm:w-40 sm:h-40 rounded-full border-8 border-white overflow-hidden bg-gray-800 shrink-0 mb-6 shadow-2xl">
                         <img src="/person/person0.jpg" alt="Advisor" className="w-full h-full object-cover" onError={(e) => (e.target as HTMLImageElement).src = `https://api.dicebear.com/7.x/avataaars/svg?seed=advisor`} />
                      </div>
                      <div className="flex flex-col items-center">
                         <span className="text-xs sm:text-sm font-black text-[#22c55e] uppercase tracking-[0.4em] mb-3">{lang === 'th' ? 'อาจารย์ที่ปรึกษา' : 'PROJECT ADVISOR'}</span>
                         <span className="font-black text-2xl sm:text-4xl tracking-tight text-white text-center">ผศ.ดร.สุพจน์ แก้วกรณ์</span>
                         <span className="text-[10px] font-bold text-gray-500 uppercase mt-4 tracking-widest">{t.inst_value}</span>
                      </div>
                   </div>

                   {/* Teams Grid */}
                   <div className="grid grid-cols-1 md:grid-cols-2 gap-16 sm:gap-24">
                      {/* Team A */}
                      <div className="space-y-8">
                         <div className="flex justify-between items-end border-b border-white/20 pb-4 mb-2">
                           <h3 className="text-lg font-black tracking-widest text-[#22c55e] uppercase">TEAM SOFTWARE</h3>
                         </div>
                         {[
                            { name: "นายโชคพิพัฒน์ ดิษฐ์เลิศธนกุล", img: "/person/person1.png" },
                            { name: "นายณัฐวุฒิ ศรีอ่อน", img: "/person/person2.png" },
                            { name: "นายเจนกวิน ย่านสากล", img: "/person/person3.png" }
                         ].map((member, i) => (
                            <div key={i} className="flex items-center gap-6 group">
                               <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full border-4 border-white/20 overflow-hidden bg-gray-800 shrink-0 transition-transform group-hover:scale-110">
                                  <img src={member.img} alt={member.name} className="w-full h-full object-cover" onError={(e) => (e.target as HTMLImageElement).src = `https://api.dicebear.com/7.x/avataaars/svg?seed=a${i}`} />
                               </div>
                               <div className="flex flex-col">
                                  <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1">DEVELOPER</span>
                                  <span className="font-black text-base sm:text-lg leading-tight text-white">{member.name}</span>
                               </div>
                            </div>
                         ))}
                      </div>

                      {/* Team B */}
                      <div className="space-y-8">
                         <div className="flex justify-between items-end border-b border-white/20 pb-4 mb-2">
                           <h3 className="text-lg font-black tracking-widest text-[#22c55e] uppercase">TEAM HARDWARE</h3>
                         </div>
                         {[
                            { name: "นายจูเลี่ยน ประเสริฐ", img: "/person/person4.jpg" },
                            { name: "นายอนุพันธ์ ท้วมวงศ์", img: "/person/person5.jpg" },
                            { name: "นายภัทรพล แสงคำ", img: "/person/person6.jpg" }
                         ].map((member, i) => (
                            <div key={i} className="flex items-center gap-6 group">
                               <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full border-4 border-white/20 overflow-hidden bg-gray-800 shrink-0 transition-transform group-hover:scale-110">
                                  <img src={member.img} alt={member.name} className="w-full h-full object-cover" onError={(e) => (e.target as HTMLImageElement).src = `https://api.dicebear.com/7.x/avataaars/svg?seed=b${i}`} />
                               </div>
                               <div className="flex flex-col">
                                  <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1">DEVELOPER</span>
                                  <span className="font-black text-base sm:text-lg leading-tight text-white">{member.name}</span>
                               </div>
                            </div>
                         ))}
                      </div>
                   </div>

                   {/* Footer Quote */}
                   <div className="mt-20 pt-10 border-t border-white/10 text-center italic text-gray-500 text-xs">
                     "Automating the physical world through code and intelligence."
                   </div>
               </div>
            </div>
          </motion.div>
        ) : view === 'gallery' ? (
          <motion.div 
            initial={{ opacity: 0, scale: 0.98, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 120 }}
            className="flex-1 flex flex-col pt-10"
          >
            <div className="flex items-center gap-6 mb-12">
              <div className="flex gap-4">
                <div className="w-16 h-16 sm:w-20 sm:h-20 flex items-center justify-center bg-transparent p-1">
                  <img 
                    src="/logo/logo.png" 
                    alt="KMUTNB" 
                    className="w-full h-full object-contain"
                  />
                </div>
                <div className="w-16 h-16 sm:w-20 sm:h-20 flex items-center justify-center bg-transparent p-1">
                  <img 
                    src="/logo/logo2.png" 
                    alt="Logo 2" 
                    className="w-full h-full object-contain"
                  />
                </div>
              </div>
              <div>
                <h1 className="text-2xl sm:text-4xl md:text-6xl font-black tracking-tighter leading-none mb-2">{lang === 'th' ? 'แกลเลอรี่โครงการ' : 'GALLERY'}</h1>
                <p className="text-[8px] sm:text-xs font-bold text-gray-400 tracking-tight sm:tracking-[0.1em] uppercase leading-tight">Visual Field Documentation & Progress</p>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6">
                {[
                  '665108993_1347049720620889_3942740309544427124_n.jpg',
                  '665193417_999804972999397_3779305772829628182_n.jpg',
                  '665797994_1313230597432721_7401155319504346035_n.jpg',
                  '668813309_2829730480719380_7201648612407399436_n.jpg',
                  '668813309_864421445958429_3997512588218532495_n.jpg',
                  '668842994_1344199257766283_2498898871718563839_n.jpg',
                  '669364869_2442180749560862_3721912035129363699_n.jpg',
                  '669375449_984555490888724_3070797389505805262_n.jpg',
                  '671153151_1441748457703166_92581223828938756_n.jpg',
                  '671366609_1920251345317180_512938661228880599_n.jpg',
                  '671517031_1360150942599307_3759236595094922638_n.jpg',
                  '671603281_974973031585471_7547218204159348625_n.jpg',
                  '671680112_1696589761474792_4218581411384078930_n.jpg',
                  '671783058_26895953406681220_1962940762018238454_n.jpg',
                  '672115680_3935619596743529_968607634762429723_n.jpg',
                  '672165765_2910215725990618_8670062747554425318_n.jpg',
                  '672183096_1319477220316927_6381103252807740233_n.jpg',
                  '672240746_2211031805969833_929798505854476953_n.jpg',
                  '672578346_1551345343280840_4231644091340028203_n.jpg',
                  '673010871_1504053891119446_8493092311875826839_n.jpg',
                  '673436824_2185605768642651_5291520371103803663_n.jpg',
                  '673468747_1458064508938753_8139284388626675147_n.jpg',
                  '674330311_1998576460778245_4277346437431074588_n.jpg',
                  '674338686_1312012867539109_7473594028563883505_n.jpg',
                  '674941786_1892342564785202_4338253602076522691_n.jpg',
                  '676427031_985941390560746_1373793281664596488_n.jpg',
                  '677041072_1679415693091803_5630998944295851038_n.jpg',
                  '684185208_1679960263224651_9108961494422427282_n.jpg',
                  '686354663_1350465487004220_544609828601504527_n.jpg',
                  '687872246_984533117271653_2137492318346047025_n.jpg',
                  '687892215_972787482281266_731855086472239926_n.jpg',
                  '687955674_1295341545860612_8770291544624223411_n.jpg',
                  '687979406_972440885714422_2019849779191540807_n.jpg',
                  '688013363_969021302404436_4773491481150027016_n.jpg',
                  '688047343_1449854409800817_7416815562721035033_n.jpg',
                  '688137770_1332618678931922_3176833776631251841_n.jpg',
                  '688501667_959280206997868_7230136938615155063_n.jpg',
                  '689608909_1630848151319613_7493825178660962171_n.jpg',
                  '691483141_27905760682346467_8527996212161507271_n.jpg',
                  '692842891_1018716660842227_946711966078317824_n.jpg',
                  '693343436_1288531573368454_5501628118450964247_n.jpg',
                  '693467086_1619802243225957_4733870540036968289_n.jpg',
                  '693546648_1661808848488235_1481415623159307185_n.jpg',
                  '693612053_1737186924324788_2705795435741237184_n.jpg',
                  '694532861_1714275083317896_1572283592904312342_n.jpg',
                  '695532404_954582227558737_2121059039702243983_n.jpg',
                  '695685653_1351221640184954_5605973137035462505_n.jpg',
                  '695823947_1700329040968748_8504208513306902535_n.jpg',
                  '696187427_966540376081365_1218022910700932098_n.jpg',
                  '696195646_1699180797741902_5714024066754859541_n.jpg',
                  '701220434_1279746097664390_6557688673590458890_n.jpg'
                ].map((img, i) => (
                  <motion.div 
                    key={i}
                    whileHover={{ scale: 1.02 }}
                    onClick={() => setSelectedImage(`/GALLERY/${img}`)}
                    className="aspect-square border-[3px] border-black overflow-hidden bg-gray-100 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] transition-all cursor-zoom-in"
                  >
                    <img 
                      src={`/GALLERY/${img}`} 
                      alt={`Field image ${i + 1}`} 
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  </motion.div>
                ))}
              </div>
          </motion.div>
        ) : (
          <motion.div 
            initial={{ opacity: 0, scale: 0.98, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 120 }}
            className="flex-1 flex flex-col"
          >
            {/* Top Header Section */}
        <div className="flex flex-col lg:flex-row justify-between items-center lg:items-start w-full mb-10 gap-8">
          <div className="flex flex-col items-center lg:items-start gap-4 w-full lg:w-auto">
            <div className="flex items-center gap-4">
              <div className="flex gap-3">
                <div className="w-14 h-14 sm:w-16 sm:h-16 flex items-center justify-center bg-transparent p-1">
                  <img 
                    src="/logo/logo.png" 
                    alt="KMUTNB" 
                    className="w-full h-full object-contain"
                  />
                </div>
                <div className="w-14 h-14 sm:w-16 sm:h-16 flex items-center justify-center bg-transparent p-1">
                  <img 
                    src="/logo/logo2.png" 
                    alt="Logo 2" 
                    className="w-full h-full object-contain"
                  />
                </div>
              </div>
              <div className="flex flex-col">
                <h1 className="text-2xl sm:text-3xl font-black tracking-tighter leading-none">CraneAI</h1>
                <span className="text-[8px] sm:text-[10px] font-bold text-gray-400 tracking-[0.1em] uppercase mt-1">King Mongkut's University of Technology North Bangkok.</span>
              </div>
            </div>
          </div>
          
          <div className="flex flex-col items-center lg:items-end gap-2 w-full lg:w-auto mt-4 lg:mt-0">
            <div className="flex items-center gap-3 sm:gap-4 w-full justify-center lg:justify-end">
              <div className="flex items-center glass border border-black/10 rounded-lg p-1 shadow-sm gap-1 sm:gap-2 w-full max-w-sm sm:max-w-md lg:w-auto">
                <input 
                  type="text" 
                  value={wsUrl}
                  onChange={(e) => setWsUrl(e.target.value)}
                  className="bg-transparent px-2 sm:px-3 py-2 font-mono text-[9px] sm:text-[11px] outline-none flex-1 min-w-0"
                  placeholder="ws://localhost:9090"
                />
                <div className="h-4 w-[1px] bg-gray-200 mx-0.5 sm:mx-1" />
                <button 
                  onClick={connected ? () => ros?.close() : connect}
                  className={cn(
                    "px-2 sm:px-6 py-2 font-black text-[9px] sm:text-[11px] uppercase tracking-widest transition-all whitespace-nowrap",
                    connected ? "text-rose-500 hover:bg-rose-50" : "text-blue-600 hover:bg-blue-50"
                  )}
                >
                  {connected ? t.disconnect : t.connect}
                </button>
              </div>
            </div>
            {error && (
              <span className="text-[9px] font-bold text-rose-500 uppercase tracking-wider text-center lg:text-right">
                {error}
              </span>
            )}
          </div>
        </div>

      {/* Main Content Area */}
        <div className="flex-1 flex flex-col gap-6 lg:gap-10 xl:gap-14 w-full">
          
          <div className="w-full flex flex-col lg:grid lg:grid-cols-12 gap-6 lg:gap-10 xl:gap-14 items-center lg:items-start shrink-0">
            
            {/* Left Side: Display */}
            <div className="w-full col-span-12 lg:col-span-8 flex flex-col gap-4 items-center lg:items-stretch h-full">
              <div className="w-full aspect-video border-[3px] sm:border-[5px] border-black rounded-sm flex items-center justify-center bg-transparent glass relative shadow-[4px_4px_0px_0px_rgba(0,0,0,0.05)] sm:shadow-[10px_10px_0px_0px_rgba(0,0,0,0.05)] max-w-full lg:max-w-none overflow-hidden mx-auto lg:mx-0 max-h-[60vh] lg:max-h-none">
                 {/* Live Video Feed */}
                 <img 
                   src={videoUrl} 
                   alt="Live Crane Feed"
                   className="w-full h-full object-contain bg-black"
                   onError={(e) => {
                     (e.target as HTMLImageElement).style.display = 'none';
                     const parent = (e.target as HTMLImageElement).parentElement;
                     if (parent) {
                       const fallback = parent.querySelector('.video-fallback');
                       if (fallback) (fallback as HTMLElement).style.display = 'flex';
                     }
                   }}
                 />

                  {/* Video Fallback UI */}
                  <div className="video-fallback hidden absolute inset-0 flex-col items-center justify-center gap-2 p-4">
                    <span className="text-emerald-500 text-[12vw] sm:text-6xl md:text-8xl font-black uppercase tracking-[0.1em] sm:tracking-[0.3em] opacity-40 text-center">{t.display}</span>
                    <div className="text-[8px] sm:text-[12px] font-bold text-gray-400 uppercase tracking-[0.1em] sm:tracking-[0.4em] bg-white/80 px-2 sm:px-4 py-1 sm:py-2 rounded text-center">
                      {t.waiting_signal}
                    </div>
                  </div>

                 {/* Simple Live Data Overlay */}
                 <div className="absolute top-4 right-4 sm:top-8 sm:right-8 flex flex-col items-end font-mono text-[9px] sm:text-[12px] text-gray-400 glass p-2 sm:p-4 rounded-sm border border-black/5 shadow-sm">
                   <div className="font-bold flex items-center gap-1 sm:gap-3 text-black mb-0.5 sm:mb-1">
                     <div className={cn("w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full", connected ? "bg-red-500 animate-pulse" : "bg-gray-300")} />
                     LIVE_FEED
                   </div>
                   <div className="font-bold opacity-60">
                     AZIM: {(() => {
                       const val = craneState.current_head_deg ?? 0;
                       const isRad = Math.abs(val) <= 2 * Math.PI && val !== 0;
                       const deg = isRad ? (val * 180 / Math.PI) : (val / 17.0667);
                       return deg.toFixed(1);
                     })()}°
                   </div>
                   <div className="font-bold opacity-60">
                     BOOM: {(() => {
                       const val = craneState.last_bungkee_pos ?? 0;
                       const isMeter = Math.abs(val) <= 15;
                       const meter = isMeter ? val : (val / 2265);
                       return meter.toFixed(3);
                     })()}m
                   </div>
                 </div>
              </div>
            </div>

            {/* Right Side: Status Indicators */}
            <div className="col-span-12 lg:col-span-4 flex flex-col items-center w-full pt-1 sm:pt-4">
              <h2 className="text-xl sm:text-2xl xl:text-3xl font-black uppercase tracking-[0.1em] xl:tracking-[0.2em] text-[#1a1a1a] mb-4 xl:mb-12 text-center">{t.status}</h2>
              
              <div className="grid grid-cols-3 gap-x-2 sm:gap-x-4 lg:gap-x-8 xl:gap-x-12 gap-y-4 lg:gap-y-10 xl:gap-y-16 w-full max-w-sm lg:max-w-none justify-items-center">
                 {/* P1 Pair */}
                 <div className="flex flex-col items-center gap-2 sm:gap-3 xl:gap-12">
                   <div className="flex flex-col items-center gap-1 xl:gap-4">
                     <span className="text-[10px] sm:text-[13px] font-black text-gray-400 tracking-wider uppercase">{t.full}</span>
                     <div className={cn(
                       "w-8 h-8 sm:w-10 sm:h-10 lg:w-16 lg:h-16 xl:w-24 xl:h-24 rounded-full border-[3px] sm:border-[4px] border-black transition-all duration-700",
                       isFull(craneState.p1) 
                         ? "bg-[#22c55e] scale-110 shadow-[0_0_30px_rgba(34,197,94,0.3)]" 
                         : "bg-white shadow-inner"
                     )} />
                   </div>
                   <div className="flex flex-col items-center gap-1 xl:gap-4">
                     <div className={cn(
                       "w-8 h-8 sm:w-10 sm:h-10 lg:w-16 lg:h-16 xl:w-24 xl:h-24 rounded-full border-[3px] sm:border-[4px] border-black transition-all duration-700",
                       !isFull(craneState.p1) 
                         ? "bg-[#ef4444] scale-110 shadow-[0_0_30px_rgba(239,68,68,0.3)]" 
                         : "bg-white shadow-inner"
                     )} />
                     <span className="text-[10px] sm:text-[13px] font-black text-gray-400 tracking-wider uppercase">{t.empty}</span>
                   </div>
                 </div>

                 {/* P2 Pair */}
                 <div className="flex flex-col items-center gap-2 sm:gap-3 xl:gap-12">
                   <div className="flex flex-col items-center gap-1 xl:gap-4">
                     <span className="text-[10px] sm:text-[13px] font-black text-gray-400 tracking-wider uppercase">{t.full}</span>
                     <div className={cn(
                       "w-8 h-8 sm:w-10 sm:h-10 lg:w-16 lg:h-16 xl:w-24 xl:h-24 rounded-full border-[3px] sm:border-[4px] border-black transition-all duration-700",
                       isFull(craneState.p2) 
                         ? "bg-[#22c55e] scale-110 shadow-[0_0_30px_rgba(34,197,94,0.3)]" 
                         : "bg-white shadow-inner"
                     )} />
                   </div>
                   <div className="flex flex-col items-center gap-1 xl:gap-4">
                     <div className={cn(
                       "w-8 h-8 sm:w-10 sm:h-10 lg:w-16 lg:h-16 xl:w-24 xl:h-24 rounded-full border-[3px] sm:border-[4px] border-black transition-all duration-700",
                       !isFull(craneState.p2) 
                         ? "bg-[#ef4444] scale-110 shadow-[0_0_30px_rgba(239,68,68,0.3)]" 
                         : "bg-white shadow-inner"
                     )} />
                     <span className="text-[10px] sm:text-[13px] font-black text-gray-400 tracking-wider uppercase">{t.empty}</span>
                   </div>
                 </div>

                 {/* P3 Pair */}
                 <div className="flex flex-col items-center gap-2 sm:gap-3 xl:gap-12">
                   <div className="flex flex-col items-center gap-1 xl:gap-4">
                     <span className="text-[10px] sm:text-[13px] font-black text-gray-400 tracking-wider uppercase">{t.full}</span>
                     <div className={cn(
                       "w-8 h-8 sm:w-10 sm:h-10 lg:w-16 lg:h-16 xl:w-24 xl:h-24 rounded-full border-[3px] sm:border-[4px] border-black transition-all duration-700",
                       isFull(craneState.p3) 
                         ? "bg-[#22c55e] scale-110 shadow-[0_0_30px_rgba(34,197,94,0.3)]" 
                         : "bg-white shadow-inner"
                     )} />
                   </div>
                   <div className="flex flex-col items-center gap-1 xl:gap-4">
                     <div className={cn(
                       "w-8 h-8 sm:w-10 sm:h-10 lg:w-16 lg:h-16 xl:w-24 xl:h-24 rounded-full border-[3px] sm:border-[4px] border-black transition-all duration-700",
                       !isFull(craneState.p3) 
                         ? "bg-[#ef4444] scale-110 shadow-[0_0_30px_rgba(239,68,68,0.3)]" 
                         : "bg-white shadow-inner"
                     )} />
                     <span className="text-[10px] sm:text-[13px] font-black text-gray-400 tracking-wider uppercase">{t.empty}</span>
                   </div>
                 </div>
               </div>
            </div>
          </div>

          {/* Bottom Control Section */}
          <div className="flex flex-col w-full items-center shrink-0 mb-8 sm:mb-0">
            {/* Round Controls */}
            <div className="flex flex-col gap-4 sm:gap-12 items-center lg:items-stretch w-full">
               <div className="flex flex-col sm:flex-row justify-around items-center gap-6 sm:gap-10 w-full">
                  {/* STOP */}
                  <div className="flex flex-col items-center gap-2 sm:gap-6">
                     <span className="text-[10px] sm:text-[13px] font-black uppercase tracking-widest text-[#ef4444]">STOP [Q]</span>
                     <button 
                       onClick={() => sendCommand('q')}
                       className={cn(
                         "w-24 h-24 sm:w-40 sm:h-40 rounded-full bg-transparent border-[6px] sm:border-[12px] flex items-center justify-center group relative transition-all active:scale-95 shadow-sm",
                         craneState.is_system_ready 
                          ? "border-[#ef4444] bg-[#ef4444]/5 shadow-[0_0_30px_rgba(239,68,68,0.2)] hover:scale-105" 
                          : "border-black/20 hover:scale-105 hover:border-black/45"
                       )}
                     >
                       <div className="absolute inset-1 sm:inset-2 rounded-full border-[2px] sm:border-[4px] border-black/5" />
                       <span className={cn(
                         "font-black text-lg sm:text-2xl tracking-tighter transition-colors",
                         craneState.is_system_ready ? "text-[#ef4444]" : "text-gray-400 group-hover:text-gray-600"
                       )}>STOP</span>
                     </button>
                  </div>

                  {/* AUTO */}
                  <div className="flex flex-col items-center gap-2 sm:gap-6">
                     <span className="text-[10px] sm:text-[13px] font-black uppercase tracking-widest text-[#22c55e]">AUTO [X]</span>
                     <button 
                       onClick={() => sendCommand('x')}
                       className={cn(
                         "w-24 h-24 sm:w-40 sm:h-40 rounded-full bg-transparent border-[6px] sm:border-[12px] flex items-center justify-center group relative transition-all active:scale-95 shadow-sm",
                         craneState.is_system_ready 
                          ? "border-[#22c55e] bg-[#22c55e]/5 shadow-[0_0_30px_rgba(34,197,94,0.2)] hover:scale-105" 
                          : "border-black/20 hover:scale-105 hover:border-black/45"
                       )}
                     >
                       <div className="absolute inset-1 sm:inset-2 rounded-full border-[2px] sm:border-[4px] border-black/5" />
                       <span className={cn(
                         "font-black text-lg sm:text-2xl tracking-tighter transition-colors",
                         craneState.is_system_ready ? "text-[#22c55e]" : "text-gray-400 group-hover:text-gray-600"
                       )}>AUTO</span>
                     </button>
                  </div>

                  {/* HOME */}
                  <div className="flex flex-col items-center gap-2 sm:gap-6">
                     <span className="text-[10px] sm:text-[13px] font-black uppercase tracking-widest text-[#0ea5e9]">HOME [H]</span>
                     <button 
                       onClick={() => sendCommand('h')}
                       className={cn(
                         "w-24 h-24 sm:w-40 sm:h-40 rounded-full bg-transparent border-[6px] sm:border-[12px] flex items-center justify-center group relative transition-all active:scale-95 shadow-sm",
                         craneState.is_system_ready 
                          ? "border-[#0ea5e9] bg-[#0ea5e9]/5 shadow-[0_0_30px_rgba(14,165,233,0.2)] hover:scale-105" 
                          : "border-black/20 hover:scale-105 hover:border-black/45"
                       )}
                     >
                       <div className="absolute inset-1 sm:inset-2 rounded-full border-[2px] sm:border-[4px] border-black/5" />
                       <span className={cn(
                         "font-black text-lg sm:text-2xl tracking-tighter transition-colors",
                         craneState.is_system_ready ? "text-[#0ea5e9]" : "text-gray-400 group-hover:text-gray-600"
                       )}>HOME</span>
                     </button>
                  </div>
               </div>

               {/* Start Program Buttons */}
               <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-8 px-4 w-full justify-center">
                  <button onClick={() => sendCommand('c1')} className="py-5 glass border-[4px] border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,0.1)] font-black uppercase text-[10px] sm:text-xs tracking-widest hover:translate-y-[-2px] hover:shadow-[12px_12px_0px_0px_rgba(0,0,0,0.05)] transition-all active:translate-y-[2px] active:shadow-none w-full rounded-3xl text-black">START PROGRAM 1</button>
                  <button onClick={() => sendCommand('c2')} className="py-5 glass border-[4px] border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,0.1)] font-black uppercase text-[10px] sm:text-xs tracking-widest hover:translate-y-[-2px] hover:shadow-[12px_12px_0px_0px_rgba(0,0,0,0.05)] transition-all active:translate-y-[2px] active:shadow-none w-full rounded-3xl text-black">START PROGRAM 2</button>
                  <button onClick={() => sendCommand('c3')} className="py-5 glass border-[4px] border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,0.1)] font-black uppercase text-[10px] sm:text-xs tracking-widest hover:translate-y-[-2px] hover:shadow-[12px_12px_0px_0px_rgba(0,0,0,0.05)] transition-all active:translate-y-[2px] active:shadow-none w-full rounded-3xl text-black">START PROGRAM 3</button>
               </div>
            </div>
          </div>
        </div>
          </motion.div>
        )}

        {/* Footer Meta */}
        <div className="mt-auto pt-10 flex flex-col md:flex-row justify-between items-center text-[9px] md:text-[10px] font-black uppercase tracking-[0.2em] text-gray-400 gap-4">
          <div className="flex gap-4">
            <span>CraneAI | KMUTNB beta 0.01</span>
            <span className="text-gray-200 hidden md:inline">|</span>
            <span className="hidden md:inline">SECURE_LINK: {connected ? "ACTIVE" : "PENDING"}</span>
          </div>
          <div className="text-black bg-gray-100 px-3 py-1 rounded">
            {currentTime}
          </div>
        </div>
      </div>

      {/* Image Enlarged Overlay */}
      {selectedImage && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => setSelectedImage(null)}
          className="fixed inset-0 z-[200] bg-black/90 backdrop-blur-md flex items-center justify-center p-4 sm:p-10 cursor-zoom-out"
        >
          <motion.div 
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="relative max-w-5xl w-full aspect-auto flex items-center justify-center"
          >
            <img 
              src={selectedImage} 
              alt="Enlarged view" 
              className="max-w-full max-h-[90vh] object-contain border-[10px] border-white shadow-2xl"
            />
            <div className="absolute top-4 right-4 bg-white text-black px-4 py-2 font-black uppercase text-xs tracking-widest shadow-xl">
              CLICK TO CLOSE
            </div>
          </motion.div>
        </motion.div>
      )}
    </div>
  </div>
  );
}
