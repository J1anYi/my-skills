# B站下载到夸克上传 - 自动化脚本

## 文件结构

```
~/.hermes/
├── scripts/
│   ├── bilibili/
│   │   └── bilibili_downloader.py    # B站下载器
│   ├── quark/
│   │   └── quark_uploader.py         # 夸克上传器
│   └── bilibili_to_quark.py          # 完整工作流
├── skills/
│   └── automation/
│       └── bilibili-download-to-quark/SKILL.md
└── skills_backup_20260508/            # 备份目录
    ├── bilibili-download/
    ├── bilibili-download-to-quark/
    └── quark-file-organization/
```

## 快速使用

### 1. 检查状态

```bash
python3 ~/.hermes/scripts/bilibili/bilibili_downloader.py check-cookie
```

### 2. 一键下载上传

```bash
python3 ~/.hermes/scripts/bilibili_to_quark.py full "https://www.bilibili.com/bangumi/play/ss229649" \
  --target-dir "番剧/放开那个女巫" \
  --episodes 1-4
```

### 3. 分步操作

```bash
# 下载
python3 ~/.hermes/scripts/bilibili/bilibili_downloader.py download "URL" --episodes 1-4

# 合并
python3 ~/.hermes/scripts/bilibili/bilibili_downloader.py merge ~/bilibili-download/xxx

# 上传
python3 ~/.hermes/scripts/quark/quark_uploader.py upload *.mp4 --target-dir "番剧/xxx"
```

## 脚本详解

### bilibili_downloader.py

**命令**：
- `check-cookie` - 检查Cookie是否有效
- `generate-cookie` - 生成netscape格式cookie文件
- `info <url>` - 获取视频信息
- `download <url>` - 下载视频
- `merge <directory>` - 合并视频音频

**参数**：
- `--auth-file` - 认证文件路径
- `--cookie-file` - Cookie文件路径
- `--quality` - 画质 (1080/4K/auto)
- `--episodes` - 集数范围 (如: 1-4)

### quark_uploader.py

**命令**：
- `init` - 初始化浏览器
- `upload <files...>` - 上传文件
- `create-folder <name>` - 创建文件夹
- `list` - 列出文件

**参数**：
- `--target-dir` - 目标目录
- `--parent` - 父目录
- `--wait` - 等待时间

### bilibili_to_quark.py

**命令**：
- `check` - 检查前置条件
- `download <url>` - 下载
- `upload --source-dir <dir> --target-dir <dir>` - 上传
- `full <url> --target-dir <dir>` - 完整工作流

## 回滚

如果脚本有问题，可以使用备份的原版skill：

```bash
# 查看备份
ls ~/.hermes/skills_backup_20260508/

# 恢复原版
cp -r ~/.hermes/skills_backup_20260508/bilibili-download-to-quark ~/.hermes/skills/automation/
```

## 更新日志

**2026-05-08**:
- 新增 Python 脚本自动化
- 支持命令行调用
- 整合完整工作流
- 备份原版 skills 到 skills_backup_20260508/

## 注意事项

1. **Cookie过期**：Cookie有效期约7天，过期需要重新登录
2. **下载目录**：建议将 `~/bilibili-download` symlink 到 D 盘
3. **上传等待**：大文件上传后需要等待足够时间（默认20秒）
4. **代理问题**：下载时自动禁用代理
