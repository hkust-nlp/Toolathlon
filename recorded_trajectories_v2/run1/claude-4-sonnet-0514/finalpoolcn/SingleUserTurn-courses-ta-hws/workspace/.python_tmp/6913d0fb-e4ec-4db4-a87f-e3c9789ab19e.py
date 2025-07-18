# 查找与"操作系统基础"课程相关且属于第3次作业的文件
os_hw3_files = []

# 定义操作系统相关的关键词
os_keywords = ['操作系统', 'OS', '操作系统基础']

# 定义第3次作业的关键词
hw3_keywords = ['第3次', '3rd', 'hw3', 'assignment_3', '3.', '_3', 'project_3rd', 'hw第3次']

# 遍历所有文件，查找符合条件的文件
for filename in all_files:
    if filename == '学院学号对应表.xlsx':
        continue
    
    # 检查是否包含操作系统相关关键词
    has_os_keyword = any(keyword in filename for keyword in os_keywords)
    
    # 检查是否包含第3次作业相关关键词
    has_hw3_keyword = any(keyword in filename for keyword in hw3_keywords)
    
    if has_os_keyword and has_hw3_keyword:
        os_hw3_files.append(filename)

print(f"找到操作系统第3次作业文件数: {len(os_hw3_files)}")
print("文件列表:")
for i, filename in enumerate(os_hw3_files, 1):
    print(f"{i:2d}. {filename}")