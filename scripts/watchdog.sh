#!/bin/bash
# Hermes Gateway + SSH隧道 守护脚本
# 检查并自动重启gateway和SSH隧道

HERMES_VENV="/home/dministrator/hermes-agent/venv"
SSH_KEY="/home/dministrator/.ssh/hermes_server"
SERVER="root@123.207.4.102"
LOG_FILE="/home/dministrator/.hermes/logs/watchdog.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

# 检查SSH隧道
check_ssh_tunnel() {
    if ! pgrep -f "ssh.*-D 127.0.0.1:1080.*$SERVER" > /dev/null; then
        log "SSH隧道(SOCKS)已断开，重新启动..."
        nohup ssh -i "$SSH_KEY" \
            -o StrictHostKeyChecking=no \
            -o ServerAliveInterval=30 \
            -o ServerAliveCountMax=3 \
            -D 127.0.0.1:1080 \
            -N "$SERVER" > /dev/null 2>&1 &
        sleep 2
        log "SSH隧道(SOCKS)已重启，PID: $(pgrep -f 'ssh.*-D 127.0.0.1:1080')"
    fi
    
    if ! pgrep -f "ssh.*-L 127.0.0.1:9090:127.0.0.1:9090.*$SERVER" > /dev/null; then
        log "SSH隧道(WebSocket)已断开，重新启动..."
        nohup ssh -i "$SSH_KEY" \
            -o StrictHostKeyChecking=no \
            -o ServerAliveInterval=30 \
            -L 127.0.0.1:9090:127.0.0.1:9090 \
            -N "$SERVER" > /dev/null 2>&1 &
        sleep 2
        log "SSH隧道(WebSocket)已重启，PID: $(pgrep -f 'ssh.*-L 127.0.0.1:9090')"
    fi
}

# 检查Gateway
check_gateway() {
    if ! pgrep -f "hermes.*gateway run" > /dev/null; then
        log "Gateway已断开，重新启动..."
        source "$HERMES_VENV/bin/activate"
        nohup hermes gateway run --replace > /dev/null 2>&1 &
        sleep 5
        log "Gateway已重启，PID: $(pgrep -f 'hermes.*gateway run')"
    fi
}

# 主循环
log "=== Watchdog启动 ==="
while true; do
    check_ssh_tunnel
    check_gateway
    sleep 60
done
