#!/usr/bin/env python3
"""
Usage example for WooCommerce client functionality
"""

import sys
import os

# Add project paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, project_root)

from utils.app_specific.woocommerce.client import WooCommerceClient


def reset_store_example():
    """Store reset example"""

    # WooCommerce API configuration
    SITE_URL = "http://localhost:10003/store84"
    CONSUMER_KEY = "ck_woocommerce_token_benjhMtCdOGk"
    CONSUMER_SECRET = "cs_woocommerce_token_benjhMtCdOGk"

    # Create client
    client = WooCommerceClient(
        site_url=SITE_URL,
        consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET
    )

    print("🚨 WARNING: About to completely reset store!")
    print("⚠️  This operation will delete all data, irreversible!")

    # # Confirmation prompt
    # confirm = input("\nAre you sure you want to continue? Type 'YES' to confirm: ")

    # if confirm != 'YES':
    #     print("❌ Operation cancelled")
    #     return

    # confirm = 'YES'

    # Execute complete reset
    result = client.reset_to_empty_store(confirm=True)

    if result.get("success"):
        print("\n🎉 Store reset successful!")
        print("📋 Reset summary:")
        print(result.get("summary", ""))

        # Save reset report
        import json
        from datetime import datetime

        os.makedirs("./tmp", exist_ok=True)
        report_filename = f"./tmp/store_reset_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"📄 Detailed report saved to: {report_filename}")

    else:
        print("\n❌ Store reset failed")
        print(f"Error message: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    reset_store_example()