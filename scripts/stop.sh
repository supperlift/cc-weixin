#!/bin/bash
# 停止 cc-weixin 服务

if [ ! -f /tmp/cc-weixin.pid ]; then
    echo "❌ 服务未运行"
    exit 1
fi

PID=$(cat /tmp/cc-weixin.pid)

if ! ps -p $PID > /dev/null 2>&1; then
    echo "❌ 服务未运行 (PID 文件存在但进程不存在)"
    rm -f /tmp/cc-weixin.pid
    exit 1
fi

echo "🛑 停止 cc-weixin 服务 (PID: $PID)..."
kill $PID

# 等待进程结束
for i in {1..10}; do
    if ! ps -p $PID > /dev/null 2>&1; then
        echo "✅ 服务已停止"
        rm -f /tmp/cc-weixin.pid
        exit 0
    fi
    sleep 1
done

# 强制杀死
echo "⚠️  进程未响应，强制停止..."
kill -9 $PID
rm -f /tmp/cc-weixin.pid
echo "✅ 服务已强制停止"
