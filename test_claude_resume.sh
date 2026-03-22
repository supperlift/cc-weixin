#!/bin/bash
# 测试 claude --resume 功能

# 清除嵌套检测环境变量
unset CLAUDECODE

echo "=== 测试1: 创建新会话并记住信息 ==="
SESSION_OUTPUT=$(claude -p "你好，我是测试用户。请记住我叫张三，我喜欢Python编程。只需简短回复即可。" --output-format text 2>&1)
echo "$SESSION_OUTPUT"

# 从输出中提取 session ID（假设在某处会显示）
# 或者直接查找最新的 session 文件
echo ""
echo "=== 查找最新的 session ID ==="
# session 存储在项目目录下，需要找到对应项目的 sessions
PROJECT_DIR=$(pwd | sed 's/\//-/g' | sed 's/^-//')
SESSION_DIR="$HOME/.claude/projects/$PROJECT_DIR"
echo "项目 session 目录: $SESSION_DIR"

LATEST_SESSION=$(ls -t "$SESSION_DIR"/*.jsonl 2>/dev/null | head -1 | xargs basename 2>/dev/null | sed 's/.jsonl$//')
echo "找到 session: $LATEST_SESSION"

if [ -z "$LATEST_SESSION" ]; then
    echo "错误：未找到 session 文件"
    exit 1
fi

echo ""
echo "=== 测试2: 使用 --resume 恢复会话并测试记忆 ==="
RESUME_OUTPUT=$(claude --resume "$LATEST_SESSION" -p "我叫什么名字？我喜欢什么编程语言？" --output-format text 2>&1)
echo "$RESUME_OUTPUT"

echo ""
echo "=== 测试3: 再次 resume 验证持续性 ==="
RESUME_OUTPUT2=$(claude --resume "$LATEST_SESSION" -p "总结一下你对我的了解" --output-format text 2>&1)
echo "$RESUME_OUTPUT2"
