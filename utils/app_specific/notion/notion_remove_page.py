#!/usr/bin/env python3
"""
Delete child pages with specific names from a Notion page

Usage:
    python delete_notion_pages.py --url "page_url" --name "page_name_to_delete"
    
Environment Variables:
    NOTION_TOKEN: Notion API Token (required)
"""

import os
import sys
import argparse
import requests
from urllib.parse import urlparse

def get_page_id_from_url(url):
    """Extract page ID from URL"""
    path = urlparse(url).path
    page_id = path.split('-')[-1]
    if len(page_id) == 32:
        return f"{page_id[:8]}-{page_id[8:12]}-{page_id[12:16]}-{page_id[16:20]}-{page_id[20:32]}"
    return page_id

def get_child_pages(parent_id, headers):
    """Get all child pages"""
    url = f"https://api.notion.com/v1/blocks/{parent_id}/children"
    
    all_children = []
    has_more = True
    start_cursor = None
    
    while has_more:
        params = {"page_size": 100}
        if start_cursor:
            params["start_cursor"] = start_cursor
            
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error: Unable to get child pages - {response.status_code}")
            print(f"Response: {response.text}")
            return []
            
        data = response.json()
        
        if "results" in data:
            all_children.extend(data["results"])
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")
    
    return all_children

def delete_pages_by_title(parent_id, target_title, headers, dry_run=False):
    """Delete child pages with specific title (including all their content)"""
    children = get_child_pages(parent_id, headers)
    
    if not children:
        print("No child pages found")
        return 0
    
    # Find all matching pages
    pages_to_delete = []
    for child in children:
        if child.get("type") == "child_page":
            title = child.get("child_page", {}).get("title", "")
            if title == target_title:
                pages_to_delete.append((child['id'], title))
    
    if not pages_to_delete:
        print(f"No child pages found with title '{target_title}'")
        return 0
    
    # Show pages to be deleted in dry run mode
    print(f"Found {len(pages_to_delete)} matching pages:")
    for page_id, title in pages_to_delete:
        print(f"  - {title} (ID: {page_id})")
    
    if dry_run:
        print("\n[Dry run mode] No content will actually be deleted")
        return 0
    
    # Confirm deletion
    print("\n⚠️  Warning: This will permanently delete the above pages and all their sub-content!")
    confirm = input("Are you sure you want to continue? (Type 'yes' to confirm): ")
    
    if confirm.lower() != 'yes':
        print("Operation cancelled")
        return 0
    
    # Execute deletion
    deleted_count = 0
    print("\nStarting deletion...")
    
    for page_id, title in pages_to_delete:
        delete_url = f"https://api.notion.com/v1/blocks/{page_id}"
        response = requests.delete(delete_url, headers=headers)
        
        if response.status_code == 200:
            print(f"✓ Deleted: {title}")
            deleted_count += 1
        else:
            print(f"✗ Deletion failed: {title} - {response.status_code}: {response.text}")
    
    return deleted_count

def main():
    parser = argparse.ArgumentParser(
        description='Delete child pages with specific names from a Notion page',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --url "https://www.notion.so/Page-Name-xxx" --name "page_to_delete"
  %(prog)s -u "page_url" -n "page_name" --dry-run
  
Environment Variables:
  NOTION_TOKEN: Notion API Token (required)
  
Notes:
  1. You need to add the Integration to the page first
  2. Deletion is irreversible and will delete the page and all its sub-content
        """
    )
    
    parser.add_argument(
        '-u', '--url',
        required=True,
        help='Notion page URL'
    )
    
    parser.add_argument(
        '-n', '--name',
        required=True,
        help='Name of the child page to delete'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode, only show what would be deleted without actually deleting'
    )
    
    parser.add_argument(
        '--token',
        help='Notion API Token (or use environment variable NOTION_TOKEN)'
    )
    
    parser.add_argument(
        '--no-confirm',
        action='store_true',
        help='Skip confirmation prompt (dangerous!)'
    )
    
    args = parser.parse_args()
    
    # Get Token
    token = args.token or os.environ.get('NOTION_TOKEN')
    if not token:
        print("Error: Notion API Token is required")
        print("Please use --token parameter or set environment variable NOTION_TOKEN")
        sys.exit(1)
    
    # Set request headers
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    # Extract page ID
    try:
        page_id = get_page_id_from_url(args.url)
        print(f"Page ID: {page_id}")
    except Exception as e:
        print(f"Error: Unable to parse URL - {e}")
        sys.exit(1)
    
    print(f"Searching for child pages with title '{args.name}'...")
    print("-" * 50)
    
    # If no-confirm is set, temporarily modify delete function
    if args.no_confirm and not args.dry_run:
        # Monkey patch to skip confirmation
        import builtins
        original_input = builtins.input
        builtins.input = lambda _: 'yes'
        
        try:
            count = delete_pages_by_title(page_id, args.name, headers, args.dry_run)
        finally:
            builtins.input = original_input
    else:
        count = delete_pages_by_title(page_id, args.name, headers, args.dry_run)
    
    print("-" * 50)
    if not args.dry_run:
        print(f"Complete! Deleted {count} pages")

if __name__ == "__main__":
    main()