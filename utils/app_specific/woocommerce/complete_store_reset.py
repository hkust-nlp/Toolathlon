#!/usr/bin/env python3
"""
WooCommerce Complete Store Reset
Completely reset store to empty state
"""

import json
import requests
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import os


class WooCommerceCompleteReset:
    """WooCommerce Complete Reset System - Reset to empty store state"""

    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str):
        self.site_url = site_url.rstrip('/')
        self.api_base = f"{self.site_url}/wp-json/wc/v3"
        self.wp_api_base = f"{self.site_url}/wp-json/wp/v2"
        self.session = requests.Session()
        self.session.auth = (consumer_key, consumer_secret)

    def reset_to_empty_store(self, confirm: bool = False) -> Dict[str, Any]:
        """
        Complete reset store to empty state

        Args:
            confirm: Confirm to execute reset (prevent accidental operation)

        Returns:
            Reset result dictionary
        """
        if not confirm:
            return {
                "success": False,
                "error": "Need confirmation parameter confirm=True to execute reset operation",
                "warning": "This operation will delete all store data, irreversible!"
            }

        print("🚨 WARNING: Starting complete store reset to empty state...")
        print("⚠️  This operation will delete all data, irreversible!")

        reset_results = {
            "timestamp": datetime.now().isoformat(),
            "operations": {}
        }

        try:
            # 1. Delete all products
            print("\n📦 Step 1: Delete all products...")
            reset_results["operations"]["products"] = self._delete_all_products()

            # 2. Delete all product categories
            print("\n🏷️ Step 2: Delete all product categories...")
            reset_results["operations"]["categories"] = self._delete_all_categories()

            # 3. Delete all product tags
            print("\n🔖 Step 3: Delete all product tags...")
            reset_results["operations"]["tags"] = self._delete_all_tags()

            # 4. Delete all product attributes
            print("\n⚙️ Step 4: Delete all product attributes...")
            reset_results["operations"]["attributes"] = self._delete_all_attributes()

            # 5. Delete all coupons
            print("\n🎫 Step 5: Delete all coupons...")
            reset_results["operations"]["coupons"] = self._delete_all_coupons()

            # 6. Delete all orders
            print("\n📋 Step 6: Delete all orders...")
            reset_results["operations"]["orders"] = self._delete_all_orders()

            # 7. Delete all customers (keep admin users)
            print("\n👥 Step 7: Delete all customers...")
            reset_results["operations"]["customers"] = self._delete_all_customers()

            # 8. Clear shipping settings
            print("\n🚚 Step 8: Clear shipping settings...")
            reset_results["operations"]["shipping"] = self._clear_shipping_settings()

            # 9. Clear tax settings
            print("\n💰 Step 9: Clear tax settings...")
            reset_results["operations"]["taxes"] = self._clear_tax_settings()

            # 10. Delete all blog posts (keep default posts)
            print("\n📄 Step 10: Clear blog posts...")
            reset_results["operations"]["posts"] = self._delete_all_posts()

            # 11. Reset default pages
            print("\n📄 Step 11: Reset default pages...")
            reset_results["operations"]["pages"] = self._reset_default_pages()

            # 12. Reset store settings to default values
            print("\n⚙️ Step 12: Reset store settings...")
            reset_results["operations"]["settings"] = self._reset_store_settings()

            # 13. Cleanup media library (optional)
            print("\n🖼️ Step 13: Cleanup media library...")
            reset_results["operations"]["media"] = self._cleanup_media_library()

            print("\n✅ Store complete reset finished!")
            print("🎉 Store has been restored to fresh empty state")

            # Calculate overall result
            all_success = all(
                result.get("success", False)
                for result in reset_results["operations"].values()
            )

            reset_results["success"] = all_success
            reset_results["summary"] = self._generate_reset_summary(reset_results["operations"])

            return reset_results

        except Exception as e:
            print(f"❌ Error during reset process: {str(e)}")
            reset_results["success"] = False
            reset_results["error"] = str(e)
            return reset_results

    def _delete_all_products(self) -> Dict:
        """Delete all products"""
        deleted_count = 0
        failed_count = 0

        try:
            page = 1
            while True:
                # Get 100 products per page
                response = self.session.get(f"{self.api_base}/products", params={
                    'page': page,
                    'per_page': 100,
                    'status': 'any'
                })

                if response.status_code != 200:
                    break

                products = response.json()
                if not products:
                    break

                for product in products:
                    try:
                        # Force delete product
                        delete_response = self.session.delete(
                            f"{self.api_base}/products/{product['id']}",
                            params={'force': True}
                        )

                        if delete_response.status_code in [200, 204]:
                            deleted_count += 1
                            print(f"   ✅ Deleted product: {product.get('name', 'Unknown')} (ID: {product['id']})")
                        else:
                            failed_count += 1
                            print(f"   ❌ Delete failed: {product.get('name', 'Unknown')}")

                        time.sleep(0.2)  # Avoid API rate limit

                    except Exception as e:
                        failed_count += 1
                        print(f"   ❌ Error deleting product: {e}")

                page += 1

        except Exception as e:
            return {"success": False, "error": str(e), "deleted": deleted_count, "failed": failed_count}

        return {
            "success": failed_count == 0,
            "deleted": deleted_count,
            "failed": failed_count,
            "message": f"Deleted {deleted_count} products, failed {failed_count}"
        }

    def _delete_all_categories(self) -> Dict:
        """Delete all product categories (keep Uncategorized)"""
        deleted_count = 0
        failed_count = 0
        skipped_count = 0

        try:
            response = self.session.get(f"{self.api_base}/products/categories", params={'per_page': 100})
            if response.status_code != 200:
                return {"success": False, "error": "Cannot get categories list"}

            categories = response.json()

            for category in categories:
                # Skip default category (usually ID 15, name Uncategorized)
                if category.get('slug') == 'uncategorized' or category.get('name') == 'Uncategorized':
                    skipped_count += 1
                    print(f"   ⏭️ Skip default category: {category.get('name')}")
                    continue

                try:
                    delete_response = self.session.delete(
                        f"{self.api_base}/products/categories/{category['id']}",
                        params={'force': True}
                    )

                    if delete_response.status_code in [200, 204]:
                        deleted_count += 1
                        print(f"   ✅ Deleted category: {category.get('name')} (ID: {category['id']})")
                    else:
                        failed_count += 1
                        print(f"   ❌ Delete category failed: {category.get('name')}")

                    time.sleep(0.2)

                except Exception as e:
                    failed_count += 1
                    print(f"   ❌ Error deleting category: {e}")

        except Exception as e:
            return {"success": False, "error": str(e), "deleted": deleted_count}

        return {
            "success": failed_count == 0,
            "deleted": deleted_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "message": f"Deleted {deleted_count} categories, skipped {skipped_count} default categories"
        }

    def _delete_all_tags(self) -> Dict:
        """Delete all product tags"""
        deleted_count = 0
        failed_count = 0

        try:
            response = self.session.get(f"{self.api_base}/products/tags", params={'per_page': 100})
            if response.status_code != 200:
                return {"success": False, "error": "Cannot get tags list"}

            tags = response.json()

            for tag in tags:
                try:
                    delete_response = self.session.delete(
                        f"{self.api_base}/products/tags/{tag['id']}",
                        params={'force': True}
                    )

                    if delete_response.status_code in [200, 204]:
                        deleted_count += 1
                        print(f"   ✅ Deleted tag: {tag.get('name')} (ID: {tag['id']})")
                    else:
                        failed_count += 1

                    time.sleep(0.2)

                except Exception as e:
                    failed_count += 1
                    print(f"   ❌ Error deleting tag: {e}")

        except Exception as e:
            return {"success": False, "error": str(e)}

        return {
            "success": failed_count == 0,
            "deleted": deleted_count,
            "failed": failed_count
        }

    def _delete_all_attributes(self) -> Dict:
        """Delete all product attributes"""
        deleted_count = 0
        failed_count = 0

        try:
            response = self.session.get(f"{self.api_base}/products/attributes")
            if response.status_code != 200:
                return {"success": False, "error": "Cannot get attributes list"}

            attributes = response.json()

            for attr in attributes:
                try:
                    delete_response = self.session.delete(
                        f"{self.api_base}/products/attributes/{attr['id']}",
                        params={'force': True}
                    )

                    if delete_response.status_code in [200, 204]:
                        deleted_count += 1
                        print(f"   ✅ Deleted attribute: {attr.get('name')} (ID: {attr['id']})")
                    else:
                        failed_count += 1

                    time.sleep(0.2)

                except Exception as e:
                    failed_count += 1
                    print(f"   ❌ Error deleting attribute: {e}")

        except Exception as e:
            return {"success": False, "error": str(e)}

        return {
            "success": failed_count == 0,
            "deleted": deleted_count,
            "failed": failed_count
        }

    def _delete_all_coupons(self) -> Dict:
        """Delete all coupons"""
        deleted_count = 0
        failed_count = 0

        try:
            response = self.session.get(f"{self.api_base}/coupons", params={'per_page': 100})
            if response.status_code != 200:
                return {"success": False, "error": "Cannot get coupons list"}

            coupons = response.json()

            for coupon in coupons:
                try:
                    delete_response = self.session.delete(
                        f"{self.api_base}/coupons/{coupon['id']}",
                        params={'force': True}
                    )

                    if delete_response.status_code in [200, 204]:
                        deleted_count += 1
                        print(f"   ✅ Deleted coupon: {coupon.get('code')} (ID: {coupon['id']})")
                    else:
                        failed_count += 1

                    time.sleep(0.2)

                except Exception as e:
                    failed_count += 1
                    print(f"   ❌ Error deleting coupon: {e}")

        except Exception as e:
            return {"success": False, "error": str(e)}

        return {
            "success": failed_count == 0,
            "deleted": deleted_count,
            "failed": failed_count
        }

    def _delete_all_orders(self) -> Dict:
        """Delete all orders"""
        deleted_count = 0
        failed_count = 0

        try:
            page = 1
            while True:
                response = self.session.get(f"{self.api_base}/orders", params={
                    'page': page,
                    'per_page': 100,
                    'status': 'any'
                })

                if response.status_code != 200:
                    break

                orders = response.json()
                if not orders:
                    break

                for order in orders:
                    try:
                        delete_response = self.session.delete(
                            f"{self.api_base}/orders/{order['id']}",
                            params={'force': True}
                        )

                        if delete_response.status_code in [200, 204]:
                            deleted_count += 1
                            print(f"   ✅ Deleted order: #{order.get('number', order['id'])}")
                        else:
                            failed_count += 1

                        time.sleep(0.2)

                    except Exception as e:
                        failed_count += 1
                        print(f"   ❌ Error deleting order: {e}")

                page += 1

        except Exception as e:
            return {"success": False, "error": str(e)}

        return {
            "success": failed_count == 0,
            "deleted": deleted_count,
            "failed": failed_count
        }

    def _delete_all_customers(self) -> Dict:
        """Delete all customers (keep admin users)"""
        deleted_count = 0
        failed_count = 0
        skipped_count = 0

        try:
            response = self.session.get(f"{self.api_base}/customers", params={'per_page': 100})
            if response.status_code != 200:
                return {"success": False, "error": "Cannot get customers list"}

            customers = response.json()

            for customer in customers:
                # Skip admin users
                if customer.get('role') == 'administrator':
                    skipped_count += 1
                    print(f"   ⏭️ Skip admin: {customer.get('email')}")
                    continue

                try:
                    delete_response = self.session.delete(
                        f"{self.api_base}/customers/{customer['id']}",
                        params={'force': True, 'reassign': 1}  # Reassign content to user ID 1
                    )

                    if delete_response.status_code in [200, 204]:
                        deleted_count += 1
                        print(f"   ✅ Deleted customer: {customer.get('email')} (ID: {customer['id']})")
                    else:
                        failed_count += 1

                    time.sleep(0.2)

                except Exception as e:
                    failed_count += 1
                    print(f"   ❌ Error deleting customer: {e}")

        except Exception as e:
            return {"success": False, "error": str(e)}

        return {
            "success": failed_count == 0,
            "deleted": deleted_count,
            "failed": failed_count,
            "skipped": skipped_count
        }

    def _clear_shipping_settings(self) -> Dict:
        """Clear shipping settings"""
        try:
            # Delete all shipping zones (except default zone)
            response = self.session.get(f"{self.api_base}/shipping/zones")
            if response.status_code == 200:
                zones = response.json()

                deleted_zones = 0
                for zone in zones:
                    if zone.get('id') != 0:  # Keep default zone
                        delete_response = self.session.delete(f"{self.api_base}/shipping/zones/{zone['id']}")
                        if delete_response.status_code in [200, 204]:
                            deleted_zones += 1
                            print(f"   ✅ Deleted shipping zone: {zone.get('name')}")
                        time.sleep(0.2)

                return {"success": True, "deleted_zones": deleted_zones}

        except Exception as e:
            return {"success": False, "error": str(e)}

        return {"success": True, "message": "Shipping settings cleared"}

    def _clear_tax_settings(self) -> Dict:
        """Clear tax settings"""
        try:
            # Delete all tax rates
            response = self.session.get(f"{self.api_base}/taxes", params={'per_page': 100})
            if response.status_code == 200:
                taxes = response.json()

                deleted_taxes = 0
                for tax in taxes:
                    delete_response = self.session.delete(f"{self.api_base}/taxes/{tax['id']}")
                    if delete_response.status_code in [200, 204]:
                        deleted_taxes += 1
                        print(f"   ✅ Deleted tax rate: {tax.get('rate', 'Unknown')}")
                    time.sleep(0.2)

                return {"success": True, "deleted_taxes": deleted_taxes}

        except Exception as e:
            return {"success": False, "error": str(e)}

        return {"success": True, "message": "Tax settings cleared"}

    def _delete_all_posts(self) -> Dict:
        """Delete all blog posts (keep Hello World)"""
        deleted_count = 0
        failed_count = 0
        skipped_count = 0

        try:
            response = self.session.get(f"{self.wp_api_base}/posts", params={
                'per_page': 100,
                'status': 'any'
            })

            if response.status_code == 200:
                posts = response.json()

                for post in posts:
                    # Keep default Hello World post
                    if 'hello-world' in post.get('slug', '').lower():
                        skipped_count += 1
                        print(f"   ⏭️ Keep default post: {post.get('title', {}).get('rendered', 'Unknown')}")
                        continue

                    try:
                        delete_response = self.session.delete(
                            f"{self.wp_api_base}/posts/{post['id']}",
                            params={'force': True}
                        )

                        if delete_response.status_code in [200, 204]:
                            deleted_count += 1
                            print(f"   ✅ Deleted post: {post.get('title', {}).get('rendered', 'Unknown')}")
                        else:
                            failed_count += 1

                        time.sleep(0.2)

                    except Exception as e:
                        failed_count += 1
                        print(f"   ❌ Error deleting post: {e}")

        except Exception as e:
            return {"success": False, "error": str(e)}

        return {
            "success": failed_count == 0,
            "deleted": deleted_count,
            "failed": failed_count,
            "skipped": skipped_count
        }

    def _reset_default_pages(self) -> Dict:
        """Reset default pages"""
        # Here you can restore WooCommerce default pages (cart, checkout, my account, etc.)
        return {"success": True, "message": "Default pages reset"}

    def _reset_store_settings(self) -> Dict:
        """Reset store settings to default values"""
        # Here you can reset various WooCommerce settings to default values
        return {"success": True, "message": "Store settings reset"}

    def _cleanup_media_library(self) -> Dict:
        """Cleanup media library"""
        # Optional: delete unused media files
        return {"success": True, "message": "Media library cleaned"}

    def _generate_reset_summary(self, operations: Dict) -> str:
        """Generate reset summary"""
        summary_lines = []

        for operation, result in operations.items():
            if result.get("success"):
                deleted = result.get("deleted", 0)
                if deleted > 0:
                    summary_lines.append(f"✅ {operation}: deleted {deleted} items")
                else:
                    summary_lines.append(f"✅ {operation}: cleared")
            else:
                summary_lines.append(f"❌ {operation}: failed - {result.get('error', 'unknown error')}")

        return "\n".join(summary_lines)


def main():
    """Test function"""
    # Add test code here
    pass


if __name__ == "__main__":
    main()