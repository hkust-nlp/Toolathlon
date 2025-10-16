from typing import Dict
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime
import time

GOOGLE_CREDENTIAL_FILE = "configs/google_credentials.json"

def clear_google_forms(form_name_pattern: str = None) -> Dict:
    """
    Delete all Google Forms that match the given name pattern
    
    Args:
        form_name_pattern: Pattern for the form name to match. If None, delete all forms.
    
    Returns:
        Dictionary with deletion results
    """
    print("📝 Starting cleanup of Google Forms...")
    
    try:
        try:
            with open(GOOGLE_CREDENTIAL_FILE, 'r') as f:
                cred_data = json.load(f)
            
            creds = Credentials(
                token=cred_data['token'],
                refresh_token=cred_data['refresh_token'],
                token_uri=cred_data['token_uri'],
                client_id=cred_data['client_id'],
                client_secret=cred_data['client_secret'],
                scopes=cred_data['scopes']
            )
            
        except Exception as e:
            print(f"⚠️ Unable to read Google credentials config file: {e}")
            return {
                "success": False,
                "error": f"Google credentials configuration error: {e}",
                "timestamp": datetime.now().isoformat()
            }
        
        # Build Google Drive service
        drive_service = build('drive', 'v3', credentials=creds)
        
        # Build query string
        if form_name_pattern:
            query = f"name contains '{form_name_pattern}' and mimeType='application/vnd.google-apps.form'"
            print(f"🔍 Searching for Google Forms containing '{form_name_pattern}'...")
        else:
            query = "mimeType='application/vnd.google-apps.form'"
            print("🔍 Searching for all Google Forms...")
        
        # Find all matching Google Forms
        page_token = None
        all_forms = []
        
        while True:
            try:
                results = drive_service.files().list(
                    q=query,
                    fields="nextPageToken, files(id, name, createdTime)",
                    pageToken=page_token
                ).execute()
                
                forms = results.get('files', [])
                all_forms.extend(forms)
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
            except Exception as e:
                print(f"⚠️ Error occurred when querying Google Forms: {e}")
                break
        
        if not all_forms:
            print("📭 No matching Google Forms found")
            return {
                "success": True,
                "deleted_count": 0,
                "found_count": 0,
                "message": "No matching forms found",
                "timestamp": datetime.now().isoformat()
            }
        
        print(f"📋 Found {len(all_forms)} matching Google Forms")
        
        # Delete matched forms
        deleted_count = 0
        failed_count = 0
        deleted_forms = []
        
        for i, form in enumerate(all_forms, 1):
            form_id = form['id']
            form_name = form['name']
            created_time = form.get('createdTime', 'Unknown')
            
            try:
                # Delete form
                drive_service.files().delete(fileId=form_id).execute()
                deleted_count += 1
                deleted_forms.append({
                    "id": form_id,
                    "name": form_name,
                    "created_time": created_time
                })
                print(f"   ✅ Deleted form '{form_name}' (ID: {form_id}) [{i}/{len(all_forms)}]")
                
                # Add short delay to avoid API limits
                time.sleep(0.2)
                
            except Exception as e:
                failed_count += 1
                print(f"   ❌ Failed to delete form '{form_name}' (ID: {form_id}): {e}")
        
        # Calculate result
        all_success = failed_count == 0
        
        final_result = {
            "success": all_success,
            "found_count": len(all_forms),
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "deleted_forms": deleted_forms,
            "search_pattern": form_name_pattern,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"📊 Google Forms cleanup complete:")
        print(f"   Forms found: {len(all_forms)}")
        print(f"   Successfully deleted: {deleted_count}")
        print(f"   Failed deletions: {failed_count}")
        
        if all_success:
            print("✅ All Google Forms deleted successfully!")
        else:
            print("⚠️ Partial success: some forms failed to be deleted")
        
        return final_result
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        print(f"❌ Error occurred during Google Forms cleanup: {e}")
        return error_result