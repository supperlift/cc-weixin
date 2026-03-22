# cc-weixin 快速使用指南

## 一键安装

```bash
cd /Users/mac/Documents/www/cc-weixin
./install.sh
```

安装完成后服务自动启动，并设置为开机自启。

## 命令行管理

```bash
# 查看状态
./ccweixin status

# 启动服务
./ccweixin start

# 停止服务
./ccweixin stop

# 重启服务
./ccweixin restart

# 查看实时日志
./ccweixin logs

# 卸载服务
./ccweixin uninstall
```

## 可选：全局命令

在 `~/.zshrc` 添加：

```bash
export PATH="/Users/mac/Documents/www/cc-weixin:$PATH"
```

然后在任意目录使用 `ccweixin` 命令。

## 微信使用

首次启动查看日志获取二维码：

```bash
./ccweixin logs
```

扫码登录后即可在微信中使用：

- `/help` - 查看帮助
- `/pwd` - 当前目录
- `/cd <路径>` - 切换目录
- `/status` - 查看状态
- `/new` - 新会话
- 直接发消息 - 与 Claude 对话

## 文件结构

```
cc-weixin/
├── ccweixin              # 命令行工具
├── install.sh            # 一键安装脚本
├── scripts/
│   ├── com.ccweixin.plist  # launchd 配置
│   ├── start.sh
│   ├── stop.sh
│   └── status.sh
├── logs/
│   ├── stdout.log        # 标准输出日志
│   └── stderr.log        # 错误日志
└── INSTALL.md            # 详细安装文档
```

详细文档见 `INSTALL.md`。
