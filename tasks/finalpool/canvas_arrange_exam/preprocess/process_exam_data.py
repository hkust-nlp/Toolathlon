#!/usr/bin/env python3
"""
考试信息整理脚本
从course_config.json中提取考试信息，按照preprocess/result.csv的列名要求整理并写入exam_schedule.csv
"""

import json
import csv
from pathlib import Path
from datetime import datetime

def load_course_config():
    """加载课程配置文件"""
    config_file = Path(__file__).parent.parent / "files" / "course_config copy.json"
    
    if not config_file.exists():
        raise FileNotFoundError(f"课程配置文件不存在: {config_file}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_exam_info(course_data):
    """从课程数据中提取考试信息"""
    exam_records = []
    
    for course in course_data.get('courses', []):
        # 基本信息
        course_code = course.get('course_code', '')
        course_name = course.get('name', '')
        exam_time = course.get('exam_time', '')
        teacher = course.get('teacher', '')
        
        # 处理考试类型
        exam_type = course.get('exam_type', 'closed_book')
        if exam_type == 'closed_book':
            open_closed_book = 'Closed-book'
        elif exam_type == 'open_book':
            open_closed_book = 'Open-book'
        elif exam_type == 'no_exam':
            open_closed_book = 'No Exam'
        else:
            open_closed_book = exam_type.title()
        
        # 处理时长
        duration_value = course.get('duration', '')
        duration_unit = course.get('duration_unit', 'minutes')
        if duration_value and duration_unit:
            duration = f"{duration_value} {duration_unit}"
        else:
            duration = 'TBD'
        
        # 处理地点
        location = course.get('location', 'TBD')
        
        # 处理时间
        if exam_time:
            try:
                # 解析时间格式
                dt = datetime.strptime(exam_time, "%Y-%m-%d %H:%M")
                final_date = dt.strftime("%Y-%m-%d")
                time_str = dt.strftime("%H:%M")
            except ValueError:
                final_date = exam_time
                time_str = 'TBD'
        else:
            final_date = 'TBD'
            time_str = 'TBD'
        
        # 信息源（默认为Announcement）
        information_source = 'Announcement'
        
        # 课程学分
        course_credit = str(course.get('credits', 'TBD'))
        
        # 创建考试记录
        exam_record = {
            'Course Code': course_code,
            'Course Name': course_name,
            'Teacher': teacher,
            'Open-book/Closed-book': open_closed_book,
            'Final Date': final_date,
            'Time': time_str,
            'Duration': duration,
            'Location': location,
            'Information Source(Announcement/Email/Message)': information_source,
            'Course Credit': course_credit
        }
        
        exam_records.append(exam_record)
    
    return exam_records

def write_to_csv(exam_records, output_file):
    """将考试信息写入CSV文件"""
    if not exam_records:
        print("没有考试信息需要写入")
        return
    
    # 定义列名顺序（根据preprocess/result.csv）
    columns = [
        'Course Code',
        'Course Name',
        'Teacher',
        'Open-book/Closed-book',
        'Final Date',
        'Time',
        'Duration',
        'Location',
        'Information Source(Announcement/Email/Message)',
        'Course Credit'
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=columns)
        
        # 写入表头
        writer.writeheader()
        
        # 写入数据
        for record in exam_records:
            writer.writerow(record)
    
    print(f"考试信息已成功写入: {output_file}")

def main():
    """主函数"""
    try:
        print("开始处理考试信息...")
        
        # 1. 加载课程配置
        print("加载课程配置文件...")
        course_data = load_course_config()
        print(f"成功加载 {len(course_data.get('courses', []))} 门课程")
        
        # 2. 提取考试信息
        print("提取考试信息...")
        exam_records = extract_exam_info(course_data)
        print(f"提取到 {len(exam_records)} 条考试记录")
        
        # 3. 写入CSV文件
        output_file = Path(__file__).parent / "exam_schedule.csv"
        print(f"写入考试信息到: {output_file}")
        write_to_csv(exam_records, output_file)
        
        # 4. 显示统计信息
        print("\n考试信息统计:")
        print(f"总课程数: {len(course_data.get('courses', []))}")
        print(f"考试记录数: {len(exam_records)}")
        
        # 5. 显示前几条记录作为预览
        if exam_records:
            print("\n前3条考试记录预览:")
            for i, record in enumerate(exam_records[:3]):
                print(f"\n记录 {i+1}:")
                for key, value in record.items():
                    print(f"  {key}: {value}")
        
        print("\n✅ 考试信息处理完成！")
        
    except Exception as e:
        print(f"❌ 处理过程中发生错误: {str(e)}")
        raise

if __name__ == "__main__":
    main()
