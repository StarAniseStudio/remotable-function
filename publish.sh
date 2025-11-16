#!/bin/bash

# Remotable Function 发布脚本
# 使用方法: ./publish.sh [testpypi|pypi]

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Remotable Function 发布脚本${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# 检查参数
if [ $# -eq 0 ]; then
    echo -e "${YELLOW}使用方法:${NC}"
    echo "  ./publish.sh testpypi  - 发布到 TestPyPI (测试)"
    echo "  ./publish.sh pypi      - 发布到 PyPI (正式)"
    echo ""
    exit 1
fi

TARGET=$1

# 验证目标
if [ "$TARGET" != "testpypi" ] && [ "$TARGET" != "pypi" ]; then
    echo -e "${RED}错误: 无效的目标 '$TARGET'${NC}"
    echo "请使用 'testpypi' 或 'pypi'"
    exit 1
fi

# 1. 清理旧产物
echo -e "${YELLOW}[1/6] 清理旧的构建产物...${NC}"
rm -rf dist/ build/ *.egg-info remotable.egg-info
echo -e "${GREEN}✓ 清理完成${NC}"
echo ""

# 2. 构建包
echo -e "${YELLOW}[2/6] 构建 Python 包...${NC}"
python3 -m build
echo -e "${GREEN}✓ 构建完成${NC}"
echo ""

# 3. 检查包
echo -e "${YELLOW}[3/6] 检查包的有效性...${NC}"
python3 -m twine check dist/*
echo -e "${GREEN}✓ 检查通过${NC}"
echo ""

# 4. 显示包信息
echo -e "${YELLOW}[4/6] 包信息:${NC}"
ls -lh dist/
echo ""

# 5. 上传确认
echo -e "${YELLOW}[5/6] 准备上传到 $TARGET...${NC}"
if [ "$TARGET" = "testpypi" ]; then
    echo -e "${YELLOW}目标: TestPyPI (https://test.pypi.org)${NC}"
    echo ""
    read -p "确认上传到 TestPyPI? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}已取消${NC}"
        exit 1
    fi

    echo ""
    echo -e "${YELLOW}正在上传...${NC}"
    python3 -m twine upload --repository testpypi dist/*

    echo ""
    echo -e "${GREEN}✓ 上传成功！${NC}"
    echo ""
    echo -e "${GREEN}安装测试命令:${NC}"
    echo "  pip install --index-url https://test.pypi.org/simple/ --no-deps remotable-function"

else
    echo -e "${RED}目标: PyPI (https://pypi.org) - 正式发布！${NC}"
    echo ""
    echo -e "${RED}警告: 这将正式发布到 PyPI，版本号不可重复使用！${NC}"
    echo ""
    read -p "确认上传到 PyPI? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}已取消${NC}"
        exit 1
    fi

    echo ""
    echo -e "${YELLOW}正在上传...${NC}"
    python3 -m twine upload dist/*

    echo ""
    echo -e "${GREEN}✓ 上传成功！${NC}"
    echo ""
    echo -e "${GREEN}安装命令:${NC}"
    echo "  pip install remotable-function"
fi

echo ""
echo -e "${GREEN}[6/6] 完成！${NC}"
echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}发布完成！${NC}"
echo -e "${GREEN}================================${NC}"
