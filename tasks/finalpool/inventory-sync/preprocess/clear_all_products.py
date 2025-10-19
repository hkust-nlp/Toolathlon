#!/usr/bin/env python3
"""
Tool to clear all products from a WooCommerce store.
USE WITH CAUTION: This operation will DELETE all products and categories from the store.
"""

import requests
from requests.auth import HTTPBasicAuth
import json
import time
import sys
from typing import List, Dict, Any, Tuple
import os

# Add project root directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
task_dir = os.path.dirname(current_dir)
sys.path.append(task_dir)

class WooCommerceCleaner:
    """WooCommerce Store Cleanup Utility"""
    
    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str):
        """
        Initialize the cleaner
        
        Args:
            site_url: WooCommerce site URL
            consumer_key: WooCommerce API consumer key
            consumer_secret: WooCommerce API consumer secret
        """
        self.site_url = site_url.rstrip('/')
        self.api_base = f"{self.site_url}/wp-json/wc/v3"
        self.auth = HTTPBasicAuth(consumer_key, consumer_secret)
        self.session = requests.Session()
        self.session.auth = self.auth
        
        # API rate limiting
        self.request_delay = 0.2  # 200ms between requests
        self.batch_size = 100     # Batch operation size
        
        print(f"🔧 Initialized WooCommerce Cleaner: {self.site_url}")
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Tuple[bool, Any]:
        """Send API request"""
        url = f"{self.api_base}/{endpoint}"
        
        try:
            time.sleep(self.request_delay)
            
            if method.upper() == 'GET':
                response = self.session.get(url, params=params)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, params=params)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, params=params)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, params=params)
            else:
                return False, f"Unsupported HTTP method: {method}"
            
            if response.status_code in [200, 201, 204]:
                try:
                    return True, response.json() if response.text else {}
                except:
                    return True, {}
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            return False, str(e)
    
    def test_connection(self) -> bool:
        """Test API connection"""
        print("🔍 Testing API connection...")
        
        success, response = self._make_request('GET', 'products', params={'per_page': 1})
        
        if success:
            print("✅ API connection successful")
            return True
        else:
            print(f"❌ API connection failed: {response}")
            return False
    
    def get_all_products(self) -> List[Dict[str, Any]]:
        """Fetch all products"""
        print("📦 Fetching all products...")
        
        all_products = []
        page = 1
        
        while True:
            success, products = self._make_request('GET', 'products', params={
                'per_page': self.batch_size,
                'page': page,
                'status': 'any'  # Get products of all statuses
            })
            
            if not success:
                print(f"❌ Failed to get products on page {page}: {products}")
                break
            
            if not products:
                break
            
            all_products.extend(products)
            print(f"  📄 Page {page}: {len(products)} products")
            
            if len(products) < self.batch_size:
                break
            
            page += 1
        
        print(f"📊 Found {len(all_products)} products in total")
        return all_products
    
    def get_all_categories(self) -> List[Dict[str, Any]]:
        """Fetch all product categories"""
        print("📂 Fetching all product categories...")
        
        all_categories = []
        page = 1
        
        while True:
            success, categories = self._make_request('GET', 'products/categories', params={
                'per_page': self.batch_size,
                'page': page
            })
            
            if not success:
                print(f"❌ Failed to get categories on page {page}: {categories}")
                break
            
            if not categories:
                break
            
            all_categories.extend(categories)
            print(f"  📄 Page {page}: {len(categories)} categories")
            
            if len(categories) < self.batch_size:
                break
            
            page += 1
        
        print(f"📊 Found {len(all_categories)} categories in total")
        return all_categories
    
    def delete_products_batch(self, product_ids: List[int]) -> Tuple[int, int]:
        """Batch delete products"""
        success_count = 0
        failed_count = 0
        
        # WooCommerce supports batch deletion
        batch_data = {
            'delete': [{'id': pid} for pid in product_ids]
        }
        
        success, response = self._make_request('POST', 'products/batch', data=batch_data)
        
        if success:
            deleted = response.get('delete', [])
            for item in deleted:
                if 'error' in item:
                    failed_count += 1
                    print(f"    ❌ Failed to delete product {item.get('id', 'unknown')}: {item['error']['message']}")
                else:
                    success_count += 1
        else:
            print(f"❌ Batch product deletion failed: {response}")
            failed_count = len(product_ids)
        
        return success_count, failed_count
    
    def delete_all_products(self, confirm: bool = False) -> Tuple[int, int]:
        """Delete all products"""
        if not confirm:
            print("⚠️ This operation will delete all products, please use confirm=True to proceed")
            return 0, 0
        
        products = self.get_all_products()
        
        if not products:
            print("✅ No products to delete")
            return 0, 0
        
        print(f"🗑️ Starting to delete {len(products)} products...")
        
        total_success = 0
        total_failed = 0
        
        # Batch deletion
        for i in range(0, len(products), self.batch_size):
            batch = products[i:i + self.batch_size]
            batch_ids = [p['id'] for p in batch]
            
            print(f"  🗂️ Deleting batch {i//self.batch_size + 1} ({len(batch_ids)} products)...")
            
            success_count, failed_count = self.delete_products_batch(batch_ids)
            total_success += success_count
            total_failed += failed_count
            
            print(f"    ✅ Success: {success_count}, ❌ Failed: {failed_count}")
        
        print(f"📊 Product deletion completed: Success {total_success}, Failed {total_failed}")
        return total_success, total_failed
    
    def delete_categories_batch(self, category_ids: List[int]) -> Tuple[int, int]:
        """Batch delete categories"""
        success_count = 0
        failed_count = 0
        
        # WooCommerce supports batch deletion of categories
        batch_data = {
            'delete': [{'id': cid, 'force': True} for cid in category_ids]  # force=True for permanent deletion
        }
        
        success, response = self._make_request('POST', 'products/categories/batch', data=batch_data)
        
        if success:
            deleted = response.get('delete', [])
            for item in deleted:
                if 'error' in item:
                    failed_count += 1
                    print(f"    ❌ Failed to delete category {item.get('id', 'unknown')}: {item['error']['message']}")
                else:
                    success_count += 1
        else:
            print(f"❌ Batch category deletion failed: {response}")
            failed_count = len(category_ids)
        
        return success_count, failed_count
    
    def delete_all_categories(self, confirm: bool = False) -> Tuple[int, int]:
        """Delete all product categories (except the default)"""
        if not confirm:
            print("⚠️ This operation will delete all categories, please use confirm=True to proceed")
            return 0, 0
        
        categories = self.get_all_categories()
        
        # Exclude the default category (usually ID 15, slug "uncategorized")
        deletable_categories = [cat for cat in categories if cat['id'] != 15 and cat['slug'] != 'uncategorized']
        
        if not deletable_categories:
            print("✅ No categories to delete")
            return 0, 0
        
        print(f"🗑️ Starting to delete {len(deletable_categories)} categories...")
        
        total_success = 0
        total_failed = 0
        
        # Batch deletion
        for i in range(0, len(deletable_categories), self.batch_size):
            batch = deletable_categories[i:i + self.batch_size]
            batch_ids = [c['id'] for c in batch]
            
            print(f"  🗂️ Deleting batch {i//self.batch_size + 1} ({len(batch_ids)} categories)...")
            
            success_count, failed_count = self.delete_categories_batch(batch_ids)
            total_success += success_count
            total_failed += failed_count
            
            print(f"    ✅ Success: {success_count}, ❌ Failed: {failed_count}")
        
        print(f"📊 Category deletion completed: Success {total_success}, Failed {total_failed}")
        return total_success, total_failed
    
    def clear_all_store_data(self, confirm: bool = False) -> Dict[str, Tuple[int, int]]:
        """Clear all store data (products and categories)"""
        if not confirm:
            print("⚠️ This operation will clear the entire store, please use confirm=True to proceed")
            return {"products": (0, 0), "categories": (0, 0)}
        
        print("🧹 Starting WooCommerce store cleanup...")
        print("=" * 60)
        
        results = {}
        
        # 1. Delete all products
        print("\n1️⃣ Deleting all products")
        results["products"] = self.delete_all_products(confirm=True)
        
        # 2. Delete all categories
        print("\n2️⃣ Deleting all categories")
        results["categories"] = self.delete_all_categories(confirm=True)
        
        print("\n" + "=" * 60)
        print("🎉 Store cleanup finished!")
        
        total_products = sum(results["products"])
        total_categories = sum(results["categories"])
        
        print(f"📊 Summary:")
        print(f"  Products: Deleted {results['products'][0]} successfully, {results['products'][1]} failed")
        print(f"  Categories: Deleted {results['categories'][0]} successfully, {results['categories'][1]} failed")
        print(f"  Total: {total_products + total_categories} items")
        
        return results
    
    def get_store_summary(self) -> Dict[str, Any]:
        """Get store summary info"""
        print("📊 Fetching store summary...")
        
        # Get product count
        success, products = self._make_request('GET', 'products', params={'per_page': 1})
        total_products = 0
        if success:
            try:
                all_products = self.get_all_products()
                total_products = len(all_products)
            except:
                total_products = 0
        
        # Get category count
        success, categories = self._make_request('GET', 'products/categories', params={'per_page': 1})
        total_categories = 0
        if success:
            try:
                all_categories = self.get_all_categories()
                total_categories = len(all_categories)
            except:
                total_categories = 0
        
        summary = {
            "total_products": total_products,
            "total_categories": total_categories,
            "store_url": self.site_url
        }
        
        print(f"  Total products: {total_products}")
        print(f"  Total categories: {total_categories}")
        
        return summary

def load_config_from_file() -> Dict[str, str]:
    """Load WooCommerce credentials from config file"""
    try:
        from token_key_session import all_token_key_session

        return {
            "site_url": all_token_key_session.woocommerce_site_url.rstrip('/'),
            "consumer_key": all_token_key_session.woocommerce_api_key,
            "consumer_secret": all_token_key_session.woocommerce_api_secret
        }
    except:
        print(f"❌ Config file not found: {config_file}")
        return {}

def main():
    """Main function"""
    print("🧹 WooCommerce Store Cleaner")
    print("=" * 50)
    
    # Try to load from config file
    config = load_config_from_file()
    
    if config and all(config.values()):
        print("✅ Loaded credentials from config file")
        site_url = config["site_url"]
        consumer_key = config["consumer_key"]
        consumer_secret = config["consumer_secret"]
    else:
        print("📝 Please enter WooCommerce credentials:")
        site_url = input("Site URL: ").strip()
        consumer_key = input("Consumer Key: ").strip()
        consumer_secret = input("Consumer Secret: ").strip()
    
    if not all([site_url, consumer_key, consumer_secret]):
        print("❌ Please provide complete credential information")
        sys.exit(1)
    
    # Create cleaner
    cleaner = WooCommerceCleaner(site_url, consumer_key, consumer_secret)
    
    # Test connection
    if not cleaner.test_connection():
        print("❌ Unable to connect to WooCommerce API")
        sys.exit(1)
    
    # Show current store status
    print("\n📊 Store status:")
    summary = cleaner.get_store_summary()
    
    if summary["total_products"] == 0 and summary["total_categories"] <= 1:
        print("✅ The store is already empty")
        return
    
    # # Confirmation
    # print(f"\n⚠️ WARNING: You are about to delete:")
    # print(f"  - {summary['total_products']} products")
    # print(f"  - {summary['total_categories']} categories")
    # print(f"  - Site: {summary['store_url']}")
    
    # confirm = input("\nConfirm store cleanup? Type 'YES' to continue: ").strip()
    
    # if confirm != "YES":
    #     print("❌ Operation cancelled")
    #     sys.exit(0)
    
    # Execute cleanup
    results = cleaner.clear_all_store_data(confirm=True)
    
    # Final check
    print("\n🔍 Verifying cleanup result...")
    final_summary = cleaner.get_store_summary()
    
    if final_summary["total_products"] == 0:
        print("✅ All products have been cleaned up")
    else:
        print(f"⚠️ There are still {final_summary['total_products']} products not deleted")
    
    if final_summary["total_categories"] <= 1:  # Keep the default category
        print("✅ All custom categories have been cleaned up")
    else:
        print(f"⚠️ There are still {final_summary['total_categories']} categories not deleted")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        sys.exit(1)
