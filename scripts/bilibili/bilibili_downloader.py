#!/usr/bin/env python3
"""
B站下载器 - 支持大会员视频下载、Cookie检查、音视频合并
用法:
    python bilibili_downloader.py check-cookie [--auth-file PATH]
    python bilibili_downloader.py download <url> [--episodes 1-4] [--quality 1080]
    python bilibili_downloader.py merge <directory>
    python bilibili_downloader.py info <url>
"""

import argparse
import json
import os
import subprocess
import sys
import time
import glob
import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple

# 默认路径
DEFAULT_AUTH_FILE = "/mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced/bilibili-auth.json"
DEFAULT_COOKIE_FILE = "/home/administrator/bilibili-cookies.txt"
DEFAULT_DOWNLOAD_DIR = "/home/administrator/bilibili-download"
FFMPEG_PATH = "/mnt/d/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe"


def check_cookie(auth_file: str = DEFAULT_AUTH_FILE) -> Dict:
    """检查B站Cookie是否有效"""
    result = {
        "valid": False,
        "sessdata_found": False,
        "expired": False,
        "expires_str": "",
        "message": ""
    }
    
    if not os.path.exists(auth_file):
        result["message"] = f"❌ 认证文件不存在: {auth_file}"
        return result
    
    try:
        with open(auth_file, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        result["message"] = f"❌ 认证文件格式错误: {auth_file}"
        return result
    
    cookies = data.get('cookies', [])
    
    for c in cookies:
        if c.get('name') == 'SESSDATA':
            result["sessdata_found"] = True
            expires = c.get('expires', 0)
            result["expires_str"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expires)) if expires > 0 else '会话'
            
            if expires > 0 and expires < time.time():
                result["expired"] = True
                result["message"] = f"⚠️ Cookie已过期 (过期时间: {result['expires_str']})"
            else:
                result["valid"] = True
                result["message"] = f"✓ Cookie有效 (过期时间: {result['expires_str']})"
            break
    
    if not result["sessdata_found"]:
        result["message"] = "❌ 未找到SESSDATA，请重新登录"
    
    return result


def generate_cookie_file(auth_file: str = DEFAULT_AUTH_FILE, 
                         cookie_file: str = DEFAULT_COOKIE_FILE) -> Dict:
    """从auth.json生成netscape格式的cookie文件"""
    result = {"success": False, "count": 0, "message": ""}
    
    if not os.path.exists(auth_file):
        result["message"] = f"❌ 认证文件不存在: {auth_file}"
        return result
    
    try:
        with open(auth_file, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        result["message"] = f"❌ 认证文件格式错误"
        return result
    
    cookies = data.get('cookies', [])
    
    output = [
        '# Netscape HTTP Cookie File',
        '# https://curl.haxx.se/rfc/cookie_spec.html',
        '# This is a generated file! Do not edit.',
        ''
    ]
    
    for cookie in cookies:
        domain = cookie.get('domain', '').lstrip('.')
        if not domain:
            continue
        path = cookie.get('path', '/')
        secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
        name = cookie.get('name', '')
        value = cookie.get('value', '')
        expires = int(cookie.get('expires', 0))
        if expires < 0 or expires > 2147483647:
            expires = 2147483647
        output.append(f'.{domain}\tTRUE\t{path}\t{secure}\t{expires}\t{name}\t{value}')
    
    os.makedirs(os.path.dirname(cookie_file), exist_ok=True)
    with open(cookie_file, 'w') as f:
        f.write('\n'.join(output))
    
    result["success"] = True
    result["count"] = len(cookies)
    result["message"] = f"✓ Cookie文件已生成: {cookie_file} ({len(cookies)} 个cookie)"
    return result


def get_video_info(url: str, cookie_file: str = DEFAULT_COOKIE_FILE) -> Dict:
    """获取视频信息"""
    result = {"success": False, "info": {}, "message": ""}
    
    cmd = [
        'yt-dlp', '--cookies', cookie_file,
        '--dump-json', '--no-download',
        url
    ]
    
    # 禁用代理
    env = os.environ.copy()
    env['http_proxy'] = ''
    env['https_proxy'] = ''
    
    try:
        output = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)
        if output.returncode == 0:
            data = json.loads(output.stdout)
            result["success"] = True
            result["info"] = {
                "title": data.get('title', ''),
                "series": data.get('series', ''),
                "episode": data.get('episode', ''),
                "episode_number": data.get('episode_number', ''),
                "duration": data.get('duration', 0),
                "formats": []
            }
            
            # 获取可用格式
            formats_output = subprocess.run(
                ['yt-dlp', '--cookies', cookie_file, '-F', url],
                capture_output=True, text=True, env=env, timeout=30
            )
            if formats_output.returncode == 0:
                for line in formats_output.stdout.split('\n'):
                    if 'MiB' in line and ('mp4' in line or 'm4a' in line):
                        result["info"]["formats"].append(line.strip())
            
            result["message"] = f"✓ 获取信息成功: {result['info']['title']}"
        else:
            result["message"] = f"❌ 获取失败: {output.stderr[:200]}"
    except Exception as e:
        result["message"] = f"❌ 错误: {str(e)}"
    
    return result


def download_video(url: str, 
                   output_dir: str = DEFAULT_DOWNLOAD_DIR,
                   cookie_file: str = DEFAULT_COOKIE_FILE,
                   quality: str = "1080",
                   episode_range: Optional[str] = None) -> Dict:
    """下载B站视频"""
    result = {"success": False, "files": [], "message": ""}
    
    # 检查cookie
    cookie_check = check_cookie()
    if not cookie_check["valid"]:
        result["message"] = f"❌ Cookie无效: {cookie_check['message']}"
        return result
    
    # 生成cookie文件
    gen_result = generate_cookie_file()
    if not gen_result["success"]:
        result["message"] = gen_result["message"]
        return result
    
    # 确定格式选择
    if quality == "4K":
        format_selector = "30125+30280"  # 4K + 音频
    elif quality == "1080":
        format_selector = "30112+30280"  # 1080P + 音频
    else:
        format_selector = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 构建命令
    cmd = [
        'yt-dlp',
        '--cookies', cookie_file,
        '-f', format_selector,
        '-o', f'{output_dir}/%(series)s/%(episode_number)s-%(episode)s.%(ext)s',
        url
    ]
    
    # 添加集数限制
    if episode_range:
        if '-' in episode_range:
            start, end = episode_range.split('-')
            cmd.extend(['--playlist-start', start, '--playlist-end', end])
        else:
            cmd.extend(['--playlist-items', episode_range])
    
    # 禁用代理
    env = os.environ.copy()
    env['http_proxy'] = ''
    env['https_proxy'] = ''
    
    print(f"开始下载: {url}")
    print(f"格式: {format_selector}")
    print(f"输出目录: {output_dir}")
    
    try:
        process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, 
                                   stderr=subprocess.STDOUT, text=True)
        
        # 实时输出
        for line in process.stdout:
            print(line, end='')
            # 检测是否下载到预览版
            if 'MiB' in line:
                match = re.search(r'of\s+([\d.]+)MiB', line)
                if match:
                    size = float(match.group(1))
                    if size < 50:  # 预览版通常小于50MB
                        print(f"\n⚠️ 警告: 文件过小 ({size}MB)，可能是预览版！")
        
        process.wait()
        
        if process.returncode == 0:
            # 查找下载的文件
            files = glob.glob(f'{output_dir}/**/*.mp4', recursive=True)
            files.extend(glob.glob(f'{output_dir}/**/*.m4a', recursive=True))
            result["files"] = files
            result["success"] = True
            result["message"] = f"✓ 下载完成，共 {len(files)} 个文件"
        else:
            result["message"] = f"❌ 下载失败 (退出码: {process.returncode})"
    
    except Exception as e:
        result["message"] = f"❌ 下载错误: {str(e)}"
    
    return result


def merge_videos(directory: str, ffmpeg_path: str = FFMPEG_PATH) -> Dict:
    """合并视频和音频文件"""
    result = {"success": False, "merged": [], "message": ""}
    
    if not os.path.exists(ffmpeg_path):
        result["message"] = f"❌ ffmpeg不存在: {ffmpeg_path}"
        return result
    
    # 查找所有视频和音频文件
    video_files = sorted(glob.glob(f'{directory}/*.f30*.mp4'))
    audio_files = sorted(glob.glob(f'{directory}/*.f30280.m4a'))
    
    if not video_files:
        result["message"] = f"❌ 未找到视频文件: {directory}"
        return result
    
    print(f"找到 {len(video_files)} 个视频文件")
    print(f"找到 {len(audio_files)} 个音频文件")
    
    merged_count = 0
    
    for video in video_files:
        basename = os.path.basename(video).rsplit('.', 2)[0]
        
        # 查找对应的音频文件
        audio = None
        for a in audio_files:
            if basename in a or basename.replace('.f30112', '').replace('.f30125', '') in a:
                audio = a
                break
        
        if audio:
            output = os.path.join(directory, f"{basename}.mp4")
            
            # 转换路径为Windows格式
            win_video = video.replace('/mnt/d', 'D:').replace('/mnt/c', 'C:').replace('/', '\\')
            win_audio = audio.replace('/mnt/d', 'D:').replace('/mnt/c', 'C:').replace('/', '\\')
            win_output = output.replace('/mnt/d', 'D:').replace('/mnt/c', 'C:').replace('/', '\\')
            
            cmd = [
                ffmpeg_path,
                '-i', win_video,
                '-i', win_audio,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-y',
                win_output
            ]
            
            print(f"合并: {basename}")
            
            try:
                subprocess.run(cmd, capture_output=True, timeout=120)
                if os.path.exists(output):
                    # 删除原始文件
                    os.remove(video)
                    os.remove(audio)
                    result["merged"].append(output)
                    merged_count += 1
                    print(f"  ✓ 合并完成")
            except Exception as e:
                print(f"  ✗ 合并失败: {e}")
    
    result["success"] = merged_count > 0
    result["message"] = f"✓ 合并完成: {merged_count} 个文件"
    return result


def main():
    parser = argparse.ArgumentParser(description='B站视频下载器')
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # check-cookie 命令
    check_parser = subparsers.add_parser('check-cookie', help='检查Cookie是否有效')
    check_parser.add_argument('--auth-file', default=DEFAULT_AUTH_FILE, help='认证文件路径')
    
    # generate-cookie 命令
    gen_parser = subparsers.add_parser('generate-cookie', help='生成Cookie文件')
    gen_parser.add_argument('--auth-file', default=DEFAULT_AUTH_FILE, help='认证文件路径')
    gen_parser.add_argument('--cookie-file', default=DEFAULT_COOKIE_FILE, help='输出Cookie文件路径')
    
    # info 命令
    info_parser = subparsers.add_parser('info', help='获取视频信息')
    info_parser.add_argument('url', help='视频URL')
    info_parser.add_argument('--cookie-file', default=DEFAULT_COOKIE_FILE, help='Cookie文件路径')
    
    # download 命令
    dl_parser = subparsers.add_parser('download', help='下载视频')
    dl_parser.add_argument('url', help='视频URL')
    dl_parser.add_argument('--output-dir', default=DEFAULT_DOWNLOAD_DIR, help='输出目录')
    dl_parser.add_argument('--cookie-file', default=DEFAULT_COOKIE_FILE, help='Cookie文件路径')
    dl_parser.add_argument('--quality', default='1080', choices=['1080', '4K', 'auto'], help='画质')
    dl_parser.add_argument('--episodes', help='集数范围 (如: 1-4)')
    
    # merge 命令
    merge_parser = subparsers.add_parser('merge', help='合并视频音频')
    merge_parser.add_argument('directory', help='视频目录')
    merge_parser.add_argument('--ffmpeg', default=FFMPEG_PATH, help='ffmpeg路径')
    
    args = parser.parse_args()
    
    if args.command == 'check-cookie':
        result = check_cookie(args.auth_file)
        print(result["message"])
        sys.exit(0 if result["valid"] else 1)
    
    elif args.command == 'generate-cookie':
        result = generate_cookie_file(args.auth_file, args.cookie_file)
        print(result["message"])
        sys.exit(0 if result["success"] else 1)
    
    elif args.command == 'info':
        result = get_video_info(args.url, args.cookie_file)
        print(result["message"])
        if result["success"]:
            print(f"\n标题: {result['info']['title']}")
            print(f"番剧: {result['info']['series']}")
            print(f"集数: {result['info']['episode_number']} - {result['info']['episode']}")
            print(f"时长: {result['info']['duration']}秒")
            print(f"\n可用格式:")
            for fmt in result['info']['formats']:
                print(f"  {fmt}")
        sys.exit(0 if result["success"] else 1)
    
    elif args.command == 'download':
        result = download_video(args.url, args.output_dir, args.cookie_file, 
                               args.quality, args.episodes)
        print(result["message"])
        sys.exit(0 if result["success"] else 1)
    
    elif args.command == 'merge':
        result = merge_videos(args.directory, args.ffmpeg)
        print(result["message"])
        sys.exit(0 if result["success"] else 1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
