# cc-weixin 开机自启配置指南

## 快速开始

### 1. 安装服务（开机自启）

```bash
cd /Users/mac/Documents/www/cc-weixin
./ccweixin install
```

这会：
- 将服务配置复制到 `~/Library/LaunchAgents/`
- 立即启动服务
- 设置为开机自动启动

### 2. 管理服务

```bash
# 查看状态
./ccweixin status

# 停止服务
./ccweixin stop

# 启动服务
./ccweixin start

# 重启服务
./ccweixin restart

# 查看实时日志
./ccweixin logs

# 卸载服务
./ccweixin uninstall
```

---

## 可选：全局命令安装

如果希望在任意目录都能使用 `ccweixin` 命令，执行以下步骤：

### 方式1：添加到 PATH（推荐）

```bash
# 编辑 ~/.zshrc
echo 'export PATH="/Users/mac/Documents/www/cc-weixin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 现在可以在任意目录使用
ccweixin status
```

### 方式2：创建软链接

```bash
# 需要管理员权限
sudo ln -s /Users/mac/Documents/www/cc-weixin/ccweixin /usr/local/bin/ccweixin

# 现在可以在任意目录使用
ccweixin status
```

---

## 服务配置说明

### launchd 配置文件

位置：`~/Library/LaunchAgents/com.ccweixin.plist`

关键配置：
- `RunAtLoad`: 开机自动启动
- `KeepAlive`: 进程崩溃自动重启
- `WorkingDirectory`: 工作目录
- `StandardOutPath/StandardErrorPath`: 日志输出路径

### 日志文件

- **stdout**: `/Users/mac/Documents/www/cc-weixin/logs/stdout.log`
- **stderr**: `/Users/mac/Documents/www/cc-weixin/logs/stderr.log`

查看日志：
```bash
# 实时日志
./ccweixin logs

# 或直接查看文件
tail -f logs/stdout.log
tail -f logs/stderr.log
```

---

## 常见问题

### Q: 如何确认服务是否在运行？

```bash
./ccweixin status
```

或者：
```bash
launchctl list | grep com.ccweixin
```

### Q: 服务启动失败怎么办？

1. 查看错误日志：
```bash
cat logs/stderr.log
```

2. 检查 Python 路径是否正确：
```bash
which python3
```

3. 手动测试启动：
```bash
python3 app.py
```

### Q: 如何修改服务配置？

1. 编辑配置文件：
```bash
vim scripts/com.ccweixin.plist
```

2. 重新安装：
```bash
./ccweixin uninstall
./ccweixin install
```

### Q: 如何临时禁用开机自启？

```bash
./ccweixin stop
```

服务会停止，但下次开机仍会自动启动。如需永久禁用：
```bash
./ccweixin uninstall
```

### Q: 如何查看服务占用的资源？

```bash
# 查看进程信息
./ccweixin status

# 或使用 Activity Monitor（活动监视器）搜索 "python3"
```

---

## 手动管理（不使用 launchd）

如果不想使用开机自启，可以手动管理：

```bash
# 启动（后台运行）
cd /Users/mac/Documents/www/cc-weixin
nohup python3 app.py > logs/app.log 2>&1 &

# 查看进程
ps aux | grep "python3 app.py"

# 停止（找到 PID 后）
kill <PID>
```

---

## 卸载

完全移除服务：

```bash
# 1. 卸载 launchd 服务
./ccweixin uninstall

# 2. 删除项目（可选）
cd ~
rm -rf /Users/mac/Documents/www/cc-weixin

# 3. 移除全局命令（如果安装了）
sudo rm /usr/local/bin/ccweixin
# 或从 ~/.zshrc 中删除 PATH 配置
```

---

## 技术细节

### launchd vs cron

使用 `launchd` 而非 `cron` 的原因：
- macOS 原生服务管理器
- 支持开机自启
- 自动重启崩溃进程
- 更好的日志管理
- 环境变量继承

### 进程守护

`KeepAlive: true` 确保：
- 进程崩溃后自动重启
- 意外退出后立即恢复
- 无需手动监控

### 权限说明

服务运行在用户权限下（`~/Library/LaunchAgents/`），无需 root 权限。
