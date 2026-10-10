#!/usr/bin/env bash
# 关闭当前用户下所有 Gazebo 进程 (Fortress 的 ign gazebo 与新版 gz sim).
#
# 作用:
#   把 gazebo 本体以及启动它的包装 shell 一起收掉. 残留的 gz server 会继续往
#   /clock 里灌时间戳, 多个 gz server 交错两个仿真时间会让 ROS 侧时间倒退:
#   tf2_buffer 报 jump back in time, TF 被清空, rviz2 反复 Reset.
#
# 注意:
#   只处理当前用户自己的进程, 其他用户的 gazebo 不受影响.
#   本脚本不管 ros_gz_bridge / robot_state_publisher, 那些由 tools/kill_launch.sh 处理.

set -u

PATTERN='ign gazebo|gz sim'
GRACE_TICKS=50	# 每次 0.1 秒, 共 5 秒

SELF_PID=$$
# 父进程就是运行本脚本的 shell, 它的命令行里带着本脚本名, 要排除掉
PARENT_PID=$(ps -o ppid= -p "$SELF_PID" | tr -d ' ')

# ---------- 工具函数 ----------

# 打印仍然存活的那部分 PID, 每行一个
list_alive() {
	local pid
	for pid in "$@"; do
		kill -0 "$pid" 2>/dev/null && printf '%s\n' "$pid"
	done
}

# ---------- 1. 找出 gazebo 进程 ----------

gazebo_pids=()
while read -r pid; do
	[ -z "$pid" ] && continue
	[ "$pid" = "$SELF_PID" ] && continue
	[ "$pid" = "$PARENT_PID" ] && continue
	gazebo_pids+=("$pid")
done < <(pgrep -u "$(id -u)" -f "$PATTERN" 2>/dev/null || true)

if [ "${#gazebo_pids[@]}" -eq 0 ]; then
	echo '[kill_gazebo] 没有找到运行中的 gazebo 进程'
	exit 0
fi

echo "[kill_gazebo] 找到 ${#gazebo_pids[@]} 个 gazebo 进程:"
ps -o pid=,args= -p "${gazebo_pids[@]}"

# ---------- 2. 先 SIGTERM ----------

echo '[kill_gazebo] 发送 SIGTERM'
kill -TERM "${gazebo_pids[@]}" 2>/dev/null

ticks=0
while [ "$ticks" -lt "$GRACE_TICKS" ]; do
	[ -z "$(list_alive "${gazebo_pids[@]}")" ] && break
	sleep 0.1
	ticks=$((ticks + 1))
done

# ---------- 3. 顽固残留补 SIGKILL ----------

left=()
while read -r pid; do
	[ -n "$pid" ] && left+=("$pid")
done < <(list_alive "${gazebo_pids[@]}")

if [ "${#left[@]}" -gt 0 ]; then
	echo "[kill_gazebo] 强制结束 ${#left[@]} 个进程 (SIGKILL)"
	kill -KILL "${left[@]}" 2>/dev/null
	sleep 1
fi

# ---------- 4. 复查 ----------

left=()
while read -r pid; do
	[ -n "$pid" ] && left+=("$pid")
done < <(list_alive "${gazebo_pids[@]}")

if [ "${#left[@]}" -eq 0 ]; then
	echo '[kill_gazebo] 已全部关闭'
	exit 0
fi

echo "[kill_gazebo] 以下进程仍未退出:" >&2
for pid in "${left[@]}"; do
	ps -o pid=,args= -p "$pid" >&2
done
exit 1
