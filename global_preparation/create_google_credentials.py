import webbrowser
from urllib.parse import urlparse, parse_qs
from google_auth_oauthlib.flow import Flow
import json
import requests

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://mail.google.com/',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/youtube',
    # 'https://www.googleapis.com/auth/maps',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/forms',
]

def manual_oauth_flow_debug():
    try:
        # Create Flow object
        flow = Flow.from_client_secrets_file(
            'configs/gcp-oauth.keys.json',
            scopes=SCOPES,
            redirect_uri='http://localhost:3000/oauth2callback'
        )
        
        # Generate authorization URL
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        print('='*60)
        print('OAuth2 Authorization Steps:')
        print('='*60)
        print(f'\n1. Please copy the URL below and open it in your browser:\n')
        print(auth_url)
        print(f'\n2. In the browser:')
        print('   - Login to your Google account')
        print('   - Agree to all permission requests')
        print('   - Browser will redirect to http://localhost:3000/oauth2callback?code=...')
        print('   - Page may show "This site cannot be reached", this is normal!')
        print(f'\n3. Important: Copy the complete URL from browser address bar')
        print('   URL should look like this:')
        print('   http://localhost:3000/oauth2callback?code=4/0AeaYSH...&scope=...')
        
        redirect_response = input('\nPlease paste the complete URL (starting with http://): ').strip()
        
        # Try multiple ways to parse code
        code = None
        
        # Method 1: Parse from complete URL
        if redirect_response.startswith('http'):
            parsed_url = urlparse(redirect_response)
            params = parse_qs(parsed_url.query)
            code = params.get('code', [None])[0]
        
        # Method 2: If user only pasted the code part
        elif redirect_response.startswith('4/'):
            code = redirect_response
        
        # Method 3: Parse parameters after question mark
        elif 'code=' in redirect_response:
            params = parse_qs(redirect_response.split('?')[-1])
            code = params.get('code', [None])[0]
        
        if not code:
            print('\n❌ Error: Unable to extract authorization code from URL')
            print('Please ensure you copied the complete redirect URL')
            return None
        
        print(f'\n✅ Successfully extracted authorization code: {code[:20]}...')
        print('Exchanging token...')
        
        # Exchange code for token
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        
        # Check if refresh_token was obtained
        if not credentials.refresh_token:
            print('\n⚠️ Warning: No refresh_token obtained')
            print('You may need to:')
            print('1. Revoke this app\'s access in Google account settings')
            print('2. Re-run this script')
        
        # Save credentials
        credentials_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': list(credentials.scopes) if credentials.scopes else SCOPES
        }
        
        with open('./configs/google_credentials.json', 'w') as f:
            json.dump(credentials_data, f, indent=2)
        
        print('\n✅ Success! ./configs/google_credentials.json has been generated')
        print(f'Token: {credentials.token[:30]}...')
        if credentials.refresh_token:
            print(f'Refresh Token: {credentials.refresh_token[:30]}...')
        
        return credentials_data
        
    except Exception as e:
        print(f'\n❌ Error occurred: {str(e)}')
        print('\nPossible causes:')
        print('1. Authorization code has expired (please restart the process)')
        print('2. redirect_uri mismatch')
        print('3. Network connection issues')
        return None

if __name__ == '__main__':
    # Check if file exists first
    import os
    if not os.path.exists('configs/gcp-oauth.keys.json'):
        print('❌ Error: Cannot find configs/gcp-oauth.keys.json file')
        print('Please ensure the filename is correct and in the appropriate directory')
    else:
        manual_oauth_flow_debug()