#!/usr/bin/env python3
"""
测试 OpenClawBot 功能
"""

import sys
sys.path.insert(0, '/Users/mac/Documents/www/cc-weixin')

from models.openclaw.openclaw_bot import OpenClawBot
from bridge.context import Context, ContextType

def test_openclaw_bot():
    print("=" * 60)
    print("OpenClawBot 功能测试")
    print("=" * 60)

    # 创建 bot 实例
    bot = OpenClawBot()
    user_id = "test_user"

    # 测试1: /help 命令
    print("\n【测试1】/help 命令")
    context = Context(ContextType.TEXT, "/help")
    context["session_id"] = user_id
    reply = bot.reply("/help", context)
    print(f"返回内容:\n{reply.content}\n")

    # 测试2: /status 命令
    print("\n【测试2】/status 命令")
    context = Context(ContextType.TEXT, "/status")
    context["session_id"] = user_id
    reply = bot.reply("/status", context)
    print(f"返回内容:\n{reply.content}\n")

    # 测试3: 检查 OpenClaw 路径
    print("\n【测试3】检查 OpenClaw 配置")
    print(f"OpenClaw 路径: {bot.openclaw_path}")
    print(f"Node 路径: {bot.node_path}")
    print(f"工作目录: {bot.default_work_dir}")

    print("\n" + "=" * 60)
    print("基础测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_openclaw_bot()
