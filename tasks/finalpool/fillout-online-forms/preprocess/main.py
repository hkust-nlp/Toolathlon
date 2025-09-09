from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from argparse import ArgumentParser
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from token_key_session import all_token_key_session

SPREADSHEET_ID = '11laynQ5hFs8jP1BsqaczAJY6yWiNEDalZB4WqxdoE8g'

def update_groundtruth_timestamps(launch_time):
    """更新groundtruth_workspace中JSON文件的时间戳"""
    print("正在更新groundtruth文件的时间戳...")

    timestamp = launch_time
    
    # 获取groundtruth_workspace目录路径
    current_dir = Path(__file__).parent.parent
    groundtruth_dir = current_dir / "groundtruth_workspace"
    
    # 更新所有JSON文件的时间戳
    json_files = ["mcp_response.json", "alex_response.json"]
    
    for json_file in json_files:
        file_path = groundtruth_dir / json_file
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 更新时间戳记字段
                data["时间戳记"] = timestamp
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                print(f"✔ 已更新 {json_file} 的时间戳为: {timestamp}")
                
            except Exception as e:
                print(f"更新 {json_file} 时出错: {e}")
        else:
            print(f"文件不存在: {json_file}")

def _load_credentials(credentials_file):
    """从指定的凭证文件中加载Google凭证"""
    try:
        with open(credentials_file, 'r') as f:
            credentials_info = json.load(f)
        return credentials_info
    except Exception as e:
        print(f"加载凭证失败: {e}")
        return None

def _get_service(credentials_file):
    """从指定的凭证文件创建Google Sheets API服务对象"""
    try:
        credentials_info = _load_credentials(credentials_file)
        if not credentials_info:
            return None
            
        creds = Credentials.from_authorized_user_info(credentials_info, scopes=credentials_info["scopes"])
        
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        
        service = build("sheets", "v4", credentials=creds)
        return service
    except Exception as e:
        print(f"创建服务失败: {e}")
        return None

def clear_google_sheet_data(credentials_file):
    """清空Google表格中所有的数据（保留表头）"""
    print("正在执行 '清空数据' 操作...")
    service = _get_service(credentials_file)
    if not service:
        return

    try:
        sheet = service.spreadsheets()
        meta = sheet.get(spreadsheetId=SPREADSHEET_ID).execute()
        sheet_name = meta["sheets"][0]["properties"]["title"]
        
        clear_range = f"{sheet_name}!A2:Z"
        print(f"即将清空范围: '{clear_range}'...")

        request_body = {}
        sheet.values().clear(
            spreadsheetId=SPREADSHEET_ID,
            range=clear_range,
            body=request_body
        ).execute()

        print("✔ 数据已成功清空！")
        
    except HttpError as err:
        print(f"API 调用失败: {err}")
        print("请检查表格ID和用户凭证是否正确，以及该用户是否有权限访问该表格。")
    except Exception as e:
        print(f"发生了一个错误: {e}")

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=True, help="Launch time")
    parser.add_argument("--credentials_file", required=False)
    args = parser.parse_args()

    credentials_file = args.credentials_file
    if not credentials_file:
        credentials_file = all_token_key_session.get("google_oauth2_credentials_path", "configs/google_credentials.json")
    print("Preprocess...")
    
    # 更新groundtruth文件的时间戳
    update_groundtruth_timestamps(args.launch_time)
    
    print("Clearing Google Sheet Data...")
    clear_google_sheet_data(credentials_file)
    print("Google Sheet Data Cleared.")
