#!/bin/bash
# Remotable Function Demo - 服务器启动脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

clear

echo "=========================================="
echo "Remotable Function Server"
echo "=========================================="
echo ""

# 检查是否在demo目录
if [ ! -d "server" ]; then
    echo -e "${RED}❌ 错误: 请在 demo 目录下运行此脚本${NC}"
    echo "   cd demo && ./start_server.sh"
    exit 1
fi

# 检查并安装 rich 库
if ! python3 -c "import rich" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  未检测到 rich 库，正在安装...${NC}"
    pip3 install rich -q
    echo -e "${GREEN}✓ rich 库安装完成${NC}"
    echo ""
fi

# 执行清理
echo "🧹 清理环境..."
if [ -d "test_files" ]; then
    rm -rf test_files
    echo -e "${GREEN}✓ 已清理测试文件${NC}"
fi
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo -e "${GREEN}✓ 已清理 Python 缓存${NC}"
echo ""

echo "启动服务器..."
echo ""
echo -e "${BLUE}提示：服务器将会：${NC}"
echo "  1. 监听 ws://0.0.0.0:8000"
echo "  2. 等待客户端连接"
echo "  3. 自动执行演示（读取、创建、修改文件等）"
echo ""
echo -e "${YELLOW}⚠️  重要：启动顺序${NC}"
echo "  1️⃣  先启动服务器（本终端）"
echo "  2️⃣  等服务器就绪后，再启动客户端（另一个终端）"
echo ""
echo "按 Ctrl+C 停止"
echo ""
echo "=========================================="
echo ""

# 进入 server 目录并启动
cd server
python3 main.py
