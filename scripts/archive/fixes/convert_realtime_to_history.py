#!/usr/bin/env python3
"""
将错误的Realtime任务转换为History任务

使用场景：
  - 首次运行监控爬虫时生成了大量Realtime任务
  - 这些任务实际上是历史评论，应该作为History任务慢慢处理

用法：
    python scripts/convert_realtime_to_history.py
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
    """将Realtime任务转换为History任务"""
    db = DatabaseManager()
    session = db.get_session()

    try:
        print("="*70)
        print("将Realtime任务转换为History任务")
        print("="*70)

        # 获取所有目标账号
        accounts = session.query(TargetAccount).all()

        total_converted = 0

        for acc in accounts:
            print(f"\n账号: {acc.account_name} ({acc.account_id})")

            # 查询今天创建的Realtime任务
            today = date.today()
            realtime_tasks = session.query(InteractionTask).filter(
                InteractionTask.target_account_id == acc.id,
                InteractionTask.task_type == 'realtime',
                InteractionTask.status == 'pending'  # 只转换未处理的
            ).all()

            print(f"  待处理的Realtime任务: {len(realtime_tasks)} 个")

            if realtime_tasks:
                # 询问用户是否转换
                response = input(f"\n  是否将这 {len(realtime_tasks)} 个任务转换为History类型？(y/n): ")

                if response.lower() == 'y':
                    for task in realtime_tasks:
                        task.task_type = 'history'
                        task.priority = 1  # 降低优先级

                    session.commit()
                    total_converted += len(realtime_tasks)
                    print(f"  ✓ 已转换 {len(realtime_tasks)} 个任务")
                else:
                    print(f"  跳过")

        print(f"\n{'='*70}")
        print(f"总计转换: {total_converted} 个任务")
        print(f"{'='*70}")

        if total_converted > 0:
            print("\n接下来的步骤:")
            print("  1. 运行 run_long_term_automation.py（处理这些History任务）")
            print("  2. 重新运行 run_monitor_crawler.py（检测真正的新增评论）")
            print("  3. 运行 run_realtime_automation.py（处理真正的新增评论）")

    except Exception as e:
        session.rollback()
        print(f"\n✗ 错误: {e}")
        return 1
    finally:
        session.close()

    return 0

if __name__ == '__main__':
    exit(main())
