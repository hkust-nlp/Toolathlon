import re
from argparse import ArgumentParser
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def reset_folder_with_sheet(drive_service, folder_id: str, source_sheet_url: str, new_name: str = "GDP CR5 Analysis"):
    # 1) 从 URL 提取源表格 fileId
    m = re.search(r"/d/([a-zA-Z0-9\-_]+)", source_sheet_url)
    if not m:
        raise ValueError("无法从链接中解析表格 fileId，请检查 URL 是否为标准的 docs.google.com/spreadsheets 链接。")
    source_file_id = m.group(1)

    # 2) 校验源文件是否存在且为 Google 表格
    src = drive_service.files().get(
        fileId=source_file_id,
        fields="id, name, mimeType",
        supportsAllDrives=True
    ).execute()
    if src.get("mimeType") != "application/vnd.google-apps.spreadsheet":
        raise RuntimeError(f"源文件不是 Google 表格，实际 mimeType: {src.get('mimeType')}")

    # 3) 清空目标文件夹（永久删除）
    page_token = None
    while True:
        resp = drive_service.files().list(
            q=f"'{folder_id}' in parents",
            fields="nextPageToken, files(id, name, mimeType)",
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            pageToken=page_token
        ).execute()
        for f in resp.get("files", []):
            try:
                drive_service.files().delete(
                    fileId=f["id"],
                    supportsAllDrives=True
                ).execute()
                print(f"Deleted: {f['name']} ({f['id']})")
            except Exception as e:
                print(f"删除失败: {f['name']} ({f['id']}) - {e}")

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    # 4) 复制源表格到目标文件夹
    copy_body = {
        "name": new_name or src["name"],
        "parents": [folder_id],
        "mimeType": "application/vnd.google-apps.spreadsheet"
    }
    new_file = drive_service.files().copy(
        fileId=source_file_id,
        body=copy_body,
        fields="id, name, parents",
        supportsAllDrives=True
    ).execute()

    print(f"Copied sheet to folder. New file: {new_file['name']} ({new_file['id']})")
    return new_file["id"], new_file["name"]

def main():
    parser = ArgumentParser()
    parser.add_argument("--folder_id", default="1Xi5bBHdiyGxYDBud5GqkWYo-DOPkWkZl")
    parser.add_argument("--credentials_file",default="configs/credentials.json")
    args = parser.parse_args()

    print(f"Using folder ID: {args.folder_id}")

    with open(args.credentials_file,"r",encoding="utf-8") as f:
        OAUTH_JSON = json.load(f)
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_authorized_user_info(OAUTH_JSON, scopes=SCOPES)

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise RuntimeError("Credentials invalid and no refresh_token available.")
        
    sheets_service = build("sheets", "v4", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)
    print("Google Sheets and Drive API clients initialized successfully.")

    reset_folder_with_sheet(drive_service, args.folder_id, "https://docs.google.com/spreadsheets/d/1l_XCK3ebOsKESX-SRamka0Z_O2K5Y2REqo6OHh4C93c/edit?usp=sharing", "GDP CR5 Analysis")

if __name__ == "__main__":
    main() 