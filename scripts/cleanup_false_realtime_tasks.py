#!/usr/bin/env python3
"""
清理错误的Realtime任务 - 将今天生成的Realtime任务删除，重新建立正确的基线

使用场景：
  - 首次运行监控爬虫时，Comment表为空，导致所有评论都被当作"新增"
  - 需要清理这些错误的Realtime任务

用法：
    python scripts/cleanup_false_realtime_tasks.py          # 分析模式（只查看，不删除）
    python scripts/cleanup_false_realtime_tasks.py --delete # 删除模式
"""

import sys
from pathlib import Path

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager
from src.database.models import InteractionTask, TargetAccount, Comment
from datetime import datetime, date

def main():
    """清理错误的Realtime任务"""
    import argparse
    parser = argparse.ArgumentParser(description='清理错误的Realtime任务')
    parser.add_argument('--delete', action='store_true', help='删除模式（不加此参数只分析，不删除）')
    args = parser.parse_args()

    db = DatabaseManager()
    session = db.get_session()

    try:
        print("="*70)
        if args.delete:
            print("清理错误的Realtime任务 [删除模式]")
        else:
            print("分析Realtime任务 [只查看，不删除]")
        print("="*70)

        # 获取所有目标账号
        accounts = session.query(TargetAccount).all()

        total_deleted = 0
        total_in_history = 0
        total_not_in_history = 0

        for acc in accounts:
            print(f"\n账号: {acc.account_name} ({acc.account_id})")

            # 查询今天创建的Realtime任务
            today = date.today()
            realtime_tasks = session.query(InteractionTask).filter(
                InteractionTask.target_account_id == acc.id,
                InteractionTask.task_type == 'realtime',
                InteractionTask.created_at >= datetime(today.year, today.month, today.day)
            ).all()

            print(f"  今天创建的Realtime任务: {len(realtime_tasks)} 个")

            if realtime_tasks:
                # 检查这些任务对应的用户是否在Comment表中
                in_history = 0
                not_in_history = 0

                for task in realtime_tasks:
                    existing = session.query(Comment).filter_by(
                        target_account_id=acc.id,
                        comment_user_id=task.comment_user_id
                    ).first()

                    if existing:
                        in_history += 1
                    else:
                        not_in_history += 1

                print(f"    - 在历史基线中: {in_history} 个（应该删除）")
                print(f"    - 不在历史基线中: {not_in_history} 个（真正的新增）")

                total_in_history += in_history
                total_not_in_history += not_in_history

                if args.delete:
                    # 删除所有今天创建的Realtime任务
                    for task in realtime_tasks:
                        session.delete(task)
                    session.commit()
                    total_deleted += len(realtime_tasks)
                    print(f"  ✓ 已删除 {len(realtime_tasks)} 个任务")

        print(f"\n{'='*70}")
        print(f"统计汇总:")
        print(f"  在历史基线中: {total_in_history} 个（假新增）")
        print(f"  不在历史基线中: {total_not_in_history} 个（真新增）")
        if args.delete:
            print(f"  总计删除: {total_deleted} 个任务")
        else:
            print(f"  预计删除: {total_in_history + total_not_in_history} 个任务")
        print(f"{'='*70}")

        if args.delete and total_deleted > 0:
            print("\n✓ 清理完成！")
            print("\n接下来的步骤:")
            print("  1. 确认所有账号都已运行过 run_history_crawler.py（建立历史基线）")
            print("  2. 重新运行 run_monitor_crawler.py（检测真正的新增评论）")
            print("  3. 运行 run_realtime_automation.py（处理新增评论任务）")
        elif not args.delete:
            print("\n💡 这是分析模式，没有删除任何数据")
            print("   如需删除，请运行: python scripts/cleanup_false_realtime_tasks.py --delete")

    except Exception as e:
        session.rollback()
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        session.close()

    return 0

if __name__ == '__main__':
    exit(main())
