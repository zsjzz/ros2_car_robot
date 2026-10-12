#!/usr/bin/env python3
"""功能分支: 三维点云转二维激光扫描.

	作用:
	用 pointcloud_to_laserscan 把桥接过来的三维点云 /points_raw
	(64000 点, 字段 x/y/z/intensity/ring, frame_id=laser_link) 按高度切片,
	投影成二维 LaserScan 并发布到 /scan, 供 RViz 或后续导航栈使用.

	启动参数:
	use_sim_time 是否使用仿真时间(依赖 /clock), 默认 true.
	target_frame 切片结果所在坐标系, 默认 laser_link; 点云会先变换到该坐标系
	             再取水平面切片, 输出的 LaserScan.header.frame_id 即该坐标系.
	min_height / max_height 参与切片的高度带(单位 m, 相对 target_frame),
	             默认 -0.20 / 0.30, 即雷达平面下方 0.20m 到上方 0.30m;
	             下界高于地面, 可滤掉雷达打在地面上的那一圈回波.
	range_min / range_max 有效测距范围(单位 m), 默认 0.15 / 70.0, 与 C32 雷达量程一致.

	注意:
	该节点在 /scan 下游无订阅者时不会订阅 /points_raw(懒订阅), 因此单独起本
	分支看不到点云被消费是正常现象; RViz 里勾上 LaserScan 显示项即可唤醒.

"""

import math

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
	# 1. 启动参数
	declare_use_sim_time = DeclareLaunchArgument(
		'use_sim_time',
		default_value='true',
		description='是否使用仿真时间(依赖 /clock)'
	)
	declare_target_frame = DeclareLaunchArgument(
		'target_frame',
		default_value='laser_link',
		description='LaserScan 输出的坐标系'
	)
	declare_min_height = DeclareLaunchArgument(
		'min_height',
		default_value='-0.20',
		description='切片高度带下界(m, 相对 target_frame)'
	)
	declare_max_height = DeclareLaunchArgument(
		'max_height',
		default_value='0.30',
		description='切片高度带上界(m, 相对 target_frame)'
	)
	declare_range_min = DeclareLaunchArgument(
		'range_min',
		default_value='0.15',
		description='有效测距范围下限(m)'
	)
	declare_range_max = DeclareLaunchArgument(
		'range_max',
		default_value='70.0',
		description='有效测距范围上限(m)'
	)

	use_sim_time = LaunchConfiguration('use_sim_time')
	target_frame = LaunchConfiguration('target_frame')
	min_height = LaunchConfiguration('min_height')
	max_height = LaunchConfiguration('max_height')
	range_min = LaunchConfiguration('range_min')
	range_max = LaunchConfiguration('range_max')

	# 2. 节点
	# 参数与 laser_gazebo.urdf.xacro 里的 C32 雷达对齐:
	#   水平 360 度 2000 线 -> angle_increment = 2*pi/2000
	#   10Hz -> scan_time = 0.1
	pointcloud_to_laserscan = Node(
		package='pointcloud_to_laserscan',
		executable='pointcloud_to_laserscan_node',
		name='pointcloud_to_laserscan',
		output='screen',
		remappings=[
			('cloud_in', '/points_raw'),
			('scan', '/scan'),
		],
		parameters=[{
			'use_sim_time': use_sim_time,
			'target_frame': target_frame,
			'transform_tolerance': 0.01,
			'min_height': min_height,
			'max_height': max_height,
			'angle_min': -math.pi,
			'angle_max': math.pi,
			'angle_increment': 2.0 * math.pi / 2000.0,
			'scan_time': 0.1,
			'range_min': range_min,
			'range_max': range_max,
			'use_inf': True,
			'inf_epsilon': 1.0,
		}]
	)

	# 3. 组装启动描述
	return LaunchDescription([
		declare_use_sim_time,
		declare_target_frame,
		declare_min_height,
		declare_max_height,
		declare_range_min,
		declare_range_max,
		pointcloud_to_laserscan,
	])
