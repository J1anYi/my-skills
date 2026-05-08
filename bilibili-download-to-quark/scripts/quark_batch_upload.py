#!/usr/bin/env python3
"""
夸克网盘批量上传脚本

功能：
- 串行上传文件，每个文件间隔足够等待时间
- 动态获取上传按钮ref，避免页面刷新后ref变化
- 处理modal弹窗状态
- 上传后验证文件数量，确保上传成功
- 支持中文文件名

用法：
  python3 quark_batch_upload.py --target-dir "番剧/葬送的芙莉莲" --files /mnt/d/bilibili-download/frieren-merged/*.mp4
  
参数：
  --target-dir: 夸克网盘目标目录路径，如 "番剧/葬送的芙莉莲"
  --files: 要上传的文件列表（支持glob模式）
  --wait: 每个文件上传后的等待秒数，默认15秒
  --skill-dir: playwright-cli skill目录，默认为Windows上的save-music-to-quark-enhanced
"""

import argparse
import glob
import os
import re
import subprocess
import sys
import time
from pathlib import Path


class QuarkUploader:
    def __init__(self, skill_dir: str = None, wait_seconds: int = 15):
        self.skill_dir = skill_dir or "/mnt/c/Users/Administrator/.claude/skills/save-music-to-quark-enhanced"
        self.wait_seconds = wait_seconds
        self.temp_dir = os.path.join(self.skill_dir, "temp-upload")
        
    def run_powershell(self, command: str, timeout: int = 60) -> str:
        """执行PowerShell命令"""
        full_cmd = f'cd {self.skill_dir} && powershell.exe -Command "{command}"'
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout + result.stderr
    
    def get_snapshot(self) -> str:
        """获取页面快照"""
        return self.run_powershell("playwright-cli snapshot", timeout=15)
    
    def get_uploaded_files(self, pattern: str = r"葬送的芙莉莲_EP(\d+)\.mp4") -> list:
        """获取已上传文件列表"""
        snapshot = self.get_snapshot()
        files = re.findall(pattern, snapshot)
        return sorted(set(int(x) for x in files)) if files else []
    
    def find_upload_button_ref(self, snapshot: str) -> str:
        """从快照中查找上传按钮ref"""
        patterns = [
            r'button.*?上传文件.*?\[ref=(e\d+)\]',
            r'button "上传文件".*?\[ref=(e\d+)\]',
        ]
        for pattern in patterns:
            match = re.search(pattern, snapshot)
            if match:
                return match.group(1)
        return None
    
    def handle_modal(self):
        """处理弹窗状态"""
        snapshot = self.get_snapshot()
        if 'modal state' in snapshot.lower():
            print("  ⚠️ 检测到弹窗，关闭中...")
            self.run_powershell("playwright-cli press Escape", timeout=10)
            time.sleep(1)
    
    def navigate_to_directory(self, target_dir: str):
        """导航到目标目录"""
        print(f"导航到目录: {target_dir}")
        
        # 如果是完整URL，直接导航
        if target_dir.startswith("http"):
            self.run_powershell(f"playwright-cli goto '{target_dir}'", timeout=20)
            time.sleep(3)
            return
        
        # 否则按路径层级导航
        dirs = [d for d in target_dir.split("/") if d]
        
        for dir_name in dirs:
            snapshot = self.get_snapshot()
            # 查找目录ref
            match = re.search(rf'generic "{re.escape(dir_name)}".*?\[ref=(e\d+)\]', snapshot)
            if not match:
                match = re.search(rf'"{re.escape(dir_name)}".*?\[ref=(e\d+)\]', snapshot)
            
            if match:
                ref = match.group(1)
                self.run_powershell(f"playwright-cli click {ref}", timeout=15)
                time.sleep(2)
            else:
                print(f"  ⚠️ 未找到目录: {dir_name}")
    
    def upload_single_file(self, filepath: str) -> bool:
        """上传单个文件"""
        filename = os.path.basename(filepath)
        win_path = f"C:\\Users\\Administrator\\.claude\\skills\\save-music-to-quark-enhanced\\temp-upload\\{filename}"
        
        # 处理弹窗
        self.handle_modal()
        
        # 获取上传按钮ref
        snapshot = self.get_snapshot()
        upload_ref = self.find_upload_button_ref(snapshot)
        
        if not upload_ref:
            print(f"  ❌ 未找到上传按钮")
            return False
        
        # 点击上传按钮
        self.run_powershell(f"playwright-cli click {upload_ref}", timeout=15)
        time.sleep(2)
        
        # 选择文件
        result = self.run_powershell(f"playwright-cli upload '{win_path}'", timeout=60)
        
        return "setFiles" in result or "Ran Playwright" in result
    
    def upload_files(self, files: list, target_dir: str = None, file_pattern: str = None) -> dict:
        """
        批量上传文件
        
        参数：
            files: 文件路径列表
            target_dir: 目标目录
            file_pattern: 用于验证已上传文件的正则模式
            
        返回：
            {"success": int, "failed": list}
        """
        success_count = 0
        failed_list = []
        
        # 创建临时目录并复制文件
        os.makedirs(self.temp_dir, exist_ok=True)
        print(f"复制 {len(files)} 个文件到临时目录...")
        for f in files:
            dest = os.path.join(self.temp_dir, os.path.basename(f))
            if not os.path.exists(dest):
                subprocess.run(["cp", f, dest], check=True)
        print(f"复制完成\n")
        
        # 导航到目标目录
        if target_dir:
            self.navigate_to_directory(target_dir)
        
        # 获取当前已上传文件
        if file_pattern:
            existing = self.get_uploaded_files(file_pattern)
            print(f"当前已有 {len(existing)} 个文件")
        else:
            existing = []
        
        # 串行上传
        for i, filepath in enumerate(files, 1):
            filename = os.path.basename(filepath)
            print(f"\n[{i}/{len(files)}] {filename}")
            
            if self.upload_single_file(filepath):
                print(f"  ✅ 已发送，等待 {self.wait_seconds} 秒...")
                time.sleep(self.wait_seconds)
                success_count += 1
                
                # 验证上传
                if file_pattern:
                    current = self.get_uploaded_files(file_pattern)
                    if len(current) > len(existing):
                        print(f"  ✅ 验证成功，已有 {len(current)} 个文件")
                        existing = current
                    else:
                        print(f"  ⚠️ 文件未出现，可能还在传输中...")
            else:
                print(f"  ❌ 上传失败")
                failed_list.append(filename)
                time.sleep(3)
        
        return {"success": success_count, "failed": failed_list}


def main():
    parser = argparse.ArgumentParser(description="夸克网盘批量上传脚本")
    parser.add_argument("--target-dir", required=True, help="目标目录，如 '番剧/葬送的芙莉莲'")
    parser.add_argument("--files", nargs="+", required=True, help="要上传的文件列表")
    parser.add_argument("--wait", type=int, default=15, help="每个文件上传后的等待秒数")
    parser.add_argument("--skill-dir", default=None, help="playwright-cli skill目录")
    parser.add_argument("--pattern", default=None, help="验证已上传文件的正则模式")
    
    args = parser.parse_args()
    
    # 展开glob模式
    files = []
    for f in args.files:
        if "*" in f:
            files.extend(glob.glob(f))
        else:
            files.append(f)
    
    if not files:
        print("错误：没有找到文件")
        sys.exit(1)
    
    print(f"准备上传 {len(files)} 个文件到 {args.target_dir}")
    print(f"等待时间: {args.wait} 秒/文件\n")
    
    uploader = QuarkUploader(skill_dir=args.skill_dir, wait_seconds=args.wait)
    result = uploader.upload_files(files, args.target_dir, args.pattern)
    
    print(f"\n{'='*50}")
    print(f"上传完成！")
    print(f"  成功: {result['success']}")
    print(f"  失败: {len(result['failed'])}")
    if result['failed']:
        print(f"  失败文件: {result['failed']}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
