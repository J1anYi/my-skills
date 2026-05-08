#!/usr/bin/env python3
"""
B站下载记录追踪器

功能：
- 记录已下载的视频信息
- 防止重复下载
- 支持查询、删除、统计

使用方法：
  python download_tracker.py init                    # 初始化数据库
  python download_tracker.py add <episode_id> <title> <size>  # 添加记录
  python download_tracker.py check <episode_id>      # 检查是否已下载
  python download_tracker.py list [--series <名称>]  # 列出记录
  python download_tracker.py delete <episode_id>     # 删除记录
  python download_tracker.py stats                   # 统计信息
"""

import sqlite3
import json
import argparse
from datetime import datetime
from pathlib import Path

# 数据库路径（放在skill目录下）
DB_PATH = Path(__file__).parent.parent / "download_history.db"


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            episode_id TEXT UNIQUE NOT NULL,
            series TEXT,
            title TEXT NOT NULL,
            episode_number INTEGER,
            quality TEXT,
            file_size TEXT,
            file_path TEXT,
            quark_path TEXT,
            downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            uploaded_at TIMESTAMP,
            notes TEXT
        )
    ''')
    
    # 创建索引加速查询
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_episode_id ON downloads(episode_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_series ON downloads(series)')
    
    conn.commit()
    conn.close()
    print(f"✓ 数据库已初始化: {DB_PATH}")


def add_record(episode_id: str, title: str, size: str = None, 
               series: str = None, episode_number: int = None,
               quality: str = "1080P", file_path: str = None,
               quark_path: str = None, notes: str = None):
    """添加下载记录"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO downloads 
            (episode_id, series, title, episode_number, quality, file_size, file_path, quark_path, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (episode_id, series, title, episode_number, quality, size, file_path, quark_path, notes))
        
        conn.commit()
        print(f"✓ 已记录: {title} ({episode_id})")
        return True
    except sqlite3.IntegrityError:
        print(f"⚠ 已存在: {episode_id}")
        return False
    finally:
        conn.close()


def check_exists(episode_id: str) -> bool:
    """检查是否已下载"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM downloads WHERE episode_id = ?', (episode_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        print(f"✓ 已下载: {row['title']} (下载时间: {row['downloaded_at']})")
        return True
    else:
        print(f"✗ 未下载: {episode_id}")
        return False


def list_records(series: str = None, limit: int = 50):
    """列出下载记录"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if series:
        cursor.execute('''
            SELECT * FROM downloads 
            WHERE series LIKE ? 
            ORDER BY downloaded_at DESC 
            LIMIT ?
        ''', (f'%{series}%', limit))
    else:
        cursor.execute('SELECT * FROM downloads ORDER BY downloaded_at DESC LIMIT ?', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("无记录")
        return
    
    print(f"\n下载记录 (共{len(rows)}条):")
    print("-" * 80)
    for row in rows:
        ep_info = f"第{row['episode_number']}集" if row['episode_number'] else ""
        print(f"  [{row['episode_id']}] {row['series']} {ep_info} - {row['title']}")
        print(f"      大小: {row['file_size'] or '未知'} | 画质: {row['quality']} | 时间: {row['downloaded_at']}")
        if row['quark_path']:
            print(f"      夸克路径: {row['quark_path']}")


def delete_record(episode_id: str):
    """删除记录"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM downloads WHERE episode_id = ?', (episode_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    if deleted:
        print(f"✓ 已删除: {episode_id}")
    else:
        print(f"✗ 未找到: {episode_id}")


def mark_uploaded(episode_id: str, quark_path: str = None):
    """标记已上传"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE downloads 
        SET uploaded_at = CURRENT_TIMESTAMP, quark_path = ?
        WHERE episode_id = ?
    ''', (quark_path, episode_id))
    
    conn.commit()
    conn.close()
    print(f"✓ 已标记上传: {episode_id}")


def get_stats():
    """获取统计信息"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 总记录数
    cursor.execute('SELECT COUNT(*) as total FROM downloads')
    total = cursor.fetchone()['total']
    
    # 按番剧分组
    cursor.execute('''
        SELECT series, COUNT(*) as count 
        FROM downloads 
        WHERE series IS NOT NULL 
        GROUP BY series 
        ORDER BY count DESC
    ''')
    by_series = cursor.fetchall()
    
    # 已上传数量
    cursor.execute('SELECT COUNT(*) as uploaded FROM downloads WHERE uploaded_at IS NOT NULL')
    uploaded = cursor.fetchone()['uploaded']
    
    conn.close()
    
    print("\n📊 下载统计:")
    print("-" * 40)
    print(f"  总记录数: {total}")
    print(f"  已上传: {uploaded}")
    print(f"  未上传: {total - uploaded}")
    print("\n按番剧分类:")
    for row in by_series:
        print(f"  - {row['series']}: {row['count']}集")


def export_json(output_path: str = None):
    """导出为JSON"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM downloads ORDER BY downloaded_at DESC')
    rows = cursor.fetchall()
    conn.close()
    
    data = [dict(row) for row in rows]
    
    if output_path is None:
        output_path = Path(__file__).parent.parent / "download_history.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"✓ 已导出: {output_path} ({len(data)}条记录)")


def main():
    parser = argparse.ArgumentParser(description='B站下载记录追踪器')
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # init
    subparsers.add_parser('init', help='初始化数据库')
    
    # add
    add_parser = subparsers.add_parser('add', help='添加下载记录')
    add_parser.add_argument('episode_id', help='剧集ID (如: ep1231584)')
    add_parser.add_argument('title', help='标题')
    add_parser.add_argument('--size', help='文件大小')
    add_parser.add_argument('--series', help='番剧名称')
    add_parser.add_argument('--episode', type=int, help='集数')
    add_parser.add_argument('--quality', default='1080P', help='画质')
    add_parser.add_argument('--path', help='本地文件路径')
    add_parser.add_argument('--quark', help='夸克网盘路径')
    
    # check
    check_parser = subparsers.add_parser('check', help='检查是否已下载')
    check_parser.add_argument('episode_id', help='剧集ID')
    
    # list
    list_parser = subparsers.add_parser('list', help='列出下载记录')
    list_parser.add_argument('--series', help='按番剧筛选')
    list_parser.add_argument('--limit', type=int, default=50, help='限制数量')
    
    # delete
    delete_parser = subparsers.add_parser('delete', help='删除记录')
    delete_parser.add_argument('episode_id', help='剧集ID')
    
    # uploaded
    upload_parser = subparsers.add_parser('uploaded', help='标记已上传')
    upload_parser.add_argument('episode_id', help='剧集ID')
    upload_parser.add_argument('--quark', help='夸克网盘路径')
    
    # stats
    subparsers.add_parser('stats', help='统计信息')
    
    # export
    export_parser = subparsers.add_parser('export', help='导出为JSON')
    export_parser.add_argument('--output', help='输出文件路径')
    
    args = parser.parse_args()
    
    if args.command == 'init':
        init_db()
    elif args.command == 'add':
        add_record(
            args.episode_id, args.title, args.size,
            args.series, args.episode, args.quality,
            args.path, args.quark
        )
    elif args.command == 'check':
        check_exists(args.episode_id)
    elif args.command == 'list':
        list_records(args.series, args.limit)
    elif args.command == 'delete':
        delete_record(args.episode_id)
    elif args.command == 'uploaded':
        mark_uploaded(args.episode_id, args.quark)
    elif args.command == 'stats':
        get_stats()
    elif args.command == 'export':
        export_json(args.output)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
