# 微信控制 Claude Code CLI 使用指南

## 项目概述

通过微信消息控制本机 Claude Code CLI，实现远程编程助手功能。

## 架构说明

```
微信用户
    ↓ (ilink bot HTTP API)
WeixinChannel (长轮询接收消息)
    ↓
ClaudeCodeBot (应用层维护对话历史)
    ↓
subprocess: claude -p "<prompt>" (每条消息独立进程)
    ↓
捕获输出 → 回复微信
```

### 核心特性

- ✅ 多轮对话支持（应用层维护历史上下文）
- ✅ 工作目录切换
- ✅ 会话管理（新建/重试/状态查询）
- ✅ 自动分段（输出过长时截断）
- ✅ 超时保护（默认 300 秒）
- ✅ 网络波动自动重连

## 快速开始

### 1. 安装依赖

```bash
cd /Users/mac/Documents/www/cc-weixin
pip3 install -r requirements.txt
pip3 install -r requirements-optional.txt
```

### 2. 配置文件

`config.json` 已配置完成：

```json
{
  "channel_type": "weixin",
  "bot_type": "claudecode",
  "claudecode_work_dir": "/Users/mac/Documents/www/cc-weixin",
  "claudecode_timeout": 300,
  "claudecode_max_history": 20,
  "claudecode_max_output_length": 3500
}
```

### 3. 启动服务

```bash
python3 app.py
```

首次启动会显示二维码，用微信扫码登录。

### 4. 守护进程（可选）

使用 `pm2` 或 `launchd` 保持服务常驻：

```bash
# 使用 pm2
npm install -g pm2
pm2 start app.py --name cc-weixin --interpreter python3
pm2 save
pm2 startup
```

## 微信命令使用

### 基础命令

| 命令 | 说明 | 示例 |
|---|---|---|
| `/help` | 显示帮助信息 | `/help` |
| `/pwd` | 显示当前工作目录 | `/pwd` |
| `/cd <路径>` | 切换工作目录 | `/cd /Users/mac/project` |
| `/status` | 查看状态（目录/历史/超时） | `/status` |
| `/new` | 开启新会话（清空历史） | `/new` |
| `/retry` | 重试上一条命令 | `/retry` |

### 对话示例

**示例1：多轮对话**

```
你: 帮我创建一个 Python 脚本，计算斐波那契数列
Claude: [创建 fib.py 文件]

你: 添加命令行参数支持
Claude: [修改 fib.py，添加 argparse]

你: 写个测试
Claude: [创建 test_fib.py]
```

**示例2：切换项目**

```
你: /pwd
Claude: 📁 当前目录: /Users/mac/Documents/www/cc-weixin

你: /cd /Users/mac/Documents/www/my-project
Claude: ✅ 已切换到: /Users/mac/Documents/www/my-project

你: 查看这个项目的 README
Claude: [读取并显示 README.md 内容]
```

**示例3：会话管理**

```
你: /status
Claude: 📊 状态信息
       📁 工作目录: /Users/mac/Documents/www/cc-weixin
       💬 历史记录: 5 轮对话
       ⏱️ 超时设置: 300 秒

你: /new
Claude: ✅ 已开启新会话，历史记录已清空
```

## 配置说明

### config.json 参数

| 参数 | 说明 | 默认值 |
|---|---|---|
| `channel_type` | 通道类型 | `"weixin"` |
| `bot_type` | Bot 类型 | `"claudecode"` |
| `claudecode_work_dir` | 默认工作目录 | 当前目录 |
| `claudecode_timeout` | 命令超时时间（秒） | `300` |
| `claudecode_max_history` | 最大历史记录数 | `20` |
| `claudecode_max_output_length` | 最大输出长度（字符） | `3500` |

### 微信登录凭证

凭证保存在 `~/.weixin_cow_credentials.json`，包含：
- `token`: 微信 bot token
- `base_url`: API 服务器地址
- `bot_id`: Bot ID
- `user_id`: 用户 ID

**重新登录**：删除该文件后重启服务。

## 异常处理

| 场景 | 表现 | 处理方式 |
|---|---|---|
| 执行超时 | 回复"⏱️ 执行超时" | 发送 `/retry` 重试 |
| 命令失败 | 回复"❌ 执行失败: ..." | 查看错误信息，调整命令 |
| 输出过长 | 自动截断 + 提示 | 正常，完整输出已保存在历史中 |
| 网络中断 | 自动重连 | 无需操作，等待重连 |
| Python 服务崩溃 | 无响应 | 重启服务或检查守护进程 |

## 测试验证

运行测试脚本验证功能：

```bash
python3 test_bot.py
```

测试覆盖：
- ✅ 命令解析（/help, /status, /pwd）
- ✅ Claude 执行（简单对话）
- ✅ 多轮对话记忆

## 文件结构

```
cc-weixin/
├── models/claudecode/
│   ├── __init__.py
│   └── claude_code_bot.py      # 核心 Bot 实现
├── common/const.py              # 添加 CLAUDECODE 常量
├── models/bot_factory.py        # 注册 ClaudeCodeBot
├── config.json                  # 配置文件
├── app.py                       # 主程序入口
├── test_bot.py                  # 测试脚本
└── README_CLAUDECODE.md         # 本文档
```

## 安全注意事项

1. **权限模式**：默认使用 `--permission-mode bypassPermissions`，Claude 会自动执行操作
2. **工作目录隔离**：每个用户独立的工作目录，避免冲突
3. **超时保护**：防止长时间阻塞
4. **环境变量清理**：自动移除 `CLAUDECODE` 避免嵌套检测

## 常见问题

### Q: 为什么不使用 `--resume` 保持会话？
A: `claude -p` 模式不保存 session，因此在应用层维护对话历史，每次调用时拼接上下文。

### Q: 如何处理多个用户同时使用？
A: 每个微信用户有独立的 `user_id`，对话历史和工作目录完全隔离。

### Q: 输出过长怎么办？
A: 自动截断到 3500 字符，可通过 `claudecode_max_output_length` 调整。

### Q: 如何查看完整日志？
A: 日志输出到终端，可重定向到文件：
```bash
python3 app.py > logs/app.log 2>&1
```

## 下一步优化

- [ ] 支持文件上传/下载（图片、代码文件）
- [ ] 添加用户权限控制（白名单）
- [ ] 支持多人协作（共享会话）
- [ ] 集成 Git 操作快捷命令
- [ ] 添加执行进度反馈（长任务）

## 技术支持

- 项目地址：https://github.com/zhayujie/chatgpt-on-wechat
- Claude Code 文档：https://docs.anthropic.com/claude/docs
