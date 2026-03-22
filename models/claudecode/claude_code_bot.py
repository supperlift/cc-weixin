"""
Claude Code Bot - 通过微信控制本机 Claude Code CLI

架构：
- 每条消息启动独立的 claude -p 子进程
- 在应用层维护对话历史，实现多轮对话
- 支持工作目录切换、会话管理等命令
"""

import os
import subprocess
import time
from typing import Dict, List, Optional
from models.bot import Bot
from bridge.reply import Reply, ReplyType
from bridge.context import Context, ContextType
from common.log import logger
from config import conf


class ClaudeCodeBot(Bot):
    def __init__(self):
        super().__init__()
        # 每个用户的对话历史 {user_id: [{"role": "user/assistant", "content": "..."}]}
        self.conversations: Dict[str, List[Dict]] = {}
        # 每个用户的工作目录 {user_id: "/path/to/project"}
        self.work_dirs: Dict[str, str] = {}
        # 每个用户的上一条命令（用于重试）{user_id: "last_query"}
        self.last_queries: Dict[str, str] = {}

        # 配置
        self.default_work_dir = conf().get("claudecode_work_dir", os.getcwd())
        self.timeout = conf().get("claudecode_timeout", 300)
        self.max_history = conf().get("claudecode_max_history", 20)
        self.max_output_length = conf().get("claudecode_max_output_length", 3500)

        logger.info(f"[ClaudeCodeBot] 初始化完成，默认工作目录: {self.default_work_dir}")

    def reply(self, query: str, context: Context = None) -> Reply:
        """处理用户消息"""
        try:
            user_id = context.get("session_id", "default") if context else "default"

            # 处理特殊命令
            if query.startswith("/"):
                return self._handle_command(query, user_id)

            # 保存当前查询（用于重试）
            self.last_queries[user_id] = query

            # 获取工作目录
            work_dir = self.work_dirs.get(user_id, self.default_work_dir)

            # 获取对话历史
            history = self.conversations.get(user_id, [])

            # 构建完整 prompt
            full_prompt = self._build_prompt(history, query)

            # 执行 claude -p
            logger.info(f"[ClaudeCodeBot] 用户 {user_id} 执行命令，工作目录: {work_dir}")
            output = self._execute_claude(full_prompt, work_dir)

            # 保存到历史
            history.append({"role": "user", "content": query})
            history.append({"role": "assistant", "content": output})
            self.conversations[user_id] = history[-self.max_history:]

            # 处理过长输出
            if len(output) > self.max_output_length:
                truncated = output[:self.max_output_length]
                return Reply(ReplyType.TEXT,
                           f"{truncated}\n\n...\n[输出过长已截断，共 {len(output)} 字符]")

            return Reply(ReplyType.TEXT, output or "[无输出]")

        except subprocess.TimeoutExpired:
            logger.error(f"[ClaudeCodeBot] 执行超时")
            return Reply(ReplyType.TEXT, f"⏱️ 执行超时（{self.timeout}秒），请发送 /retry 重试")
        except Exception as e:
            logger.error(f"[ClaudeCodeBot] 执行失败: {e}", exc_info=True)
            return Reply(ReplyType.TEXT, f"❌ 执行失败: {str(e)}")

    def _handle_command(self, command: str, user_id: str) -> Reply:
        """处理特殊命令"""
        cmd = command.strip()

        # /cd - 切换工作目录
        if cmd.startswith("/cd "):
            new_dir = cmd[4:].strip()
            if not os.path.isdir(new_dir):
                return Reply(ReplyType.TEXT, f"❌ 目录不存在: {new_dir}")
            self.work_dirs[user_id] = new_dir
            logger.info(f"[ClaudeCodeBot] 用户 {user_id} 切换目录到: {new_dir}")
            return Reply(ReplyType.TEXT, f"✅ 已切换到: {new_dir}")

        # /pwd - 显示当前目录
        if cmd == "/pwd":
            work_dir = self.work_dirs.get(user_id, self.default_work_dir)
            return Reply(ReplyType.TEXT, f"📁 当前目录: {work_dir}")

        # /new - 开启新会话
        if cmd == "/new":
            self.conversations[user_id] = []
            logger.info(f"[ClaudeCodeBot] 用户 {user_id} 开启新会话")
            return Reply(ReplyType.TEXT, "✅ 已开启新会话，历史记录已清空")

        # /status - 查看状态
        if cmd == "/status":
            work_dir = self.work_dirs.get(user_id, self.default_work_dir)
            history_len = len(self.conversations.get(user_id, []))
            status = f"📊 状态信息\n"
            status += f"📁 工作目录: {work_dir}\n"
            status += f"💬 历史记录: {history_len // 2} 轮对话\n"
            status += f"⏱️ 超时设置: {self.timeout} 秒"
            return Reply(ReplyType.TEXT, status)

        # /retry - 重试上一条命令
        if cmd == "/retry":
            last_query = self.last_queries.get(user_id)
            if not last_query:
                return Reply(ReplyType.TEXT, "❌ 没有可重试的命令")
            logger.info(f"[ClaudeCodeBot] 用户 {user_id} 重试上一条命令")
            # 移除上一次的失败记录
            history = self.conversations.get(user_id, [])
            if len(history) >= 2:
                history = history[:-2]
                self.conversations[user_id] = history
            # 递归调用 reply 重新执行
            return self.reply(last_query, Context(ContextType.TEXT, last_query))

        # /help - 帮助信息
        if cmd == "/help":
            help_text = """🤖 Claude Code Bot 命令帮助

基本命令：
/pwd - 显示当前工作目录
/cd <路径> - 切换工作目录
/status - 查看当前状态
/new - 开启新会话（清空历史）
/retry - 重试上一条命令
/help - 显示此帮助

使用方式：
直接发送消息即可与 Claude Code 对话
支持多轮对话，会自动记住上下文"""
            return Reply(ReplyType.TEXT, help_text)

        return Reply(ReplyType.TEXT, f"❌ 未知命令: {cmd}\n发送 /help 查看帮助")

    def _build_prompt(self, history: List[Dict], new_query: str) -> str:
        """构建包含历史上下文的完整 prompt"""
        if not history:
            return new_query

        # 只取最近的对话（避免 prompt 过长）
        recent_history = history[-(self.max_history // 2 * 2):]  # 保证成对

        # 构建上下文
        context_parts = ["以下是之前的对话历史：\n"]
        for msg in recent_history:
            role = "用户" if msg["role"] == "user" else "Claude"
            content = msg["content"]
            # 截断过长的历史消息
            if len(content) > 500:
                content = content[:500] + "..."
            context_parts.append(f"{role}: {content}\n")

        context_parts.append(f"\n用户: {new_query}")
        return "\n".join(context_parts)

    def _execute_claude(self, prompt: str, work_dir: str) -> str:
        """执行 claude -p 命令"""
        # 准备环境变量（移除 CLAUDECODE 避免嵌套检测）
        env = os.environ.copy()
        env.pop('CLAUDECODE', None)

        # 构建命令（使用完整路径）
        claude_path = "/Users/mac/.local/bin/claude"
        cmd = [
            claude_path,
            "-p",
            prompt,
            "--output-format", "text",
            "--permission-mode", "bypassPermissions"  # 自动执行，不询问
        ]

        logger.debug(f"[ClaudeCodeBot] 执行命令: {' '.join(cmd[:3])}... (工作目录: {work_dir})")

        # 执行
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            cwd=work_dir,
            env=env
        )

        # 处理输出
        output = result.stdout.strip()
        error = result.stderr.strip()

        if result.returncode != 0:
            logger.error(f"[ClaudeCodeBot] 命令执行失败，返回码: {result.returncode}")
            if error:
                logger.error(f"[ClaudeCodeBot] 错误信息: {error}")
                return f"❌ 执行失败:\n{error}"
            return "❌ 执行失败，未返回错误信息"

        if not output and error:
            # 有些信息可能在 stderr 中
            return error

        return output or "[命令执行成功但无输出]"
