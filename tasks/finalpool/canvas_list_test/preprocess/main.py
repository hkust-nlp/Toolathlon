#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Canvas考试环境预处理主脚本
执行课程设置和邮件发送功能
"""

import asyncio
import sys
import json
import random
from pathlib import Path
from argparse import ArgumentParser
from datetime import datetime, timedelta
# 添加当前目录到Python路径，确保能正确导入模块
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 导入本地模块
from setup_courses_with_mcp import run_with_args  as setup_courses_main
from extract_quiz_info import parse_quiz_data, parse_assign_data
# from send_exam_notification_smtp import main as send_email_main

def update_course_due_dates():
    """更新course_config.json中的due_at时间为当前时间后一周左右"""
    try:
        # 获取course_config.json文件路径
        config_file_path = current_dir.parent / 'files' / 'course_config.json'
        
        print(f"📅 开始更新课程截止时间...")
        print(f"📁 配置文件路径: {config_file_path}")
        
        # 检查文件是否存在
        if not config_file_path.exists():
            print(f"❌ 错误: 配置文件不存在 - {config_file_path}")
            return False
        
        # 创建备份文件
        backup_path = config_file_path.with_suffix('.json.backup')
        with open(config_file_path, 'r', encoding='utf-8') as src, \
             open(backup_path, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
        print(f"💾 已创建备份文件: {backup_path}")
        
        # 读取现有配置文件
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # 获取当前时间
        current_time = datetime.now()
        print(f"⏰ 当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        updated_courses = 0
        
        # 遍历所有课程
        for course in config_data.get('courses', []):
            course_name = course.get('name', 'Unknown')
            course_code = course.get('course_code', 'Unknown')
            
            # 为每个课程生成随机的截止时间（7-14天后）
            base_days = 7
            random_days = random.randint(0, 7)  # 0-7天的随机偏移
            random_hours = random.randint(0, 23)  # 0-23小时的随机偏移
            
            due_date = current_time + timedelta(days=base_days + random_days, hours=random_hours)
            # 设置为当天的23:59:00
            due_date = due_date.replace(hour=23, minute=59, second=0, microsecond=0)
            due_date_str = due_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            print(f"📚 更新课程 {course_code} ({course_name}):")
            
            # 更新测验截止时间
            if 'quiz' in course and course['quiz']:
                old_quiz_due = course['quiz'].get('due_at', 'N/A')
                course['quiz']['due_at'] = due_date_str
                print(f"  📝 测验截止时间: {old_quiz_due} → {due_date_str}")
            
            # 更新作业截止时间
            if 'assignment' in course and course['assignment']:
                old_assignment_due = course['assignment'].get('due_at', 'N/A')
                # 作业截止时间比测验晚1-3天
                assignment_days_offset = random.randint(1, 3)
                assignment_due_date = due_date + timedelta(days=assignment_days_offset)
                assignment_due_date_str = assignment_due_date.strftime('%Y-%m-%dT%H:%M:%SZ')
                course['assignment']['due_at'] = assignment_due_date_str
                print(f"  📋 作业截止时间: {old_assignment_due} → {assignment_due_date_str}")
            
            updated_courses += 1
        
        # 将更新后的数据写回文件
        with open(config_file_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 成功更新 {updated_courses} 个课程的截止时间")
        print(f"💾 配置文件已保存: {config_file_path}")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ 错误: 找不到配置文件 {config_file_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ 错误: JSON文件格式错误 - {e}")
        return False
    except Exception as e:
        print(f"❌ 更新截止时间时发生错误: {e}")
        return False

def update_csv_files():
    """更新测验和作业信息的CSV文件"""
    try:
        # 获取course_config.json文件路径
        config_file_path = current_dir.parent / 'files' / 'course_config.json'
        
        # 使用相对路径的groundtruth_workspace路径
        groundtruth_path = current_dir.parent / 'groundtruth_workspace'
        quiz_csv_path = groundtruth_path / 'quiz_info.csv'
        assignment_csv_path = groundtruth_path / 'assignment_info.csv'
        
        print(f"📝 开始更新CSV文件...")
        print(f"📁 配置文件路径: {config_file_path}")
        print(f"📍 固定输出目录: {groundtruth_path}")
        print(f"📊 测验CSV输出路径: {quiz_csv_path}")
        print(f"📋 作业CSV输出路径: {assignment_csv_path}")
        
        # 确保输出目录存在
        groundtruth_path.mkdir(parents=True, exist_ok=True)
        
        # 更新测验信息CSV
        print("📝 正在更新测验信息CSV...")
        quiz_count = parse_quiz_data(str(config_file_path), str(quiz_csv_path))
        print(f"✅ 成功更新测验信息，共 {quiz_count} 个测验")
        
        # 更新作业信息CSV
        print("📋 正在更新作业信息CSV...")
        assignment_count = parse_assign_data(str(config_file_path), str(assignment_csv_path))
        print(f"✅ 成功更新作业信息，共 {assignment_count} 个作业")
        
        print(f"📊 CSV文件更新完成:")
        print(f"  - 测验信息: {quiz_csv_path}")
        print(f"  - 作业信息: {assignment_csv_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ 更新CSV文件时发生错误: {e}")
        return False

async def main(agent_workspace=None, launch_time=None):
    """主函数"""
    try:
        print("🚀 开始执行Canvas考试环境预处理...")
        
        # 0. 首先更新课程配置文件中的截止时间
        print("\n📅 第1步: 更新课程截止时间")
        if not update_course_due_dates():
            print("❌ 更新截止时间失败，终止执行")
            sys.exit(1)
        
        # 1.5. 更新CSV文件
        print("\n📊 第2步: 更新测验和作业信息CSV文件")
        if not update_csv_files():
            print("❌ 更新CSV文件失败，终止执行")
            sys.exit(1)
        
        print("\n📚 第3步: 创建课程并自动发布...")
    
        # 现在课程创建时会自动发布，不需要单独的发布步骤

        # 2. 删除所有课程
        print("\n🗑️ 第4步: 删除现有课程")
        await setup_courses_main(delete=True, agent_workspace=agent_workspace)

        # 3. 创建课程并自动发布
        print("\n✨ 第5步: 创建新课程")
        await setup_courses_main(agent_workspace=agent_workspace)

        # 4. 提交作业
        print("\n📝 第6步: 提交学生作业")
        await setup_courses_main(submit_assignments=True, agent_workspace=agent_workspace)

        print("\n🎉 Canvas考试环境预处理完成！")
        print("✅ 所有课程已创建并自动发布")
        print("✅ 课程截止时间已更新为未来一周左右")
        print("✅ 测验和作业信息CSV文件已更新")
        print("✅ 学生作业已自动提交")

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


