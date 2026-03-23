"""
OpenClaw Bot - 通过微信控制本机 OpenClaw AI Assistant

架构：
- 每条消息启动独立的 openclaw agent 子进程
- 异步执行，每分钟推送进度更新
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
        # 正在执行的任务
        self.running_tasks: Dict[str, dict] = {}

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

            # 检查是否有正在执行的任务
            if user_id in self.running_tasks:
                return Reply(ReplyType.TEXT, "⏳ 上一个任务还在执行中，请稍候...")

            # 保存当前查询
            self.last_queries[user_id] = query

            # 获取工作目录
            work_dir = self.work_dirs.get(user_id, self.default_work_dir)

            # 获取对话历史
            history = self.conversations.get(user_id, [])

            # 构建完整 prompt
            full_prompt = self._build_prompt(history, query)

            # 启动异步执行
            logger.info(f"[OpenClawBot] 用户 {user_id} 执行命令，工作目录: {work_dir}")
            self._execute_openclaw_async(full_prompt, work_dir, user_id, context)

            return Reply(ReplyType.TEXT, "🚀 任务已开始执行，我会每分钟向你报告进度...")

        except Exception as e:
            logger.error(f"[OpenClawBot] 执行失败: {e}", exc_info=True)
            return Reply(ReplyType.TEXT, f"❌ 执行失败: {str(e)}")

    def _execute_openclaw_async(self, prompt: str, work_dir: str, user_id: str, context: Context):
        """异步执行 OpenClaw 并定时推送进度"""
        def run_task():
            try:
                # 标记任务开始
                start_time = time.time()
                self.running_tasks[user_id] = {
                    "start_time": start_time,
                    "process": None,
                    "completed": False
                }

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
                self.running_tasks[user_id]["process"] = process

                # 启动进度推送线程
                progress_thread = threading.Thread(
                    target=self._send_progress_updates,
                    args=(user_id, context, start_time)
                )
                progress_thread.daemon = True
                progress_thread.start()

                # 等待进程完成
                try:
                    stdout, stderr = process.communicate(timeout=self.timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                    self._send_final_result(user_id, context, "⏱️ 执行超时", is_error=True)
                    return

                # 标记任务完成
                self.running_tasks[user_id]["completed"] = True

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
                    self._send_final_result(user_id, context, f"❌ {error_msg}", is_error=True)
                    return

                # 保存到历史
                history = self.conversations.get(user_id, [])
                history.append({"role": "user", "content": self.last_queries.get(user_id, "")})
                history.append({"role": "assistant", "content": output})
                self.conversations[user_id] = history[-self.max_history:]

                # 发送最终结果
                final_output = output or "[命令执行成功但无输出]"
                if len(final_output) > self.max_output_length:
                    final_output = f"{final_output[:self.max_output_length]}\n\n...\n[输出过长已截断，共 {len(final_output)} 字符]"

                self._send_final_result(user_id, context, f"✅ 任务完成\n\n{final_output}")

            except Exception as e:
                logger.error(f"[OpenClawBot] 异步执行失败: {e}", exc_info=True)
                self._send_final_result(user_id, context, f"❌ 执行失败: {str(e)}", is_error=True)
            finally:
                # 清理任务状态
                if user_id in self.running_tasks:
                    del self.running_tasks[user_id]

        # 启动后台线程
        thread = threading.Thread(target=run_task)
        thread.daemon = True
        thread.start()

    def _send_progress_updates(self, user_id: str, context: Context, start_time: float):
        """定时发送进度更新"""
        try:
            while user_id in self.running_tasks and not self.running_tasks[user_id]["completed"]:
                time.sleep(self.progress_interval)

                if user_id not in self.running_tasks or self.running_tasks[user_id]["completed"]:
                    break

                elapsed = int(time.time() - start_time)
                minutes = elapsed // 60
                seconds = elapsed % 60

                progress_msg = f"⏳ 任务执行中... 已运行 {minutes}分{seconds}秒"

                # 发送进度消息
                self._send_message(context, progress_msg)
                logger.info(f"[OpenClawBot] 发送进度更新: {user_id} - {progress_msg}")

        except Exception as e:
            logger.error(f"[OpenClawBot] 进度推送失败: {e}", exc_info=True)

    def _send_final_result(self, user_id: str, context: Context, message: str, is_error: bool = False):
        """发送最终结果"""
        try:
            self._send_message(context, message)
            if is_error:
                logger.error(f"[OpenClawBot] 任务失败: {user_id}")
            else:
                logger.info(f"[OpenClawBot] 任务完成: {user_id}")
        except Exception as e:
            logger.error(f"[OpenClawBot] 发送最终结果失败: {e}", exc_info=True)

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
            is_running = user_id in self.running_tasks
            status = f"📊 OpenClaw 状态\n"
            status += f"📁 工作目录: {work_dir}\n"
            status += f"💬 历史记录: {history_len // 2} 轮对话\n"
            status += f"⏱️ 超时设置: {self.timeout} 秒\n"
            status += f"🔄 任务状态: {'执行中' if is_running else '空闲'}"
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
长时间任务会每分钟报告进度"""
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
