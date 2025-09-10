#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Canvas考试环境预处理主脚本
执行课程设置和邮件发送功能
"""

import asyncio
import sys
from pathlib import Path
from argparse import ArgumentParser
# 添加当前目录到Python路径，确保能正确导入模块
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 导入本地模块
from setup_courses_with_mcp import run_with_args  as setup_courses_main
from update_dates import update_config_dates
# from send_exam_notification_smtp import main as send_email_main

async def main(agent_workspace=None, launch_time=None):
    """主函数"""
    try:
        print("🚀 开始执行Canvas考试环境预处理...")
        
        # Update course configuration dates to next day
        config_path = current_dir.parent / "files" / "course_config.json"
        print(f"📅 更新配置文件中的日期: {config_path}")
        update_config_dates(str(config_path))
        
        await setup_courses_main( agent_workspace=agent_workspace)
        
        
        print("\n🎉 Canvas考试环境预处理完成！")
        
    except Exception as e:
        print(f"❌ 预处理过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    # 运行异步主函数
    asyncio.run(main(agent_workspace=args.agent_workspace, launch_time=args.launch_time))


