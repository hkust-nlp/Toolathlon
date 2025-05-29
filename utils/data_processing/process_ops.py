import os
import shutil
import re

def copy_file_with_increment_advanced(source_path, target_dir=None):
    """
    复制文件，使用 copy、copy 2、copy 3 等命名规则
    
    Args:
        source_path: 源文件路径
        target_dir: 目标目录（可选），如果不指定则复制到源文件所在目录
        
    Returns:
        str: 新创建的文件路径
    """
    # 检查源文件是否存在
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"源文件不存在: {source_path}")
    
    if not os.path.isfile(source_path):
        raise ValueError(f"路径不是文件: {source_path}")
    
    # 确定目标目录
    if target_dir is None:
        target_dir = os.path.dirname(source_path)
    else:
        # 确保目标目录存在
        os.makedirs(target_dir, exist_ok=True)
    
    # 获取文件名和扩展名
    filename = os.path.basename(source_path)
    name, ext = os.path.splitext(filename)
    
    # 检查文件名是否已经包含 "copy" 或 "copy N" 模式
    # 这样可以避免生成 "test copy copy.txt" 这样的名字
    copy_pattern = r'(.+?)(?: copy(?: (\d+))?)?$'
    match = re.match(copy_pattern, name)
    if match:
        base_name = match.group(1)
    else:
        base_name = name
    
    # 如果是复制到同一目录，直接使用 copy 后缀
    if target_dir == os.path.dirname(source_path):
        new_filename = f"{base_name} copy{ext}"
        new_path = os.path.join(target_dir, new_filename)
        
        # 如果 "copy" 已存在，尝试 "copy 2", "copy 3" 等
        counter = 2
        while os.path.exists(new_path):
            new_filename = f"{base_name} copy {counter}{ext}"
            new_path = os.path.join(target_dir, new_filename)
            counter += 1
    else:
        # 如果是复制到其他目录，先尝试使用原文件名
        new_filename = filename
        new_path = os.path.join(target_dir, new_filename)
        
        # 如果目标目录已有同名文件，才添加 copy 后缀
        if os.path.exists(new_path):
            new_filename = f"{name} copy{ext}"
            new_path = os.path.join(target_dir, new_filename)
            
            counter = 2
            while os.path.exists(new_path):
                new_filename = f"{name} copy {counter}{ext}"
                new_path = os.path.join(target_dir, new_filename)
                counter += 1
    
    # 复制文件
    try:
        shutil.copy2(source_path, new_path)
        return new_path
    except Exception as e:
        raise Exception(f"复制文件时出错: {str(e)}")

# 获取下一个可用的副本名称（不实际复制）
def get_next_copy_name(file_path):
    """
    获取下一个可用的副本文件名，但不执行复制
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 下一个可用的文件名
    """
    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    name, ext = os.path.splitext(filename)
    
    new_filename = f"{name} copy{ext}"
    new_path = os.path.join(directory, new_filename)
    
    counter = 2
    while os.path.exists(new_path):
        new_filename = f"{name} copy {counter}{ext}"
        new_path = os.path.join(directory, new_filename)
        counter += 1
    
    return new_filename

# 批量复制
def copy_multiple_times(file_path, times):
    """
    多次复制同一个文件
    
    Args:
        file_path: 要复制的文件路径
        times: 复制次数
        
    Returns:
        list: 创建的所有副本路径列表
    """
    copies = []
    for i in range(times):
        new_path = copy_file_with_increment_advanced(file_path)
        copies.append(new_path)
        print(f"创建副本 {i+1}: {os.path.basename(new_path)}")
    return copies