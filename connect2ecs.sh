#!/bin/bash

# 保存SSH密码（如果使用密码登录）
export SSHPASS='MCPTEST0606!!'

while true; do
    echo "[$(date)] Starting SSH tunnel..."
    
    # 启动SSH隧道
    ssh -N -L 12345:localhost:12345 \
        -o ServerAliveInterval=5 \
        -o ServerAliveCountMax=3 \
        -o TCPKeepAlive=yes \
        -o ExitOnForwardFailure=yes \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=10 \
        -o IPQoS=throughput \
        -o Compression=no \
        -o ConnectionAttempts=3 \
        root@47.84.80.161 &
    
    SSH_PID=$!
    
    # 持续检查连接
    while kill -0 $SSH_PID 2>/dev/null; do
        # 每分钟主动测试一次连接
        if ! timeout 5 nc -z localhost 12345 2>/dev/null; then
            echo "[$(date)] Port check failed, killing SSH..."
            kill $SSH_PID 2>/dev/null
            break
        fi
        sleep 60
    done
    
    echo "[$(date)] SSH tunnel died. Restarting in 3 seconds..."
    sleep 3
done
