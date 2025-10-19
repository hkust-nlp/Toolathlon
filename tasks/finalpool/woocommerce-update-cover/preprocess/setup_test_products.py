import requests
from requests.auth import HTTPBasicAuth
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os
from pathlib import Path

current_dir = os.path.dirname(os.path.abspath(__file__))
task_dir = os.path.dirname(current_dir)
sys.path.append(task_dir)

from preprocess.woocommerce_client import WooCommerceClient, ImageManager, add_woocommerce_extensions

class TestProductSetup:
    
    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str, 
                 wp_username: str = None, wp_password: str = None):

        self.wc_client = add_woocommerce_extensions(
            WooCommerceClient(site_url, consumer_key, consumer_secret, wp_username=wp_username, wp_password=wp_password)
        )
        self.image_manager = ImageManager(self.wc_client)
        self.created_products = []
        self.created_attributes = []
        self.created_orders = []
        import time
        timestamp = int(time.time())
        self.image_ids = {
            "Red": 16 + timestamp,
            "Blue": 34 + timestamp,
            "Green": 35 + timestamp,
            "Yellow": 36 + timestamp,
        }
        print(f"🎨Image IDs initialized (timestamp: {timestamp}): {self.image_ids}")
    
    def clear_all_products(self) -> Dict:
        """Clear all products, attributes, and media in the store"""
        print("🧹 Start clearing all products and related data in the store...")
        
        try:
            # 1. Delete all products
            print("📦 Clear products...")
            all_products = self.wc_client.get_all_products()

            deleted_products = 0
            failed_products = 0
            
            if all_products:
                for product in all_products:
                    product_id = product.get('id')
                    product_name = product.get('name', 'Unknown')
                    
                    try:
                        success, result = self.wc_client.delete_product(str(product_id), force=True)
                        if success:
                            print(f"   ✅ Delete product: {product_name} (ID: {product_id})")
                            deleted_products += 1
                        else:
                            print(f"   ❌ Delete failed: {product_name} - {result}")
                            failed_products += 1
                    except Exception as e:
                        print(f"   ❌ Delete product {product_name} failed: {e}")
                        failed_products += 1
                    
                    time.sleep(0.3)
            
            # 2. Clear custom attributes
            print("🏷️ Clear product attributes...")
            success, attributes = self.wc_client.get_product_attributes()
            deleted_attributes = 0
            failed_attributes = 0
            
            if success and attributes:
                test_attribute_names = ["Color", "Size", "Material"]
                
                for attr in attributes:
                    attr_name = attr.get('name', '')
                    attr_id = attr.get('id')
                    
                    if attr_name in test_attribute_names:
                        try:
                            delete_url = f"{self.wc_client.api_base}/products/attributes/{attr_id}"
                            response = self.wc_client.session.delete(delete_url, params={'force': True})
                            
                            if response.status_code in [200, 204]:
                                print(f"   ✅ Delete attribute: {attr_name} (ID: {attr_id})")
                                deleted_attributes += 1
                            else:
                                print(f"   ⚠️ Skip attribute: {attr_name}")
                        except Exception as e:
                            print(f"   ❌ Delete attribute {attr_name} failed: {e}")
                            failed_attributes += 1
                        
                        time.sleep(0.3)
            

            # 3. Clear orders
            print("🗑️ Start deleting all orders...")

            page = 1
            per_page = 20  # Reduce page size to avoid timeout
            total_deleted = 0
            max_pages = 10  # Limit max pages to avoid infinite loop

            while page <= max_pages:
                # Get order list
                success, orders = self.wc_client._make_request('GET', 'orders', params={"page": page, "per_page": per_page})
                if not success:
                    print(f"⚠️ Get orders failed: {orders}")
                    break

                if not orders or not isinstance(orders, list) or len(orders) == 0:
                    # No more orders
                    break

                print(f"   📄 Process page {page}, found {len(orders)} orders")

                for i, order in enumerate(orders):
                    order_id = order.get('id')
                    if not order_id:
                        continue

                    try:
                        success, response = self.wc_client.delete_order(order_id)
                        if success:
                            total_deleted += 1
                            print(f"   ✅ Delete order: {order_id}")
                        else:
                            print(f"   ⚠️ Delete order {order_id} failed: {response}")
                    except Exception as e:
                        print(f"   ❌ Delete order {order_id} failed: {e}")

                    # Add delay to avoid request too fast
                    if i % 5 == 0:  # Pause for 5 orders
                        time.sleep(0.5)

                # If the number of orders returned is less than per_page, it means it's the last page
                if len(orders) < per_page:
                    break

                page += 1
                time.sleep(1)  # Delay between pages

            clear_result = {
                "success": failed_products == 0 and failed_attributes == 0,
                "products": {
                    "total_found": len(all_products) if all_products else 0,
                    "deleted": deleted_products,
                    "failed": failed_products
                },
                "attributes": {
                    "deleted": deleted_attributes,
                    "failed": failed_attributes
                },
                "orders": {
                    "deleted": total_deleted
                },
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"\n📊 Clear completed:") 
            print(f"   Products: deleted {deleted_products} failed {failed_products} ")
            print(f"   Attributes: deleted {deleted_attributes} failed {failed_attributes} ")
            print(f"   Orders: deleted {total_deleted} ")
            
            return clear_result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            print(f"❌ Clear failed: {e}")
            return error_result
    
    def setup_product_attributes(self) -> Dict:
        """Setup product attributes (color, size, etc.)"""
        print("🏷️ Setup product attributes...")
        
        attributes_to_create = [
            {
                "name": "Color",
                "slug": "color",
                "type": "select",
                "order_by": "menu_order",
                "has_archives": True,
                "terms": [
                    {"name": "Red", "slug": "red"},
                    {"name": "Blue", "slug": "blue"},
                    {"name": "Green", "slug": "green"},
                    {"name": "Yellow", "slug": "yellow"},
                ]
            },
        ]
        
        created_attributes = []
        
        for attr_data in attributes_to_create:
            # Create attribute
            print(f"   Create attribute: {attr_data['name']}")
            
            attribute_info = {
                "name": attr_data["name"],
                "slug": attr_data["slug"],
                "type": attr_data["type"],
                "order_by": attr_data["order_by"],
                "has_archives": attr_data["has_archives"]
            }
            
            success, attr_result = self.wc_client.create_product_attribute(attribute_info)
            
            if success:
                attr_id = attr_result.get('id')
                print(f"     ✅ Attribute created successfully (ID: {attr_id})")
                
                # Create attribute terms
                created_terms = []
                for term_data in attr_data["terms"]:
                    print(f"     Create attribute term: {term_data['name']}")
                    
                    success_term, term_result = self.wc_client.create_attribute_term(
                        str(attr_id), term_data
                    )
                    
                    if success_term:
                        created_terms.append({
                            "id": term_result.get('id'),
                            "name": term_result.get('name'),
                            "slug": term_result.get('slug')
                        })
                        print(f"       ✅ Attribute term created successfully: {term_data['name']}")
                    else:
                        print(f"       ❌ Attribute term created failed: {term_data['name']} - {term_result}")
                    
                    time.sleep(0.3)
                
                created_attributes.append({
                    "id": attr_id,
                    "name": attr_result.get('name'),
                    "slug": attr_result.get('slug'),
                    "terms": created_terms
                })
                
                self.created_attributes.append(created_attributes[-1])
                
            else:
                print(f"     ❌ Attribute created failed: {attr_data['name']} - {attr_result}")
            
            time.sleep(0.5)
        
        return {
            "success": len(created_attributes) > 0,
            "created_attributes": created_attributes,
            "total_created": len(created_attributes)
        }
    
    def create_test_products(self, delete_existing_orders=True) -> Dict:
        """
        Create test products
        Includes:
        1. Variable products (with different specifications and corresponding images)
        2. Simulated last week's sales data
        
        Args:
            delete_existing_orders: Whether to delete existing orders before creating new orders (default True)
        
        Returns:
            Dictionary with creation results
        """
        print("🛒 Start creating test products...")
        
        #1. Upload test images
        print("🎨 Create and upload test images...")
        test_images = self.image_manager.create_test_images(6)
        uploaded_images = self.image_manager.upload_test_images(test_images)
        self.uploaded_images = uploaded_images
        
        if not uploaded_images:
            return {"success": False, "error": "Failed to upload test images"}
        
        # Update image ID to real media ID
        print("🔄 Update image ID mapping...")
        self.image_ids = {}
        for img in uploaded_images:
            color = img.get('color', '')
            media_id = img.get('media_id')
            if color and media_id:
                self.image_ids[color] = media_id
                print(f"   {color}: {media_id}")
        
        print(f"✅ Image IDs updated: {self.image_ids}")
        
        # 2. Get attribute information
        color_attr = next((attr for attr in self.created_attributes if attr['name'] == 'Color'), None)
        
        if not color_attr:
            return {"success": False, "error": "Missing required product attributes"}
        
        # 3. Define test product data
        test_products = self._generate_variable_product_data(color_attr)

        print(f"   🔄 Test product data: {test_products}")
        
        created_count = 0
        failed_count = 0
        
        for product_data in test_products:
            success, result = self.wc_client.create_product(product_data)
            if success:
                product_id = result.get('id')
                product_name = result.get('name')
                product_type = result.get('type', 'simple')
                
                created_product_info = {
                    'id': product_id,
                    'name': product_name,
                    'type': product_type,
                    'variations': []
                }
                
                print(f"✅ Create product: {product_name} (ID: {product_id}, Type: {product_type})")
                
                # Verify product status
                product_status = result.get('status', 'unknown')
                if product_status != 'publish':
                    print(f"⚠️ Product status is: {product_status}, trying to update to publish")
                    update_data = {"status": "publish"}
                    success_update, update_result = self.wc_client._make_request('PUT', f'products/{product_id}', data=update_data)
                    if success_update:
                        print(f"✅ Product status updated to publish")
                    else:
                        print(f"❌ Update product status failed: {update_result}")
                
                # If it's a variable product, create variations
                if product_type == 'variable':
                    variations_info = self._create_product_variations(
                        product_id, product_data, color_attr
                    )
                    created_product_info['variations'] = variations_info
                
                self.created_products.append(created_product_info)
                created_count += 1
            else:
                print(f"❌ Create product failed: {product_data.get('name')} - {result}")
                failed_count += 1
            
            # Avoid API limit
            time.sleep(1.0)
        
        # 4. Create simulated order data
        if created_count > 0:
            print("📊 Create simulated sales data...")
            # Based on the parameter, decide whether to delete existing orders
            if delete_existing_orders:
                self._delete_existing_orders()
            else:
                print("ℹ️ Keep existing orders, new orders will be added to existing orders")
            # Use 42 as the default random seed to ensure reproducibility, if you need true random, pass None
            self._create_mock_orders(random_seed=42)
        
        setup_result = {
            "success": failed_count == 0,
            "created_count": created_count,
            "failed_count": failed_count,
            "created_products": self.created_products,
            "variable_products_count": len([p for p in self.created_products if p.get('type') == 'variable'])
        }
        
        print(f"Product creation completed:")
        print(f"   Created successfully: {created_count} products")
        print(f"   Created failed: {failed_count} products")
        print(f"   Variable products: {setup_result['variable_products_count']} products")
        
        return setup_result
    
    def _generate_variable_product_data(self, color_attr: Dict) -> List[Dict]:
        """Generate variable product data"""
        import random
        current_date = datetime.now()

        # Multiple different types of products, increase the authenticity of the test
        product_templates = [
            {
                "name": "Rainbow Sneakers",
                "description": "Comfortable and lightweight sneakers available in multiple colors, suitable for daily sports and casual wear",
                "short_description": "Stylish Rainbow Sneakers",
                "base_price": "199.99",
                "days_ago": 45,
                "default_color": "Yellow"  # Set default main image color to yellow, avoid conflict with the best selling variation
            },
            {
                "name": "Fashion Backpack",
                "description": "Large capacity multifunctional backpack made with high-quality materials, available in multiple colors",
                "short_description": "Multi-color Fashion Backpack",
                "base_price": "129.99",
                "days_ago": 30,
                "default_color": "Green"  # Set default main image color to green, avoid conflict with the best selling variation
            },
            {
                "name": "Wireless Bluetooth Headphones",
                "description": "High-quality wireless Bluetooth headphones with noise reduction feature, available in various colorful designs",
                "short_description": "Colorful Bluetooth Headphones",
                "base_price": "299.99",
                "days_ago": 60,
                "default_color": "Blue"  
            }
        ]

        products = []

        for template in product_templates:
            # Get the image ID corresponding to the default color
            default_color = template["default_color"]
            main_image_id = self.image_ids.get(default_color)

            # Build the main image array
            images_array = []
            if main_image_id:
                # Use media ID instead of URL, avoid WooCommerce re-downloading
                images_array.append({
                    "id": main_image_id,  # Directly use media ID
                    "position": 0  # Main image position
                })
                print(f"   🎨 Set main image for {template['name']}: {default_color} (ID: {main_image_id})")
            else:
                print(f"   ⚠️ No image ID found for {default_color}")

            product = {
                "name": template["name"],
                "type": "variable",
                "description": template["description"],
                "short_description": template["short_description"],
                "regular_price": "",
                "manage_stock": False,
                "stock_status": "instock",
                "status": "publish",  # Ensure product is published
                "date_created": (current_date - timedelta(days=template["days_ago"])).isoformat(),
                "images": images_array,  # Use the correct images array
                "attributes": [
                    {
                        "id": color_attr['id'],
                        "name": color_attr['name'],
                        "position": 0,
                        "visible": True,
                        "variation": True,
                        "options": [term['name'] for term in color_attr['terms']]
                    }
                ],
                "meta_data": [
                    {"key": "test_product_type", "value": "variable_product"},
                    {"key": "base_price", "value": template["base_price"]},
                    {"key": "created_days_ago", "value": str(template["days_ago"])},
                    {"key": "default_main_image_color", "value": default_color}  # Record default main image color
                ]
            }
            products.append(product)

        return products
    
    def _create_product_variations(self, product_id: int, product_data: Dict, 
                                   color_attr: Dict) -> List[Dict]:
        """Create variations for the product"""
        import random
        
        print(f"   🔄 Create variations for the product {product_id}...")
        
        variations_info = []
        variation_counter = 0
        
        # Get the base price of the product
        base_price = "199.99"  # Default price
        for meta in product_data.get('meta_data', []):
            if meta.get('key') == 'base_price':
                base_price = meta.get('value', '199.99')
                break
        
        product_name = product_data.get('name', '')
        
        # Create variations for all colors of the product
        for color_term in color_attr['terms']:
            color_name = color_term['name']
            
            # Set stock and price variation based on the product type
            stock_quantity = random.randint(10, 25)
            
            # Price may have slight fluctuations
            price_float = float(base_price)
            price_variation = random.uniform(0.95, 1.05)  # ±5% price variation
            final_price = round(price_float * price_variation, 2)
            
            variation_data = {
                "regular_price": str(final_price),
                "stock_quantity": stock_quantity,
                "manage_stock": True,
                "stock_status": "instock",
                "attributes": [
                    {
                        "id": color_attr['id'],
                        "name": color_attr['name'],
                        "option": color_term['name']
                    }
                ],
                "meta_data": [
                    {"key": "test_variation_color", "value": color_term['name']},
                    {"key": "base_price", "value": base_price},
                    {"key": "price_variation_factor", "value": str(round(price_variation, 3))}
                ]
            }
            
            # Only add image when the color corresponding image ID exists
            if color_name in self.image_ids and self.image_ids[color_name]:
                variation_data["image"] = {
                    "id": self.image_ids[color_name]
                }
                print(f"     🖼️ Set variation image: {color_name} -> ID {self.image_ids[color_name]}")
            else:
                print(f"     ⚠️ No image ID found for color {color_name}")
            
            success, variation_result = self.wc_client.create_variation(str(product_id), variation_data)
            
            if success:
                variation_info = {
                    'id': variation_result.get('id'),
                    'color': color_term['name'],
                    'price': str(final_price),
                    'image_id': self.image_ids.get(color_name),  # Use real image ID
                    'stock_quantity': stock_quantity
                }
                variations_info.append(variation_info)
                print(f"     ✅ Create variation: {color_term['name']} - ¥{final_price} (ID: {variation_result.get('id')})")
                variation_counter += 1
            else:
                print(f"     ❌ Create variation failed: {color_term['name']} - {variation_result}")
            
            time.sleep(0.5)
        
        print(f"   📊 {product_name} created {variation_counter} variations")
        return variations_info
    
    def _create_mock_orders(self, random_seed=None):
        """Create and upload simulated order data (simulated last week's sales)
        
        Args:
            random_seed: Random seed, None means true random, number means reproducible random result
        """
        import random
        
        # Set random seed
        if random_seed is not None:
            random.seed(random_seed)
            print(f"📦 Create simulated sales data (random seed: {random_seed})...")
        else:
            print("📦 Create simulated sales data (true random mode)...")
        
        print("   🎲 Use random popularity distribution, any variation can become the best seller")

        today = datetime.now()
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)

        # Create a list of all orders, then shuffle them
        all_orders_plan = []

        for product in self.created_products:
            if product.get('type') == 'variable' and product.get('variations'):
                variations = product['variations']
                product_name = product.get('name', '')
                
                # Set base sales multiplier based on the product type
                if 'Sneakers' in product_name:
                    product_multiplier = 1.0  # Sneakers sales standard
                elif 'Backpack' in product_name:
                    product_multiplier = 0.7  # Backpack sales lower
                elif 'Headphones' in product_name:
                    product_multiplier = 1.2  # Headphones sales higher
                else:
                    product_multiplier = 1.0
                
                # Randomly assign popularity to each variation, create random sales distribution
                popularity_levels = ['High popular', 'Medium popular', 'Normal', 'Low popular']
                variation_popularity = random.sample(popularity_levels, min(len(variations), len(popularity_levels)))
                
                # If the number of variations exceeds the number of popularity levels, the rest are randomly assigned
                if len(variations) > len(popularity_levels):
                    additional_popularity = [random.choice(popularity_levels) for _ in range(len(variations) - len(popularity_levels))]
                    variation_popularity.extend(additional_popularity)
                
                print(f"🛍️ Create orders for '{product_name}' (sales multiplier: {product_multiplier})")
                print(f"   📊 Variation popularity distribution: {dict(zip([v.get('color', f'Variation{i}') for i, v in enumerate(variations)], variation_popularity))}")

                for i, variation in enumerate(variations):
                    # Determine the sales range based on the randomly assigned popularity
                    popularity = variation_popularity[i]
                    
                    if popularity == 'High popular':
                        base_sales_range = (6, 9)  # Highest sales
                    elif popularity == 'Medium popular':
                        base_sales_range = (4, 5)   # Medium sales
                    elif popularity == 'Normal':
                        base_sales_range = (2, 3)    # Normal sales
                    else:  # Low popular
                        base_sales_range = (1, 2)    # Low sales
                    
                    # Apply product type multiplier
                    min_sales = max(1, int(base_sales_range[0] * product_multiplier))
                    max_sales = max(2, int(base_sales_range[1] * product_multiplier))
                    base_sales = random.randint(min_sales, max_sales)
                    
                    print(f"   🎯 {variation.get('color', f'Variation{i}')} ({popularity}): Plan {base_sales} orders")
                    
                    # Generate random date and time for each order
                    for order_num in range(base_sales):
                        # Generate random date and time within the last week
                        random_day = random.randint(0, 6)  # Monday to Sunday
                        random_hour = random.randint(8, 22)  # 8 to 22
                        random_minute = random.randint(0, 59)
                        random_second = random.randint(0, 59)
                        
                        order_date = last_monday + timedelta(
                            days=random_day,
                            hours=random_hour,
                            minutes=random_minute,
                            seconds=random_second
                        )
                        
                        # Random quantity: mostly 1, occasionally 2-3
                        quantity = random.choices([1, 2, 3], weights=[70, 25, 5])[0]
                        
                        all_orders_plan.append({
                            'product': product,
                            'variation': variation,
                            'variation_index': i,
                            'variation_popularity': variation_popularity[i],  # Save popularity information
                            'order_date': order_date,
                            'quantity': quantity,
                            'order_number': order_num
                        })

        # Shuffle order creation order (sort by date and time, but add some randomness)
        print(f"📋 Plan to create {len(all_orders_plan)} orders...")
        
        # First sort by date, then add some random shuffling
        all_orders_plan.sort(key=lambda x: x['order_date'])
        
        # Group shuffling: shuffle 3-5 orders at a time, keep the general time order but add randomness
        shuffled_orders = []
        group_size = random.randint(3, 5)
        for i in range(0, len(all_orders_plan), group_size):
            group = all_orders_plan[i:i+group_size]
            random.shuffle(group)
            shuffled_orders.extend(group)
        
        print(f"🔀 Order creation order has been shuffled, starting...")

        # Execute order creation
        successful_orders = 0
        failed_orders = 0
        
        for order_plan in shuffled_orders:
            product = order_plan['product']
            variation = order_plan['variation']
            variation_index = order_plan['variation_index']
            variation_popularity_info = order_plan['variation_popularity']
            order_date = order_plan['order_date']
            quantity = order_plan['quantity']
            product_name = product.get('name', '')
            
            # Construct WooCommerce order data
            order_data = {
                "status": "completed",
                "customer_id": 1,
                "payment_method": "bacs",
                "payment_method_title": "Direct Bank Transfer",
                # Note: date_created is a read-only field, API will ignore this value and use current time
                # "date_created": order_date.isoformat(),
                "line_items": [
                    {
                        "product_id": product['id'],
                        "variation_id": variation['id'],
                        "quantity": quantity,
                        "price": variation['price']
                    }
                ],
                "meta_data": [
                    {"key": "test_order", "value": "true"},
                    {"key": "test_week", "value": f"{last_monday.date()}_to_{last_sunday.date()}"},
                    {"key": "original_date_created", "value": order_date.isoformat()},  # Store original date
                    {"key": "simulated_historical_order", "value": "true"},
                    {"key": "variation_color", "value": variation.get('color', '')},
                    {"key": "quantity_ordered", "value": str(quantity)},
                    {"key": "variation_index", "value": str(variation_index)},
                    {"key": "variation_popularity", "value": variation_popularity_info}
                ]
            }

            # Call create_order to upload order
            success, response = self.wc_client.create_order(order_data)

            # print("success", success)
            # print("response", response)

            if success:
                wc_order_id = response.get('id')
                successful_orders += 1
                print(f"✅ Order #{wc_order_id} created successfully - {variation.get('color', '')} x{quantity} @ {order_date.strftime('%m-%d %H:%M')}")
                
                # Try to update the historical creation date of the order
                try:
                    self._update_order_historical_date(wc_order_id, order_date.isoformat())
                except Exception as e:
                    print(f"⚠️ Update order #{wc_order_id} historical date failed: {e}")
            else:
                wc_order_id = None
                failed_orders += 1
                print(f"❌ Create order failed: {response}")

            # Save created order information               
            self.created_orders.append({
                'product_id': product['id'],
                'product_name': product_name,
                'variation_id': variation['id'],
                'sales_count': quantity,  # Now record actual quantity
                'order_date': order_date.isoformat(),
                'variation_color': variation.get('color', ''),
                'variation_index': variation_index,
                'variation_popularity': variation_popularity_info,
                'expected_top_seller': False,  # Now cannot simply determine based on index
                'wc_order_id': wc_order_id,
                'quantity': quantity
            })
            
            # Add delay to avoid API limit
            time.sleep(0.8)

        # Count detailed sales information for each variation
        variation_stats = {}
        total_quantity = 0
        
        for order in self.created_orders:
            if order['wc_order_id']:  # Only count successfully created orders
                color = order['variation_color']
                quantity = order['quantity']
                popularity = order.get('variation_popularity', 'Normal')
                product_name = order.get('product_name', 'Unknown product')
                
                key = f"{product_name}-{color}"
                if key not in variation_stats:
                    variation_stats[key] = {
                        'product_name': product_name,
                        'color': color,
                        'popularity': popularity,
                        'orders': 0, 
                        'total_quantity': 0,
                        'variation_id': order['variation_id']
                    }
                variation_stats[key]['orders'] += 1
                variation_stats[key]['total_quantity'] += quantity
                total_quantity += quantity
        
        # Sort by sales
        sorted_sales = sorted(variation_stats.items(), key=lambda x: x[1]['total_quantity'], reverse=True)
        
        print(f"\n📊 Simulated sales data created completed:")
        print(f"   ✅ Successfully created: {successful_orders} orders")
        print(f"   ❌ Create failed: {failed_orders} orders")
        print(f"   📦 Total sales: {total_quantity} items")
        print(f"   📅 Time range: {last_monday.date()} to {last_sunday.date()}")
        
        print(f"\n🏆 All variations sales ranking:")
        for i, (key, stats) in enumerate(sorted_sales, 1):
            popularity_emoji = {
                'High popular': '🔥', 'Medium popular': '⭐', 'Normal': '👍', 'Low popular': '💤'
            }.get(stats['popularity'], '📦')
            
            print(f"   {i}. {stats['product_name']} - {stats['color']} {popularity_emoji}: "
                  f"{stats['total_quantity']} items ({stats['orders']} orders)")
        
        if sorted_sales:
            top_seller_info = sorted_sales[0][1]
            print(f"\n🥇 Actual best sales variation: {top_seller_info['product_name']} - {top_seller_info['color']} "
                  f"(Expected: {top_seller_info['popularity']})")
            
            # Group by product to display the best sales variation
            product_top_sellers = {}
            for key, stats in sorted_sales:
                product_name = stats['product_name']
                if product_name not in product_top_sellers:
                    product_top_sellers[product_name] = stats
            
            print(f"\n🎯 All products best sales variation:")
            for product_name, stats in product_top_sellers.items():
                print(f"   📱 {product_name}: {stats['color']} ({stats['total_quantity']} items)")
        
        # Detailed order list (optional, used for debugging)
        if len(self.created_orders) <= 20:  # Only show detailed information when the number of orders is less than 20
            print(f"\n📋 Detailed order list:")
            for order in self.created_orders:
                if order['wc_order_id']:
                    order_time = datetime.fromisoformat(order['order_date'])
                    print(f"   Order #{order['wc_order_id']}: {order['variation_color']} x{order['quantity']} @ {order_time.strftime('%m-%d %H:%M')}")
        else:
            print(f"\n📋 Order list too long, detailed information has been omitted (total {len(self.created_orders)} records)")
    
    def _delete_existing_orders(self):
        """Delete all existing orders, ensure a clean environment before creating orders"""
        print("🗑️ Delete existing orders...")
        
        try:
            page = 1
            per_page = 50
            total_deleted = 0
            start_time = time.time()
            
            while True:
                # Get order list
                success, orders = self.wc_client._make_request('GET', 'orders', params={"page": page, "per_page": per_page})
                if not success:
                    print(f"⚠️ Get order failed: {orders}")
                    break

                if not orders or len(orders) == 0:
                    # No more orders
                    break

                print(f"   📋 Page {page}, found {len(orders)} orders")
                
                for i, order in enumerate(orders, 1):
                    order_id = order['id']
                    order_status = order.get('status', 'unknown')
                    success, response = self.wc_client.delete_order(order_id)
                    if success:
                        total_deleted += 1
                        print(f"   ✅ Delete order #{order_id} ({order_status}) [{i}/{len(orders)}]")
                    else:
                        print(f"   ❌ Delete order #{order_id} failed: {response}")
                    
                    # Add brief delay to avoid API limit
                    time.sleep(0.3)

                page += 1
                
                # Safety check: avoid infinite loop
                if page > 50:  # Maximum 50 pages, 50 orders per page = 2500 orders
                    print("⚠️ Reached maximum page limit, stopping deletion")
                    break

            elapsed_time = time.time() - start_time
            if total_deleted > 0:
                print(f"✅ Successfully deleted {total_deleted} existing orders (time: {elapsed_time:.1f} seconds)")
            else:
                print("ℹ️ No orders found to delete")
                
        except Exception as e:
            print(f"❌ Error deleting orders: {e}")
    
    def _update_order_historical_date(self, order_id: int, historical_date: str):
        """
        Update order metadata through WooCommerce REST API, then update creation date through database directly
        
        Args:
            order_id: WooCommerce order ID
            historical_date: Historical date (ISO format)
        """
        try:
            # Method 1: Update metadata through REST API (this always works)
            update_data = {
                "meta_data": [
                    {"key": "original_date_created", "value": historical_date},
                    {"key": "simulated_historical_order", "value": "true"},
                    {"key": "date_update_attempted", "value": datetime.now().isoformat()}
                ]
            }
            
            success, result = self.wc_client.update_order(str(order_id), update_data)

            if success:
                print(f"✅ Order #{order_id} metadata updated, historical date: {historical_date}")
            else:
                print(f"⚠️ Update order #{order_id} metadata failed: {result}")
                
            # Method 2: If possible, try to update the database directly (requires database access)
            # This can be implemented through a WordPress plugin or direct database access
            # Since we don't have direct database access, we only record the orders that need to be updated
            
        except Exception as e:
            print(f"❌ Error updating order #{order_id} historical date: {e}")
    
    def get_expected_results(self) -> Dict:
        """Get expected results, for evaluation"""
        expected_updates = {}
        
        # Calculate actual sales for each variation
        variation_sales = {}
        for order in self.created_orders:
            if order['wc_order_id']:  # Only count successfully created orders
                variation_id = order['variation_id']
                quantity = order['quantity']
                if variation_id not in variation_sales:
                    variation_sales[variation_id] = 0
                variation_sales[variation_id] += quantity
        
        for product in self.created_products:
            if product.get('type') == 'variable' and product.get('variations'):
                variations = product['variations']
                if variations:
                    # Calculate actual sales for each variation and find the best sales variation
                    variation_sales_data = []
                    for variation in variations:
                        variation_id = variation['id']
                        total_sales = variation_sales.get(variation_id, 0)
                        variation_sales_data.append({
                            'variation': variation,
                            'total_sales': total_sales
                        })
                    
                    # Sort by sales
                    variation_sales_data.sort(key=lambda x: x['total_sales'], reverse=True)
                    
                    if variation_sales_data:
                        top_variation_data = variation_sales_data[0]
                        top_variation = top_variation_data['variation']
                        
                        expected_updates[product['id']] = {
                            'product_name': product['name'],
                            'expected_top_variation_id': top_variation['id'],
                            'expected_featured_image_id': top_variation.get('image_id'),
                            'expected_color': top_variation.get('color', ''),
                            'expected_sales_quantity': top_variation_data['total_sales'],
                            'current_featured_image_id': None,  # Current featured image (initial None or default image)
                            'all_variations_sales': [
                                {
                                    'variation_id': vd['variation']['id'],
                                    'color': vd['variation'].get('color', ''),
                                    'sales': vd['total_sales']
                                }
                                for vd in variation_sales_data
                            ]
                        }
        
        # Count overall information
        total_orders = len([o for o in self.created_orders if o['wc_order_id']])
        total_quantity = sum(o['quantity'] for o in self.created_orders if o['wc_order_id'])
        
        today = datetime.now()
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        
        return {
            "expected_updates": expected_updates,
            "total_products_to_update": len(expected_updates),
            "analysis_period": {
                "description": "Last week (Monday to Sunday)",
                "start_date": last_monday.date().isoformat(),
                "end_date": last_sunday.date().isoformat(),
                "note": "Based on random popularity and actual simulated sales data, any variation can become the best sales"
            },
            "created_test_data": {
                "products_count": len(self.created_products),
                "variations_total": sum(len(p.get('variations', [])) for p in self.created_products),
                "total_orders": total_orders,
                "total_quantity_sold": total_quantity,
                "average_order_quantity": round(total_quantity / total_orders, 2) if total_orders > 0 else 0
            },
            "sales_summary": {
                variation_id: sales for variation_id, sales in variation_sales.items()
            }
        }
    
    def cleanup_test_data(self) -> Dict:
        """Clean all test data"""
        print("🧹 Start cleaning test data...")
        
        cleanup_results = {
            "products": {"deleted": 0, "failed": 0},
            "images": {"deleted": 0, "failed": 0},
            "attributes": {"deleted": 0, "failed": 0}
        }
        
        # 1. Delete products (will automatically delete variations)
        for product in self.created_products:
            product_id = product.get('id')
            product_name = product.get('name')
            
            success, result = self.wc_client.delete_product(str(product_id), force=True)
            if success:
                print(f"✅ Delete product: {product_name} (ID: {product_id})")
                cleanup_results["products"]["deleted"] += 1
            else:
                print(f"❌ Delete product failed: {product_name} - {result}")
                cleanup_results["products"]["failed"] += 1
            
            time.sleep(0.3)
        
        # 2. Clean attributes
        for attr in self.created_attributes:
            attr_id = attr.get('id')
            attr_name = attr.get('name')
            
            try:
                delete_url = f"{self.wc_client.api_base}/products/attributes/{attr_id}"
                response = self.wc_client.session.delete(delete_url, params={'force': True})
                
                if response.status_code in [200, 204]:
                    print(f"✅ Delete attribute: {attr_name} (ID: {attr_id})")
                    cleanup_results["attributes"]["deleted"] += 1
                else:
                    print(f"❌ Delete attribute failed: {attr_name}")
                    cleanup_results["attributes"]["failed"] += 1
            except Exception as e:
                print(f"❌ Delete attribute {attr_name} failed: {e}")
                cleanup_results["attributes"]["failed"] += 1
            
            time.sleep(0.3)
        
        print(f"\n📊 Clean completed:")
        print(f"   Products: deleted {cleanup_results['products']['deleted']} items")
        print(f"   Images: deleted {cleanup_results['images']['deleted']} items")
        print(f"   Attributes: deleted {cleanup_results['attributes']['deleted']} items")
        
        return cleanup_results


def main():
    """Main function - for independent running of test data setup"""
    import sys
    
    # Check command line parameters
    delete_orders = True  # Default to delete existing orders
    if len(sys.argv) > 1:
        if sys.argv[1] == "--keep-orders":
            delete_orders = False
            print("🔧 Parameters: keep existing orders")
        elif sys.argv[1] == "--delete-orders":
            delete_orders = True
            print("🔧 Parameters: delete existing orders")
        elif sys.argv[1] == "--help":
            print("📖 Usage:")
            print("  python setup_test_products.py                # Default to delete existing orders")
            print("  python setup_test_products.py --delete-orders # Explicitly delete existing orders")
            print("  python setup_test_products.py --keep-orders   # Keep existing orders")
            print("  python setup_test_products.py --help         # Show this help")
            return True
    
    # Read configuration from token configuration file
    from token_key_session import all_token_key_session
    
    site_url = all_token_key_session.woocommerce_site_url
    consumer_key = all_token_key_session.woocommerce_api_key
    consumer_secret = all_token_key_session.woocommerce_api_secret
    
    print(f"🚀 Initialize test product setup: {site_url}")
    
    setup = TestProductSetup(site_url, consumer_key, consumer_secret)
    
    try:
        # 1. Clean existing data in the store
        print("\n" + "="*60)
        print("Step 1: Clean existing data in the store")
        print("="*60)
        
        clear_result = setup.clear_all_products()
        if not clear_result.get('success'):
            print("⚠️ Clean not fully successful, but continue to the next step...")
        
        time.sleep(3)
        
        # 2. Set product attributes
        print("\n" + "="*60)
        print("Step 2: Set product attributes")
        print("="*60)
        
        attr_result = setup.setup_product_attributes()
        if not attr_result.get('success'):
            print("❌ Attribute setting failed!")
            return False
        
        time.sleep(2)
        
        # 3. Create test products
        print("\n" + "="*60)
        print("Step 3: Create test products and data")
        print("="*60)
        
        product_result = setup.create_test_products(delete_existing_orders=delete_orders)
        
        if product_result.get('success'):
            print("✅ Test data setup completed!")
            
            # Save expected results
            expected_results = setup.get_expected_results()
            results_path = str(Path(__file__).parent.parent) + "/groundtruth_workspace/expected_results.json"
            with open(results_path, 'w', encoding='utf-8') as f:
                json.dump(expected_results, f, indent=2, ensure_ascii=False)
            print("📄 Expected results saved to expected_results.json")
            
            return True
        else:
            print("❌ Test product creation failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        return False


def clear_store_only():
    """Only clear the store"""
    from token_key_session import all_token_key_session
    
    site_url = all_token_key_session.woocommerce_site_url
    consumer_key = all_token_key_session.woocommerce_api_key
    consumer_secret = all_token_key_session.woocommerce_api_secret
    
    print(f"🚀 Connect to store: {site_url}")
    
    setup = TestProductSetup(site_url, consumer_key, consumer_secret)
    clear_result = setup.clear_all_products()
    
    return clear_result.get('success', False)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--clear-only":
        clear_store_only()
    else:
        main()