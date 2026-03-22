#!/bin/bash
# cc-weixin 一键安装脚本

set -e

echo "=================================="
echo "cc-weixin 一键安装"
echo "=================================="
echo ""

# 检查 Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，请先安装 Python 3"
    exit 1
fi

echo "✅ Python3: $(python3 --version)"

# 创建虚拟环境
echo ""
if [ ! -d "venv" ]; then
    echo "📦 创建 Python 虚拟环境..."
    python3 -m venv venv
    echo "✅ 虚拟环境已创建"
else
    echo "✅ 虚拟环境已存在"
fi

# 激活虚拟环境并安装依赖
echo ""
echo "📦 安装 Python 依赖..."
cd /Users/mac/Documents/www/cc-weixin
source venv/bin/activate
pip install -r requirements-minimal.txt -q
echo "✅ 核心依赖安装完成（精简版，适配 Python 3.14）"

# 创建日志目录
mkdir -p logs
echo "✅ 日志目录已创建"

# 安装 launchd 服务
echo ""
echo "📦 安装开机自启服务..."
./ccweixin install

echo ""
echo "=================================="
echo "✅ 安装完成！"
echo "=================================="
echo ""
echo "服务已启动并设置为开机自启"
echo ""
echo "常用命令："
echo "  ./ccweixin status   - 查看服务状态"
echo "  ./ccweixin logs     - 查看实时日志"
echo "  ./ccweixin stop     - 停止服务"
echo "  ./ccweixin start    - 启动服务"
echo ""
echo "首次使用请扫描二维码登录微信"
echo "日志位置: logs/stdout.log"
echo ""
