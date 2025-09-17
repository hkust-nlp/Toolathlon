#!/usr/bin/env python3
"""
测试 main.py 修改后的功能
验证从 page_id 查找 database_id 的逻辑是否正常
"""

import sys
import os
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def test_token_loading():
    """测试 token 加载"""
    print("🔍 测试 token 加载...")
    
    try:
        from token_key_session import all_token_key_session
        
        print(f"✅ 成功加载 token 配置")
        print(f"📄 Page ID: {all_token_key_session.notion_allowed_page_ids}")
        print(f"🔑 Integration Key (前10位): {all_token_key_session.notion_integration_key[:10]}...")
        
        return all_token_key_session
        
    except Exception as e:
        print(f"❌ Token 加载失败: {e}")
        return None

def test_debug_functions():
    """测试 debug_notion.py 函数导入"""
    print("\n🔍 测试 debug_notion.py 函数导入...")
    
    try:
        from debug_notion import find_database_ids_in_page, get_page_content, get_page_blocks
        
        print(f"✅ 成功导入所有函数")
        print(f"   - find_database_ids_in_page: {find_database_ids_in_page}")
        print(f"   - get_page_content: {get_page_content}")
        print(f"   - get_page_blocks: {get_page_blocks}")
        
        return True
        
    except Exception as e:
        print(f"❌ 函数导入失败: {e}")
        return False

def test_page_id_lookup():
    """测试页面 ID 查找数据库功能"""
    print("\n🔍 测试页面 ID 查找数据库功能...")
    
    tokens = test_token_loading()
    if not tokens:
        return False
    
    functions_ok = test_debug_functions()
    if not functions_ok:
        return False
    
    try:
        from debug_notion import find_database_ids_in_page
        
        page_id = tokens.notion_allowed_page_ids.strip()
        notion_token = tokens.notion_integration_key
        
        print(f"📄 使用页面 ID: {page_id}")
        print(f"🔑 使用 Token (前10位): {notion_token[:10]}...")
        
        # 查找数据库 ID
        database_ids = find_database_ids_in_page(notion_token, page_id, debug=True)
        
        if database_ids:
            print(f"✅ 成功找到 {len(database_ids)} 个数据库:")
            for i, db_id in enumerate(database_ids, 1):
                print(f"   {i}. {db_id}")
            return database_ids
        else:
            print(f"❌ 未找到任何数据库")
            return []
            
    except Exception as e:
        print(f"❌ 页面查找失败: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_main_logic():
    """测试 main.py 的主要逻辑"""
    print("\n🔍 测试 main.py 主要逻辑...")
    
    try:
        # 模拟 main.py 中的逻辑
        import runpy
        from pathlib import Path
        
        def load_tokens(token_path: Path):
            ns = runpy.run_path(str(token_path))
            if "all_token_key_session" not in ns:
                raise RuntimeError("all_token_key_session not found in token file")
            return ns["all_token_key_session"]
        
        # 加载 token
        token_path = Path("token_key_session.py")
        tokens = load_tokens(token_path)
        
        # 获取页面 ID
        page_id = tokens.notion_allowed_page_ids.strip()
        notion_token = str(tokens.notion_integration_key)
        
        print(f"📄 页面 ID: {page_id}")
        print(f"🔑 Notion Token: {notion_token[:10]}...")
        
        # 查找数据库
        from debug_notion import find_database_ids_in_page
        database_ids = find_database_ids_in_page(notion_token, page_id, debug=False)
        
        if not database_ids:
            print(f"❌ 在页面中未找到任何数据库")
            return False
        
        # 模拟选择第一个数据库
        db_id = database_ids[0]
        if len(database_ids) > 1:
            print(f"⚠️  找到 {len(database_ids)} 个数据库，使用第一个: {db_id}")
        
        print(f"🎯 选择的数据库 ID: {db_id}")
        
        # 这里可以继续测试数据库查询，但为了避免过多 API 调用，我们先到这里
        print(f"✅ 主要逻辑测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 主要逻辑测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试 main.py 修改后的功能")
    print("=" * 60)
    
    # 执行所有测试
    tests = [
        ("Token 加载", test_token_loading),
        ("Debug 函数导入", test_debug_functions),
        ("页面查找数据库", test_page_id_lookup),
        ("主要逻辑", test_main_logic),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result is not False and result is not None
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            results[test_name] = False
    
    # 打印测试结果
    print("\n" + "=" * 60)
    print("🎯 测试结果总结:")
    for test_name, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"   {test_name}: {status}")
    
    overall_success = all(results.values())
    if overall_success:
        print(f"\n🎉 所有测试通过！main.py 修改成功")
    else:
        print(f"\n⚠️  部分测试失败，请检查相关配置")
    
    return overall_success

if __name__ == "__main__":
    main() 