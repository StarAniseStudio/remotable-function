#!/bin/bash
# Remotable Function Demo - 清理脚本

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🧹 清理环境...${NC}"
echo ""

# 清理测试文件
if [ -d "test_files" ]; then
    echo "清理测试文件..."
    rm -rf test_files
    echo -e "${GREEN}✓ 已清理 test_files 目录${NC}"
fi

# 清理 Python 缓存
echo "清理 Python 缓存..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo -e "${GREEN}✓ 已清理 Python 缓存${NC}"

# 检查并关闭运行中的进程
if pgrep -f "python.*demo.*main.py" > /dev/null; then
    echo ""
    echo "发现运行中的进程："
    pgrep -f "python.*demo.*main.py" -l
    echo ""
    read -p "是否要关闭这些进程? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -f "python.*demo.*main.py"
        echo -e "${GREEN}✓ 已关闭进程${NC}"
    fi
fi

echo ""
echo -e "${GREEN}✅ 清理完成！${NC}"
echo ""
