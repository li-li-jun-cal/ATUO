"""
快速检查重复任务

显示数据库中是否存在重复的互动任务
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager
from src.database.models import InteractionTask
from sqlalchemy import func

def check_duplicate_tasks():
    """检查重复任务"""
    db = DatabaseManager()
    session = db.get_session()

    try:
        print("\n" + "=" * 80)
        print("任务重复检查")
        print("=" * 80)

        # 1. 按状态统计任务
        print("\n[1] 任务状态统计:")
        status_stats = session.query(
            InteractionTask.status,
            func.count(InteractionTask.id)
        ).group_by(InteractionTask.status).all()

        for status, count in status_stats:
            print(f"  {status:15s}: {count:5d}")

        # 2. 查找有多个任务的用户
        print("\n[2] 查找重复用户:")

        # 按 comment_unique_id 分组
        unique_id_duplicates = session.query(
            InteractionTask.comment_unique_id,
            InteractionTask.comment_user_name,
            func.count(InteractionTask.id).label('count')
        ).filter(
            InteractionTask.comment_unique_id.isnot(None),
            InteractionTask.status.in_(['pending', 'in_progress', 'completed'])
        ).group_by(
            InteractionTask.comment_unique_id,
            InteractionTask.comment_user_name
        ).having(
            func.count(InteractionTask.id) > 1
        ).order_by(
            func.count(InteractionTask.id).desc()
        ).limit(20).all()

        if unique_id_duplicates:
            print(f"\n  发现 {len(unique_id_duplicates)} 个用户有多个任务:")
            print(f"\n  {'抖音号':<20s} {'用户名':<20s} {'任务数':<10s}")
            print("  " + "-" * 50)
            for unique_id, user_name, count in unique_id_duplicates:
                print(f"  {unique_id:<20s} {user_name:<20s} {count:<10d}")
        else:
            print("  ✓ 没有发现重复任务")

        # 3. 详细显示前3个重复用户的任务
        if unique_id_duplicates:
            print("\n[3] 重复任务详情（前3个用户）:")
            for idx, (unique_id, user_name, count) in enumerate(unique_id_duplicates[:3], 1):
                print(f"\n  [{idx}] 用户: {user_name} ({unique_id})")

                tasks = session.query(InteractionTask)\
                    .filter_by(comment_unique_id=unique_id)\
                    .order_by(InteractionTask.created_at.asc())\
                    .all()

                for task in tasks:
                    print(f"      任务 #{task.id:4d} | 状态: {task.status:12s} | "
                          f"创建: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')} | "
                          f"完成: {task.completed_at.strftime('%Y-%m-%d %H:%M:%S') if task.completed_at else 'N/A'}")

        # 4. 总结
        print("\n" + "=" * 80)
        print("总结")
        print("=" * 80)

        total_tasks = sum(count for _, count in status_stats)
        print(f"\n  总任务数: {total_tasks}")

        if unique_id_duplicates:
            total_duplicates = sum(count - 1 for _, _, count in unique_id_duplicates)
            print(f"  重复用户数: {len(unique_id_duplicates)}")
            print(f"  重复任务数: {total_duplicates}")
            print(f"\n  ⚠️  建议运行清理脚本: python scripts/clean_duplicate_tasks.py")
        else:
            print(f"  ✓ 没有发现重复任务")

        print("\n" + "=" * 80)

    finally:
        session.close()


if __name__ == "__main__":
    check_duplicate_tasks()
