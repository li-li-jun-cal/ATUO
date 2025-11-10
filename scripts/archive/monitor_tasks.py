"""
实时监控任务执行情况

显示：
1. completed 任务数量变化
2. 哪些设备完成了哪些用户
3. 是否有重复关注的情况
"""
import sys
from pathlib import Path
import time

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager
from src.database.models import InteractionTask
from sqlalchemy import func

def monitor():
    """监控任务执行"""
    db = DatabaseManager()

    print("\n" + "=" * 80)
    print("实时监控任务执行情况")
    print("=" * 80)
    print("\n按 Ctrl+C 停止监控\n")

    last_completed_count = 0

    try:
        while True:
            session = db.get_session()

            try:
                # 统计任务状态
                status_stats = session.query(
                    InteractionTask.status,
                    func.count(InteractionTask.id)
                ).group_by(InteractionTask.status).all()

                status_dict = {status: count for status, count in status_stats}
                completed_count = status_dict.get('completed', 0)

                # 只在数量变化时显示
                if completed_count != last_completed_count:
                    print(f"\n[{time.strftime('%H:%M:%S')}] 任务状态:")
                    for status, count in status_stats:
                        print(f"  {status:15s}: {count:5d}")

                    # 显示最新完成的任务
                    if completed_count > last_completed_count:
                        new_completed = session.query(InteractionTask)\
                            .filter_by(status='completed')\
                            .order_by(InteractionTask.completed_at.desc())\
                            .limit(completed_count - last_completed_count)\
                            .all()

                        print(f"\n  最新完成的任务:")
                        for task in reversed(new_completed):
                            print(f"    ✓ [{task.assigned_device}] {task.comment_user_name} ({task.comment_unique_id})")

                    # 检查重复关注
                    duplicates = session.query(
                        InteractionTask.comment_unique_id,
                        InteractionTask.comment_user_name,
                        func.group_concat(InteractionTask.assigned_device).label('devices')
                    ).filter(
                        InteractionTask.status == 'completed',
                        InteractionTask.comment_unique_id.isnot(None)
                    ).group_by(
                        InteractionTask.comment_unique_id,
                        InteractionTask.comment_user_name
                    ).having(
                        func.count(InteractionTask.assigned_device) > 1
                    ).all()

                    if duplicates:
                        print(f"\n  被多台设备关注的用户:")
                        for unique_id, user_name, devices in duplicates:
                            device_list = devices.split(',')
                            print(f"    📍 {user_name} ({unique_id})")
                            print(f"       设备: {', '.join(device_list)}")

                    # 按设备统计
                    device_stats = session.query(
                        InteractionTask.assigned_device,
                        func.count(func.distinct(InteractionTask.comment_unique_id)).label('users')
                    ).filter(
                        InteractionTask.status == 'completed',
                        InteractionTask.assigned_device.isnot(None)
                    ).group_by(
                        InteractionTask.assigned_device
                    ).all()

                    if device_stats:
                        print(f"\n  设备统计:")
                        for device, users in device_stats:
                            print(f"    {device}: 完成 {users} 个用户")

                    last_completed_count = completed_count
                    print("\n" + "=" * 80)

            finally:
                session.close()

            time.sleep(5)  # 每5秒检查一次

    except KeyboardInterrupt:
        print("\n\n停止监控")


if __name__ == "__main__":
    monitor()
