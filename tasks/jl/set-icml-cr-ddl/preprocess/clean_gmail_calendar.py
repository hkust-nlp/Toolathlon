import email
from annotated_types import Len
from utils.data_processing.process_ops import copy_multiple_times
from utils.general.helper import run_command
from argparse import ArgumentParser
import os
import asyncio

import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def clean_emails(credentials_file):
    """清理所有邮件 - 优先尝试删除，失败则移到回收站"""
    
    print("=" * 60)
    print("Gmail 邮件清理")
    print("=" * 60)
    
    # 加载凭证
    with open(credentials_file, 'r') as f:
        cred_data = json.load(f)
    
    creds = Credentials(
        token=cred_data.get('token'),
        refresh_token=cred_data.get('refresh_token'),
        token_uri=cred_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
        client_id=cred_data.get('client_id'),
        client_secret=cred_data.get('client_secret')
    )
    
    # 刷新 token
    if creds.expired:
        print("正在刷新访问令牌...")
        creds.refresh(Request())
    
    # 构建 Gmail 服务
    gmail = build('gmail', 'v1', credentials=creds)
    
    try:
        # 获取用户信息
        profile = gmail.users().getProfile(userId='me').execute()
        print(f"账户: {profile.get('emailAddress')}")
        
        total_deleted = 0
        total_trashed = 0
        can_delete = None  # 用于记住是否可以删除
        page_token = None
        
        print("\n开始清理邮件...")
        
        while True:
            # 获取邮件列表
            results = gmail.users().messages().list(
                userId='me',
                pageToken=page_token,
                maxResults=500
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                print("⚠️ 无邮件！直接退出！")
                break
            
            # 如果还未测试删除能力，先用批量删除测试
            if can_delete is None and len(messages) > 0:
                try:
                    # 尝试批量删除
                    message_ids = [msg['id'] for msg in messages[:10]]  # 先试10个
                    gmail.users().messages().batchDelete(
                        userId='me',
                        body={'ids': message_ids}
                    ).execute()
                    can_delete = True
                    total_deleted += len(message_ids)
                    print("✅ 检测到删除权限，将永久删除邮件")
                    
                    # 删除剩余的
                    if len(messages) > 10:
                        remaining_ids = [msg['id'] for msg in messages[10:]]
                        for i in range(0, len(remaining_ids), 1000):
                            batch = remaining_ids[i:i+1000]
                            gmail.users().messages().batchDelete(
                                userId='me',
                                body={'ids': batch}
                            ).execute()
                            total_deleted += len(batch)
                            
                except HttpError as e:
                    if e.resp.status == 403:
                        can_delete = False
                        print("⚠️  没有删除权限，将改为移到回收站")
                        # 这批邮件改为移到回收站
                        for msg in messages:
                            try:
                                gmail.users().messages().trash(
                                    userId='me',
                                    id=msg['id']
                                ).execute()
                                total_trashed += 1
                            except:
                                pass
                    else:
                        raise e
            else:
                # 根据已知的权限处理
                if can_delete:
                    # 批量删除
                    message_ids = [msg['id'] for msg in messages]
                    for i in range(0, len(message_ids), 1000):
                        batch = message_ids[i:i+1000]
                        try:
                            gmail.users().messages().batchDelete(
                                userId='me',
                                body={'ids': batch}
                            ).execute()
                            total_deleted += len(batch)
                        except:
                            # 如果批量失败，尝试单个删除
                            for msg_id in batch:
                                try:
                                    gmail.users().messages().delete(
                                        userId='me',
                                        id=msg_id
                                    ).execute()
                                    total_deleted += 1
                                except:
                                    pass
                else:
                    # 移到回收站
                    for msg in messages:
                        try:
                            gmail.users().messages().trash(
                                userId='me',
                                id=msg['id']
                            ).execute()
                            total_trashed += 1
                        except:
                            pass
            
            # 显示进度
            total_processed = total_deleted + total_trashed
            if total_processed % 100 == 0:
                if can_delete:
                    print(f"  已删除: {total_deleted} 封邮件...")
                else:
                    print(f"  已移到回收站: {total_trashed} 封邮件...")
            
            # 获取下一页
            page_token = results.get('nextPageToken')
            if not page_token:
                break
        
        print(f"\n✅ 邮件清理完成！")
        if total_deleted > 0:
            print(f"   永久删除: {total_deleted} 封")
        if total_trashed > 0:
            print(f"   移到回收站: {total_trashed} 封（30天后自动删除）")
        
    except HttpError as e:
        print(f"❌ Gmail API 错误: {e}")

def delete_all_calendar_events(credentials_file):
    """删除所有可以删除的日历事件"""
    
    print("\n" + "=" * 60)
    print("Google Calendar 清理")
    print("=" * 60)
    
    # 加载凭证
    with open(credentials_file, 'r') as f:
        cred_data = json.load(f)
    
    creds = Credentials(
        token=cred_data.get('token'),
        refresh_token=cred_data.get('refresh_token'),
        token_uri=cred_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
        client_id=cred_data.get('client_id'),
        client_secret=cred_data.get('client_secret')
    )
    
    if creds.expired:
        creds.refresh(Request())
    
    # 构建日历服务
    calendar = build('calendar', 'v3', credentials=creds)
    
    # 获取日历列表
    calendar_list = calendar.calendarList().list().execute()
    
    total_deleted = 0
    total_failed = 0
    
    for cal_item in calendar_list.get('items', []):
        calendar_id = cal_item['id']
        calendar_name = cal_item.get('summary', 'Unknown')
        
        print(f"\n📅 处理日历: {calendar_name}")
        
        page_token = None
        cal_deleted = 0
        cal_failed = 0
        
        while True:
            try:
                # 获取事件列表
                events_result = calendar.events().list(
                    calendarId=calendar_id,
                    pageToken=page_token,
                    maxResults=250,
                    singleEvents=True,
                    showDeleted=False
                ).execute()
                
                events = events_result.get('items', [])
                
                if not events:
                    break
                
                for event in events:
                    event_id = event['id']
                    
                    # 尝试删除
                    try:
                        calendar.events().delete(
                            calendarId=calendar_id,
                            eventId=event_id
                        ).execute()
                        
                        cal_deleted += 1
                        total_deleted += 1
                        
                        # 每50个事件显示一次进度
                        if cal_deleted % 50 == 0:
                            print(f"   已删除 {cal_deleted} 个事件...")
                            
                    except:
                        # 删除失败，静默处理
                        cal_failed += 1
                        total_failed += 1
                
                page_token = events_result.get('nextPageToken')
                if not page_token:
                    break
                    
            except Exception as e:
                print(f"   ❌ 获取事件列表失败: {e}")
                break
        
        # 显示每个日历的统计
        if cal_deleted > 0 or cal_failed > 0:
            print(f"   📊 完成: 删除 {cal_deleted} 个，失败 {cal_failed} 个")
    
    # 显示总体统计
    print("\n" + "=" * 60)
    print("📊 日历清理统计")
    print("=" * 60)
    print(f"✅ 成功删除: {total_deleted} 个事件")
    print(f"❌ 无法删除: {total_failed} 个事件（可能是订阅内容）")

def delete_main(credentials_file):
    """主函数"""
    print("Google 账户清理工具")
    print("=" * 60)
    print("功能：")
    print("1. 清理所有邮件（优先永久删除，否则移到回收站）")
    print("2. 删除所有可删除的日历事件")
    print("=" * 60)
    
    # confirmation = input("\n确认继续？(yes/no): ")
    confirmation = "yes"
    
    if confirmation.lower() != 'yes':
        print("操作已取消")
        return
    
    try:
        # 处理邮件
        clean_emails(credentials_file)
        
        # 处理日历
        delete_all_calendar_events(credentials_file)
        
        print("\n✅ 所有操作完成！")
        
    except FileNotFoundError:
        print("❌ 找不到 credentials.json 文件")
    except Exception as e:
        print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--credentials_file", type=str, default="./configs/credentials.json")
    args = parser.parse_args()
    delete_main(args.credentials_file)