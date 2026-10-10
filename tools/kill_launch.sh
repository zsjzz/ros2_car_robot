#!/usr/bin/env bash
# 关闭当前用户下所有 ros2 launch 进程及其派生的子进程.
#
# 作用:
#   1. 先给 ros2 launch 发 SIGINT, 等价于在终端里按 Ctrl+C, 让它按正常流程关闭子节点;
#   2. 超时后对仍存活的进程补 SIGTERM, 再补 SIGKILL;
#   3. 递归处理整棵进程树, 避免留下孤儿节点.
#
# 为什么不能只 kill ros2 launch 的 PID:
#   SIGTERM 发给 ros2 launch 时子进程不会跟着退出, 变成孤儿后仍然占着
#   /clock /points_raw 等话题的发布者名额, 后续仿真就会出现重复发布者,
#   两个仿真时钟互相打架 -> TF 时间跳变 -> rviz2 反复 Reset.
#
# 注意:
#   只处理当前用户自己的进程, 不会影响其他用户.
#   本脚本不负责关 gazebo 本体, 那只 gz server 用 tools/kill_gazebo.sh 处理.

set -u

SELF_PID=$$
GRACE_TICKS=50	# 每次 0.1 秒, 共 5 秒

# ---------- 工具函数 ----------

# 递归输出一棵进程树的所有 PID, 先子后父
collect_tree() {
	local pid=$1
	local child
	for child in $(pgrep -P "$pid" 2>/dev/null); do
		collect_tree "$child"
	done
	printf '%s\n' "$pid"
}

# 打印仍然存活的那部分 PID, 每行一个
list_alive() {
	local pid
	for pid in "$@"; do
		kill -0 "$pid" 2>/dev/null && printf '%s\n' "$pid"
	done
}

# ---------- 1. 找出 ros2 launch 进程 ----------

launch_pids=()
while read -r pid; do
	[ -z "$pid" ] && continue
	[ "$pid" = "$SELF_PID" ] && continue
	launch_pids+=("$pid")
done < <(pgrep -u "$(id -u)" -f 'ros2 launch' 2>/dev/null || true)

if [ "${#launch_pids[@]}" -eq 0 ]; then
	echo '[kill_launch] 没有找到运行中的 ros2 launch 进程'
	exit 0
fi

echo "[kill_launch] 找到 ${#launch_pids[@]} 个 ros2 launch 进程:"
ps -o pid=,args= -p "${launch_pids[@]}"

# ---------- 2. 收集整棵进程树 ----------

tree_pids=()
for pid in "${launch_pids[@]}"; do
	while read -r p; do
		tree_pids+=("$p")
	done < <(collect_tree "$pid")
done

echo "[kill_launch] 进程树共 ${#tree_pids[@]} 个进程, 先发 SIGINT"

# ---------- 3. 优雅关闭 ----------

kill -INT "${launch_pids[@]}" 2>/dev/null

ticks=0
while [ "$ticks" -lt "$GRACE_TICKS" ]; do
	[ -z "$(list_alive "${tree_pids[@]}")" ] && break
	sleep 0.1
	ticks=$((ticks + 1))
done

# ---------- 4. 补 SIGTERM ----------

left=()
while read -r pid; do
	[ -n "$pid" ] && left+=("$pid")
done < <(list_alive "${tree_pids[@]}")

if [ "${#left[@]}" -gt 0 ]; then
	echo "[kill_launch] 仍有 ${#left[@]} 个进程未退出, 补发 SIGTERM"
	kill -TERM "${left[@]}" 2>/dev/null
	sleep 1
fi

# ---------- 5. 最后 SIGKILL ----------

left=()
while read -r pid; do
	[ -n "$pid" ] && left+=("$pid")
done < <(list_alive "${tree_pids[@]}")

if [ "${#left[@]}" -gt 0 ]; then
	echo "[kill_launch] 强制结束 ${#left[@]} 个进程 (SIGKILL)"
	kill -KILL "${left[@]}" 2>/dev/null
	sleep 1
fi

# ---------- 6. 复查 ----------

left=()
while read -r pid; do
	[ -n "$pid" ] && left+=("$pid")
done < <(list_alive "${tree_pids[@]}")

if [ "${#left[@]}" -eq 0 ]; then
	echo '[kill_launch] 已全部关闭'
	exit 0
fi

echo "[kill_launch] 以下进程仍未退出:" >&2
for pid in "${left[@]}"; do
	ps -o pid=,args= -p "$pid" >&2
done
exit 1
