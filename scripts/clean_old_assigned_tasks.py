"""
清理旧的 assigned 任务

问题：数据库中有大量 assigned 状态的任务（旧逻辑遗留）
解决：将这些任务重置为 skipped，从干净状态开始
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager
from src.database.models import InteractionTask
from datetime import datetime

def clean_old_assigned_tasks():
    """清理旧的 assigned 任务"""
    print("\n" + "=" * 80)
    print("清理旧的 assigned 任务")
    print("=" * 80)

    db = DatabaseManager()
    session = db.get_session()

    try:
        # 统计当前状态
        print("\n[1] 当前任务状态:")
        from sqlalchemy import func
        status_stats = session.query(
            InteractionTask.status,
            func.count(InteractionTask.id)
        ).group_by(InteractionTask.status).all()

        for status, count in status_stats:
            print(f"  {status:15s}: {count:5d}")

        # 获取所有 assigned 任务
        assigned_tasks = session.query(InteractionTask)\
            .filter_by(status='assigned')\
            .all()

        if not assigned_tasks:
            print("\n✓ 没有 assigned 任务需要清理")
            return

        print(f"\n[2] 发现 {len(assigned_tasks)} 个 assigned 任务（旧逻辑遗留）")
        print("\n清理策略:")
        print("  1. 标记为 'skipped' - 保留记录，跳过执行（推荐）")
        print("  2. 重置为 'pending' - 重新执行")
        print("  3. 直接删除")
        print("  4. 取消")

        choice = input("\n请选择 [1/2/3/4]: ").strip()

        if choice == '1':
            # 标记为 skipped
            for task in assigned_tasks:
                task.status = 'skipped'
                task.error_msg = '旧逻辑遗留任务，已跳过'
                task.completed_at = datetime.now()

            session.commit()
            print(f"\n✓ 已标记 {len(assigned_tasks)} 个任务为 'skipped'")

        elif choice == '2':
            # 重置为 pending
            for task in assigned_tasks:
                task.status = 'pending'
                task.assigned_device = None

            session.commit()
            print(f"\n✓ 已重置 {len(assigned_tasks)} 个任务为 'pending'")
            print("  ⚠️  注意：这些任务会被重新执行，可能导致重复关注")

        elif choice == '3':
            # 删除
            confirm = input(f"\n⚠️  确认删除 {len(assigned_tasks)} 个任务？[y/N]: ").strip().lower()
            if confirm == 'y':
                for task in assigned_tasks:
                    session.delete(task)
                session.commit()
                print(f"\n✓ 已删除 {len(assigned_tasks)} 个任务")
            else:
                print("\n取消删除")
                return

        else:
            print("\n取消操作")
            return

        # 显示清理后的状态
        print("\n[3] 清理后的任务状态:")
        status_stats = session.query(
            InteractionTask.status,
            func.count(InteractionTask.id)
        ).group_by(InteractionTask.status).all()

        for status, count in status_stats:
            print(f"  {status:15s}: {count:5d}")

        print("\n" + "=" * 80)
        print("✓ 清理完成")
        print("=" * 80)
        print("\n现在可以重新运行自动化系统，系统将从干净的状态开始")
        print("新的去重逻辑将正常工作：")
        print("  - 设备完成任务后会标记为 'completed'")
        print("  - 调度器会自动排除已完成的用户")
        print("  - 每个用户最多被 3 台设备关注（可配置）")

    except Exception as e:
        session.rollback()
        print(f"\n✗ 清理失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        session.close()


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("清理旧的 assigned 任务")
    print("=" * 80)
    print("\n说明:")
    print("  数据库中有大量 assigned 状态的任务（1097个）")
    print("  这些是旧逻辑遗留的，需要清理才能让新逻辑正常工作")
    print("\n  新逻辑依赖 'completed' 状态来判断设备是否关注过用户")
    print("  如果不清理，调度器会认为所有设备都没有关注过任何用户")
    print("  导致重复分配任务")
    print("\n按 Enter 继续，Ctrl+C 取消...")
    input()

    clean_old_assigned_tasks()
