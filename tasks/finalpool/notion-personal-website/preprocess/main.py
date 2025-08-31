import os
import sys
import requests
import json
from typing import List, Dict, Optional
from argparse import ArgumentParser

current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)
parent_dir = os.path.dirname(current_dir)
grandparent_dir = os.path.dirname(parent_dir)
sys.path.insert(0, os.path.dirname(os.path.dirname(grandparent_dir)))
print(f"Added directory to sys.path: {grandparent_dir}")

# --- Configuration ---
import configs.token_key_session as configs
NOTION_TOKEN = configs.all_token_key_session.notion_integration_key

class NotionPageResetter:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        self.base_url = "https://api.notion.com/v1"

    def _get_page_title(self, page: Dict) -> str:
        """Extract title from a page object"""
        properties = page.get('properties', {})

        for prop_name, prop_data in properties.items():
            if prop_data.get('type') == 'title':
                title_array = prop_data.get('title', [])
                if title_array:
                    return ''.join([t.get('plain_text', '') for t in title_array])

        return "Untitled"

    def find_page_by_path(self, target_path: str) -> Optional[Dict]:
        """Find page by its full path"""
        # Search for all pages
        url = f"{self.base_url}/search"
        payload = {
            "filter": {
                "value": "page",
                "property": "object"
            }
        }

        response = requests.post(url, headers=self.headers, json=payload)
        if response.status_code != 200:
            raise Exception(f"Failed to search pages: {response.status_code} - {response.text}")

        data = response.json()

        # Look for the specific page
        for page in data.get('results', []):
            title = self._get_page_title(page)
            if target_path.lower() in title.lower() or title.lower() in target_path.lower():
                print(f"Found: {target_path} == {title}")
                return {
                    'id': page['id'],
                    'title': title,
                    'url': page.get('url', '')
                }

        return None

    def get_page_blocks(self, page_id: str) -> List[Dict]:
        """Get all blocks from a page"""
        url = f"{self.base_url}/blocks/{page_id}/children"
        response = requests.get(url, headers=self.headers)

        if response.status_code != 200:
            raise Exception(f"Failed to get page blocks: {response.status_code} - {response.text}")

        return response.json().get('results', [])

    def delete_all_blocks(self, page_id: str):
        """Delete all blocks from a page"""
        blocks = self.get_page_blocks(page_id)

        for block in blocks:
            block_id = block['id']
            url = f"{self.base_url}/blocks/{block_id}"
            response = requests.delete(url, headers=self.headers)

            if response.status_code not in [200, 404]:  # 404 is OK if already deleted
                print(f"Warning: Failed to delete block {block_id}: {response.status_code}")

    def create_initial_content(self, page_id: str):
        """Create the initial template content"""
        url = f"{self.base_url}/blocks/{page_id}/children"

        blocks = [
            # Introduction heading
            {
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "📌 Introduction"}
                        }
                    ]
                }
            },
            # Introduction paragraph
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "Hi, I'm Colley Whisson, a passionate and creative professional dedicated to painting. Let me take you through my journey and expertise."}
                        }
                    ]
                }
            },
            # About Me heading
            {
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "🏷 About Me"}
                        }
                    ]
                }
            },
            # About Me content
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "👋 Hi, my name is [Your Name]!"}
                        }
                    ]
                }
            },
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "🎓 Background: [Birth, Your education, experience, or expertise]"}
                        }
                    ]
                }
            },
            # Paintings heading
            {
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "📁 Paintings"}
                        }
                    ]
                }
            },
            # Workshop heading
            {
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "📰 WorkShop"}
                        }
                    ]
                }
            },
            # Prizes heading
            {
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "📜 Prizes"}
                        }
                    ]
                }
            },
            # Exhibitions heading
            {
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "🎨 Exhibitions"}
                        }
                    ]
                }
            }
        ]

        payload = {"children": blocks}
        response = requests.patch(url, headers=self.headers, json=payload)

        if response.status_code != 200:
            raise Exception(f"Failed to create content: {response.status_code} - {response.text}")

    def reset_page_to_initial_state(self, page_path: str):
        """Reset the specified page to initial template state"""
        print(f"Searching for page: {page_path}")

        # Find the page
        page = self.find_page_by_path(page_path)
        if not page:
            raise Exception(f"Page not found: {page_path}")

        print(f"Found page: {page['title']} (ID: {page['id']})")

        # Delete all existing blocks
        print("Deleting existing content...")
        self.delete_all_blocks(page['id'])

        # Add initial template content
        print("Adding initial template content...")
        self.create_initial_content(page['id'])

        print(f"✅ Successfully reset page to initial state!")
        print(f"Page URL: {page['url']}")

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()
    try:
        resetter = NotionPageResetter(NOTION_TOKEN)

        # Reset the MCPTestPage/Colley Whisson page
        target_path = "MCPTestPage/Colley Whisson"  # or just "Colley Whisson"
        resetter.reset_page_to_initial_state(target_path)

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        exit(1)

"""initial content
# 📌 Introduction
Hi, I’m Colley Whisson, a passionate and creative professional dedicated to painting. Let me take you through my journey and expertise.
# 🏷 About Me
👋 Hi, my name is [Your Name]!
🎓 Background: [Birth, Your education, experience, or expertise]
# 📁 Paintings
# 📰 WorkShop
# 📜 Prizes
# 🎨 Exhibitions
"""
