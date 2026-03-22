#!/usr/bin/env python3
"""
测试 ClaudeCodeBot 功能
模拟微信消息输入，验证 bot 是否正常工作
"""

import sys
import os

# 添加项目路径到 sys.path
sys.path.insert(0, '/Users/mac/Documents/www/cc-weixin')

from models.claudecode.claude_code_bot import ClaudeCodeBot
from bridge.context import Context, ContextType
from bridge.reply import ReplyType

def test_bot():
    print("=" * 60)
    print("ClaudeCodeBot 功能测试")
    print("=" * 60)

    # 创建 bot 实例
    bot = ClaudeCodeBot()
    user_id = "test_user"

    # 测试1: /help 命令
    print("\n【测试1】/help 命令")
    context = Context(ContextType.TEXT, "/help")
    context["session_id"] = user_id
    reply = bot.reply("/help", context)
    print(f"返回类型: {reply.type}")
    print(f"返回内容:\n{reply.content}\n")

    # 测试2: /status 命令
    print("\n【测试2】/status 命令")
    context = Context(ContextType.TEXT, "/status")
    context["session_id"] = user_id
    reply = bot.reply("/status", context)
    print(f"返回内容:\n{reply.content}\n")

    # 测试3: /pwd 命令
    print("\n【测试3】/pwd 命令")
    context = Context(ContextType.TEXT, "/pwd")
    context["session_id"] = user_id
    reply = bot.reply("/pwd", context)
    print(f"返回内容:\n{reply.content}\n")

    # 测试4: 简单的 Claude 命令（快速测试）
    print("\n【测试4】简单的 Claude 命令")
    print("发送: 你好，请简短回复'收到'即可")
    context = Context(ContextType.TEXT, "你好，请简短回复'收到'即可")
    context["session_id"] = user_id

    try:
        reply = bot.reply("你好，请简短回复'收到'即可", context)
        print(f"返回类型: {reply.type}")
        print(f"返回内容:\n{reply.content}\n")

        if reply.type == ReplyType.TEXT and reply.content:
            print("✅ 测试4成功 - Claude 正常响应")
        else:
            print("⚠️  测试4部分成功 - 有响应但可能不符合预期")
    except Exception as e:
        print(f"❌ 测试4失败: {e}")

    # 测试5: 多轮对话（测试历史记忆）
    print("\n【测试5】多轮对话测试")
    print("第一轮: 请记住我叫张三")
    context1 = Context(ContextType.TEXT, "请记住我叫张三，只需回复'已记住'")
    context1["session_id"] = user_id

    try:
        reply1 = bot.reply("请记住我叫张三，只需回复'已记住'", context1)
        print(f"第一轮回复:\n{reply1.content}\n")

        print("第二轮: 我叫什么名字？")
        context2 = Context(ContextType.TEXT, "我叫什么名字？")
        context2["session_id"] = user_id
        reply2 = bot.reply("我叫什么名字？", context2)
        print(f"第二轮回复:\n{reply2.content}\n")

        if "张三" in reply2.content or "zhangsan" in reply2.content.lower():
            print("✅ 测试5成功 - 多轮对话记忆正常")
        else:
            print("⚠️  测试5部分成功 - 可能未正确记住信息")
    except Exception as e:
        print(f"❌ 测试5失败: {e}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_bot()
