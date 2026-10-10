#!/usr/bin/env python3
"""Gazebo (Fortress) 四轮差速小车仿真总入口.

	用法:
	ros2 launch bringup_gazebo gazebo.launch.py
	ros2 launch bringup_gazebo gazebo.launch.py gui:=false rviz:=false
	ros2 launch bringup_gazebo gazebo.launch.py world:="$(pwd)/src/bringup_gazebo/worlds/laser_test.sdf"

	控制器已重映射到标准 /cmd_vel:
	ros2 run teleop_twist_keyboard teleop_twist_keyboard

"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
	# 1. 路径
	pkg_share = get_package_share_directory('bringup_gazebo')
	include_dir = os.path.join(pkg_share, 'launch', 'include')
	rviz_config = os.path.join(pkg_share, 'rviz', 'gazebo.rviz')
	default_world = os.path.join(pkg_share, 'worlds', 'laser_test.sdf')
	default_model = os.path.join(pkg_share, 'urdf', 'robot_gazebo.urdf.xacro')

	# 2. 启动参数
	# 与 include/ 下各分支同名, 这里集中声明并向下传递,
	# 分支自身保留默认值, 便于单独运行调试.
	declare_use_sim_time = DeclareLaunchArgument(
		'use_sim_time',
		default_value='true',
		description='节点使用仿真时间(依赖 /clock 桥接)'
	)
	declare_world = DeclareLaunchArgument(
		'world',
		default_value=default_world,
		description='Gazebo world 文件(.sdf)'
	)
	declare_gui = DeclareLaunchArgument(
		'gui',
		default_value='true',
		description='是否启动 Gazebo 图形界面, false 表示 headless'
	)
	declare_spawn_z = DeclareLaunchArgument(
		'spawn_z',
		default_value='0.10',
		description='模型生成高度'
	)
	declare_model_file = DeclareLaunchArgument(
		'model_file',
		default_value=default_model,
		description='机器人模型 xacro 文件路径'
	)
	declare_rviz = DeclareLaunchArgument(
		'rviz',
		default_value='true',
		description='是否启动 RViz'
	)

	use_sim_time = LaunchConfiguration('use_sim_time')
	world = LaunchConfiguration('world')
	gui = LaunchConfiguration('gui')
	spawn_z = LaunchConfiguration('spawn_z')
	model_file = LaunchConfiguration('model_file')
	rviz = LaunchConfiguration('rviz')

	def include_branch(name, launch_arguments=None):
		"""引入 include/ 下的功能分支."""
		return IncludeLaunchDescription(
			PythonLaunchDescriptionSource(os.path.join(include_dir, name)),
			launch_arguments=(launch_arguments or {}).items(),
		)

	# 3. 六个功能分支
	branch_gazebo_world = include_branch('gazebo_world.launch.py', {
		'world': world,
		'gui': gui,
	})
	branch_robot_description = include_branch('robot_description.launch.py', {
		'model_file': model_file,
		'use_sim_time': use_sim_time,
	})
	branch_gazebo_robot = include_branch('gazebo_robot.launch.py', {
		'spawn_z': spawn_z,
	})
	branch_bridge = include_branch('bridge.launch.py')
	branch_control = include_branch('control.launch.py')

	# 4. RViz
	rviz_node = Node(
		package='rviz2',
		executable='rviz2',
		name='rviz2',
		output='screen',
		arguments=['-d', rviz_config],
		parameters=[{'use_sim_time': use_sim_time}],
		condition=IfCondition(rviz),
	)

	# 5. 组装启动描述
	return LaunchDescription([
		declare_use_sim_time,
		declare_world,
		declare_gui,
		declare_spawn_z,
		declare_model_file,
		declare_rviz,
		branch_gazebo_world,
		branch_robot_description,
		branch_gazebo_robot,
		branch_bridge,
		branch_control,
		rviz_node,
	])
