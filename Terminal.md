# 🚀 การเปิดใช้งานระบบ ROS / การเชื่อมต่อ Pi / STM32

---

## โหมดที่ 1 — ระบบทำงานจริง (Main System)

### ขั้นที่ 1 — เปิดการเชื่อมต่อ STM32 → Pi5 → ROS

เปิดใน **Windows CMD**

```bash
cd Desktop
```

```bash
python udp_bridge1.py
```

---

### ขั้นที่ 2 — เปิดการเชื่อมต่อ ROS ↔ Website (ROSBridge)

เปิดใน **Ubuntu 22.04**

```bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

---

### ขั้นที่ 3 — เปิด Gazebo

เปิดใน **Ubuntu 22.04**

```bash
source /opt/ros/humble/setup.bash
```

```bash
gazebo --verbose \
  -s libgazebo_ros_init.so \
  -s libgazebo_ros_factory.so
```

---

### ขั้นที่ 4 — โหลด URDF Model เข้า Gazebo

เปิดใน **Ubuntu 22.04**

```bash
source /opt/ros/humble/setup.bash
```

```bash
ros2 run robot_state_publisher robot_state_publisher \
  ~/dev_ws/ros2_ws/src/crane_motor/urdf/cranemotor.urdf
```

---

### ขั้นที่ 5 — Spawn Model เข้า Gazebo

เปิดใน **Ubuntu 22.04**

```bash
source /opt/ros/humble/setup.bash
```

```bash
ros2 run gazebo_ros spawn_entity.py \
  -entity crane_motor \
  -topic robot_description
```

---

### ขั้นที่ 6 — โหลด Joint Controllers

เปิดใน **Ubuntu 22.04**

```bash
source /opt/ros/humble/setup.bash
```

```bash
ros2 control load_controller --set-state active joint_state_broadcaster
```

```bash
ros2 control load_controller --set-state active arm_group_controller
```

---

### ขั้นที่ 7 — Main Program ROS

เปิดใน **Ubuntu 22.04**

```bash
python3 ~/dev_ws/ros2_ws/src/crane_motor/scripts/mainROS.py
```

---

### ขั้นที่ 8 — Main Program Pi

เปิดใน **Raspberry Pi 5**

```bash
cd ~/dev_ws
```

```bash
python3 mainPI.py
```

---

## โหมดที่ 2 — Point Cloud Simulation (RViz2)

### ขั้นที่ 1 — เปิด RViz2

เปิดใน **Ubuntu 22.04**

```bash
source /opt/ros/humble/setup.bash
```

```bash
rviz2
```

---

### ขั้นที่ 2 — เปิด robot_state_publisher พร้อม xacro

เปิดใน **Ubuntu 22.04** — Terminal 1

```bash
export LIBGL_ALWAYS_SOFTWARE=1
```

```bash
ros2 run robot_state_publisher robot_state_publisher \
  --ros-args -p robot_description:="$(xacro /home/pi/dev_ws/ros2_ws/src/crane_motor/urdf/cranemotor.urdf)"
```

---

### ขั้นที่ 3 — เปิด Joint State Publisher GUI

เปิดใน **Ubuntu 22.04** — Terminal 2

```bash
ros2 run joint_state_publisher_gui joint_state_publisher_gui
```

---

### ขั้นที่ 4 — เปิด simROS

เปิดใน **Ubuntu 22.04**

```bash
python3 ~/dev_ws/ros2_ws/src/crane_motor/scripts/simROS.py
```

---

### ขั้นที่ 5 — เปิด simPI

เปิดใน **Raspberry Pi 5**

```bash
cd ~/dev_ws
```

```bash
python3 simPI.py
```
