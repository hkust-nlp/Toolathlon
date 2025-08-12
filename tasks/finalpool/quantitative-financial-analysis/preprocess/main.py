#!/usr/bin/env python3
"""
Google Sheets预处理脚本
用于检测并删除已存在的2025_Q2_Market_Data Google Sheet文件
"""
from argparse import ArgumentParser
import gspread
import os
import sys
import json
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# 动态添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.append(project_root)
import configs.token_key_session as configs

# Google Sheets配置
GOOGLE_CREDENTIALS_PATH = 'configs/google_credentials.json'
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

TARGET_SPREADSHEET_NAME = "2025_Q2_Market_Data"
TARGET_FOLDER_ID = "1LYqmSCIlY0NmHtFJwF3Mh1RTb81RWHvU"  # 指定的Google Drive文件夹ID

def get_current_user_email(drive_service):
    """获取当前认证用户的邮箱地址"""
    try:
        about = drive_service.about().get(fields="user").execute()
        user_email = about['user']['emailAddress']
        print(f"当前用户: {user_email}")
        return user_email
    except Exception as e:
        print(f"获取用户信息失败: {e}")
        return None

def authenticate_google_services():
    """认证Google服务 - 使用OAuth2用户凭证"""
    try:
        print("正在认证Google服务...")
        
        # 读取OAuth2凭证文件
        with open(GOOGLE_CREDENTIALS_PATH, 'r') as f:
            creds_data = json.load(f)
        
        # 创建OAuth2凭证对象
        credentials = Credentials(
            token=creds_data.get('token'),
            refresh_token=creds_data.get('refresh_token'),
            token_uri=creds_data.get('token_uri'),
            client_id=creds_data.get('client_id'),
            client_secret=creds_data.get('client_secret'),
            scopes=creds_data.get('scopes', SCOPES)
        )
        
        # 如果token过期，自动刷新
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            
            # 更新保存的token
            creds_data['token'] = credentials.token
            with open(GOOGLE_CREDENTIALS_PATH, 'w') as f:
                json.dump(creds_data, f, indent=2)
            print("✓ Token已刷新并保存")
        
        # 初始化gspread客户端
        gc = gspread.authorize(credentials)
        
        # 初始化Google Drive API客户端
        drive_service = build('drive', 'v3', credentials=credentials)
        
        print("✓ Google服务认证成功")
        return gc, drive_service
        
    except FileNotFoundError:
        raise Exception(f"错误：找不到凭证文件 '{GOOGLE_CREDENTIALS_PATH}'")
    except json.JSONDecodeError:
        raise Exception(f"错误：凭证文件格式错误 '{GOOGLE_CREDENTIALS_PATH}'")
    except Exception as e:
        raise Exception(f"Google服务认证失败: {e}")

def find_existing_spreadsheets(gc, drive_service, spreadsheet_name, folder_id=None):
    """查找已存在的同名Google Sheets文件"""
    try:
        print(f"正在搜索名为 '{spreadsheet_name}' 的Google Sheets文件...")
        if folder_id:
            print(f"搜索范围限制在文件夹ID: {folder_id}")
        
        existing_spreadsheets = []
        
        # 方法1: 使用gspread直接搜索（无法限制文件夹）
        if not folder_id:  # 只有在不限制文件夹时才使用gspread方法
            try:
                spreadsheet = gc.open(spreadsheet_name)
                existing_spreadsheets.append({
                    'id': spreadsheet.id,
                    'title': spreadsheet.title,
                    'url': spreadsheet.url,
                    'method': 'gspread'
                })
                print(f"✓ 通过gspread找到spreadsheet: {spreadsheet.title} (ID: {spreadsheet.id})")
            except gspread.SpreadsheetNotFound:
                print("  gspread未找到同名文件")
            except Exception as e:
                print(f"  gspread搜索时出错: {e}")
        
        # 方法2: 使用Google Drive API搜索（支持文件夹限制）
        try:
            # 构建查询条件
            query_parts = [
                f"name='{spreadsheet_name}'",
                "mimeType='application/vnd.google-apps.spreadsheet'",
                "trashed=false"
            ]
            
            # 如果指定了文件夹ID，添加到查询条件
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")
            
            query = " and ".join(query_parts)
            print(f"Drive API查询条件: {query}")
            
            results = drive_service.files().list(q=query, fields="files(id, name, webViewLink, parents)").execute()
            files = results.get('files', [])
            
            for file in files:
                # 避免重复添加
                if not any(item['id'] == file['id'] for item in existing_spreadsheets):
                    existing_spreadsheets.append({
                        'id': file['id'],
                        'title': file['name'],
                        'url': file['webViewLink'],
                        'parents': file.get('parents', []),
                        'method': 'drive_api'
                    })
                    parents_info = ', '.join(file.get('parents', []))
                    print(f"✓ 通过Drive API找到spreadsheet: {file['name']} (ID: {file['id']}, 父文件夹: {parents_info})")
            
            if not files:
                if folder_id:
                    print(f"  Drive API在指定文件夹中未找到同名文件")
                else:
                    print("  Drive API未找到同名文件")
                
        except Exception as e:
            print(f"  Drive API搜索时出错: {e}")
        
        print(f"总共找到 {len(existing_spreadsheets)} 个同名文件")
        return existing_spreadsheets
        
    except Exception as e:
        raise Exception(f"搜索已存在文件时出错: {e}")

def delete_spreadsheet(drive_service, spreadsheet_id, spreadsheet_title):
    """删除指定的Google Sheets文件"""
    try:
        print(f"正在删除spreadsheet: {spreadsheet_title} (ID: {spreadsheet_id})")
        
        # 使用Google Drive API删除文件
        drive_service.files().delete(fileId=spreadsheet_id).execute()
        
        print(f"✓ 成功删除spreadsheet: {spreadsheet_title}")
        return True
        
    except Exception as e:
        error_msg = str(e)
        if "insufficientFilePermissions" in error_msg or "403" in error_msg:
            print(f"⚠ 权限不足，无法删除spreadsheet: {spreadsheet_title}")
            print(f"  建议：请确认您是文件的拥有者或有删除权限")
            return "permission_error"
        elif "notFound" in error_msg or "404" in error_msg:
            print(f"ℹ 文件不存在（可能已被删除）: {spreadsheet_title}")
            return True  # 文件不存在视为删除成功
        else:
            print(f"✗ 删除spreadsheet失败: {e}")
            return False

def verify_folder_exists(drive_service, folder_id):
    """验证指定的文件夹ID是否存在"""
    try:
        print(f"正在验证文件夹ID: {folder_id}")
        folder_info = drive_service.files().get(fileId=folder_id, fields="id, name, mimeType").execute()
        
        if folder_info.get('mimeType') == 'application/vnd.google-apps.folder':
            print(f"✓ 文件夹验证成功: {folder_info['name']} (ID: {folder_info['id']})")
            return True, folder_info['name']
        else:
            print(f"✗ 指定ID不是文件夹: {folder_info.get('mimeType')}")
            return False, None
            
    except Exception as e:
        print(f"✗ 文件夹验证失败: {e}")
        return False, None

def cleanup_existing_spreadsheets(target_name=TARGET_SPREADSHEET_NAME, target_folder=TARGET_FOLDER_ID):
    """主要的清理函数"""
    print("=" * 60)
    print("开始Google Sheets预处理 - 清理已存在的文件")
    if target_folder:
        print(f"清理范围：文件夹ID {target_folder}")
    print("=" * 60)
    
    try:
        # 认证Google服务
        gc, drive_service = authenticate_google_services()
        
        # 如果指定了文件夹，先验证文件夹是否存在
        if target_folder:
            folder_exists, folder_name = verify_folder_exists(drive_service, target_folder)
            if not folder_exists:
                print("✗ 指定的文件夹不存在或无法访问")
                return False
        
        # 查找已存在的同名文件
        existing_files = find_existing_spreadsheets(gc, drive_service, target_name, target_folder)
        
        if not existing_files:
            if target_folder:
                print(f"✓ 在指定文件夹中未找到名为 '{target_name}' 的现有文件，无需清理")
            else:
                print(f"✓ 未找到名为 '{target_name}' 的现有文件，无需清理")
            return True
        
        # 删除找到的文件
        print(f"\n开始删除 {len(existing_files)} 个同名文件...")
        deleted_count = 0
        failed_count = 0
        permission_error_count = 0
        
        for file_info in existing_files:
            result = delete_spreadsheet(
                drive_service, 
                file_info['id'], 
                file_info['title']
            )
            if result is True:
                deleted_count += 1
            elif result == "permission_error":
                permission_error_count += 1
            else:
                failed_count += 1
        
        print(f"\n清理结果:")
        print(f"  成功删除: {deleted_count} 个文件")
        print(f"  权限不足: {permission_error_count} 个文件")
        print(f"  其他失败: {failed_count} 个文件")
        
        # 如果只是权限问题，我们认为这是可接受的（因为文件存在但无法删除）
        if failed_count > 0:
            print("✗ 存在无法处理的错误")
            return False
        elif permission_error_count > 0:
            print("⚠ 部分文件因权限问题无法删除，这可能会影响任务执行")
            print("  建议：手动删除这些文件或授予服务账号更多权限")
            # 权限问题不应该阻止任务执行，因为agent可能有不同的权限
            return True
        else:
            print("✓ 所有同名文件已成功清理")
            return True
            
    except Exception as e:
        print(f"✗ 预处理过程中发生错误: {e}")
        return False

def verify_cleanup():
    """验证清理结果"""
    try:
        print("\n验证清理结果...")
        gc, drive_service = authenticate_google_services()
        existing_files = find_existing_spreadsheets(gc, drive_service, TARGET_SPREADSHEET_NAME, TARGET_FOLDER_ID)
        
        if not existing_files:
            if TARGET_FOLDER_ID:
                print("✓ 验证通过：在指定文件夹中未发现同名文件")
            else:
                print("✓ 验证通过：未发现同名文件")
            return True
        else:
            if TARGET_FOLDER_ID:
                print(f"✗ 验证失败：在指定文件夹中仍然存在 {len(existing_files)} 个同名文件")
            else:
                print(f"✗ 验证失败：仍然存在 {len(existing_files)} 个同名文件")
            for file_info in existing_files:
                parents_info = ', '.join(file_info.get('parents', []))
                print(f"  - {file_info['title']} (ID: {file_info['id']}, 父文件夹: {parents_info})")
            return False
            
    except Exception as e:
        print(f"验证过程中出错: {e}")
        return False

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--launch_time", nargs='*', required=False, help="Launch time (can contain spaces)")
    args = parser.parse_args()
    
    print("Google Sheets预处理工具")
    print("用途：清理已存在的2025_Q2_Market_Data文件")
    print(f"目标文件夹ID: {TARGET_FOLDER_ID}")
    
    try:
        # 执行清理
        success = cleanup_existing_spreadsheets()
        
        if success:
            # 验证清理结果
            verify_success = verify_cleanup()
            if verify_success:
                print("\n" + "=" * 60)
                print("✓ 预处理完成：环境已清理，可以开始任务")
                print("=" * 60)
                sys.exit(0)
            else:
                print("\n" + "=" * 60)
                print("✗ 预处理未完全成功：环境清理不彻底")
                print("=" * 60)
                sys.exit(1)
        else:
            print("\n" + "=" * 60)
            print("✗ 预处理失败：无法清理环境")
            print("=" * 60)
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n用户中断了预处理过程")
        sys.exit(1)
    except Exception as e:
        print(f"\n预处理过程中发生未知错误: {e}")
        sys.exit(1)