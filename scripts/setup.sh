#!/bin/bash
# 设置脚本 - 初始化飞书机器人监控项目

set -e

echo "🚀 BookFab 平台监控机器人 - 设置脚本"
echo "====================================="

# 检查 Python 版本
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python3，请先安装 Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Python 版本: $PYTHON_VERSION"

# 安装依赖
echo ""
echo "📦 安装依赖..."
pip3 install -r requirements.txt

# 创建日志目录
mkdir -p logs

# 检查配置文件
echo ""
echo "⚙️  检查配置..."
if [ ! -f "config/config.yaml" ]; then
    echo "⚠️  警告: 配置文件不存在，请复制 config/config.yaml.example 并修改"
fi

# 测试运行
echo ""
echo "🧪 测试运行..."
cd src && python3 main.py

echo ""
echo "✅ 设置完成！"
echo ""
echo "下一步:"
echo "1. 在 config/config.yaml 中配置飞书 Webhook URL"
echo "2. 运行 'python3 src/scheduler.py' 启动定时推送"
echo "3. 或使用 GitHub Actions 自动推送"
