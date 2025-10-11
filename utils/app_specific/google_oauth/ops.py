from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

GOOGLE_CREDENTIAL_FILE = "configs/google_credentials.json"

def get_credentials(google_credential_file=GOOGLE_CREDENTIAL_FILE):
    """Get Google API credentials from the existing token file"""
    creds = Credentials.from_authorized_user_file(google_credential_file)
    
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
    
    return creds