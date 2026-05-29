cmake_minimum_required(VERSION 3.8)
project(crane_motor)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# ค้นหาแพ็กเกจที่เป็น ROS 2 (ห้ามมี catkin)
find_package(ament_cmake REQUIRED)
find_package(urdf REQUIRED)

# ติดตั้งโฟลเดอร์ต่างๆ ไปยังโฟลเดอร์ install
install(DIRECTORY
  config
  launch
  meshes
  urdf
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
