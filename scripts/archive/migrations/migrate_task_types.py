#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迁移旧的 'history' 任务类型为 'history_recent' 或 'history_old'

背景: 系统之前有4种任务类型（realtime, history_recent, history_old, history）
应该只有3种（realtime, history_recent, history_old）

解决: 将旧的 'history' 类型任务重新分类为 history_recent 或 history_old
依据: 根据 comment_time 判断 - 3个月内为 history_recent，3个月前为 history_old
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager
from src.database.models import InteractionTask
from datetime import datetime, timedelta
from sqlalchemy import func

def migrate_history_tasks():
    """迁移旧的history任务"""
    db = DatabaseManager()

    print('='*70)
    print('📊 迁移旧的 history 任务类型')
    print('='*70)

    with db.get_session() as session:
        # 统计旧的history任务
        total_history = session.query(func.count(InteractionTask.id)).filter(
            InteractionTask.task_type == 'history'
        ).scalar() or 0

        print(f'\n发现 {total_history} 个需要迁移的 history 任务\n')

        # 获取所有history任务
        history_tasks = session.query(InteractionTask).filter(
            InteractionTask.task_type == 'history'
        ).all()

        # 定义3个月前的时间
        three_months_ago = datetime.now() - timedelta(days=90)

        recent_count = 0
        old_count = 0

        print('开始迁移...\n')

        for idx, task in enumerate(history_tasks, 1):
            if idx % 100 == 0:
                print(f'  进度: {idx}/{total_history}')

            # 根据comment_time判断应该分类为哪种
            if task.comment_time and task.comment_time >= three_months_ago:
                # 3个月内 -> history_recent
                task.task_type = 'history_recent'
                recent_count += 1
            elif task.comment_time:
                # 3个月前 -> history_old
                task.task_type = 'history_old'
                old_count += 1
            else:
                # 没有comment_time，默认分类为history_recent
                task.task_type = 'history_recent'
                recent_count += 1
                print(f'  ⚠️ 任务 #{task.id} 缺少 comment_time，默认分类为 history_recent')

        # 提交所有修改
        session.commit()

        print(f'\n✅ 迁移完成！')
        print(f'  转换为 history_recent: {recent_count} 个')
        print(f'  转换为 history_old: {old_count} 个')
        print(f'  总计: {recent_count + old_count} 个')

        # 验证迁移结果
        print(f'\n【验证迁移结果】')
        remaining_history = session.query(func.count(InteractionTask.id)).filter(
            InteractionTask.task_type == 'history'
        ).scalar() or 0

        print(f'  剩余的 history 任务: {remaining_history}')

        if remaining_history == 0:
            print(f'  ✅ 迁移成功！不再有 history 类型的任务')
        else:
            print(f'  ⚠️ 仍有 {remaining_history} 个 history 任务未迁移')

        # 显示最终的任务分布
        print(f'\n【最终任务分布】')
        realtime = session.query(func.count(InteractionTask.id)).filter(
            InteractionTask.task_type == 'realtime'
        ).scalar() or 0
        recent = session.query(func.count(InteractionTask.id)).filter(
            InteractionTask.task_type == 'history_recent'
        ).scalar() or 0
        old = session.query(func.count(InteractionTask.id)).filter(
            InteractionTask.task_type == 'history_old'
        ).scalar() or 0

        print(f'  realtime (监控新增): {realtime}')
        print(f'  history_recent (3个月内): {recent}')
        print(f'  history_old (3个月前): {old}')
        print(f'  总计: {realtime + recent + old}')

def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='迁移旧的 history 任务类型')
    parser.add_argument('--auto', action='store_true', help='自动确认迁移')
    args = parser.parse_args()

    print('\n' + '='*70)
    print('🔧 任务类型迁移工具')
    print('='*70)
    print('\n说明: 将旧的 "history" 任务类型重新分类为 "history_recent" 或 "history_old"')
    print('依据: 根据评论时间（comment_time）判断')
    print('  • 3个月内 → history_recent')
    print('  • 3个月前 → history_old')

    if args.auto:
        confirm = 'yes'
        print('\n自动模式：开始迁移...')
    else:
        confirm = input('\n确认执行迁移? (yes/no): ').strip().lower()

    if confirm == 'yes':
        migrate_history_tasks()
        print('\n' + '='*70)
        print('✅ 迁移完成！')
        print('='*70)
        print('\n后续说明:')
        print('  • 现在任务类型标准化为 3 种')
        print('  • 菜单统计将不再显示 "history" 类型')
        print('  • 自动化处理逻辑保持不变')
    else:
        print('\n已取消迁移')

if __name__ == '__main__':
    main()
