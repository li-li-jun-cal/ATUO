#!/usr/bin/env python3
"""
历史评论爬虫启动脚本 - 爬取用户所有视频的评论

用法:
    python programs/run_history_crawler.py              # 交互式选择账号
    python programs/run_history_crawler.py --all        # 爬取所有账号
    python programs/run_history_crawler.py --accounts 1,3  # 爬取指定编号账号

功能:
    - 爬取所有目标账号的所有视频评论（不限制时间范围）
    - 存储到数据库的 comments 表
    - 生成 history 类型的自动化任务
    - 近3个月的视频评论自动设置为高优先级
    - 支持交互式选择账号

说明:
    这个脚本会获取用户的所有视频，不只是3个月内的
    近3个月的评论会被标记为高优先级，优先被自动化处理
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
        logging.FileHandler('logs/history_crawler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

from src.database.manager import DatabaseManager
from src.crawler.history_crawler import HistoryCrawler
from src.scheduler.task_generator import TaskGenerator
from src.crawler.api_client import DouyinAPIClient
import argparse


def select_accounts_interactive(target_accounts):
    """交互式选择账号

    Args:
        target_accounts: 所有目标账号列表

    Returns:
        选中的账号列表
    """
    print("\n" + "=" * 70)
    print("📋 可用账号列表")
    print("=" * 70)

    for idx, account in enumerate(target_accounts, 1):
        print(f"  [{idx}] {account.account_name}")
        print(f"      ID: {account.account_id}")
        print(f"      sec_user_id: {account.sec_user_id[:30]}...")
        print()

    print("=" * 70)
    print("\n请选择要爬取的账号：")
    print("  - 输入编号，多个用逗号分隔（如：1,3）")
    print("  - 输入 'all' 爬取所有账号")
    print("  - 按回车默认爬取所有账号")
    print()

    while True:
        choice = input("请输入选择: ").strip()

        # 默认选择所有
        if not choice or choice.lower() == 'all':
            logger.info(f"✓ 已选择所有 {len(target_accounts)} 个账号")
            return target_accounts

        try:
            # 解析输入的编号
            indices = [int(x.strip()) for x in choice.split(',')]

            # 验证编号范围
            if any(i < 1 or i > len(target_accounts) for i in indices):
                print(f"❌ 编号超出范围！请输入 1-{len(target_accounts)} 之间的数字")
                continue

            # 去重并排序
            indices = sorted(set(indices))

            # 获取选中的账号
            selected = [target_accounts[i-1] for i in indices]

            # 确认选择
            print(f"\n✓ 已选择 {len(selected)} 个账号:")
            for account in selected:
                print(f"  - {account.account_name}")

            confirm = input("\n确认开始爬取？(y/n): ").strip().lower()
            if confirm in ['y', 'yes', '']:
                logger.info(f"✓ 用户确认，开始爬取 {len(selected)} 个账号")
                return selected
            else:
                print("\n已取消，请重新选择...\n")
                continue

        except ValueError:
            print("❌ 输入格式错误！请输入数字编号，多个用逗号分隔（如：1,3）")
            continue


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='历史评论爬虫 - 支持选择性爬取')
    parser.add_argument('--all', action='store_true', help='爬取所有账号（跳过交互）')
    parser.add_argument('--accounts', type=str, help='指定账号编号，逗号分隔（如：1,3）')
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("📝 历史评论爬虫 - 启动（爬取所有视频）")
    logger.info("=" * 70)

    try:
        # 初始化数据库
        logger.info("\n初始化数据库...")
        db = DatabaseManager()
        db.init_db()
        logger.info("✓ 数据库初始化完成")

        # 检查是否有API客户端
        # 注意：这里使用项目中的DouyinAPIClient
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
        crawler = HistoryCrawler(db, api_client)
        task_generator = TaskGenerator(db)

        # 获取所有目标账号
        target_accounts = db.get_target_accounts()
        if not target_accounts:
            logger.error("❌ 未配置任何目标账号")
            logger.info("请在 config/target_accounts.json 中配置目标账号")
            return 1

        logger.info(f"✓ 找到 {len(target_accounts)} 个目标账号")

        # 根据参数选择账号
        if args.all:
            # --all 参数：爬取所有账号
            selected_accounts = target_accounts
            logger.info(f"✓ [--all] 将爬取所有 {len(selected_accounts)} 个账号")

        elif args.accounts:
            # --accounts 参数：指定账号编号
            try:
                indices = [int(x.strip()) for x in args.accounts.split(',')]

                # 验证编号范围
                if any(i < 1 or i > len(target_accounts) for i in indices):
                    logger.error(f"❌ 编号超出范围！请输入 1-{len(target_accounts)} 之间的数字")
                    return 1

                # 去重并排序
                indices = sorted(set(indices))
                selected_accounts = [target_accounts[i-1] for i in indices]

                logger.info(f"✓ [--accounts] 已选择 {len(selected_accounts)} 个账号:")
                for account in selected_accounts:
                    logger.info(f"  - {account.account_name}")

            except ValueError:
                logger.error("❌ --accounts 参数格式错误！示例：--accounts 1,3")
                return 1
        else:
            # 无参数：交互式选择
            selected_accounts = select_accounts_interactive(target_accounts)
            if not selected_accounts:
                logger.warning("未选择任何账号，退出")
                return 0

        # 逐个爬取选中的账号
        logger.info("\n" + "=" * 70)
        logger.info(f"开始爬取历史评论 - 共 {len(selected_accounts)} 个账号")
        logger.info("=" * 70)

        total_comments = 0
        total_videos = 0

        for idx, account in enumerate(selected_accounts, 1):
            logger.info(f"\n[账号 {idx}/{len(selected_accounts)}] {account.account_name}")
            logger.info("-" * 70)

            # 爬取历史评论
            result = crawler.crawl_history(account, days=90)

            if result['status'] == 'success':
                logger.info(f"  ✓ 爬虫完成")
                logger.info(f"    - 视频数: {result.get('total_videos', 0)}")
                logger.info(f"    - 评论数: {result.get('total_comments', 0)}")

                total_comments += result.get('total_comments', 0)
                total_videos += result.get('total_videos', 0)

                # 生成任务
                task_count = task_generator.generate_from_history(account.id)
                logger.info(f"  ✓ 任务生成完成")
                logger.info(f"    - 生成任务: {task_count}")

            else:
                logger.error(f"  ✗ 爬虫失败: {result.get('error', '未知错误')}")

        # 统计结果
        logger.info("\n" + "=" * 70)
        logger.info("📊 爬虫统计结果")
        logger.info("=" * 70)
        logger.info(f"  总视频数: {total_videos}")
        logger.info(f"  总评论数: {total_comments}")
        logger.info(f"  ✓ 爬虫执行完成")

        logger.info("\n📌 下一步:")
        logger.info("  1. 查看生成的任务: python programs/run_long_term_automation.py")
        logger.info("  2. 启动长期自动化处理评论")
        logger.info("=" * 70)

        return 0

    except Exception as e:
        logger.error(f"\n❌ 执行出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
