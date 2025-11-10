# 阶段 0：快速清理 - 详细实施清单

> **阶段目标**: 删除废弃代码，统一接口，为后续阶段做准备
> **工作量**: 7小时
> **时间**: 2-3天
> **优先级**: 🔴 最高 (必须完成)
> **成果**: 删除 3,917行代码，项目立即减少 35% 的冗余

---

## 📋 任务清单

### 任务 0.0: 准备工作 (0.5小时)

#### 0.0.1: 创建特性分支

```bash
cd D:\Users\zk\Desktop\ATUO-main

# 确认当前在哪个分支
git status
git branch

# 创建新分支用于重构
git checkout -b feature/refactor-v2

# 确认在新分支上
git status  # 应该显示 On branch feature/refactor-v2
```

#### 0.0.2: 备份数据库

```bash
# 备份现有的数据库 (防止意外丢失)
cp data/dy_interaction.db data/dy_interaction.db.backup.$(date +%Y%m%d_%H%M%S)

# 验证备份成功
ls -lh data/dy_interaction.db*
```

#### 0.0.3: 验证项目能正常运行

```bash
# 测试是否能启动菜单
python main_menu.py

# 测试是否能导入关键模块
python -c "from src.database.manager import DatabaseManager; print('✅ DatabaseManager 导入成功')"
python -c "from src.crawler.api_client import DouyinAPIClient; print('✅ DouyinAPIClient 导入成功')"
python -c "from src.executor.automation_executor import AutomationExecutor; print('✅ AutomationExecutor 导入成功')"
```

**预期输出**: 所有导入都成功，菜单能正常显示

---

### 任务 0.1: 删除 DouyinOperations_v2.py (1小时)

#### 0.1.1: 验证 v2 版本真的未使用

```bash
# 查找所有导入 douyin_operations_v2 的地方
grep -r "douyin_operations_v2" --include="*.py" .

# 查找所有导入 DouyinOperations_v2 的地方
grep -r "DouyinOperations_v2" --include="*.py" .

# 预期结果: 空 (没有任何导入)
```

**确认**: 如果上面两个命令都返回空，说明 v2 版本真的未使用，可以安全删除。

#### 0.1.2: 删除 v2 文件

```bash
# 删除文件
rm src/executor/douyin_operations_v2.py

# 验证删除
ls src/executor/douyin_operations*.py
# 应该只看到: douyin_operations.py (v1)
```

#### 0.1.3: 验证删除没有破坏代码

```bash
# 测试导入 v1 版本
python -c "from src.executor.douyin_operations import DouyinOperations; print('✅ DouyinOperations v1 导入成功')"

# 测试是否能启动菜单
python main_menu.py
# 选择任何选项，确保不会报错
```

#### 0.1.4: 提交删除

```bash
git add src/executor/douyin_operations_v2.py
git commit -m "[Refactor] Remove unused douyin_operations_v2.py (1,617 lines)

- Completely unused file, no imports found
- Duplicate of v1 with compilation errors
- Safe deletion with zero impact"
```

**删除收益**: 1,617 行 ✅

---

### 任务 0.2: 删除 8 个未使用的程序 (1小时)

#### 0.2.1: 创建存档目录

```bash
# 创建存档目录
mkdir -p programs/archive

# 验证创建成功
ls -la programs/ | grep archive
```

#### 0.2.2: 列出要删除的程序

这些程序完全未使用，无任何代码导入：

```
程序列表:
  1. batch_processor.py (220行)
  2. monitor_automation.py (215行)
  3. standalone_interaction_executor.py (302行)
  4. test_priority_automation.py (189行)
  5. long_term_monitor_executor.py (198行)
  6. realtime_monitor.py (167行)
  7. simple_executor.py (145行)
  8. standalone_douyin_operations.py (302行)

总计: 1,738行
```

#### 0.2.3: 验证这些程序未被使用

```bash
# 逐个验证
for file in batch_processor monitor_automation standalone_interaction_executor \
            test_priority_automation long_term_monitor_executor realtime_monitor \
            simple_executor standalone_douyin_operations; do

  # 查找导入
  count=$(grep -r "from programs.${file}" --include="*.py" . 2>/dev/null | wc -l)
  count2=$(grep -r "import ${file}" --include="*.py" . 2>/dev/null | wc -l)

  if [ $count -eq 0 ] && [ $count2 -eq 0 ]; then
    echo "✅ $file - 未使用，可删除"
  else
    echo "❌ $file - 有导入，禁止删除"
  fi
done
```

**预期结果**: 所有8个程序都显示"✅ 未使用，可删除"

#### 0.2.4: 移动到存档

```bash
# 移动到存档目录
mv programs/batch_processor.py programs/archive/
mv programs/monitor_automation.py programs/archive/
mv programs/standalone_interaction_executor.py programs/archive/
mv programs/test_priority_automation.py programs/archive/
mv programs/long_term_monitor_executor.py programs/archive/
mv programs/realtime_monitor.py programs/archive/
mv programs/simple_executor.py programs/archive/
mv programs/standalone_douyin_operations.py programs/archive/

# 验证移动成功
ls programs/       # 应该只剩下4个主程序 + archive + main_menu.py
ls programs/archive/  # 应该有8个程序
```

#### 0.2.5: 创建存档说明

```bash
cat > programs/archive/README.md << 'EOF'
# 存档的程序

这些程序已被存档，原因包括：
- 实验版本，从未使用过
- 功能被更新的版本替代
- 测试程序

## 列表

- batch_processor.py - 批处理器 (未使用)
- monitor_automation.py - 监控自动化 (未使用)
- standalone_interaction_executor.py - 独立执行器 (未使用)
- test_priority_automation.py - 测试程序 (未使用)
- long_term_monitor_executor.py - 长期监控执行器 (未使用)
- realtime_monitor.py - 实时监控 (未使用)
- simple_executor.py - 简单执行器 (未使用)
- standalone_douyin_operations.py - 独立操作器 (未使用)

## 恢复方法

如果需要恢复某个程序：

```bash
git restore programs/archive/<filename>
```

或从git历史检出：

```bash
git log --all --oneline -- programs/<filename>
git show <commit>:programs/<filename> > programs/<filename>
```
EOF

# 验证 README 创建成功
cat programs/archive/README.md
```

#### 0.2.6: 验证删除没有破坏系统

```bash
# 测试菜单是否能正常运行
python main_menu.py

# 测试导入是否正常
python -c "from programs.run_history_crawler import main; print('✅ 爬虫程序导入成功')"
python -c "from programs.run_priority_automation import main; print('✅ 优先级自动化导入成功')"
python -c "from programs.run_long_term_automation import main; print('✅ 长期自动化导入成功')"
```

#### 0.2.7: 提交删除

```bash
git add programs/
git commit -m "[Refactor] Archive 8 unused programs (1,738 lines)

Archived the following unused programs:
  - batch_processor.py
  - monitor_automation.py
  - standalone_interaction_executor.py
  - test_priority_automation.py
  - long_term_monitor_executor.py
  - realtime_monitor.py
  - simple_executor.py
  - standalone_douyin_operations.py

These programs were never used and had no imports.
Moved to programs/archive/ for historical reference."
```

**删除收益**: 1,738 行 ✅

---

### 任务 0.3: 整理 scripts 目录 (2小时)

#### 0.3.1: 创建存档子目录

```bash
# 创建分类目录
mkdir -p scripts/archive/migrations
mkdir -p scripts/archive/fixes
mkdir -p scripts/archive/setup
mkdir -p scripts/archive/deprecated

# 验证创建
ls -la scripts/archive/
```

#### 0.3.2: 分类移动脚本

**数据库迁移脚本** (一次性，已执行):

```bash
# 迁移脚本
mv scripts/migrate_add_video_cache.py scripts/archive/migrations/
mv scripts/migrate_add_video_create_time.py scripts/archive/migrations/
mv scripts/migrate_task_types.py scripts/archive/migrations/

# 验证
ls scripts/archive/migrations/
```

**数据修复脚本** (一次性，已执行):

```bash
# 修复脚本
mv scripts/fix_task_classification.py scripts/archive/fixes/
mv scripts/fix_user_id_issue.py scripts/archive/fixes/
mv scripts/clean_old_assigned_tasks.py scripts/archive/fixes/
mv scripts/cleanup_false_realtime_tasks.py scripts/archive/fixes/
mv scripts/convert_realtime_to_history.py scripts/archive/fixes/
mv scripts/add_comment_time_to_tasks.py scripts/archive/fixes/
mv scripts/manage_comments.py scripts/archive/fixes/

# 验证
ls scripts/archive/fixes/
```

**初始化脚本** (可能需要在新环境使用):

```bash
# 初始化脚本
mv scripts/import_target_accounts.py scripts/archive/setup/
mv scripts/rebuild_video_cache_from_comments.py scripts/archive/setup/
mv scripts/reset_database.py scripts/archive/setup/

# 检查是否还有其他初始化脚本
ls scripts/ | grep -E "(init|setup|create)"
# 如果有其他，也移过去
```

**已弃用脚本** (功能已集成):

```bash
# 已弃用脚本 (功能已集成到 main_menu.py)
mv scripts/show_stats.py scripts/archive/deprecated/
mv scripts/view_stats.py scripts/archive/deprecated/

# 检查是否还有其他已弃用脚本
ls scripts/ | grep -v ".py"  # 找非Python文件，不相关
```

#### 0.3.3: 创建脚本说明文档

```bash
cat > scripts/archive/README.md << 'EOF'
# 存档的脚本

本目录包含已弃用或一次性执行过的脚本。

## 目录说明

### migrations/ - 数据库迁移脚本
这些是历史的数据库迁移脚本，已被执行过。
如果需要在新环境重新执行初始化，可以参考这些脚本。

#### 文件清单
- migrate_add_video_cache.py - 添加视频缓存表
- migrate_add_video_create_time.py - 添加视频创建时间字段
- migrate_task_types.py - 迁移任务类型字段

### fixes/ - 数据修复脚本
这些是过去用于修复数据的脚本，已不再需要。
保存用于审计和参考。

#### 文件清单
- fix_task_classification.py - 修复任务分类
- fix_user_id_issue.py - 修复用户ID问题
- clean_old_assigned_tasks.py - 清理旧的已分配任务
- cleanup_false_realtime_tasks.py - 清理错误的实时任务
- convert_realtime_to_history.py - 转换实时任务为历史任务
- add_comment_time_to_tasks.py - 添加评论时间字段
- manage_comments.py - 评论管理工具

### setup/ - 初始化脚本
这些是初始化脚本，用于第一次设置数据库或导入数据。
新部署时可能需要使用。

#### 文件清单
- import_target_accounts.py - 导入目标账号
- rebuild_video_cache_from_comments.py - 从评论重建视频缓存
- reset_database.py - 重置数据库

### deprecated/ - 已弃用脚本
这些脚本的功能已被集成到主程序中，不再需要使用。

#### 文件清单
- show_stats.py - 统计显示 (已集成到 main_menu.py)
- view_stats.py - 统计查看 (已集成到 main_menu.py)

## 如何使用

### 如果需要运行迁移脚本

```bash
cd scripts/archive/migrations
python migrate_add_video_cache.py
```

### 如果需要运行初始化脚本

```bash
cd scripts/archive/setup
python import_target_accounts.py
```

### 如果需要查看修复脚本

```bash
cd scripts/archive/fixes
cat fix_task_classification.py  # 查看脚本内容
```

## 恢复到根目录

如果需要将某个脚本恢复到 scripts/ 根目录：

```bash
mv scripts/archive/<subdir>/<filename> scripts/
```
EOF

cat > scripts/README.md << 'EOF'
# Scripts - 工具脚本目录

本目录包含所有的工具脚本。

## 活跃脚本 (当前使用)

这些脚本当前正在使用，用于日常维护和管理。

### 数据清理

- **cleanup_duplicate_tasks.py** - 清理重复的交互任务
  使用场景：定期清理数据库中的重复任务
  用法：`python cleanup_duplicate_tasks.py --auto`

### Cookie 管理

- **update_server_cookie.py** - 更新服务器 Cookie
  使用场景：Cookie 过期时更新
  用法：`python update_server_cookie.py`

- **update_cookie_pool.py** - 更新 Cookie 池
  使用场景：维护多个 Cookie 备份
  用法：`python update_cookie_pool.py`

### 设备管理

- **check_devices.py** - 检查手机设备状态
  使用场景：监控设备是否在线
  用法：`python check_devices.py`

### API 管理

- **manage_api_servers.py** - 管理 API 服务器配置
  使用场景：切换 API 服务器或添加新服务器
  用法：`python manage_api_servers.py`

### 任务管理

- **generate_tasks_from_comments.py** - 从评论生成新任务
  使用场景：批量生成待执行任务
  用法：`python generate_tasks_from_comments.py --auto`

- **delete_tasks_without_unique_id.py** - 删除缺陷任务
  使用场景：数据清理
  用法：`python delete_tasks_without_unique_id.py --auto`

## 过期脚本

过期的脚本已移到 archive/ 目录，按类别分类：

- `archive/migrations/` - 数据库迁移脚本
- `archive/fixes/` - 数据修复脚本
- `archive/setup/` - 初始化脚本
- `archive/deprecated/` - 已弃用脚本

详见 `archive/README.md`
EOF

# 验证文件创建成功
cat scripts/archive/README.md | head -20
cat scripts/README.md | head -30
```

#### 0.3.4: 验证脚本目录结构

```bash
# 查看脚本目录结构
tree scripts/ -L 2  # 如果没有 tree 命令，使用 find

# 或者用 find
find scripts -type f -name "*.py" | sort
```

**预期结构**:
```
scripts/
├── 【活跃脚本】7个 .py 文件
├── archive/
│   ├── migrations/ (3个)
│   ├── fixes/ (7个)
│   ├── setup/ (3个)
│   ├── deprecated/ (2个)
│   └── README.md
├── README.md
└── (.gitkeep 如果目录为空)
```

#### 0.3.5: 验证活跃脚本还能运行

```bash
# 测试几个活跃脚本的导入
python -c "import sys; sys.path.insert(0, 'scripts'); from cleanup_duplicate_tasks import *; print('✅ cleanup_duplicate_tasks 导入成功')"
python -c "import sys; sys.path.insert(0, 'scripts'); from check_devices import *; print('✅ check_devices 导入成功')"

# 测试菜单是否能找到这些脚本
python main_menu.py
# 选择脚本菜单选项，确保脚本都还能找到
```

#### 0.3.6: 提交整理

```bash
git add scripts/
git commit -m "[Refactor] Organize scripts into archive (16+ scripts archived)

Categorized archived scripts:
  - migrations/ (3 database migration scripts)
  - fixes/ (7 data repair scripts)
  - setup/ (3 initialization scripts)
  - deprecated/ (2 deprecated scripts)

Active scripts remain in root:
  - cleanup_duplicate_tasks.py
  - update_server_cookie.py
  - update_cookie_pool.py
  - check_devices.py
  - manage_api_servers.py
  - generate_tasks_from_comments.py
  - delete_tasks_without_unique_id.py

Added README.md files for documentation."
```

**整理收益**: 更清晰的项目结构 ✅

---

### 任务 0.4: 合并 TaskGenerator (3-4小时) 🔴 关键

这是最重要的一个任务，直接影响后续的爬虫和自动化分离。

#### 0.4.1: 分析两个版本的差异

```bash
# 使用 diff 比较两个文件
diff src/generator/task_generator.py src/scheduler/task_generator.py | head -50

# 或使用 git 历史查看
git log --all --oneline -- src/generator/task_generator.py
git log --all --oneline -- src/scheduler/task_generator.py
```

#### 0.4.2: 备份现有版本

```bash
# 备份两个版本
cp src/generator/task_generator.py src/generator/task_generator.py.backup
cp src/scheduler/task_generator.py src/scheduler/task_generator.py.backup
```

#### 0.4.3: 合并代码 (详见下面的代码示例)

**新的统一版本**: `src/generator/task_generator.py`

```python
# src/generator/task_generator.py (合并后的版本)

from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session

from src.database.manager import DatabaseManager
from src.database.models import InteractionTask, Comment, NewComment
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TaskGenerator:
    """统一的任务生成器 - 合并了原来的两个版本"""

    def __init__(self, db: DatabaseManager):
        """初始化任务生成器

        Args:
            db: 数据库管理器实例
        """
        self.db = db

    # ========== 方法1: 从实时API评论生成任务 (旧版本的功能) ==========

    def generate_realtime_tasks(
        self,
        target_account_id: int,
        comments: List[Dict]
    ) -> List[InteractionTask]:
        """从API返回的评论列表生成任务 (新评论优先)

        使用场景:
            爬虫刚获取到新评论 (来自monitor_crawler)
            需要立即生成高优先级任务进行交互

        Args:
            target_account_id: 目标账号ID
            comments: API返回的评论列表
                {
                    'id': 'comment_xxx',
                    'user_id': 123,
                    'video_id': 'v_xxx',
                    'text': '评论内容',
                    'create_time': datetime
                }

        Returns:
            生成的InteractionTask列表

        Raises:
            ValueError: 如果输入参数无效
        """
        if not target_account_id:
            raise ValueError("target_account_id 不能为空")

        if not comments:
            logger.warning(f"没有评论数据要生成任务")
            return []

        tasks = []
        created_count = 0
        skipped_count = 0

        with self.db.get_session() as session:
            for comment in comments:
                try:
                    # 提取评论信息
                    comment_id = comment.get('id')
                    comment_user_id = comment.get('user_id')
                    video_id = comment.get('video_id')
                    comment_text = comment.get('text')
                    comment_time = comment.get('create_time')

                    # 校验必要字段
                    if not all([comment_id, comment_user_id, video_id]):
                        logger.warning(f"评论字段不完整，跳过: {comment}")
                        skipped_count += 1
                        continue

                    # 检查是否已经存在这条评论的任务
                    existing = session.query(InteractionTask).filter(
                        InteractionTask.comment_id == comment_id,
                        InteractionTask.target_account_id == target_account_id
                    ).first()

                    if existing:
                        logger.debug(f"任务已存在 (comment_id={comment_id}), 跳过")
                        skipped_count += 1
                        continue

                    # 创建新任务
                    task = InteractionTask(
                        target_account_id=target_account_id,
                        comment_user_id=comment_user_id,
                        video_id=video_id,
                        comment_id=comment_id,
                        comment_text=comment_text,
                        comment_time=comment_time,
                        status='pending',
                        priority='high',  # ← 新评论优先级最高！
                        task_type='realtime',  # 标记为实时任务
                        created_at=datetime.now(),
                    )
                    session.add(task)
                    tasks.append(task)
                    created_count += 1

                except Exception as e:
                    logger.error(f"生成任务失败 (comment={comment}): {e}")
                    skipped_count += 1
                    continue

            # 批量提交
            if tasks:
                session.commit()

        logger.info(f"生成了 {created_count} 个实时任务 (优先级:高), 跳过了 {skipped_count} 条")
        return tasks

    # ========== 方法2: 从历史评论生成任务 (旧版本的功能) ==========

    def generate_from_history(
        self,
        target_account_id: int,
        limit: Optional[int] = None
    ) -> List[InteractionTask]:
        """从数据库历史评论生成任务 (支持智能去重)

        使用场景:
            首次爬虫完成后，从所有历史评论生成任务
            支持去重：同一用户只生成一个任务，避免重复互动

        Args:
            target_account_id: 目标账号ID
            limit: 生成任务的最大数量 (可选)

        Returns:
            生成的InteractionTask列表

        Raises:
            ValueError: 如果target_account_id无效
        """
        if not target_account_id:
            raise ValueError("target_account_id 不能为空")

        tasks = []
        created_count = 0
        skipped_count = 0

        with self.db.get_session() as session:
            # 高级查询: 获取所有的历史评论，但排除已有任务的用户
            # 这样可以避免对同一个用户重复互动
            query = session.query(Comment).filter(
                Comment.target_account_id == target_account_id,
                # 不包含: 已经有任务的用户
                ~session.query(InteractionTask).filter(
                    InteractionTask.target_account_id == target_account_id,
                    InteractionTask.comment_user_id == Comment.comment_user_id
                ).exists()
            ).order_by(Comment.create_time.desc())  # 新评论优先

            if limit:
                query = query.limit(limit)

            comments = query.all()
            logger.info(f"从历史评论找到 {len(comments)} 条评论用于生成任务")

            for comment in comments:
                try:
                    # 检查是否已经存在
                    existing = session.query(InteractionTask).filter(
                        InteractionTask.comment_id == comment.id,
                        InteractionTask.target_account_id == target_account_id
                    ).first()

                    if existing:
                        logger.debug(f"任务已存在 (comment_id={comment.id}), 跳过")
                        skipped_count += 1
                        continue

                    # 创建新任务
                    task = InteractionTask(
                        target_account_id=target_account_id,
                        comment_user_id=comment.comment_user_id,
                        video_id=comment.video_id,
                        comment_id=comment.id,
                        comment_text=comment.text,
                        comment_time=comment.create_time,
                        status='pending',
                        priority='normal',  # ← 历史评论优先级普通
                        task_type='history',  # 标记为历史任务
                        created_at=datetime.now(),
                    )
                    session.add(task)
                    tasks.append(task)
                    created_count += 1

                except Exception as e:
                    logger.error(f"生成任务失败 (comment_id={comment.id}): {e}")
                    skipped_count += 1
                    continue

            # 批量提交
            if tasks:
                session.commit()

        logger.info(f"生成了 {created_count} 个历史任务 (优先级:普通), 跳过了 {skipped_count} 条")
        return tasks

    # ========== 通用方法 ==========

    def generate_tasks(
        self,
        target_account_id: int,
        source: str = 'history',
        **kwargs
    ) -> List[InteractionTask]:
        """通用任务生成方法 (自动选择合适的生成策略)

        Args:
            target_account_id: 目标账号ID
            source: 数据来源
                - 'realtime': 从API实时评论生成
                - 'history': 从数据库历史评论生成
            **kwargs: 传递给具体方法的参数

        Returns:
            生成的InteractionTask列表

        Raises:
            ValueError: 如果source无效
        """
        if source == 'realtime':
            comments = kwargs.get('comments', [])
            return self.generate_realtime_tasks(target_account_id, comments)
        elif source == 'history':
            limit = kwargs.get('limit')
            return self.generate_from_history(target_account_id, limit)
        else:
            raise ValueError(f"Unknown source: {source}")

    def generate_batch(
        self,
        target_accounts: List[int],
        source: str = 'history'
    ) -> Dict[int, List[InteractionTask]]:
        """批量生成任务 (为多个账号生成任务)

        Args:
            target_accounts: 目标账号ID列表
            source: 数据来源

        Returns:
            字典 {account_id: task_list}
        """
        results = {}

        for account_id in target_accounts:
            try:
                tasks = self.generate_tasks(account_id, source=source)
                results[account_id] = tasks
            except Exception as e:
                logger.error(f"为账号 {account_id} 生成任务失败: {e}")
                results[account_id] = []

        return results
```

#### 0.4.4: 更新所有导入

```bash
# 查找所有导入 scheduler.task_generator 的地方
grep -r "from src.scheduler.task_generator" --include="*.py" .

# 查找结果应该包括 (需要更新):
# - 可能的其他程序或模块
```

```bash
# 使用 sed 进行全局替换
find . -name "*.py" -type f -exec sed -i 's/from src\.scheduler\.task_generator/from src.generator.task_generator/g' {} \;

# 验证替换
grep -r "scheduler.task_generator" --include="*.py" .
# 应该返回空

# 验证新导入路径
grep -r "from src.generator.task_generator" --include="*.py" .
# 应该显示所有使用 TaskGenerator 的位置
```

#### 0.4.5: 删除旧版本

```bash
# 删除 scheduler 目录中的 task_generator.py
rm src/scheduler/task_generator.py

# 验证删除
ls src/scheduler/
# 应该不再看到 task_generator.py
```

#### 0.4.6: 验证合并没有破坏代码

```bash
# 测试导入新的 TaskGenerator
python -c "from src.generator.task_generator import TaskGenerator; print('✅ TaskGenerator 导入成功')"

# 测试是否能创建实例
python -c "
from src.generator.task_generator import TaskGenerator
from src.database.manager import DatabaseManager

db = DatabaseManager()
gen = TaskGenerator(db)
print('✅ TaskGenerator 实例创建成功')

# 验证两个方法都存在
assert hasattr(gen, 'generate_realtime_tasks'), 'generate_realtime_tasks 方法不存在'
assert hasattr(gen, 'generate_from_history'), 'generate_from_history 方法不存在'
print('✅ TaskGenerator 所有方法都存在')
"

# 测试菜单是否能正常运行
python main_menu.py
```

**预期结果**: 所有测试都通过

#### 0.4.7: 提交合并

```bash
git add src/
git commit -m "[Refactor] Merge TaskGenerator versions (delete scheduler version)

Merged two versions of TaskGenerator:
  - src/generator/task_generator.py (original)
  - src/scheduler/task_generator.py (deleted)

New unified TaskGenerator includes:
  - generate_realtime_tasks() - for API comments (high priority)
  - generate_from_history() - for database comments (normal priority)
  - generate_batch() - batch generation for multiple accounts

Updated all imports:
  - from src.scheduler.task_generator -> from src.generator.task_generator

Deleted 313 lines of duplicate code."
```

**删除收益**: 313 行 ✅

---

### 任务 0.5: 更新 .gitignore (0.5小时)

#### 0.5.1: 查看当前 .gitignore

```bash
cat .gitignore
```

#### 0.5.2: 确保包含敏感文件

```bash
cat >> .gitignore << 'EOF'

# 敏感信息 (包含API密钥、Cookie等)
config/config.json
config/target_accounts.json
config/.env
config/*_cookie*
config/*_key*
config/*.txt
EOF

# 验证
cat .gitignore | grep -A 5 "敏感信息"
```

#### 0.5.3: 确保已经忽略的文件

```bash
# 检查这些文件是否已在 gitignore 中
grep -E "logs/|__pycache__|\.venv|\.idea" .gitignore
```

如果没有，添加：

```bash
cat >> .gitignore << 'EOF'

# 日志
logs/
*.log

# 缓存
__pycache__/
*.pyc
*.pyo
*.egg-info/

# 虚拟环境
.venv/
venv/

# IDE
.idea/
.vscode/
*.swp
*.swo
*.sublime-workspace

# 操作系统
.DS_Store
Thumbs.db
EOF
```

#### 0.5.4: 提交 .gitignore 更新

```bash
git add .gitignore
git commit -m "[Security] Update .gitignore to protect sensitive files

Added rules for:
  - API configuration files
  - Cookie and key files
  - Environment variables
  - Additional logs and caches"
```

---

## ✅ 阶段 0 完成验证清单

### 总结

完成阶段 0 的所有任务后，您应该看到：

```
删除的代码:
  ✅ douyin_operations_v2.py: 1,617 行
  ✅ 8个未使用程序: 1,738 行
  ✅ TaskGenerator 重复版本: 313 行
  ✅ 脚本整理 (更清晰的结构)
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  总计: 3,668 行

代码改进:
  ✅ TaskGenerator 合并为统一版本
  ✅ .gitignore 更新，保护敏感文件
  ✅ scripts 目录分类整理

项目状态:
  ✅ 没有破坏任何现有功能
  ✅ 所有导入都更新正确
  ✅ 菜单和脚本都能正常运行
  ✅ 数据库完整，无数据丢失
```

### 验证步骤

在进入下一个阶段前，运行以下验证：

```bash
# 1. 验证项目能启动
python main_menu.py

# 2. 验证没有被删除的模块导入
python -c "from src.executor.douyin_operations_v2 import DouyinOperations" 2>&1 | grep "No module named" && echo "✅ v2版本已删除"

# 3. 验证 TaskGenerator 合并成功
python -c "
from src.generator.task_generator import TaskGenerator
from src.database.manager import DatabaseManager
db = DatabaseManager()
gen = TaskGenerator(db)
assert hasattr(gen, 'generate_realtime_tasks')
assert hasattr(gen, 'generate_from_history')
print('✅ TaskGenerator 合并成功')
"

# 4. 验证脚本能导入
python -c "import sys; sys.path.insert(0, 'scripts'); from cleanup_duplicate_tasks import *; print('✅ 活跃脚本可用')"

# 5. 检查 git 状态
git status
# 应该没有未提交的更改

# 6. 查看提交历史
git log --oneline | head -5
# 应该能看到阶段0的提交
```

### 磁盘空间节省

```bash
# 查看代码行数变化
find src programs scripts -name "*.py" | xargs wc -l | tail -1
# 应该比开始时少了 ~3,600 行
```

---

## 📝 问题排查

### 如果导入失败

```bash
# 检查语法错误
python -m py_compile src/generator/task_generator.py

# 检查导入路径
python -c "import sys; print(sys.path)"

# 验证文件存在
ls -la src/generator/task_generator.py
```

### 如果 sed 替换失败

```bash
# 手动更新导入
# 打开每个 Python 文件，查找:
#   from src.scheduler.task_generator
# 替换为:
#   from src.generator.task_generator
```

### 如果菜单无法启动

```bash
# 查看错误信息
python main_menu.py 2>&1 | head -50

# 检查是否有语法错误
python -c "from src.database.manager import DatabaseManager; print('DatabaseManager OK')"

# 逐个检查导入
python -c "
try:
    from src.database.manager import DatabaseManager
    print('✅ DatabaseManager')
except Exception as e:
    print(f'❌ DatabaseManager: {e}')

try:
    from src.generator.task_generator import TaskGenerator
    print('✅ TaskGenerator')
except Exception as e:
    print(f'❌ TaskGenerator: {e}')
"
```

---

**阶段 0 完成后，请按照 [PHASE_1_CRAWLER.md](./PHASE_1_CRAWLER.md) 继续进行阶段 1 的爬虫服务分离**

