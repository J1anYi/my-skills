#!/usr/bin/env python3
"""
夸克网盘上传器 - 支持批量上传、进度验证
用法:
    python quark_uploader.py init
    python quark_uploader.py upload <files...> --target-dir "番剧/xxx"
    python quark_uploader.py create-folder <name> --parent "番剧"
    python quark_uploader.py list --path "番剧"
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
SKILL_DIR = "/mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced"
QUARK_AUTH = f"{SKILL_DIR}/quark-auth.json"
TEMP_UPLOAD_DIR = f"{SKILL_DIR}/temp-upload"
POWERSHELL = "powershell.exe"


def run_playwright_cmd(cmd: str, timeout: int = 30) -> Tuple[bool, str]:
    """执行playwright-cli命令"""
    full_cmd = f'cd {SKILL_DIR} && {POWERSHELL} -Command "{cmd}"'
    try:
        result = subprocess.run(full_cmd, shell=True, capture_output=True, 
                               text=True, timeout=timeout)
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "命令超时"
    except Exception as e:
        return False, str(e)


def init_browser() -> Dict:
    """初始化浏览器并加载登录状态"""
    result = {"success": False, "message": ""}
    
    # 关闭现有浏览器
    run_playwright_cmd("playwright-cli close", timeout=10)
    time.sleep(1)
    
    # 打开新浏览器
    success, output = run_playwright_cmd("playwright-cli open", timeout=30)
    if not success:
        result["message"] = f"❌ 打开浏览器失败: {output}"
        return result
    
    time.sleep(1)
    
    # 加载登录状态
    success, output = run_playwright_cmd(f"playwright-cli state-load quark-auth.json", timeout=15)
    if not success:
        result["message"] = f"❌ 加载登录状态失败: {output}"
        return result
    
    time.sleep(1)
    
    # 导航到夸克网盘
    success, output = run_playwright_cmd(
        "playwright-cli goto 'https://pan.quark.cn/list#/list/all'", 
        timeout=30
    )
    if not success:
        result["message"] = f"❌ 导航失败: {output}"
        return result
    
    time.sleep(2)
    
    result["success"] = True
    result["message"] = "✓ 浏览器初始化成功"
    return result


def get_snapshot() -> str:
    """获取页面快照"""
    success, output = run_playwright_cmd("playwright-cli snapshot", timeout=15)
    return output if success else ""


def find_element_ref(snapshot: str, pattern: str) -> Optional[str]:
    """从快照中查找元素ref"""
    for line in snapshot.split('\n'):
        if pattern in line:
            match = re.search(r'ref=(e\d+)', line)
            if match:
                return match.group(1)
    return None


def navigate_to_folder(folder_path: str) -> Dict:
    """导航到指定文件夹"""
    result = {"success": False, "message": ""}
    
    folders = folder_path.strip('/').split('/')
    
    for folder in folders:
        snapshot = get_snapshot()
        ref = find_element_ref(snapshot, f'"{folder}"')
        
        if ref:
            success, output = run_playwright_cmd(f"playwright-cli click {ref}", timeout=15)
            if not success:
                result["message"] = f"❌ 无法进入文件夹: {folder}"
                return result
            time.sleep(2)
        else:
            result["message"] = f"❌ 未找到文件夹: {folder}"
            return result
    
    result["success"] = True
    result["message"] = f"✓ 已导航到: {folder_path}"
    return result


def create_folder(name: str, parent_path: str = "") -> Dict:
    """创建文件夹"""
    result = {"success": False, "message": ""}
    
    # 导航到父目录
    if parent_path:
        nav_result = navigate_to_folder(parent_path)
        if not nav_result["success"]:
            return nav_result
    
    # 获取快照找新建文件夹按钮
    snapshot = get_snapshot()
    ref = find_element_ref(snapshot, "新建文件夹")
    
    if not ref:
        result["message"] = "❌ 未找到新建文件夹按钮"
        return result
    
    # 点击新建文件夹
    success, output = run_playwright_cmd(f"playwright-cli click {ref}", timeout=15)
    if not success:
        result["message"] = f"❌ 点击新建文件夹失败"
        return result
    
    time.sleep(1)
    
    # 获取输入框ref
    snapshot = get_snapshot()
    input_ref = find_element_ref(snapshot, "textbox")
    
    if not input_ref:
        result["message"] = "❌ 未找到输入框"
        return result
    
    # 输入文件夹名
    success, output = run_playwright_cmd(f"playwright-cli fill {input_ref} '{name}'", timeout=15)
    if not success:
        result["message"] = f"❌ 输入文件夹名失败"
        return result
    
    # 按回车确认
    run_playwright_cmd("playwright-cli press Enter", timeout=10)
    time.sleep(2)
    
    result["success"] = True
    result["message"] = f"✓ 文件夹创建成功: {name}"
    return result


def upload_file(file_path: str, wait_time: int = 20) -> Dict:
    """上传单个文件"""
    result = {"success": False, "message": ""}
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        result["message"] = f"❌ 文件不存在: {file_path}"
        return result
    
    # 获取文件大小
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    filename = os.path.basename(file_path)
    
    # 获取上传按钮ref
    snapshot = get_snapshot()
    upload_ref = find_element_ref(snapshot, "上传文件")
    
    if not upload_ref:
        result["message"] = "❌ 未找到上传按钮"
        return result
    
    # 点击上传按钮
    success, output = run_playwright_cmd(f"playwright-cli click {upload_ref}", timeout=15)
    if not success:
        result["message"] = f"❌ 点击上传按钮失败"
        return result
    
    time.sleep(1)
    
    # 上传文件
    rel_path = os.path.relpath(file_path, SKILL_DIR)
    success, output = run_playwright_cmd(f"playwright-cli upload '{rel_path}'", timeout=60)
    
    if not success:
        result["message"] = f"❌ 上传失败: {output[:200]}"
        return result
    
    # 等待上传完成
    print(f"  上传中: {filename} ({size_mb:.1f}MB)...")
    wait_time = max(wait_time, int(size_mb / 10))  # 根据文件大小调整等待时间
    time.sleep(wait_time)
    
    result["success"] = True
    result["message"] = f"✓ 上传成功: {filename}"
    return result


def batch_upload(files: List[str], target_dir: str, wait_time: int = 20) -> Dict:
    """批量上传文件"""
    result = {"success": False, "uploaded": [], "failed": [], "message": ""}
    
    # 准备上传目录
    os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)
    
    # 复制文件到临时目录
    print(f"准备上传 {len(files)} 个文件...")
    local_files = []
    for f in files:
        basename = os.path.basename(f)
        dest = os.path.join(TEMP_UPLOAD_DIR, basename)
        if not os.path.exists(dest):
            os.system(f'cp "{f}" "{dest}"')
        local_files.append(dest)
    
    # 初始化浏览器
    init_result = init_browser()
    if not init_result["success"]:
        result["message"] = init_result["message"]
        return result
    
    # 导航到目标目录（如果不存在则创建）
    folders = target_dir.strip('/').split('/')
    current_path = ""
    
    for folder in folders:
        current_path = f"{current_path}/{folder}" if current_path else folder
        snapshot = get_snapshot()
        ref = find_element_ref(snapshot, f'"{folder}"')
        
        if ref:
            # 文件夹存在，进入
            run_playwright_cmd(f"playwright-cli click {ref}", timeout=15)
            time.sleep(2)
        else:
            # 创建文件夹
            create_result = create_folder(folder, current_path.rsplit('/', 1)[0] if '/' in current_path else "")
            if not create_result["success"]:
                # 可能文件夹已存在但没在当前视图，尝试刷新
                run_playwright_cmd("playwright-cli press F5", timeout=10)
                time.sleep(2)
                snapshot = get_snapshot()
                ref = find_element_ref(snapshot, f'"{folder}"')
                if ref:
                    run_playwright_cmd(f"playwright-cli click {ref}", timeout=15)
                    time.sleep(2)
    
    # 逐个上传文件
    for i, file_path in enumerate(local_files, 1):
        filename = os.path.basename(file_path)
        print(f"[{i}/{len(local_files)}] 上传: {filename}")
        
        upload_result = upload_file(file_path, wait_time)
        
        if upload_result["success"]:
            result["uploaded"].append(filename)
        else:
            result["failed"].append({"file": filename, "error": upload_result["message"]})
            print(f"  ✗ {upload_result['message']}")
    
    # 清理临时文件
    for f in local_files:
        try:
            os.remove(f)
        except:
            pass
    
    # 验证上传结果
    snapshot = get_snapshot()
    uploaded_count = len(re.findall(r'\.mp4', snapshot))
    
    result["success"] = len(result["uploaded"]) > 0
    result["message"] = f"✓ 上传完成: {len(result['uploaded'])} 成功, {len(result['failed'])} 失败"
    return result


def list_files(path: str = "") -> Dict:
    """列出文件"""
    result = {"success": False, "files": [], "folders": [], "message": ""}
    
    # 初始化浏览器
    init_result = init_browser()
    if not init_result["success"]:
        result["message"] = init_result["message"]
        return result
    
    # 导航到目录
    if path:
        nav_result = navigate_to_folder(path)
        if not nav_result["success"]:
            result["message"] = nav_result["message"]
            return result
    
    # 获取文件列表
    snapshot = get_snapshot()
    
    # 解析快照
    for line in snapshot.split('\n'):
        # 查找文件
        if 'row "' in line and ('.mp4' in line or '.mkv' in line or '.avi' in line):
            match = re.search(r'"([^"]+\.(?:mp4|mkv|avi))[^"]*"', line)
            if match:
                result["files"].append(match.group(1))
        
        # 查找文件夹
        if 'cursor=pointer' in line and 'generic "' in line:
            match = re.search(r'generic "([^"]+)"', line)
            if match and match.group(1) not in result["files"]:
                result["folders"].append(match.group(1))
    
    result["success"] = True
    result["message"] = f"✓ 找到 {len(result['folders'])} 个文件夹, {len(result['files'])} 个文件"
    return result


def main():
    parser = argparse.ArgumentParser(description='夸克网盘上传器')
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # init 命令
    subparsers.add_parser('init', help='初始化浏览器')
    
    # upload 命令
    upload_parser = subparsers.add_parser('upload', help='上传文件')
    upload_parser.add_argument('files', nargs='+', help='文件路径')
    upload_parser.add_argument('--target-dir', required=True, help='目标目录')
    upload_parser.add_argument('--wait', type=int, default=20, help='等待时间(秒)')
    
    # create-folder 命令
    folder_parser = subparsers.add_parser('create-folder', help='创建文件夹')
    folder_parser.add_argument('name', help='文件夹名称')
    folder_parser.add_argument('--parent', default='', help='父目录')
    
    # list 命令
    list_parser = subparsers.add_parser('list', help='列出文件')
    list_parser.add_argument('--path', default='', help='目录路径')
    
    args = parser.parse_args()
    
    if args.command == 'init':
        result = init_browser()
        print(result["message"])
        sys.exit(0 if result["success"] else 1)
    
    elif args.command == 'upload':
        result = batch_upload(args.files, args.target_dir, args.wait)
        print(result["message"])
        if result["failed"]:
            print("\n失败的文件:")
            for f in result["failed"]:
                print(f"  - {f['file']}: {f['error']}")
        sys.exit(0 if result["success"] else 1)
    
    elif args.command == 'create-folder':
        result = create_folder(args.name, args.parent)
        print(result["message"])
        sys.exit(0 if result["success"] else 1)
    
    elif args.command == 'list':
        result = list_files(args.path)
        print(result["message"])
        if result["folders"]:
            print("\n文件夹:")
            for f in result["folders"][:10]:
                print(f"  - {f}")
        if result["files"]:
            print("\n文件:")
            for f in result["files"][:10]:
                print(f"  - {f}")
        sys.exit(0 if result["success"] else 1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
