import os
import json
import gspread
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from utils.app_specific.google_oauth.ops import get_credentials
import pandas as pd
from typing import Optional

def get_google_service():
    credentials_file = "configs/google_credentials.json"
    
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
    

    original_file = drive_service.files().get(fileId=sheet_id, fields='name').execute()
    original_name = original_file['name']
    
    copy_metadata = {
        'parents': [folder_id]
    }
    
    copied_file = drive_service.files().copy(
        fileId=sheet_id,
        body=copy_metadata
    ).execute()
    

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

def authenticate_google_services():
    """Authenticate Google services using OAuth2 user credentials."""
    credentials = get_credentials()

    # Authorize gspread client
    gc = gspread.authorize(credentials)

    # Initialize Google Drive API client
    drive_service = build('drive', 'v3', credentials=credentials)

    return gc, drive_service

def find_spreadsheet_in_folder(target_folder_id: str, spreadsheet_name: str = "NHL-B2B-Analysis") -> str:
    """
    Search for the Spreadsheet file in the agent workspace folder.
    Preference: use folder_id.txt to retrieve folder ID for search.
    """
    gc, drive_service = authenticate_google_services()

    # Query the target folder for the Spreadsheet with specified name
    query = f"'{target_folder_id}' in parents and name='{spreadsheet_name}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
    results = drive_service.files().list(
        q=query,
        fields="files(id, name, mimeType)"
    ).execute()

    files = results.get('files', [])
    if not files:
        raise Exception(f"No Google Spreadsheet file found in the folder {target_folder_id} with name {spreadsheet_name}")

    # Return the spreadsheet ID with the specified name
    spreadsheet = files[0]
    return spreadsheet['id']

def fetch_google_sheet_data_gspread(sheet_id: str) -> Optional[pd.DataFrame]:
    """
    Fetch Google Sheet data using gspread.
    Note: I'm not sure if this can handle multi sheet spreadsheets.
    """
    print(f"Warning: This function can only handle single sheet spreadsheets!!!!")
    gc, drive_service = authenticate_google_services()
    spreadsheet = gc.open_by_key(sheet_id)

    # Get the first worksheet
    worksheet = spreadsheet.get_worksheet(0)
    if not worksheet:
        raise Exception("No worksheets found in spreadsheet")

    # Get all data
    values = worksheet.get_all_values()

    if len(values) < 2:
        raise Exception("Sheet data insufficient (needs at least one header row and one data row)")

    # Convert to DataFrame
    df = pd.DataFrame(values[1:], columns=values[0])
    df = df.dropna(how='all')  # Drop entirely empty rows

    return df