#!/bin/bash
# Remotable Function Demo - 客户端启动脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear

echo "=========================================="
echo "Remotable Function Client"
echo "=========================================="
echo ""

# 检查是否在demo目录
if [ ! -d "client" ]; then
    echo "❌ 错误: 请在 demo 目录下运行此脚本"
    echo "   cd demo && ./start_client.sh"
    exit 1
fi

# 检查并安装 rich 库
if ! python3 -c "import rich" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  未检测到 rich 库，正在安装...${NC}"
    pip3 install rich -q
    echo -e "${GREEN}✓ rich 库安装完成${NC}"
    echo ""
fi

# 清理旧的测试文件
if [ -d "test_files" ]; then
    echo "🗑️  清理旧的测试文件..."
    rm -rf test_files
fi

echo ""
echo "启动客户端..."
echo ""
echo -e "${BLUE}提示：客户端将会：${NC}"
echo "  1. 创建测试文件目录"
echo "  2. 注册 5 个内置工具"
echo "  3. 连接到 ws://localhost:8000"
echo ""
echo -e "${YELLOW}⚠️  重要：请先确保服务器已启动${NC}"
echo ""
echo "按 Ctrl+C 停止"
echo ""
echo "=========================================="
echo ""

# 进入 client 目录并启动
cd client
python3 main.py
