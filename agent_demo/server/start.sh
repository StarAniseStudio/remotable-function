#!/bin/bash

# Server 启动脚本

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
echo -e "${MAGENTA}Remotable AI Agent Server${NC}"
echo "=========================================="
echo ""

# 检查是否在 server 目录
if [ ! -f "main.py" ]; then
    echo -e "${RED}错误: 请在 server 目录下运行此脚本${NC}"
    echo ""
    echo "正确用法:"
    echo "  cd agent_demo/server"
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

# 检查并加载 .env 文件
echo -e "${YELLOW}检查配置...${NC}"
if [ -f ".env" ]; then
    echo -e "${GREEN}✓${NC} 找到 .env 文件"

    # 从 .env 文件加载 OPENAI_API_KEY（如果环境变量未设置）
    if [ -z "$OPENAI_API_KEY" ]; then
        # 读取 .env 文件中的 OPENAI_API_KEY
        ENV_API_KEY=$(grep -E "^OPENAI_API_KEY=" .env | cut -d '=' -f 2- | tr -d '\r' | tr -d '"' | tr -d "'")
        if [ -n "$ENV_API_KEY" ]; then
            export OPENAI_API_KEY="$ENV_API_KEY"
            echo -e "${GREEN}✓${NC} 从 .env 加载 API Key"
        fi
    else
        echo -e "${GREEN}✓${NC} 使用环境变量中的 API Key"
    fi
else
    echo -e "${YELLOW}⚠️${NC}  未找到 .env 文件"
    echo ""
    echo "如需使用 AI 模式，可以:"
    echo -e "${CYAN}  1. 复制模板: cp .env.example .env${NC}"
    echo -e "${CYAN}  2. 编辑 .env 文件，填入你的 API Key${NC}"
    echo ""
fi
echo ""

# 检查 OPENAI_API_KEY 是否已设置
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  OPENAI_API_KEY 未设置${NC}"
    echo -e "${YELLOW}→  将使用简单模式（基于关键词匹配）${NC}"
    echo ""
else
    echo -e "${GREEN}✓${NC} OPENAI_API_KEY 已设置"

    # 检查 Agno
    if ! python3 -c "import agno" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Agno 未安装，将使用简单模式${NC}"
        echo ""
    else
        echo -e "${GREEN}✓${NC} AI 模式已启用"
        echo ""
    fi
fi

# 显示服务器信息
echo "=========================================="
echo -e "${CYAN}服务器信息${NC}"
echo "=========================================="
echo ""
echo -e "${BLUE}监听地址:${NC} 0.0.0.0:8000"
echo -e "${BLUE}协议:${NC} WebSocket + JSON-RPC 2.0"
echo ""
echo "=========================================="
echo ""

# 启动服务器
echo -e "${GREEN}启动服务器...${NC}"
echo ""

python3 main.py

# 退出处理
echo ""
echo -e "${YELLOW}服务器已停止${NC}"
echo ""
