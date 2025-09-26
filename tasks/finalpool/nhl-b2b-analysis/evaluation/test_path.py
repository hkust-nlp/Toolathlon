#!/usr/bin/env python3
"""
路径验证测试脚本
检查google_credentials.json路径是否正确
"""

from pathlib import Path
import os

def test_credential_path():
    """测试认证文件路径"""
    print("🔍 测试google_credentials.json路径...")
    
    # 当前文件路径
    current_file = Path(__file__)
    print(f"当前文件: {current_file}")
    
    # 计算项目根目录 (从evaluation目录向上4级)
    project_root = current_file.parent.parent.parent.parent
    print(f"项目根目录: {project_root.absolute()}")
    
    # 认证文件路径
    credentials_path = project_root / "configs" / "google_credentials.json"
    print(f"计算的认证文件路径: {credentials_path.absolute()}")
    
    # 用户提供的实际路径
    expected_path = "/Users/zengweihao/mcp-bench/mcpbench_dev/configs/google_credentials.json"
    print(f"期望的认证文件路径: {expected_path}")
    
    # 检查路径是否匹配
    if str(credentials_path.absolute()) == expected_path:
        print("✅ 路径计算正确!")
    else:
        print("❌ 路径不匹配!")
        print(f"  计算值: {credentials_path.absolute()}")
        print(f"  期望值: {expected_path}")
    
    # 检查文件是否存在
    if credentials_path.exists():
        print("✅ 认证文件存在")
        
        # 检查文件内容
        try:
            import json
            with open(credentials_path, 'r') as f:
                creds_data = json.load(f)
            
            required_keys = ['token', 'refresh_token', 'client_id', 'client_secret']
            missing_keys = [key for key in required_keys if key not in creds_data]
            
            if not missing_keys:
                print("✅ 认证文件格式正确")
            else:
                print(f"⚠️ 认证文件缺少字段: {missing_keys}")
                
        except Exception as e:
            print(f"❌ 读取认证文件失败: {e}")
    else:
        print("❌ 认证文件不存在")
        
        # 尝试查找文件
        search_paths = [
            Path("/Users/zengweihao/mcp-bench/mcpbench_dev/configs/google_credentials.json"),
            project_root / "configs" / "credentials.json",
            project_root / "configs" / "token_key_session.py"
        ]
        
        print("\n🔍 查找相关认证文件:")
        for search_path in search_paths:
            if search_path.exists():
                print(f"  ✅ 找到: {search_path}")
            else:
                print(f"  ❌ 不存在: {search_path}")

def test_google_auth_helper_import():
    """测试google_auth_helper模块导入"""
    print("\n🔍 测试google_auth_helper模块...")
    
    try:
        from google_auth_helper import GoogleSheetsAuthenticator
        print("✅ 模块导入成功")
        
        # 测试路径
        authenticator = GoogleSheetsAuthenticator()
        print(f"认证器使用的路径: {authenticator.credentials_path}")
        
        # 检查路径是否存在
        if Path(authenticator.credentials_path).exists():
            print("✅ 认证器路径正确")
        else:
            print("❌ 认证器路径不存在")
            
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")

if __name__ == "__main__":
    print("📁 Google Credentials 路径验证")
    print("=" * 50)
    
    test_credential_path()
    test_google_auth_helper_import()
    
    print("\n" + "=" * 50)
    print("测试完成!") 