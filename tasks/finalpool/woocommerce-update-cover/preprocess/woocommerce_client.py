import requests
from requests.auth import HTTPBasicAuth
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os

class WooCommerceClient:
    """WooCommerce API client - For low selling product filter task"""
    
    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str, version: str = "v3", 
                 wp_username: str = None, wp_password: str = None):
        """
        Initialize WooCommerce client
        
        Args:
            site_url: WooCommerce website URL (e.g. https://your-site.com)
            consumer_key: WooCommerce API consumer key
            consumer_secret: WooCommerce API consumer secret
            version: API version (default: v3)
            wp_username: WordPress admin username (for media upload)
            wp_password: WordPress admin password (for media upload)
        """
        self.site_url = site_url.rstrip('/')
        self.api_base = f"{self.site_url}/wp-json/wc/{version}"
        self.auth = HTTPBasicAuth(consumer_key, consumer_secret)
        self.session = requests.Session()
        self.session.auth = self.auth

        # Set up connection pool and timeout configuration
        self.session.verify = False  # Disable SSL verification (for local development)
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=1,
            pool_maxsize=1,
            max_retries=3
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        # WordPress user authentication (for media upload)
        self.wp_auth = None
        self.wp_username = wp_username
        self.wp_password = wp_password
        if wp_username and wp_password:
            self.wp_auth = HTTPBasicAuth(wp_username, wp_password)

        # API call limit (to avoid exceeding rate limit)
        self.request_delay = 1.0  # Increase to 1 second interval
        self.last_request_time = 0
        self.max_retries = 3  # Maximum retry times
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Tuple[bool, Dict]:
        """
        Send API request (with retry mechanism)

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            data: Request data
            params: URL parameters

        Returns:
            (Success flag, response data)
        """
        # Control request frequency
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_delay:
            time.sleep(self.request_delay - time_since_last)

        url = f"{self.api_base}/{endpoint.lstrip('/')}"

        # Retry mechanism
        for attempt in range(self.max_retries + 1):
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Connection": "close",  # Ensure connection is closed, to avoid connection pool problem
                    "User-Agent": "WooCommerce-Python-Client/1.0"
                }

                # Set timeout
                timeout = (10, 30)  # (Connection timeout, read timeout)

                if method.upper() == 'GET':
                    response = self.session.get(url, params=params, headers=headers, timeout=timeout)
                elif method.upper() == 'POST':
                    response = self.session.post(url, json=data, params=params, headers=headers, timeout=timeout)
                elif method.upper() == 'PUT':
                    response = self.session.put(url, json=data, params=params, headers=headers, timeout=timeout)
                elif method.upper() == 'DELETE':
                    response = self.session.delete(url, params=params, headers=headers, timeout=timeout)
                else:
                    return False, {"error": f"Unsupported HTTP method: {method}"}

                self.last_request_time = time.time()

                # Check response status
                if response.status_code >= 200 and response.status_code < 300:
                    try:
                        return True, response.json()
                    except ValueError:  # JSON parsing failed
                        return True, {"message": "Success", "status_code": response.status_code}
                else:
                    # HTTP error status code
                    error_data = {"error": f"HTTP {response.status_code}", "status_code": response.status_code}
                    try:
                        error_detail = response.json()
                        error_data.update(error_detail)
                    except ValueError:
                        error_data["raw_response"] = response.text[:500]
                    return False, error_data

            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    ConnectionResetError) as e:
                if attempt < self.max_retries:
                    wait_time = (attempt + 1) * 2  # Incremental wait time
                    print(f"   🔄 Connection failed, {wait_time} seconds later retry ({attempt + 1} times): {str(e)[:100]}")
                    time.sleep(wait_time)
                    continue
                else:
                    error_msg = f"API request failed (tried {self.max_retries} times): {str(e)}"
                    return False, {"error": error_msg}

            except requests.exceptions.RequestException as e:
                error_msg = f"API request failed: {str(e)}"
                if hasattr(e, 'response') and e.response is not None:
                    error_msg += f" - HTTP {e.response.status_code}"
                    try:
                        error_detail = e.response.json()
                        error_msg += f" - {error_detail}"
                    except ValueError:
                        error_msg += f" - {e.response.text[:200]}"
                return False, {"error": error_msg}

            except Exception as e:
                error_msg = f"Unknown error: {str(e)}"
                return False, {"error": error_msg}

        return False, {"error": "Request failed, reached maximum retry times"}
    
    def get_product(self, product_id: str) -> Tuple[bool, Dict]:
        """Get product information"""
        return self._make_request('GET', f'products/{product_id}')
    
    def list_products(self, page: int = 1, per_page: int = 100, **kwargs) -> Tuple[bool, List[Dict]]:
        """Get product list"""
        params = {
            'page': page,
            'per_page': per_page,
            **kwargs
        }
        success, data = self._make_request('GET', 'products', params=params)
        return success, data if isinstance(data, list) else []
    
    def get_all_products(self) -> List[Dict]:
        """Get all products (paginated)"""
        all_products = []
        page = 1
        per_page = 100
        
        while True:
            success, products = self.list_products(page=page, per_page=per_page)
            if not success or not products:
                break
            
            all_products.extend(products)
            
            # If the number of products returned is less than per_page, it means it's the last page
            if len(products) < per_page:
                break
            
            page += 1
        
        print(f"📦 Get {len(all_products)} products")
        return all_products
    
    def create_product(self, product_data: Dict) -> Tuple[bool, Dict]:
        """Create product"""
        return self._make_request('POST', 'products', data=product_data)
    
    def update_product(self, product_id: str, product_data: Dict) -> Tuple[bool, Dict]:
        """Update product information"""
        return self._make_request('PUT', f'products/{product_id}', data=product_data)
    
    def delete_product(self, product_id: str, force: bool = True) -> Tuple[bool, Dict]:
        """Delete product"""
        params = {'force': force} if force else {}
        return self._make_request('DELETE', f'products/{product_id}', params=params)
    
    def create_order(self, order_data: Dict) -> Tuple[bool, Dict]:
        """Create order"""
        return self._make_request('POST', 'orders', data=order_data)

    def delete_order(self, order_id: int) -> Tuple[bool, Dict]:
        """Delete specified order"""
        return self._make_request('DELETE', f'orders/{order_id}', params={"force": True})

    def get_product_categories(self) -> Tuple[bool, List[Dict]]:
        """Get product category list"""
        return self._make_request('GET', 'products/categories')
    
    def create_category(self, category_data: Dict) -> Tuple[bool, Dict]:
        """Create product category"""
        return self._make_request('POST', 'products/categories', data=category_data)
    
    def update_category(self, category_id: str, category_data: Dict) -> Tuple[bool, Dict]:
        """Update product category"""
        return self._make_request('PUT', f'products/categories/{category_id}', data=category_data)
    
    def batch_update_products(self, updates: List[Dict]) -> Tuple[bool, Dict]:
        """Batch update products"""
        batch_data = {
            "update": updates
        }
        return self._make_request('POST', 'products/batch', data=batch_data)


class LowSellingProductFilter:
    """Low selling product filter"""
    
    def __init__(self, wc_client: WooCommerceClient):
        """
        Initialize filter
        
        Args:
            wc_client: WooCommerce client instance
        """
        self.wc_client = wc_client
        self.outlet_category_id = None
    
    def analyze_products(self, days_in_stock_threshold: int = 90, 
                        sales_30_days_threshold: int = 10) -> Dict:
        """
        Analyze products, filter out low selling products
        
        Args:
            days_in_stock_threshold: In stock days threshold (default: 90 days)
            sales_30_days_threshold: 30 days sales threshold (default: 10 items)
            
        Returns:
            Dictionary containing analysis results
        """
        print(f"🔍 Start analyzing products...")
        print(f"   Filter criteria: In stock days > {days_in_stock_threshold} days AND 30 days sales < {sales_30_days_threshold} items")
        
        # Get all products
        all_products = self.wc_client.get_all_products()
        
        low_selling_products = []
        normal_products = []
        current_date = datetime.now()
        
        for product in all_products:
            try:
                # Get product creation date
                date_created_str = product.get('date_created', '')
                if not date_created_str:
                    continue
                
                # Parse creation date
                date_created = datetime.fromisoformat(date_created_str.replace('Z', '+00:00'))
                days_in_stock = (current_date - date_created.replace(tzinfo=None)).days
                
                # Get 30 days sales data (from meta_data)
                sales_30_days = 0
                meta_data = product.get('meta_data', [])
                for meta in meta_data:
                    if meta.get('key') in ['sales_last_30_days', '_sales_last_30_days', 'sales_30_days']:
                        try:
                            sales_30_days = int(meta.get('value', 0))
                            break
                        except (ValueError, TypeError):
                            continue
                
                # If not found in meta_data, try to estimate from total sales
                if sales_30_days == 0:
                    # We can estimate 30 days sales from total sales
                    total_sales = product.get('total_sales', 0)
                    if total_sales > 0:
                        # Simple estimation: assume sales are evenly distributed
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
                
                # Determine if it's a low selling product
                if (days_in_stock > days_in_stock_threshold and 
                    sales_30_days < sales_30_days_threshold):
                    low_selling_products.append(product_info)
                else:
                    normal_products.append(product_info)
                    
            except Exception as e:
                print(f"⚠️ Error processing product {product.get('name', 'Unknown')}: {e}")
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
        
        print(f"📊 Analysis complete:")
        print(f"   Total products: {analysis_result['total_products']}")
        print(f"   Low selling products: {analysis_result['low_selling_count']}")
        print(f"   Normal products: {analysis_result['normal_count']}")
        
        return analysis_result
    
    def ensure_outlet_category(self) -> bool:
        """Ensure "Outlet/Clearance" category exists"""
        print("🏷️ Check Outlet/Clearance category...")
        
        # Get existing categories
        success, categories = self.wc_client.get_product_categories()
        if not success:
            print(f"❌ Failed to get categories: {categories}")
            return False
        
        # Check if Outlet/Clearance category exists
        outlet_names = ["Outlet", "Clearance", "Outlet/Clearance"]
        
        for category in categories:
            if category.get('name', '') in outlet_names:
                self.outlet_category_id = category.get('id')
                print(f"✅ Found existing category: {category.get('name')} (ID: {self.outlet_category_id})")
                return True
        
        # If not exists, create new category
        category_data = {
            "name": "Outlet/Clearance",
            "description": "Low selling products clearance promotion category",
            "slug": "outlet-clearance"
        }
        
        success, new_category = self.wc_client.create_category(category_data)
        if success:
            self.outlet_category_id = new_category.get('id')
            print(f"✅ Created new category: Outlet/Clearance (ID: {self.outlet_category_id})")
            return True
        else:
            print(f"❌ Failed to create category: {new_category}")
            return False
    
    def move_products_to_outlet(self, low_selling_products: List[Dict]) -> Dict:
        """
        Move low selling products to Outlet/Clearance category
        
        Args:
            low_selling_products: Low selling products list
            
        Returns:
            Move operation result
        """
        if not self.outlet_category_id:
            if not self.ensure_outlet_category():
                return {"success": False, "error": "Failed to create or find Outlet/Clearance category"}
        
        print(f"📦 Start moving {len(low_selling_products)} products to Outlet/Clearance category...")
        
        # Prepare batch update data
        updates = []
        for product in low_selling_products:
            product_id = product.get('id')
            if not product_id:
                continue
            
            # Get existing categories, add Outlet/Clearance category
            existing_categories = product.get('categories', [])
            category_ids = [cat.get('id') for cat in existing_categories if cat.get('id')]
            
            # Add Outlet/Clearance category ID (if not exists)
            if self.outlet_category_id not in category_ids:
                category_ids.append(self.outlet_category_id)
            
            update_data = {
                "id": product_id,
                "categories": [{"id": cat_id} for cat_id in category_ids]
            }
            updates.append(update_data)
        
        # Batch update (WooCommerce API limit, process in batches)
        batch_size = 20
        successful_moves = []
        failed_moves = []
        
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]
            success, result = self.wc_client.batch_update_products(batch)
            
            if success:
                # Check batch operation result
                updated_products = result.get('update', [])
                for updated_product in updated_products:
                    if updated_product.get('id'):
                        successful_moves.append(updated_product.get('id'))
                    else:
                        failed_moves.append(updated_product)
            else:
                print(f"❌ Failed to batch update: {result}")
                failed_moves.extend(batch)
            
            # Avoid API limit
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
        
        print(f"📊 Move result:")
        print(f"   Successfully moved: {move_result['successful_moves']} products")
        print(f"   Failed to move: {move_result['failed_moves']} products")
        
        return move_result
    
    def generate_report(self, analysis_result: Dict, move_result: Dict = None) -> str:
        """
        Generate analysis report
        
        Args:
            analysis_result: Product analysis result
            move_result: Move operation result (optional)
            
        Returns:
            Report content string
        """
        report_lines = []
        report_lines.append("# Low selling product filter report")
        report_lines.append("")
        report_lines.append(f"**Analysis time**: {analysis_result.get('analysis_date', '')}")
        report_lines.append("")
        
        # Filter criteria
        criteria = analysis_result.get('filter_criteria', {})
        report_lines.append("## Filter criteria")
        report_lines.append(f"- In stock days threshold: > {criteria.get('days_in_stock_threshold', 90)} days")
        report_lines.append(f"- 30 days sales threshold: < {criteria.get('sales_30_days_threshold', 10)} items")
        report_lines.append("")
        
        # Overall statistics
        report_lines.append("## Analysis results")
        report_lines.append(f"- Total products: {analysis_result.get('total_products', 0)}")
        report_lines.append(f"- Low selling products: {analysis_result.get('low_selling_count', 0)}")
        report_lines.append(f"- Normal selling products: {analysis_result.get('normal_count', 0)}")
        report_lines.append("")
        
        # Low selling products details
        low_selling_products = analysis_result.get('low_selling_products', [])
        if low_selling_products:
            report_lines.append("## Low selling products details")
            report_lines.append("")
            report_lines.append("| Product name | SKU | Price | Stock | In stock days | 30 days sales | Total sales |")
            report_lines.append("|----------|-----|------|------|----------|----------|--------|")
            
            for product in low_selling_products[:20]:  # Only show first 20
                name = product.get('name', '')[:30]  # Limit length
                sku = product.get('sku', '')
                price = product.get('price', '0')
                stock = product.get('stock_quantity', 0)
                days = product.get('days_in_stock', 0)
                sales_30 = product.get('sales_30_days', 0)
                total_sales = product.get('total_sales', 0)
                
                report_lines.append(f"| {name} | {sku} | ¥{price} | {stock} | {days} | {sales_30} | {total_sales} |")
            
            if len(low_selling_products) > 20:
                report_lines.append(f"| ... | ... | ... | ... | ... | ... | ... |")
                report_lines.append(f"*(Showing first 20 out of {len(low_selling_products)} low-selling products)*")
            
            report_lines.append("")
        
        # Move operation results
        if move_result:
            report_lines.append("## Category move results")
            report_lines.append(f"- Successfully moved to Outlet category: {move_result.get('successful_moves', 0)} products")
            report_lines.append(f"- Failed to move: {move_result.get('failed_moves', 0)} products")
            report_lines.append(f"- Outlet category ID: {move_result.get('outlet_category_id', 'N/A')}")
            report_lines.append("")
        
        report_lines.append("---")
        report_lines.append("*Report generated by low-selling product filter system*")
        
        return "\n".join(report_lines)


class ImageManager:
    """WooCommerce image manager - for creating and uploading test images"""
    
    def __init__(self, wc_client: WooCommerceClient):
        """
        Initialize image manager
        
        Args:
            wc_client: WooCommerce client instance
        """
        self.wc_client = wc_client
        self.created_images = []
    
    def create_test_images(self, count: int = 6) -> List[Dict]:
        """
        Create test image data
        
        Args:
            count: Number of images to create
            
        Returns:
            Image data list
        """
        from PIL import Image, ImageDraw, ImageFont
        import io
        import os
        import tempfile
        
        colors = [
            ('Red', '#FF6B6B', 'red'), ('Blue', '#4ECDC4', 'blue'), ('Green', '#45B7D1', 'green'),
            ('Yellow', '#FFA07A', 'yellow'), ('Purple', '#D6336C', 'purple'), ('Orange', '#F9CA24', 'orange')
        ]
        
        test_images = []
        
        for i in range(min(count, len(colors))):
            color_name, color_hex, color_english = colors[i]
            
            # Create a simple colored image
            img = Image.new('RGB', (400, 400), color_hex)
            draw = ImageDraw.Draw(img)
            
            # Add text identifier
            try:
                # Try using default font
                font = ImageFont.load_default()
            except:
                font = None
            
            text = f"{color_name}\nTest Image {i+1}"
            
            # Draw text on the image
            if font:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                text_width, text_height = 100, 40
            
            x = (400 - text_width) // 2
            y = (400 - text_height) // 2
            
            draw.text((x, y), text, fill='white', font=font)
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix=f'_{color_english}.jpg', delete=False)
            img.save(temp_file.name, 'JPEG', quality=85)
            temp_file.close()
            
            test_images.append({
                'file_path': temp_file.name,
                'color': color_name,
                'color_hex': color_hex,
                'color_english': color_english,
                'filename': f'test_image_{color_english}.jpg',
                'alt_text': f'{color_name} Test Image'
            })
            
        print(f"🎨 Created {len(test_images)} test images")
        self.created_images = test_images
        return test_images
    
    def clear_media_library(self) -> Dict:
        """
        Clear all images in media library
        
        Returns:
            Clear operation result
        """
        print("🗑️ Start clearing media library images...")
        
        try:
            import requests
            
            # Get all media files in media library
            media_url = f"{self.wc_client.site_url}/wp-json/wp/v2/media"
            
            # Get all media files in media library
            all_media = []
            page = 1
            per_page = 100
            
            while True:
                params = {
                    'page': page,
                    'per_page': per_page,
                    'media_type': 'image'  # Only get images
                }
                
                # Use Cookie authentication (same as when uploading images)
                session = self._get_authenticated_session()
                if not session:
                    print(f"   ❌ Failed to get authenticated session")
                    return {
                        'success': False,
                        'error': 'Failed to get authenticated session',
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
                    print(f"   ❌ Failed to get media list: HTTP {response.status_code}")
                    return {
                        'success': False,
                        'error': f'Failed to get media list: HTTP {response.status_code}',
                        'deleted_count': 0
                    }
            
            print(f"   📊 Found {len(all_media)} image files")
            
            # Delete all found images
            deleted_count = 0
            failed_count = 0
            
            for media in all_media:
                media_id = media.get('id')
                media_title = media.get('title', {}).get('rendered', f'ID:{media_id}')
                
                if media_id:
                    delete_url = f"{media_url}/{media_id}"
                    delete_params = {'force': True}  # Force delete, not put in recycle bin
                    
                    try:
                        delete_response = session.delete(
                            delete_url,
                            params=delete_params,
                            timeout=10
                        )
                        
                        if delete_response.status_code == 200:
                            deleted_count += 1
                            print(f"   ✅ Delete: {media_title}")
                        else:
                            failed_count += 1
                            print(f"   ❌ Delete failed: {media_title} - HTTP {delete_response.status_code}")
                    
                    except Exception as e:
                        failed_count += 1
                        print(f"   ❌ Delete error: {media_title} - {e}")
                    
                    # Avoid API limit
                    time.sleep(0.2)
            
            result = {
                'success': failed_count == 0,
                'total_found': len(all_media),
                'deleted_count': deleted_count,
                'failed_count': failed_count
            }
            
            print(f"📊 Clear completed: successfully deleted {deleted_count}/{len(all_media)} images")
            if failed_count > 0:
                print(f"   ⚠️ {failed_count} images deleted failed")
            
            return result
            
        except Exception as e:
            print(f"❌ Clear media library error: {e}")
            return {
                'success': False,
                'error': str(e),
                'deleted_count': 0
            }
    
    def _get_authenticated_session(self):
        """
        Get authenticated session (using Cookie authentication)
        
        Returns:
            Authenticated session object, return None if failed
        """
        import requests
        
        try:
            # Create a session to keep Cookie
            session = requests.Session()
            
            # First try to get nonce of WordPress login page
            login_url = f"{self.wc_client.site_url}/wp-login.php"
            
            # Get login page
            login_page = session.get(login_url, timeout=10)
            
            if login_page.status_code == 200:
                # Extract nonce (if any)
                import re
                nonce_match = re.search(r'name="_wpnonce".*?value="([^"]+)"', login_page.text)
                nonce = nonce_match.group(1) if nonce_match else ""
                
                # Prepare login data
                login_data = {
                    'log': self.wc_client.wp_username,
                    'pwd': self.wc_client.wp_password,
                    'wp-submit': 'Log In',
                    'redirect_to': f"{self.wc_client.site_url}/wp-admin/",
                    'testcookie': '1'
                }
                
                if nonce:
                    login_data['_wpnonce'] = nonce
                
                # Execute login
                login_response = session.post(login_url, data=login_data, timeout=10)
                
                # Check if login is successful (usually redirects to wp-admin)
                if login_response.status_code in [200, 302]:
                    print(f"   ✅ Cookie authentication session created successfully")
                    
                    # Get REST API nonce
                    nonce_url = f"{self.wc_client.site_url}/wp-admin/admin-ajax.php?action=rest-nonce"
                    nonce_response = session.get(nonce_url, timeout=10)
                    
                    # If nonce is successfully obtained, add to session headers
                    if nonce_response.status_code == 200:
                        session.headers.update({'X-WP-Nonce': nonce_response.text.strip()})
                    
                    return session
                else:
                    print(f"   ❌ WordPress login failed: {login_response.status_code}")
            else:
                print(f"   ❌ Unable to access WordPress login page: {login_page.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error creating authenticated session: {e}")
        
        return None
    
    def upload_test_images(self, test_images: List[Dict], clear_before_upload: bool = True) -> List[Dict]:
        """
        Upload test images to WooCommerce media library
        
        Args:
            test_images: Test image data list
            clear_before_upload: Whether to clear media library before uploading (default: True)
            
        Returns:
            Upload result list, including media ID
        """
        # Clear media library before uploading
        if clear_before_upload:
            clear_result = self.clear_media_library()
            if not clear_result['success']:
                print(f"⚠️ Clear media library failed, but continue uploading: {clear_result.get('error', '')}")
        
        uploaded_images = []
        
        for img_data in test_images:
            file_path = img_data['file_path']
            filename = img_data['filename']
            alt_text = img_data['alt_text']
            
            print(f"📤 Upload image: {filename}")
            
            try:
                # Read image file
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                # Upload to WordPress media library
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
                    print(f"   ✅ Upload success (Media ID: {media_id})")
                else:
                    print(f"   ❌ Upload failed: {upload_result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"   ❌ Upload image {filename} error: {e}")
            
            time.sleep(0.5)  # Avoid API limit
        
        print(f"📊 Image upload completed: {len(uploaded_images)}/{len(test_images)} success")
        return uploaded_images
    
    def _upload_to_media_library(self, file_content: bytes, filename: str, alt_text: str) -> Dict:
        """
        Upload file to WordPress media library (using Cookie authentication)
        
        Args:
            file_content: File content
            filename: File name
            alt_text: Alternative text
            
        Returns:
            Upload result
        """
        # WordPress media upload endpoint
        media_url = f"{self.wc_client.site_url}/wp-json/wp/v2/media"
        
        # Ensure filename only contains ASCII characters, avoid encoding problems
        safe_filename = filename.encode('ascii', 'ignore').decode('ascii') if filename else 'image.jpg'
        
        headers = {
            'Content-Disposition': f'attachment; filename="{safe_filename}"',
            'Content-Type': 'image/jpeg'
        }
        
        try:
            # Directly use Cookie authentication session
            session = self._get_authenticated_session()
            if not session:
                return {
                    'success': False,
                    'error': 'Failed to get authenticated session'
                }
            
            print(f"   🔐 Using Cookie authentication upload...")
            response = session.post(
                media_url,
                headers=headers,
                data=file_content,
                timeout=30
            )
            
            print(f"   📊 Response status: {response.status_code}")
            
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
        """Clean test image files"""
        import os
        
        print("🧹 Clean test image files...")
        
        for img_data in self.created_images:
            file_path = img_data.get('file_path', '')
            if file_path and os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                    print(f"   ✅ Delete file: {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"   ❌ Delete file failed: {file_path} - {e}")
        
        print(f"📊 Clean completed")


# WooCommerce client extensions
def add_woocommerce_extensions(wc_client):
    """Add extensions to WooCommerceClient"""
    
    def get_product_attributes(self):
        """Get product attributes list"""
        return self._make_request('GET', 'products/attributes')
    
    def create_product_attribute(self, attribute_data):
        """Create product attribute"""
        return self._make_request('POST', 'products/attributes', data=attribute_data)
    
    def create_attribute_term(self, attribute_id, term_data):
        """Create attribute term"""
        return self._make_request('POST', f'products/attributes/{attribute_id}/terms', data=term_data)
    
    def create_variation(self, product_id, variation_data):
        """Create variation for product"""
        return self._make_request('POST', f'products/{product_id}/variations', data=variation_data)
    
    def list_variations(self, product_id, **params):
        """Get product variations list"""
        return self._make_request('GET', f'products/{product_id}/variations', params=params)
    
    def update_variation(self, product_id, variation_id, variation_data):
        """Update product variation"""
        return self._make_request('PUT', f'products/{product_id}/variations/{variation_id}', data=variation_data)
    
    def update_order(self, order_id, order_data):
        """Update order"""
        return self._make_request('PUT', f'orders/{order_id}', data=order_data)
    
    # Dynamically add methods to class
    import types
    wc_client.get_product_attributes = types.MethodType(get_product_attributes, wc_client)
    wc_client.create_product_attribute = types.MethodType(create_product_attribute, wc_client)
    wc_client.create_attribute_term = types.MethodType(create_attribute_term, wc_client)
    wc_client.create_variation = types.MethodType(create_variation, wc_client)
    wc_client.list_variations = types.MethodType(list_variations, wc_client)
    wc_client.update_variation = types.MethodType(update_variation, wc_client)
    wc_client.update_order = types.MethodType(update_order, wc_client)
    
    return wc_client
