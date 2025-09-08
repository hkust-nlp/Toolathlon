#!/usr/bin/env python3
"""
Google Sheets预处理脚本
用于创建动态文件夹并清理已存在的投资分析相关Google Sheet文件
"""
import os
import sys
from argparse import ArgumentParser

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# 尝试使用现有的drive_helper，如果失败则使用自定义实现
try:
    from utils.app_specific.googlesheet.drive_helper import (
        get_google_service, find_folder_by_name, create_folder, 
        clear_folder
    )
    USE_DRIVE_HELPER = True
    print("✅ 使用现有的drive_helper模块")
except ImportError as e:
    print(f"⚠️ 无法导入drive_helper: {e}")
    USE_DRIVE_HELPER = False

# 如果无法使用drive_helper，使用自定义实现
if not USE_DRIVE_HELPER:
    import json
    import gspread
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    
    # Google Sheets配置
    GOOGLE_CREDENTIALS_PATH = 'configs/google_credentials.json'
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    def get_google_service():
        """获取Google服务"""
        try:
            # 查找凭证文件的可能路径
            possible_paths = [
                GOOGLE_CREDENTIALS_PATH,
                f"../{GOOGLE_CREDENTIALS_PATH}",
                f"../../{GOOGLE_CREDENTIALS_PATH}",
                f"../../../{GOOGLE_CREDENTIALS_PATH}",
                f"../../../../{GOOGLE_CREDENTIALS_PATH}"
            ]
            
            credentials_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    credentials_path = path
                    break
                    
            if not credentials_path:
                raise Exception(f"找不到凭证文件，查找路径: {possible_paths}")
            
            # 读取OAuth2凭证文件
            with open(credentials_path, 'r') as f:
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
                with open(credentials_path, 'w') as f:
                    json.dump(creds_data, f, indent=2)
            
            # 初始化服务
            drive_service = build('drive', 'v3', credentials=credentials)
            sheets_service = build('sheets', 'v4', credentials=credentials)
            
            return drive_service, sheets_service
            
        except Exception as e:
            raise Exception(f"Google服务认证失败: {e}")
    
    def find_folder_by_name(drive_service, folder_name):
        """查找指定名称的文件夹"""
        results = drive_service.files().list(
            q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id, name)"
        ).execute()
        
        files = results.get('files', [])
        return files[0]['id'] if files else None

    def create_folder(drive_service, folder_name):
        """创建新文件夹"""
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
        return folder.get('id')

    def clear_folder(drive_service, folder_id):
        """清理文件夹内的所有文件"""
        results = drive_service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name)"
        ).execute()
        
        for file in results.get('files', []):
            try:
                drive_service.files().delete(fileId=file['id']).execute()
            except Exception as e:
                print(f"警告：无法删除文件 {file.get('name', file['id'])}: {e}")

# 任务配置
FOLDER_NAME = "InvestmentAnalysisWorkspace"

def main():
    """主函数 - 模仿googlesheet-example的实现"""
    parser = ArgumentParser(description="Investment Decision Analysis preprocess")
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False)
    args = parser.parse_args()

    print("Investment Decision Analysis预处理工具")
    print("用途：创建动态文件夹并清理已存在的投资分析相关Google Sheets文件")
    print(f"动态文件夹名称: {FOLDER_NAME}")
    print("=" * 60)

    try:
        # 设置文件路径
        task_root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.makedirs(os.path.join(task_root_path, "files"), exist_ok=True)
        folder_id_file = os.path.join(task_root_path, "files", "folder_id.txt")

        # 删除旧的folder_id文件
        if os.path.exists(folder_id_file):
            os.remove(folder_id_file)
            print("✅ 已删除旧的folder_id文件")

        # 获取Google服务
        drive_service, sheets_service = get_google_service()
        print("✅ Google服务认证成功")

        # 查找或创建文件夹
        folder_id = find_folder_by_name(drive_service, FOLDER_NAME)
        if not folder_id:
            folder_id = create_folder(drive_service, FOLDER_NAME)
            print(f"✅ 创建了新文件夹: {FOLDER_NAME} (ID: {folder_id})")
        else:
            print(f"✅ 找到现有文件夹: {FOLDER_NAME} (ID: {folder_id})")

        # 清理文件夹内容
        clear_folder(drive_service, folder_id)
        print("✅ 已清理文件夹内容")

        # 保存folder_id到文件
        with open(folder_id_file, "w") as f:
            f.write(folder_id)

        print(f"✅ Folder ID已保存: {folder_id}")
        print("=" * 60)
        print("✅ 预处理完成：环境已准备好，可以开始任务")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ 预处理过程中发生错误: {e}")
        print("=" * 60)
        print("❌ 预处理失败：无法准备环境")
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)