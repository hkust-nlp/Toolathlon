#!/usr/bin/env python3
"""
Simple automated Google OAuth helper

This is a streamlined version that:
1. Starts a local server
2. Prints the auth URL
3. Waits for callback
4. Saves credentials
5. Exits

Perfect for integration into larger automation scripts.
"""

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from google_auth_oauthlib.flow import Flow

# Configuration
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://mail.google.com/',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/forms',
]

REDIRECT_URI = 'http://localhost:3000/oauth2callback'
SERVER_PORT = 3000

# Globals
auth_code = None
auth_error = None
server_instance = None


class SimpleOAuthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        global auth_code, auth_error
        parsed = urlparse(self.path)

        if parsed.path == '/oauth2callback':
            params = parse_qs(parsed.query)

            if 'code' in params:
                auth_code = params['code'][0]
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<html><body><h1>Success! You can close this window.</h1></body></html>')
            elif 'error' in params:
                auth_error = params['error'][0]
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<html><body><h1>Error! Check the terminal.</h1></body></html>')

            threading.Thread(target=lambda: self.shutdown_server(), daemon=True).start()

    def shutdown_server(self):
        import time
        time.sleep(0.5)
        if server_instance:
            server_instance.shutdown()


def run_oauth_flow(oauth_keys_path='configs/gcp-oauth.keys.json',
                   output_path='./configs/google_credentials.json',
                   auto_open_browser=True,
                   verbose=True):
    """
    Run OAuth flow and return credentials

    Args:
        oauth_keys_path: Path to OAuth keys JSON
        output_path: Where to save credentials
        auto_open_browser: Whether to auto-open browser
        verbose: Print status messages

    Returns:
        dict: Credentials data or None on failure
    """
    global auth_code, auth_error, server_instance

    if not os.path.exists(oauth_keys_path):
        if verbose:
            print(f'ERROR: {oauth_keys_path} not found', file=sys.stderr)
        return None

    try:
        # Get current gcloud account to pre-select it in OAuth flow
        import subprocess
        try:
            result = subprocess.run(
                ['gcloud', 'auth', 'list', '--format=value(account)', '--filter=status:ACTIVE'],
                capture_output=True,
                text=True,
                timeout=5
            )
            login_hint = result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            login_hint = None

        # Create flow
        flow = Flow.from_client_secrets_file(
            oauth_keys_path,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )

        # Generate auth URL with login_hint to pre-select account
        auth_url_params = {
            'access_type': 'offline',
            'include_granted_scopes': 'true',
            'prompt': 'consent'
        }

        # Add login_hint if we have it to pre-select the Google account
        if login_hint:
            auth_url_params['login_hint'] = login_hint
            if verbose:
                print(f'Pre-selecting Google account: {login_hint}')

        auth_url, _ = flow.authorization_url(**auth_url_params)

        # Start server
        server_instance = HTTPServer(('localhost', SERVER_PORT), SimpleOAuthHandler)
        server_thread = threading.Thread(target=server_instance.serve_forever, daemon=True)
        server_thread.start()

        if verbose:
            print('='*80)
            print('GOOGLE OAUTH AUTHORIZATION URL:')
            print('='*80)
            print(auth_url)
            print('='*80)
            print('Please open the URL above in a browser to authorize. You need to authorize all the requested permissions.')
            print('Waiting for authorization...')

        # Auto-open browser
        if auto_open_browser:
            try:
                import webbrowser
                webbrowser.open(auth_url)
            except:
                pass

        # Wait for callback
        server_instance.serve_forever()

        if auth_error:
            if verbose:
                print(f'ERROR: OAuth failed - {auth_error}', file=sys.stderr)
            return None

        if not auth_code:
            if verbose:
                print('ERROR: No authorization code received', file=sys.stderr)
            return None

        if verbose:
            print('Authorization code received, exchanging for tokens...')

        # Exchange code
        flow.fetch_token(code=auth_code)
        creds = flow.credentials

        # Build credentials dict
        creds_data = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': list(creds.scopes) if creds.scopes else SCOPES
        }

        # Save
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(creds_data, f, indent=2)

        if verbose:
            print(f'SUCCESS: Credentials saved to {output_path}')

        return creds_data

    except Exception as e:
        if verbose:
            print(f'ERROR: {e}', file=sys.stderr)
        return None
    finally:
        if server_instance:
            try:
                server_instance.shutdown()
            except:
                pass


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Automated Google OAuth')
    parser.add_argument('--oauth-keys', default='configs/gcp-oauth.keys.json',
                       help='Path to OAuth keys JSON')
    parser.add_argument('--output', default='./configs/google_credentials.json',
                       help='Path to save credentials')
    parser.add_argument('--no-browser', action='store_true',
                       help='Do not auto-open browser')
    parser.add_argument('--quiet', action='store_true',
                       help='Minimal output')

    args = parser.parse_args()

    result = run_oauth_flow(
        oauth_keys_path=args.oauth_keys,
        output_path=args.output,
        auto_open_browser=not args.no_browser,
        verbose=not args.quiet
    )

    sys.exit(0 if result else 1)
