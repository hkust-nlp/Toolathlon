#!/usr/bin/env python3
"""
测试 check_local.py 中的评估逻辑
主要测试空行处理和Excel格式检查的合理性
"""

import pandas as pd
import numpy as np
import tempfile
import os
from pathlib import Path
import sys

# 添加evaluation目录到path
# Correct the path to be relative to the script's location
evaluation_path = Path(__file__).parent / 'evaluation'
sys.path.append(str(evaluation_path.resolve()))
from check_local import check_excel_format, check_data_accuracy, check_local

def create_test_excel_data():
    """创建测试用的Excel数据，模拟标准格式"""
    # 标准格式数据（包含空行）
    standard_data = [
        ['Department', 'Report Period'],
        ['R&D Department', '2025-04 to 2025-06'],
        [np.nan, np.nan],  # 空行
        ['Month', 'Total Amount'],
        ['2025-04', 326.72],
        ['2025-05', 404.56],
        ['2025-06', 353.15],
        [np.nan, np.nan],  # 空行
        ['Total', np.nan],
        ['Total Amount: CNY 1084.43', 1084.43]
    ]
    
    # 没有空行的数据（紧凑格式）
    compact_data = [
        ['Department', 'Report Period'],
        ['R&D Department', '2025-04 to 2025-06'],
        ['Month', 'Total Amount'],
        ['2025-04', 326.72],
        ['2025-05', 404.56],
        ['2025-06', 353.15],
        ['Total', np.nan],
        ['Total Amount: CNY 1084.43', 1084.43]
    ]
    
    return standard_data, compact_data

def test_excel_format_with_standard_data():
    """测试标准格式（包含空行）的Excel数据"""
    print("=== 测试1: 标准格式（包含空行）===")
    standard_data, _ = create_test_excel_data()
    df = pd.DataFrame(standard_data)
    
    # The check_excel_format function expects more rows, let's align with its expectation
    # The original groundtruth has 10 rows, let's simulate that
    # The check logic expects at least 8 rows.
    # Let's align the test data to what check_excel_format expects.
    # The logic checks iloc[0], iloc[1], iloc[3], iloc[4-6], iloc[7]
    # This means it expects a fixed structure with at least 8 rows.
    
    # Let's create data that will fail and pass based on current logic
    failing_df = pd.DataFrame(df.values) # Re-index
    
    result, message = check_excel_format(failing_df)
    print(f"检查结果: {result}")
    print(f"消息: {message}")
    print(f"DataFrame形状: {failing_df.shape}")
    print("DataFrame内容:")
    print(failing_df)
    print()
    
    return result

def test_excel_format_with_compact_data():
    """测试紧凑格式（无空行）的Excel数据"""
    print("=== 测试2: 紧凑格式（无空行）===")
    _, compact_data = create_test_excel_data()
    df = pd.DataFrame(compact_data)
    
    result, message = check_excel_format(df)
    print(f"检查结果: {result}")
    print(f"消息: {message}")
    print(f"DataFrame形状: {df.shape}")
    print("DataFrame内容:")
    print(df)
    print()
    
    return result

def test_dropna_approach():
    """测试使用dropna去除空行的方法"""
    print("=== 测试3: 使用dropna去除空行 ===")
    standard_data, _ = create_test_excel_data()
    df = pd.DataFrame(standard_data)
    
    print("原始DataFrame:")
    print(df)
    print(f"原始形状: {df.shape}")
    
    # 方法1: 去除完全为空的行
    df_dropna_all = df.dropna(how='all').reset_index(drop=True)
    print("\n使用dropna(how='all').reset_index(drop=True)后:")
    print(df_dropna_all)
    print(f"新形状: {df_dropna_all.shape}")
    
    # 测试去除空行后的格式检查
    print("\n--- 测试去除空行后的格式检查 ---")
    result, message = check_excel_format(df_dropna_all)
    print(f"检查结果: {result}")
    print(f"消息: {message}")
    print()

def analyze_current_issues():
    """分析当前评估代码的问题"""
    print("=== 分析当前评估代码的问题 ===")
    
    issues = [
        "1. 硬编码行号问题：代码使用 `iloc` 对固定的行索引进行检查，这使得它对空行非常敏感。",
        "2. 空行处理：`check_excel_format` 目前无法处理包含空行的标准格式，因为它期望一个紧凑的8行DataFrame。", 
        "3. 灵活性差：任何偏离预定8行结构的格式都会导致检查失败，即使数据在语义上是正确的。"
    ]
    
    for issue in issues:
        print(issue)
    
    print("\n=== 建议的改进方案 ===")
    suggestions = [
        "1. **预处理DataFrame**：在检查之前，使用 `df.dropna(how='all').reset_index(drop=True)` 来删除所有完全为空的行并重置索引。",
        "2. **修改检查逻辑**：调整 `check_excel_format` 函数中的行索引，以匹配清理后DataFrame的结构。",
        "3. **提高鲁棒性**：让检查逻辑更能适应不同的、但语义相同的布局。"
    ]
    
    for suggestion in suggestions:
        print(suggestion)
    print()

def main():
    """运行所有测试"""
    print("开始测试 check_local.py 的评估逻辑\n")
    
    # 运行各项测试
    test1_result = test_excel_format_with_standard_data()
    test2_result = test_excel_format_with_compact_data()  
    
    test_dropna_approach()
    analyze_current_issues()
    
    # 总结测试结果
    print("=== 测试总结 ===")
    print(f"标准格式（含空行）检查: {'通过' if test1_result else '失败'}")
    print(f"紧凑格式（无空行）检查: {'通过' if test2_result else '失败'}")
    
    if test1_result and not test2_result:
        print("\n✅ 结论：代码只接受包含空行的格式，这与预期不符，因为它应该能处理清理后的数据。")
    elif not test1_result and test2_result:
        print("\n✅ 结论：代码只接受紧凑格式，拒绝标准答案中包含空行的格式。这是当前实现的主要问题。") 
    elif test1_result and test2_result:
        print("\n✅ 代码能够处理两种格式，这是理想状态。")
    else:
        print("\n❌ 结论：代码存在严重问题，两种格式都无法正确处理。")
    
    print("\n核心问题是 `check_local` 中的 `check_excel_format` 函数没有对读入的DataFrame进行预处理（如去除空行），导致硬编码的行索引失效。")

if __name__ == "__main__":
    # Add the parent directory to sys.path to find the 'evaluation' module
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main() 