#!/bin/bash
# 查看 cc-weixin 服务状态

if [ ! -f /tmp/cc-weixin.pid ]; then
    echo "❌ 服务未运行"
    exit 1
fi

PID=$(cat /tmp/cc-weixin.pid)

if ps -p $PID > /dev/null 2>&1; then
    echo "✅ 服务运行中"
    echo "📊 PID: $PID"
    echo "📝 日志: /Users/mac/Documents/www/cc-weixin/logs/app.log"
    echo ""
    echo "进程信息:"
    ps -p $PID -o pid,ppid,%cpu,%mem,etime,command
else
    echo "❌ 服务未运行 (PID 文件存在但进程不存在)"
    rm -f /tmp/cc-weixin.pid
    exit 1
fi
