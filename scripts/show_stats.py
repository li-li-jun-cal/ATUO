#!/usr/bin/env python3
"""
设备统计查看工具 - 清晰展示每台设备的历史数据
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager
from src.database.models import DeviceDailyStats

def show_device_stats(days=7):
    """显示设备统计数据

    Args:
        days: 显示最近N天的数据
    """
    print("=" * 100)
    print("📊 设备操作统计报告")
    print("=" * 100)

    db = DatabaseManager()
    session = db.get_session()

    try:
        # 获取所有统计数据，按设备和日期排序
        stats = session.query(DeviceDailyStats).order_by(
            DeviceDailyStats.device_id,
            DeviceDailyStats.date
        ).all()

        if not stats:
            print("\n暂无统计数据")
            return

        # 按设备分组
        devices = {}
        for stat in stats:
            if stat.device_id not in devices:
                devices[stat.device_id] = []
            devices[stat.device_id].append(stat)

        # 显示每台设备的统计
        for device_id in sorted(devices.keys()):
            device_stats = devices[device_id]

            print(f"\n{'='*100}")
            print(f"设备: {device_id}")
            print(f"{'='*100}")
            print(f"{'日期':12s} {'关注':>8s} {'点赞':>8s} {'收藏':>8s} {'完成任务':>10s} {'失败任务':>10s} {'关注率':>8s}")
            print(f"{'-'*100}")

            total_follow = 0
            total_like = 0
            total_collect = 0
            total_completed = 0
            total_failed = 0

            for stat in device_stats:
                date_str = stat.date.strftime('%Y-%m-%d')
                follow_count = stat.follow_count or 0
                like_count = stat.like_count or 0
                collect_count = stat.collect_count or 0
                completed = stat.completed_tasks or 0
                failed = stat.failed_tasks or 0

                # 计算关注率（相对于限制50的百分比）
                follow_rate = f"{follow_count}/50" if follow_count <= 50 else f"{follow_count}/50 ⚠️"

                print(f"{date_str:12s} {follow_count:8d} {like_count:8d} {collect_count:8d} {completed:10d} {failed:10d} {follow_rate:>8s}")

                total_follow += follow_count
                total_like += like_count
                total_collect += collect_count
                total_completed += completed
                total_failed += failed

            print(f"{'-'*100}")
            print(f"{'总计':12s} {total_follow:8d} {total_like:8d} {total_collect:8d} {total_completed:10d} {total_failed:10d}")

        # 全局汇总
        print(f"\n{'='*100}")
        print(f"📈 全局汇总")
        print(f"{'='*100}")

        all_stats = session.query(DeviceDailyStats).all()

        grand_total_follow = sum(s.follow_count or 0 for s in all_stats)
        grand_total_like = sum(s.like_count or 0 for s in all_stats)
        grand_total_collect = sum(s.collect_count or 0 for s in all_stats)
        grand_total_completed = sum(s.completed_tasks or 0 for s in all_stats)
        grand_total_failed = sum(s.failed_tasks or 0 for s in all_stats)

        print(f"  总设备数: {len(devices)}")
        print(f"  总记录数: {len(all_stats)}")
        print(f"  总关注数: {grand_total_follow}")
        print(f"  总点赞数: {grand_total_like}")
        print(f"  总收藏数: {grand_total_collect}")
        print(f"  完成任务: {grand_total_completed}")
        print(f"  失败任务: {grand_total_failed}")
        print(f"{'='*100}")

        # 今日统计
        print(f"\n{'='*100}")
        print(f"📅 今日统计 ({datetime.now().strftime('%Y-%m-%d')})")
        print(f"{'='*100}")

        today_start = datetime.combine(datetime.now().date(), datetime.min.time())
        today_end = datetime.combine(datetime.now().date(), datetime.max.time())

        today_stats = session.query(DeviceDailyStats).filter(
            DeviceDailyStats.date >= today_start,
            DeviceDailyStats.date <= today_end
        ).all()

        if today_stats:
            print(f"{'设备ID':15s} {'关注':>8s} {'点赞':>8s} {'收藏':>8s} {'完成':>8s} {'失败':>8s} {'状态':>10s}")
            print(f"{'-'*100}")

            today_follow = 0
            today_like = 0
            today_collect = 0

            for stat in today_stats:
                follow = stat.follow_count or 0
                like = stat.like_count or 0
                collect = stat.collect_count or 0
                completed = stat.completed_tasks or 0
                failed = stat.failed_tasks or 0

                status = "✓ 正常" if follow <= 50 else "⚠️ 超限"

                print(f"{stat.device_id:15s} {follow:8d} {like:8d} {collect:8d} {completed:8d} {failed:8d} {status:>10s}")

                today_follow += follow
                today_like += like
                today_collect += collect

            print(f"{'-'*100}")
            print(f"{'今日总计':15s} {today_follow:8d} {today_like:8d} {today_collect:8d}")
        else:
            print("  今日暂无数据")

        print(f"{'='*100}")

    finally:
        session.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='查看设备统计数据')
    parser.add_argument('--days', type=int, default=7, help='显示最近N天的数据（默认7天）')
    args = parser.parse_args()

    show_device_stats(args.days)
