#!/usr/bin/env python3
"""功能分支: Gazebo 与 ROS 2 的话题桥接.

	作用:
	把 Gazebo 侧的话题转换成 ROS 2 话题:

	启动参数:
	无.

"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
	# 1. 节点
	# Gazebo -> ROS 2: 仿真时钟
	clock_bridge = Node(
		package='ros_gz_bridge',
		executable='parameter_bridge',
		arguments=[
			'/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
		],
		output='screen',
	)

	# Gazebo -> ROS 2: 雷达点云
	c32_bridge = Node(
		package='ros_gz_bridge',
		executable='parameter_bridge',
		name='c32_bridge',
		arguments=[
			'/c32/points@sensor_msgs/msg/PointCloud2'
			'[ignition.msgs.PointCloudPacked',
		],
		remappings=[
			('/c32/points', '/points_raw'),
		],
		output='screen',
	)

	# 2. 组装启动描述
	return LaunchDescription([
		clock_bridge,
		c32_bridge,
	])
