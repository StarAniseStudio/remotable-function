# 发布指南

本文档说明如何发布 Remotable Function 到 PyPI。

## 发布流程概述

我们使用 GitHub Actions 自动化发布流程，这是业界标准做法。

### 发布方式

有两种发布方式：

1. **通过 GitHub Release（推荐）**：创建 GitHub Release 时自动发布到 PyPI
2. **手动触发**：通过 GitHub Actions 手动触发发布

## 前置准备

### 1. 配置 PyPI Trusted Publishing（推荐）

这是最安全的方式，无需 API token：

1. 访问 [PyPI 账户设置](https://pypi.org/manage/account/)
2. 进入 "API tokens" 或 "Trusted publishers"
3. 添加新的 trusted publisher：
   - **PyPI project name**: `remotable-function`
   - **Owner**: `StarAniseStudio`
   - **Workflow filename**: `.github/workflows/publish.yml`
   - **Environment name**: （留空）

### 2. 或使用 API Token（备选方案）

如果不想使用 Trusted Publishing：

1. 在 PyPI 创建 API token：https://pypi.org/manage/account/token/
2. 在 GitHub 仓库设置中添加 Secret：
   - Settings → Secrets and variables → Actions
   - 添加 `PYPI_API_TOKEN`

## 发布步骤

### 方式一：通过 GitHub Release 发布（推荐）

1. **更新版本号**

   编辑 `pyproject.toml`，更新版本号：
   ```toml
   version = "1.0.1"  # 例如从 1.0.0 升级到 1.0.1
   ```

2. **更新 CHANGELOG.md**

   记录本次发布的变更内容。

3. **提交并推送代码**

   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "Bump version to 1.0.1"
   git push origin main
   ```

4. **创建 Git Tag**

   ```bash
   git tag -a v1.0.1 -m "Release v1.0.1"
   git push origin v1.0.1
   ```

5. **创建 GitHub Release**

   - 访问：https://github.com/StarAniseStudio/remotable-function/releases/new
   - 选择刚创建的 tag（如 `v1.0.1`）
   - 填写 Release 标题：`Remotable Function v1.0.1`
   - 填写 Release 说明（可从 CHANGELOG.md 复制）
   - 点击 "Publish release"

6. **自动发布**

   GitHub Actions 会自动：
   - 构建 Python 包
   - 检查包的有效性
   - 发布到 PyPI
   - 你可以在 Actions 页面查看进度

### 方式二：手动触发发布

1. 在 GitHub 仓库页面，进入 "Actions" 标签
2. 选择 "Publish to PyPI" 工作流
3. 点击 "Run workflow"
4. 输入版本号（如 `1.0.1`）
5. 点击 "Run workflow"

## 测试发布（TestPyPI）

在正式发布前，建议先发布到 TestPyPI 进行测试：

### 使用本地脚本

```bash
./publish.sh testpypi
```

### 使用 GitHub Actions

可以创建一个单独的 workflow 用于 TestPyPI，或修改现有 workflow 添加 testpypi 选项。

## 验证发布

发布成功后，验证安装：

```bash
pip install remotable-function
```

或指定版本：

```bash
pip install remotable-function==1.0.1
```

## 版本号规范

遵循 [语义化版本](https://semver.org/lang/zh-CN/)：

- **主版本号**：不兼容的 API 修改
- **次版本号**：向下兼容的功能性新增
- **修订号**：向下兼容的问题修正

示例：
- `1.0.0` → `1.0.1`：修复 bug
- `1.0.1` → `1.1.0`：新增功能
- `1.1.0` → `2.0.0`：破坏性变更

## 常见问题

### Q: 发布失败怎么办？

A: 检查：
1. 版本号是否已存在（PyPI 不允许重复版本）
2. 包名是否正确
3. PyPI 认证是否配置正确
4. 查看 GitHub Actions 日志获取详细错误信息

### Q: 如何回滚版本？

A: PyPI 不允许删除已发布的版本，但可以：
1. 发布一个新的修复版本
2. 在 README 中说明问题版本

### Q: 可以发布预发布版本吗？

A: 可以，使用版本号后缀，如 `1.0.1a1`、`1.0.1b1`、`1.0.1rc1`。

## 相关资源

- [PyPI 文档](https://packaging.python.org/en/latest/)
- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [语义化版本](https://semver.org/)

