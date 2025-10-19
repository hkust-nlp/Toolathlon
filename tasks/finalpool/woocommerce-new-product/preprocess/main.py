# #!/usr/bin/env python3
# """
# Preprocessing Script - Initialize environment for new product email task
# """

# import os
# import sys
# import shutil
# from argparse import ArgumentParser
# from pathlib import Path

# # Add project path
# current_dir = Path(__file__).parent
# task_dir = current_dir.parent
# sys.path.insert(0, str(task_dir))

# # Import email management modules
# from token_key_session import all_token_key_session
# from utils.app_specific.poste.local_email_manager import LocalEmailManager


# def clear_all_email_folders():
#     """
#     Clear all emails in INBOX, Drafts, and Sent folders.
#     """
#     # Get email config file path
#     emails_config_file = all_token_key_session.emails_config_file
#     print(f"Using email config file: {emails_config_file}")

#     # Initialize email manager
#     email_manager = LocalEmailManager(emails_config_file, verbose=True)

#     # Folders to clear (try to clear these, handle errors if not exist)
#     folders_to_clear = ['INBOX', 'Drafts', 'Sent']

#     print(f"Folders to be cleared: {folders_to_clear}")

#     for folder in folders_to_clear:
#         try:
#             print(f"Clearing folder {folder} ...")
#             email_manager.clear_all_emails(mailbox=folder)
#             print(f"✅ Folder {folder} cleared")
#         except Exception as e:
#             print(f"⚠️ Error while clearing folder {folder}: {e}")

#     print("📧 All email folders have been cleared.")


# def setup_woocommerce_test_data():
#     """Set up WooCommerce test data"""
#     print("🛒 Setting up WooCommerce test data...")
    
#     try:
#         from .setup_new_product_data import main as setup_main
#         success = setup_main()
#         if success:
#             print("✅ WooCommerce test data setup completed")
#         else:
#             print("⚠️ WooCommerce test data was only partially set up")
#         return success
#     except Exception as e:
#         print(f"❌ WooCommerce test data setup failed: {e}")
#         return False

# if __name__ == "__main__":
#     parser = ArgumentParser(description="Preprocessing script - Initialize environment for new product email task")
#     parser.add_argument("--agent_workspace", required=False, help="Path to the agent workspace")
#     parser.add_argument("--launch_time", required=False, help="Launch time (optional)")

#     args = parser.parse_args()
    
#     print("=" * 60)
#     print("📧 New Product Reservation and Discount Notification Email Task - Preprocessing")
#     print("=" * 60)

#     # Step 0: Clear email folders
#     print("=" * 60)
#     print("Step 0: Clear email folders")
#     print("=" * 60)
#     clear_all_email_folders()

#     # Step 1: Set up WooCommerce test data
#     print("\n" + "=" * 60)
#     print("Step 1: Set up WooCommerce test data")
#     print("=" * 60)
#     success = setup_woocommerce_test_data()
#     print(f"WooCommerce test data setup result: {success}")
    
#     if success:
#         print("\n🎉 Preprocessing completed! Agent workspace is ready.")
#         exit(0)
#     else:
#         print("\n⚠️ Preprocessing partially completed, please check the error messages above.")
#         exit(1)