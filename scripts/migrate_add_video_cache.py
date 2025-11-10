#!/usr/bin/env python3
"""
数据库迁移脚本 - 添加 video_cache 表

用法:
    python scripts/migrate_add_video_cache.py
"""

import sys
from pathlib import Path

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager
from src.database.models import Base, VideoCache
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 70)
    logger.info("数据库迁移 - 添加 video_cache 表")
    logger.info("=" * 70)

    try:
        # 初始化数据库
        db = DatabaseManager()

        # 创建表（如果不存在）
        logger.info("\n创建 video_cache 表...")
        Base.metadata.create_all(db.engine, tables=[VideoCache.__table__])
        logger.info("✓ video_cache 表创建成功")

        # 验证表是否存在
        session = db.get_session()
        try:
            # 尝试查询表
            count = session.query(VideoCache).count()
            logger.info(f"✓ 验证成功: video_cache 表当前有 {count} 条记录")
        finally:
            session.close()

        logger.info("\n" + "=" * 70)
        logger.info("✓ 迁移完成")
        logger.info("=" * 70)

        return 0

    except Exception as e:
        logger.error(f"\n✗ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
