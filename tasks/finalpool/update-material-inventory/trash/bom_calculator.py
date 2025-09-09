#!/usr/bin/env python3
"""
BOM计算器 - 根据物料清单计算原材料需求
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class BOMItem:
    """BOM项目"""
    product_sku: str
    product_name: str
    material_id: str
    material_name: str
    unit_consumption: float
    unit: str

@dataclass
class MaterialRequirement:
    """原材料需求"""
    material_id: str
    material_name: str
    required_quantity: float
    unit: str
    current_stock: float
    sufficient: bool

class BOMCalculator:
    """BOM计算器"""
    
    def __init__(self, sheets_client=None):
        """
        初始化BOM计算器
        
        Args:
            sheets_client: Google Sheets客户端
        """
        self.sheets_client = sheets_client
        self.logger = self._setup_logging()
        self.bom_data = {}  # {product_sku: [BOMItem, ...]}
        self.inventory_data = {}  # {material_id: {name, current_stock, unit, min_stock, supplier}}
        
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)
    
    def load_bom_from_sheets(self, spreadsheet_id: str) -> bool:
        """从Google Sheets加载BOM数据"""
        if not self.sheets_client:
            self.logger.error("未提供Google Sheets客户端")
            return False
            
        try:
            self.logger.info("📊 从Google Sheets加载BOM数据...")
            
            # 获取BOM工作表数据
            result = self.sheets_client.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='BOM!A2:F1000'  # 跳过标题行
            ).execute()
            
            values = result.get('values', [])
            self.bom_data = {}
            
            for row in values:
                if len(row) >= 6:
                    product_sku = row[0].strip()
                    product_name = row[1].strip()
                    material_id = row[2].strip()
                    material_name = row[3].strip()
                    
                    try:
                        unit_consumption = float(row[4])
                        unit = row[5].strip()
                        
                        bom_item = BOMItem(
                            product_sku=product_sku,
                            product_name=product_name,
                            material_id=material_id,
                            material_name=material_name,
                            unit_consumption=unit_consumption,
                            unit=unit
                        )
                        
                        if product_sku not in self.bom_data:
                            self.bom_data[product_sku] = []
                        self.bom_data[product_sku].append(bom_item)
                        
                    except ValueError as e:
                        self.logger.warning(f"跳过无效行数据: {row} - {e}")
                        continue
            
            self.logger.info(f"✅ 成功加载 {len(self.bom_data)} 个产品的BOM数据")
            return True
            
        except Exception as e:
            self.logger.error(f"加载BOM数据失败: {e}")
            return False
    
    def load_inventory_from_sheets(self, spreadsheet_id: str) -> bool:
        """从Google Sheets加载库存数据"""
        if not self.sheets_client:
            self.logger.error("未提供Google Sheets客户端")
            return False
            
        try:
            self.logger.info("📦 从Google Sheets加载库存数据...")
            
            # 获取库存工作表数据
            result = self.sheets_client.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='Material_Inventory!A2:F1000'  # 跳过标题行
            ).execute()
            
            values = result.get('values', [])
            self.inventory_data = {}
            
            for row in values:
                if len(row) >= 6:
                    material_id = row[0].strip()
                    material_name = row[1].strip()
                    
                    try:
                        current_stock = float(row[2])
                        unit = row[3].strip()
                        min_stock = float(row[4])
                        supplier = row[5].strip()
                        
                        self.inventory_data[material_id] = {
                            'name': material_name,
                            'current_stock': current_stock,
                            'unit': unit,
                            'min_stock': min_stock,
                            'supplier': supplier
                        }
                        
                    except ValueError as e:
                        self.logger.warning(f"跳过无效库存数据: {row} - {e}")
                        continue
            
            self.logger.info(f"✅ 成功加载 {len(self.inventory_data)} 种原材料库存数据")
            return True
            
        except Exception as e:
            self.logger.error(f"加载库存数据失败: {e}")
            return False
    
    def calculate_material_requirements(self, order_items: List[Dict]) -> List[MaterialRequirement]:
        """
        计算订单的原材料需求
        
        Args:
            order_items: 订单项目列表 [{'sku': str, 'quantity': int}, ...]
            
        Returns:
            原材料需求列表
        """
        self.logger.info("🧮 计算原材料需求...")
        
        # 汇总所有原材料需求
        material_requirements = {}  # {material_id: total_required}
        
        for item in order_items:
            sku = item['sku']
            quantity = item['quantity']
            
            if sku not in self.bom_data:
                self.logger.warning(f"未找到产品 {sku} 的BOM数据")
                continue
            
            self.logger.info(f"  处理产品: {sku} x{quantity}")
            
            # 计算该产品需要的原材料
            for bom_item in self.bom_data[sku]:
                material_id = bom_item.material_id
                required_per_unit = bom_item.unit_consumption
                total_required = required_per_unit * quantity
                
                if material_id in material_requirements:
                    material_requirements[material_id] += total_required
                else:
                    material_requirements[material_id] = total_required
                
                self.logger.info(f"    - {bom_item.material_name}: {total_required} {bom_item.unit}")
        
        # 构建需求列表，检查库存是否充足
        requirements = []
        for material_id, required_qty in material_requirements.items():
            inventory_info = self.inventory_data.get(material_id, {})
            current_stock = inventory_info.get('current_stock', 0)
            material_name = inventory_info.get('name', material_id)
            unit = inventory_info.get('unit', '个')
            
            sufficient = current_stock >= required_qty
            
            requirements.append(MaterialRequirement(
                material_id=material_id,
                material_name=material_name,
                required_quantity=required_qty,
                unit=unit,
                current_stock=current_stock,
                sufficient=sufficient
            ))
            
            status = "✅ 充足" if sufficient else "❌ 不足"
            self.logger.info(f"  {material_name}: 需要 {required_qty} {unit}, 库存 {current_stock} {unit} {status}")
        
        return requirements
    
    def check_order_feasibility(self, order_items: List[Dict]) -> Tuple[bool, List[MaterialRequirement]]:
        """
        检查订单是否可以完成（原材料是否充足）
        
        Args:
            order_items: 订单项目列表
            
        Returns:
            (是否可行, 原材料需求列表)
        """
        requirements = self.calculate_material_requirements(order_items)
        
        # 检查是否所有原材料都充足
        feasible = all(req.sufficient for req in requirements)
        
        if feasible:
            self.logger.info("✅ 订单可以完成，原材料充足")
        else:
            insufficient_materials = [req for req in requirements if not req.sufficient]
            self.logger.warning(f"❌ 订单无法完成，{len(insufficient_materials)} 种原材料不足:")
            for req in insufficient_materials:
                shortage = req.required_quantity - req.current_stock
                self.logger.warning(f"  - {req.material_name}: 缺少 {shortage} {req.unit}")
        
        return feasible, requirements
    
    def update_inventory_after_order(self, spreadsheet_id: str, requirements: List[MaterialRequirement]) -> bool:
        """
        订单完成后更新库存数据
        
        Args:
            spreadsheet_id: 电子表格ID
            requirements: 原材料需求列表
            
        Returns:
            更新是否成功
        """
        if not self.sheets_client:
            self.logger.error("未提供Google Sheets客户端")
            return False
            
        try:
            self.logger.info("📝 更新库存数据...")
            
            # 准备批量更新数据
            updates = []
            
            for req in requirements:
                if not req.sufficient:
                    self.logger.warning(f"跳过原材料不足的项目: {req.material_name}")
                    continue
                
                # 计算新的库存量
                new_stock = req.current_stock - req.required_quantity
                
                # 找到该原材料在表格中的行号
                # 这里需要重新读取数据来找到正确的行号
                result = self.sheets_client.service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range='Material_Inventory!A:A'
                ).execute()
                
                values = result.get('values', [])
                row_index = None
                
                for i, row in enumerate(values):
                    if row and row[0] == req.material_id:
                        row_index = i + 1  # Google Sheets行号从1开始
                        break
                
                if row_index:
                    # 更新库存数量（第C列）
                    updates.append({
                        'range': f'Material_Inventory!C{row_index}',
                        'values': [[str(new_stock)]]
                    })
                    
                    # 更新本地缓存
                    self.inventory_data[req.material_id]['current_stock'] = new_stock
                    
                    self.logger.info(f"  {req.material_name}: {req.current_stock} → {new_stock} {req.unit}")
            
            # 批量更新
            if updates:
                body = {
                    'valueInputOption': 'RAW',
                    'data': updates
                }
                
                self.sheets_client.service.spreadsheets().values().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()
                
                self.logger.info(f"✅ 成功更新 {len(updates)} 个库存项目")
                return True
            else:
                self.logger.info("没有需要更新的库存项目")
                return True
                
        except Exception as e:
            self.logger.error(f"更新库存数据失败: {e}")
            return False
    
    def calculate_max_production_capacity(self) -> Dict[str, int]:
        """
        根据当前库存计算所有产品的最大生产能力
        
        Returns:
            {product_sku: max_quantity}
        """
        self.logger.info("🏭 计算最大生产能力...")
        
        max_production = {}
        
        for product_sku, bom_items in self.bom_data.items():
            # 计算该产品受各种原材料限制的最大生产数量
            max_qty = float('inf')
            
            for bom_item in bom_items:
                material_id = bom_item.material_id
                unit_consumption = bom_item.unit_consumption
                
                inventory_info = self.inventory_data.get(material_id, {})
                current_stock = inventory_info.get('current_stock', 0)
                
                # 计算该原材料能支持的最大生产数量
                if unit_consumption > 0:
                    material_limit = int(current_stock / unit_consumption)
                    max_qty = min(max_qty, material_limit)
            
            # 如果没有限制或者计算出无限大，设为0
            if max_qty == float('inf'):
                max_qty = 0
            
            max_production[product_sku] = max_qty
            
            self.logger.info(f"  {product_sku}: 最大可生产 {max_qty} 个")
        
        return max_production

if __name__ == "__main__":
    # 测试BOM计算器
    calculator = BOMCalculator()
    
    # 模拟一些数据进行测试
    calculator.bom_data = {
        'CHAIR_001': [
            BOMItem('CHAIR_001', '经典木椅', 'WOOD_OAK', '橡木板材', 2.5, '平方米'),
            BOMItem('CHAIR_001', '经典木椅', 'SCREW_M6', 'M6螺丝', 8, '个'),
        ]
    }
    
    calculator.inventory_data = {
        'WOOD_OAK': {'name': '橡木板材', 'current_stock': 50.0, 'unit': '平方米', 'min_stock': 10.0, 'supplier': '供应商A'},
        'SCREW_M6': {'name': 'M6螺丝', 'current_stock': 1000, 'unit': '个', 'min_stock': 200, 'supplier': '供应商B'}
    }
    
    # 测试订单
    test_order = [{'sku': 'CHAIR_001', 'quantity': 3}]
    
    feasible, requirements = calculator.check_order_feasibility(test_order)
    print(f"订单可行性: {feasible}")
    
    max_production = calculator.calculate_max_production_capacity()
    print(f"最大生产能力: {max_production}")
