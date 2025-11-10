#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化执行统计集成版本 - 包含执行报告

用法:
    python programs/run_automation_with_stats.py --mode realtime
    python programs/run_automation_with_stats.py --mode recent
    python programs/run_automation_with_stats.py --mode long_term
    python programs/run_automation_with_stats.py --mode mixed
"""

import argparse
import logging
import signal
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.stats.automation_execution_stats import AutomationExecutionStats

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 全局统计对象
execution_stats = None


def signal_handler(sig, frame):
    """处理中断信号"""
    global execution_stats

    if execution_stats:
        logger.info('\n自动化已被中断，生成最终报告...\n')
        execution_stats.finish_execution()
        execution_stats.print_report()

    logger.info('程序退出')
    sys.exit(0)


def run_automation(mode):
    """运行自动化任务"""
    global execution_stats

    # 初始化统计
    execution_stats = AutomationExecutionStats(mode)

    logger.info(f'\n启动 {execution_stats._mode_display(mode)}')
    logger.info(f'开始时间: {execution_stats.start_time.strftime("%Y-%m-%d %H:%M:%S")}')

    try:
        # 导入相应的自动化脚本
        if mode == 'realtime':
            from programs.run_realtime_automation import main as run_realtime
            run_realtime()
        elif mode == 'recent':
            # 运行近期自动化
            from programs.run_priority_automation import main as run_priority
            import sys as sys_module
            sys_module.argv = ['run_priority_automation.py', '--mode', 'recent']
            run_priority()
        elif mode == 'long_term':
            # 运行长期自动化
            from programs.run_long_term_automation import main as run_longterm
            import sys as sys_module
            sys_module.argv = ['run_long_term_automation.py', '--auto']
            run_longterm()
        elif mode == 'mixed':
            # 运行混合自动化
            from programs.run_priority_automation import main as run_priority
            import sys as sys_module
            sys_module.argv = ['run_priority_automation.py', '--mode', 'mixed']
            run_priority()

    except KeyboardInterrupt:
        logger.info('\n用户中断')
    except Exception as e:
        logger.error(f'自动化执行出错: {e}')
    finally:
        # 生成报告
        if execution_stats:
            execution_stats.finish_execution()
            execution_stats.print_report()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='自动化执行 (包含统计报告)')
    parser.add_argument(
        '--mode',
        choices=['realtime', 'recent', 'long_term', 'mixed'],
        default='realtime',
        help='自动化模式'
    )

    args = parser.parse_args()

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)

    # 运行自动化
    run_automation(args.mode)


if __name__ == '__main__':
    main()
