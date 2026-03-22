#!/bin/bash
# 测试通过 stdin 与 claude 交互式会话通信

unset CLAUDECODE

echo "=== 测试：通过 stdin 发送消息到 claude 交互式会话 ==="

# 使用 expect 或直接管道测试
# 方案1：使用 echo 管道（可能不工作，因为 claude 需要 TTY）
echo "你好，我叫张三" | timeout 10 claude --permission-mode bypassPermissions 2>&1 | head -20

echo ""
echo "=== 如果上面失败，说明需要 PTY 伪终端 ==="
