#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试脚本 - 测试统一的高优先级自动化脚本
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

def test_help():
    """测试帮助信息"""
    print("=" * 70)
    print("测试1: 查看帮助信息")
    print("=" * 70)
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / 'programs' / 'run_priority_automation.py'), '--help'],
        capture_output=False
    )
    return result.returncode == 0

def test_mode_check():
    """测试模式参数检查"""
    print("\n" + "=" * 70)
    print("测试2: 模式参数检查（应该报错）")
    print("=" * 70)
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / 'programs' / 'run_priority_automation.py')],
        capture_output=True,
        text=True
    )
    print(result.stderr)
    # 应该失败（因为缺少必需参数）
    return result.returncode != 0

def main():
    print("🧪 高优先级自动化脚本 - 快速测试\n")

    # 测试1: 帮助信息
    success1 = test_help()
    print(f"\n{'✅' if success1 else '❌'} 测试1: {'通过' if success1 else '失败'}")

    # 测试2: 参数检查
    success2 = test_mode_check()
    print(f"{'✅' if success2 else '❌'} 测试2: {'通过' if success2 else '失败'}")

    print("\n" + "=" * 70)
    print("📊 测试结果汇总")
    print("=" * 70)

    all_pass = success1 and success2
    print(f"总体结果: {'✅ 全部通过' if all_pass else '❌ 部分失败'}")

    if all_pass:
        print("\n💡 下一步:")
        print("  1. 测试实时模式（需要设备）:")
        print("     python programs/run_priority_automation.py --mode realtime --auto")
        print("\n  2. 测试近期模式（需要设备）:")
        print("     python programs/run_priority_automation.py --mode recent --auto")
        print("\n  3. 测试混合模式（推荐）:")
        print("     python programs/run_priority_automation.py --mode mixed --auto")

    print("=" * 70)

if __name__ == '__main__':
    main()
