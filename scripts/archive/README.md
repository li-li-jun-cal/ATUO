# 存档的脚本

本目录包含已弃用或一次性执行过的脚本。

## 目录说明

### migrations/ - 数据库迁移脚本
这些是历史的数据库迁移脚本，已被执行过。
如果需要在新环境重新执行初始化，可以参考这些脚本。

#### 文件清单
- **migrate_add_video_cache.py** - 添加视频缓存表
- **migrate_add_video_create_time.py** - 添加视频创建时间字段
- **migrate_task_types.py** - 迁移任务类型字段

### fixes/ - 数据修复脚本
这些是过去用于修复数据的脚本，已不再需要。
保存用于审计和参考。

#### 文件清单
- **fix_task_classification.py** - 修复任务分类
- **fix_user_id_issue.py** - 修复用户ID问题
- **clean_old_assigned_tasks.py** - 清理旧的已分配任务
- **cleanup_false_realtime_tasks.py** - 清理错误的实时任务
- **convert_realtime_to_history.py** - 转换实时任务为历史任务
- **add_comment_time_to_tasks.py** - 添加评论时间字段
- **manage_comments.py** - 评论管理工具

### setup/ - 初始化脚本
这些是初始化脚本，用于第一次设置数据库或导入数据。
新部署时可能需要使用。

#### 文件清单
- **import_target_accounts.py** - 导入目标账号
- **rebuild_video_cache_from_comments.py** - 从评论重建视频缓存
- **reset_database.py** - 重置数据库

### deprecated/ - 已弃用脚本
这些脚本的功能已被集成到主程序中，不再需要使用。

#### 文件清单
- **show_stats.py** - 统计显示 (已集成到 main_menu.py)
- **view_stats.py** - 统计查看 (已集成到 main_menu.py)
- **test_priority_automation.py** - 测试程序 (已弃用)
- **cleanup_unused_scripts.py** - 清理未使用脚本 (已完成)

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

---
*存档日期: 2025-11-10*
*重构阶段: Phase 0.3*
