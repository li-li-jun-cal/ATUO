#!/usr/bin/env python3
"""
数据库重置脚本

⚠️ 警告：此脚本会删除所有数据！

功能：
1. 删除旧的数据库文件
2. 重新创建数据库（包含所有新字段）
3. 初始化表结构
"""

import sys
import os
from pathlib import Path

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def reset_database():
    """重置数据库"""
    print("=" * 70)
    print("⚠️  数据库重置工具")
    print("=" * 70)
    print()
    print("此操作将删除所有数据，包括：")
    print("  - 目标账号")
    print("  - 评论数据")
    print("  - 交互任务")
    print("  - 设备统计")
    print("  - 所有历史记录")
    print()

    # 确认操作
    confirm = input("是否确认重置数据库？(输入 'YES' 确认): ")
    if confirm != 'YES':
        print("❌ 操作已取消")
        return 1

    print()
    print("开始重置数据库...")
    print("-" * 70)

    # 数据库文件路径
    db_path = PROJECT_ROOT / 'data' / 'dy_interaction.db'

    # 删除旧数据库
    if db_path.exists():
        print(f"✓ 找到旧数据库: {db_path}")
        try:
            os.remove(db_path)
            print("✓ 旧数据库已删除")
        except Exception as e:
            print(f"❌ 删除失败: {e}")
            return 1
    else:
        print("ℹ️  未发现旧数据库文件")

    # 确保 data 目录存在
    data_dir = PROJECT_ROOT / 'data'
    data_dir.mkdir(exist_ok=True)
    print(f"✓ 数据目录: {data_dir}")

    # 重新创建数据库
    print()
    print("正在创建新数据库...")
    print("-" * 70)

    try:
        from src.database.manager import DatabaseManager
        from src.database.models import (
            Base, TargetAccount, Comment, InteractionTask,
            InteractionLog, BatchProgress, Device,
            DeviceAssignment, DeviceDailyStats, MonitorLog
        )

        # 初始化数据库
        db = DatabaseManager()
        db.init_db()

        print()
        print("✓ 数据库创建成功！")
        print()
        print("已创建的表：")
        print("  - target_accounts      (目标账号)")
        print("  - comments             (评论数据)")
        print("  - interaction_tasks    (交互任务)")
        print("  - interaction_logs     (交互日志)")
        print("  - batch_progress       (批次进度)")
        print("  - devices              (设备信息)")
        print("  - device_assignment    (设备分配)")
        print("  - device_daily_stats   (设备每日统计 - 包含配额字段)")
        print("  - monitor_logs         (监控日志)")
        print()

        # 显示新增字段
        print("✓ device_daily_stats 表包含以下配额字段：")
        print("  - follow_count   (关注数量)")
        print("  - like_count     (点赞数量)")
        print("  - collect_count  (收藏数量)")
        print()

        print("=" * 70)
        print("✓ 数据库重置完成！")
        print("=" * 70)

        return 0

    except Exception as e:
        print(f"❌ 创建数据库失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = reset_database()
    sys.exit(exit_code)
