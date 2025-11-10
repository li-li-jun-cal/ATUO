#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复任务中缺少的comment_unique_id字段

问题：自动化任务使用comment_user_id搜索用户会失败
解决：确保所有任务都有comment_unique_id（抖音号）
"""

import sys
from pathlib import Path

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager
from src.database.models import InteractionTask, Comment
from sqlalchemy import func


def analyze_tasks():
    """分析任务中的用户ID字段"""
    db = DatabaseManager()

    with db.get_session() as session:
        print("=" * 70)
        print("分析任务中的用户ID字段")
        print("=" * 70)

        # 统计总任务数
        total_tasks = session.query(func.count(InteractionTask.id)).scalar() or 0
        print(f"\n总任务数: {total_tasks}")

        # 统计有comment_unique_id的任务
        with_unique_id = session.query(func.count(InteractionTask.id)).filter(
            InteractionTask.comment_unique_id.isnot(None),
            InteractionTask.comment_unique_id != ''
        ).scalar() or 0

        # 统计缺少comment_unique_id的任务
        without_unique_id = session.query(func.count(InteractionTask.id)).filter(
            (InteractionTask.comment_unique_id.is_(None)) |
            (InteractionTask.comment_unique_id == '')
        ).scalar() or 0

        print(f"有comment_unique_id（抖音号）: {with_unique_id}")
        print(f"缺少comment_unique_id: {without_unique_id}")

        if without_unique_id > 0:
            print(f"\n⚠️ 有 {without_unique_id} 个任务缺少抖音号，无法正确搜索用户！")

            # 显示一些缺少unique_id的任务示例
            missing_tasks = session.query(InteractionTask).filter(
                (InteractionTask.comment_unique_id.is_(None)) |
                (InteractionTask.comment_unique_id == '')
            ).limit(10).all()

            print("\n缺少抖音号的任务示例:")
            for task in missing_tasks:
                print(f"  任务#{task.id}: {task.comment_user_name}")
                print(f"    comment_user_id: {task.comment_user_id}")
                print(f"    comment_uid: {task.comment_uid}")
                print(f"    comment_unique_id: {task.comment_unique_id or '(空)'}")
                print()

        return without_unique_id


def fix_missing_unique_ids():
    """尝试从Comments表补充缺失的unique_id"""
    db = DatabaseManager()

    with db.get_session() as session:
        print("\n" + "=" * 70)
        print("尝试修复缺失的comment_unique_id")
        print("=" * 70)

        # 查找缺少unique_id的任务
        missing_tasks = session.query(InteractionTask).filter(
            (InteractionTask.comment_unique_id.is_(None)) |
            (InteractionTask.comment_unique_id == '')
        ).all()

        fixed_count = 0
        failed_count = 0

        for task in missing_tasks:
            # 尝试从Comments表找到对应的评论
            comment = session.query(Comment).filter(
                Comment.comment_user_id == task.comment_user_id,
                Comment.video_id == task.video_id
            ).first()

            if comment and comment.comment_unique_id:
                # 找到了，更新任务
                task.comment_unique_id = comment.comment_unique_id

                # 同时更新其他可能缺失的字段
                if not task.comment_uid and comment.comment_uid:
                    task.comment_uid = comment.comment_uid
                if not task.comment_sec_uid and comment.comment_sec_uid:
                    task.comment_sec_uid = comment.comment_sec_uid

                fixed_count += 1
                print(f"✓ 修复任务 #{task.id}: {task.comment_user_name} -> {comment.comment_unique_id}")
            else:
                failed_count += 1
                print(f"✗ 无法修复任务 #{task.id}: {task.comment_user_name} (未找到对应评论)")

        if fixed_count > 0:
            session.commit()
            print(f"\n✓ 成功修复 {fixed_count} 个任务")

        if failed_count > 0:
            print(f"⚠️ 有 {failed_count} 个任务无法自动修复")
            print("  这些任务可能需要手动处理或重新爬取")

        return fixed_count, failed_count


def verify_fix():
    """验证修复结果"""
    db = DatabaseManager()

    with db.get_session() as session:
        print("\n" + "=" * 70)
        print("验证修复结果")
        print("=" * 70)

        # 重新统计
        total_tasks = session.query(func.count(InteractionTask.id)).scalar() or 0
        with_unique_id = session.query(func.count(InteractionTask.id)).filter(
            InteractionTask.comment_unique_id.isnot(None),
            InteractionTask.comment_unique_id != ''
        ).scalar() or 0
        without_unique_id = total_tasks - with_unique_id

        print(f"\n修复后的统计:")
        print(f"  总任务数: {total_tasks}")
        print(f"  有抖音号: {with_unique_id} ({with_unique_id/total_tasks*100:.1f}%)")
        print(f"  缺少抖音号: {without_unique_id} ({without_unique_id/total_tasks*100:.1f}%)")

        if without_unique_id == 0:
            print("\n✅ 所有任务都有抖音号了！自动化任务可以正常执行。")
        else:
            print(f"\n⚠️ 还有 {without_unique_id} 个任务缺少抖音号")
            print("建议：")
            print("  1. 重新运行历史爬虫，获取完整的用户信息")
            print("  2. 或者将这些任务标记为失败")


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='修复任务用户ID问题')
    parser.add_argument('--auto', action='store_true', help='自动确认修复')
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("修复自动化任务用户ID问题")
    print("=" * 70)
    print("\n背景：自动化任务必须使用 comment_unique_id（抖音号）来搜索用户")
    print("      使用 comment_user_id 会导致搜索失败")

    # 1. 分析现状
    missing_count = analyze_tasks()

    if missing_count == 0:
        print("\n✅ 所有任务都有正确的抖音号，无需修复")
        return

    # 2. 确认修复
    if args.auto:
        print(f"\n自动模式：准备修复 {missing_count} 个任务")
        confirm = 'yes'
    else:
        print("\n" + "=" * 70)
        confirm = input(f"确认修复 {missing_count} 个任务? (yes/no): ").strip().lower()

    if confirm != 'yes':
        print("已取消修复")
        return

    # 3. 执行修复
    fixed, failed = fix_missing_unique_ids()

    # 4. 验证结果
    verify_fix()

    print("\n" + "=" * 70)
    print("修复完成！")
    print("=" * 70)
    print("\n重要提醒：")
    print("  1. 执行器代码已修复为使用 comment_unique_id")
    print("  2. 未来生成的任务应确保包含 comment_unique_id")
    print("  3. 如果还有任务失败，检查日志中的'缺少抖音号'错误")


if __name__ == '__main__':
    main()