#!/usr/bin/env python3
"""
查看自动化执行统计数据

显示每个设备的关注、点赞、收藏等详细统计
"""

import sys
from pathlib import Path
from datetime import datetime, date, timedelta

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager
from src.database.models import DeviceDailyStats, InteractionTask
from sqlalchemy import func

def print_separator(char="=", length=80):
    """打印分隔线"""
    print(char * length)

def print_section_header(title):
    """打印章节标题"""
    print_separator()
    print(f"{title:^80}")
    print_separator()

def show_today_stats():
    """显示今日统计"""
    db = DatabaseManager()
    session = db.get_session()

    print_section_header("📊 今日执行统计")

    today = date.today()

    # 查询今日所有设备的统计
    stats = session.query(DeviceDailyStats).filter_by(date=today).all()

    if not stats:
        print("\n⚠️  今天还没有执行数据")
        session.close()
        return

    print(f"\n日期: {today}")
    print("\n" + "-" * 70)
    print(f"{'设备ID':<20} {'关注':<10} {'点赞':<10} {'收藏':<10} {'完成任务':<15}")
    print("-" * 70)

    total_follow = 0
    total_like = 0
    total_collect = 0
    total_tasks = 0

    for stat in stats:
        print(f"{stat.device_id:<20} {stat.follow_count:<10} {stat.like_count:<10} "
              f"{stat.collect_count:<10} {stat.completed_tasks:<15}")
        total_follow += stat.follow_count
        total_like += stat.like_count
        total_collect += stat.collect_count
        total_tasks += stat.completed_tasks

    print("-" * 70)
    print(f"{'总计':<20} {total_follow:<10} {total_like:<10} "
          f"{total_collect:<10} {total_tasks:<15}")

    session.close()

def show_week_stats():
    """显示本周统计"""
    db = DatabaseManager()
    session = db.get_session()

    print_section_header("📈 本周执行统计（最近7天）")

    # 最近7天
    today = date.today()
    week_ago = today - timedelta(days=6)

    stats = session.query(
        DeviceDailyStats.device_id,
        func.sum(DeviceDailyStats.follow_count).label('total_follow'),
        func.sum(DeviceDailyStats.like_count).label('total_like'),
        func.sum(DeviceDailyStats.collect_count).label('total_collect'),
        func.sum(DeviceDailyStats.completed_tasks).label('total_tasks')
    ).filter(
        DeviceDailyStats.date >= week_ago,
        DeviceDailyStats.date <= today
    ).group_by(
        DeviceDailyStats.device_id
    ).all()

    if not stats:
        print("\n⚠️  本周还没有执行数据")
        session.close()
        return

    print(f"\n日期范围: {week_ago} ~ {today}")
    print("\n" + "-" * 70)
    print(f"{'设备ID':<20} {'关注':<10} {'点赞':<10} {'收藏':<10} {'完成任务':<15}")
    print("-" * 70)

    total_follow = 0
    total_like = 0
    total_collect = 0
    total_tasks = 0

    for stat in stats:
        print(f"{stat.device_id:<20} {stat.total_follow or 0:<10} {stat.total_like or 0:<10} "
              f"{stat.total_collect or 0:<10} {stat.total_tasks or 0:<15}")
        total_follow += stat.total_follow or 0
        total_like += stat.total_like or 0
        total_collect += stat.total_collect or 0
        total_tasks += stat.total_tasks or 0

    print("-" * 70)
    print(f"{'总计':<20} {total_follow:<10} {total_like:<10} "
          f"{total_collect:<10} {total_tasks:<15}")

    session.close()

def show_task_stats():
    """显示任务统计"""
    db = DatabaseManager()
    session = db.get_session()

    print_section_header("📋 任务执行统计")

    # 按类型和状态统计
    print("\n按类型和状态分组:")
    print("-" * 60)
    print(f"{'任务类型':<15} {'状态':<15} {'数量':<10}")
    print("-" * 60)

    task_stats = session.query(
        InteractionTask.task_type,
        InteractionTask.status,
        func.count(InteractionTask.id).label('count')
    ).group_by(
        InteractionTask.task_type,
        InteractionTask.status
    ).all()

    for stat in task_stats:
        print(f"{stat.task_type:<15} {stat.status:<15} {stat.count:<10}")

    # 今日完成任务统计
    print("\n" + "="*60)
    print("\n今日完成任务:")
    print("-" * 60)

    today = datetime.now().date()
    today_start = datetime(today.year, today.month, today.day)
    today_end = today_start + timedelta(days=1)

    today_completed = session.query(
        InteractionTask.task_type,
        func.count(InteractionTask.id).label('count')
    ).filter(
        InteractionTask.status == 'completed',
        InteractionTask.completed_at >= today_start,
        InteractionTask.completed_at < today_end
    ).group_by(
        InteractionTask.task_type
    ).all()

    if today_completed:
        print(f"{'任务类型':<15} {'完成数量':<10}")
        print("-" * 60)
        total = 0
        for stat in today_completed:
            print(f"{stat.task_type:<15} {stat.count:<10}")
            total += stat.count
        print("-" * 60)
        print(f"{'总计':<15} {total:<10}")
    else:
        print("今天还没有完成任务")

    session.close()

def show_daily_trend(days=7):
    """显示每日趋势"""
    db = DatabaseManager()
    session = db.get_session()

    print_section_header(f"📉 每日执行趋势（最近{days}天）")

    today = date.today()
    start_date = today - timedelta(days=days-1)

    # 按日期统计
    daily_stats = session.query(
        DeviceDailyStats.date,
        func.sum(DeviceDailyStats.follow_count).label('total_follow'),
        func.sum(DeviceDailyStats.like_count).label('total_like'),
        func.sum(DeviceDailyStats.collect_count).label('total_collect'),
        func.sum(DeviceDailyStats.completed_tasks).label('total_tasks')
    ).filter(
        DeviceDailyStats.date >= start_date,
        DeviceDailyStats.date <= today
    ).group_by(
        DeviceDailyStats.date
    ).order_by(
        DeviceDailyStats.date
    ).all()

    if not daily_stats:
        print("\n⚠️  没有统计数据")
        session.close()
        return

    print("\n" + "-" * 70)
    print(f"{'日期':<15} {'关注':<10} {'点赞':<10} {'收藏':<10} {'完成任务':<15}")
    print("-" * 70)

    for stat in daily_stats:
        print(f"{str(stat.date):<15} {stat.total_follow or 0:<10} {stat.total_like or 0:<10} "
              f"{stat.total_collect or 0:<10} {stat.total_tasks or 0:<15}")

    session.close()

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='查看自动化执行统计')
    parser.add_argument('--today', action='store_true', help='只显示今日统计')
    parser.add_argument('--week', action='store_true', help='只显示本周统计')
    parser.add_argument('--tasks', action='store_true', help='只显示任务统计')
    parser.add_argument('--trend', action='store_true', help='只显示每日趋势')
    parser.add_argument('--days', type=int, default=7, help='趋势统计天数（默认7天）')
    args = parser.parse_args()

    print()
    print("=" * 80)
    print(f"{'DY-Interaction 执行统计':^80}")
    print(f"{'查询时间: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'):^80}")
    print("=" * 80)
    print()

    # 如果没有指定任何参数，显示所有统计
    show_all = not any([args.today, args.week, args.tasks, args.trend])

    if args.today or show_all:
        show_today_stats()
        print()

    if args.week or show_all:
        show_week_stats()
        print()

    if args.tasks or show_all:
        show_task_stats()
        print()

    if args.trend or show_all:
        show_daily_trend(args.days)
        print()

    print()

if __name__ == '__main__':
    main()
