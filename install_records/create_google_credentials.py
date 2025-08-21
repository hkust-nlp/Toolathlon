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
        # 创建Flow对象
        flow = Flow.from_client_secrets_file(
            'configs/gcp-oauth.keys.json',
            scopes=SCOPES,
            redirect_uri='http://localhost:3000/oauth2callback'
        )
        
        # 生成授权URL
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        print('='*60)
        print('OAuth2 授权步骤：')
        print('='*60)
        print(f'\n1. 请复制下面的URL到浏览器中打开：\n')
        print(auth_url)
        print(f'\n2. 在浏览器中：')
        print('   - 登录你的Google账号')
        print('   - 同意所有权限请求')
        print('   - 浏览器会跳转到 http://localhost:3000/oauth2callback?code=...')
        print('   - 页面可能显示"无法访问此网站"，这是正常的！')
        print(f'\n3. 重要：复制浏览器地址栏中的【完整URL】')
        print('   URL应该类似这样：')
        print('   http://localhost:3000/oauth2callback?code=4/0AeaYSH...&scope=...')
        
        redirect_response = input('\n请粘贴完整的URL（包括http://开头）: ').strip()
        
        # 尝试多种方式解析code
        code = None
        
        # 方法1：从完整URL解析
        if redirect_response.startswith('http'):
            parsed_url = urlparse(redirect_response)
            params = parse_qs(parsed_url.query)
            code = params.get('code', [None])[0]
        
        # 方法2：如果用户只粘贴了code部分
        elif redirect_response.startswith('4/'):
            code = redirect_response
        
        # 方法3：从问号后的参数解析
        elif 'code=' in redirect_response:
            params = parse_qs(redirect_response.split('?')[-1])
            code = params.get('code', [None])[0]
        
        if not code:
            print('\n❌ 错误：无法从URL中提取授权码')
            print('请确保复制了完整的重定向URL')
            return None
        
        print(f'\n✅ 成功提取授权码: {code[:20]}...')
        print('正在交换token...')
        
        # 交换code获取token
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        
        # 检查是否获得了refresh_token
        if not credentials.refresh_token:
            print('\n⚠️ 警告：未获得refresh_token')
            print('可能需要：')
            print('1. 在Google账号设置中撤销此应用的访问权限')
            print('2. 重新运行此脚本')
        
        # 保存credentials
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
        
        print('\n✅ 成功！./configs/gooele_credentials.json 已生成')
        print(f'Token: {credentials.token[:30]}...')
        if credentials.refresh_token:
            print(f'Refresh Token: {credentials.refresh_token[:30]}...')
        
        return credentials_data
        
    except Exception as e:
        print(f'\n❌ 发生错误: {str(e)}')
        print('\n可能的原因：')
        print('1. 授权码已过期（请重新开始流程）')
        print('2. redirect_uri不匹配')
        print('3. 网络连接问题')
        return None

if __name__ == '__main__':
    # 先检查文件是否存在
    import os
    if not os.path.exists('configs/gcp-oauth.keys.json'):
        print('❌ 错误：找不到 configs/gcp-oauth.keys.json 文件')
        print('请确保文件名正确并在对应目录下')
    else:
        manual_oauth_flow_debug()