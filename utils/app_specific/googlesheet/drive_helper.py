import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def get_google_service():
    credentials_file = "/ssddata/junlong/projects/mcpbench_finalpool_dev/configs/google_credentials.json"
    
    with open(credentials_file, 'r') as f:
        cred_data = json.load(f)
    
    creds = Credentials(
        token=cred_data['token'],
        refresh_token=cred_data['refresh_token'],
        token_uri=cred_data['token_uri'],
        client_id=cred_data['client_id'],
        client_secret=cred_data['client_secret'],
        scopes=cred_data['scopes']
    )
    
    drive_service = build('drive', 'v3', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    
    return drive_service, sheets_service

def find_folder_by_name(drive_service, folder_name):
    results = drive_service.files().list(
        q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'",
        fields="files(id, name)"
    ).execute()
    
    files = results.get('files', [])
    return files[0]['id'] if files else None

def create_folder(drive_service, folder_name):
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    
    folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
    return folder.get('id')

def clear_folder(drive_service, folder_id):
    results = drive_service.files().list(
        q=f"'{folder_id}' in parents",
        fields="files(id)"
    ).execute()
    
    for file in results.get('files', []):
        drive_service.files().delete(fileId=file['id']).execute()

def copy_sheet_to_folder(drive_service, sheet_url, folder_id):
    sheet_id = sheet_url.split('/d/')[1].split('/')[0]
    
    # 获取原始sheet的名称
    original_file = drive_service.files().get(fileId=sheet_id, fields='name').execute()
    original_name = original_file['name']
    
    copy_metadata = {
        'parents': [folder_id]
    }
    
    copied_file = drive_service.files().copy(
        fileId=sheet_id,
        body=copy_metadata
    ).execute()
    
    # 将复制的文件重命名为原始名称，去掉"（副本）"后缀
    rename_metadata = {
        'name': original_name
    }
    
    drive_service.files().update(
        fileId=copied_file['id'],
        body=rename_metadata
    ).execute()
    
    permission = {
        'role': 'writer',
        'type': 'anyone'
    }
    
    drive_service.permissions().create(
        fileId=copied_file['id'],
        body=permission
    ).execute()
    
    return copied_file['id']