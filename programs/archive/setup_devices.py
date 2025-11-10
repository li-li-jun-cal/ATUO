#!/usr/bin/env python3
"""
动态设备配置脚本
根据 config.json 中的 connected_count 和比例自动计算设备分配
"""

import json
import sys
from pathlib import Path

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.scheduler.task_scheduler import TaskScheduler
from src.database.manager import DatabaseManager


def calculate_device_allocation(total_count, ratio_str="1:4"):
    """
    根据总设备数和比例计算设备分配

    Args:
        total_count: 总设备数
        ratio_str: 比例字符串，格式为 "1:4"（实时:长期）

    Returns:
        dict: {
            'realtime_count': 实时设备数,
            'longterm_count': 长期设备数,
            'devices': 设备列表
        }
    """
    # 解析比例
    parts = ratio_str.split(':')
    realtime_ratio = int(parts[0])
    longterm_ratio = int(parts[1])

    # 计算总单位数
    total_ratio = realtime_ratio + longterm_ratio

    # 计算每种设备的数量
    realtime_count = max(1, (total_count * realtime_ratio) // total_ratio)
    longterm_count = total_count - realtime_count

    # 确保至少有1台长期设备
    if longterm_count < 1:
        longterm_count = 1
        realtime_count = max(1, total_count - 1)

    print(f"✓ 设备分配计算")
    print(f"  总设备数：{total_count}")
    print(f"  比例（实时:长期）：{ratio_str}")
    print(f"  → 实时设备：{realtime_count} 台")
    print(f"  → 长期设备：{longterm_count} 台")
    print()

    # 生成设备列表
    devices = []

    # 长期设备
    for i in range(1, longterm_count + 1):
        devices.append({
            'device_id': f'Device-{i}',
            'device_name': f'设备{i}-长期',
            'assignment_type': 'long_term',
            'quota': 50
        })

    # 实时设备（从 Device-N 开始编号）
    start_idx = longterm_count + 1
    for i in range(realtime_count):
        devices.append({
            'device_id': f'Device-{start_idx + i}',
            'device_name': f'设备{start_idx + i}-实时',
            'assignment_type': 'realtime',
            'quota': 999
        })

    return {
        'realtime_count': realtime_count,
        'longterm_count': longterm_count,
        'devices': devices
    }


def load_config(config_path='config/config.json'):
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ 配置文件不存在: {config_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ 配置文件 JSON 格式错误: {e}")
        return None


def update_device_config(allocation):
    """
    更新代码中的设备配置
    """
    print("✓ 更新系统设备配置...")
    print()

    # 更新 schedule_manager.py
    schedule_mgr_path = PROJECT_ROOT / 'src/scheduler/schedule_manager.py'

    longterm_devices = [d['device_id'] for d in allocation['devices']
                       if d['assignment_type'] == 'long_term']

    longterm_str = ', '.join(f"'{d}'" for d in longterm_devices)

    with open(schedule_mgr_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换长期设备列表
    import re
    pattern = r"devices = \['Device-\d+',\s*'Device-\d+',.*?\]"
    replacement = f"devices = [{longterm_str}]"
    content = re.sub(pattern, replacement, content)

    with open(schedule_mgr_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  ✓ 更新 schedule_manager.py")

    # 更新 task_scheduler.py（通过重新初始化）
    db = DatabaseManager()
    db.init_db()

    # 清空旧的设备配置
    session = db.get_session()
    from src.database.models import DeviceAssignment
    session.query(DeviceAssignment).delete()
    session.commit()

    # 添加新的设备配置
    for device in allocation['devices']:
        assignment = DeviceAssignment(
            device_id=device['device_id'],
            device_name=device['device_name'],
            assignment_type=device['assignment_type'],
            max_daily_quota=device['quota']
        )
        session.add(assignment)

    session.commit()
    session.close()

    print(f"  ✓ 更新 task_scheduler.py")
    print()


def print_device_list(allocation):
    """打印设备列表"""
    print("=" * 70)
    print("📱 设备配置清单")
    print("=" * 70)

    print("\n🟢 长期工作设备（历史评论处理）：")
    for device in allocation['devices']:
        if device['assignment_type'] == 'long_term':
            print(f"  • {device['device_id']}: {device['device_name']} - 日配额 {device['quota']}")

    print("\n🔵 实时工作设备（新增评论处理）：")
    for device in allocation['devices']:
        if device['assignment_type'] == 'realtime':
            print(f"  • {device['device_id']}: {device['device_name']} - 日配额 无限制")

    print()
    total_quota = sum(d['quota'] for d in allocation['devices']
                     if d['assignment_type'] == 'long_term')
    print(f"📊 总日处理能力: ~{total_quota} 条评论/天")
    print("=" * 70)
    print()


def main():
    """主函数"""
    print("=" * 70)
    print("DY-Interaction 动态设备配置")
    print("=" * 70)
    print()

    # 加载配置
    config = load_config()
    if not config:
        return 1

    # 获取设备配置信息
    device_config = config.get('devices', {})
    connected_count = device_config.get('connected_count')
    ratio = device_config.get('ratio', '1:4')

    if not connected_count:
        print("❌ 配置文件中缺少 devices.connected_count 设置")
        print("   请在 config.json 中添加:")
        print('   "devices": { "connected_count": 6, "ratio": "1:4" }')
        return 1

    print(f"✓ 从配置文件读取设备信息")
    print()

    # 计算设备分配
    allocation = calculate_device_allocation(connected_count, ratio)

    # 更新配置
    try:
        update_device_config(allocation)
        print("✅ 设备配置更新成功！")
        print()
    except Exception as e:
        print(f"❌ 配置更新失败: {e}")
        return 1

    # 打印设备清单
    print_device_list(allocation)

    print("下一步:")
    print("  1. 清理旧数据库: rm data/dy_interaction.db")
    print("  2. 重新初始化: python programs/init_config.py")
    print("  3. 启动系统: python programs/run_all_in_one.py")
    print()

    return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
