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
from setup_courses_with_mcp import main as setup_courses_main
from send_exam_notification_smtp import main as send_email_main

async def main(agent_workspace=None, launch_time=None):
    """主函数"""
    try:
        print("🚀 开始执行Canvas考试环境预处理...")
        
        # 1. 创建课程
        print("\n📚 步骤1: 创建课程...")
        await setup_courses_main(agent_workspace=agent_workspace)
        
        # 2. 发布课程
        print("\n📢 步骤2: 发布课程...")
        # 调用publish模式，传递agent_workspace参数
        await setup_courses_main(publish=True, agent_workspace=agent_workspace)
        
        # 3. 发送考试通知邮件
        print("\n📧 步骤3: 发送考试通知邮件...")
        send_email_main()
        
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


