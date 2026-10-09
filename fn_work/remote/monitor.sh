#!/bin/bash
# 训练实时监测器：每 60s 心跳写 STATUS.log + status.txt 快照（可随时 cat 查看）
cd ~/ptcg-train
while true; do
  TS=$(date "+%H:%M:%S")
  PROCS=$(pgrep -fc "train_si[l]|train_es|train_sel" || echo 0)
  LOAD=$(uptime | grep -oP 'load average: \K.*')
  GPU=$(/usr/lib/wsl/lib/nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader 2>/dev/null | head -1)
  FRESH=$(stat -c %Y sil.log 2>/dev/null || echo 0)
  NOW=$(date +%s)
  AGE=$((NOW - FRESH))
  LAST=$(tail -1 sil.log 2>/dev/null | cut -c1-120)
  echo "$TS procs=$PROCS load=$LOAD gpu=$GPU log_age=${AGE}s | $LAST" >> STATUS.log
  cat > status.txt << TXT
=== PTCG 训练状态 $TS ===
进程数: $PROCS (0=训练已停!)
CPU负载: $LOAD  (32核满载应~32)
GPU: $GPU  (当前负载 CPU 型，GPU 闲=正常；CPU 欠载=异常)
日志新鲜度: ${AGE}s 前 (秒数大=卡死)
最新成绩: $LAST
STATUS.log 逐分钟心跳持续累积中
TXT
  tail -100 STATUS.log > STATUS.trim && mv STATUS.trim STATUS.log
  sleep 60
done
