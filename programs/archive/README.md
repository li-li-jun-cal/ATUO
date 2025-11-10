# 存档的程序

这些程序已被存档，原因包括：
- 实验版本，从未使用过
- 功能被更新的版本替代
- 测试程序或配置程序，不再需要

## 列表

### 未使用的程序
- **batch_processor.py** - 批处理器 (未使用)
- **realtime_monitor.py** - 实时监控 (未使用)
- **run_all_in_one.py** - 一体化运行 (未使用)

### 配置和初始化程序
- **setup_devices.py** - 设备设置 (已完成，不再需要)
- **configure_devices.py** - 设备配置 (已完成，不再需要)
- **init_config.py** - 配置初始化 (已完成，不再需要)

### 实验性程序
- **run_automation_with_stats.py** - 带统计的自动化 (实验版本)

## 活跃程序（保留在 programs/ 根目录）

当前正在使用的程序：
1. **run_history_crawler.py** - 全量爬虫
2. **run_monitor_crawler.py** - 监控爬虫
3. **run_priority_automation.py** - 优先级自动化（主要）
4. **run_long_term_automation.py** - 长期自动化
5. **run_realtime_automation.py** - 实时自动化
6. **run_recent_automation.py** - 近期自动化

## 恢复方法

如果需要恢复某个程序：

```bash
# 从 archive 恢复
mv programs/archive/<filename> programs/

# 或从 git 历史检出
git log --all --oneline -- programs/<filename>
git show <commit>:programs/<filename> > programs/<filename>
```

## 说明

这些程序被移到 archive 是 Phase 0 重构计划的一部分，目的是清理项目结构，使代码更易于维护。所有程序的历史记录都保存在 git 历史中，可随时恢复。

---
*存档日期: 2025-11-10*
*重构阶段: Phase 0.2*
