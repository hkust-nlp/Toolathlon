#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Canvas考试环境预处理主脚本
执行课程设置和邮件注入功能
"""

import asyncio
import sys
from pathlib import Path
from argparse import ArgumentParser
# 添加当前目录到Python路径，确保能正确导入模块
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 导入本地模块
from setup_courses_with_mcp import main as setup_courses_main
from send_exam_notification_smtp import inject_exam_emails_from_config
from datetime import datetime

async def main(agent_workspace=None, launch_time=None):
    """主函数"""
    try:

        
        print("🚀 开始执行Canvas考试环境预处理...")

        # # 0. 删除课程
        # print("\n📚 步骤0: 删除课程...")
        # await setup_courses_main(delete=True, agent_workspace=agent_workspace)
        
        # 1. 创建课程
        print("\n📚 步骤1: 创建课程...")
        await setup_courses_main(agent_workspace=agent_workspace)
        
        # 2. 发布课程
        print("\n📢 步骤2: 发布课程...")
        # 调用publish模式，传递agent_workspace参数
        await setup_courses_main(publish=True, agent_workspace=agent_workspace)
        
        # 3. 注入考试通知邮件
        print("\n📧 步骤3: 注入考试通知邮件...")
        # 设置邮件时间为2024年12月1日上午10点（期末准备期间）
        email_time = datetime(2025, 1, 1, 10, 0, 0)
        email_timestamp = email_time.timestamp()
        print(f"⏰ 邮件时间设置为: {email_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 配置文件路径
        config_file = Path(__file__).parent.parent / 'files' / 'email_config.json'
        
        # 注入邮件到收件箱
        email_success = inject_exam_emails_from_config(str(config_file), email_timestamp, clear_inbox=True, add_distractions=True)
        if not email_success:
            print("⚠️ 邮件注入失败，但继续执行后续步骤")
        else:
            print("✅ 考试通知邮件注入成功")
        
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


