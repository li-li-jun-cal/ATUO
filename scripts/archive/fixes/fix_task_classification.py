#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复任务分类错误

问题：
  - 14584个"实时任务"被错误地标记为 realtime
  - 这些任务实际上是来自 generate_tasks_from_comments.py 的历史评论
  - 应该根据 comment_time 重新分类为 history_recent 或 history_old

正确的分类标准：
  - realtime: 来自 NewComment 表的新评论（监控爬虫发现）
  - history_recent: comment_time >= 90天前的评论
  - history_old: comment_time < 90天前的评论

用法：
    python scripts/fix_task_classification.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager
from src.database.models import InteractionTask


def main():
    """修复任务分类"""
    db = DatabaseManager()

    with db.get_session() as session:
        print("="*70)
        print("🔧 修复任务分类错误")
        print("="*70)
        print()

        # 定义时间分界线
        three_months_ago = datetime.now() - timedelta(days=90)

        # 获取所有被错误标记为 realtime 的任务
        # 这些任务的 comment_time 都在最近，说明它们来自任务生成脚本
        realtime_tasks = session.query(InteractionTask).filter(
            InteractionTask.task_type == 'realtime'
        ).all()

        print(f"发现 {len(realtime_tasks)} 个被标记为 realtime 的任务")
        print()

        # 按正确的标准重新分类
        reclassified_count = 0
        to_recent = 0
        to_old = 0

        print("【重新分类】")
        for idx, task in enumerate(realtime_tasks, 1):
            if idx % 1000 == 0:
                print(f"  进度: {idx}/{len(realtime_tasks)}")

            # 根据 comment_time 重新分类
            if task.comment_time and task.comment_time >= three_months_ago:
                # comment_time >= 90天前 -> history_recent
                new_type = 'history_recent'
                to_recent += 1
            elif task.comment_time and task.comment_time < three_months_ago:
                # comment_time < 90天前 -> history_old
                new_type = 'history_old'
                to_old += 1
            else:
                # 无 comment_time，默认 history_recent
                new_type = 'history_recent'
                to_recent += 1

            # 更新任务类型
            if task.task_type != new_type:
                task.task_type = new_type
                reclassified_count += 1

        # 提交更改
        if reclassified_count > 0:
            session.commit()
            print(f"\n✓ 已重新分类 {reclassified_count} 个任务")
            print(f"  - 分类为 history_recent: {to_recent}")
            print(f"  - 分类为 history_old: {to_old}")
        else:
            print(f"\n✓ 任务分类正确，无需修改")

        print()

        # 验证修复结果
        print("【验证修复结果】")
        realtime_count = session.query(InteractionTask).filter(
            InteractionTask.task_type == 'realtime'
        ).count()

        recent_count = session.query(InteractionTask).filter(
            InteractionTask.task_type == 'history_recent'
        ).count()

        old_count = session.query(InteractionTask).filter(
            InteractionTask.task_type == 'history_old'
        ).count()

        print(f"修复后的任务分布:")
        print(f"  - realtime: {realtime_count} 个")
        print(f"  - history_recent: {recent_count} 个")
        print(f"  - history_old: {old_count} 个")
        print()

        print("="*70)
        if reclassified_count > 0:
            print("✓ 任务分类修复完成！")
            print()
            print("接下来的步骤:")
            print("  1. 查看菜单统计，确认任务分布正确")
            print("  2. 运行自动化处理这些历史任务")
        else:
            print("✓ 任务分类无需修改")
        print("="*70)


if __name__ == '__main__':
    main()
