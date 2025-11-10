"""
改进的监控爬虫 - 基于时间戳的增量监控

相比旧方案的改进：
1. 监控最近发布的视频（而不是评论最多的）
2. 使用评论时间戳进行增量对比
3. 支持分页获取所有新评论
4. 按 comment_id 去重（更准确）
"""

import logging
from datetime import datetime, timedelta
from src.database.models import Comment, NewComment
from src.database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class ImprovedMonitorCrawler:
    """改进的监控爬虫 - 基于时间戳"""

    def __init__(self, db_manager, api_client):
        """初始化监控爬虫

        Args:
            db_manager: 数据库管理器
            api_client: API 客户端
        """
        self.db = db_manager
        self.api = api_client

    def monitor_incremental(self, target_account, days_back=30, video_limit=20):
        """增量监控新评论（基于时间戳）

        Args:
            target_account: 目标账号对象
            days_back: 监控最近N天的视频（默认30天）
            video_limit: 最多监控多少个视频（默认20）

        Returns:
            {
                'account_id': int,
                'new_comments_count': int,
                'videos_checked': int,
                'status': 'success' or 'failed',
                'error': 错误信息（如有）
            }
        """
        session = self.db.get_session()
        try:
            logger.info(f"开始增量监控账号 {target_account.account_id}")

            # 步骤1: 获取最近的视频（而不是评论最多的）
            logger.info(f"  [1/3] 获取最近 {days_back} 天的视频（最多{video_limit}个）...")
            recent_videos = self.get_recent_videos(
                target_account,
                days_back=days_back,
                limit=video_limit
            )

            if not recent_videos:
                logger.warning(f"  [!] 未找到最近的视频")
                return {
                    'account_id': target_account.id,
                    'new_comments_count': 0,
                    'videos_checked': 0,
                    'status': 'success'
                }

            logger.info(f"    找到 {len(recent_videos)} 个最近的视频")

            # 步骤2: 获取每个视频的最后处理时间
            logger.info(f"  [2/3] 获取每个视频的最后处理时间...")
            video_last_times = {}
            for video in recent_videos:
                video_id = video.get('video_id')
                if not video_id:
                    continue

                # 查询该视频最新的评论时间
                last_comment = session.query(Comment)\
                    .filter_by(
                        target_account_id=target_account.id,
                        video_id=video_id
                    )\
                    .order_by(Comment.created_at.desc())\
                    .first()

                if last_comment and last_comment.created_at:
                    video_last_times[video_id] = last_comment.created_at
                else:
                    # 如果没有历史评论，设为很久以前
                    video_last_times[video_id] = datetime(2020, 1, 1)

                logger.debug(f"    视频 {video_id[:20]}... 最后处理时间: {video_last_times[video_id]}")

            # 步骤3: 检查新增评论
            logger.info(f"  [3/3] 检查新增评论...")
            new_comments_count = 0
            videos_checked = 0

            for video in recent_videos:
                video_id = video.get('video_id')
                if not video_id or video_id not in video_last_times:
                    continue

                videos_checked += 1
                last_time = video_last_times[video_id]

                try:
                    # 获取该视频的所有评论（分页）
                    cursor = 0
                    has_more = True
                    page = 0

                    while has_more and page < 10:  # 最多10页，避免无限循环
                        page += 1
                        logger.debug(f"      获取视频 {video_id[:20]}... 的评论（第{page}页）...")

                        comments_data = self.api.get_video_comments(
                            video_id=video_id,
                            cursor=cursor,
                            count=20  # 每页20条
                        )

                        if not comments_data or 'comments' not in comments_data:
                            break

                        comments = comments_data.get('comments', [])
                        has_more = comments_data.get('has_more', False)
                        cursor = comments_data.get('cursor', 0)

                        # 检查每条评论
                        for comment in comments:
                            comment_id = comment.get('cid')
                            comment_time = comment.get('create_time')

                            if not comment_id:
                                continue

                            # 如果评论时间早于最后处理时间，跳过
                            if comment_time and comment_time <= last_time.timestamp():
                                logger.debug(f"        评论 {comment_id} 在最后处理时间之前，停止")
                                has_more = False  # 停止分页
                                break

                            # 检查是否已在历史评论中（按comment_id）
                            existing_in_history = session.query(Comment).filter_by(
                                target_account_id=target_account.id,
                                comment_id=comment_id
                            ).first()

                            if existing_in_history:
                                logger.debug(f"        评论 {comment_id} 已在历史中，跳过")
                                continue

                            # 检查是否已在新评论表中
                            existing_in_new = session.query(NewComment).filter_by(
                                target_account_id=target_account.id,
                                comment_id=comment_id
                            ).first()

                            if existing_in_new:
                                logger.debug(f"        评论 {comment_id} 已在新评论表中，跳过")
                                continue

                            # 添加为新评论
                            new_comment = NewComment(
                                target_account_id=target_account.id,
                                video_id=video_id,
                                comment_id=comment_id,
                                comment_user_id=comment.get('user', {}).get('uid', ''),
                                comment_user_name=comment.get('user', {}).get('nickname', ''),
                                comment_text=comment.get('text', ''),
                                discovered_at=datetime.now()
                            )
                            session.add(new_comment)
                            new_comments_count += 1

                            logger.debug(f"        ✓ 新评论: {comment.get('user', {}).get('nickname', '')} - {comment.get('text', '')[:30]}...")

                except Exception as e:
                    logger.warning(f"    [!] 检查视频 {video_id} 失败: {e}")
                    continue

            session.commit()

            logger.info(f"✓ 监控完成: 检查 {videos_checked} 个视频，发现 {new_comments_count} 条新增评论")

            return {
                'account_id': target_account.id,
                'new_comments_count': new_comments_count,
                'videos_checked': videos_checked,
                'status': 'success'
            }

        except Exception as e:
            session.rollback()
            logger.error(f"✗ 监控失败: {e}")
            return {
                'account_id': target_account.id,
                'new_comments_count': 0,
                'videos_checked': 0,
                'status': 'failed',
                'error': str(e)
            }
        finally:
            session.close()

    def get_recent_videos(self, target_account, days_back=30, limit=20):
        """获取最近发布的视频

        Args:
            target_account: 目标账号
            days_back: 最近N天
            limit: 最多返回多少个

        Returns:
            视频列表
        """
        try:
            # 从API获取用户视频
            videos = self.api.get_user_videos(
                sec_user_id=target_account.sec_user_id
            )

            if not videos:
                return []

            # 计算时间阈值
            time_threshold = datetime.now() - timedelta(days=days_back)
            timestamp_threshold = time_threshold.timestamp()

            # 过滤最近的视频
            recent_videos = []
            for video in videos:
                create_time = video.get('create_time', 0)
                if create_time >= timestamp_threshold:
                    recent_videos.append(video)

            # 按时间排序（最新的在前）
            recent_videos.sort(key=lambda x: x.get('create_time', 0), reverse=True)

            return recent_videos[:limit]

        except Exception as e:
            logger.error(f"获取最近视频失败: {e}")
            return []
