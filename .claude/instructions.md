# DY-Interaction 项目指引

**最后更新**: 2025-11-10

## 🚀 快速开始

这是一个抖音(Douyin)自动化交互框架。核心入口是 `main_menu.py`，它提供了菜单式界面来运行各种功能。

**详细分析见**: `CODE_ANALYSIS.md` (包含完整的文件关系、使用情况、待删除文件清单)

---

## 📋 项目结构速览

```
src/          → 核心框架 (60+ 模块)
programs/     → 可执行程序 (4个在用 + 8个未用)
scripts/      → 工具脚本 (8个在用 + 16+个未用)
main_menu.py  → 主菜单入口 (708 行)
```

---

## ✅ 正在使用的文件 (从 main_menu.py 调用)

### Programs (4个)
- `run_history_crawler.py` - 全量爬虫 (菜单选项1)
- `run_monitor_crawler.py` - 监控爬虫 (菜单选项2)
- `run_priority_automation.py` - 优先级自动化 (菜单选项3,4,6)
- `run_long_term_automation.py` - 长期自动化 (菜单选项5)

### Scripts (8个)
- `cleanup_duplicate_tasks.py` - 清理重复任务 (菜单选项14)
- `update_server_cookie.py` - 更新Cookie (菜单选项16)
- `update_cookie_pool.py` - 更新Cookie池 (菜单选项16)
- `check_devices.py` - 检查设备 (菜单选项17)
- `manage_api_servers.py` - 管理API (菜单选项12)
- `generate_tasks_from_comments.py` - 生成任务 (菜单选项13)
- `delete_tasks_without_unique_id.py` - 删除缺陷任务 (菜单选项15)

### Core Modules (src/)
- `src/database/manager.py` - 数据库操作 (43+ 导入，核心)
- `src/database/models.py` - ORM 模型 (38+ 导入，核心)
- `src/scheduler/task_scheduler.py` - 任务调度
- `src/executor/automation_executor.py` - 自动化执行
- `src/crawler/api_client.py` - API 客户端
- 其他 50+ 模块都在使用中

---

## ❌ 未使用的文件 (可以删除)

### Programs (8个 - 可立即删除)
```
batch_processor.py, configure_devices.py, init_config.py,
realtime_monitor.py, run_all_in_one.py, run_automation_with_stats.py,
run_recent_automation.py, setup_devices.py
```

### Scripts (16+ 个 - 可选择删除)

**已集成功能** (功能已合并到 main_menu.py):
- `show_stats.py`, `view_stats.py` → 已集成为 show_detailed_stats()

**一次性迁移脚本** (可删除):
- `migrate_*.py` (3个) - 数据库迁移

**数据修复脚本** (问题已修复，可删除):
- `fix_*.py`, `clean_*.py`, `add_comment_time_to_tasks.py` 等 (7个)

**其他** (可删除):
- `import_target_accounts.py`, `manage_comments.py`, `rebuild_video_cache_from_comments.py`,
  `reset_database.py`, `test_priority_automation.py`, `scripts/archive/*` 等

### 重复模块 (需要审查)
- `src/executor/douyin_operations.py` (1,639 行) vs `douyin_operations_v2.py` (1,617 行)
- `src/crawler/monitor_crawler.py` vs `improved_monitor_crawler.py`
- `src/generator/task_generator.py` vs `src/scheduler/task_generator.py`

**详细对比见** `CODE_ANALYSIS.md` - 重复和冗余模块 章节

---

## 🔴 已知问题

### 代码质量
- 敏感信息硬编码 (API密钥、账号)
- `manager.py` 数据库会话泄漏
- `device_coordinator.py` 竞态条件
- 过大模块需要拆分 (douyin_operations 1,639 行)

### 文件系统
- 日志文件未加入 .gitignore
- config.json 和 target_accounts.json 未加入 .gitignore (安全风险)

### 测试覆盖率
- 仅 3 个测试文件，覆盖率极低

**详细问题见** `CODE_ANALYSIS.md` - 关键发现和问题 章节

---

## 🛠️ 常见任务

### 添加新菜单功能
1. 修改 `main_menu.py`:
   - 在 `show_menu()` 中添加菜单项
   - 在 `main()` 中添加对应的 elif 分支
   - 使用 `run_command()` 调用程序或脚本

### 修改自动化逻辑
- 主要文件: `src/executor/automation_executor.py` 或 `src/executor/douyin_operations.py`
- 调度逻辑: `src/scheduler/task_scheduler.py`

### 修改数据模型
- 文件: `src/database/models.py`
- 之后可能需要数据库迁移脚本

### 查看/修改统计数据
- 文件: `src/stats/interaction_stats.py`
- 调用位置: `main_menu.py` 的 `show_detailed_stats()` 函数

---

## 📊 菜单选项映射表

| 选项 | 功能 | 调用文件 | 类型 |
|------|------|---------|------|
| 1 | 全量爬虫 | `programs/run_history_crawler.py` | Program |
| 2 | 监控爬虫 | `programs/run_monitor_crawler.py` | Program |
| 3 | 实时自动化 | `programs/run_priority_automation.py --mode realtime` | Program |
| 4 | 近期自动化 | `programs/run_priority_automation.py --mode recent` | Program |
| 5 | 长期自动化 | `programs/run_long_term_automation.py` | Program |
| 6 | 混合自动化 | `programs/run_priority_automation.py --mode mixed` | Program |
| 7 | 详细统计 | `main_menu.py:show_detailed_stats()` | Local |
| 8 | 设备列表 | `main_menu.py:show_devices()` | Local |
| 9 | 账号列表 | `main_menu.py:show_accounts()` | Local |
| 10 | 添加账号 | `main_menu.py:add_account()` | Local |
| 11 | 删除账号 | `main_menu.py:delete_account()` | Local |
| 12 | 管理API | `scripts/manage_api_servers.py` | Script |
| 13 | 生成任务 | `scripts/generate_tasks_from_comments.py` | Script |
| 14 | 清理重复 | `scripts/cleanup_duplicate_tasks.py` | Script |
| 15 | 删除缺陷 | `scripts/delete_tasks_without_unique_id.py` | Script |
| 16 | 更新Cookie | `scripts/update_server_cookie.py` 或 `update_cookie_pool.py` | Script |
| 17 | 检查设备 | `scripts/check_devices.py` | Script |

---

## 📌 重要文件位置

```
主菜单入口
  └─ D:\Users\zk\Desktop\DY-Interaction\main_menu.py

核心框架
  ├─ src/database/manager.py (数据库)
  ├─ src/database/models.py (数据模型)
  ├─ src/executor/automation_executor.py (执行引擎)
  ├─ src/executor/douyin_operations.py (抖音API)
  └─ src/scheduler/task_scheduler.py (任务调度)

配置文件
  ├─ config/config.json ⚠️ (含敏感信息，未加入.gitignore)
  ├─ config/target_accounts.json ⚠️ (未加入.gitignore)
  └─ config/douyin_cookie.txt ✅ (已忽略)

分析文档
  └─ CODE_ANALYSIS.md (完整分析)
```

---

## 💡 使用提示

### 第一次打开项目
1. 阅读本文件 (2 分钟)
2. 查看 `CODE_ANALYSIS.md` 的菜单选项映射表
3. 如需详细信息再查看 CODE_ANALYSIS.md 对应章节

### 快速找文件
- "我想修改爬虫逻辑" → 查看本文 "修改自动化逻辑" 或 CODE_ANALYSIS.md 快速索引
- "xx.py 有什么用？" → 查看本文 "正在使用的文件" 或 CODE_ANALYSIS.md 的菜单映射表
- "可以删除哪些文件？" → 查看本文 "未使用的文件" 或 CODE_ANALYSIS.md

### 提问时的信息
- 告诉我具体文件名或功能 (如 "监控爬虫" 而不是 "爬虫代码")
- 提供菜单选项号 (如 "菜单选项2" 而不是 "那个爬虫")
- 参考 CODE_ANALYSIS.md 中的信息

---

## 🔗 相关文档

- **CODE_ANALYSIS.md** - 完整的代码分析 (含详细关联图、问题分析、维护建议)
- **REVIEW_SUMMARY.txt** - 代码质量评分和问题列表
- **SECURITY_ISSUES.txt** - 安全问题分析

---

## 更新记录

- **2025-11-10** - 初版，基于完整代码分析生成

