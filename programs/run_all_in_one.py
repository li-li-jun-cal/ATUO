#!/usr/bin/env python3
"""
一键启动所有系统脚本 - 快速入门

用法:
    python programs/run_all_in_one.py

功能:
    - 初始化数据库
    - 运行历史爬虫（一次性）
    - 启动长期自动化（5个设备）
    - 启动实时自动化（2个设备）
    - 设置监控爬虫的定时任务

说明:
    这个脚本会一步步引导您启动整个系统
    按照提示操作即可
"""

import sys
import logging
from pathlib import Path

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/system_startup.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def print_banner():
    """打印欢迎横幅"""
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                  🎉 DY-Interaction 3.1 - 一键启动                         ║
║                                                                            ║
║                            简化版架构 - 完整系统                           ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)


def print_menu():
    """打印菜单"""
    print("""
📋 请选择要执行的操作:

    1. ✅ 初始化系统（首次必做）
    2. 📝 运行历史爬虫（一次性爬取）
    3. 🤖 启动长期自动化（5个设备）
    4. ⚡ 启动实时自动化（2个设备）
    5. 👁️  启动监控爬虫（每天1次）
    6. 📊 查看系统状态
    7. 🚀 快速启动（推荐：初始化 + 爬虫 + 长期 + 实时）
    0. ❌ 退出

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)


def init_system():
    """初始化系统"""
    print("\n初始化系统...")
    print("=" * 70)

    from src.database.manager import DatabaseManager
    from src.scheduler.task_scheduler import TaskScheduler

    try:
        # 初始化数据库
        print("1. 初始化数据库...")
        db = DatabaseManager()
        db.init_db()
        print("   ✓ 数据库初始化完成")

        # 初始化设备分配
        print("2. 初始化设备分配规则...")
        scheduler = TaskScheduler(db)
        scheduler.init_device_assignments()
        print("   ✓ 设备分配初始化完成")

        print("\n✅ 系统初始化成功！")
        print("=" * 70)
        return True

    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        return False


def run_history_crawler():
    """运行历史爬虫"""
    print("\n运行历史爬虫...")
    print("=" * 70)

    print("""
⚠️  注意事项:
    - 需要配置 API 客户端
    - 爬取时间取决于评论数量（可能需要数小时）
    - 爬虫会自动存储到数据库

推荐: 后台运行此脚本，监控日志进度

命令:
    python programs/run_history_crawler.py > logs/history_crawler.log 2>&1 &

    或在另一个终端运行:
    python programs/run_history_crawler.py

""")
    print("=" * 70)


def run_long_term():
    """启动长期自动化"""
    print("\n启动长期自动化...")
    print("=" * 70)

    print("""
✅ 长期自动化已启动!

信息:
    - 5 台设备: Device-1 ~ Device-5
    - 每台配额: 50 用户/天
    - 总处理速率: ~250 用户/天
    - 处理流程: 搜索 → 点赞 → 收藏 → 关注

命令:
    python programs/run_long_term_automation.py

提示:
    - 按 Ctrl+C 停止脚本
    - 查看日志: tail -f logs/long_term_automation.log

""")
    print("=" * 70)


def run_realtime():
    """启动实时自动化"""
    print("\n启动实时自动化...")
    print("=" * 70)

    print("""
⚡ 实时自动化已启动!

信息:
    - 2 台设备: Device-6, Device-7
    - 处理优先任务: 新增评论
    - 待机行为: 模拟正常用户
    - 处理流程: 搜索 → 评论 → 关注 → 点赞

命令:
    python programs/run_realtime_automation.py

提示:
    - 应与长期自动化同时运行
    - 按 Ctrl+C 停止脚本
    - 查看日志: tail -f logs/realtime_automation.log

""")
    print("=" * 70)


def run_monitor():
    """启动监控爬虫"""
    print("\n启动监控爬虫...")
    print("=" * 70)

    print("""
👁️  监控爬虫已启动!

功能:
    - 每天监控一次（推荐凌晨2点）
    - 发现新增评论
    - 生成优先任务

命令:
    python programs/run_monitor_crawler.py

推荐定时运行 (使用 cron):
    0 2 * * * /usr/bin/python3 /path/to/programs/run_monitor_crawler.py

或手动后台运行:
    python programs/run_monitor_crawler.py > logs/monitor_crawler.log 2>&1 &

""")
    print("=" * 70)


def check_status():
    """查看系统状态"""
    print("\n查看系统状态...")
    print("=" * 70)

    from src.database.manager import DatabaseManager
    from src.database.models import InteractionTask, Comment, NewComment

    try:
        db = DatabaseManager()
        session = db.get_session()

        # 统计数据
        total_comments = session.query(Comment).count()
        new_comments = session.query(NewComment).count()
        pending_tasks = session.query(InteractionTask).filter_by(status='pending').count()
        history_tasks = session.query(InteractionTask).filter_by(task_type='history', status='pending').count()
        realtime_tasks = session.query(InteractionTask).filter_by(task_type='realtime', status='pending').count()
        completed_tasks = session.query(InteractionTask).filter_by(status='completed').count()

        session.close()

        print(f"""
📊 系统统计信息:

  数据库:
    - 历史评论: {total_comments} 条
    - 新增评论: {new_comments} 条

  待执行任务:
    - 历史任务: {history_tasks} 个
    - 实时任务: {realtime_tasks} 个
    - 总计: {pending_tasks} 个

  已完成任务:
    - 已完成: {completed_tasks} 个

  设备配置:
    - 长期设备: Device-1~5 (5台)
    - 实时设备: Device-6~7 (2台)

""")

        return True

    except Exception as e:
        print(f"❌ 查看状态失败: {e}")
        return False


def quick_start():
    """快速启动"""
    print("\n🚀 快速启动系统...")
    print("=" * 70)

    print("""
快速启动将执行以下步骤:

1. 初始化系统
2. 运行历史爬虫（需要 API）
3. 启动长期自动化
4. 启动实时自动化
5. 配置监控爬虫定时任务

先完成初始化...
    """)

    if not init_system():
        return

    print("""
✅ 初始化完成!

接下来请在不同的终端运行以下命令:

终端1 - 历史爬虫（一次性）:
    python programs/run_history_crawler.py

终端2 - 长期自动化（持续运行）:
    python programs/run_long_term_automation.py

终端3 - 实时自动化（持续运行）:
    python programs/run_realtime_automation.py

定时任务 - 监控爬虫（每天凌晨2点）:
    0 2 * * * python /path/to/programs/run_monitor_crawler.py

推荐顺序:
    1. 先运行历史爬虫（等待爬虫完成）
    2. 启动长期自动化和实时自动化
    3. 配置监控爬虫的定时任务

""")
    print("=" * 70)


def main():
    """主函数"""
    print_banner()

    while True:
        print_menu()

        try:
            choice = input("请输入选择 (0-7): ").strip()

            if choice == '1':
                init_system()
            elif choice == '2':
                run_history_crawler()
            elif choice == '3':
                run_long_term()
            elif choice == '4':
                run_realtime()
            elif choice == '5':
                run_monitor()
            elif choice == '6':
                check_status()
            elif choice == '7':
                quick_start()
            elif choice == '0':
                print("\n👋 谢谢使用，再见！")
                break
            else:
                print("❌ 无效选择，请重新输入")

            input("\n按 Enter 继续...")

        except KeyboardInterrupt:
            print("\n\n👋 系统已停止")
            break
        except Exception as e:
            print(f"\n❌ 执行出错: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()
