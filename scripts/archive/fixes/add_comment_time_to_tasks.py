"""
数据库迁移脚本: 为 InteractionTask 表添加 comment_time 字段

这个脚本会:
1. 添加 comment_time 列到 interaction_tasks 表
2. 从 comments 表中获取评论时间填充现有任务
3. 为 comment_time 字段创建索引

运行方法:
python scripts/add_comment_time_to_tasks.py
"""

import sqlite3
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.manager import DatabaseManager

def migrate():
    """执行数据库迁移"""

    print("=" * 60)
    print("📦 数据库迁移: 添加 comment_time 字段")
    print("=" * 60)

    db_path = project_root / 'data' / 'dy_interaction.db'

    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return

    print(f"✓ 数据库路径: {db_path}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 步骤1: 检查列是否已存在
        print("\n[1/4] 检查 comment_time 列是否存在...")
        cursor.execute("PRAGMA table_info(interaction_tasks)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'comment_time' in columns:
            print("  ⚠️  comment_time 列已存在,跳过创建")
        else:
            # 添加新列
            print("  ✓ 添加 comment_time 列...")
            cursor.execute("""
                ALTER TABLE interaction_tasks
                ADD COLUMN comment_time DATETIME
            """)
            conn.commit()
            print("  ✓ comment_time 列已添加")

        # 步骤2: 从 comments 表填充数据
        print("\n[2/4] 从 comments 表填充 comment_time 数据...")

        # 获取需要更新的任务数
        cursor.execute("""
            SELECT COUNT(*)
            FROM interaction_tasks t
            WHERE t.comment_time IS NULL
              AND EXISTS (
                  SELECT 1 FROM comments c
                  WHERE c.video_id = t.video_id
                    AND c.comment_user_id = t.comment_user_id
                    AND c.target_account_id = t.target_account_id
              )
        """)
        update_count = cursor.fetchone()[0]
        print(f"  ✓ 找到 {update_count} 条任务需要更新")

        if update_count > 0:
            # 执行更新
            cursor.execute("""
                UPDATE interaction_tasks
                SET comment_time = (
                    SELECT c.comment_time
                    FROM comments c
                    WHERE c.video_id = interaction_tasks.video_id
                      AND c.comment_user_id = interaction_tasks.comment_user_id
                      AND c.target_account_id = interaction_tasks.target_account_id
                    LIMIT 1
                )
                WHERE interaction_tasks.comment_time IS NULL
                  AND EXISTS (
                      SELECT 1 FROM comments c
                      WHERE c.video_id = interaction_tasks.video_id
                        AND c.comment_user_id = interaction_tasks.comment_user_id
                        AND c.target_account_id = interaction_tasks.target_account_id
                  )
            """)
            conn.commit()
            print(f"  ✓ 已更新 {cursor.rowcount} 条任务的 comment_time")

        # 步骤3: 创建索引
        print("\n[3/4] 创建 comment_time 索引...")
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_interaction_tasks_comment_time
                ON interaction_tasks(comment_time)
            """)
            conn.commit()
            print("  ✓ 索引已创建")
        except sqlite3.OperationalError as e:
            if "already exists" in str(e):
                print("  ⚠️  索引已存在,跳过")
            else:
                raise

        # 步骤4: 验证结果
        print("\n[4/4] 验证迁移结果...")

        cursor.execute("SELECT COUNT(*) FROM interaction_tasks")
        total_tasks = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM interaction_tasks WHERE comment_time IS NOT NULL")
        tasks_with_time = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM interaction_tasks WHERE comment_time IS NULL")
        tasks_without_time = cursor.fetchone()[0]

        print(f"  ✓ 任务总数: {total_tasks}")
        print(f"  ✓ 有 comment_time: {tasks_with_time}")
        print(f"  ✓ 无 comment_time: {tasks_without_time}")

        if tasks_without_time > 0:
            print(f"  ⚠️  {tasks_without_time} 条任务没有 comment_time (可能是新任务或评论已被删除)")

        print("\n" + "=" * 60)
        print("✅ 迁移完成!")
        print("=" * 60)

    except Exception as e:
        conn.rollback()
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
