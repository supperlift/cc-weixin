"""
OpenClaw Bot - 通过微信控制本机 OpenClaw AI Assistant

架构：
- 每条消息启动独立的 openclaw agent 子进程
- 同步执行，后台线程监控进度
- 超过1分钟未完成时发送进度提示
- 在应用层维护对话历史，实现多轮对话
- 支持工作目录切换、会话管理等命令
"""

import os
import subprocess
import threading
import time
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
        self.progress_interval = conf().get("openclaw_progress_interval", 60)  # 进度推送间隔（秒）

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

            # 执行 openclaw agent（同步执行，带进度监控）
            logger.info(f"[OpenClawBot] 用户 {user_id} 执行命令，工作目录: {work_dir}")
            output = self._execute_openclaw_with_progress(full_prompt, work_dir, user_id, context)

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

    def _execute_openclaw_with_progress(self, prompt: str, work_dir: str, user_id: str, context: Context) -> str:
        """执行 OpenClaw 并监控进度"""
        # 准备环境和命令
        env = os.environ.copy()
        env["PATH"] = f"{os.path.dirname(self.node_path)}:{env.get('PATH', '')}"

        import re
        clean_user_id = re.sub(r'[^a-zA-Z0-9-]', '-', user_id)
        session_id = f"weixin-{clean_user_id}"

        cmd = [
            self.node_path,
            f"{self.openclaw_path}/openclaw.mjs",
            "--no-color",
            "agent",
            "--local",
            "--session-id", session_id,
            "--message", prompt,
            "--thinking", "low"
        ]

        logger.debug(f"[OpenClawBot] 执行命令: {' '.join(cmd[:5])}...")

        # 启动进程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=work_dir,
            env=env
        )

        # 启动进度监控线程
        completed = {"value": False}

        def monitor_progress():
            """监控进度，超过1分钟未完成时发送提示"""
            time.sleep(self.progress_interval)  # 等待第一个间隔（60秒）

            while not completed["value"]:
                # 发送进度提示
                try:
                    self._send_message(context, "⏳ 任务执行中，请稍候...")
                    logger.info(f"[OpenClawBot] 发送进度提示: {user_id}")
                except Exception as e:
                    logger.error(f"[OpenClawBot] 发送进度失败: {e}")

                # 等待下一个间隔
                time.sleep(self.progress_interval)

        progress_thread = threading.Thread(target=monitor_progress)
        progress_thread.daemon = True
        progress_thread.start()

        # 等待进程完成
        try:
            stdout, stderr = process.communicate(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            completed["value"] = True
            raise
        finally:
            completed["value"] = True

        # 处理输出
        raw_output = stdout.strip()
        lines = raw_output.splitlines()
        clean_lines = [
            line for line in lines
            if not line.startswith("[plugins]") and "Registered" not in line
        ]
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
        output = ansi_escape.sub('', '\n'.join(clean_lines)).strip()

        if process.returncode != 0:
            error_msg = stderr.strip() if stderr else "执行失败，未返回错误信息"
            logger.error(f"[OpenClawBot] 命令执行失败，返回码: {process.returncode}")
            return f"❌ {error_msg}"

        return output or "[命令执行成功但无输出]"

    def _send_message(self, context: Context, message: str):
        """发送消息到微信"""
        try:
            from channel.channel_factory import create_channel
            channel_type = context.get("channel_type", "weixin")
            channel = create_channel(channel_type)
            reply = Reply(ReplyType.TEXT, message)
            channel.send(reply, context)
        except Exception as e:
            logger.error(f"[OpenClawBot] 发送消息失败: {e}", exc_info=True)

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
            ctx = Context(ContextType.TEXT, last_query)
            ctx["session_id"] = user_id
            return self.reply(last_query, ctx)

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
支持多轮对话，会自动记住上下文
长时间任务会每分钟发送进度提示"""
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
