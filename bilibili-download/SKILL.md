---
name: bilibili-download
description: |
  下载B站视频（包括大会员专属内容）。
  
  特性：
  - 支持大会员高清视频下载
  - 自动从Playwright登录状态提取cookie
  - 支持番剧、视频、课程等多种内容
  - 合并DASH视频和音频流
  
  触发场景：
  - 用户想要下载B站视频
  - 用户提到"凡人修仙传"、"B站"、"番剧下载"
  - 用户需要保存大会员专属内容
  - 用户提供了B站视频或番剧链接
---

# B站视频下载

使用 yt-dlp 下载B站视频，支持大会员高清内容。

## 前置条件

### 安装 yt-dlp

```bash
pip install yt-dlp -U
```

### 安装 ffmpeg（用于合并视频音频）

Windows 上推荐使用 ffmpeg：
```powershell
# 检查是否有 ffmpeg
ffmpeg -version

# 如果没有，可从 https://www.gyan.dev/ffmpeg/builds/ 下载
```

## 核心工作流

### 1. 获取B站登录Cookie

**方法一：从Playwright登录状态提取（推荐）**

如果已有 Playwright 登录状态文件（如 `bilibili-auth.json`）：

```python
import json

# 读取 auth 文件
with open('bilibili-auth.json', 'r') as f:
    data = json.load(f)

cookies = data.get('cookies', [])

# 生成 netscape 格式的 cookie 文件
output = ['# Netscape HTTP Cookie File', '# https://www.bilibili.com', '']
for cookie in cookies:
    domain = cookie.get('domain', '').lstrip('.')
    path = cookie.get('path', '/')
    secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
    name = cookie.get('name', '')
    value = cookie.get('value', '')
    expires = int(cookie.get('expires', 0))
    if expires < 0:
        expires = 2147483647
    output.append(f'.{domain}\tTRUE\t{path}\t{secure}\t{expires}\t{name}\t{value}')

with open('bilibili-cookies.txt', 'w') as f:
    f.write('\n'.join(output))

print(f'Cookie文件已保存，共 {len(cookies)} 个cookie')
```

**关键：HttpOnly Cookie**

`document.cookie` 不包含 HttpOnly 的 cookie（如 SESSDATA），必须从 Playwright 的 `state-save` 输出文件中提取。

### 2. 搜索视频/番剧

```bash
# 使用 yt-dlp 搜索
yt-dlp --cookies bilibili-cookies.txt "ytsearch:凡人修仙传 最新"

# 或直接使用URL
# 番剧: https://www.bilibili.com/bangumi/play/ep1231584
# 视频: https://www.bilibili.com/video/BV1xx411c7mD
```

### 3. 下载视频

```bash
# 基本下载
yt-dlp --cookies bilibili-cookies.txt \
  -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
  --merge-output-format mp4 \
  -o "%(series)s/%(episode_number)s-%(episode)s.%(ext)s" \
  "https://www.bilibili.com/bangumi/play/ep1231584"
```

### 4. 下载多集

```bash
# 下载最新2集
yt-dlp --cookies bilibili-cookies.txt \
  -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
  --merge-output-format mp4 \
  -o "%(series)s/%(episode_number)s-%(episode)s.%(ext)s" \
  "https://www.bilibili.com/bangumi/play/ep1231584" \
  "https://www.bilibili.com/bangumi/play/ep1231583"
```

## 前置检查：Cookie是否有效

**下载前先检查Cookie有效期**，避免下载预览版浪费时间：

```python
import json
import time

auth_path = "bilibili-auth.json"  # 或 bilibili-auth-new.json
with open(auth_path, 'r') as f:
    data = json.load(f)

cookies = data.get('cookies', [])
sessdata = None

for c in cookies:
    name = c.get('name', '')
    if name == 'SESSDATA':
        sessdata = c
        expires = c.get('expires', 0)
        expires_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expires)) if expires > 0 else '会话'
        is_expired = expires > 0 and expires < time.time()
        print(f"SESSDATA: 找到 ✓")
        print(f"  过期时间: {expires_str}")
        print(f"  是否过期: {'是 ⚠️' if is_expired else '否 ✓'}")
        break

if not sessdata:
    print("❌ 未找到 SESSDATA，登录可能失败")
```

**完整流程：检测过期 → 提示登录 → 保存新状态 → 生成cookie文件**

```python
from hermes_tools import terminal
import json
import time
import os

# 1. 检查cookie是否过期
auth_path = "/mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced/bilibili-auth.json"
with open(auth_path, 'r') as f:
    data = json.load(f)

cookies = data.get('cookies', [])
for c in cookies:
    if c.get('name') == 'SESSDATA':
        expires = c.get('expires', 0)
        if expires > 0 and expires < time.time():
            print("⚠️ Cookie已过期，需要重新登录！")
            # 2. 打开浏览器让用户登录
            terminal('powershell.exe -Command "playwright-cli open --headed \'https://www.bilibili.com\'"')
            print("请在浏览器中扫码登录，登录完成后告诉我")
            # 等待用户确认...
        break

# 3. 登录成功后保存新状态
# terminal('powershell.exe -Command "playwright-cli state-save bilibili-auth-new.json"')

# 4. 生成netscape格式cookie文件
output = ['# Netscape HTTP Cookie File', '# https://curl.haxx.se/rfc/cookie_spec.html', '# This is a generated file!  Do not edit.', '']
for cookie in cookies:
    domain = cookie.get('domain', '').lstrip('.')
    if not domain:
        continue
    expires = int(cookie.get('expires', 0))
    if expires < 0 or expires > 2147483647:
        expires = 2147483647
    output.append(f'.{domain}\tTRUE\t{cookie.get("path","/")}\t{"TRUE" if cookie.get("secure") else "FALSE"}\t{expires}\t{cookie.get("name")}\t{cookie.get("value")}')

with open('/home/administrator/bilibili-cookies.txt', 'w') as f:
    f.write('\n'.join(output))
print(f"✓ Cookie文件已更新")
```

**文件大小判断**：下载时观察文件大小可立即判断是否为大会员版本
- 大会员版本：通常 150MB-300MB/集（1080P）
- 预览版：通常 10-30MB/集（仅2分钟预览）

**实时监控下载**：使用 `process poll` 查看下载进度，发现文件过小立即停止

```python
from hermes_tools import process

# 检查下载任务进度
result = process(action="poll", session_id="proc_xxx")
# 输出示例: "225.78MiB at 10.41MiB/s" → 大会员版本 ✓
# 输出示例: "11.65MiB at 1.00MiB/s" → 预览版 ✗ 需要停止
```

如果看到下载文件只有20MB左右，**立即停止**并刷新Cookie：

```python
# 停止错误的下载任务
process(action="kill", session_id="proc_xxx")

# 重新登录获取有效cookie
# ...（见上方登录流程）
```

## 常见问题

### 只下载到预览版（2分钟）

**原因**：cookie 未正确传递或已过期

**解决方案**：
1. **先检查Cookie是否过期**（见上方"前置检查"）
2. 确认 cookie 文件包含 `SESSDATA`、`bili_jct`、`DedeUserID`
3. 从 Playwright auth JSON 重新生成 cookie 文件
4. 检查 cookie 文件格式是否为 netscape 格式
5. 重新登录B站获取新Cookie

### `--cookies-from-browser` 失败

**原因**：WSL 中无法访问 Windows 的 DPAPI 加密

**错误信息**：
```
ERROR: Failed to decrypt with DPAPI
```

**解决方案**：使用 cookie 文件方式，不要用 `--cookies-from-browser`

### ffmpeg 未安装

**现象**：
```
WARNING: You have requested merging of multiple formats but ffmpeg is not installed
```

**结果**：视频和音频分别保存为 `.mp4` 和 `.m4a` 文件

**解决方案**：
```bash
# 合并分离的文件
ffmpeg -i video.mp4 -i audio.m4a -c:v copy -c:a aac output.mp4
```

### WSL 环境运行 ffmpeg

```bash
# 使用 Windows 上的 ffmpeg
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "
  \$ffmpeg = 'D:\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe'
  & \$ffmpeg -i video.mp4 -i audio.m4a -c:v copy -c:a aac output.mp4 -y
"
```

## 格式选择

### 画质选项

| 选项 | 说明 |
|------|------|
| `bestvideo+bestaudio` | 最高画质 |
| `bestvideo[height<=1080]+bestaudio` | 最高1080P |
| `bestvideo[height<=720]+bestaudio` | 最高720P |
| `best` | 最佳单文件格式 |

### 输出模板

| 变量 | 说明 |
|------|------|
| `%(series)s` | 番剧名称 |
| `%(episode_number)s` | 集数 |
| `%(episode)s` | 集标题 |
| `%(title)s` | 视频标题 |
| `%(uploader)s` | UP主 |

## 完整示例

### 下载番剧最新集

```bash
# 1. 从 Playwright 登录状态生成 cookie
python3 << 'EOF'
import json
with open('/path/to/bilibili-auth.json', 'r') as f:
    data = json.load(f)
cookies = data.get('cookies', [])
output = ['# Netscape HTTP Cookie File']
for c in cookies:
    output.append(f".{c.get('domain','').lstrip('.')}\tTRUE\t{c.get('path','/')}\t{'TRUE' if c.get('secure') else 'FALSE'}\t{c.get('expires',2147483647)}\t{c.get('name')}\t{c.get('value')}")
with open('bilibili-cookies.txt', 'w') as f:
    f.write('\n'.join(output))
EOF

# 2. 下载视频
yt-dlp --cookies bilibili-cookies.txt \
  -f "bestvideo[height<=1080]+bestaudio" \
  --merge-output-format mp4 \
  -o "~/bilibili-download/%(series)s/%(episode_number)s-%(episode)s.%(ext)s" \
  "https://www.bilibili.com/bangumi/play/ep1231584"

# 3. 检查下载结果
ls -lh ~/bilibili-download/*/
```

## Playwright 登录B站（Cookie刷新流程）

如果Cookie已过期或下载到预览版，需要重新登录：

```bash
# 1. 打开有头浏览器（用户可见窗口）
cd /mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced/
powershell.exe -Command "playwright-cli open --headed 'https://www.bilibili.com'"

# 2. 等待用户扫码登录（浏览器窗口已打开）
# 用户在浏览器中完成登录操作

# 3. 登录成功后保存状态
powershell.exe -Command "playwright-cli state-save bilibili-auth-new.json"

# 4. 转换为yt-dlp可用的cookie文件
python3 << 'EOF'
import json
auth_path = "bilibili-auth-new.json"
with open(auth_path, 'r') as f:
    data = json.load(f)
cookies = data.get('cookies', [])
output = ['# Netscape HTTP Cookie File']
for c in cookies:
    domain = c.get('domain', '').lstrip('.')
    if not domain:
        continue
    expires = int(c.get('expires', 0))
    if expires < 0 or expires > 2147483647:
        expires = 2147483647
    output.append(f".{domain}\tTRUE\t{c.get('path','/')}\t{'TRUE' if c.get('secure') else 'FALSE'}\t{expires}\t{c.get('name')}\t{c.get('value')}")
with open('/home/administrator/bilibili-cookies.txt', 'w') as f:
    f.write('\n'.join(output))
print(f"✓ Cookie已更新，共 {len(cookies)} 个")
EOF

# 5. 验证cookie有效性
# 下载时观察文件大小：大会员版本通常150MB+/集，预览版仅20MB左右
```

## 下载后上传到夸克网盘

完整流程：下载 → 合并 → 复制到允许目录 → 上传 → 移动到目标目录

### 1. 下载和合并

```bash
# 下载视频（会生成 .mp4 视频和 .m4a 音频）
yt-dlp --cookies bilibili-cookies.txt \
  -f "bestvideo[height<=1080]+bestaudio" \
  -o "%(series)s/%(episode_number)s-%(episode)s.%(ext)s" \
  "https://www.bilibili.com/bangumi/play/ep1231584"

# 合并视频和音频
ffmpeg -i video.mp4 -i audio.m4a -c:v copy -c:a aac output.mp4
```

### 2. 复制到夸克上传允许目录

playwright-cli 的 upload 命令有路径限制，必须先复制文件：

```bash
# 复制到 skill 目录的 upload 子目录
mkdir -p /mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced/upload/
cp ~/bilibili-download/*/*.mp4 /mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced/upload/
```

### 3. 上传到夸克网盘

```bash
cd /mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced/

# 打开浏览器并加载登录状态
powershell.exe -Command "playwright-cli open"
powershell.exe -Command "playwright-cli state-load quark-auth.json"
powershell.exe -Command "playwright-cli goto 'https://pan.quark.cn/list#/list/all'"

# 创建目录结构（番剧/凡人修仙传）
powershell.exe -Command "playwright-cli click <新建文件夹>"
powershell.exe -Command "playwright-cli fill <input> '番剧'"
powershell.exe -Command "playwright-cli press Enter"

# 进入目录并上传
powershell.exe -Command "playwright-cli click <番剧文件夹>"
powershell.exe -Command "playwright-cli click <上传文件按钮>"
powershell.exe -Command "playwright-cli upload 'upload/175-重返天南23.mp4'"
powershell.exe -Command "playwright-cli click <上传文件按钮>"
powershell.exe -Command "playwright-cli upload 'upload/176-重返天南24.mp4'"
```

### 4. 移动到子目录

如果需要移动到子目录（如 番剧/凡人修仙传/）：

```bash
# 选中已上传的文件
powershell.exe -Command "playwright-cli click <文件checkbox>"

# 移动到子目录
powershell.exe -Command "playwright-cli click <移动到按钮>"
powershell.exe -Command "playwright-cli click <凡人修仙传文件夹>"
powershell.exe -Command "playwright-cli click <确认按钮>"
```

### 完整示例：下载凡人修仙传并上传

```bash
# 1. 下载最新2集
yt-dlp --cookies bilibili-cookies.txt \
  -f "bestvideo[height<=1080]+bestaudio" \
  --merge-output-format mp4 \
  -o "%(series)s/%(episode_number)s-%(episode)s.%(ext)s" \
  "https://www.bilibili.com/bangumi/play/ep1231584" \
  "https://www.bilibili.com/bangumi/play/ep1231583"

# 2. 合并（如果没有 ffmpeg）
# 使用 Windows ffmpeg
powershell.exe -Command "
  \$ffmpeg = 'D:\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe'
  & \$ffmpeg -i video.mp4 -i audio.m4a -c:v copy -c:a aac output.mp4 -y
"

# 3. 复制到上传目录
cp ~/bilibili-download/*/*.mp4 /mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced/upload/

# 4. 上传到夸克网盘（见上文）
```

## 相关技能

- `playwright-cli`: Playwright 浏览器自动化
- `quark-file-organization`: 夸克网盘文件上传和整理（详细的上传流程）
- `save-music-to-quark-enhanced`: 提供 quark-auth.json 登录状态
- `youtube-content`: YouTube 内容处理
