การเปิดใช้งาน ros / การเชื่อมต่อ pi / stm32
-------------------------------------
1 เปิดการเชื่อมต่อ stm32 - pi5 - Ros  (เปิดใน cmd)
-------------------------------------
cd Desktop
python udp_bridge1.py
-------------------------------------
2 เปิดการเชื่อมต่อ ros-rosbridge (website) (เปิดใน ubutu22.04)
-------------------------------------
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
-------------------------------------
3 เปิด gazebo (เปิดใน ubutu22.04)
-------------------------------------
source /opt/ros/humble/setup.bash

gazebo --verbose \
  -s libgazebo_ros_init.so \
  -s libgazebo_ros_factory.so
-------------------------------------
4 เปิด stl ของ model gazebo (เปิดใน ubutu22.04)
-------------------------------------
source /opt/ros/humble/setup.bash
ros2 run robot_state_publisher robot_state_publisher \
  ~/dev_ws/ros2_ws/src/crane_motor/urdf/cranemotor.urdf
------------------------------------
5 เปิด model เข้า gazebo (เปิดใน ubutu22.04)
------------------------------------
source /opt/ros/humble/setup.bash
ros2 run gazebo_ros spawn_entity.py -entity crane_motor -topic robot_description
------------------------------------
6 เปิดตัว control joint ต่างๆเข้า model (เปิดใน ubutu22.04)
------------------------------------
source /opt/ros/humble/setup.bash
ros2 control load_controller --set-state active joint_state_broadcaster
ros2 control load_controller --set-state active arm_group_controller
------------------------------------
7 main Program Ros ในการควบคุมต่าง (เปิดใน ubutu22.04)
------------------------------------
python3 ~/dev_ws/ros2_ws/src/crane_motor/scripts/mainROS.py
------------------------------------
8 main Program Pi ในการควบคุมต่าง  (เปิดใน pi5)
------------------------------------
cd ~/dev_ws
python3 mainPI.py
------------------------------------
9 3 point cloud  (เปิดใน ubutu22.04)
-------------------------------------
source /opt/ros/humble/setup.bash
rviz2
-------------------------------------------
export LIBGL_ALWAYS_SOFTWARE=1

# Terminal 1 - robot_state_publisher
ros2 run robot_state_publisher robot_state_publisher --ros-args -p robot_description:="$(xacro /home/pi/dev_ws/ros2_ws/src/crane_motor/urdf/cranemotor.urdf)"

-------------------------------------------
# Terminal 2 - joint_state_publisher_gui
ros2 run joint_state_publisher_gui joint_state_publisher_gui
---------------------------------------------
(เปิดใน ubutu22.04)
python3 ~/dev_ws/ros2_ws/src/crane_motor/scripts/simROS.py
---------------------------------------------
(เปิดใน pi5)
cd ~/dev_ws
python3 simPI.py
