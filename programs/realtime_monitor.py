"""
DY-Interaction 实时监控版本

监控目标账号的最新评论，立即执行互动操作
"""

import sys
import os
import time
import logging
import json
import argparse
from datetime import datetime

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config.settings import (
    LOG_DIR, LOG_LEVEL, REALTIME_CHECK_INTERVAL,
    INTERACTION_COMMENT_ENABLED, INTERACTION_LIKE_ENABLED,
    INTERACTION_FOLLOW_ENABLED, INTERACTION_DM_ENABLED
)
from src.database.manager import DatabaseManager
from src.crawler.scheduler import CrawlerScheduler
from src.executor.device_coordinator import MultiDeviceCoordinator
from src.generator.task_generator import TaskGenerator

# 日志配置
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'{LOG_DIR}/realtime_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RealtimeMonitor:
    """实时监控类"""

    def __init__(self, test_mode=False, test_cycles=1):
        """初始化实时监控

        Args:
            test_mode: 是否为测试模式（执行指定次数后退出）
            test_cycles: 测试模式下执行的循环次数（默认1次）
        """
        logger.info("=" * 80)
        logger.info("DY-Interaction 实时监控版本 v1.0")
        logger.info("=" * 80)

        if test_mode:
            logger.info(f"⚠ 测试模式已启用 - 执行 {test_cycles} 个循环后退出")
            logger.info("=" * 80)

        # 初始化组件
        self.db = DatabaseManager()
        self.executor = None  # 将在 run() 中初始化
        self.crawler = None  # 将在 run() 中初始化
        self.generator = None  # 将在 run() 中初始化
        self.test_mode = test_mode
        self.test_cycles = test_cycles

        logger.info("✓ 基础组件初始化完成")

    def load_config(self):
        """加载配置文件"""
        try:
            with open('config/target_accounts.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"✓ 加载配置: {len(config['target_accounts'])} 个目标账号")
            return config
        except FileNotFoundError:
            logger.error("✗ 配置文件不存在: config/target_accounts.json")
            logger.info("请复制 config/target_accounts.example.json 为 config/target_accounts.json")
            raise

    def check_devices(self):
        """检查设备连接"""
        if not self.executor:
            logger.error("✗ 执行器未初始化")
            return False

        devices = self.executor.get_available_devices()
        if not devices:
            logger.error("✗ 没有可用的设备")
            return False

        logger.info(f"✓ 检测到 {len(devices)} 个可用设备:")
        for device in devices:
            device_info = self.executor.get_device_info(device)
            logger.info(f"  - {device}: {device_info.get('device_name', 'Unknown')}")

        return True

    def run(self):
        """主循环"""
        try:
            # 初始化数据库
            logger.info("\n1. 初始化数据库...")
            self.db.init_db()
            logger.info("✓ 数据库初始化完成")

            # 加载配置
            logger.info("\n2. 加载配置文件...")
            config = self.load_config()

            # 初始化爬虫调度器
            logger.info("\n3. 初始化爬虫调度器...")
            from src.crawler.api_client import DouyinAPIClient
            api_client = DouyinAPIClient(config_path='config/api_config.json')
            self.crawler = CrawlerScheduler(self.db, api_client)
            logger.info("✓ 爬虫调度器初始化完成")

            # 初始化任务生成器
            logger.info("\n4. 初始化任务生成器...")
            self.generator = TaskGenerator(self.db)
            logger.info("✓ 任务生成器初始化完成")

            # 初始化设备协调器
            logger.info("\n5. 初始化设备协调器...")
            self.executor = MultiDeviceCoordinator(self.db)
            logger.info("✓ 设备协调器初始化完成")

            # 检查设备
            logger.info("\n6. 检查设备连接...")
            if not self.check_devices():
                raise Exception("设备检查失败")

            logger.info("\n" + "=" * 80)
            logger.info("开始实时监控")
            logger.info("=" * 80)

            cycle_count = 0

            while True:
                try:
                    cycle_count += 1
                    logger.info(f"\n{'=' * 80}")
                    logger.info(f"[循环 {cycle_count}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.info(f"{'=' * 80}")

                    # 获取所有目标账号
                    target_accounts = self.db.get_target_accounts()
                    logger.info(f"目标账号数: {len(target_accounts)}")

                    for i, account in enumerate(target_accounts, 1):
                        logger.info(f"\n[{i}/{len(target_accounts)}] 处理账号: {account.account_name}")

                        try:
                            # 爬取最新评论
                            logger.info("  爬取最新视频和评论...")
                            comments = self.crawler.crawl_target_account(
                                account,
                                max_videos=5
                            )
                            logger.info(f"  ✓ 获取评论数: {len(comments)}")

                            if not comments:
                                logger.info("  没有新评论，跳过")
                                continue

                            # 生成任务
                            logger.info("  生成互动任务...")
                            tasks = self.generator.generate_realtime_tasks(account, comments)
                            logger.info(f"  ✓ 生成任务数: {len(tasks)}")

                            if not tasks:
                                logger.info("  没有新任务，跳过")
                                continue

                            # 执行任务
                            logger.info("  执行互动任务...")
                            results = self.executor.execute_task_parallel(tasks)
                            success_count = sum(1 for _, success in results if success)
                            logger.info(f"  ✓ 执行完成: {success_count}/{len(tasks)} 个任务成功")

                        except Exception as e:
                            logger.error(f"  ✗ 处理失败: {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                            continue

                    # 获取统计信息
                    logger.info(f"\n{'=' * 80}")
                    logger.info("[统计信息]")
                    logger.info(f"{'=' * 80}")

                    stats = self.db.get_task_stats()
                    logger.info(f"任务状态:")
                    logger.info(f"  - 总数: {stats['total']}")
                    logger.info(f"  - 待执行: {stats['pending']}")
                    logger.info(f"  - 执行中: {stats['in_progress']}")
                    logger.info(f"  - 已完成: {stats['completed']}")
                    logger.info(f"  - 失败: {stats['failed']}")

                    device_stats = self.db.get_device_stats()
                    logger.info(f"\n设备状态:")
                    logger.info(f"  - 总数: {device_stats['total']}")
                    logger.info(f"  - 空闲: {device_stats['idle']}")
                    logger.info(f"  - 忙碌: {device_stats['busy']}")
                    logger.info(f"  - 错误: {device_stats['error']}")

                    # 如果在测试模式下，执行所有待执行的任务
                    if self.test_mode and stats['pending'] > 0:
                        logger.info(f"\n{'=' * 80}")
                        logger.info("[测试模式] 执行所有待执行的任务")
                        logger.info(f"{'=' * 80}")

                        pending_tasks = self.db.get_interaction_tasks(status='pending', limit=1000)
                        logger.info(f"执行待执行任务: {len(pending_tasks)} 个")

                        if pending_tasks:
                            results = self.executor.execute_task_parallel(pending_tasks)
                            success_count = sum(1 for _, success in results if success)
                            logger.info(f"✓ 任务执行完成: {success_count}/{len(results)} 个任务成功")

                    # 测试模式检查
                    if self.test_mode and cycle_count >= self.test_cycles:
                        logger.info(f"\n✓ 测试模式完成（执行 {cycle_count} 个循环）")
                        break

                    # 等待下一个检查周期
                    logger.info(f"\n等待 {REALTIME_CHECK_INTERVAL} 秒后继续...")
                    logger.info(f"{'=' * 80}\n")
                    time.sleep(REALTIME_CHECK_INTERVAL if not self.test_mode else 1)

                except KeyboardInterrupt:
                    logger.info("\n收到停止信号 (Ctrl+C)")
                    break
                except Exception as e:
                    logger.error(f"\n✗ 循环错误: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    logger.info("等待 60 秒后继续...")
                    time.sleep(60)

            logger.info("\n" + "=" * 80)
            logger.info("实时监控已停止")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"\n✗ 初始化失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='DY-Interaction 实时监控版本')
    parser.add_argument(
        '--test',
        '-t',
        action='store_true',
        help='启用测试模式：执行1个循环后退出'
    )
    parser.add_argument(
        '--cycles',
        '-c',
        type=int,
        default=1,
        help='测试模式下执行的循环次数（默认1次）'
    )

    args = parser.parse_args()

    monitor = RealtimeMonitor(test_mode=args.test, test_cycles=args.cycles)
    monitor.run()


if __name__ == '__main__':
    main()
