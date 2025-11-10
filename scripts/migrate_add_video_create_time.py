#!/usr/bin/env python3
"""
数据库迁移脚本：为 Comment 表添加 video_create_time 字段
用途：记录视频发布时间，用于任务优先级判断
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager
from src.database.models import Base, Comment
from sqlalchemy import text

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate():
    """执行迁移"""
    logger.info("=" * 70)
    logger.info("开始数据库迁移：添加 video_create_time 字段")
    logger.info("=" * 70)

    try:
        # 初始化数据库
        db = DatabaseManager()

        # 使用 SQLAlchemy 的 DDL 功能添加字段
        # 注意：SQLite 有限的 ALTER TABLE 支持，但添加列是支持的
        with db.engine.connect() as conn:
            # 检查字段是否已存在
            result = conn.execute(
                text("PRAGMA table_info(comments)")
            )
            columns = [row[1] for row in result]

            if 'video_create_time' in columns:
                logger.info("✓ video_create_time 字段已存在，无需迁移")
                return

            # 添加新字段
            logger.info("正在添加 video_create_time 字段...")
            conn.execute(
                text("ALTER TABLE comments ADD COLUMN video_create_time DATETIME")
            )
            conn.commit()

            logger.info("✓ video_create_time 字段添加成功")

            # 创建索引
            logger.info("正在创建索引...")
            try:
                conn.execute(
                    text("CREATE INDEX IF NOT EXISTS idx_video_create_time ON comments(video_create_time)")
                )
                conn.commit()
                logger.info("✓ 索引创建成功")
            except Exception as e:
                logger.warning(f"⚠ 索引创建失败（可能已存在）: {e}")

        logger.info("\n" + "=" * 70)
        logger.info("✓ 数据库迁移完成")
        logger.info("=" * 70)
        logger.info("\n📌 下一步:")
        logger.info("  1. 运行 python programs/run_history_crawler.py 重新爬取视频")
        logger.info("  2. 新爬取的评论将包含 video_create_time 字段")
        logger.info("  3. 近3个月的视频评论将自动设置为高优先级")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit_code = migrate()
    sys.exit(exit_code)
