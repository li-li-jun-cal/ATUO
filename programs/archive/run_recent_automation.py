#!/usr/bin/env python3
"""
近期评论自动化脚本 - 专门处理近3个月的视频评论

功能:
    - 只处理 task_type='history_recent' 的任务（近3个月视频评论）
    - 高优先级处理（priority='high'）
    - 适合快速清理近期评论，获得最大化转化效果

说明:
    这个脚本专注于处理近3个月的评论，因为这些用户更活跃，转化率更高
    可以配合 run_long_term_automation.py 一起使用：
      - run_recent_automation.py: 处理近期评论（高优先级）
      - run_long_term_automation.py: 处理所有评论（混合优先级）
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
import time

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/recent_automation.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

from src.database.manager import DatabaseManager
from src.database.models import InteractionTask
from sqlalchemy import and_


def get_task_statistics(db):
    """获取任务统计信息"""
    session = db.get_session()
    try:
        # 统计近期历史任务
        recent_pending = session.query(InteractionTask).filter(
            and_(
                InteractionTask.task_type == 'history_recent',
                InteractionTask.status == 'pending'
            )
        ).count()

        recent_completed = session.query(InteractionTask).filter(
            and_(
                InteractionTask.task_type == 'history_recent',
                InteractionTask.status == 'completed'
            )
        ).count()

        # 统计旧历史任务
        old_pending = session.query(InteractionTask).filter(
            and_(
                InteractionTask.task_type == 'history_old',
                InteractionTask.status == 'pending'
            )
        ).count()

        # 统计实时任务
        realtime_pending = session.query(InteractionTask).filter(
            and_(
                InteractionTask.task_type == 'realtime',
                InteractionTask.status == 'pending'
            )
        ).count()

        return {
            'recent_pending': recent_pending,
            'recent_completed': recent_completed,
            'old_pending': old_pending,
            'realtime_pending': realtime_pending
        }
    finally:
        session.close()


def get_next_recent_task(db):
    """获取下一个近期历史任务

    只获取 history_recent 类型的任务
    """
    session = db.get_session()
    try:
        task = session.query(InteractionTask).filter(
            and_(
                InteractionTask.task_type == 'history_recent',  # 只处理近期历史
                InteractionTask.status == 'pending',
                InteractionTask.priority == 'high'  # 高优先级
            )
        ).order_by(
            InteractionTask.created_at.asc()  # 按创建时间排序
        ).first()

        return task
    finally:
        session.close()


def main():
    """主函数"""
    logger.info("=" * 70)
    logger.info("🚀 近期评论自动化脚本 - 启动")
    logger.info("=" * 70)

    try:
        # 初始化数据库
        logger.info("\n初始化数据库...")
        db = DatabaseManager()
        db.init_db()
        logger.info("✓ 数据库初始化完成")

        # 获取任务统计
        logger.info("\n" + "=" * 70)
        logger.info("📊 任务统计")
        logger.info("=" * 70)

        stats = get_task_statistics(db)

        logger.info(f"\n【近期历史评论】(history_recent)")
        logger.info(f"  待处理: {stats['recent_pending']} 个任务")
        logger.info(f"  已完成: {stats['recent_completed']} 个任务")
        logger.info(f"  完成率: {stats['recent_completed'] / (stats['recent_completed'] + stats['recent_pending']) * 100:.1f}%" if stats['recent_pending'] + stats['recent_completed'] > 0 else "  完成率: N/A")

        logger.info(f"\n【历史旧评论】(history_old)")
        logger.info(f"  待处理: {stats['old_pending']} 个任务")

        logger.info(f"\n【实时新增评论】(realtime)")
        logger.info(f"  待处理: {stats['realtime_pending']} 个任务")

        if stats['recent_pending'] == 0:
            logger.info("\n✓ 所有近期历史评论任务已处理完成！")
            logger.info("\n📌 提示:")
            logger.info(f"  - 如需处理历史旧评论（{stats['old_pending']}个），运行: python programs/run_long_term_automation.py")
            logger.info(f"  - 如需处理实时新增评论（{stats['realtime_pending']}个），运行: python programs/run_monitor_crawler.py")
            return 0

        # 确认开始
        logger.info("\n" + "=" * 70)
        logger.info(f"准备处理 {stats['recent_pending']} 个近期历史评论任务")
        logger.info("=" * 70)

        confirm = input("\n是否开始自动化处理？(y/n): ").strip().lower()
        if confirm not in ['y', 'yes', '']:
            logger.info("已取消")
            return 0

        # 开始处理任务
        logger.info("\n" + "=" * 70)
        logger.info("开始处理近期历史评论任务")
        logger.info("=" * 70)

        processed_count = 0
        start_time = datetime.now()

        while True:
            # 获取下一个任务
            task = get_next_recent_task(db)
            if not task:
                logger.info("\n✓ 所有近期历史评论任务处理完成！")
                break

            processed_count += 1

            logger.info(f"\n[{processed_count}/{stats['recent_pending']}] 处理任务: {task.comment_user_name}")
            logger.info(f"  任务类型: {task.task_type}")
            logger.info(f"  优先级: {task.priority}")
            logger.info(f"  视频ID: {task.video_id}")

            # TODO: 这里接入你的自动化设备处理逻辑
            # 示例：
            # from src.automation.device_controller import DeviceController
            # controller = DeviceController()
            # result = controller.process_task(task)

            # 模拟处理
            logger.info("  [!] 注意：当前为演示模式，未实际处理任务")
            logger.info("      请在代码中接入你的设备自动化逻辑")

            # 休眠（防止过快）
            time.sleep(1)

            # 每10个任务显示一次进度
            if processed_count % 10 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                avg_time = elapsed / processed_count
                remaining = stats['recent_pending'] - processed_count
                eta = remaining * avg_time

                logger.info(f"\n⏱ 进度统计:")
                logger.info(f"  已处理: {processed_count} / {stats['recent_pending']}")
                logger.info(f"  平均耗时: {avg_time:.1f}秒/任务")
                logger.info(f"  预计剩余: {eta/60:.1f}分钟")

        # 最终统计
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info("\n" + "=" * 70)
        logger.info("📊 处理完成统计")
        logger.info("=" * 70)
        logger.info(f"  处理任务数: {processed_count}")
        logger.info(f"  总耗时: {elapsed/60:.1f}分钟")
        logger.info(f"  平均耗时: {elapsed/processed_count:.1f}秒/任务" if processed_count > 0 else "  平均耗时: N/A")

        logger.info("\n📌 下一步:")
        logger.info("  1. 查看处理日志: logs/recent_automation.log")
        logger.info("  2. 查看设备执行日志: logs/device_*.log")
        logger.info("  3. 如需处理历史旧评论，运行: python programs/run_long_term_automation.py")
        logger.info("=" * 70)

        return 0

    except KeyboardInterrupt:
        logger.info("\n\n⚠ 用户中断执行")
        return 1
    except Exception as e:
        logger.error(f"\n❌ 执行出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
