#!/usr/bin/env python3
"""
快速设备配置脚本
根据 config.json 自动生成设备配置
"""

import json
import sys
from pathlib import Path


def calculate_devices(total_count, ratio="1:4"):
    """
    根据总数和比例计算设备列表
    比例 1:4 意思是：1台实时设备对应4台长期设备
    """
    # 解析比例
    realtime_unit, longterm_unit = map(int, ratio.split(':'))
    total_unit = realtime_unit + longterm_unit

    # 计算数量
    realtime_count = max(1, (total_count * realtime_unit) // total_unit)
    longterm_count = total_count - realtime_count

    # 生成设备列表
    result = {
        'longterm': [f'Device-{i+1}' for i in range(longterm_count)],
        'realtime': [f'Device-{longterm_count+i+1}' for i in range(realtime_count)]
    }

    return result


def main():
    # 读取配置
    config_path = Path('config/config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    device_config = config.get('devices', {})
    total = device_config.get('connected_count', 6)
    ratio = device_config.get('ratio', '1:4')

    devices = calculate_devices(total, ratio)

    print("=" * 70)
    print("📱 动态设备配置")
    print("=" * 70)
    print(f"总设备数: {total}")
    print(f"比例: {ratio}")
    print()
    print(f"长期设备 ({len(devices['longterm'])} 台): {', '.join(devices['longterm'])}")
    print(f"实时设备 ({len(devices['realtime'])} 台): {', '.join(devices['realtime'])}")
    print("=" * 70)
    print()

    # 更新 schedule_manager.py
    schedule_file = Path('src/scheduler/schedule_manager.py')
    content = schedule_file.read_text(encoding='utf-8')

    longterm_list = '[' + ', '.join(f"'{d}'" for d in devices['longterm']) + ']'

    # 查找并替换设备列表
    import re
    # 替换长期设备列表
    content = re.sub(
        r"devices = \[.*?Device-.*?\]",
        f"devices = {longterm_list}",
        content,
        flags=re.DOTALL
    )

    schedule_file.write_text(content, encoding='utf-8')
    print("✓ 已更新 src/scheduler/schedule_manager.py")

    # 输出下一步
    print()
    print("下一步:")
    print("  rm data/dy_interaction.db")
    print("  python programs/init_config.py")
    print()


if __name__ == '__main__':
    main()
