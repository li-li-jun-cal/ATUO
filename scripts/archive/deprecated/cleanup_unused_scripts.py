#!/usr/bin/env python3
"""
清理无用的脚本文件

根据代码审查报告，安全删除已不再需要的脚本
"""

import os
import shutil
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 需要删除的文件
FILES_TO_DELETE = [
    'scripts/migrate_add_quota_columns.py',
    'scripts/fix_duplicate_stats.py',
    'scripts/clean_duplicate_tasks.py',
    'scripts/auto_clean_assigned.py',
    'scripts/diagnose_monitor.py',
    'scripts/migrate_new_to_history.py',
    'scripts/check_comment_tables.py',
    'scripts/check_video_id_match.py',
    'scripts/diagnose_dedup_logic.py',
]

# 需要归档的文件
FILES_TO_ARCHIVE = [
    'scripts/check_duplicate_tasks.py',
    'scripts/monitor_tasks.py',
]

def main():
    """清理无用脚本"""
    print("="*70)
    print("清理无用脚本")
    print("="*70)

    # 创建归档目录
    archive_dir = PROJECT_ROOT / 'scripts' / 'archive'
    archive_dir.mkdir(exist_ok=True)
    print(f"\n✓ 创建归档目录: {archive_dir}")

    # 归档文件
    print(f"\n归档文件:")
    for file_path in FILES_TO_ARCHIVE:
        src = PROJECT_ROOT / file_path
        if src.exists():
            dst = archive_dir / src.name
            shutil.move(str(src), str(dst))
            print(f"  ✓ 已归档: {file_path} -> scripts/archive/{src.name}")
        else:
            print(f"  ⊗ 文件不存在: {file_path}")

    # 删除文件
    print(f"\n删除文件:")
    for file_path in FILES_TO_DELETE:
        src = PROJECT_ROOT / file_path
        if src.exists():
            os.remove(src)
            print(f"  ✓ 已删除: {file_path}")
        else:
            print(f"  ⊗ 文件不存在: {file_path}")

    print(f"\n{'='*70}")
    print(f"清理完成！")
    print(f"  - 归档: {len([f for f in FILES_TO_ARCHIVE if (PROJECT_ROOT / f).exists()])} 个文件")
    print(f"  - 删除: {len([f for f in FILES_TO_DELETE if (PROJECT_ROOT / f).exists()])} 个文件")
    print(f"{'='*70}")

if __name__ == '__main__':
    main()
