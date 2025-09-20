#!/usr/bin/env python3
"""
Google Sheets客户端 - 用于设置BOM和库存数据
"""

import json
import logging
import os
from typing import Dict, List, Optional
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import sys
import os
import asyncio
from argparse import ArgumentParser

sys.path.append(os.path.dirname(__file__))

from utils.app_specific.googlesheet.drive_helper import (
    get_google_service, find_folder_by_name, create_folder, 
    clear_folder, copy_sheet_to_folder
)

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

try:
    import gspread
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    
    # 尝试导入配置
    try:
        from token_key_session import all_token_key_session
        TARGET_FOLDER_ID = all_token_key_session.get('google_sheets_folder_id', "13K_oZ32wICyZUai_ETcwicAP2K2P0_pZ")
    except ImportError:
        TARGET_FOLDER_ID = "13K_oZ32wICyZUai_ETcwicAP2K2P0_pZ"  # 备用硬编码值
        
except ImportError as e:
    print(f"Warning: Google API dependencies not available: {e}")
    gspread = None
    service_account = None
    TARGET_FOLDER_ID = "13K_oZ32wICyZUai_ETcwicAP2K2P0_pZ"

# Google Sheets API范围
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
SA_KEY_FILE_PATH = 'configs/credentials.json'
TARGET_SPREADSHEET_NAME = "Material_Inventory"

class GoogleSheetsClient:
    """Google Sheets客户端"""
    
    def __init__(self, credentials_file: str = SA_KEY_FILE_PATH):
        """
        初始化Google Sheets客户端
        
        Args:
            credentials_file: 服务账号凭据文件路径
        """
        self.credentials_file = credentials_file
        self.service = None
        self.drive_service = None  # Drive API 服务
        self.gc = None  # gspread客户端
        self.logger = self._setup_logging()
        
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)
    
    def authenticate(self) -> bool:
        """
        认证Google Sheets API - 使用服务账号凭证
        
        Returns:
            认证是否成功
        """
        try:
            self.logger.info("正在使用服务账号认证Google服务...")
            with open(self.credentials_file, 'r') as f:
                creds_data = json.load(f)
        
        # 创建OAuth2凭证对象
            credentials = Credentials(
                token=creds_data.get('token'),
                refresh_token=creds_data.get('refresh_token'),
                token_uri=creds_data.get('token_uri'),
                client_id=creds_data.get('client_id'),
                client_secret=creds_data.get('client_secret'),
                scopes=creds_data.get('scopes', SCOPES)
            )
            # 使用服务账号凭证文件创建凭证
            # credentials = service_account.Credentials.from_service_account_file(
            #     self.credentials_file, scopes=SCOPES)
            
            # 构建Google Sheets API服务
            self.service = build('sheets', 'v4', credentials=credentials)
            
            # 构建Google Drive API服务
            self.drive_service = build('drive', 'v3', credentials=credentials)
            
            # 同时初始化gspread客户端
            self.gc = gspread.authorize(credentials)
            self.logger.info("✓ Google Sheets API认证成功")
            return True
            
        except FileNotFoundError:
            self.logger.error(f"错误：找不到服务账号凭证文件 '{self.credentials_file}'")
            return False
        except json.JSONDecodeError:
            self.logger.error(f"错误：服务账号凭证文件格式错误 '{self.credentials_file}'")
            return False
        except Exception as e:
            self.logger.error(f"Google服务认证失败: {e}")
            return False
    
    def check_folder_access(self, folder_id: str) -> bool:
        """
        检查是否可以访问指定文件夹
        
        Args:
            folder_id: 文件夹ID
            
        Returns:
            是否可以访问
        """
        if not self.drive_service:
            self.logger.error("Drive服务未初始化")
            return False
            
        try:
            folder = self.drive_service.files().get(fileId=folder_id, fields='id,name,mimeType').execute()
            if folder.get('mimeType') == 'application/vnd.google-apps.folder':
                self.logger.info(f"文件夹访问成功: {folder.get('name')} ({folder_id})")
                return True
            else:
                self.logger.error(f"指定ID不是文件夹: {folder.get('mimeType')}")
                return False
                
        except HttpError as error:
            self.logger.error(f"无法访问文件夹 {folder_id}: {error}")
            return False
        except Exception as e:
            self.logger.error(f"检查文件夹访问权限时发生错误: {e}")
            return False
    
    def move_to_folder(self, file_id: str, folder_id: str) -> bool:
        """
        将文件移动到指定文件夹
        
        Args:
            file_id: 文件ID
            folder_id: 目标文件夹ID
            
        Returns:
            移动是否成功
        """
        if not self.drive_service:
            self.logger.error("Drive服务未初始化")
            return False
            
        try:
            self.logger.info(f"开始移动文件 {file_id} 到文件夹 {folder_id}")
            
            # 获取当前文件的父文件夹
            file = self.drive_service.files().get(fileId=file_id, fields='parents').execute()
            previous_parents = ",".join(file.get('parents', []))
            self.logger.info(f"当前父文件夹: {previous_parents}")
            
            # 移动文件到新文件夹
            file = self.drive_service.files().update(
                fileId=file_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            
            new_parents = ",".join(file.get('parents', []))
            self.logger.info(f"文件 {file_id} 成功移动到文件夹 {folder_id}，新父文件夹: {new_parents}")
            return True
            
        except HttpError as error:
            self.logger.error(f"移动文件失败: {error}")
            self.logger.error(f"错误详情: {error.resp.status} - {error.content}")
            return False
        except Exception as e:
            self.logger.error(f"移动文件时发生未预期错误: {e}")
            return False
    
    def create_test_spreadsheet(self, title: str = "Material Inventory Management Test") -> Optional[str]:
        """
        创建测试电子表格
        
        Args:
            title: 电子表格标题
            
        Returns:
            电子表格ID，失败返回None
        """
        if not self.service:
            self.logger.error("服务未初始化")
            return None
        
        try:
            spreadsheet = {
                'properties': {
                    'title': title
                },
                'sheets': [
                    {
                        'properties': {
                            'title': 'BOM',
                            'gridProperties': {
                                'rowCount': 1000,
                                'columnCount': 26
                            }
                        }
                    },
                    {
                        'properties': {
                            'title': 'Material_Inventory',
                            'gridProperties': {
                                'rowCount': 1000,
                                'columnCount': 26
                            }
                        }
                    }
                ]
            }
            
            result = self.service.spreadsheets().create(body=spreadsheet).execute()
            spreadsheet_id = result.get('spreadsheetId')
            
            # 将新创建的表格移动到指定文件夹
            if spreadsheet_id and TARGET_FOLDER_ID:
                self.logger.info(f"尝试将表格 {spreadsheet_id} 移动到文件夹 {TARGET_FOLDER_ID}")
                
                # 先检查文件夹是否可以访问
                if not self.check_folder_access(TARGET_FOLDER_ID):
                    self.logger.error(f"无法访问目标文件夹 {TARGET_FOLDER_ID}，跳过移动操作")
                elif self.move_to_folder(spreadsheet_id, TARGET_FOLDER_ID):
                    self.logger.info(f"表格成功移动到指定文件夹: {TARGET_FOLDER_ID}")
                else:
                    self.logger.warning("表格创建成功但移动到指定文件夹失败")
            elif not TARGET_FOLDER_ID:
                self.logger.warning("TARGET_FOLDER_ID 未设置，跳过移动表格")
            else:
                self.logger.warning("spreadsheet_id 为空，无法移动表格")
            
            self.logger.info(f"创建电子表格成功: {spreadsheet_id}")
            return spreadsheet_id
            
        except HttpError as error:
            self.logger.error(f"创建电子表格失败: {error}")
            return None
    
    def setup_bom_data(self, spreadsheet_id: str) -> bool:
        """
        设置BOM数据
        
        Args:
            spreadsheet_id: 电子表格ID
            
        Returns:
            设置是否成功
        """
        if not self.service:
            self.logger.error("服务未初始化")
            return False
        
        # BOM data
        bom_data = [
            ['Product SKU', 'Product Name', 'Material ID', 'Material Name', 'Unit Usage', 'Unit'],
            ['CHAIR_001', 'Classic Wooden Chair', 'WOOD_OAK', 'Oak Wood Board', '2.5', 'sqm'],
            ['CHAIR_001', 'Classic Wooden Chair', 'SCREW_M6', 'M6 Screw', '8', 'pcs'],
            ['CHAIR_001', 'Classic Wooden Chair', 'GLUE_WOOD', 'Wood Glue', '0.1', 'L'],
            ['CHAIR_001', 'Classic Wooden Chair', 'FINISH_VARNISH', 'Varnish', '0.2', 'L'],
            ['TABLE_001', 'Oak Dining Table', 'WOOD_OAK', 'Oak Wood Board', '5.0', 'sqm'],
            ['TABLE_001', 'Oak Dining Table', 'SCREW_M8', 'M8 Screw', '12', 'pcs'],
            ['TABLE_001', 'Oak Dining Table', 'GLUE_WOOD', 'Wood Glue', '0.3', 'L'],
            ['TABLE_001', 'Oak Dining Table', 'FINISH_VARNISH', 'Varnish', '0.5', 'L'],
            ['DESK_001', 'Office Desk', 'WOOD_PINE', 'Pine Wood Board', '3.0', 'sqm'],
            ['DESK_001', 'Office Desk', 'METAL_LEG', 'Metal Table Leg', '4', 'pcs'],
            ['DESK_001', 'Office Desk', 'SCREW_M6', 'M6 Screw', '16', 'pcs'],
            ['DESK_001', 'Office Desk', 'FINISH_PAINT', 'Paint', '0.3', 'L']
        ]
        
        try:
            body = {
                'values': bom_data
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='BOM!A1',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            self.logger.info(f"BOM数据设置成功，更新了 {result.get('updatedCells')} 个单元格")
            return True
            
        except HttpError as error:
            self.logger.error(f"设置BOM数据失败: {error}")
            return False
    
    def setup_inventory_data(self, spreadsheet_id: str) -> bool:
        """
        设置库存数据
        
        Args:
            spreadsheet_id: 电子表格ID
            
        Returns:
            设置是否成功
        """
        if not self.service:
            self.logger.error("服务未初始化")
            return False
        
        inventory_data = [
            ['Material ID', 'Material Name', 'Current Stock', 'Unit', 'Min Stock', 'Supplier'],
            ['WOOD_OAK', 'Oak Wood Board', '250.0', 'sqm', '10.0', 'Wood Supplier A'],
            ['SCREW_M6', 'M6 Screw', '600', 'pcs', '200', 'Hardware Supplier A'],
            ['SCREW_M8', 'M8 Screw', '450', 'pcs', '150', 'Hardware Supplier A'],
            ['GLUE_WOOD', 'Wood Glue', '15.0', 'L', '1.0', 'Chemical Supplier'],
            ['FINISH_VARNISH', 'Varnish', '25.0', 'L', '0.5', 'Paint Supplier'],
            ['WOOD_PINE', 'Pine Wood Board', '100.0', 'sqm', '8.0', 'Wood Supplier B'],
            ['METAL_LEG', 'Metal Table Leg', '100', 'pcs', '5', 'Metal Factory'],
            ['FINISH_PAINT', 'Paint', '10.0', 'L', '0.5', 'Paint Supplier']
        ]
        
        try:
            body = {
                'values': inventory_data
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='Material_Inventory!A1',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            self.logger.info(f"库存数据设置成功，更新了 {result.get('updatedCells')} 个单元格")
            return True
            
        except HttpError as error:
            self.logger.error(f"设置库存数据失败: {error}")
            return False
    
    def find_spreadsheets_in_folder(self, folder_id: str) -> List[Dict[str, str]]:
        """
        在指定文件夹中查找所有的 Google Sheets
        
        Args:
            folder_id: 文件夹ID
            
        Returns:
            包含 spreadsheet 信息的列表，每个元素包含 'id' 和 'name'
        """
        if not self.drive_service:
            self.logger.error("Drive服务未初始化")
            return []
            
        try:
            # 查找文件夹中的所有 Google Sheets
            query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'"
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name)"
            ).execute()
            
            files = results.get('files', [])
            self.logger.info(f"在文件夹 {folder_id} 中找到 {len(files)} 个电子表格")
            
            for file in files:
                self.logger.info(f"  - {file['name']} ({file['id']})")
            
            return files
            
        except HttpError as error:
            self.logger.error(f"查找文件夹中的电子表格失败: {error}")
            return []
        except Exception as e:
            self.logger.error(f"查找电子表格时发生错误: {e}")
            return []
    
    def find_spreadsheet_by_name_pattern(self, folder_id: str, name_pattern: str = None) -> Optional[str]:
        """
        在文件夹中根据名称模式查找特定的 spreadsheet
        
        Args:
            folder_id: 文件夹ID
            name_pattern: 名称模式，默认查找包含 'Material_Inventory' 或 'inventory' 的表格
            
        Returns:
            找到的 spreadsheet ID，未找到返回 None
        """
        spreadsheets = self.find_spreadsheets_in_folder(folder_id)
        
        if not spreadsheets:
            return None
        
        # 如果只有一个电子表格，直接返回
        if len(spreadsheets) == 1:
            self.logger.info(f"文件夹中只有一个电子表格，使用: {spreadsheets[0]['name']}")
            return spreadsheets[0]['id']
        
        # 根据名称模式查找
        if name_pattern is None:
            # 默认查找包含库存相关关键词的表格
            patterns = ['Material_Inventory', 'material_inventory', 'inventory', 'Inventory', '库存', '原材料']
        else:
            patterns = [name_pattern]
        
        for pattern in patterns:
            for sheet in spreadsheets:
                if pattern.lower() in sheet['name'].lower():
                    self.logger.info(f"找到匹配的电子表格: {sheet['name']} (模式: {pattern})")
                    return sheet['id']
        
        # 如果没有找到匹配的，返回第一个
        self.logger.warning(f"未找到匹配模式的电子表格，使用第一个: {spreadsheets[0]['name']}")
        return spreadsheets[0]['id']

    def get_current_inventory(self, folder_or_spreadsheet_id: str) -> Dict[str, float]:
        """
        获取当前库存数据
        
        Args:
            folder_or_spreadsheet_id: 文件夹ID或电子表格ID
            
        Returns:
            库存数据字典
        """
        if not self.service:
            self.logger.error("服务未初始化")
            return {}
        
        spreadsheet_id = folder_or_spreadsheet_id
        
        # 首先尝试检测这是否是一个文件夹ID
        try:
            # 检查是否是文件夹
            if self.drive_service:
                file_info = self.drive_service.files().get(
                    fileId=folder_or_spreadsheet_id, 
                    fields='mimeType,name'
                ).execute()
                
                if file_info.get('mimeType') == 'application/vnd.google-apps.folder':
                    self.logger.info(f"检测到文件夹ID: {folder_or_spreadsheet_id}")
                    # 在文件夹中查找电子表格
                    spreadsheet_id = self.find_spreadsheet_by_name_pattern(folder_or_spreadsheet_id)
                    if not spreadsheet_id:
                        self.logger.error("在文件夹中未找到电子表格")
                        return {}
                    self.logger.info(f"使用电子表格ID: {spreadsheet_id}")
                else:
                    self.logger.info(f"使用直接的电子表格ID: {folder_or_spreadsheet_id}")
        except Exception as e:
            # 如果无法检测类型，假设是电子表格ID
            self.logger.warning(f"无法检测文件类型，假设为电子表格ID: {e}")
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='Material_Inventory!A2:C100'
            ).execute()
            
            values = result.get('values', [])
            inventory = {}
            
            for row in values:
                if len(row) >= 3:
                    material_id = row[0]
                    try:
                        current_stock = float(row[2])
                        inventory[material_id] = current_stock
                    except (ValueError, TypeError):
                        continue
            
            return inventory
            
        except HttpError as error:
            self.logger.error(f"获取库存数据失败: {error}")
            return {}

import os

if __name__ == "__main__":
    # 测试Google Sheets客户端
    client = GoogleSheetsClient()
    
    # 认证
    if not client.authenticate():
        print("❌ Google Sheets认证失败")
        exit(1)
    
    # 创建测试电子表格
    spreadsheet_id = client.create_test_spreadsheet()
    if not spreadsheet_id:
        print("❌ 创建电子表格失败")
        exit(1)
    
    print(f"✅ 电子表格创建成功: {spreadsheet_id}")
    
    # 设置数据
    if client.setup_bom_data(spreadsheet_id):
        print("✅ BOM数据设置成功")
    else:
        print("❌ BOM数据设置失败")
    
    if client.setup_inventory_data(spreadsheet_id):
        print("✅ 库存数据设置成功")
    else:
        print("❌ 库存数据设置失败")
    
    # 保存电子表格ID
    config = {'spreadsheet_id': spreadsheet_id}
    with open('test_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"📄 配置已保存到 test_config.json")
    print(f"🔗 电子表格链接: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")


    GOOGLESHEET_URLS = [
    "https://docs.google.com/spreadsheets/d/1S9BFFHU262CjU87DnGFfP_LMChhAT4lx7uNvwY-7HoI",
    ]

    FOLDER_NAME = "update-material-inventory"

    drive_service, sheets_service = get_google_service()

    folder_id = find_folder_by_name(drive_service, FOLDER_NAME)
    if not folder_id:
        folder_id = create_folder(drive_service, FOLDER_NAME)
    clear_folder(drive_service, folder_id)

    for sheet_url in GOOGLESHEET_URLS:
        copy_sheet_to_folder(drive_service, sheet_url, folder_id)    
