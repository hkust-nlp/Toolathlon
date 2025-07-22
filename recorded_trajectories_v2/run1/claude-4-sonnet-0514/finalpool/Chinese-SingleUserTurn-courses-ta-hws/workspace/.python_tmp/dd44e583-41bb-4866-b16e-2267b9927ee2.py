# 创建目标目录结构
target_dir = os.path.join(workspace_dir, "操作系统作业3")
c_dir = os.path.join(target_dir, "C")
rust_dir = os.path.join(target_dir, "Rust")
python_dir = os.path.join(target_dir, "Python")

# 创建目录
for dir_path in [target_dir, c_dir, rust_dir, python_dir]:
    os.makedirs(dir_path, exist_ok=True)
    print(f"创建目录: {dir_path}")

# 重命名并分类文件
renamed_files = []
errors = []

for filename in os_hw3_files:
    try:
        # 提取学生姓名（文件名开头的姓名部分）
        name_match = re.match(r'^([^-_]+)', filename)
        if not name_match:
            errors.append(f"无法提取姓名: {filename}")
            continue
        
        student_name = name_match.group(1)
        
        # 检查学生信息是否存在
        if student_name not in students_info:
            errors.append(f"找不到学生信息: {student_name} in {filename}")
            continue
        
        # 获取学生信息
        student_info = students_info[student_name]
        college = student_info['学院']
        student_id = student_info['学号']
        
        # 获取文件扩展名
        file_ext = os.path.splitext(filename)[1]
        
        # 生成新文件名
        new_filename = f"{student_name}-{college}-{student_id}-OS-HW3{file_ext}"
        
        # 确定目标目录
        if file_ext.lower() == '.c':
            dest_dir = c_dir
        elif file_ext.lower() == '.rs':
            dest_dir = rust_dir
        elif file_ext.lower() == '.py':
            dest_dir = python_dir
        else:
            errors.append(f"未知文件类型: {filename}")
            continue
        
        # 复制并重命名文件
        src_path = os.path.join(workspace_dir, filename)
        dest_path = os.path.join(dest_dir, new_filename)
        
        shutil.copy2(src_path, dest_path)
        renamed_files.append((filename, new_filename, dest_dir))
        
    except Exception as e:
        errors.append(f"处理文件 {filename} 时出错: {str(e)}")

print(f"\n成功重命名并分类的文件数: {len(renamed_files)}")
print(f"错误数: {len(errors)}")

if errors:
    print("\n错误列表:")
    for error in errors:
        print(f"  - {error}")

# 统计各类型文件数量
c_count = len([f for f in renamed_files if f[2] == c_dir])
rust_count = len([f for f in renamed_files if f[2] == rust_dir])
python_count = len([f for f in renamed_files if f[2] == python_dir])

print(f"\n文件分类统计:")
print(f"  C 文件: {c_count}")
print(f"  Rust 文件: {rust_count}")
print(f"  Python 文件: {python_count}")
print(f"  总计: {len(renamed_files)}")