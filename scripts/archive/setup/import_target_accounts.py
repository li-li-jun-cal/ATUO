#!/usr/bin/env python3
"""
导入目标账号到数据库

从 config/target_accounts.json 读取账号信息并导入到数据库
"""

import sys
import json
from pathlib import Path

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager
from src.database.models import TargetAccount

def import_target_accounts():
    """从配置文件导入目标账号"""
    print("=" * 70)
    print("📥 导入目标账号")
    print("=" * 70)

    # 读取配置文件
    config_file = PROJECT_ROOT / 'config' / 'target_accounts.json'

    if not config_file.exists():
        print(f"❌ 配置文件不存在: {config_file}")
        return 1

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
        return 1

    accounts = config.get('accounts', [])
    if not accounts:
        print("❌ 配置文件中没有账号数据")
        return 1

    print(f"\n找到 {len(accounts)} 个账号配置")
    print("-" * 70)

    # 初始化数据库
    db = DatabaseManager()
    session = db.get_session()

    try:
        imported = 0
        skipped = 0

        for idx, acc in enumerate(accounts, 1):
            account_name = acc.get('account_name', 'Unknown')
            sec_user_id = acc.get('sec_user_id')
            unique_id = acc.get('unique_id', '')
            status = acc.get('status', 'active')

            if not sec_user_id:
                print(f"  {idx}. [{account_name}] - ❌ 缺少 sec_user_id，跳过")
                skipped += 1
                continue

            # 检查是否已存在
            existing = session.query(TargetAccount).filter_by(sec_user_id=sec_user_id).first()
            if existing:
                print(f"  {idx}. [{account_name}] - ⚠️  已存在，跳过")
                skipped += 1
                continue

            # 创建新账号
            new_account = TargetAccount(
                sec_user_id=sec_user_id,
                account_name=account_name,
                account_id=unique_id,
                homepage_url=f"https://www.douyin.com/user/{sec_user_id}",
                priority=idx,
                enabled=(status == 'active')
            )

            session.add(new_account)
            print(f"  {idx}. [{account_name}] - ✓ 导入成功")
            imported += 1

        session.commit()

        print()
        print("=" * 70)
        print(f"✓ 导入完成！")
        print(f"  - 成功导入: {imported} 个")
        print(f"  - 跳过: {skipped} 个")
        print("=" * 70)

        return 0

    except Exception as e:
        session.rollback()
        print(f"\n❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        session.close()


if __name__ == '__main__':
    exit_code = import_target_accounts()
    sys.exit(exit_code)
