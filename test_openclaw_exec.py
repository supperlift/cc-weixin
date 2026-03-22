#!/usr/bin/env python3
"""
测试 OpenClaw 实际执行
"""

import sys
sys.path.insert(0, '/Users/mac/Documents/www/cc-weixin')

from models.openclaw.openclaw_bot import OpenClawBot
from bridge.context import Context, ContextType

def test_openclaw_execution():
    print("=" * 60)
    print("OpenClaw 执行测试")
    print("=" * 60)

    bot = OpenClawBot()
    user_id = "test_user"

    # 测试简单的 OpenClaw 命令
    print("\n【测试】发送简单消息给 OpenClaw")
    print("消息: 你好，请简短回复")

    context = Context(ContextType.TEXT, "你好，请简短回复")
    context["session_id"] = user_id

    try:
        reply = bot.reply("你好，请简短回复", context)
        print(f"\n返回类型: {reply.type}")
        print(f"返回内容:\n{reply.content}\n")

        if "执行失败" in reply.content or "❌" in reply.content:
            print("⚠️  OpenClaw 执行失败，可能需要检查配置")
        else:
            print("✅ OpenClaw 执行成功")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_openclaw_execution()
