"""
OpenClaw Bot - 通过微信控制本机 OpenClaw AI Assistant

架构：
- 每条消息启动独立的 openclaw agent 子进程
- 在应用层维护对话历史，实现多轮对话
- 支持工作目录切换、会话管理等命令
"""

import os
import subprocess
from typing import Dict, List
from models.bot import Bot
from bridge.reply import Reply, ReplyType
from bridge.context import Context, ContextType
from common.log import logger
from config import conf


class OpenClawBot(Bot):
    def __init__(self):
        super().__init__()
        # 每个用户的对话历史
        self.conversations: Dict[str, List[Dict]] = {}
        # 每个用户的工作目录
        self.work_dirs: Dict[str, str] = {}
        # 每个用户的上一条命令
        self.last_queries: Dict[str, str] = {}

        # 配置
        self.default_work_dir = conf().get("openclaw_work_dir", os.getcwd())
        self.timeout = conf().get("openclaw_timeout", 300)
        self.max_history = conf().get("openclaw_max_history", 20)
        self.max_output_length = conf().get("openclaw_max_output_length", 3500)

        # OpenClaw 路径配置
        self.openclaw_path = conf().get("openclaw_path", "/Users/mac/Documents/www/openclaw-ai/openclaw")
        self.node_path = conf().get("openclaw_node_path", "/Users/mac/.nvm/versions/node/v22.22.1/bin/node")

        logger.info(f"[OpenClawBot] 初始化完成，默认工作目录: {self.default_work_dir}")
        logger.info(f"[OpenClawBot] OpenClaw 路径: {self.openclaw_path}")

    def reply(self, query: str, context: Context = None) -> Reply:
        """处理用户消息"""
        try:
            user_id = context.get("session_id", "default") if context else "default"

            # 处理特殊命令
            if query.startswith("/"):
                return self._handle_command(query, user_id)

            # 保存当前查询
            self.last_queries[user_id] = query

            # 获取工作目录
            work_dir = self.work_dirs.get(user_id, self.default_work_dir)

            # 获取对话历史
            history = self.conversations.get(user_id, [])

            # 构建完整 prompt
            full_prompt = self._build_prompt(history, query)

            # 执行 openclaw agent
            logger.info(f"[OpenClawBot] 用户 {user_id} 执行命令，工作目录: {work_dir}")
            output = self._execute_openclaw(full_prompt, work_dir, user_id)

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
            logger.error(f"[OpenClawBot] 执行超时")
            return Reply(ReplyType.TEXT, f"⏱️ 执行超时（{self.timeout}秒），请发送 /retry 重试")
        except Exception as e:
            logger.error(f"[OpenClawBot] 执行失败: {e}", exc_info=True)
            return Reply(ReplyType.TEXT, f"❌ 执行失败: {str(e)}")

    def _handle_command(self, command: str, user_id: str) -> Reply:
        """处理特殊命令"""
        cmd = command.strip()

        if cmd.startswith("/cd "):
            new_dir = cmd[4:].strip()
            if not os.path.isdir(new_dir):
                return Reply(ReplyType.TEXT, f"❌ 目录不存在: {new_dir}")
            self.work_dirs[user_id] = new_dir
            logger.info(f"[OpenClawBot] 用户 {user_id} 切换目录到: {new_dir}")
            return Reply(ReplyType.TEXT, f"✅ 已切换到: {new_dir}")

        if cmd == "/pwd":
            work_dir = self.work_dirs.get(user_id, self.default_work_dir)
            return Reply(ReplyType.TEXT, f"📁 当前目录: {work_dir}")

        if cmd == "/new":
            self.conversations[user_id] = []
            logger.info(f"[OpenClawBot] 用户 {user_id} 开启新会话")
            return Reply(ReplyType.TEXT, "✅ 已开启新会话，历史记录已清空")

        if cmd == "/status":
            work_dir = self.work_dirs.get(user_id, self.default_work_dir)
            history_len = len(self.conversations.get(user_id, []))
            status = f"📊 OpenClaw 状态\n"
            status += f"📁 工作目录: {work_dir}\n"
            status += f"💬 历史记录: {history_len // 2} 轮对话\n"
            status += f"⏱️ 超时设置: {self.timeout} 秒"
            return Reply(ReplyType.TEXT, status)

        if cmd == "/retry":
            last_query = self.last_queries.get(user_id)
            if not last_query:
                return Reply(ReplyType.TEXT, "❌ 没有可重试的命令")
            logger.info(f"[OpenClawBot] 用户 {user_id} 重试上一条命令")
            history = self.conversations.get(user_id, [])
            if len(history) >= 2:
                history = history[:-2]
                self.conversations[user_id] = history
            return self.reply(last_query, Context(ContextType.TEXT, last_query))

        if cmd == "/help":
            help_text = """🦞 OpenClaw Bot 命令帮助

基本命令：
/pwd - 显示当前工作目录
/cd <路径> - 切换工作目录
/status - 查看当前状态
/new - 开启新会话（清空历史）
/retry - 重试上一条命令
/help - 显示此帮助

使用方式：
直接发送消息即可与 OpenClaw 对话
支持多轮对话，会自动记住上下文"""
            return Reply(ReplyType.TEXT, help_text)

        return Reply(ReplyType.TEXT, f"❌ 未知命令: {cmd}\n发送 /help 查看帮助")

    def _build_prompt(self, history: List[Dict], new_query: str) -> str:
        """构建包含历史上下文的完整 prompt"""
        if not history:
            return new_query

        recent_history = history[-(self.max_history // 2 * 2):]
        context_parts = ["以下是之前的对话历史：\n"]
        for msg in recent_history:
            role = "用户" if msg["role"] == "user" else "OpenClaw"
            content = msg["content"]
            if len(content) > 500:
                content = content[:500] + "..."
            context_parts.append(f"{role}: {content}\n")

        context_parts.append(f"\n用户: {new_query}")
        return "\n".join(context_parts)

    def _execute_openclaw(self, prompt: str, work_dir: str, user_id: str) -> str:
        """执行 openclaw agent 命令"""
        env = os.environ.copy()

        # 设置 Node 路径
        env["PATH"] = f"{os.path.dirname(self.node_path)}:{env.get('PATH', '')}"

        # 为每个用户生成唯一的 session_id
        session_id = f"weixin-{user_id}"

        # 构建命令 - 使用 openclaw agent --local 模式（不需要 Gateway）
        cmd = [
            self.node_path,
            f"{self.openclaw_path}/openclaw.mjs",
            "agent",
            "--local",  # 使用本地模式，不需要 Gateway
            "--session-id", session_id,
            "--message", prompt,
            "--thinking", "low"
        ]

        logger.debug(f"[OpenClawBot] 执行命令: {' '.join(cmd[:5])}...")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            cwd=work_dir,
            env=env
        )

        output = result.stdout.strip()
        error = result.stderr.strip()

        if result.returncode != 0:
            logger.error(f"[OpenClawBot] 命令执行失败，返回码: {result.returncode}")
            if error:
                logger.error(f"[OpenClawBot] 错误信息: {error}")
                return f"❌ 执行失败:\n{error}"
            return "❌ 执行失败，未返回错误信息"

        if not output and error:
            return error

        return output or "[命令执行成功但无输出]"
