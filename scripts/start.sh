#!/bin/bash
# 启动 cc-weixin 服务

cd /Users/mac/Documents/www/cc-weixin

# 检查是否已在运行
if [ -f /tmp/cc-weixin.pid ]; then
    PID=$(cat /tmp/cc-weixin.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "❌ 服务已在运行 (PID: $PID)"
        exit 1
    fi
fi

# 启动服务
echo "🚀 启动 cc-weixin 服务..."
nohup python3 app.py > logs/app.log 2>&1 &
PID=$!
echo $PID > /tmp/cc-weixin.pid

# 等待启动
sleep 2

if ps -p $PID > /dev/null 2>&1; then
    echo "✅ 服务启动成功 (PID: $PID)"
    echo "📝 日志文件: logs/app.log"
else
    echo "❌ 服务启动失败，查看日志: logs/app.log"
    rm -f /tmp/cc-weixin.pid
    exit 1
fi
