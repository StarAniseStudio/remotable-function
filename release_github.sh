#!/bin/bash

# GitHub 发布脚本
# 创建 Git tag 并推送到 GitHub

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

VERSION="v1.0.0"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}GitHub 发布脚本${NC}"
echo -e "${GREEN}版本: $VERSION${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# 1. 检查 Git 状态
echo -e "${YELLOW}[1/4] 检查 Git 状态...${NC}"
if [[ -n $(git status -s) ]]; then
    echo -e "${RED}错误: 有未提交的更改！${NC}"
    echo ""
    git status -s
    echo ""
    echo "请先提交所有更改后再发布。"
    exit 1
fi
echo -e "${GREEN}✓ Git 状态干净${NC}"
echo ""

# 2. 推送到 GitHub
echo -e "${YELLOW}[2/4] 推送到 GitHub...${NC}"
echo "正在推送分支..."
git push origin main
echo -e "${GREEN}✓ 分支推送成功${NC}"
echo ""

# 3. 创建并推送标签
echo -e "${YELLOW}[3/4] 创建发布标签...${NC}"

# 检查标签是否已存在
if git rev-parse "$VERSION" >/dev/null 2>&1; then
    echo -e "${YELLOW}标签 $VERSION 已存在${NC}"
    read -p "是否删除并重新创建? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "删除本地标签..."
        git tag -d "$VERSION"
        echo "删除远程标签..."
        git push origin ":refs/tags/$VERSION" || true
    else
        echo -e "${RED}已取消${NC}"
        exit 1
    fi
fi

echo "创建标签 $VERSION..."
git tag -a "$VERSION" -m "Release $VERSION"

echo "推送标签到 GitHub..."
git push origin "$VERSION"

echo -e "${GREEN}✓ 标签创建成功${NC}"
echo ""

# 4. 提示下一步
echo -e "${GREEN}[4/4] 完成！${NC}"
echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}标签已推送到 GitHub！${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "${YELLOW}下一步操作:${NC}"
echo ""
echo "1. 访问 GitHub Releases 页面:"
echo "   https://github.com/StarAniseStudio/remotable-function/releases/new"
echo ""
echo "2. 选择标签: $VERSION"
echo ""
echo "3. 发布标题: Remotable Function $VERSION"
echo ""
echo "4. 发布说明: 复制 CHANGELOG.md 的内容"
echo ""
echo "5. 上传构建产物:"
echo "   - dist/remotable-function-1.0.0-py3-none-any.whl"
echo "   - dist/remotable-function-1.0.0.tar.gz"
echo ""
echo "6. 点击 'Publish release'"
echo ""
