#!/usr/bin/env python3
"""
Shared GitHub data fetcher for git-milestone task.
This module provides common functionality for fetching GitHub repository data
used by both preprocess and evaluation scripts.
"""

import json
import os
import sys
import requests
import time
from typing import Dict, Any, Optional

# Import GitHub token from config
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from configs.token_key_session import all_token_key_session


class GitHubDataFetcher:
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token or all_token_key_session.github_token
        self.headers = {}
        if self.github_token:
            self.headers['Authorization'] = f'token {self.github_token}'
        self.headers['Accept'] = 'application/vnd.github.v3+json'
        self.base_url = 'https://api.github.com'
        
        # Repository IDs to fetch (excluding 1000 which doesn't exist)
        self.repo_ids = [1, 1000000, 1000000000]
        
    def fetch_repo_by_id(self, repo_id: int) -> Optional[Dict[str, Any]]:
        """Fetch repository information by GitHub repo ID."""
        url = f"{self.base_url}/repositories/{repo_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 404:
                print(f"⚠️  Repository ID {repo_id} not found (404)")
                return None
            elif response.status_code == 403:
                print(f"❌ Rate limit exceeded or access forbidden for repo ID {repo_id}")
                return None
            elif response.status_code != 200:
                print(f"❌ Error fetching repo ID {repo_id}: HTTP {response.status_code}")
                return None
                
            repo_data = response.json()
            
            # Extract required fields
            extracted_data = {
                "repo_name": repo_data.get("name"),
                "owner": repo_data.get("owner", {}).get("login"),
                "star_count": repo_data.get("stargazers_count", 0),
                "fork_count": repo_data.get("forks_count", 0),
                "creation_date": repo_data.get("created_at"),
                "description": repo_data.get("description"),
                "language": repo_data.get("language"),
                "repo_url": repo_data.get("html_url")
            }
            
            print(f"✅ Successfully fetched data for repo ID {repo_id}: {extracted_data['owner']}/{extracted_data['repo_name']}")
            return extracted_data
            
        except requests.RequestException as e:
            print(f"❌ Network error fetching repo ID {repo_id}: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error fetching repo ID {repo_id}: {e}")
            return None
    
    def fetch_all_repos(self, verbose: bool = True) -> Dict[str, Any]:
        """Fetch all required repository data."""
        results = {}
        
        for repo_id in self.repo_ids:
            if verbose:
                print(f"🔍 Fetching repository ID {repo_id}...")
            repo_data = self.fetch_repo_by_id(repo_id)
            
            if repo_data:
                results[str(repo_id)] = repo_data
            else:
                if verbose:
                    print(f"⚠️  Skipping repo ID {repo_id} due to fetch failure")
            
            # Rate limiting: GitHub allows 60 requests/hour without auth, 5000 with auth
            time.sleep(0.1)  # Small delay to be polite
            
        return results
    
    def save_results(self, data: Dict[str, Any], output_path: str, verbose: bool = True) -> None:
        """Save fetched data to JSON file."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        if verbose:
            print(f"💾 Results saved to: {output_path}")


def fetch_and_save_github_data(output_path: str, github_token: Optional[str] = None, verbose: bool = True) -> Dict[str, Any]:
    """
    Convenience function to fetch GitHub data and save to file.
    
    Args:
        output_path: Path to save the JSON file
        github_token: Optional GitHub token (uses config default if None)
        verbose: Whether to print progress messages
        
    Returns:
        Dict containing the fetched repository data
    """
    fetcher = GitHubDataFetcher(github_token)
    repo_data = fetcher.fetch_all_repos(verbose=verbose)
    
    if repo_data:
        fetcher.save_results(repo_data, output_path, verbose=verbose)
        if verbose:
            print(f"📊 Successfully collected data for {len(repo_data)} repositories!")
    else:
        if verbose:
            print("❌ No repository data was successfully fetched")
    
    return repo_data