import requests
from requests.auth import HTTPBasicAuth
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os

class WooCommerceClient:
    """WooCommerce API客户端 - 用于低销量产品筛选任务"""
    
    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str, version: str = "v3", 
                 wp_username: str = None, wp_password: str = None):
        """
        初始化WooCommerce客户端
        
        Args:
            site_url: WooCommerce网站URL (例如: https://your-site.com)
            consumer_key: WooCommerce API消费者密钥
            consumer_secret: WooCommerce API消费者密钥
            version: API版本 (默认: v3)
            wp_username: WordPress管理员用户名 (用于媒体上传)
            wp_password: WordPress管理员密码 (用于媒体上传)
        """
        self.site_url = site_url.rstrip('/')
        self.api_base = f"{self.site_url}/wp-json/wc/{version}"
        self.auth = HTTPBasicAuth(consumer_key, consumer_secret)
        self.session = requests.Session()
        self.session.auth = self.auth
        
        # WordPress用户认证 (用于媒体上传)
        self.wp_auth = None
        self.wp_username = wp_username
        self.wp_password = wp_password
        if wp_username and wp_password:
            self.wp_auth = HTTPBasicAuth(wp_username, wp_password)
        
        # API调用限制 (避免超过速率限制)
        self.request_delay = 0.5  # 每次请求间隔500ms
        self.last_request_time = 0
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Tuple[bool, Dict]:
        """
        发送API请求
        
        Args:
            method: HTTP方法 (GET, POST, PUT, DELETE)
            endpoint: API端点
            data: 请求数据
            params: URL参数
            
        Returns:
            (成功标志, 响应数据)
        """
        # 控制请求频率
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_delay:
            time.sleep(self.request_delay - time_since_last)
        
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        
        try:
            headers = {"Content-Type": "application/json"}
            
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, headers=headers)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, params=params, headers=headers)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, params=params, headers=headers)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, params=params, headers=headers)
            else:
                return False, {"error": f"不支持的HTTP方法: {method}"}
            
            self.last_request_time = time.time()
            
            response.raise_for_status()
            return True, response.json()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API请求失败: {str(e)}"
            if hasattr(e.response, 'text'):
                error_msg += f" - {e.response.text}"
            return False, {"error": error_msg}
    
    def get_product(self, product_id: str) -> Tuple[bool, Dict]:
        """获取商品信息"""
        return self._make_request('GET', f'products/{product_id}')
    
    def list_products(self, page: int = 1, per_page: int = 100, **kwargs) -> Tuple[bool, List[Dict]]:
        """获取商品列表"""
        params = {
            'page': page,
            'per_page': per_page,
            **kwargs
        }
        success, data = self._make_request('GET', 'products', params=params)
        return success, data if isinstance(data, list) else []
    
    def get_all_products(self) -> List[Dict]:
        """获取所有商品（分页获取）"""
        all_products = []
        page = 1
        per_page = 100
        
        while True:
            success, products = self.list_products(page=page, per_page=per_page)
            if not success or not products:
                break
            
            all_products.extend(products)
            
            # 如果返回的商品数量少于per_page，说明已经是最后一页
            if len(products) < per_page:
                break
            
            page += 1
        
        print(f"📦 获取到 {len(all_products)} 个商品")
        return all_products
    
    def create_product(self, product_data: Dict) -> Tuple[bool, Dict]:
        """创建商品"""
        return self._make_request('POST', 'products', data=product_data)
    
    def update_product(self, product_id: str, product_data: Dict) -> Tuple[bool, Dict]:
        """更新商品信息"""
        return self._make_request('PUT', f'products/{product_id}', data=product_data)
    
    def delete_product(self, product_id: str, force: bool = True) -> Tuple[bool, Dict]:
        """删除商品"""
        params = {'force': force} if force else {}
        return self._make_request('DELETE', f'products/{product_id}', params=params)
    
    def create_order(self, order_data: Dict) -> Tuple[bool, Dict]:
        """创建订单"""
        return self._make_request('POST', 'orders', data=order_data)

    def delete_order(self, order_id: int) -> Tuple[bool, Dict]:
        """删除指定订单"""
        return self._make_request('DELETE', f'orders/{order_id}', params={"force": True})

    def get_product_categories(self) -> Tuple[bool, List[Dict]]:
        """获取商品分类列表"""
        return self._make_request('GET', 'products/categories')
    
    def create_category(self, category_data: Dict) -> Tuple[bool, Dict]:
        """创建商品分类"""
        return self._make_request('POST', 'products/categories', data=category_data)
    
    def update_category(self, category_id: str, category_data: Dict) -> Tuple[bool, Dict]:
        """更新商品分类"""
        return self._make_request('PUT', f'products/categories/{category_id}', data=category_data)
    
    def batch_update_products(self, updates: List[Dict]) -> Tuple[bool, Dict]:
        """批量更新商品"""
        batch_data = {
            "update": updates
        }
        return self._make_request('POST', 'products/batch', data=batch_data)


class LowSellingProductFilter:
    """低销量产品筛选器"""
    
    def __init__(self, wc_client: WooCommerceClient):
        """
        初始化筛选器
        
        Args:
            wc_client: WooCommerce客户端实例
        """
        self.wc_client = wc_client
        self.outlet_category_id = None
    
    def analyze_products(self, days_in_stock_threshold: int = 90, 
                        sales_30_days_threshold: int = 10) -> Dict:
        """
        分析商品，筛选出低销量产品
        
        Args:
            days_in_stock_threshold: 在库天数阈值（默认90天）
            sales_30_days_threshold: 30天销量阈值（默认10件）
            
        Returns:
            包含分析结果的字典
        """
        print(f"🔍 开始分析产品...")
        print(f"   筛选条件: 在库天数 > {days_in_stock_threshold}天 且 30天销量 < {sales_30_days_threshold}件")
        
        # 获取所有商品
        all_products = self.wc_client.get_all_products()
        
        low_selling_products = []
        normal_products = []
        current_date = datetime.now()
        
        for product in all_products:
            try:
                # 获取商品发布日期
                date_created_str = product.get('date_created', '')
                if not date_created_str:
                    continue
                
                # 解析发布日期
                date_created = datetime.fromisoformat(date_created_str.replace('Z', '+00:00'))
                days_in_stock = (current_date - date_created.replace(tzinfo=None)).days
                
                # 获取30天销量数据（从meta_data中）
                sales_30_days = 0
                meta_data = product.get('meta_data', [])
                for meta in meta_data:
                    if meta.get('key') in ['sales_last_30_days', '_sales_last_30_days', 'sales_30_days']:
                        try:
                            sales_30_days = int(meta.get('value', 0))
                            break
                        except (ValueError, TypeError):
                            continue
                
                # 如果没有在meta_data中找到，尝试从其他字段获取
                if sales_30_days == 0:
                    # 可以根据总销量估算30天销量
                    total_sales = product.get('total_sales', 0)
                    if total_sales > 0:
                        # 简单估算：假设销量均匀分布
                        sales_30_days = max(1, int(total_sales * 30 / max(days_in_stock, 30)))
                
                product_info = {
                    'id': product.get('id'),
                    'name': product.get('name', ''),
                    'sku': product.get('sku', ''),
                    'price': product.get('price', '0'),
                    'stock_quantity': product.get('stock_quantity', 0),
                    'stock_status': product.get('stock_status', ''),
                    'date_created': date_created_str,
                    'days_in_stock': days_in_stock,
                    'sales_30_days': sales_30_days,
                    'total_sales': product.get('total_sales', 0),
                    'categories': [cat.get('name', '') for cat in product.get('categories', [])],
                    'status': product.get('status', '')
                }
                
                # 判断是否为低销量商品
                if (days_in_stock > days_in_stock_threshold and 
                    sales_30_days < sales_30_days_threshold):
                    low_selling_products.append(product_info)
                else:
                    normal_products.append(product_info)
                    
            except Exception as e:
                print(f"⚠️ 处理商品 {product.get('name', 'Unknown')} 时出错: {e}")
                continue
        
        analysis_result = {
            'total_products': len(all_products),
            'low_selling_products': low_selling_products,
            'normal_products': normal_products,
            'low_selling_count': len(low_selling_products),
            'normal_count': len(normal_products),
            'filter_criteria': {
                'days_in_stock_threshold': days_in_stock_threshold,
                'sales_30_days_threshold': sales_30_days_threshold
            },
            'analysis_date': current_date.isoformat()
        }
        
        print(f"📊 分析完成:")
        print(f"   总商品数: {analysis_result['total_products']}")
        print(f"   低销量商品: {analysis_result['low_selling_count']}")
        print(f"   正常商品: {analysis_result['normal_count']}")
        
        return analysis_result
    
    def ensure_outlet_category(self) -> bool:
        """确保"奥特莱斯/清仓"分类存在"""
        print("🏷️ 检查奥特莱斯/清仓分类...")
        
        # 获取现有分类
        success, categories = self.wc_client.get_product_categories()
        if not success:
            print(f"❌ 获取分类失败: {categories}")
            return False
        
        # 查找是否已存在奥特莱斯分类
        outlet_names = ["奥特莱斯", "清仓", "奥特莱斯/清仓", "Outlet", "Clearance"]
        
        for category in categories:
            if category.get('name', '') in outlet_names:
                self.outlet_category_id = category.get('id')
                print(f"✅ 找到现有分类: {category.get('name')} (ID: {self.outlet_category_id})")
                return True
        
        # 如果不存在，创建新分类
        category_data = {
            "name": "奥特莱斯/清仓",
            "description": "低销量商品清仓促销分类",
            "slug": "outlet-clearance"
        }
        
        success, new_category = self.wc_client.create_category(category_data)
        if success:
            self.outlet_category_id = new_category.get('id')
            print(f"✅ 创建新分类: 奥特莱斯/清仓 (ID: {self.outlet_category_id})")
            return True
        else:
            print(f"❌ 创建分类失败: {new_category}")
            return False
    
    def move_products_to_outlet(self, low_selling_products: List[Dict]) -> Dict:
        """
        将低销量商品移动到奥特莱斯分类
        
        Args:
            low_selling_products: 低销量商品列表
            
        Returns:
            移动操作的结果
        """
        if not self.outlet_category_id:
            if not self.ensure_outlet_category():
                return {"success": False, "error": "无法创建或找到奥特莱斯分类"}
        
        print(f"📦 开始移动 {len(low_selling_products)} 个商品到奥特莱斯分类...")
        
        # 准备批量更新数据
        updates = []
        for product in low_selling_products:
            product_id = product.get('id')
            if not product_id:
                continue
            
            # 获取现有分类，添加奥特莱斯分类
            existing_categories = product.get('categories', [])
            category_ids = [cat.get('id') for cat in existing_categories if cat.get('id')]
            
            # 添加奥特莱斯分类ID（如果还没有）
            if self.outlet_category_id not in category_ids:
                category_ids.append(self.outlet_category_id)
            
            update_data = {
                "id": product_id,
                "categories": [{"id": cat_id} for cat_id in category_ids]
            }
            updates.append(update_data)
        
        # 批量更新（WooCommerce API限制，分批处理）
        batch_size = 20
        successful_moves = []
        failed_moves = []
        
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]
            success, result = self.wc_client.batch_update_products(batch)
            
            if success:
                # 检查批量操作结果
                updated_products = result.get('update', [])
                for updated_product in updated_products:
                    if updated_product.get('id'):
                        successful_moves.append(updated_product.get('id'))
                    else:
                        failed_moves.append(updated_product)
            else:
                print(f"❌ 批量更新失败: {result}")
                failed_moves.extend(batch)
            
            # 避免API限制
            time.sleep(1)
        
        move_result = {
            "success": len(failed_moves) == 0,
            "total_products": len(low_selling_products),
            "successful_moves": len(successful_moves),
            "failed_moves": len(failed_moves),
            "outlet_category_id": self.outlet_category_id,
            "moved_product_ids": successful_moves,
            "failed_product_data": failed_moves
        }
        
        print(f"📊 移动结果:")
        print(f"   成功移动: {move_result['successful_moves']} 个商品")
        print(f"   移动失败: {move_result['failed_moves']} 个商品")
        
        return move_result
    
    def generate_report(self, analysis_result: Dict, move_result: Dict = None) -> str:
        """
        生成分析报告
        
        Args:
            analysis_result: 商品分析结果
            move_result: 移动操作结果（可选）
            
        Returns:
            报告内容字符串
        """
        report_lines = []
        report_lines.append("# 低销量商品筛选报告")
        report_lines.append("")
        report_lines.append(f"**分析时间**: {analysis_result.get('analysis_date', '')}")
        report_lines.append("")
        
        # 筛选条件
        criteria = analysis_result.get('filter_criteria', {})
        report_lines.append("## 筛选条件")
        report_lines.append(f"- 在库天数阈值: > {criteria.get('days_in_stock_threshold', 90)} 天")
        report_lines.append(f"- 30天销量阈值: < {criteria.get('sales_30_days_threshold', 10)} 件")
        report_lines.append("")
        
        # 总体统计
        report_lines.append("## 分析结果")
        report_lines.append(f"- 总商品数: {analysis_result.get('total_products', 0)}")
        report_lines.append(f"- 低销量商品: {analysis_result.get('low_selling_count', 0)}")
        report_lines.append(f"- 正常销量商品: {analysis_result.get('normal_count', 0)}")
        report_lines.append("")
        
        # 低销量商品详情
        low_selling_products = analysis_result.get('low_selling_products', [])
        if low_selling_products:
            report_lines.append("## 低销量商品详情")
            report_lines.append("")
            report_lines.append("| 商品名称 | SKU | 价格 | 库存 | 在库天数 | 30天销量 | 总销量 |")
            report_lines.append("|----------|-----|------|------|----------|----------|--------|")
            
            for product in low_selling_products[:20]:  # 只显示前20个
                name = product.get('name', '')[:30]  # 限制长度
                sku = product.get('sku', '')
                price = product.get('price', '0')
                stock = product.get('stock_quantity', 0)
                days = product.get('days_in_stock', 0)
                sales_30 = product.get('sales_30_days', 0)
                total_sales = product.get('total_sales', 0)
                
                report_lines.append(f"| {name} | {sku} | ¥{price} | {stock} | {days} | {sales_30} | {total_sales} |")
            
            if len(low_selling_products) > 20:
                report_lines.append(f"| ... | ... | ... | ... | ... | ... | ... |")
                report_lines.append(f"*（显示前20个，共{len(low_selling_products)}个低销量商品）*")
            
            report_lines.append("")
        
        # 移动操作结果
        if move_result:
            report_lines.append("## 分类移动结果")
            report_lines.append(f"- 成功移动到奥特莱斯分类: {move_result.get('successful_moves', 0)} 个商品")
            report_lines.append(f"- 移动失败: {move_result.get('failed_moves', 0)} 个商品")
            report_lines.append(f"- 奥特莱斯分类ID: {move_result.get('outlet_category_id', 'N/A')}")
            report_lines.append("")
        
        report_lines.append("---")
        report_lines.append("*报告由低销量商品筛选系统自动生成*")
        
        return "\n".join(report_lines)


class ImageManager:
    """WooCommerce图片管理器 - 用于创建和上传测试图片"""
    
    def __init__(self, wc_client: WooCommerceClient):
        """
        初始化图片管理器
        
        Args:
            wc_client: WooCommerce客户端实例
        """
        self.wc_client = wc_client
        self.created_images = []
    
    def create_test_images(self, count: int = 6) -> List[Dict]:
        """
        创建测试图片数据
        
        Args:
            count: 要创建的图片数量
            
        Returns:
            图片数据列表
        """
        from PIL import Image, ImageDraw, ImageFont
        import io
        import os
        import tempfile
        
        colors = [
            ('红色', '#FF6B6B', 'red'), ('蓝色', '#4ECDC4', 'blue'), ('绿色', '#45B7D1', 'green'),
            ('黄色', '#FFA07A', 'yellow'), ('紫色', '#D6336C', 'purple'), ('橙色', '#F9CA24', 'orange')
        ]
        
        test_images = []
        
        for i in range(min(count, len(colors))):
            color_name, color_hex, color_english = colors[i]
            
            # 创建一个简单的彩色图片
            img = Image.new('RGB', (400, 400), color_hex)
            draw = ImageDraw.Draw(img)
            
            # 添加文本标识
            try:
                # 尝试使用默认字体
                font = ImageFont.load_default()
            except:
                font = None
            
            text = f"{color_name}\nTest Image {i+1}"
            
            # 在图片上绘制文本
            if font:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                text_width, text_height = 100, 40
            
            x = (400 - text_width) // 2
            y = (400 - text_height) // 2
            
            draw.text((x, y), text, fill='white', font=font)
            
            # 保存到临时文件
            temp_file = tempfile.NamedTemporaryFile(suffix=f'_{color_english}.jpg', delete=False)
            img.save(temp_file.name, 'JPEG', quality=85)
            temp_file.close()
            
            test_images.append({
                'file_path': temp_file.name,
                'color': color_name,
                'color_hex': color_hex,
                'color_english': color_english,
                'filename': f'test_image_{color_english}.jpg',
                'alt_text': f'{color_name}测试图片'
            })
            
        print(f"🎨 创建了 {len(test_images)} 个测试图片")
        self.created_images = test_images
        return test_images
    
    def clear_media_library(self) -> Dict:
        """
        清除媒体库中的所有图片
        
        Returns:
            清除操作结果
        """
        print("🗑️ 开始清除媒体库图片...")
        
        try:
            import requests
            
            # 获取媒体库中的所有媒体文件
            media_url = f"{self.wc_client.site_url}/wp-json/wp/v2/media"
            
            # 分页获取所有媒体文件
            all_media = []
            page = 1
            per_page = 100
            
            while True:
                params = {
                    'page': page,
                    'per_page': per_page,
                    'media_type': 'image'  # 只获取图片
                }
                
                # 使用Cookie认证方式（和上传图片时相同）
                session = self._get_authenticated_session()
                if not session:
                    print(f"   ❌ 无法获取认证会话")
                    return {
                        'success': False,
                        'error': '无法获取认证会话',
                        'deleted_count': 0
                    }
                
                response = session.get(
                    media_url,
                    params=params,
                    timeout=30
                )
                
                if response.status_code == 200:
                    media_list = response.json()
                    if not media_list:
                        break
                    
                    all_media.extend(media_list)
                    
                    if len(media_list) < per_page:
                        break
                    
                    page += 1
                else:
                    print(f"   ❌ 获取媒体列表失败: HTTP {response.status_code}")
                    return {
                        'success': False,
                        'error': f'获取媒体列表失败: HTTP {response.status_code}',
                        'deleted_count': 0
                    }
            
            print(f"   📊 找到 {len(all_media)} 个图片文件")
            
            # 删除所有找到的图片
            deleted_count = 0
            failed_count = 0
            
            for media in all_media:
                media_id = media.get('id')
                media_title = media.get('title', {}).get('rendered', f'ID:{media_id}')
                
                if media_id:
                    delete_url = f"{media_url}/{media_id}"
                    delete_params = {'force': True}  # 强制删除，不放入回收站
                    
                    try:
                        delete_response = session.delete(
                            delete_url,
                            params=delete_params,
                            timeout=10
                        )
                        
                        if delete_response.status_code == 200:
                            deleted_count += 1
                            print(f"   ✅ 删除: {media_title}")
                        else:
                            failed_count += 1
                            print(f"   ❌ 删除失败: {media_title} - HTTP {delete_response.status_code}")
                    
                    except Exception as e:
                        failed_count += 1
                        print(f"   ❌ 删除出错: {media_title} - {e}")
                    
                    # 避免API限制
                    time.sleep(0.2)
            
            result = {
                'success': failed_count == 0,
                'total_found': len(all_media),
                'deleted_count': deleted_count,
                'failed_count': failed_count
            }
            
            print(f"📊 清除完成: 成功删除 {deleted_count}/{len(all_media)} 个图片")
            if failed_count > 0:
                print(f"   ⚠️ {failed_count} 个图片删除失败")
            
            return result
            
        except Exception as e:
            print(f"❌ 清除媒体库时出错: {e}")
            return {
                'success': False,
                'error': str(e),
                'deleted_count': 0
            }
    
    def _get_authenticated_session(self):
        """
        获取已认证的会话（使用Cookie认证）
        
        Returns:
            认证成功的会话对象，失败返回None
        """
        import requests
        
        try:
            # 创建一个会话来保持Cookie
            session = requests.Session()
            
            # 首先尝试获取WordPress登录页面的nonce
            login_url = f"{self.wc_client.site_url}/wp-login.php"
            
            # 获取登录页面
            login_page = session.get(login_url, timeout=10)
            
            if login_page.status_code == 200:
                # 提取nonce (如果有的话)
                import re
                nonce_match = re.search(r'name="_wpnonce".*?value="([^"]+)"', login_page.text)
                nonce = nonce_match.group(1) if nonce_match else ""
                
                # 准备登录数据
                login_data = {
                    'log': self.wc_client.wp_username,
                    'pwd': self.wc_client.wp_password,
                    'wp-submit': 'Log In',
                    'redirect_to': f"{self.wc_client.site_url}/wp-admin/",
                    'testcookie': '1'
                }
                
                if nonce:
                    login_data['_wpnonce'] = nonce
                
                # 执行登录
                login_response = session.post(login_url, data=login_data, timeout=10)
                
                # 检查是否登录成功 (通常会重定向到wp-admin)
                if login_response.status_code in [200, 302]:
                    print(f"   ✅ Cookie认证会话创建成功")
                    
                    # 获取REST API nonce
                    nonce_url = f"{self.wc_client.site_url}/wp-admin/admin-ajax.php?action=rest-nonce"
                    nonce_response = session.get(nonce_url, timeout=10)
                    
                    # 如果成功获取nonce，添加到session headers
                    if nonce_response.status_code == 200:
                        session.headers.update({'X-WP-Nonce': nonce_response.text.strip()})
                    
                    return session
                else:
                    print(f"   ❌ WordPress登录失败: {login_response.status_code}")
            else:
                print(f"   ❌ 无法访问WordPress登录页面: {login_page.status_code}")
                
        except Exception as e:
            print(f"   ❌ 创建认证会话时出错: {e}")
        
        return None
    
    def upload_test_images(self, test_images: List[Dict], clear_before_upload: bool = True) -> List[Dict]:
        """
        上传测试图片到WooCommerce媒体库
        
        Args:
            test_images: 测试图片数据列表
            clear_before_upload: 是否在上传前清除媒体库 (默认: True)
            
        Returns:
            上传结果列表，包含媒体ID
        """
        # 在上传前先清除媒体库
        if clear_before_upload:
            clear_result = self.clear_media_library()
            if not clear_result['success']:
                print(f"⚠️ 清除媒体库失败，但继续上传: {clear_result.get('error', '')}")
        
        uploaded_images = []
        
        for img_data in test_images:
            file_path = img_data['file_path']
            filename = img_data['filename']
            alt_text = img_data['alt_text']
            
            print(f"📤 上传图片: {filename}")
            
            try:
                # 读取图片文件
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                # 上传到WordPress媒体库
                upload_result = self._upload_to_media_library(
                    file_content, filename, alt_text
                )
                
                if upload_result.get('success'):
                    media_id = upload_result['media_id']
                    uploaded_images.append({
                        'media_id': media_id,
                        'color': img_data['color'],
                        'color_hex': img_data['color_hex'],
                        'filename': filename,
                        'alt_text': alt_text,
                        'url': upload_result.get('url', ''),
                        'file_path': file_path
                    })
                    print(f"   ✅ 上传成功 (Media ID: {media_id})")
                else:
                    print(f"   ❌ 上传失败: {upload_result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"   ❌ 上传图片 {filename} 时出错: {e}")
            
            time.sleep(0.5)  # 避免API限制
        
        print(f"📊 图片上传完成: {len(uploaded_images)}/{len(test_images)} 成功")
        return uploaded_images
    
    def _upload_to_media_library(self, file_content: bytes, filename: str, alt_text: str) -> Dict:
        """
        上传文件到WordPress媒体库（使用Cookie认证）
        
        Args:
            file_content: 文件内容
            filename: 文件名
            alt_text: 替代文本
            
        Returns:
            上传结果
        """
        # WordPress媒体上传端点
        media_url = f"{self.wc_client.site_url}/wp-json/wp/v2/media"
        
        # 确保filename只包含ASCII字符，避免编码问题
        safe_filename = filename.encode('ascii', 'ignore').decode('ascii') if filename else 'image.jpg'
        
        headers = {
            'Content-Disposition': f'attachment; filename="{safe_filename}"',
            'Content-Type': 'image/jpeg'
        }
        
        try:
            # 直接使用Cookie认证会话
            session = self._get_authenticated_session()
            if not session:
                return {
                    'success': False,
                    'error': '无法获取认证会话'
                }
            
            print(f"   🔐 使用Cookie认证上传...")
            response = session.post(
                media_url,
                headers=headers,
                data=file_content,
                timeout=30
            )
            
            print(f"   📊 响应状态: {response.status_code}")
            
            if response.status_code == 201:
                media_data = response.json()
                media_id = media_data.get('id')
                
                return {
                    'success': True,
                    'media_id': media_id,
                    'url': media_data.get('source_url', ''),
                    'title': media_data.get('title', {}).get('rendered', ''),
                    'response': media_data
                }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response.text}',
                    'response': response.text
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Request failed: {str(e)}'
            }
    

    
    def cleanup_test_images(self):
        """清理测试图片文件"""
        import os
        
        print("🧹 清理测试图片文件...")
        
        for img_data in self.created_images:
            file_path = img_data.get('file_path', '')
            if file_path and os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                    print(f"   ✅ 删除文件: {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"   ❌ 删除文件失败: {file_path} - {e}")
        
        print(f"📊 清理完成")


# WooCommerce客户端扩展方法
def add_woocommerce_extensions(wc_client):
    """为WooCommerceClient添加扩展方法"""
    
    def get_product_attributes(self):
        """获取商品属性列表"""
        return self._make_request('GET', 'products/attributes')
    
    def create_product_attribute(self, attribute_data):
        """创建商品属性"""
        return self._make_request('POST', 'products/attributes', data=attribute_data)
    
    def create_attribute_term(self, attribute_id, term_data):
        """创建属性项"""
        return self._make_request('POST', f'products/attributes/{attribute_id}/terms', data=term_data)
    
    def create_variation(self, product_id, variation_data):
        """为商品创建变体"""
        return self._make_request('POST', f'products/{product_id}/variations', data=variation_data)
    
    def list_variations(self, product_id, **params):
        """获取商品变体列表"""
        return self._make_request('GET', f'products/{product_id}/variations', params=params)
    
    def update_variation(self, product_id, variation_id, variation_data):
        """更新商品变体"""
        return self._make_request('PUT', f'products/{product_id}/variations/{variation_id}', data=variation_data)
    
    def update_order(self, order_id, order_data):
        """更新订单"""
        return self._make_request('PUT', f'orders/{order_id}', data=order_data)
    
    # 动态添加方法到类
    import types
    wc_client.get_product_attributes = types.MethodType(get_product_attributes, wc_client)
    wc_client.create_product_attribute = types.MethodType(create_product_attribute, wc_client)
    wc_client.create_attribute_term = types.MethodType(create_attribute_term, wc_client)
    wc_client.create_variation = types.MethodType(create_variation, wc_client)
    wc_client.list_variations = types.MethodType(list_variations, wc_client)
    wc_client.update_variation = types.MethodType(update_variation, wc_client)
    wc_client.update_order = types.MethodType(update_order, wc_client)
    
    return wc_client
