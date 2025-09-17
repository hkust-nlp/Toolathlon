from typing import Dict
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime
import time

GOOGLE_CREDENTIAL_FILE = "configs/google_credentials.json"

def clear_google_forms(form_name_pattern: str = None) -> Dict:
    """
    根据Google Form名称删除所有匹配的表单
    
    Args:
        form_name_pattern: 表单名称模式，如果为None则删除所有表单
    
    Returns:
        删除结果字典
    """
    print("📝 开始清理Google Forms...")
    
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
            print(f"⚠️ 无法读取Google凭据配置文件: {e}")
            return {
                "success": False,
                "error": f"Google凭据配置错误: {e}",
                "timestamp": datetime.now().isoformat()
            }
        
        # 构建Google Drive服务
        drive_service = build('drive', 'v3', credentials=creds)
        
        # 构建查询字符串
        if form_name_pattern:
            query = f"name contains '{form_name_pattern}' and mimeType='application/vnd.google-apps.form'"
            print(f"🔍 查找包含 '{form_name_pattern}' 的Google Forms...")
        else:
            query = "mimeType='application/vnd.google-apps.form'"
            print("🔍 查找所有Google Forms...")
        
        # 查找所有匹配的Google Forms
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
                print(f"⚠️ 查询Google Forms时出错: {e}")
                break
        
        if not all_forms:
            print("📭 没有找到匹配的Google Forms")
            return {
                "success": True,
                "deleted_count": 0,
                "found_count": 0,
                "message": "没有找到匹配的表单",
                "timestamp": datetime.now().isoformat()
            }
        
        print(f"📋 找到 {len(all_forms)} 个匹配的Google Forms")
        
        # 删除找到的表单
        deleted_count = 0
        failed_count = 0
        deleted_forms = []
        
        for i, form in enumerate(all_forms, 1):
            form_id = form['id']
            form_name = form['name']
            created_time = form.get('createdTime', 'Unknown')
            
            try:
                # 删除表单
                drive_service.files().delete(fileId=form_id).execute()
                deleted_count += 1
                deleted_forms.append({
                    "id": form_id,
                    "name": form_name,
                    "created_time": created_time
                })
                print(f"   ✅ 删除表单 '{form_name}' (ID: {form_id}) [{i}/{len(all_forms)}]")
                
                # 添加短暂延迟避免API限制
                time.sleep(0.2)
                
            except Exception as e:
                failed_count += 1
                print(f"   ❌ 删除表单 '{form_name}' (ID: {form_id}) 失败: {e}")
        
        # 计算结果
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
        
        print(f"📊 Google Forms清理完成:")
        print(f"   找到表单: {len(all_forms)} 个")
        print(f"   成功删除: {deleted_count} 个")
        print(f"   删除失败: {failed_count} 个")
        
        if all_success:
            print("✅ Google Forms清理成功！")
        else:
            print("⚠️ Google Forms清理部分完成，有部分表单删除失败")
        
        return final_result
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        print(f"❌ Google Forms清理过程中出错: {e}")
        return error_result