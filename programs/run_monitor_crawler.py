#!/usr/bin/env python3
"""
监控爬虫启动脚本 - 每天监控新增评论

用法:
    python programs/run_monitor_crawler.py

    或定时运行（如使用 cron）:
    0 2 * * * python /path/to/programs/run_monitor_crawler.py

功能:
    - 每天检查目标账号的评论
    - 发现新增评论（与历史数据对比）
    - 存储到数据库的 new_comments 表
    - 生成 realtime 类型的高优先级任务（给实时设备处理）

说明:
    - 推荐每天凌晨2点运行一次
    - 发现的新增评论会作为高优先级任务
    - 实时设备会优先处理这些任务
    - 可以手动运行或使用定时任务调度
    - 与长期自动化系统配合工作
"""

import sys
import logging
import json
from pathlib import Path
from datetime import datetime

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 确保日志目录存在
log_dir = PROJECT_ROOT / 'logs'
log_dir.mkdir(exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'monitor_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

from src.database.manager import DatabaseManager
from src.crawler.monitor_crawler import MonitorCrawler
from src.scheduler.task_generator import TaskGenerator
from src.crawler.api_client import DouyinAPIClient


def load_config():
    """加载配置文件（与 run_long_term_automation.py 保持一致）"""
    try:
        config_file = PROJECT_ROOT / 'config' / 'config.json'
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning("⚠ 配置文件不存在，使用默认配置")
            return {}
    except Exception as e:
        logger.warning(f"⚠ 读取配置文件失败: {e}，使用默认配置")
        return {}


def main():
    """主函数"""
    logger.info("=" * 70)
    logger.info("👁️  监控爬虫 - 启动")
    logger.info(f"    运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    try:
        # 加载配置
        config = load_config()

        # 初始化数据库
        logger.info("\n初始化数据库...")
        db = DatabaseManager()
        db.init_db()
        logger.info("✓ 数据库初始化完成")

        # 检查是否有API客户端
        logger.info("\n初始化API客户端...")
        try:
            api_client = DouyinAPIClient()
            logger.info("✓ API客户端初始化完成")
        except Exception as e:
            logger.error(f"""
❌ API客户端初始化失败: {e}

可能的原因:
  1. 配置文件不存在: config/config.json
  2. API服务器无法连接
  3. 网络连接问题

解决方案:
  1. 创建 config/config.json 配置文件
  2. 配置API服务器地址和密钥
  3. 检查网络连接

配置文件示例:
    {{
        "api": {{
            "servers": [
                {{
                    "name": "主力服务器",
                    "base_url": "http://your-api-server.com",
                    "priority": 1,
                    "api_key": "your-api-key"
                }}
            ],
            "timeout": 30,
            "max_retries": 3,
            "request_delay": 0.5
        }}
    }}
            """)
            return 1

        # 初始化爬虫
        logger.info("\n初始化爬虫...")
        crawler = MonitorCrawler(db, api_client)
        task_generator = TaskGenerator(db)
        logger.info("✓ 爬虫初始化完成")

        # 获取所有目标账号
        target_accounts = db.get_target_accounts()
        if not target_accounts:
            logger.error("❌ 未配置任何目标账号")
            logger.info("请在 config/target_accounts.json 中配置目标账号")
            return 1

        logger.info(f"✓ 找到 {len(target_accounts)} 个目标账号")

        # 从配置中获取监控参数
        monitor_config = config.get('monitor', {})
        top_n_videos = monitor_config.get('top_n_videos', 5)  # 默认监控前5个视频

        # 逐个监控
        logger.info("\n" + "=" * 70)
        logger.info("开始监控新增评论...")
        logger.info(f"  监控参数: 每个账号取前 {top_n_videos} 个视频")
        logger.info("=" * 70)

        total_new_comments = 0
        total_tasks_generated = 0
        success_accounts = 0
        failed_accounts = 0

        for idx, account in enumerate(target_accounts, 1):
            logger.info(f"\n[账号 {idx}/{len(target_accounts)}] {account.account_name}")
            logger.info("-" * 70)

            try:
                # 监控新增评论
                result = crawler.monitor_daily(account, top_n=top_n_videos)

                if result['status'] == 'success':
                    new_count = result.get('new_comments_count', 0)
                    logger.info(f"  ✓ 监控完成")
                    logger.info(f"    - 发现新增: {new_count} 条")

                    total_new_comments += new_count
                    success_accounts += 1

                    # 生成任务（如果有新增评论）
                    if new_count > 0:
                        task_count = task_generator.generate_from_realtime(account.id)
                        total_tasks_generated += task_count
                        logger.info(f"  ✓ 任务生成完成")
                        logger.info(f"    - 生成高优先级任务: {task_count} 个")
                        logger.info(f"    - 这些任务将被实时设备优先处理")
                    else:
                        logger.info(f"  ℹ️  暂无新增评论")

                else:
                    failed_accounts += 1
                    error_msg = result.get('error', '未知错误')
                    logger.error(f"  ✗ 监控失败: {error_msg}")

            except Exception as e:
                failed_accounts += 1
                logger.error(f"  ✗ 处理账号时出错: {e}")
                import traceback
                logger.debug(traceback.format_exc())

        # 统计结果
        logger.info("\n" + "=" * 70)
        logger.info("📊 监控统计结果")
        logger.info("=" * 70)
        logger.info(f"  监控账号数: {len(target_accounts)} 个")
        logger.info(f"    - 成功: {success_accounts} 个")
        logger.info(f"    - 失败: {failed_accounts} 个")
        logger.info(f"  发现新增评论: {total_new_comments} 条")
        logger.info(f"  生成任务数: {total_tasks_generated} 个")

        if total_new_comments > 0:
            logger.info(f"\n  ✓ 已生成 {total_tasks_generated} 个高优先级任务")
            logger.info(f"  ⏱️  实时设备将在1小时内处理")
        else:
            logger.info(f"\n  ℹ️  本次监控暂无新增评论")

        logger.info("=" * 70)

        # 记录本次监控到数据库（可选）
        try:
            session = db.get_session()
            from src.database.models import MonitorLog

            # 假设有 MonitorLog 模型（如果没有可以跳过）
            monitor_log = MonitorLog(
                monitor_time=datetime.now(),
                accounts_count=len(target_accounts),
                success_count=success_accounts,
                failed_count=failed_accounts,
                new_comments_count=total_new_comments,
                tasks_generated=total_tasks_generated
            )
            session.add(monitor_log)
            session.commit()
            session.close()
            logger.debug("✓ 监控日志已保存到数据库")
        except Exception as e:
            logger.debug(f"⚠ 保存监控日志失败（可忽略）: {e}")

        return 0

    except KeyboardInterrupt:
        logger.info("\n\n[停止] 收到停止信号")
        return 0

    except Exception as e:
        logger.error(f"\n❌ 执行出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
