#!/usr/bin/env python3
"""
B站到夸克完整工作流 - 一键下载上传
用法:
    python bilibili_to_quark.py download <bangumi_url> [--episodes 1-4]
    python bilibili_to_quark.py upload --source-dir <dir> --target-dir "番剧/xxx"
    python bilibili_to_quark.py full <bangumi_url> --target-dir "番剧/xxx" [--episodes 1-4]
"""

import argparse
import os
import sys
import subprocess
import glob
import time

# 脚本目录
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BILIBILI_SCRIPT = os.path.join(SCRIPTS_DIR, "bilibili", "bilibili_downloader.py")
QUARK_SCRIPT = os.path.join(SCRIPTS_DIR, "quark", "quark_uploader.py")


def run_command(cmd: list, check: bool = True) -> tuple:
    """运行命令并返回结果"""
    print(f"\n执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0, result.returncode


def check_prerequisites() -> bool:
    """检查前置条件"""
    print("检查前置条件...")
    
    # 检查脚本
    if not os.path.exists(BILIBILI_SCRIPT):
        print(f"❌ B站下载脚本不存在: {BILIBILI_SCRIPT}")
        return False
    
    if not os.path.exists(QUARK_SCRIPT):
        print(f"❌ 夸克上传脚本不存在: {QUARK_SCRIPT}")
        return False
    
    # 检查认证文件
    auth_file = "/mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced/bilibili-auth.json"
    if not os.path.exists(auth_file):
        print(f"❌ B站认证文件不存在，请先登录")
        return False
    
    quark_auth = "/mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced/quark-auth.json"
    if not os.path.exists(quark_auth):
        print(f"❌ 夸克认证文件不存在，请先登录")
        return False
    
    # 检查Cookie
    success, _ = run_command(['python3', BILIBILI_SCRIPT, 'check-cookie'], check=False)
    if not success:
        print("❌ B站 Cookie 无效或已过期，请重新登录")
        return False
    
    print("✓ 前置条件检查通过")
    return True


def download_bangumi(url: str, episodes: str = None, quality: str = "1080") -> dict:
    """下载番剧"""
    result = {"success": False, "files": [], "message": ""}
    
    cmd = ['python3', BILIBILI_SCRIPT, 'download', url, '--quality', quality]
    if episodes:
        cmd.extend(['--episodes', episodes])
    
    success, _ = run_command(cmd, check=False)
    
    if success:
        # 查找下载的文件
        download_dir = os.path.expanduser("~/bilibili-download")
        files = glob.glob(f'{download_dir}/**/*.mp4', recursive=True)
        result["files"] = [f for f in files if 'f30' not in f]  # 排除未合并的
        result["success"] = True
        result["message"] = f"✓ 下载完成: {len(result['files'])} 个文件"
    else:
        result["message"] = "❌ 下载失败"
    
    return result


def merge_videos(directory: str) -> dict:
    """合并视频"""
    result = {"success": False, "message": ""}
    
    cmd = ['python3', BILIBILI_SCRIPT, 'merge', directory]
    success, _ = run_command(cmd, check=False)
    
    result["success"] = success
    result["message"] = "✓ 合并完成" if success else "❌ 合并失败"
    return result


def upload_to_quark(files: list, target_dir: str, wait: int = 20) -> dict:
    """上传到夸克"""
    result = {"success": False, "message": ""}
    
    cmd = ['python3', QUARK_SCRIPT, 'upload'] + files + ['--target-dir', target_dir, '--wait', str(wait)]
    success, _ = run_command(cmd, check=False)
    
    result["success"] = success
    result["message"] = "✓ 上传完成" if success else "❌ 上传失败"
    return result


def full_workflow(url: str, target_dir: str, episodes: str = None, quality: str = "1080", wait: int = 20):
    """完整工作流: 下载 -> 合并 -> 上传"""
    print("=" * 60)
    print("B站到夸克完整工作流")
    print("=" * 60)
    
    # 检查前置条件
    if not check_prerequisites():
        return False
    
    # 步骤1: 下载
    print("\n[步骤 1/3] 下载番剧")
    print("-" * 40)
    dl_result = download_bangumi(url, episodes, quality)
    if not dl_result["success"]:
        print(dl_result["message"])
        return False
    print(dl_result["message"])
    
    # 查找下载目录
    download_dir = os.path.expanduser("~/bilibili-download")
    bangumi_dirs = [d for d in glob.glob(f'{download_dir}/*') if os.path.isdir(d)]
    if not bangumi_dirs:
        print("❌ 未找到下载目录")
        return False
    
    latest_dir = max(bangumi_dirs, key=os.path.getmtime)
    print(f"下载目录: {latest_dir}")
    
    # 步骤2: 合并（如果需要）
    print("\n[步骤 2/3] 检查合并")
    print("-" * 40)
    
    video_parts = glob.glob(f'{latest_dir}/*.f30*.mp4')
    if video_parts:
        print(f"发现 {len(video_parts)} 个未合并文件，开始合并...")
        merge_result = merge_videos(latest_dir)
        print(merge_result["message"])
    else:
        print("✓ 文件已合并，跳过")
    
    # 步骤3: 上传
    print("\n[步骤 3/3] 上传到夸克")
    print("-" * 40)
    
    final_files = [f for f in glob.glob(f'{latest_dir}/*.mp4') if 'f30' not in f]
    if not final_files:
        print("❌ 未找到最终文件")
        return False
    
    print(f"准备上传 {len(final_files)} 个文件到 {target_dir}")
    upload_result = upload_to_quark(final_files, target_dir, wait)
    print(upload_result["message"])
    
    # 完成
    print("\n" + "=" * 60)
    if upload_result["success"]:
        print("✅ 工作流完成！")
        print(f"夸克位置: {target_dir}")
        return True
    else:
        print("❌ 工作流失败")
        return False


def main():
    parser = argparse.ArgumentParser(description='B站到夸克完整工作流')
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # download 命令
    dl_parser = subparsers.add_parser('download', help='下载番剧')
    dl_parser.add_argument('url', help='番剧URL')
    dl_parser.add_argument('--episodes', help='集数范围 (如: 1-4)')
    dl_parser.add_argument('--quality', default='1080', choices=['1080', '4K', 'auto'])
    
    # upload 命令
    ul_parser = subparsers.add_parser('upload', help='上传到夸克')
    ul_parser.add_argument('--source-dir', required=True, help='源目录')
    ul_parser.add_argument('--target-dir', required=True, help='目标目录')
    ul_parser.add_argument('--wait', type=int, default=20, help='等待时间')
    
    # full 命令
    full_parser = subparsers.add_parser('full', help='完整工作流')
    full_parser.add_argument('url', help='番剧URL')
    full_parser.add_argument('--target-dir', required=True, help='夸克目标目录')
    full_parser.add_argument('--episodes', help='集数范围')
    full_parser.add_argument('--quality', default='1080', choices=['1080', '4K', 'auto'])
    full_parser.add_argument('--wait', type=int, default=20, help='上传等待时间')
    
    # check 命令
    subparsers.add_parser('check', help='检查前置条件')
    
    args = parser.parse_args()
    
    if args.command == 'download':
        result = download_bangumi(args.url, args.episodes, args.quality)
        print(result["message"])
        sys.exit(0 if result["success"] else 1)
    
    elif args.command == 'upload':
        files = glob.glob(f'{args.source_dir}/*.mp4')
        if not files:
            print(f"❌ 未找到文件: {args.source_dir}")
            sys.exit(1)
        result = upload_to_quark(files, args.target_dir, args.wait)
        print(result["message"])
        sys.exit(0 if result["success"] else 1)
    
    elif args.command == 'full':
        success = full_workflow(args.url, args.target_dir, args.episodes, args.quality, args.wait)
        sys.exit(0 if success else 1)
    
    elif args.command == 'check':
        success = check_prerequisites()
        sys.exit(0 if success else 1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
