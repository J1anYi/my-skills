---
name: quark-file-organization
description: |
  使用 playwright-cli 自动化整理夸克网盘文件。
  
  功能：
  - 搜索并分类文件
  - 批量移动文件到目标目录
  - 创建目录结构
  - 生成文件清单
  
  触发场景：
  - 用户需要整理夸克网盘中的文件
  - 用户想要将某类文件移动到特定目录
  - 用户需要查找并列出夸克中的特定类型文件
  - 用户提到"夸克"、"移动文件"、"整理文件"等关键词
---

# 夸克网盘文件整理

使用 playwright-cli 自动化整理夸克网盘中的文件。

## 前置条件

### 登录状态文件

使用 `save-music-to-quark-enhanced` skill 目录下的 `quark-auth.json`：

```
/mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced/quark-auth.json
```

### WSL 环境执行

在 WSL 中必须通过 PowerShell 执行 playwright-cli：

```bash
powershell.exe -Command "playwright-cli ..."
```

## 核心工作流

### 1. 打开浏览器并加载登录状态

```bash
# 进入 skill 目录
cd /mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced

# 打开浏览器
powershell.exe -Command "playwright-cli open"

# 加载登录状态（必须！）
powershell.exe -Command "playwright-cli state-load quark-auth.json"

# 导航到夸克网盘
powershell.exe -Command "playwright-cli goto 'https://pan.quark.cn/list#/list/all'"
```

### 2. 搜索文件

```bash
# 在搜索框输入关键词
powershell.exe -Command "playwright-cli fill e80 '电影'"

# 按回车搜索
powershell.exe -Command "playwright-cli press Enter"

# 等待结果并获取快照
powershell.exe -Command "playwright-cli snapshot"
```

### 3. 浏览目录结构

```bash
# 点击文件夹进入
powershell.exe -Command "playwright-cli click <文件夹ref>"

# 返回上一级
powershell.exe -Command "playwright-cli click <返回按钮ref>"

# 滚动加载更多
powershell.exe -Command "playwright-cli eval 'window.scrollBy(0, 800)'"
```

### 4. 选中文件

```bash
# 单选：点击文件的 checkbox
powershell.exe -Command "playwright-cli click <checkbox ref>"

# 全选：点击表头的 checkbox
powershell.exe -Command "playwright-cli click <全选checkbox ref>"
```

### 5. 移动文件

```bash
# 点击"移动到..."按钮
powershell.exe -Command "playwright-cli click <移动到按钮ref>"

# 在对话框中选择目标目录
powershell.exe -Command "playwright-cli click <目标文件夹ref>"

# 或创建新文件夹
powershell.exe -Command "playwright-cli click <新建文件夹按钮ref>"
powershell.exe -Command "playwright-cli fill <输入框ref> '电影'"
powershell.exe -Command "playwright-cli press Enter"

# 确认移动
powershell.exe -Command "playwright-cli click <确认按钮ref>"
```

### 6. 关闭浏览器

```bash
powershell.exe -Command "playwright-cli close"
```

## 常用场景

### 场景1: 整理电影文件

```
用户: 帮我把夸克里的电影文件全部移动到 文件/电影 里面
```

步骤：
1. 搜索"电影"关键词
2. 或浏览"视频"分类
3. 识别电影文件夹/文件（通常包含 mkv/mp4 大文件）
4. 全选并移动到 `全部文件/电影/`

### 场景2: 按类型整理文件

```
用户: 帮我把夸克里的所有 PDF 文档整理到 文档/PDF 目录
```

步骤：
1. 搜索".pdf"或浏览"文档"分类
2. 识别 PDF 文件
3. 创建目标目录
4. 批量移动

### 场景3: 清理下载目录

```
用户: 帮我整理"来自：分享"目录里的文件
```

步骤：
1. 进入"来自：分享"目录
2. 按类型分类文件
3. 移动到对应的整理目录

## 文件识别技巧

### 电影文件特征

- 文件夹名包含年份：`(2024)`、`[2024]`
- 文件夹名包含质量标识：`4K`、`1080p`、`蓝光`、`REMUX`
- 包含大体积视频文件：`.mkv`、`.mp4`（通常 >1GB）
- 包含配套文件：`.nfo`、`.ass`、`-poster.jpg`、`-fanart.jpg`

### 音乐文件特征

- 音频格式：`.mp3`、`.flac`、`.wav`、`.m4a`
- 文件名格式：`歌手 - 歌曲名.扩展名`
- 通常在"来自：分享"目录下

### 文档文件特征

- 文档格式：`.pdf`、`.docx`、`.xlsx`、`.pptx`
- 电子书：`.epub`、`.mobi`

## 目录结构建议

```
全部文件/
├── 电影/           # 电影文件
│   ├── 国产电影/
│   ├── 欧美电影/
│   └── 动画电影/
├── 歌曲/           # 音乐文件
│   ├── 华语/
│   ├── 欧美/
│   └── 纯音乐/
├── 动漫/           # 动漫剧集
├── 剧集/           # 电视剧
├── 文档/           # 文档资料
│   ├── PDF/
│   ├── 电子书/
│   └── 工作文档/
└── 软件/           # 软件安装包
```

## 元素定位参考

| 元素 | 定位方式 |
|------|----------|
| 搜索框 | `textbox "搜索全部文件"` |
| 文件 checkbox | 文件行中的 `checkbox` 元素 |
| 全选 checkbox | 表头的 `checkbox` 元素 |
| 移动按钮 | `button "移动到..."` |
| 新建文件夹 | `button "新建文件夹"` |
| 确认按钮 | `button "确认"` |
| 取消按钮 | `button "取消"` |

## 注意事项

### ⚠️ 必须加载登录状态

每次操作前必须执行 `state-load`，否则会提示需要登录。

### ⚠️ 点击 checkbox 而非文件名

点击文件名会触发预览，要点文件前的 checkbox 来选中。

### ⚠️ 搜索结果会包含所有匹配

搜索"电影"会返回文件名、文件夹名包含"电影"的所有内容，需要人工筛选。

### ⚠️ 移动操作不可撤销

移动前确认选中的文件和目标目录正确。

## 删除文件

### 删除单个或多个文件

```bash
# 1. 选中要删除的文件（点击 checkbox）
powershell.exe -Command "playwright-cli click <checkbox ref>"

# 2. 点击"删除"按钮
powershell.exe -Command "playwright-cli click <删除按钮ref>"

# 3. 确认删除
powershell.exe -Command "playwright-cli click <确认删除按钮ref>"
```

### 删除重复文件

上传时可能产生重复文件（文件名带 `(1)`、`(2)` 后缀），可以批量删除：

```bash
# 1. 获取文件列表快照
powershell.exe -Command "playwright-cli snapshot" 2>&1 | grep -E "checkbox.*EP[0-9]+"

# 2. 找到重复文件的 checkbox ref（文件名包含 (1) 或 (2)）
# 3. 逐个选中
for ref in e634 e654 e669; do
  powershell.exe -Command "playwright-cli click $ref"
  sleep 0.5
done

# 4. 点击删除按钮
powershell.exe -Command "playwright-cli click <删除按钮ref>"

# 5. 确认删除
powershell.exe -Command "playwright-cli click <确认删除按钮ref>"
```

### 元素定位

| 元素 | 定位方式 |
|------|----------|
| 删除按钮 | `button "删除"` |
| 确认删除 | `button "确认删除"` |

### ⚠️ 删除操作移到回收站

删除的文件会移到回收站，可在回收站恢复。回收站会定期清理。

### 清空整个文件夹

当需要清空某个文件夹中的所有文件时：

```bash
# 1. 导航到目标文件夹
powershell.exe -Command "playwright-cli click <文件夹ref>"

# 2. 等待加载
sleep 2

# 3. 获取表头全选 checkbox
powershell.exe -Command "playwright-cli snapshot" 2>&1 | grep "checkbox" | head -1

# 4. 点击全选 checkbox（表头第一个）
powershell.exe -Command "playwright-cli click <全选checkbox ref>"

# 5. 点击删除按钮
powershell.exe -Command "playwright-cli click <删除按钮ref>"

# 6. 确认删除
powershell.exe -Command "playwright-cli click <确认删除按钮ref>"

# 7. 验证文件夹已清空（应显示"拖拽/粘贴到灰框内处上传文件"）
powershell.exe -Command "playwright-cli snapshot" 2>&1 | grep -E "拖拽|空"
```

**示例：清空番剧文件夹**

```bash
# 导航到番剧/凡人修仙传
cd /mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced
powershell.exe -Command "playwright-cli goto 'https://pan.quark.cn/list#/list/all'"

# 获取快照，找到番剧文件夹
powershell.exe -Command "playwright-cli snapshot" 2>&1 | grep "番剧"

# 进入番剧 → 凡人修仙传
powershell.exe -Command "playwright-cli click <番剧ref>"
powershell.exe -Command "playwright-cli click <凡人修仙传ref>"

# 全选并删除
powershell.exe -Command "playwright-cli click <全选checkbox>"  # 通常是 e610 之类的 ref
powershell.exe -Command "playwright-cli click <删除按钮>"       # 找 button "删除"
powershell.exe -Command "playwright-cli click <确认删除>"       # 找 button "确认删除"
```

## 完整示例：整理电影文件

```bash
# 1. 打开浏览器并加载登录状态
cd /mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced
powershell.exe -Command "playwright-cli open"
powershell.exe -Command "playwright-cli state-load quark-auth.json"
powershell.exe -Command "playwright-cli goto 'https://pan.quark.cn/list#/list/all'"

# 2. 搜索电影相关文件
powershell.exe -Command "playwright-cli fill e80 '功夫'"
powershell.exe -Command "playwright-cli press Enter"
powershell.exe -Command "playwright-cli snapshot"

# 3. 全选搜索结果
powershell.exe -Command "playwright-cli click <全选checkbox>"

# 4. 移动到电影目录
powershell.exe -Command "playwright-cli click <移动到按钮>"
powershell.exe -Command "playwright-cli click <电影文件夹>"
powershell.exe -Command "playwright-cli click <确认按钮>"

# 5. 关闭浏览器
powershell.exe -Command "playwright-cli close"
```

## 上传文件到夸克网盘

### 基本上传流程

```bash
# 1. 进入目标目录
powershell.exe -Command "playwright-cli click <目标文件夹ref>"

# 2. 点击"上传文件"按钮
powershell.exe -Command "playwright-cli click <上传文件按钮ref>"

# 3. 上传文件（文件选择器会自动打开）
powershell.exe -Command "playwright-cli upload 'path/to/file.mp4'"
```

### ⚠️ 文件路径限制

playwright-cli 的 `upload` 命令有严格的路径限制（"allowed roots"）：
- 只允许上传当前工作目录或 `.playwright-cli/` 子目录中的文件
- WSL 路径（如 `\\wsl.localhost\...`）不在允许范围内

**解决方案**：先将文件复制到 skill 目录

```bash
# 复制文件到 skill 目录
mkdir -p /mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced/upload/
cp ~/videos/*.mp4 /mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced/upload/

# 然后使用相对路径上传
cd /mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced/
powershell.exe -Command "playwright-cli upload 'upload/video.mp4'"
```

### 上传大文件

夸克网盘网页版支持大文件上传，但上传速度受网络影响：
- 400-500MB 文件约需 1-2 分钟
- 可同时上传多个文件（依次选择）
- 上传进度显示在文件列表区域

### 上传后移动文件

上传的文件会保存在当前目录，如需移动到子目录：

```bash
# 选中已上传的文件（点击 checkbox）
powershell.exe -Command "playwright-cli click <文件checkbox ref>"

# 点击"移动到..."
powershell.exe -Command "playwright-cli click <移动到按钮ref>"

# 选择目标目录
powershell.exe -Command "playwright-cli click <目标文件夹ref>"

# 确认移动
powershell.exe -Command "playwright-cli click <确认按钮ref>"
```

## 相关技能

- `save-music-to-quark-enhanced`: 保存歌曲到夸克网盘（提供 quark-auth.json）
- `playwright-cli`: Playwright 浏览器自动化
- `playwright-login-handler`: 登录状态检测和处理
- `bilibili-download`: 下载B站视频（大会员视频需要cookie认证）
