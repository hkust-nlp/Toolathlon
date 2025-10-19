#!/usr/bin/env python3
"""测试历史记录摘要功能"""

from utils.roles.context_managed_runner import ContextManagedRunner

def test_format_content_with_truncation():
    """测试内容截断格式化"""
    
    # 测试短内容（不需要截断）
    short_content = "这是一个简短的测试内容"
    result = ContextManagedRunner._format_content_with_truncation(short_content)
    print(f"短内容: {result}")
    
    # 测试长内容（需要截断）
    long_content = "这是一个很长的测试内容，" * 50  # 大约1000字符
    result = ContextManagedRunner._format_content_with_truncation(long_content)
    print(f"长内容: {result}")
    
    # 测试空内容
    empty_content = ""
    result = ContextManagedRunner._format_content_with_truncation(empty_content)
    print(f"空内容: {result}")
    
    # 测试精确500字符的内容
    exact_content = "测试" * 250  # 正好500字符
    result = ContextManagedRunner._format_content_with_truncation(exact_content)
    print(f"500字符内容: {len(exact_content)}字符 -> {result[:100]}...")

if __name__ == "__main__":
    test_format_content_with_truncation()