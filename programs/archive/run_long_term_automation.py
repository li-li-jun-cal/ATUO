#!/usr/bin/env python3
"""
长期自动化启动脚本 - 处理3个月前的历史旧评论

用法:
    python programs/run_long_term_automation.py [--auto] [--interactive] [--devices N]

功能:
    - 专门处理 history_old 类型的任务（3个月前的视频评论）
    - 普通优先级处理（priority='normal'）
    - 每台设备每天处理 50 个用户
    - 处理流程: 搜索用户 → 点赞 → 收藏 → 关注

任务类型说明:
    - history_old: 3个月前的视频评论（本脚本处理）
    - history_recent: 3个月内的视频评论（run_priority_automation.py处理）
    - realtime: 监控发现的新增评论（run_priority_automation.py处理）

设备管理:
    --auto           自动使用所有在线设备
    --interactive    交互选择设备
    --devices N      指定使用N台设备

说明:
    - 这个脚本会一直运行，直到手动停止 (Ctrl+C)
    - 设备并发工作，互不干扰
    - 每天会自动重置配额
    - 无任务时会自动休眠
    - 处理3个月前10000条评论约需40天

推荐配置:
    同时运行多个脚本，形成三层优先级处理:
    1. run_priority_automation.py --mode realtime  (最高优先级)
    2. run_priority_automation.py --mode recent    (高优先级)
    3. run_long_term_automation.py                 (普通优先级，本脚本)

注意:
    - 需要配置真实的安卓设备（使用 adb）
    - 需要安装 uiautomator2
    - 需要将设备连接到电脑
"""

import sys
import logging
from pathlib import Path

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/long_term_automation.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

from src.database.manager import DatabaseManager
from src.executor.automation_executor import AutomationExecutor
from src.scheduler.task_scheduler import TaskScheduler
from src.config.daily_quota import DailyQuota
import time
import threading


def worker_long_term(device_id, db, scheduler):
    """长期工作线程"""
    try:
        logger.info(f"✓ 启动长期工作线程: {device_id}")
        executor = AutomationExecutor(device_id, db)

        # 启动抖音应用
        logger.info(f"[{device_id}] 启动抖音应用...")
        if hasattr(executor.executor, 'navigator'):
            executor.executor.navigator.start_douyin_app()
            time.sleep(3)  # 等待应用启动完成

    except Exception as e:
        logger.error(f"✗ {device_id} 初始化失败: {e}")
        return

    consecutive_empty = 0
    max_empty_cycles = 12  # 10秒 × 12 = 120秒 无任务后重新检查

    try:
        while True:
            try:
                # 检查日配额
                quota = scheduler.check_daily_quota(device_id)

                if quota and quota['remaining'] <= 0:
                    logger.info(f"[{device_id}] 今日配额已用完，休息中...")
                    time.sleep(3600)  # 休息1小时
                    continue

                # 获取下一个历史旧任务（history_old，3个月前的视频）
                task = scheduler.get_next_task_for_device(device_id, 'history_old')

                if task:
                    consecutive_empty = 0
                    logger.info(f"[{device_id}] 获取任务 #{task.id} - {task.comment_user_name}")

                    success = executor.execute_history_task(task)

                    if success:
                        scheduler.update_daily_stats(device_id, 'completed')
                        logger.info(f"[{device_id}] ✓ 任务完成")
                    else:
                        scheduler.update_daily_stats(device_id, 'failed')
                        logger.warning(f"[{device_id}] ⚠ 任务失败")

                    time.sleep(5)  # 任务间隔
                else:
                    consecutive_empty += 1
                    if consecutive_empty % 6 == 1:  # 每60秒打印一次
                        logger.debug(f"[{device_id}] 暂无待执行任务，等待中...")
                    time.sleep(10)  # 等待10秒再检查

                    if consecutive_empty > max_empty_cycles:
                        logger.info(f"[{device_id}] 长时间无任务，进入深度休眠")
                        time.sleep(300)  # 5分钟
                        consecutive_empty = 0

            except Exception as e:
                logger.error(f"[{device_id}] 工作线程错误: {e}")
                time.sleep(30)

    finally:
        # 线程退出时关闭抖音
        try:
            logger.info(f"[{device_id}] 工作线程退出，关闭抖音应用...")
            if hasattr(executor.executor, 'navigator'):
                executor.executor.navigator.stop_douyin_app()
        except Exception as e:
            logger.error(f"[{device_id}] 关闭抖音失败: {e}")


def main():
    """主函数"""
    import argparse

    # 添加命令行参数
    parser = argparse.ArgumentParser(description='长期自动化 - 处理3个月前的历史旧评论')
    parser.add_argument('--auto', action='store_true', help='自动模式：使用所有在线设备')
    parser.add_argument('--interactive', '-i', action='store_true', help='交互模式：手动选择设备')
    parser.add_argument('--devices', type=int, help='指定使用的设备数量')
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("🤖 长期自动化 - 启动（处理3个月前的历史旧评论）")
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

        # 设备管理
        from src.utils.device_manager import DeviceManager
        device_manager = DeviceManager()

        # 检测在线设备
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

        # 根据参数选择设备
        if args.auto:
            # 自动模式：使用所有在线设备
            selected_devices = online_devices
            logger.info(f"✓ 自动模式: 使用所有 {len(selected_devices)} 台设备")

        elif args.devices:
            # 指定数量模式
            selected_devices = online_devices[:args.devices]
            logger.info(f"✓ 使用前 {len(selected_devices)} 台设备")

        elif args.interactive or len(online_devices) > 1:
            # 交互模式：手动选择设备
            selected_devices = device_manager.interactive_select_devices(online_devices)

            if not selected_devices:
                logger.warning("未选择任何设备，退出")
                return 0

        else:
            # 只有1台设备，直接使用
            selected_devices = online_devices
            logger.info(f"✓ 使用唯一在线设备: {selected_devices[0]}")

        # 映射到Device名称
        devices = device_manager.map_to_device_names(selected_devices)

        # 锁定设备（标记为被长期自动化占用）
        device_manager.lock_devices(devices, 'longterm')

        if not devices:
            logger.warning("⚠ 未配置任何设备，跳过启动")
            return 0

        workers = []

        logger.info("\n" + "=" * 70)
        logger.info(f"启动 {len(devices)} 台长期工作设备...")
        logger.info("=" * 70)

        for device_id in devices:
            thread = threading.Thread(
                target=worker_long_term,
                args=(device_id, db, scheduler),
                daemon=True
            )
            thread.start()
            workers.append(thread)
            logger.info(f"  ✓ {device_id} 已启动")

        logger.info("\n" + "=" * 70)
        logger.info("📊 系统状态")
        logger.info("=" * 70)

        # 统计待执行任务
        session = db.get_session()
        from src.database.models import InteractionTask

        # 统计历史旧任务（3个月前的）
        old_pending = session.query(InteractionTask)\
            .filter_by(task_type='history_old', status='pending')\
            .count()

        # 同时显示其他类型任务的统计
        recent_pending = session.query(InteractionTask)\
            .filter_by(task_type='history_recent', status='pending')\
            .count()

        realtime_pending = session.query(InteractionTask)\
            .filter_by(task_type='realtime', status='pending')\
            .count()

        session.close()

        device_list = ', '.join(devices)

        # 获取默认配额信息
        default_quota = DailyQuota()
        total_quota = len(devices) * default_quota.max_users

        logger.info(f"\n【任务统计】")
        logger.info(f"  历史旧评论 (history_old, 3个月前): {old_pending} 个 ← 本脚本处理")
        logger.info(f"  近期评论 (history_recent, 3个月内): {recent_pending} 个")
        logger.info(f"  实时新增 (realtime): {realtime_pending} 个")

        logger.info(f"\n【设备配置】")
        logger.info(f"  工作设备: {len(devices)} 台 ({device_list})")
        logger.info(f"  每台配额: {default_quota.max_users} 用户/天")
        logger.info(f"  总处理速率: ~{total_quota} 用户/天")
        logger.info(f"  操作配额: 关注={default_quota.max_follow}, 点赞={default_quota.max_like}, 收藏={default_quota.max_collect}")

        if old_pending > 0:
            estimated_days = (old_pending / total_quota) if total_quota > 0 else 0
            logger.info(f"\n  预计完成时间: ~{estimated_days:.0f} 天")
        else:
            logger.info(f"\n  ✓ 所有历史旧评论任务已处理完成！")

        logger.info("\n" + "=" * 70)
        logger.info("💡 提示")
        logger.info("=" * 70)
        logger.info("  - 按 Ctrl+C 停止所有工作线程")
        logger.info("  - 查看日志: tail -f logs/long_term_automation.log")
        logger.info("  - 本脚本处理: history_old（3个月前的历史旧评论）")
        logger.info("  - 如需处理近期/实时任务，运行:")
        logger.info("    python programs/run_priority_automation.py --mode mixed --auto")
        logger.info("=" * 70)

        # 保持主线程运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n\n[停止] 收到停止信号，正在关闭...")

            # 解锁设备
            device_manager.unlock_devices('longterm')
            logger.info("✓ 设备已解锁")

            logger.info("✓ 所有工作线程已停止")
            return 0

    except Exception as e:
        logger.error(f"\n❌ 执行出错: {e}")
        import traceback
        traceback.print_exc()

        # 出错时也解锁设备
        try:
            device_manager.unlock_devices('longterm')
        except:
            pass

        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
