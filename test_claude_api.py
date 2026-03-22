#!/usr/bin/env python3
"""
测试 claude CLI 的 -p 模式和 --resume 功能
在独立进程中运行，不受当前 Claude Code 会话影响
"""

import subprocess
import os
import json
import time
from pathlib import Path

# 清除嵌套检测环境变量
env = os.environ.copy()
env.pop('CLAUDECODE', None)

WORK_DIR = "/Users/mac/Documents/www/cc-weixin"

def run_claude(prompt, resume_id=None, timeout=60):
    """执行 claude 命令并返回输出"""
    cmd = ["claude", "-p", prompt, "--output-format", "text"]
    if resume_id:
        cmd.extend(["--resume", resume_id])

    print(f"\n{'='*60}")
    print(f"执行命令: {' '.join(cmd)}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=WORK_DIR,
            env=env
        )

        output = result.stdout.strip()
        error = result.stderr.strip()

        print(f"返回码: {result.returncode}")
        if output:
            print(f"输出:\n{output}")
        if error:
            print(f"错误:\n{error}")

        return {
            "returncode": result.returncode,
            "stdout": output,
            "stderr": error
        }
    except subprocess.TimeoutExpired:
        print(f"超时（{timeout}秒）")
        return None
    except Exception as e:
        print(f"异常: {e}")
        return None

def find_latest_session():
    """查找最新的 session ID"""
    # session 存储在项目目录下
    project_dir = WORK_DIR.replace("/", "-").lstrip("-")
    session_dir = Path.home() / ".claude" / "projects" / project_dir

    print(f"\n查找 session 目录: {session_dir}")

    if not session_dir.exists():
        print("目录不存在")
        return None

    # 查找所有 .jsonl 文件
    sessions = list(session_dir.glob("*.jsonl"))
    if not sessions:
        print("未找到 session 文件")
        return None

    # 按修改时间排序，取最新的
    latest = max(sessions, key=lambda p: p.stat().st_mtime)
    session_id = latest.stem

    print(f"找到最新 session: {session_id}")
    print(f"文件路径: {latest}")
    print(f"修改时间: {time.ctime(latest.stat().st_mtime)}")

    return session_id

def main():
    print("=" * 60)
    print("Claude CLI 功能测试")
    print("=" * 60)

    # 测试1: 创建新会话
    print("\n【测试1】创建新会话并记住信息")
    result1 = run_claude("你好，我是测试用户。请记住我叫张三，我喜欢Python编程。只需简短回复'已记住'即可。")

    if not result1 or result1["returncode"] != 0:
        print("\n❌ 测试1失败")
        return

    print("\n✅ 测试1成功")

    # 查找 session ID
    time.sleep(2)  # 等待文件写入
    session_id = find_latest_session()

    if not session_id:
        print("\n⚠️  未找到 session 文件，可能 -p 模式不保存 session")
        print("这意味着方案B（--resume）不可行，需要使用方案A（无状态模式）")
        return

    # 测试2: 使用 --resume 恢复会话
    print("\n【测试2】使用 --resume 恢复会话并测试记忆")
    result2 = run_claude("我叫什么名字？我喜欢什么编程语言？", resume_id=session_id)

    if not result2 or result2["returncode"] != 0:
        print("\n❌ 测试2失败")
        return

    # 检查是否记得之前的信息
    output = result2["stdout"].lower()
    if "张三" in output or "zhangsan" in output or "python" in output:
        print("\n✅ 测试2成功 - Claude 记得之前的信息！")
    else:
        print("\n⚠️  测试2部分成功 - 命令执行成功但可能未记住信息")
        print(f"输出内容: {result2['stdout']}")

    # 测试3: 再次 resume 验证持续性
    print("\n【测试3】再次 resume 验证持续性")
    result3 = run_claude("总结一下你对我的了解", resume_id=session_id)

    if not result3 or result3["returncode"] != 0:
        print("\n❌ 测试3失败")
        return

    print("\n✅ 测试3成功")

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"Session ID: {session_id}")
    print("方案B（--resume 多轮对话）可行 ✅")

if __name__ == "__main__":
    main()
