"""
RouterBot - 运行时无缝切换 AI bot

使用方式：
  config.json 设置 "bot_type": "router"
  在微信中发送 /switch <bot_type> 切换 bot
  发送 /bots 查看所有可用 bot
"""

from models.bot import Bot
from models.bot_factory import create_bot
from bridge.reply import Reply, ReplyType
from bridge.context import Context, ContextType
from common.log import logger
from config import conf

# 支持切换的 bot 类型及说明
AVAILABLE_BOTS = {
    "openclaw": "OpenClaw AI（MiniMax 驱动）",
    "claudecode": "Claude Code CLI",
    "chatgpt": "ChatGPT / OpenAI",
    "claudeAPI": "Claude API",
    "gemini": "Google Gemini",
    "minimax": "MiniMax",
    "moonshot": "Moonshot（Kimi）",
    "deepseek": "DeepSeek",
    "zhipu": "智谱 GLM",
    "dashscope": "阿里云百炼（Qwen）",
    "doubao": "字节豆包",
}


class RouterBot(Bot):
    def __init__(self):
        super().__init__()
        # 默认 bot：优先读配置中的 router_default_bot，否则用 openclaw
        default_type = conf().get("router_default_bot", "openclaw")
        self.current_type = default_type
        self.current_bot = self._load_bot(default_type)
        # 每个用户独立的 bot（可选，当前用全局 bot）
        logger.info(f"[RouterBot] 初始化完成，当前 bot: {self.current_type}")

    def reply(self, query: str, context: Context = None) -> Reply:
        cmd = query.strip()

        if cmd == "/bots":
            return self._list_bots()

        if cmd.startswith("/switch "):
            target = cmd[8:].strip()
            return self._switch_bot(target)

        if cmd == "/bot":
            desc = AVAILABLE_BOTS.get(self.current_type, self.current_type)
            return Reply(ReplyType.TEXT, f"当前 bot: {self.current_type}\n{desc}")

        # 普通消息转发给当前 bot
        logger.debug(f"[RouterBot] 转发消息给 {self.current_type}")
        return self.current_bot.reply(query, context)

    def _switch_bot(self, bot_type: str) -> Reply:
        if bot_type == self.current_type:
            return Reply(ReplyType.TEXT, f"当前已是 {bot_type}，无需切换")

        new_bot = self._load_bot(bot_type)
        if new_bot is None:
            available = "、".join(AVAILABLE_BOTS.keys())
            return Reply(ReplyType.TEXT,
                f"未知 bot 类型: {bot_type}\n可用: {available}\n发送 /bots 查看详情")

        old_type = self.current_type
        self.current_type = bot_type
        self.current_bot = new_bot
        logger.info(f"[RouterBot] 切换 bot: {old_type} → {bot_type}")
        desc = AVAILABLE_BOTS.get(bot_type, bot_type)
        return Reply(ReplyType.TEXT, f"已切换到: {bot_type}\n{desc}")

    def _load_bot(self, bot_type: str) -> Bot:
        try:
            bot = create_bot(bot_type)
            logger.info(f"[RouterBot] 加载 bot 成功: {bot_type}")
            return bot
        except Exception as e:
            logger.error(f"[RouterBot] 加载 bot 失败 {bot_type}: {e}")
            return None

    def _list_bots(self) -> Reply:
        lines = ["可用 AI Bot 列表：\n"]
        for bot_type, desc in AVAILABLE_BOTS.items():
            marker = "▶" if bot_type == self.current_type else "  "
            lines.append(f"{marker} {bot_type} - {desc}")
        lines.append("\n发送 /switch <类型> 切换")
        return Reply(ReplyType.TEXT, "\n".join(lines))
