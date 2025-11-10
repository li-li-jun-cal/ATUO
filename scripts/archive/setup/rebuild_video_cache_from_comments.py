#!/usr/bin/env python3
"""
从Comment表重建VideoCache - 修复Top视频选择错误

问题：
  - Comment表有147个视频（2092条评论）
  - VideoCache只有23个视频
  - 导致监控爬虫从错误的数据选Top 5

解决：
  - 从Comment表统计每个视频的评论数
  - 重建VideoCache表
  - 标记真正的Top 5视频

用法:
    python scripts/rebuild_video_cache_from_comments.py
"""

import sys
from pathlib import Path
from datetime import datetime

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager
from src.database.models import Comment, VideoCache, TargetAccount
from sqlalchemy import func
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def rebuild_video_cache():
    """从Comment表重建VideoCache"""
    db = DatabaseManager()
    session = db.get_session()

    try:
        logger.info("=" * 70)
        logger.info("从Comment表重建VideoCache")
        logger.info("=" * 70)

        # 获取所有目标账号
        accounts = session.query(TargetAccount).all()

        for account in accounts:
            logger.info(f"\n处理账号: {account.account_name} (ID: {account.id})")
            logger.info("-" * 70)

            # 统计每个视频的评论数（从Comment表）
            video_stats = session.query(
                Comment.video_id,
                func.count(Comment.id).label('comment_count'),
                func.max(Comment.video_url).label('video_url'),
                func.max(Comment.video_desc).label('video_desc'),
                func.max(Comment.video_digg_count).label('digg_count'),
                func.max(Comment.video_share_count).label('share_count'),
                func.max(Comment.comment_time).label('create_time')
            ).filter_by(
                target_account_id=account.id
            ).group_by(
                Comment.video_id
            ).all()

            logger.info(f"  Comment表中有 {len(video_stats)} 个视频")

            if not video_stats:
                logger.info("  跳过（无数据）")
                continue

            # 清空该账号的VideoCache
            deleted_count = session.query(VideoCache).filter_by(
                target_account_id=account.id
            ).delete()
            logger.info(f"  清空旧VideoCache: {deleted_count} 条")

            # 重建VideoCache
            added_count = 0
            for stat in video_stats:
                cache = VideoCache(
                    target_account_id=account.id,
                    video_id=stat.video_id,
                    video_url=stat.video_url,
                    video_desc=stat.video_desc[:200] if stat.video_desc else '',
                    video_title=stat.video_desc[:100] if stat.video_desc else '',
                    comment_count=stat.comment_count,
                    digg_count=stat.digg_count or 0,
                    share_count=stat.share_count or 0,
                    create_time=stat.create_time,
                    is_top_video=False
                )
                session.add(cache)
                added_count += 1

            session.commit()
            logger.info(f"  重建VideoCache: {added_count} 条")

            # 标记Top 5视频
            logger.info(f"  标记Top 5视频...")
            top_videos = session.query(VideoCache)\
                .filter_by(target_account_id=account.id)\
                .order_by(VideoCache.comment_count.desc())\
                .limit(5)\
                .all()

            for idx, video in enumerate(top_videos, 1):
                video.is_top_video = True
                logger.info(f"    Top {idx}: {video.video_id} - {video.comment_count} 条评论")

            session.commit()
            logger.info(f"  ✓ Top 5已标记")

        logger.info("\n" + "=" * 70)
        logger.info("✓ VideoCache重建完成")
        logger.info("=" * 70)

        # 验证结果
        logger.info("\n验证结果:")
        for account in accounts:
            total = session.query(VideoCache).filter_by(target_account_id=account.id).count()
            top = session.query(VideoCache).filter_by(target_account_id=account.id, is_top_video=True).count()
            logger.info(f"  {account.account_name}: {total} 个视频, {top} 个Top视频")

        return 0

    except Exception as e:
        session.rollback()
        logger.error(f"\n✗ 重建失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        session.close()


if __name__ == '__main__':
    sys.exit(rebuild_video_cache())
