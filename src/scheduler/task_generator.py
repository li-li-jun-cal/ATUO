"""
任务生成器（从评论生成自动化任务）
基于设备的去重逻辑：允许多台设备关注同一用户
优先级规则：近3个月的视频评论为高优先级
"""

import logging
import json
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import func
from src.database.models import Comment, NewComment, InteractionTask
from src.database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class TaskGenerator:
    """根据评论数据生成自动化任务"""

    def __init__(self, db_manager):
        """初始化任务生成器

        Args:
            db_manager: 数据库管理器
        """
        self.db = db_manager
        self.max_follow_devices = self._load_max_follow_devices()

    def _load_max_follow_devices(self):
        """从配置文件加载允许的最大关注设备数"""
        try:
            config_file = Path(__file__).parent.parent.parent / 'config' / 'config.json'
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    max_devices = config.get('task_deduplication', {}).get('max_follow_devices', 3)
                    logger.info(f"✓ 加载配置: 允许 {max_devices} 台设备关注同一用户")
                    return max_devices
        except Exception as e:
            logger.warning(f"⚠ 加载配置失败，使用默认值: {e}")

        # 默认值：3台设备
        return 3

    def generate_from_history(self, target_account_id):
        """从历史评论生成'history'类型的任务

        Args:
            target_account_id: 目标账号ID

        Returns:
            生成的任务数量
        """
        session = self.db.get_session()
        try:
            # 获取未处理的评论
            unprocessed_comments = session.query(Comment)\
                .filter_by(target_account_id=target_account_id, status='new')\
                .all()

            if not unprocessed_comments:
                logger.info(f"✓ 账号 {target_account_id} 无未处理的历史评论")
                return 0

            logger.info(f"  为账号 {target_account_id} 生成 history 任务...")

            task_count = 0

            for comment in unprocessed_comments:
                # ✅ 必须有comment_unique_id才能创建任务（抖音搜索需要用户名/抖音号）
                if not comment.comment_unique_id:
                    logger.warning(
                        f"    ⊗ 跳过 {comment.comment_user_name}: 缺少 comment_unique_id（无法搜索用户）"
                    )
                    comment.status = 'processed'  # 标记为已处理，不重复警告
                    continue

                # 新逻辑：检查该用户被多少台不同设备关注过（基于设备的去重）
                user_identifier = comment.comment_unique_id or comment.comment_user_id

                # 统计该用户有多少台不同设备的completed任务（包括所有历史任务类型）
                completed_device_count = session.query(
                    func.count(func.distinct(InteractionTask.assigned_device))
                ).filter(
                    InteractionTask.target_account_id == target_account_id,
                    InteractionTask.task_type.in_(['history', 'history_old', 'history_recent']),  # 兼容旧数据
                    InteractionTask.status == 'completed',
                    InteractionTask.assigned_device.isnot(None),
                    (InteractionTask.comment_unique_id == user_identifier) |
                    (InteractionTask.comment_user_id == comment.comment_user_id)
                ).scalar() or 0

                # 检查是否还有该用户的待处理任务（pending/assigned/in_progress）
                has_pending_task = session.query(InteractionTask)\
                    .filter(
                        InteractionTask.target_account_id == target_account_id,
                        InteractionTask.task_type.in_(['history', 'history_old', 'history_recent']),  # 兼容旧数据
                        InteractionTask.status.in_(['pending', 'assigned', 'in_progress']),
                        (InteractionTask.comment_unique_id == user_identifier) |
                        (InteractionTask.comment_user_id == comment.comment_user_id)
                    )\
                    .first()

                # 判断是否可以生成新任务
                can_generate = (
                    not has_pending_task and  # 没有待处理的任务
                    (self.max_follow_devices == 0 or completed_device_count < self.max_follow_devices)  # 未达上限
                )

                if can_generate:
                    # 判断任务类型和优先级：根据视频发布时间
                    three_months_ago = datetime.now() - timedelta(days=90)

                    if comment.video_create_time and comment.video_create_time >= three_months_ago:
                        # 近3个月的视频
                        task_type = 'history_recent'
                        priority = 'high'
                        logger.debug(f"    ✓ [近期历史] {comment.comment_user_name} (视频发布于 {comment.video_create_time.strftime('%Y-%m-%d')})")
                    else:
                        # 3个月前的视频
                        task_type = 'history_old'
                        priority = 'normal'
                        logger.debug(f"    ✓ [历史旧评论] {comment.comment_user_name}")

                    task = InteractionTask(
                        target_account_id=target_account_id,
                        comment_user_id=comment.comment_user_id,
                        comment_user_name=comment.comment_user_name,
                        comment_uid=comment.comment_uid,
                        comment_unique_id=comment.comment_unique_id,
                        comment_sec_uid=comment.comment_sec_uid,
                        video_id=comment.video_id,
                        comment_time=comment.comment_time,  # 保存评论时间用于统计
                        task_type=task_type,  # history_old 或 history_recent
                        priority=priority,    # normal 或 high
                        status='pending'
                    )
                    session.add(task)
                    task_count += 1
                    logger.debug(
                        f"    ✓ 生成任务: {comment.comment_user_name} "
                        f"(已有 {completed_device_count}/{self.max_follow_devices} 台设备完成)"
                    )
                else:
                    # 记录跳过原因
                    if has_pending_task:
                        logger.debug(f"    ⊗ 跳过 {comment.comment_user_name}: 已有待处理任务")
                    else:
                        logger.debug(
                            f"    ⊗ 跳过 {comment.comment_user_name}: "
                            f"已达上限 ({completed_device_count}/{self.max_follow_devices} 台设备)"
                        )

                # 标记评论为已处理
                comment.status = 'processed'

            session.commit()
            logger.info(f"    生成 {task_count} 个 history 任务")

            return task_count

        except Exception as e:
            session.rollback()
            logger.error(f"✗ 生成 history 任务失败: {e}")
            return 0
        finally:
            session.close()

    def generate_from_realtime(self, target_account_id):
        """从新增评论生成'realtime'类型的任务

        Args:
            target_account_id: 目标账号ID

        Returns:
            生成的任务数量
        """
        session = self.db.get_session()
        try:
            # 获取新增评论
            new_comments = session.query(NewComment)\
                .filter_by(target_account_id=target_account_id)\
                .all()

            if not new_comments:
                logger.info(f"✓ 账号 {target_account_id} 无新增评论")
                return 0

            logger.info(f"  为账号 {target_account_id} 生成 realtime 任务...")

            task_count = 0

            for new_comment in new_comments:
                # ✅ 必须有comment_unique_id才能创建任务（抖音搜索需要用户名/抖音号）
                if not getattr(new_comment, 'comment_unique_id', None):
                    logger.warning(
                        f"    ⊗ 跳过 {new_comment.comment_user_name}: 缺少 comment_unique_id（无法搜索用户）"
                    )
                    continue

                # 检查是否已有该用户的任务（任何状态）
                # 使用 comment_unique_id（抖音号）或 comment_user_id 进行去重
                user_identifier = getattr(new_comment, 'comment_unique_id', None) or new_comment.comment_user_id

                existing_task = session.query(InteractionTask)\
                    .filter(
                        InteractionTask.target_account_id == target_account_id,
                        InteractionTask.task_type == 'realtime'
                    )\
                    .filter(
                        (InteractionTask.comment_unique_id == user_identifier) |
                        (InteractionTask.comment_user_id == new_comment.comment_user_id)
                    )\
                    .filter(
                        # ✅ 检查所有活跃状态：pending, assigned, in_progress, completed
                        InteractionTask.status.in_(['pending', 'assigned', 'in_progress', 'completed'])
                    )\
                    .first()

                if not existing_task:
                    task = InteractionTask(
                        target_account_id=target_account_id,
                        comment_user_id=new_comment.comment_user_id,  # sec_uid
                        comment_user_name=new_comment.comment_user_name,
                        comment_uid=getattr(new_comment, 'comment_uid', None),  # 数字ID
                        comment_unique_id=getattr(new_comment, 'comment_unique_id', None),  # 抖音号
                        video_id=new_comment.video_id,
                        comment_time=new_comment.discovered_at,  # 使用discovered_at作为评论时间
                        task_type='realtime',
                        priority='high',  # 高优先级！
                        status='pending'
                    )
                    session.add(task)
                    task_count += 1

            session.commit()
            logger.info(f"    生成 {task_count} 个 realtime 任务")

            # 将新增评论添加到Comment表（作为新的历史基线）
            # 这样下次监控时就不会重复检测这些评论了
            added_to_history = 0
            for new_comment in new_comments:
                # 检查是否已在Comment表中
                existing_in_history = session.query(Comment).filter_by(
                    target_account_id=target_account_id,
                    video_id=new_comment.video_id,
                    comment_user_id=new_comment.comment_user_id
                ).first()

                if not existing_in_history:
                    # 添加到历史表
                    from datetime import datetime
                    history_comment = Comment(
                        target_account_id=target_account_id,
                        video_id=new_comment.video_id,
                        comment_user_id=new_comment.comment_user_id,
                        comment_user_name=new_comment.comment_user_name,
                        comment_text=new_comment.comment_text,
                        comment_time=new_comment.discovered_at,
                        created_at=datetime.now(),
                        status='new'  # 标记为新增的评论
                    )
                    session.add(history_comment)
                    added_to_history += 1

            session.commit()
            logger.info(f"    已将 {added_to_history} 条新增评论添加到历史基线")

            # 清空已处理的新增评论
            session.query(NewComment).filter_by(
                target_account_id=target_account_id
            ).delete()
            session.commit()

            return task_count

        except Exception as e:
            session.rollback()
            logger.error(f"✗ 生成 realtime 任务失败: {e}")
            return 0
        finally:
            session.close()

    def generate_all_from_history(self):
        """为所有账号生成history任务

        Returns:
            {'account_id': task_count, ...}
        """
        results = {}
        target_accounts = self.db.get_target_accounts()

        for account in target_accounts:
            task_count = self.generate_from_history(account.id)
            results[account.id] = task_count

        return results

    def generate_all_from_realtime(self):
        """为所有账号生成realtime任务

        Returns:
            {'account_id': task_count, ...}
        """
        results = {}
        target_accounts = self.db.get_target_accounts()

        for account in target_accounts:
            task_count = self.generate_from_realtime(account.id)
            results[account.id] = task_count

        return results
