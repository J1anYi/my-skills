---
name: bilibili-download-to-quark
description: |
  从B站下载视频/番剧并上传到夸克网盘。
  
  功能：
  - 使用 yt-dlp 下载B站大会员视频
  - 自动合并视频和音频流
  - 上传到夸克网盘指定目录
  - SQLite记录防重复下载
  
  触发场景：
  - 用户想要下载B站视频/番剧
  - 用户需要保存B站大会员内容到云盘
  - 用户提到凡人修仙传等B站番剧下载

# ===== 强制执行流程 =====
hooks:
  before_download: |
    ## 🔔 下载前检查（必须执行）
    
    每次下载前，**必须先检查数据库**，跳过已下载的剧集：
    
    ```bash
    # 初始化数据库（首次使用）
    python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/download_tracker.py init
    
    # 检查是否已下载
    python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/download_tracker.py check <episode_id>
    ```
    
    如果返回 `✓ 已下载`，则跳过该剧集。

  after_download: |
    ## 🔔 下载后记录（必须执行）
    
    每次下载成功后，**必须记录到数据库**：
    
    ```bash
    python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/download_tracker.py add <episode_id> "<title>" \
      --series "<番剧名>" --episode <集数> --size "<大小>"
    ```

  after_upload: |
    ## 🔔 上传后标记（必须执行）
    
    上传到夸克网盘后，**必须标记已上传**：
    
    ```bash
    python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/download_tracker.py uploaded <episode_id> --quark "<夸克路径>"
    ```
---

# B站视频下载到夸克网盘

自动化工作流：登录B站 → yt-dlp下载视频 → 合并音视频 → 上传夸克网盘。

## 目录结构

```
~/.claude/skills/save-music-to-quark-enhanced/
├── bilibili-auth.json      # B站登录状态
├── bilibili-cookies.txt    # yt-dlp可用的cookie文件
└── quark-auth.json         # 夸克网盘登录状态

~/bilibili-download/        # 建议symlink到D盘，避免C盘空间不足
├── fanren-full/            # 原始下载（视频+音频分离）
└── fanren-merged/          # 合并后的视频
```

⚠️ **磁盘空间注意**：番剧下载体积大（每集约500-700MB），应存放到D盘而非C盘：

```bash
# 创建D盘目录并symlink
mkdir -p /mnt/d/bilibili-download
ln -sfn /mnt/d/bilibili-download ~/bilibili-download
```

如果C盘空间不足，用rsync移动已有文件：
```bash
rsync -avh --progress --remove-source-files ~/bilibili-download/ /mnt/d/bilibili-download/
```

## 🔔 强制执行流程（Hook）

> ⚠️ 调用此Skill时，**必须按顺序执行以下步骤**，不可跳过。

### Hook 1: 下载前检查 (before_download)

```bash
# 检查数据库是否已初始化
python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/download_tracker.py init

# 检查目标剧集是否已下载
python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/download_tracker.py check ep1231584
```

- 如果返回 `✓ 已下载` → **跳过该剧集**
- 如果返回 `✗ 未下载` → 继续下载

### Hook 2: 下载后记录 (after_download)

下载成功后，**立即记录**：

```bash
python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/download_tracker.py add ep1231584 "重返天南24" \
  --series "凡人修仙传" --episode 176 --size "471.7M"
```

### Hook 3: 上传后标记 (after_upload)

上传到夸克网盘后，**标记已上传**：

```bash
python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/download_tracker.py uploaded ep1231584 \
  --quark "番剧/凡人修仙传/176-重返天南24.mp4"
```

---

## 核心步骤

### 0. 准备工作（首次使用）

```bash
# 初始化数据库
python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/download_tracker.py init

# 查看已有记录
python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/download_tracker.py stats
```

### 1. B站登录并保存Cookie

**⚠️ 重要：使用PC端登录流程，不是H5移动端！**

详细登录流程请参考 `playwright-login-handler` skill，关键步骤：

```bash
# 1. 用 --headed 打开有头浏览器
cd /mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced/
powershell.exe -Command "playwright-cli open --headed"

# 2. 导航到 B站首页
powershell.exe -Command "playwright-cli goto 'https://www.bilibili.com'"

# 3. 点击登录按钮（打开登录弹窗）
powershell.exe -Command "playwright-cli click e51"  # e51 是登录按钮的 ref

# 4. 用户扫码登录后保存状态
powershell.exe -Command "playwright-cli state-save bilibili-auth.json"
```

**关键点**：
- 使用 `--headed` 打开有头浏览器，用户能看到窗口并扫码
- B站 PC 端登录是在首页点击登录按钮弹出登录框
- 不要使用 H5 移动端登录页（`passport.bilibili.com/h5-app/...`）

**从auth.json提取cookie供yt-dlp使用**：
python3 << 'EOF'
import json

with open('bilibili-auth.json', 'r') as f:
    data = json.load(f)

cookies = data.get('cookies', [])
output = ['# Netscape HTTP Cookie File']
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
EOF
```

**方式2：`--cookies-from-browser` 问题**

⚠️ 在WSL环境中，`yt-dlp --cookies-from-browser edge/chrome` 会遇到DPAPI解密失败：
```
ERROR: Failed to decrypt with DPAPI
```

解决方案：从Playwright保存的auth.json提取cookie。

### 2. 查找番剧完整剧集ID（重要！）

⚠️ **B站番剧的剧集ID通常不连续**，不能简单通过ID+1推算下一集。必须先获取完整ID列表。

⚠️ **同一番剧可能有多个版本**（如"凡人修仙传"有重制版和原版），不同版本的剧集ID完全不同。必须先搜索确认目标版本。

**方法1：搜索番剧确认版本（推荐）**

```bash
# 1. 搜索番剧名
powershell.exe -Command "playwright-cli goto 'https://search.bilibili.com/bangumi?keyword=凡人修仙传'"

# 2. 查看搜索结果中的不同版本
powershell.exe -Command "playwright-cli snapshot" 2>&1 | grep -E "凡人修仙传|重制|风起天南"

# 3. 点击目标版本进入
powershell.exe -Command "playwright-cli click <版本ref>"
```

**版本区分示例（凡人修仙传）：**
- **重制版**：EP1-21，剧集ID `ep733316-ep733336`（燕家堡之战系列）
- **原版**：EP1-56，剧集ID分散在不同范围：
  - EP22-30: `ep428988-ep428996`（魔道争锋1-9）
  - EP31-35: `ep446721-ep446725`（魔道争锋10-14）
  - EP36-39: `ep467542-ep467545`（魔道争锋15-18）
  - EP40-46: `ep471417-ep471419`, `ep471894-ep471897`（魔道争锋19-25）
  - EP47-56: `ep471898-ep471907`（再别天南1-10）
- 第二季：从EP73开始

⚠️ **原版画质较低**：原版/老番剧可能没有1080P选项，最高只有480P（format 100023），文件较小（~40-70MB/集）

**方法2：从番剧页面提取**

```bash
# 1. 用playwright-cli打开任意一集
powershell.exe -Command "playwright-cli open 'https://www.bilibili.com/bangumi/play/ep779775'"

# 2. 等待页面加载后获取snapshot
powershell.exe -Command "playwright-cli snapshot" 2>&1 | grep -oP '/bangumi/play/ep\d+' | sed 's|/bangumi/play/ep||' | sort -u

# 输出示例（葬送的芙莉莲）：
# 779775, 779776, 779777, 779778, 780981, 780982, 780983, 787483, ...
```

**方法3：通过yt-dlp验证ID对应集数**

找到剧集ID后，务必验证ID对应的集数和时长，排除预告片：

```bash
# 批量验证ID（检查episode_number、episode标题和duration）
export http_proxy=""
export https_proxy=""

for ep_id in 446721 446722 467542 467543; do
  yt-dlp --cookies bilibili-cookies.txt \
    --print "%(episode_number)s|%(episode)s|%(duration)s" \
    "https://www.bilibili.com/bangumi/play/ep${ep_id}" 2>/dev/null
done

# 输出示例：
# 31|魔道争锋10|1470.056    ← 正片（~24分钟）✓
# 32|魔道争锋11|1420.123    ← 正片 ✓
# 333|前方高燃！...|180.456  ← 花絮/预告，跳过 ✗
```

**判断标准：**
- `duration > 1000`（约16分钟以上）= 正片 ✓
- `duration < 500`（几分钟以内）= 预告/花絮，跳过 ✗

**验证剧集ID对应的集数**

```bash
# 批量验证ID（检查episode_number和duration）
export http_proxy=""
export https_proxy=""

for ep_id in 779775 779776 787483 791310; do
  yt-dlp --cookies "bilibili-cookies.txt" \
    --print "%(episode_number)s|%(episode)s|%(duration)s" \
    "https://www.bilibili.com/bangumi/play/ep${ep_id}" 2>&1
done

# 输出示例：
# ep779775: 1|冒险的结束|1470.056    ← 正片（~24分钟）
# ep787483: 8|葬送的芙莉莲|1470.056  ← 正片
# ep791080: 44|Episode 44|42.452    ← 第二季预览（跳过）
```

**判断标准：**
- `duration > 1000`（约16分钟以上）= 正片 ✓
- `duration < 200`（几分钟以内）= 预览/预告，跳过 ✗

### 3. 使用yt-dlp下载视频

⚠️ **关键：必须指定正确的格式ID！**

B站大会员视频有多个版本：
- **预览版** (format 100027): ~120MB, 只有几分钟预览内容
- **完整版1080P** (format 30112): ~400-500MB, 正片
- **完整版4K** (format 30125): ~550-650MB, 正片

使用 `-f "bestvideo..."` 会下载预览版！必须显式指定格式：

```bash
# ✅ 正确：下载1080P完整版
yt-dlp --cookies bilibili-cookies.txt \
  -f "30112+30280" \
  -o "%(episode_number)s-%(episode)s.%(ext)s" \
  "https://www.bilibili.com/bangumi/play/ep787483"

# ❌ 错误：会下载预览版（只有~120MB）
yt-dlp --cookies bilibili-cookies.txt \
  -f "bestvideo[height<=1080]+bestaudio" \
  "https://www.bilibili.com/bangumi/play/ep787483"
```

**查看可用格式**：
```bash
yt-dlp --cookies bilibili-cookies.txt -F "https://www.bilibili.com/bangumi/play/ep787483"
# 输出示例：
# 30112  mp4 1920x1080  24     |  426.49MiB  ← 完整版1080P
# 100027 mp4 1920x1080  24     |  121.19MiB  ← 预览版（跳过）
# 30125  mp4 3840x2160  24 10  |  568.40MiB  ← 完整版4K
# 30280  m4a audio only         |   32.33MiB  ← 音频
```

**批量下载多集**：
```bash
yt-dlp --cookies bilibili-cookies.txt \
  -f "30112+30280" \
  -o "EP%(episode_number)02d-%(episode)s.%(ext)s" \
  "https://www.bilibili.com/bangumi/play/ep787483" \
  "https://www.bilibili.com/bangumi/play/ep787484" \
  "https://www.bilibili.com/bangumi/play/ep787485"
```

**重要参数说明**：
- `--cookies`: 指定cookie文件，大会员视频必需
- `-f "30112+30280"`: 1080P视频+音频（必须显式指定！）
- `-f "30125+30280"`: 4K视频+音频（更大文件）
- `%(episode_number)s`: 集数
- `%(episode)s`: 集标题

### 4. 合并视频和音频（如未自动合并）

如果没有ffmpeg，yt-dlp会下载分离的视频和音频文件。

⚠️ **WSL路径转换**：Windows ffmpeg.exe 无法识别 `/mnt/d/` 格式的WSL路径，必须转换为Windows格式：

```bash
# Windows ffmpeg路径
FFMPEG="/mnt/d/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe"

# ❌ 错误：WSL路径不工作
$FFMPEG -i "/mnt/d/video.mp4" -i "/mnt/d/audio.m4a" -c copy output.mp4

# ✅ 正确：转换为Windows路径
$FFMPEG -i "D:\\bilibili-download\\raw\\EP08.f30112.mp4" \
        -i "D:\\bilibili-download\\raw\\EP08.f30280.m4a" \
        -c:v copy -c:a aac \
        "D:\\bilibili-download\\merged\\葬送的芙莉莲_EP08.mp4" -y
```

**批量合并脚本**：
```bash
FFMPEG="/mnt/d/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe"
RAW_DIR="/mnt/d/bilibili-download/raw"
MERGED_DIR="/mnt/d/bilibili-download/merged"

for ep in 08 09 10 11 12; do
  video=$(ls "$RAW_DIR"/EP${ep}-*.f30112.mp4 2>/dev/null | head -1)
  audio=$(ls "$RAW_DIR"/EP${ep}-*.f30280.m4a 2>/dev/null | head -1)
  
  if [ -f "$video" ] && [ -f "$audio" ]; then
    # 转换为Windows路径
    win_video=$(echo "$video" | sed 's|/mnt/d|D:|' | tr '/' '\\')
    win_audio=$(echo "$audio" | sed 's|/mnt/d|D:|' | tr '/' '\\')
    win_output="D:\\bilibili-download\\merged\\葬送的芙莉莲_EP${ep}.mp4"
    
    echo "合并 EP${ep}..."
    "$FFMPEG" -i "$win_video" -i "$win_audio" -c:v copy -c:a aac "$win_output" -y 2>/dev/null
  fi
done
```

### 4. 上传到夸克网盘

#### 🎯 推荐方式：使用批量上传脚本（最可靠）

下载完成后，使用 `quark_batch_upload.py` 脚本批量上传：

```bash
# 上传葬送的芙莉莲全部28集
python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/quark_batch_upload.py \
  --target-dir "番剧/葬送的芙莉莲" \
  --files /mnt/d/bilibili-download/frieren-merged/*.mp4 \
  --wait 20 \
  --pattern "葬送的芙莉莲_EP(\d+)\.mp4"

# 参数说明：
# --target-dir: 夸克网盘目标目录（会自动创建）
# --files: 本地文件列表（支持通配符）
# --wait: 每个文件上传后等待秒数（默认15秒，大文件建议20-30秒）
# --pattern: 用于验证已上传文件的正则模式
```

**脚本特性：**
- ✅ **串行上传 + 充足等待**：避免限流，确保每个文件真正上传完成
- ✅ **自动验证**：上传后检查文件数量，确保成功
- ✅ **动态获取ref**：适应页面刷新后ref变化
- ✅ **处理弹窗**：自动关闭modal状态
- ✅ **支持中文文件名**：使用PowerShell正确处理

**完整示例：**

```bash
# 1. 下载番剧
cd ~/bilibili-download/frieren-merged
yt-dlp --cookies ~/.claude/skills/save-music-to-quark-enhanced/bilibili-cookies.txt \
  -f "30112+30280" \
  -o "葬送的芙莉莲_EP%(episode_number)02d.%(ext)s" \
  "https://www.bilibili.com/bangumi/play/ep779775" \
  "https://www.bilibili.com/bangumi/play/ep779776" \
  # ... 更多URL

# 2. 一键上传到夸克
python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/quark_batch_upload.py \
  --target-dir "番剧/葬送的芙莉莲" \
  --files ~/bilibili-download/frieren-merged/*.mp4 \
  --wait 20 \
  --pattern "葬送的芙莉莲_EP(\d+)\.mp4"
```

---

#### 手动上传方式

**⚠️ 关键：正确的登录流程**

夸克网页版登录状态加载必须在导航**之前**，否则会被重定向到登录页：

```bash
# ✅ 正确流程（登录成功）
playwright-cli open                           # 1. 打开浏览器（不导航）
playwright-cli state-load quark-auth.json     # 2. 立即加载登录状态
playwright-cli goto https://pan.quark.cn/list # 3. 然后导航

# ❌ 错误流程（被重定向到登录页）
playwright-cli open https://pan.quark.cn/list # 1. 打开并导航
playwright-cli state-load quark-auth.json     # 2. 太晚了！已经重定向
```

**完整上传流程**：

```bash
# 1. 正确加载登录状态
playwright-cli open
playwright-cli state-load quark-auth.json
playwright-cli goto https://pan.quark.cn/list

# 2. 进入目标目录（如番剧/凡人修仙传）
playwright-cli click <番剧ref>
playwright-cli click <凡人修仙传ref>

# 3. 点击上传按钮
playwright-cli click <上传文件button>

# 4. 选择文件上传（文件必须在允许目录下）
playwright-cli upload "temp-upload/1-1 风起天南1重制版.mp4"
```

**上传目录限制**：

⚠️ playwright-cli只能上传"allowed roots"目录下的文件：

```
# 允许的根目录（skill目录及其子目录）
C:\Users\Administrator\.claude\skills\save-music-to-quark-enhanced\

# 解决方案：复制文件到skill目录的子目录
mkdir -p /mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced/temp-upload/
cp ~/bilibili-download/fanren-merged/*.mp4 /mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced/temp-upload/

# 使用PowerShell上传（处理中文文件名）
powershell.exe -Command "playwright-cli upload 'C:\Users\Administrator\.claude\skills\save-music-to-quark-enhanced\temp-upload\1-1 风起天南1重制版.mp4'"
```

**批量上传示例**：

```bash
# 复制所有文件到允许目录
SKILL_DIR="/mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced"
mkdir -p "$SKILL_DIR/temp-upload"
cp ~/bilibili-download/fanren-merged/*.mp4 "$SKILL_DIR/temp-upload/"

# 逐个上传（需要每次点击上传按钮）
for file in 1-1 2-2 3-3; do
  # 点击上传按钮打开文件选择器
  /mnt/c/Windows/System32/cmd.exe /c "playwright-cli click <上传按钮ref>"
  sleep 1
  # 上传文件
  /mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command \
    "playwright-cli upload 'C:\Users\Administrator\.claude\skills\save-music-to-quark-enhanced\temp-upload\${file} 风起天南.mp4'"
  sleep 2
done

# 清理临时文件
rm -rf "$SKILL_DIR/temp-upload"
```

**🎯 一键上传函数（推荐）**：

将以下函数添加到 `~/.bashrc` 或直接使用：

```bash
# 夸克网盘批量上传函数
quark_upload() {
  local skill_dir="/mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced"
  local temp_dir="$skill_dir/temp-upload"
  
  # 1. 复制文件到允许目录
  mkdir -p "$temp_dir"
  cp "$@" "$temp_dir/"
  
  # 2. 确保夸克已登录
  cd "$skill_dir"
  /mnt/c/Windows/System32/cmd.exe /c "playwright-cli close" 2>/dev/null
  sleep 1
  /mnt/c/Windows/System32/cmd.exe /c "playwright-cli open"
  sleep 1
  /mnt/c/Windows/System32/cmd.exe /c "playwright-cli state-load quark-auth.json"
  sleep 1
  /mnt/c/Windows/System32/cmd.exe /c "playwright-cli goto https://pan.quark.cn/list"
  sleep 3
  
  # 3. 逐个上传
  for file in "$@"; do
    local filename=$(basename "$file")
    echo "上传: $filename"
    
    # 点击上传按钮（ref需要从snapshot获取）
    /mnt/c/Windows/System32/cmd.exe /c "playwright-cli click e556"
    sleep 1
    
    # 上传文件
    /mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command \
      "playwright-cli upload 'C:\Users\Administrator\.claude\skills\save-music-to-quark-enhanced\temp-upload\$filename'"
    sleep 2
  done
  
  # 4. 清理
  rm -rf "$temp_dir"
  echo "上传完成！"
}

# 使用示例
quark_upload ~/bilibili-download/fanren-merged/*.mp4
```

**📁 目标目录导航**：

上传前需要导航到目标目录：

```bash
# 方法1：点击导航
playwright-cli snapshot                           # 获取refs
playwright-cli click <番剧ref>                    # 进入番剧
playwright-cli click <凡人修仙传ref>              # 进入目标

# 方法2：直接URL（如果知道目录ID）
# 格式: https://pan.quark.cn/list#/list/all/<目录ID>
playwright-cli goto "https://pan.quark.cn/list#/list/all/5956ad3dd7754de1b1246f670a00e305-%E7%95%AA%E5%89%A7/5590a3e8cfc541819acad46534c46dd0-%E5%87%A1%E4%BA%BA%E4%BF%AE%E4%BB%99%E4%BC%A0"
```

**💡 上传技巧与坑点（重要！）**

#### ⚠️ 关键问题：upload命令不等待实际上传完成

`playwright-cli upload` 命令在选择文件后**立即返回成功**，但文件实际传输需要时间：
- 500MB文件：约10-20秒
- 1GB文件：约20-40秒
- **连续快速上传会导致大部分文件丢失！**

```bash
# ❌ 错误：等待太短，28个文件只有3个成功
sleep 2

# ✅ 正确：大文件需要充足等待
sleep 20  # 500MB文件
sleep 30  # 1GB文件
```

#### ✅ 解决方案：使用批量上传脚本（推荐）

```bash
python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/quark_batch_upload.py \
  --target-dir "番剧/葬送的芙莉莲" \
  --files /mnt/d/bilibili-download/frieren-merged/*.mp4 \
  --wait 20
```

脚本会：
1. 串行上传，每个文件间隔足够时间
2. 上传后验证文件数量
3. 自动处理弹窗和ref变化

#### 其他技巧

1. **获取上传按钮ref**：每次页面刷新后ref可能变化，需要重新获取：
   ```bash
   powershell.exe -Command "playwright-cli snapshot" 2>&1 | grep "上传文件"
   ```

2. **处理中文文件名**：必须用PowerShell，cmd.exe会乱码：
   ```bash
   # ✅ PowerShell（正确处理中文）
   powershell.exe -Command "playwright-cli upload 'C:\\...\\葬送的芙莉莲_EP01.mp4'"
   ```

3. **批量上传验证**：上传完成后务必验证文件数量：
   ```bash
   powershell.exe -Command "playwright-cli snapshot" 2>&1 | grep -c "葬送的芙莉莲_EP"
   ```

4. **推荐分批上传**：每批5-10个文件，中间刷新页面确认

### 5. 移动文件到正确目录

上传后文件在当前目录，需要移动到目标目录：

```bash
# 1. 选中文件（点击checkbox）
playwright-cli click <文件checkbox ref>

# 2. 点击"移动到..."
playwright-cli click <移动到button ref>

# 3. 在对话框中导航到目标目录
playwright-cli click <番剧ref>      # 展开
playwright-cli click <凡人修仙传ref> # 选中

# 4. 确认移动
playwright-cli click <确认button ref>
```

## 完整示例：下载凡人修仙传（带Hook）

```bash
# ========================================
# 步骤0: 初始化数据库（首次使用）
# ========================================
python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/download_tracker.py init

# ========================================
# 步骤1: 检查已下载记录 [Hook: before_download]
# ========================================
python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/download_tracker.py list --series "凡人修仙传"

# 检查单集是否已下载
for ep_id in ep1231584 ep1231583; do
  if python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/download_tracker.py check $ep_id | grep -q "已下载"; then
    echo "跳过 $ep_id (已下载)"
    continue
  fi
  # 将需要下载的ID加入列表
  to_download="$to_download $ep_id"
done

# ========================================
# 步骤2: 准备Cookie
# ========================================
cd ~/.claude/skills/save-music-to-quark-enhanced/

# 如果已有bilibili-auth.json，提取cookie
python3 << 'EOF'
import json
with open('bilibili-auth.json', 'r') as f:
    data = json.load(f)
cookies = data.get('cookies', [])
output = ['# Netscape HTTP Cookie File']
for c in cookies:
    domain = c.get('domain', '').lstrip('.')
    path = c.get('path', '/')
    secure = 'TRUE' if c.get('secure', False) else 'FALSE'
    name = c.get('name', '')
    value = c.get('value', '')
    expires = int(c.get('expires', 0))
    if expires < 0: expires = 2147483647
    output.append(f'.{domain}\tTRUE\t{path}\t{secure}\t{expires}\t{name}\t{value}')
with open('bilibili-cookies.txt', 'w') as f:
    f.write('\n'.join(output))
print(f'Cookie文件已保存，共 {len(cookies)} 个')
EOF

# ========================================
# 步骤3: 下载视频
# ========================================
mkdir -p ~/bilibili-download/fanren-merged
cd ~/bilibili-download/fanren-merged

yt-dlp --cookies ~/.claude/skills/save-music-to-quark-enhanced/bilibili-cookies.txt \
  -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
  --merge-output-format mp4 \
  -o "%(episode_number)s-%(episode)s.%(ext)s" \
  "https://www.bilibili.com/bangumi/play/ep1231584" \
  "https://www.bilibili.com/bangumi/play/ep1231583"

# ========================================
# 步骤4: 记录下载 [Hook: after_download]
# ========================================
python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/download_tracker.py add ep1231584 "重返天南24" \
  --series "凡人修仙传" --episode 176 --size "471.7M"

python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/download_tracker.py add ep1231583 "重返天南23" \
  --series "凡人修仙传" --episode 175 --size "403M"

# ========================================
# 步骤5: 上传到夸克网盘
# ========================================
# 使用批量上传脚本（推荐）
python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/quark_batch_upload.py \
  --target-dir "番剧/凡人修仙传" \
  --files ~/bilibili-download/fanren-merged/*.mp4 \
  --wait 20 \
  --pattern "凡人修仙传_EP(\d+)\.mp4"

# 或者手动上传（不推荐，容易丢失文件）
# 见上方手动上传步骤

# ========================================
# 步骤6: 标记已上传 [Hook: after_upload]
# ========================================
python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/download_tracker.py uploaded ep1231584 \
  --quark "番剧/凡人修仙传/176-重返天南24.mp4"

python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/download_tracker.py uploaded ep1231583 \
  --quark "番剧/凡人修仙传/175-重返天南23.mp4"

# ========================================
# 步骤7: 验证
# ========================================
python3 ~/.hermes/skills/automation/bilibili-download-to-quark/scripts/download_tracker.py stats
```

## 📤 快速上传到夸克

### 一键上传脚本

将以下脚本保存为 `scripts/quark_upload.sh`：

```bash
#!/bin/bash
# quark_upload.sh - 上传文件到夸克网盘
# 用法: ./quark_upload.sh <目标目录> <文件1> [文件2] ...

set -e

TARGET_DIR="$1"
shift
FILES=("$@")

SKILL_DIR="/mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced"
TEMP_DIR="$SKILL_DIR/temp-upload"

# 1. 复制文件到允许目录
mkdir -p "$TEMP_DIR"
cp "${FILES[@]}" "$TEMP_DIR/"

# 2. 初始化浏览器
cd "$SKILL_DIR"
/mnt/c/Windows/System32/cmd.exe /c "playwright-cli close" 2>/dev/null || true
sleep 1
/mnt/c/Windows/System32/cmd.exe /c "playwright-cli open"
sleep 1
/mnt/c/Windows/System32/cmd.exe /c "playwright-cli state-load quark-auth.json"
sleep 1
/mnt/c/Windows/System32/cmd.exe /c "playwright-cli goto https://pan.quark.cn/list"
sleep 3

# 3. 获取上传按钮ref
UPLOAD_BTN=$(/mnt/c/Windows/System32/cmd.exe /c "playwright-cli snapshot" 2>&1 | grep "上传文件" | head -1 | grep -oE "ref=e[0-9]+" | head -1)
echo "上传按钮: $UPLOAD_BTN"

# 4. 导航到目标目录
for dir in $(echo "$TARGET_DIR" | tr '/' ' '); do
  REF=$(/mnt/c/Windows/System32/cmd.exe /c "playwright-cli snapshot" 2>&1 | grep "\"$dir\"" | grep -oE "ref=e[0-9]+" | head -1)
  if [[ -n "$REF" ]]; then
    /mnt/c/Windows/System32/cmd.exe /c "playwright-cli click $REF"
    sleep 2
  fi
done

# 5. 逐个上传
for file in "${FILES[@]}"; do
  filename=$(basename "$file")
  echo "上传: $filename"
  
  # 点击上传按钮
  /mnt/c/Windows/System32/cmd.exe /c "playwright-cli click $UPLOAD_BTN"
  sleep 1
  
  # 上传文件
  /mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command \
    "playwright-cli upload 'C:\Users\Administrator\.claude\skills\save-music-to-quark-enhanced\temp-upload\$filename'"
  sleep 3
done

# 6. 清理
rm -rf "$TEMP_DIR"
echo "✅ 上传完成！"
```

**使用示例**：

```bash
# 上传到番剧/凡人修仙传目录
chmod +x scripts/quark_upload.sh
./scripts/quark_upload.sh "番剧/凡人修仙传" ~/bilibili-download/fanren-merged/*.mp4
```

### 手动上传步骤（推荐新手）

如果脚本遇到问题，按以下步骤手动操作：

```bash
# 步骤1: 准备文件
SKILL_DIR="/mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced"
mkdir -p "$SKILL_DIR/temp-upload"
cp ~/bilibili-download/fanren-merged/*.mp4 "$SKILL_DIR/temp-upload/"

# 步骤2: 初始化浏览器
cd "$SKILL_DIR"
/mnt/c/Windows/System32/cmd.exe /c "playwright-cli close"
/mnt/c/Windows/System32/cmd.exe /c "playwright-cli open"
/mnt/c/Windows/System32/cmd.exe /c "playwright-cli state-load quark-auth.json"
/mnt/c/Windows/System32/cmd.exe /c "playwright-cli goto https://pan.quark.cn/list"

# 步骤3: 获取当前页面的refs
/mnt/c/Windows/System32/cmd.exe /c "playwright-cli snapshot" > /tmp/quark-snapshot.txt

# 步骤4: 导航到目标目录（点击对应的ref）
# 从snapshot中找到目标文件夹的ref
grep "番剧" /tmp/quark-snapshot.txt
/mnt/c/Windows/System32/cmd.exe /c "playwright-cli click e538"  # 替换为实际ref

# 步骤5: 点击上传按钮
# 从snapshot中找到上传按钮的ref
grep "上传文件" /tmp/quark-snapshot.txt
/mnt/c/Windows/System32/cmd.exe /c "playwright-cli click e556"  # 替换为实际ref

# 步骤6: 上传文件（使用PowerShell处理中文文件名）
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command \
  "playwright-cli upload 'C:\Users\Administrator\.claude\skills\save-music-to-quark-enhanced\temp-upload\1-1 风起天南1重制版.mp4'"

# 步骤7: 重复步骤5-6上传其他文件

# 步骤8: 清理临时文件
rm -rf "$SKILL_DIR/temp-upload"
```

---

## 常见问题

| 问题 | 解决方案 |
|------|----------|
| **下载的文件只有~100MB** | 使用 `-f "30112+30280"` 显式指定完整版格式，不要用 `bestvideo` |
| **下载的文件只有~40MB (480P)** | 原版/老番剧可能没有1080P选项，用 `-F` 查看可用格式后选择最高画质 |
| **yt-dlp只下载预览版** | 格式选择器 `bestvideo` 会选到预览版(format 100027)，必须用 `-F` 查看后指定完整版ID(30112) |
| ffmpeg无法找到输入文件 | WSL路径`/mnt/d/`需转换为Windows路径`D:\\\\` |
| cookie文件格式问题 | 从auth.json重新提取 |
| DPAPI解密失败 | WSL环境无法用--cookies-from-browser，改用cookie文件 |
| 文件无法上传 | 文件必须在playwright-cli允许的目录下 |
| 上传后找不到文件 | 检查是否上传到了当前目录而非目标目录 |
| ffmpeg未安装 | 使用Windows ffmpeg: `D:\\\\ffmpeg-xxx\\\\bin\\\\ffmpeg.exe` |
| 代理连接失败 | WSL代理可能无法访问B站，需禁用：`export http_proxy="" https_proxy=""` |
| 夸克网页版登录过期 | 网页版登录状态会过期，需重新扫码登录或使用客户端上传 |
| **批量上传后文件丢失** | ⚠️ 最常见问题！`upload`命令立即返回不等待完成。使用 `quark_batch_upload.py` 脚本，或每个文件等待20-30秒后验证 |
| **WSL .part文件重命名失败** | WSL环境下大文件下载后yt-dlp可能无法将`.part`文件重命名为最终文件。症状：`ERROR: Unable to rename file`。解决：手动重命名`mv file.part file`，或检查磁盘空间和权限 |
| **上传按钮ref找不到** | 页面刷新后ref会变化，需要用脚本动态获取或手动查询 |
| **中文文件名乱码** | 必须用PowerShell执行，不要用cmd.exe |
| **批量上传后文件丢失** | upload命令立即返回，不等待实际上传完成。大文件需要sleep 10-30秒，必须验证上传数量 |

### Cookie文件混淆问题

⚠️ **常见错误**：`bilibili-cookies.txt` 和 `quark-auth.json` 是两个不同平台的登录状态！

- `bilibili-cookies.txt` / `bilibili-auth.json` → **B站登录状态**，用于yt-dlp下载大会员视频
- `quark-auth.json` → **夸克网盘登录状态**，用于上传文件

**错误示例**：
```bash
# ❌ 检查bilibili-cookies.txt时发现是夸克的cookie
head -5 bilibili-cookies.txt
# .b.quark.cn  ← 这是夸克的！不是B站的！
```

**下载前必须验证cookie域名**：
```bash
# ✅ 验证cookie是否为B站的
head -5 bilibili-cookies.txt | grep -i bilibili
# 应输出包含 .bilibili.com 的行

# 如果没有输出，说明cookie文件错误，需要重新登录B站获取
```

**解决方案**：确保从正确的来源提取cookie：
```bash
# 1. 先登录B站获取bilibili-auth.json
playwright-cli open 'https://www.bilibili.com'
# 用户扫码登录后
playwright-cli state-save bilibili-auth.json

# 2. 从auth.json提取cookie
python3 << 'EOF'
import json
with open('bilibili-auth.json', 'r') as f:
    data = json.load(f)
# 确保domain是.bilibili.com，不是.quark.cn
cookies = [c for c in data.get('cookies', []) if 'bilibili' in c.get('domain', '')]
# ... 继续提取
EOF
```

### WSL代理问题

⚠️ 在WSL环境下，如果配置了HTTP代理（如 `http://172.26.0.1:8317`），yt-dlp会自动使用代理访问B站，但代理可能无法访问B站API导致下载失败：

```
ERROR: Unable to download webpage: ('Unable to connect to proxy', OSError('Tunnel connection failed: 404 Not Found'))
```

**解决方案**：下载前禁用代理

```bash
# 方法1：临时禁用
export http_proxy=""
export https_proxy=""

# 方法2：在命令中设置
http_proxy="" https_proxy="" yt-dlp --cookies bilibili-cookies.txt ...
```

### 批量下载优化

下载多集时，建议一次传入多个URL，比逐个下载更高效：

```bash
# 批量下载（推荐）
yt-dlp --cookies bilibili-cookies.txt \
  -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
  --merge-output-format mp4 \
  -o "%(episode_number)s-%(episode)s.%(ext)s" \
  "https://www.bilibili.com/bangumi/play/ep733316" \
  "https://www.bilibili.com/bangumi/play/ep733317" \
  "https://www.bilibili.com/bangumi/play/ep733318" \
  # ... 更多URL
```

### ⚠️ 批量下载脚本陷阱

**陷阱：Bash 关联数组遍历顺序随机**

```bash
# ❌ 错误：关联数组遍历顺序不可预测，部分剧集会被跳过
declare -A EP_MAP
EP_MAP[4]=733319; EP_MAP[5]=733320; EP_MAP[6]=733321
for ep_num in "${!EP_MAP[@]}"; do  # 遍历顺序随机！
    yt-dlp ...
done

# ✅ 正确：使用普通数组按顺序遍历
for ep_num in 4 5 6 7 8 9 10; do  # 固定顺序
    ep_id=$((733316 + ep_num - 1))
    yt-dlp ...
done
```

**陷阱：后台进程意外终止**

后台下载任务可能因网络波动、SSH 断开等原因终止。建议：
1. 使用 `notify_on_complete: true` 获取完成通知
2. 下载前检查已完成的文件，支持断点续传
3. 使用 `proc_*` 进程 ID 定期检查任务状态

**检查后台下载进度**：
```bash
# 方法1：检查已完成的文件数
ls /mnt/d/bilibili-download/凡人修仙传/*.mp4 2>/dev/null | grep -v '\.f' | wc -l

# 方法2：查看临时文件（下载中的）
ls /mnt/d/bilibili-download/凡人修仙传/*.part 2>/dev/null

# 方法3：检查yt-dlp进程
ps aux | grep yt-dlp | grep -v grep
```

### 夸克网页版登录状态

⚠️ 夸克网盘网页版登录状态会过期，页面可能显示：
- "客户端已登录，点击可直接登录"
- 账号名（如"夸父1605"）但实际未登录

**解决方案**：
1. 手动在浏览器中扫码登录夸克网盘
2. 登录后保存新的auth.json
3. 或直接使用夸克客户端上传文件

## 关键发现

### 为什么yt-dlp只下载预览版？

B站大会员视频需要正确的cookie验证身份。问题原因：

1. **`--cookies-from-browser` 失败**：WSL环境下无法解密Windows浏览器的cookie（DPAPI）
2. **cookie文件不完整**：必须包含 `SESSDATA`（HttpOnly，不会出现在document.cookie中）
3. **解决方案**：从Playwright保存的 `bilibili-auth.json` 提取完整cookie

### 正确的Cookie提取方法

```python
import json

# 从Playwright auth.json读取
with open('bilibili-auth.json', 'r') as f:
    data = json.load(f)

# 关键cookie字段
for c in data.get('cookies', []):
    if c.get('name') in ['SESSDATA', 'bili_jct', 'DedeUserID']:
        print(f"{c.get('name')}: {c.get('value')[:30]}...")
```

必须包含这些字段：
- `SESSDATA`: 会话验证
- `bili_jct`: CSRF token
- `DedeUserID`: 用户ID

## 夸克网盘目录结构

建议的目录结构：

```
全部文件/
├── 番剧/
│   ├── 凡人修仙传/
│   │   ├── 175-重返天南23.mp4
│   │   └── 176-重返天南24.mp4
│   └── 其他番剧/
├── 电影/
│   ├── 哪吒之魔童闹海/
│   └── 功夫/
└── 歌曲/
    ├── 蔡健雅/
    └── 林俊杰/
```

## 下载记录追踪（防重复下载）

使用SQLite数据库记录已下载的视频，避免重复下载。

### 快速使用

```bash
# 初始化数据库
python scripts/download_tracker.py init

# 添加下载记录
python scripts/download_tracker.py add ep1231584 "重返天南24" \
  --series "凡人修仙传" --episode 176 --size "471.7M" \
  --quark "番剧/凡人修仙传/"

# 检查是否已下载
python scripts/download_tracker.py check ep1231584

# 列出所有记录
python scripts/download_tracker.py list

# 按番剧筛选
python scripts/download_tracker.py list --series "凡人修仙传"

# 标记已上传
python scripts/download_tracker.py uploaded ep1231584 --quark "番剧/凡人修仙传/"

# 统计信息
python scripts/download_tracker.py stats

# 删除记录
python scripts/download_tracker.py delete ep1231584

# 导出为JSON
python scripts/download_tracker.py export
```

### 数据库结构

| 字段 | 类型 | 说明 |
|------|------|------|
| episode_id | TEXT | 剧集ID (如 ep1231584) |
| series | TEXT | 番剧名称 |
| title | TEXT | 集标题 |
| episode_number | INT | 集数 |
| quality | TEXT | 画质 (1080P等) |
| file_size | TEXT | 文件大小 |
| file_path | TEXT | 本地文件路径 |
| quark_path | TEXT | 夸克网盘路径 |
| downloaded_at | TIMESTAMP | 下载时间 |
| uploaded_at | TIMESTAMP | 上传时间 |

### 在下载流程中使用

```bash
# 检查是否已下载
if python scripts/download_tracker.py check ep1231584 | grep -q "未下载"; then
  # 执行下载
  yt-dlp --cookies bilibili-cookies.txt ...
  
  # 记录下载
  python scripts/download_tracker.py add ep1231584 "重返天南24" \
    --series "凡人修仙传" --episode 176 --size "471.7M"
fi
```

## 相关文件

- `bilibili-auth.json`: B站登录状态（Playwright格式）
- `bilibili-cookies.txt`: yt-dlp可用的cookie（Netscape格式）
- `quark-auth.json`: 夸克网盘登录状态
- `scripts/download_tracker.py`: 下载记录追踪脚本
- `download_history.db`: SQLite数据库（自动生成）
