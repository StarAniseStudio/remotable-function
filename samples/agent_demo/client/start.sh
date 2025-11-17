#!/bin/bash

# Client 启动脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo "=========================================="
echo -e "${CYAN}Remotable Function Client - 工具提供者${NC}"
echo "=========================================="
echo ""

# 检查是否在 client 目录
if [ ! -f "main.py" ]; then
    echo -e "${RED}错误: 请在 client 目录下运行此脚本${NC}"
    echo ""
    echo "正确用法:"
    echo "  cd agent_demo/client"
    echo "  ./start.sh"
    echo ""
    exit 1
fi

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 python3${NC}"
    echo ""
    echo "请安装 Python 3.8+:"
    echo "  - macOS: brew install python3"
    echo "  - Ubuntu: sudo apt install python3"
    echo ""
    exit 1
fi

# 显示 Python 版本
PYTHON_VERSION=$(python3 --version)
echo -e "${BLUE}Python 版本:${NC} $PYTHON_VERSION"
echo ""

# 检查依赖
echo -e "${YELLOW}检查依赖...${NC}"
if ! python3 -c "import rich" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Rich 未安装，自动安装依赖...${NC}"
    echo ""
    pip3 install -r requirements.txt
    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✓${NC} 依赖安装成功"
    else
        echo ""
        echo -e "${RED}✗${NC} 依赖安装失败"
        exit 1
    fi
else
    echo -e "${GREEN}✓${NC} 依赖已安装"
fi
echo ""

# 显示客户端信息
echo "=========================================="
echo -e "${CYAN}客户端信息${NC}"
echo "=========================================="
echo ""
echo -e "${BLUE}连接地址:${NC} ws://localhost:8000"
echo -e "${BLUE}客户端ID:${NC} ai-agent-tools"
echo ""
echo "=========================================="
echo ""

# 检查服务器连接
echo -e "${YELLOW}检查服务器连接...${NC}"
if command -v nc &> /dev/null; then
    if nc -z localhost 8000 2>/dev/null; then
        echo -e "${GREEN}✓${NC} 服务器已在运行 (localhost:8000)"
        echo ""
    else
        echo -e "${YELLOW}⚠️  服务器未运行（客户端会自动重连）${NC}"
        echo ""
    fi
else
    echo -e "${YELLOW}⚠️  无法检查服务器状态${NC}"
    echo ""
fi

# 启动客户端
echo -e "${GREEN}启动客户端...${NC}"
echo ""

python3 main.py

# 退出处理
echo ""
echo -e "${YELLOW}客户端已停止${NC}"
echo ""
