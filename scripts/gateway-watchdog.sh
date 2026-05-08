#!/bin/bash
# Hermes SSH Tunnel + Gateway Watchdog
# 同时监控SSH隧道和Gateway，确保都在运行

SSH_KEY="$HOME/.ssh/tunnel_key"
SERVER="root@123.207.4.102"
LOG_FILE="$HOME/.hermes/logs/watchdog.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

check_ssh_tunnels() {
    SOCKS_RUNNING=$(ss -tlnp | grep "127.0.0.1:1080" | wc -l)
    PORT_RUNNING=$(ss -tlnp | grep "127.0.0.1:9090" | wc -l)
    
    if [ "$SOCKS_RUNNING" -eq 0 ]; then
        log "SOCKS隧道(1080)未运行，启动中..."
        ssh -i "$SSH_KEY" \
            -o StrictHostKeyChecking=no \
            -o PreferredAuthentications=publickey \
            -o ServerAliveInterval=30 \
            -o ServerAliveCountMax=3 \
            -D 127.0.0.1:1080 \
            -N \
            "$SERVER" &
        sleep 2
    fi
    
    if [ "$PORT_RUNNING" -eq 0 ]; then
        log "WebSocket隧道(9090)未运行，启动中..."
        ssh -i "$SSH_KEY" \
            -o StrictHostKeyChecking=no \
            -o PreferredAuthentications=publickey \
            -o ServerAliveInterval=30 \
            -o ServerAliveCountMax=3 \
            -L 127.0.0.1:9090:127.0.0.1:9090 \
            -N \
            "$SERVER" &
        sleep 2
    fi
}

check_gateway() {
    if pgrep -f "hermes gateway run" > /dev/null; then
        return 0  # 运行中
    else
        return 1  # 未运行
    fi
}

start_gateway() {
    log "Gateway未运行，启动中..."
    cd /home/administrator/hermes-agent
    source venv/bin/activate
    nohup hermes gateway run >> "$HOME/.hermes/logs/gateway.log" 2>&1 &
    sleep 5
    if check_gateway; then
        log "Gateway启动成功"
    else
        log "Gateway启动失败"
    fi
}

# 初始启动
log "Watchdog启动"
check_ssh_tunnels
sleep 2
start_gateway

# 主循环
while true; do
    check_ssh_tunnels
    if ! check_gateway; then
        start_gateway
    fi
    sleep 30
done
