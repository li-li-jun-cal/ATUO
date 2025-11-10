#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高优先级自动化统一脚本
支持多种工作模式：实时监控、近期历史、混合模式

用法:
    # 实时模式 - 处理监控发现的新增评论（常驻）
    python programs/run_priority_automation.py --mode realtime

    # 近期模式 - 处理3个月内的历史评论（批量）
    python programs/run_priority_automation.py --mode recent

    # 混合模式 - 同时处理实时和近期评论（常驻，优先实时）
    python programs/run_priority_automation.py --mode mixed

工作模式说明:
    realtime (实时模式):
        - 任务类型: task_type='realtime'
        - 数据来源: 监控爬虫发现的新增评论
        - 工作方式: 常驻后台，无任务时模拟正常用户
        - 响应时间: <1小时
        - 适用场景: 需要快速响应新增评论

    recent (近期模式):
        - 任务类型: task_type='history_recent'
        - 数据来源: 历史爬虫中3个月内的评论
        - 工作方式: 批量处理，处理完自动结束
        - 响应时间: 数小时到数天
        - 适用场景: 集中处理近期高价值评论

    mixed (混合模式):
        - 任务类型: 'realtime' + 'history_recent'
        - 优先级: realtime > history_recent
        - 工作方式: 常驻后台，优先处理实时，空闲处理近期
        - 响应时间: 实时<1小时，近期视队列长度
        - 适用场景: 全面覆盖，最大化转化率

设备管理:
    --auto           自动模式，使用所有在线设备
    --interactive    交互模式，手动选择设备
    --devices N      指定使用N台设备

示例:
    # 实时模式，使用所有设备
    python programs/run_priority_automation.py --mode realtime --auto

    # 近期模式，交互选择设备
    python programs/run_priority_automation.py --mode recent --interactive

    # 混合模式，使用2台设备
    python programs/run_priority_automation.py --mode mixed --devices 2
"""

import logging
from pathlib import Path
import sys
import threading
import time
import argparse
from datetime import datetime

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager
from src.database.models import InteractionTask
from src.executor.automation_executor import AutomationExecutor
from src.scheduler.task_scheduler import TaskScheduler
from src.utils.device_manager import DeviceManager
from src.config.daily_quota import interactive_quota_config
from sqlalchemy import and_, or_

# 配置日志
log_file_map = {
    'realtime': 'logs/realtime_automation.log',
    'recent': 'logs/recent_automation.log',
    'mixed': 'logs/priority_automation.log'
}

logger = logging.getLogger(__name__)


def setup_logging(mode):
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_map.get(mode, 'logs/priority_automation.log')),
            logging.StreamHandler()
        ]
    )


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

        # 统计实时任务
        realtime_pending = session.query(InteractionTask).filter(
            and_(
                InteractionTask.task_type == 'realtime',
                InteractionTask.status == 'pending'
            )
        ).count()

        realtime_completed = session.query(InteractionTask).filter(
            and_(
                InteractionTask.task_type == 'realtime',
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

        return {
            'recent_pending': recent_pending,
            'recent_completed': recent_completed,
            'realtime_pending': realtime_pending,
            'realtime_completed': realtime_completed,
            'old_pending': old_pending
        }
    finally:
        session.close()


def worker_realtime_only(device_id, db, scheduler, quota=None):
    """纯实时工作线程 - 只处理realtime任务"""
    try:
        logger.info(f"✓ 启动实时工作线程: {device_id}")
        executor = AutomationExecutor(device_id, db, daily_quota=quota)
    except Exception as e:
        logger.error(f"✗ {device_id} 初始化失败: {e}")
        return

    consecutive_empty = 0
    max_empty_cycles = 6  # 60秒无任务后进入深度待机

    while True:
        try:
            # 只获取 realtime 任务
            task = scheduler.get_next_task_for_device(device_id, 'realtime')

            if task:
                consecutive_empty = 0
                logger.info(f"[{device_id}] 获取实时任务 #{task.id} - {task.comment_user_name}")

                # realtime 任务使用完整流程（包含评论）
                success = executor.execute_realtime_task(task)

                if success:
                    scheduler.update_daily_stats(device_id, 'completed')
                    logger.info(f"[{device_id}] ✓ 任务完成")
                else:
                    scheduler.update_daily_stats(device_id, 'failed')
                    logger.warning(f"[{device_id}] ⚠ 任务失败")

                time.sleep(5)  # 任务间隔
            else:
                consecutive_empty += 1

                if consecutive_empty == 1:
                    logger.info(f"[{device_id}] 暂无实时任务，进入待机模式")
                elif consecutive_empty % 6 == 0:
                    logger.debug(f"[{device_id}] 待机中，监听新任务...")

                # 待机模式：模拟正常用户
                executor.simulate_normal_user()
                time.sleep(10)

                # 连续无任务多次后，长时间睡眠
                if consecutive_empty > max_empty_cycles:
                    logger.debug(f"[{device_id}] 进入深度睡眠")
                    time.sleep(300)  # 5分钟
                    consecutive_empty = 0

        except Exception as e:
            logger.error(f"[{device_id}] 工作线程错误: {e}")
            time.sleep(30)


def worker_recent_only(device_id, db, scheduler, quota=None):
    """纯近期工作线程 - 只处理history_recent任务"""
    try:
        logger.info(f"✓ 启动近期工作线程: {device_id}")
        executor = AutomationExecutor(device_id, db, daily_quota=quota)
    except Exception as e:
        logger.error(f"✗ {device_id} 初始化失败: {e}")
        return

    processed_count = 0

    while True:
        try:
            # 只获取 history_recent 任务
            task = scheduler.get_next_task_for_device(device_id, 'history_recent')

            if task:
                processed_count += 1
                logger.info(f"[{device_id}] 获取近期任务 #{task.id} - {task.comment_user_name} ({processed_count})")

                # history_recent 任务使用简化流程（无评论）
                success = executor.execute_history_task(task)

                if success:
                    scheduler.update_daily_stats(device_id, 'completed')
                    logger.info(f"[{device_id}] ✓ 任务完成")
                else:
                    scheduler.update_daily_stats(device_id, 'failed')
                    logger.warning(f"[{device_id}] ⚠ 任务失败")

                time.sleep(5)  # 任务间隔
            else:
                logger.info(f"[{device_id}] ✓ 所有近期任务处理完成！共处理 {processed_count} 个任务")
                break  # 近期模式：处理完就结束

        except Exception as e:
            logger.error(f"[{device_id}] 工作线程错误: {e}")
            time.sleep(30)


def worker_mixed(device_id, db, scheduler, quota=None):
    """混合工作线程 - 优先realtime，其次history_recent"""
    try:
        logger.info(f"✓ 启动混合工作线程: {device_id}")
        executor = AutomationExecutor(device_id, db, daily_quota=quota)
    except Exception as e:
        logger.error(f"✗ {device_id} 初始化失败: {e}")
        return

    consecutive_empty = 0
    max_empty_cycles = 6

    while True:
        try:
            # 优先获取 realtime 任务
            task = scheduler.get_next_task_for_device(device_id, 'realtime')
            task_type = 'realtime'

            if task:
                consecutive_empty = 0
                logger.info(f"[{device_id}] 获取实时任务 #{task.id} - {task.comment_user_name} [优先]")
            else:
                # 没有实时任务，获取近期任务
                task = scheduler.get_next_task_for_device(device_id, 'history_recent')
                task_type = 'history_recent'

                if task:
                    consecutive_empty = 0
                    logger.info(f"[{device_id}] 获取近期任务 #{task.id} - {task.comment_user_name}")

            if task:
                # 根据任务类型选择执行方法
                if task_type == 'realtime':
                    # realtime 任务：完整流程（搜索→评论→关注→点赞→收藏）
                    success = executor.execute_realtime_task(task)
                else:
                    # history_recent 任务：简化流程（搜索→关注→点赞→收藏，无评论）
                    success = executor.execute_history_task(task)

                if success:
                    scheduler.update_daily_stats(device_id, 'completed')
                    logger.info(f"[{device_id}] ✓ 任务完成")
                else:
                    scheduler.update_daily_stats(device_id, 'failed')
                    logger.warning(f"[{device_id}] ⚠ 任务失败")

                time.sleep(5)
            else:
                consecutive_empty += 1

                if consecutive_empty == 1:
                    logger.info(f"[{device_id}] 暂无任务，进入待机模式")
                elif consecutive_empty % 6 == 0:
                    logger.debug(f"[{device_id}] 待机中...")

                # 待机模式
                executor.simulate_normal_user()
                time.sleep(10)

                if consecutive_empty > max_empty_cycles:
                    logger.debug(f"[{device_id}] 进入深度睡眠")
                    time.sleep(300)
                    consecutive_empty = 0

        except Exception as e:
            logger.error(f"[{device_id}] 工作线程错误: {e}")
            time.sleep(30)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='高优先级自动化统一脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # 工作模式
    parser.add_argument('--mode', '-m',
                        choices=['realtime', 'recent', 'mixed'],
                        required=True,
                        help='工作模式: realtime(实时), recent(近期), mixed(混合)')

    # 设备选择
    parser.add_argument('--auto', action='store_true',
                        help='自动模式：使用所有在线设备')
    parser.add_argument('--interactive', '-i', action='store_true',
                        help='交互模式：手动选择设备')
    parser.add_argument('--devices', type=int,
                        help='指定使用的设备数量')

    args = parser.parse_args()

    # 设置日志
    setup_logging(args.mode)

    # 模式名称映射
    mode_names = {
        'realtime': '⚡ 实时模式',
        'recent': '📅 近期模式',
        'mixed': '🔀 混合模式'
    }

    logger.info("=" * 70)
    logger.info(f"{mode_names[args.mode]} - 启动")
    logger.info("=" * 70)

    try:
        # 初始化数据库
        logger.info("\n初始化数据库...")
        db = DatabaseManager()
        db.init_db()
        logger.info("✓ 数据库初始化完成")

        # 初始化调度器
        logger.info("\n初始化调度器...")
        scheduler = TaskScheduler(db)
        scheduler.init_device_assignments()
        logger.info("✓ 调度器初始化完成")

        # 获取任务统计
        logger.info("\n" + "=" * 70)
        logger.info("📊 任务统计")
        logger.info("=" * 70)

        stats = get_task_statistics(db)

        logger.info(f"\n【实时新增评论】(realtime)")
        logger.info(f"  待处理: {stats['realtime_pending']} 个任务")
        logger.info(f"  已完成: {stats['realtime_completed']} 个任务")

        logger.info(f"\n【近期历史评论】(history_recent, 3个月内)")
        logger.info(f"  待处理: {stats['recent_pending']} 个任务")
        logger.info(f"  已完成: {stats['recent_completed']} 个任务")

        logger.info(f"\n【历史旧评论】(history_old, 3个月前)")
        logger.info(f"  待处理: {stats['old_pending']} 个任务")
        logger.info(f"  提示: 使用 run_long_term_automation.py 处理")

        # 计算总任务数
        total_tasks = stats['realtime_pending'] + stats['recent_pending'] + stats['old_pending']

        # ✅ 配额配置（根据任务数量自动建议）
        logger.info("\n" + "=" * 70)
        quota = interactive_quota_config(total_tasks=total_tasks)
        logger.info("=" * 70)

        # 检查是否有任务需要处理
        if args.mode == 'realtime' and stats['realtime_pending'] == 0:
            logger.info("\n✓ 当前无实时任务，但仍会启动待机模式（监听新任务）")
        elif args.mode == 'recent' and stats['recent_pending'] == 0:
            logger.info("\n✓ 所有近期历史评论任务已处理完成！")
            return 0
        elif args.mode == 'mixed' and stats['realtime_pending'] == 0 and stats['recent_pending'] == 0:
            logger.info("\n✓ 当前无任务，但仍会启动待机模式（监听新任务）")

        # 设备管理
        device_manager = DeviceManager()

        logger.info("\n检测在线设备...")
        online_devices = device_manager.get_online_devices()

        if not online_devices:
            logger.error("❌ 未检测到任何在线设备")
            logger.info("  请确保:")
            logger.info("    1. ADB已正确安装并在PATH中")
            logger.info("    2. 设备已通过USB或网络连接")
            logger.info("    3. 设备已开启USB调试")
            return 1

        logger.info(f"✓ 检测到 {len(online_devices)} 台在线设备")

        # 选择设备
        if args.auto:
            selected_devices = online_devices
            logger.info(f"✓ 自动模式: 使用所有 {len(selected_devices)} 台设备")
        elif args.devices:
            selected_devices = online_devices[:args.devices]
            logger.info(f"✓ 使用前 {len(selected_devices)} 台设备")
        elif args.interactive or len(online_devices) > 1:
            selected_devices = device_manager.interactive_select_devices(online_devices)
            if not selected_devices:
                logger.warning("未选择任何设备，退出")
                return 0
        else:
            selected_devices = online_devices
            logger.info(f"✓ 使用唯一在线设备: {selected_devices[0]}")

        # 映射到Device名称
        devices = device_manager.map_to_device_names(selected_devices)

        # 锁定设备
        device_manager.lock_devices(devices, f'priority_{args.mode}')

        if not devices:
            logger.warning("⚠ 未配置任何设备，退出")
            return 0

        # 根据模式选择工作函数
        worker_func = {
            'realtime': worker_realtime_only,
            'recent': worker_recent_only,
            'mixed': worker_mixed
        }[args.mode]

        workers = []

        logger.info("\n" + "=" * 70)
        logger.info(f"启动 {len(devices)} 台设备 [{mode_names[args.mode]}]")
        logger.info("=" * 70)

        for device_id in devices:
            thread = threading.Thread(
                target=worker_func,
                args=(device_id, db, scheduler, quota),
                daemon=True
            )
            thread.start()
            workers.append(thread)
            logger.info(f"  ✓ {device_id} 已启动")

        logger.info("\n" + "=" * 70)
        logger.info("💡 工作模式说明")
        logger.info("=" * 70)

        if args.mode == 'realtime':
            logger.info("  - 监听实时新增评论（来自监控爬虫）")
            logger.info("  - 优先处理高优先级任务")
            logger.info("  - 无任务时进行待机（刷视频、点赞）")
            logger.info("  - 常驻运行，响应时间 <1小时")
        elif args.mode == 'recent':
            logger.info("  - 批量处理3个月内的历史评论")
            logger.info("  - 高优先级任务，转化率高")
            logger.info("  - 处理完自动结束")
            logger.info("  - 适合集中处理近期高价值评论")
        elif args.mode == 'mixed':
            logger.info("  - 优先处理实时新增评论")
            logger.info("  - 空闲时处理近期历史评论")
            logger.info("  - 无任务时进行待机")
            logger.info("  - 常驻运行，全面覆盖")

        logger.info("\n" + "=" * 70)
        logger.info("📊 系统状态")
        logger.info("=" * 70)
        logger.info(f"  工作设备: {len(devices)} 台 ({', '.join(devices)})")
        logger.info(f"  工作模式: {mode_names[args.mode]}")

        if args.mode == 'realtime':
            logger.info(f"  待处理任务: {stats['realtime_pending']} 个")
        elif args.mode == 'recent':
            logger.info(f"  待处理任务: {stats['recent_pending']} 个")
        elif args.mode == 'mixed':
            logger.info(f"  实时任务: {stats['realtime_pending']} 个")
            logger.info(f"  近期任务: {stats['recent_pending']} 个")

        logger.info("=" * 70)

        # 保持主线程运行
        try:
            if args.mode == 'recent':
                # 近期模式：等待所有线程完成
                for worker in workers:
                    worker.join()
                logger.info("\n✓ 所有任务处理完成，程序退出")
            else:
                # 实时/混合模式：常驻运行
                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n\n[停止] 收到停止信号，正在关闭...")

            # 解锁设备
            device_manager.unlock_devices(f'priority_{args.mode}')
            logger.info("✓ 设备已解锁")
            logger.info("✓ 所有工作线程已停止")
            return 0

    except Exception as e:
        logger.error(f"\n❌ 执行出错: {e}")
        import traceback
        traceback.print_exc()

        # 出错时也解锁设备
        try:
            device_manager.unlock_devices(f'priority_{args.mode}')
        except:
            pass

        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
