#!/usr/bin/env python3
"""
实时自动化启动脚本 - 处理监控发现的新增评论

用法:
    python programs/run_realtime_automation.py

功能:
    - 启动配置文件中指定的实时待机设备
    - 监听 realtime 类型的高优先级任务
    - 优先处理监控爬虫发现的新增评论
    - 平时进行模拟用户行为（刷视频、点赞）
    - 处理流程: 搜索用户 → 发表评论 → 关注 → 点赞

说明:
    - 设备数量由 config/config.json 中的 realtime_devices 控制
    - 这个脚本应该和长期自动化同时运行
    - 设备专门处理新增评论
    - 响应时间: 通常<1小时
    - 无新任务时进行待机模拟，看起来像真实用户

推荐:
    - 同时启动 run_long_term_automation.py 和 run_realtime_automation.py
    - 定时启动 run_monitor_crawler.py (每天凌晨2点)

注意:
    - 需要配置真实的安卓设备（使用 adb）
    - 需要安装 uiautomator2
    - 需要将设备连接到电脑
"""

import logging
from pathlib import Path
import sys
import threading
import time

# 设置项目路径（必须在导入src模块之前）
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager
from src.executor.automation_executor import AutomationExecutor
from src.scheduler.task_scheduler import TaskScheduler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/realtime_automation.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)




def worker_realtime(device_id, db, scheduler):
    """实时工作线程"""
    try:
        logger.info(f"✓ 启动实时工作线程: {device_id}")
        executor = AutomationExecutor(device_id, db)
    except Exception as e:
        logger.error(f"✗ {device_id} 初始化失败: {e}")
        return

    consecutive_empty = 0
    max_empty_cycles = 6  # 10秒 × 6 = 60秒 无任务后进入待机模式

    while True:
        try:
            # 获取下一个 realtime 任务
            task = scheduler.get_next_task_for_device(device_id, 'realtime')

            if task:
                consecutive_empty = 0
                logger.info(f"[{device_id}] 获取优先任务 #{task.id} - {task.comment_user_name}")

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
                    logger.info(f"[{device_id}] 暂无优先任务，进入待机模式")
                elif consecutive_empty % 6 == 0:  # 每60秒打印一次
                    logger.debug(f"[{device_id}] 待机中，监听新任务...")

                # 待机模式：模拟正常用户
                executor.simulate_normal_user()
                time.sleep(10)  # 待机时间

                # 连续无任务多次后，长时间睡眠
                if consecutive_empty > max_empty_cycles:
                    logger.debug(f"[{device_id}] 进入深度睡眠")
                    time.sleep(300)  # 5分钟
                    consecutive_empty = 0

        except Exception as e:
            logger.error(f"[{device_id}] 工作线程错误: {e}")
            time.sleep(30)


def main():
    """主函数"""
    import argparse

    # 添加命令行参数
    parser = argparse.ArgumentParser(description='实时自动化 - 监控新增评论任务')
    parser.add_argument('--auto', action='store_true', help='自动模式：使用所有在线设备')
    parser.add_argument('--interactive', '-i', action='store_true', help='交互模式：手动选择设备')
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("⚡ 实时自动化 - 启动")
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

        # 设备分配逻辑
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

        # 根据模式选择设备
        if args.auto:
            # 自动模式：使用所有在线设备
            selected_devices = online_devices
            logger.info(f"✓ 自动模式: 使用所有 {len(selected_devices)} 台设备")

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

        # 锁定设备（标记为被实时自动化占用）
        device_manager.lock_devices(devices, 'realtime')

        if not devices:
            logger.warning("⚠ 未配置任何实时设备，跳过启动")
            return 0

        workers = []

        logger.info("\n" + "=" * 70)
        logger.info(f"启动 {len(devices)} 台实时待机设备...")
        logger.info("=" * 70)

        for device_id in devices:
            thread = threading.Thread(
                target=worker_realtime,
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
        realtime_count = session.query(InteractionTask)\
            .filter_by(task_type='realtime', status='pending')\
            .count()
        session.close()

        device_list = ', '.join(devices)

        logger.info(f"  待执行优先任务: {realtime_count} 个")
        logger.info(f"  工作设备: {len(devices)} 台 ({device_list})")
        logger.info(f"  无新任务时: 模拟正常用户行为")
        logger.info(f"  响应时间: <1 小时")

        logger.info("\n" + "=" * 70)
        logger.info("💡 工作模式")
        logger.info("=" * 70)
        logger.info("  1. 监听新增评论任务（来自监控爬虫）")
        logger.info("  2. 优先处理高优先级任务")
        logger.info("  3. 无任务时进行待机（刷视频、点赞）")
        logger.info("  4. 发现新任务时立即处理")

        logger.info("\n" + "=" * 70)
        logger.info("🎯 推荐配置")
        logger.info("=" * 70)
        logger.info("  同时运行:")
        logger.info("    - python programs/run_long_term_automation.py")
        logger.info("    - python programs/run_realtime_automation.py (本脚本)")
        logger.info("  ")
        logger.info("  定时运行:")
        logger.info("    - python programs/run_monitor_crawler.py (每天凌晨2点)")
        logger.info("=" * 70)

        # 保持主线程运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n\n[停止] 收到停止信号，正在关闭...")

            # 解锁设备
            device_manager.unlock_devices('realtime')
            logger.info("✓ 设备已解锁")

            logger.info("✓ 所有工作线程已停止")
            return 0

    except Exception as e:
        logger.error(f"\n❌ 执行出错: {e}")
        import traceback
        traceback.print_exc()

        # 出错时也解锁设备
        try:
            device_manager.unlock_devices('realtime')
        except:
            pass

        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
