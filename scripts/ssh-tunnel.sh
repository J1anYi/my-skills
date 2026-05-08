#!/bin/bash
SSH_KEY="$HOME/.ssh/tunnel_key"
SERVER="root@123.207.4.102"

# 启动SOCKS代理
ssh -i "$SSH_KEY" \
    -o StrictHostKeyChecking=no \
    -o PreferredAuthentications=publickey \
    -o ServerAliveInterval=30 \
    -o ServerAliveCountMax=3 \
    -D 127.0.0.1:1080 \
    -N \
    "$SERVER" &

SOCKS_PID=$!

# 启动端口转发
ssh -i "$SSH_KEY" \
    -o StrictHostKeyChecking=no \
    -o PreferredAuthentications=publickey \
    -o ServerAliveInterval=30 \
    -o ServerAliveCountMax=3 \
    -L 127.0.0.1:9090:127.0.0.1:9090 \
    -N \
    "$SERVER" &

PORT_PID=$!

# 等待任一进程退出
wait -n
kill $SOCKS_PID $PORT_PID 2>/dev/null
