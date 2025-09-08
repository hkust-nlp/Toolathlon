from argparse import ArgumentParser
import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

GOOGLE_CREDENTIALS_PATH = 'configs/google_credentials.json'
TARGET_FOLDER_ID = "1wemPliO93NsmMIIbfxI5YfREQeSI7zyC"  # 指定的Google Drive文件夹ID
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

def delete_ptdata_sheet_if_exists(folder_id, creds, spreadsheet_name="LLM Pre-training Data", sheet_name="ptdata"):
    """
    删除指定Google Sheet文件中的ptdata工作表
    """
    drive_service = build('drive', 'v3', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    
    # 1. 查找文件夹下名为"LLM Pre-training Data"的表格文件
    query = (
        f"'{folder_id}' in parents and "
        f"mimeType = 'application/vnd.google-apps.spreadsheet' and "
        f"name = '{spreadsheet_name}' and trashed = false"
    )
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    if not files:
        print(f"未找到名为 {spreadsheet_name} 的Google Sheet文件。")
        return
    
    file_id = files[0]['id']
    print(f"找到文件: {spreadsheet_name} (ID: {file_id})")
    
    # 2. 获取所有工作表信息
    try:
        sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=file_id).execute()
        sheets = sheet_metadata.get('sheets', [])
        
        # 3. 查找ptdata工作表
        ptdata_sheet_id = None
        for sheet in sheets:
            if sheet['properties']['title'] == sheet_name:
                ptdata_sheet_id = sheet['properties']['sheetId']
                break
        
        if ptdata_sheet_id is None:
            print(f"未找到名为 {sheet_name} 的工作表，无需删除。")
            return
        
        # 4. 删除ptdata工作表
        request = {
            'requests': [{
                'deleteSheet': {
                    'sheetId': ptdata_sheet_id
                }
            }]
        }
        
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=file_id,
            body=request
        ).execute()
        
        print(f"已删除工作表: {sheet_name}")
        
    except Exception as e:
        print(f"删除工作表时出错: {e}")

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    # 1. 加载Google凭证
    if not os.path.exists(GOOGLE_CREDENTIALS_PATH):
        print(f"Google credentials not found at {GOOGLE_CREDENTIALS_PATH}")
        exit(1)
    creds = Credentials.from_authorized_user_file(GOOGLE_CREDENTIALS_PATH, SCOPES)

    # 2. 调用删除ptdata工作表的函数
    delete_ptdata_sheet_if_exists(TARGET_FOLDER_ID, creds)
