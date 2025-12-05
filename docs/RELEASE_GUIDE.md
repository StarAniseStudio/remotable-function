# Remotable Function 发布指南

本文档详细说明如何发布 Remotable Function 的新版本到 PyPI。

## 目录

- [发布前准备](#发布前准备)
- [发布步骤](#发布步骤)
- [发布后验证](#发布后验证)
- [回滚指南](#回滚指南)
- [常见问题](#常见问题)

---

## 发布前准备

### 1. 检查代码质量

确保所有测试通过，代码符合质量标准：

```bash
# 1. 运行所有测试
python -m pytest

# 2. 检查代码格式
black --check remotable_function/

# 3. 运行类型检查（可选）
mypy remotable_function/

# 4. 检查代码风格（可选）
flake8 remotable_function/
```

### 2. 更新版本号

在 `pyproject.toml` 中更新版本号：

```toml
[project]
name = "remotable-function"
version = "2.0.0"  # 修改这里
```

**版本号规范（遵循语义化版本）：**

- **主版本号 (Major)**：不兼容的 API 变更
- **次版本号 (Minor)**：向后兼容的功能新增
- **修订号 (Patch)**：向后兼容的问题修复

**示例：**
- `1.0.0` → `2.0.0`：重大 API 变更（如 v2.0 重构）
- `2.0.0` → `2.1.0`：新增功能，向后兼容
- `2.1.0` → `2.1.1`：Bug 修复

### 3. 更新 CHANGELOG

在 `CHANGELOG.md` 中记录本次版本的所有变更：

```markdown
## [2.0.0] - 2025-11-22

### 🎉 Major Release - Unified and Simplified

### Added
- ✨ 新功能 A
- 🔧 新功能 B

### Changed
- 📉 改进 A
- 🎯 改进 B

### Fixed
- 🐛 修复 bug A
- 🐛 修复 bug B

### Removed
- 🗑️ 删除过时功能 A
```

**Emoji 约定：**
- ✨ `:sparkles:` - 新功能
- 🐛 `:bug:` - Bug 修复
- 📝 `:memo:` - 文档更新
- 🔧 `:wrench:` - 配置变更
- ⚡ `:zap:` - 性能改进
- 🎨 `:art:` - 代码结构/格式改进
- 🔒 `:lock:` - 安全修复
- 🗑️ `:wastebasket:` - 删除代码/功能

### 4. 更新文档

确保以下文档是最新的：

- `README.md` - 主要文档
- `README_CN.md` - 中文文档
- `docs/` - 各种专题文档
- 示例代码 (`samples/`)

### 5. 本地构建测试

在发布前，先在本地测试构建：

```bash
# 1. 清理旧的构建文件
rm -rf dist/ build/ *.egg-info

# 2. 安装构建工具
pip install --upgrade build twine

# 3. 构建包
python -m build

# 4. 检查构建产物
twine check dist/*

# 5. 查看构建的文件
ls -lh dist/
```

你应该看到两个文件：
```
remotable_function-2.0.0-py3-none-any.whl
remotable_function-2.0.0.tar.gz
```

### 6. 本地安装测试

在虚拟环境中测试安装：

```bash
# 创建测试虚拟环境
python -m venv test_env
source test_env/bin/activate  # Windows: test_env\Scripts\activate

# 安装构建的包
pip install dist/remotable_function-2.0.0-py3-none-any.whl

# 测试导入
python -c "import remotable_function; print(remotable_function.__version__)"

# 运行简单示例
cd samples/simple
python server.py  # 在一个终端
python client.py  # 在另一个终端

# 清理
deactivate
rm -rf test_env
```

---

## 发布步骤

### 方法一：使用 Git Tag（推荐，自动发布）

这是最简单的方法，推送 tag 后会自动触发 GitHub Actions 构建和发布。

#### 步骤：

```bash
# 1. 提交所有变更
git add .
git commit -m "Release v2.0.0"

# 2. 创建 Git tag
git tag v2.0.0

# 3. 推送代码和 tag 到 GitHub
git push origin main
git push origin v2.0.0
```

#### 自动化流程：

1. **推送 tag** → 触发 `.github/workflows/build.yml`
2. **构建包** → 运行 `python -m build`
3. **触发发布** → 调用 `.github/workflows/publish.yml`
4. **上传到 PyPI** → 使用 `twine upload`

#### 监控进度：

访问 GitHub Actions 页面查看构建状态：
```
https://github.com/StarAniseStudio/remotable-function/actions
```

### 方法二：手动发布到 PyPI

如果需要手动控制发布过程：

#### 步骤：

```bash
# 1. 配置 PyPI 凭证（首次使用）
# 创建 ~/.pypirc 文件：
cat > ~/.pypirc << 'EOF'
[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmcC...你的token...
EOF

chmod 600 ~/.pypirc

# 2. 先发布到 TestPyPI（可选但推荐）
twine upload --repository testpypi dist/*

# 验证 TestPyPI 安装
pip install --index-url https://test.pypi.org/simple/ remotable-function

# 3. 发布到正式 PyPI
twine upload dist/*

# 4. 创建 GitHub Release
git tag v2.0.0
git push origin v2.0.0
```

#### 获取 PyPI Token：

1. 访问 https://pypi.org/manage/account/token/
2. 点击 "Add API token"
3. 选择 Scope：
   - **Entire account**（首次发布）
   - **Project: remotable-function**（后续发布）
4. 复制 token 并保存到 `~/.pypirc`

### 方法三：使用 GitHub Release

通过 GitHub UI 创建 Release：

1. 访问 https://github.com/StarAniseStudio/remotable-function/releases
2. 点击 "Draft a new release"
3. 填写信息：
   - **Tag**: `v2.0.0`（创建新 tag）
   - **Target**: `main`
   - **Title**: `v2.0.0 - Unified and Simplified`
   - **Description**: 从 CHANGELOG.md 复制内容
4. 勾选 "Set as the latest release"
5. 点击 "Publish release"

这会自动触发 GitHub Actions 发布流程。

---

## 发布后验证

### 1. 验证 PyPI 页面

访问包页面确认发布成功：

```
https://pypi.org/project/remotable-function/
```

检查：
- ✅ 版本号正确
- ✅ 描述完整
- ✅ 依赖正确
- ✅ 支持的 Python 版本正确
- ✅ 链接可用（Homepage, Documentation, Repository, Issues）

### 2. 测试安装

在干净环境中测试安装：

```bash
# 创建新虚拟环境
python -m venv verify_env
source verify_env/bin/activate

# 安装包
pip install remotable-function

# 验证版本
python -c "import remotable_function; print(remotable_function.__version__)"
# 应该输出：2.0.0

# 验证导入
python << 'EOF'
from remotable_function import Gateway, Client, Tool
from remotable_function.core.types import ToolContext
print("✅ All imports successful!")
EOF

# 运行快速测试
python << 'EOF'
import asyncio
from remotable_function import start_server

async def test():
    server = await start_server(port=9999)
    print("✅ Server started successfully!")
    server.stop()

asyncio.run(test())
EOF

# 清理
deactivate
rm -rf verify_env
```

### 3. 测试升级

如果是升级版本，测试从旧版本升级：

```bash
# 安装旧版本
pip install remotable-function==1.0.0

# 升级到新版本
pip install --upgrade remotable-function

# 验证
python -c "import remotable_function; print(remotable_function.__version__)"
```

### 4. 检查文档

确认以下位置的文档都已更新：

- ✅ PyPI 包页面（README.md）
- ✅ GitHub README
- ✅ GitHub Release 页面
- ✅ CHANGELOG.md

### 5. 通知用户

发布完成后，可以通过以下渠道通知用户：

1. **GitHub Discussions** - 发布公告
2. **Twitter/社交媒体** - 分享更新
3. **项目文档** - 更新"最新版本"链接
4. **Issue Tracker** - 关闭相关 issues 并标注版本

---

## 回滚指南

如果发现严重问题需要回滚：

### 1. 撤回 PyPI 包（不推荐）

**注意**：PyPI 不允许删除已发布的版本，但可以 yank（标记为不可用）：

```bash
# 标记版本为 yanked（不推荐新用户安装）
twine upload --skip-existing --repository pypi dist/* --yank "2.0.0"
```

**更好的做法**：发布修复版本（如 2.0.1）

### 2. 发布修复版本

```bash
# 1. 修复问题
git checkout -b hotfix/2.0.1

# 2. 修改代码并测试
# ...修复 bug...

# 3. 更新版本号
# pyproject.toml: version = "2.0.1"

# 4. 更新 CHANGELOG
# 添加 [2.0.1] 段落

# 5. 提交并发布
git commit -am "Fix critical bug in 2.0.0"
git tag v2.0.1
git push origin hotfix/2.0.1
git push origin v2.0.1

# 6. 合并到 main
git checkout main
git merge hotfix/2.0.1
git push origin main
```

### 3. 删除 Git Tag（本地）

如果还没有推送到远程：

```bash
# 删除本地 tag
git tag -d v2.0.0

# 删除远程 tag（如果已推送）
git push origin :refs/tags/v2.0.0
```

---

## 常见问题

### Q1: 构建失败，提示 "Could not build wheels"

**原因**：可能缺少构建依赖

**解决**：
```bash
pip install --upgrade pip setuptools wheel build
python -m build
```

### Q2: 上传到 PyPI 失败，提示认证错误

**原因**：PyPI token 配置不正确

**解决**：
```bash
# 检查 ~/.pypirc 文件
cat ~/.pypirc

# 或者直接在命令行指定 token
twine upload dist/* --username __token__ --password pypi-AgEI...
```

### Q3: 版本号已存在

**原因**：PyPI 不允许覆盖已发布的版本

**解决**：
```bash
# 更新版本号到新的小版本
# pyproject.toml: version = "2.0.1"
python -m build
twine upload dist/*
```

### Q4: GitHub Actions 构建失败

**查看日志**：
```
https://github.com/StarAniseStudio/remotable-function/actions
```

**常见原因**：
- 测试失败
- 依赖冲突
- PyPI token 过期

**解决**：
1. 本地重现问题
2. 修复并提交
3. 重新推送 tag

### Q5: 如何发布 beta/alpha 版本？

**使用预发布版本号**：

```toml
# pyproject.toml
version = "2.1.0a1"  # alpha 1
version = "2.1.0b1"  # beta 1
version = "2.1.0rc1" # release candidate 1
```

**安装预发布版本**：
```bash
pip install --pre remotable-function
```

### Q6: 如何同时维护多个版本（如 1.x 和 2.x）？

**使用分支策略**：

```bash
# main - 2.x 开发
# v1.x - 1.x 维护

# 在 v1.x 分支上发布补丁
git checkout v1.x
# 修改 version = "1.3.1"
git commit -am "Fix bug in v1.x"
git tag v1.3.1
git push origin v1.x
git push origin v1.3.1
```

---

## 发布检查清单

使用这个清单确保发布流程完整：

### 发布前

- [ ] 所有测试通过
- [ ] 代码格式化完成
- [ ] 版本号已更新（`pyproject.toml`）
- [ ] CHANGELOG 已更新
- [ ] 文档已更新（README.md, README_CN.md）
- [ ] 本地构建测试成功
- [ ] 本地安装测试成功
- [ ] 示例代码可运行

### 发布时

- [ ] Git 提交已完成
- [ ] Git tag 已创建（`v2.0.0`）
- [ ] 代码已推送到 GitHub
- [ ] Tag 已推送到 GitHub
- [ ] GitHub Actions 构建成功
- [ ] PyPI 发布成功

### 发布后

- [ ] PyPI 页面检查通过
- [ ] 安装测试成功
- [ ] 版本号验证正确
- [ ] 导入测试成功
- [ ] 文档链接有效
- [ ] GitHub Release 已创建
- [ ] CHANGELOG 已包含发布链接

---

## 相关链接

- **PyPI 项目页面**: https://pypi.org/project/remotable-function/
- **GitHub 仓库**: https://github.com/StarAniseStudio/remotable-function
- **GitHub Releases**: https://github.com/StarAniseStudio/remotable-function/releases
- **GitHub Actions**: https://github.com/StarAniseStudio/remotable-function/actions
- **PyPI 发布指南**: https://packaging.python.org/tutorials/packaging-projects/
- **语义化版本**: https://semver.org/

---

## 示例：发布 v2.0.0 的完整流程

```bash
# 1. 确保在 main 分支
git checkout main
git pull origin main

# 2. 运行测试
python -m pytest

# 3. 更新版本号
# 编辑 pyproject.toml: version = "2.0.0"

# 4. 更新 CHANGELOG.md
# 添加 v2.0.0 的变更记录

# 5. 提交变更
git add .
git commit -m "Release v2.0.0

- Unified and simplified API
- 62.5% code reduction
- Event-driven architecture
- Comprehensive documentation
"

# 6. 创建和推送 tag
git tag v2.0.0
git push origin main
git push origin v2.0.0

# 7. 等待 GitHub Actions 完成（约 3-5 分钟）
# 访问 https://github.com/StarAniseStudio/remotable-function/actions

# 8. 验证发布
pip install remotable-function
python -c "import remotable_function; print(remotable_function.__version__)"

# 9. 创建 GitHub Release
# 访问 https://github.com/StarAniseStudio/remotable-function/releases
# 点击 "Draft a new release"，使用 v2.0.0 tag

# 完成！🎉
```

---

**最后更新**: 2025-11-22
**适用版本**: v2.0.0+
