"""
DY-Interaction 批量处理版本

批量爬取历史评论，每天处理固定数量的用户
"""

import sys
import os
import time
import logging
import json
import argparse
from datetime import datetime, timedelta

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config.settings import (
    LOG_DIR, LOG_LEVEL, BATCH_LOOK_BACK_DAYS,
    BATCH_PROCESS_TIME, BATCH_DAILY_LIMIT
)
from src.database.manager import DatabaseManager
from src.crawler.scheduler import CrawlerScheduler
from src.crawler.api_client import DouyinAPIClient
from src.executor.device_coordinator import MultiDeviceCoordinator
from src.generator.task_generator import TaskGenerator

# 日志配置
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'{LOG_DIR}/batch_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BatchProcessor:
    """批量处理类"""

    def __init__(self, test_mode=False):
        """初始化批量处理器

        Args:
            test_mode: 是否为测试模式（立即执行，不等待）
        """
        logger.info("=" * 80)
        logger.info("DY-Interaction 批量处理版本 v1.0")
        logger.info("=" * 80)

        if test_mode:
            logger.info("⚠ 测试模式已启用 - 将立即执行，不等待定时")
            logger.info("=" * 80)

        # 初始化组件
        self.db = DatabaseManager()
        self.executor = None  # 将在 run() 中初始化
        self.crawler = None  # 将在 run() 中初始化
        self.generator = None  # 将在 run() 中初始化
        self.test_mode = test_mode

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

    def process_one_day(self):
        """处理一天的任务"""
        logger.info("\n" + "=" * 80)
        logger.info(f"开始每日批量处理: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        # 获取所有目标账号
        target_accounts = self.db.get_target_accounts()
        logger.info(f"目标账号数: {len(target_accounts)}")

        for i, account in enumerate(target_accounts, 1):
            logger.info(f"\n[{i}/{len(target_accounts)}] 处理账号: {account.account_name}")

            try:
                # 获取批量处理进度
                progress = self.db.get_batch_progress(account.id)

                if not progress:
                    # 首次处理，创建进度记录
                    logger.info("  首次处理，创建进度记录")
                    self.db.create_batch_progress(account.id)

                # 爬取历史视频
                logger.info(f"  爬取 {BATCH_LOOK_BACK_DAYS} 天内的视频...")
                videos = self.crawler.crawl_historical_videos(account, BATCH_LOOK_BACK_DAYS)

                if not videos:
                    logger.warning("  没有视频需要处理")
                    continue

                logger.info(f"  ✓ 获取到 {len(videos)} 个视频")

                # 爬取所有视频的评论
                logger.info("  爬取视频评论...")
                video_ids = [v['aweme_id'] for v in videos]
                all_comments_map = self.crawler.crawl_video_comments_batch(video_ids)

                # 合并所有评论
                all_comments = []
                for video_id, comments in all_comments_map.items():
                    for comment in comments:
                        comment['video_id'] = video_id
                        comment['target_account_id'] = account.id
                    all_comments.extend(comments)

                logger.info(f"  ✓ 总共获取到 {len(all_comments)} 条评论")

                if not all_comments:
                    logger.warning("  没有评论需要处理")
                    continue

                # 生成任务（限制每天处理的用户数）
                logger.info(f"  生成任务（限制 {BATCH_DAILY_LIMIT} 个用户）...")
                tasks = self.generator.generate_batch_tasks(
                    account,
                    all_comments,
                    daily_limit=BATCH_DAILY_LIMIT
                )

                logger.info(f"  ✓ 生成任务数: {len(tasks)}")

                if not tasks:
                    logger.warning("  没有新任务")
                    continue

                # 执行任务
                logger.info("  执行互动任务...")
                results = self.executor.execute_task_parallel(tasks)
                success_count = sum(1 for _, success in results if success)
                logger.info(f"  ✓ 执行完成: {success_count}/{len(tasks)} 个任务成功")

                # 更新进度
                last_video_id = videos[0]['aweme_id'] if videos else ''
                self.db.update_batch_progress(
                    account.id,
                    last_video_id,
                    videos_count=len(videos),
                    comments_count=len(all_comments),
                    tasks_count=len(tasks)
                )

            except Exception as e:
                logger.error(f"  ✗ 处理失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue

        # 获取统计信息
        logger.info("\n" + "=" * 80)
        logger.info("[统计信息]")
        logger.info("=" * 80)

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

        logger.info("\n" + "=" * 80)
        logger.info("每日批量处理完成")
        logger.info("=" * 80)

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
            logger.info("开始批量处理模式")
            logger.info(f"处理时间: 每天 {BATCH_PROCESS_TIME}")
            logger.info(f"每天限制: {BATCH_DAILY_LIMIT} 个用户")
            logger.info(f"回溯天数: {BATCH_LOOK_BACK_DAYS} 天")
            logger.info("=" * 80)

            day_count = 0

            while True:
                try:
                    # 测试模式：立即执行一次后退出
                    if self.test_mode:
                        day_count += 1
                        logger.info(f"\n{'=' * 80}")
                        logger.info(f"测试执行 - 第 {day_count} 次")
                        logger.info(f"{'=' * 80}")

                        self.process_one_day()

                        logger.info("\n" + "=" * 80)
                        logger.info("✓ 测试执行完成")
                        logger.info("=" * 80)
                        break

                    # 正常模式：按时间执行
                    # 计算下次执行时间
                    current_time = datetime.now()
                    hour, minute = map(int, BATCH_PROCESS_TIME.split(':'))
                    process_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)

                    # 如果已经过了今天的处理时间，设置为明天
                    if current_time >= process_time:
                        process_time = process_time + timedelta(days=1)

                    wait_seconds = (process_time - current_time).total_seconds()

                    logger.info(f"\n当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.info(f"下次执行时间: {process_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.info(f"等待: {wait_seconds / 3600:.1f} 小时")

                    # 等待到指定时间
                    time.sleep(wait_seconds)

                    # 执行批量处理
                    day_count += 1
                    logger.info(f"\n{'=' * 80}")
                    logger.info(f"第 {day_count} 天处理")
                    logger.info(f"{'=' * 80}")

                    self.process_one_day()

                except KeyboardInterrupt:
                    logger.info("\n收到停止信号 (Ctrl+C)")
                    break
                except Exception as e:
                    logger.error(f"\n✗ 执行错误: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    logger.info("等待 60 秒后继续...")
                    time.sleep(60)

            logger.info("\n" + "=" * 80)
            logger.info("批量处理已停止")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"\n✗ 初始化失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='DY-Interaction 批量处理版本')
    parser.add_argument(
        '--test',
        '-t',
        action='store_true',
        help='启用测试模式：立即执行一次，不等待定时'
    )

    args = parser.parse_args()

    processor = BatchProcessor(test_mode=args.test)
    processor.run()


if __name__ == '__main__':
    main()
