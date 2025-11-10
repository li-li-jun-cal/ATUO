#!/usr/bin/env python3
"""
初始化配置：将 config/target_accounts.json 中的账号导入到数据库
"""

import sys
import json
import logging
from pathlib import Path

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

from src.database.manager import DatabaseManager
from src.database.models import TargetAccount


def load_accounts_from_config(config_path='config/target_accounts.json'):
    """从配置文件加载账号"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        accounts = config.get('accounts', [])
        logger.info(f"✓ 从配置文件加载了 {len(accounts)} 个账号")
        return accounts

    except FileNotFoundError:
        logger.error(f"❌ 配置文件不存在: {config_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"❌ 配置文件 JSON 格式错误: {e}")
        return []


def import_accounts_to_db(accounts):
    """将账号导入到数据库"""
    db = DatabaseManager()
    db.init_db()

    logger.info("\n开始导入账号到数据库...")
    logger.info("=" * 70)

    success_count = 0
    for i, account_config in enumerate(accounts, 1):
        try:
            account_name = account_config.get('account_name')
            sec_user_id = account_config.get('sec_user_id')
            unique_id = account_config.get('unique_id')
            status = account_config.get('status', 'active')

            if not sec_user_id:
                logger.warning(f"❌ 账号 {i} 缺少 sec_user_id，跳过")
                continue

            # 检查账号是否已存在
            session = db.get_session()
            existing = session.query(TargetAccount).filter_by(
                sec_user_id=sec_user_id
            ).first()

            if existing:
                logger.info(f"ℹ️  账号 {i} 已存在: {account_name}，跳过")
                session.close()
                continue

            session.close()

            # 创建账号
            db.create_target_account(
                sec_user_id=sec_user_id,
                account_name=account_name,
                account_id=unique_id,
                homepage_url=f"https://www.douyin.com/user/{sec_user_id}",
                priority=i,
                tags=None
            )

            logger.info(f"✓ 导入账号 {i}: {account_name}")
            success_count += 1

        except Exception as e:
            logger.error(f"❌ 导入账号 {i} 失败: {e}")

    logger.info("=" * 70)
    logger.info(f"✓ 导入完成: {success_count}/{len(accounts)} 个账号")

    return success_count > 0


def main():
    """主函数"""
    logger.info("=" * 70)
    logger.info("DY-Interaction 配置初始化")
    logger.info("=" * 70)

    # 加载配置
    accounts = load_accounts_from_config()
    if not accounts:
        logger.error("❌ 无法加载账号配置")
        return 1

    # 导入到数据库
    if import_accounts_to_db(accounts):
        logger.info("\n✅ 初始化完成！")
        logger.info("\n下一步:")
        logger.info("  1. 运行历史爬虫: python programs/run_history_crawler.py")
        logger.info("  2. 启动长期自动化: python programs/run_long_term_automation.py")
        logger.info("  3. 启动实时自动化: python programs/run_realtime_automation.py")
        return 0
    else:
        logger.error("❌ 初始化失败")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
