---
name: Git PR Automation
description: |
  自动创建、合并 GitHub Pull Request。使用场景：
  (1) 当用户要求创建 PR、提交 PR、push 并创建 PR 时
  (2) 当用户要求合并 PR 到主分支时
  (3) 当用户要求直接 merge 到 main 时
  提供完整的 PR 创建和合并工作流。
---

# Git PR Automation

## Quick Start

### 1. 检查 gh CLI 是否可用

```bash
where gh 2>/dev/null || which gh 2>/dev/null || echo "gh not found"
```

如果 gh 不存在，先安装：

```bash
winget install -e --id GitHub.cli --accept-source-agreements --accept-package-agreements
```

### 2. 验证认证状态

```bash
gh auth status
```

如果未登录：

```bash
gh auth login --web
```

会显示一个设备验证码，在浏览器中打开 https://github.com/login/device 并输入代码完成登录。

### 3. 创建 PR 并合并

如果分支已推送到远程，直接执行：

```bash
# 创建 PR
gh pr create --title "PR标题" --body "PR描述" --base main --head <branch-name>

# 合并 PR (需要仓库管理员权限)
gh pr merge <PR-number> --admin --merge --delete-branch
```

## 常用命令参考

### 创建 PR

```bash
# 基本创建
gh pr create --title "title" --body "body"

# 指定 base 和 head 分支
gh pr create --base main --head feature-branch

# 使用 stdin 传入 body
echo "body content" | gh pr create --title "title" --body -
```

### 合并 PR

```bash
# 使用 admin 权限直接合并（不需要 CI 通过）
gh pr merge <number> --admin --merge

# 同时删除分支
gh pr merge <number> --admin --merge --delete-branch

# 启用自动合并（等待 CI 通过后自动合并）
gh pr merge <number> --admin --auto
```

### 查看 PR 状态

```bash
# 查看 PR 详情
gh pr view <number>

# 查看当前分支的 PR
gh pr view --web
```

## 故障排除

| 问题 | 解决方案 |
|------|----------|
| `gh: command not found` | 使用完整路径 `/c/Program Files/GitHub CLI/gh` 或添加到 PATH |
| `You are not logged in` | 运行 `gh auth login --web` |
| `--auto` 和 `--admin` 冲突 | 不能同时使用，只能选一个 |
| `--merge`, `--rebase`, or `--squash` required | 非交互模式需要明确指定合并方式 |

## 自动化脚本

如果需要一键执行（假设分支已推送）：

```bash
# 创建并合并 PR
BRANCH=$(git branch --show-current)
TITLE="PR标题"
BODY="PR描述"

# 创建 PR 并获取编号
PR_NUM=$(gh pr create --title "$TITLE" --body "$BODY" --base main --head $BRANCH --json number -q '.number')

# 合并 PR
gh pr merge $PR_NUM --admin --merge --delete-branch
```

注意：合并需要仓库的 admin 权限。