import requests
from typing import Dict, List, Optional, Tuple


def get_notion_workspace_pages(token):
    """Get all pages in Notion workspace"""
    url = "https://api.notion.com/v1/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    # Search all pages
    payload = {
        "filter": {
            "value": "page",
            "property": "object"
        },
        "sort": {
            "direction": "descending",
            "timestamp": "last_edited_time"
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to get workspace pages: {e}")


def find_page_by_title(token, target_title, partial_match=True):
    """Find page by title"""
    try:
        pages_data = get_notion_workspace_pages(token)
        matching_pages = []
        print(f"----- Searching for page: '{target_title}' (partial_match={partial_match}) -----")
        print(f"Found {len(pages_data.get('results', []))} total pages")

        for page in pages_data.get('results', []):
            page_title = ""

            # Get page title
            if 'properties' in page and 'title' in page['properties']:
                title_prop = page['properties']['title']
                if title_prop['type'] == 'title':
                    title_parts = title_prop['title']
                    page_title = ''.join([part.get('text', {}).get('content', '') for part in title_parts])

            # Print each page for debugging
            print(f"Checking page: '{page_title}' (ID: {page['id']})")

            # Check title match
            if partial_match:
                if target_title.lower() in page_title.lower():
                    print(f"✅ MATCH FOUND: '{page_title}'")
                    matching_pages.append({
                        'id': page['id'],
                        'title': page_title,
                        'url': page.get('url', ''),
                        'last_edited_time': page.get('last_edited_time', '')
                    })
            else:
                if target_title.lower() == page_title.lower():
                    print(f"✅ EXACT MATCH FOUND: '{page_title}'")
                    matching_pages.append({
                        'id': page['id'],
                        'title': page_title,
                        'url': page.get('url', ''),
                        'last_edited_time': page.get('last_edited_time', '')
                    })

        print(f"----- Search completed. Found {len(matching_pages)} matching pages -----")
        return matching_pages
    except Exception as e:
        raise Exception(f"Failed to find page: {e}")


def find_database_by_title(token, target_title, partial_match=True):
    """Find database by title"""
    url = "https://api.notion.com/v1/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    payload = {
        "filter": {
            "value": "database",
            "property": "object"
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        matching_databases = []
        print(f"Searching for database: '{target_title}' (partial_match={partial_match})")
        print(f"Found {len(data.get('results', []))} total databases")

        for db in data.get('results', []):
            db_title = ""

            # Get database title
            if 'title' in db:
                title_parts = db['title']
                db_title = ''.join([part.get('text', {}).get('content', '') for part in title_parts])

            print(f"Checking database: '{db_title}' (ID: {db['id']})")

            # Check title match
            if partial_match:
                if target_title.lower() in db_title.lower():
                    print(f"✅ DATABASE MATCH FOUND: '{db_title}'")
                    matching_databases.append({
                        'id': db['id'],
                        'title': db_title,
                        'url': db.get('url', ''),
                        'last_edited_time': db.get('last_edited_time', '')
                    })
            else:
                if target_title.lower() == db_title.lower():
                    print(f"✅ EXACT DATABASE MATCH FOUND: '{db_title}'")
                    matching_databases.append({
                        'id': db['id'],
                        'title': db_title,
                        'url': db.get('url', ''),
                        'last_edited_time': db.get('last_edited_time', '')
                    })

        print(f"Database search completed. Found {len(matching_databases)} matching databases")
        return matching_databases
    except Exception as e:
        raise Exception(f"Failed to find database: {e}")


def get_notion_page_blocks(page_id, token):
    """Get all block content from Notion page"""
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to get page blocks: {e}")


def get_database_details(database_id, token):
    """Get database details including title"""
    url = f"https://api.notion.com/v1/databases/{database_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to get database details: {e}")


def find_database_in_page(page_id, token, target_db_title):
    """Find database within a specific page"""
    try:
        # Get page blocks
        blocks_data = get_notion_page_blocks(page_id, token)

        print(f"Searching for '{target_db_title}' database in page blocks...")
        print(f"Found {len(blocks_data.get('results', []))} blocks in the page")

        for block in blocks_data.get('results', []):
            block_type = block.get('type', '')
            block_id = block.get('id', '')
            print(f"Checking block type: {block_type}, ID: {block_id}")

            # Check if this block is a child database
            if block_type == 'child_database':
                # Get database title
                db_title = block.get('child_database', {}).get('title', '')
                print(f"Found child database: '{db_title}'")

                if target_db_title.lower() in db_title.lower():
                    print(f"✅ Found matching database: '{db_title}' in page")
                    return {
                        'id': block_id,
                        'title': db_title,
                        'type': 'child_database'
                    }

            # Also check if block itself is a database (inline databases)
            elif block_type == 'database':
                try:
                    # Query the database to get its title
                    db_details = get_database_details(block_id, token)
                    db_title = ''.join([part.get('text', {}).get('content', '') for part in db_details.get('title', [])])
                    print(f"Found inline database: '{db_title}'")

                    if target_db_title.lower() in db_title.lower():
                        print(f"✅ Found matching inline database: '{db_title}' in page")
                        return {
                            'id': block_id,
                            'title': db_title,
                            'type': 'inline_database'
                        }
                except Exception as e:
                    print(f"Error getting database details for {block_id}: {e}")

        print(f"No '{target_db_title}' database found in this page")
        return None

    except Exception as e:
        print(f"Error searching for database in page: {e}")
        return None


def get_database_entries(database_id, token):
    """Get all entries from a database"""
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers, json={})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to get database entries: {e}")
