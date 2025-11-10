#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评论文案管理工具

功能：
1. 从xlsx文件导入评论文案
2. 添加/删除/修改评论文案
3. 设置评论文案的权重和分类
4. 导出评论文案到xlsx
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.manager import DatabaseManager
from src.database.models import CommentTemplate


class CommentManager:
    """评论文案管理器"""

    def __init__(self):
        self.db = DatabaseManager()
        self.db.init_db()  # 确保表已创建

    def import_from_xlsx(self, xlsx_path):
        """从Excel文件导入评论文案

        Excel格式:
        | 评论内容 | 分类 | 权重 |
        |---------|------|------|
        | 评论1   | 通用 | 1    |
        | 评论2   | 赞美 | 2    |
        """
        session = self.db.get_session()
        try:
            df = pd.read_excel(xlsx_path)

            # 支持的列名变体
            content_col = None
            category_col = None
            weight_col = None

            for col in df.columns:
                if '评论' in col or 'content' in col.lower() or '内容' in col:
                    content_col = col
                elif '分类' in col or 'category' in col.lower() or '类型' in col:
                    category_col = col
                elif '权重' in col or 'weight' in col.lower():
                    weight_col = col

            if not content_col:
                print("错误: Excel文件必须包含评论内容列")
                return 0

            count = 0
            for _, row in df.iterrows():
                content = str(row[content_col]).strip()

                if not content or content == 'nan':
                    continue

                # 检查是否已存在
                existing = session.query(CommentTemplate).filter_by(content=content).first()
                if existing:
                    print(f"跳过重复: {content[:30]}...")
                    continue

                category = str(row[category_col]) if category_col and not pd.isna(row[category_col]) else '通用'
                weight = int(row[weight_col]) if weight_col and not pd.isna(row[weight_col]) else 1

                template = CommentTemplate(
                    content=content,
                    category=category,
                    weight=weight,
                    is_active=True
                )
                session.add(template)
                count += 1
                print(f"添加: {content[:30]}... (分类:{category}, 权重:{weight})")

            session.commit()
            print(f"\n✓ 成功导入 {count} 条评论文案")
            return count

        except Exception as e:
            session.rollback()
            print(f"✗ 导入失败: {e}")
            import traceback
            traceback.print_exc()
            return 0
        finally:
            session.close()

    def add_comment(self, content, category='通用', weight=1):
        """添加单条评论文案"""
        session = self.db.get_session()
        try:
            # 检查是否已存在
            existing = session.query(CommentTemplate).filter_by(content=content).first()
            if existing:
                print(f"评论已存在: {content}")
                return False

            template = CommentTemplate(
                content=content,
                category=category,
                weight=weight,
                is_active=True
            )
            session.add(template)
            session.commit()
            print(f"✓ 添加成功: {content} (ID: {template.id})")
            return True

        except Exception as e:
            session.rollback()
            print(f"✗ 添加失败: {e}")
            return False
        finally:
            session.close()

    def list_comments(self, category=None, active_only=True):
        """列出所有评论文案"""
        session = self.db.get_session()
        try:
            query = session.query(CommentTemplate)

            if active_only:
                query = query.filter_by(is_active=True)

            if category:
                query = query.filter_by(category=category)

            templates = query.order_by(CommentTemplate.weight.desc()).all()

            print("\n" + "=" * 80)
            print(f"评论文案列表 (共 {len(templates)} 条)")
            print("=" * 80)

            for t in templates:
                status = "✓" if t.is_active else "✗"
                last_used = t.last_used_at.strftime('%Y-%m-%d') if t.last_used_at else "从未使用"
                print(f"{status} [{t.id:3d}] {t.content[:50]:50s}  分类:{t.category:6s}  权重:{t.weight}  使用:{t.usage_count}次  最后:{last_used}")

            print("=" * 80)
            return templates

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            return []
        finally:
            session.close()

    def update_comment(self, comment_id, **kwargs):
        """更新评论文案"""
        session = self.db.get_session()
        try:
            template = session.query(CommentTemplate).filter_by(id=comment_id).first()

            if not template:
                print(f"✗ 未找到ID为 {comment_id} 的评论")
                return False

            for key, value in kwargs.items():
                if hasattr(template, key):
                    setattr(template, key, value)

            template.updated_at = datetime.now()
            session.commit()
            print(f"✓ 更新成功: {template.content[:30]}...")
            return True

        except Exception as e:
            session.rollback()
            print(f"✗ 更新失败: {e}")
            return False
        finally:
            session.close()

    def delete_comment(self, comment_id):
        """删除评论文案"""
        session = self.db.get_session()
        try:
            template = session.query(CommentTemplate).filter_by(id=comment_id).first()

            if not template:
                print(f"✗ 未找到ID为 {comment_id} 的评论")
                return False

            content = template.content[:30]
            session.delete(template)
            session.commit()
            print(f"✓ 删除成功: {content}...")
            return True

        except Exception as e:
            session.rollback()
            print(f"✗ 删除失败: {e}")
            return False
        finally:
            session.close()

    def export_to_xlsx(self, xlsx_path):
        """导出评论文案到Excel"""
        session = self.db.get_session()
        try:
            templates = session.query(CommentTemplate).all()

            data = []
            for t in templates:
                data.append({
                    'ID': t.id,
                    '评论内容': t.content,
                    '分类': t.category,
                    '权重': t.weight,
                    '是否启用': '是' if t.is_active else '否',
                    '使用次数': t.usage_count,
                    '最后使用': t.last_used_at.strftime('%Y-%m-%d %H:%M') if t.last_used_at else '',
                    '创建时间': t.created_at.strftime('%Y-%m-%d %H:%M')
                })

            df = pd.DataFrame(data)
            df.to_excel(xlsx_path, index=False)
            print(f"✓ 成功导出 {len(data)} 条评论到 {xlsx_path}")
            return True

        except Exception as e:
            print(f"✗ 导出失败: {e}")
            return False
        finally:
            session.close()

    def get_stats(self):
        """获取统计信息"""
        session = self.db.get_session()
        try:
            total = session.query(CommentTemplate).count()
            active = session.query(CommentTemplate).filter_by(is_active=True).count()

            from sqlalchemy import func
            categories = session.query(
                CommentTemplate.category,
                func.count(CommentTemplate.id)
            ).group_by(CommentTemplate.category).all()

            print("\n" + "=" * 60)
            print("评论文案统计")
            print("=" * 60)
            print(f"总数: {total} 条")
            print(f"启用: {active} 条")
            print(f"停用: {total - active} 条")
            print()
            print("按分类统计:")
            for category, count in categories:
                print(f"  {category}: {count} 条")
            print("=" * 60)

        except Exception as e:
            print(f"✗ 统计失败: {e}")
        finally:
            session.close()


def main():
    """命令行交互"""
    import argparse

    parser = argparse.ArgumentParser(description='评论文案管理工具')
    subparsers = parser.add_subparsers(dest='command', help='命令')

    # 导入命令
    import_parser = subparsers.add_parser('import', help='从Excel导入评论')
    import_parser.add_argument('file', help='Excel文件路径')

    # 添加命令
    add_parser = subparsers.add_parser('add', help='添加评论')
    add_parser.add_argument('content', help='评论内容')
    add_parser.add_argument('--category', default='通用', help='分类')
    add_parser.add_argument('--weight', type=int, default=1, help='权重')

    # 列表命令
    list_parser = subparsers.add_parser('list', help='列出评论')
    list_parser.add_argument('--category', help='按分类筛选')
    list_parser.add_argument('--all', action='store_true', help='包括已停用的')

    # 更新命令
    update_parser = subparsers.add_parser('update', help='更新评论')
    update_parser.add_argument('id', type=int, help='评论ID')
    update_parser.add_argument('--content', help='新内容')
    update_parser.add_argument('--category', help='新分类')
    update_parser.add_argument('--weight', type=int, help='新权重')
    update_parser.add_argument('--disable', action='store_true', help='停用')
    update_parser.add_argument('--enable', action='store_true', help='启用')

    # 删除命令
    delete_parser = subparsers.add_parser('delete', help='删除评论')
    delete_parser.add_argument('id', type=int, help='评论ID')

    # 导出命令
    export_parser = subparsers.add_parser('export', help='导出到Excel')
    export_parser.add_argument('file', help='导出文件路径')

    # 统计命令
    stats_parser = subparsers.add_parser('stats', help='显示统计信息')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = CommentManager()

    if args.command == 'import':
        manager.import_from_xlsx(args.file)

    elif args.command == 'add':
        manager.add_comment(args.content, args.category, args.weight)

    elif args.command == 'list':
        manager.list_comments(
            category=args.category,
            active_only=not args.all
        )

    elif args.command == 'update':
        kwargs = {}
        if args.content:
            kwargs['content'] = args.content
        if args.category:
            kwargs['category'] = args.category
        if args.weight is not None:
            kwargs['weight'] = args.weight
        if args.disable:
            kwargs['is_active'] = False
        if args.enable:
            kwargs['is_active'] = True

        manager.update_comment(args.id, **kwargs)

    elif args.command == 'delete':
        confirm = input(f"确认删除评论 ID {args.id}? (y/n): ")
        if confirm.lower() == 'y':
            manager.delete_comment(args.id)

    elif args.command == 'export':
        manager.export_to_xlsx(args.file)

    elif args.command == 'stats':
        manager.get_stats()


if __name__ == '__main__':
    main()
