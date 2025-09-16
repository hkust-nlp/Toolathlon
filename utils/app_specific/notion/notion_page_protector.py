#!/usr/bin/env python3
"""
Notion Page Protection Module
==============================

This module provides protection mechanisms to prevent accidental deletion or
modification of critical parent pages in Notion operations.
"""

from typing import Optional, Set, Tuple
import sys
import os
# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from configs.token_key_session import all_token_key_session


class NotionPageProtector:
    """Protects critical Notion pages from accidental operations."""

    def __init__(self):
        """Initialize protector with URLs from config."""
        # Get URLs from config
        self.source_page_url = all_token_key_session.source_notion_page_url
        self.eval_page_url = all_token_key_session.eval_notion_page_url

        # Extract page IDs from URLs
        self.source_page_id = self.extract_page_id_from_url(self.source_page_url)
        self.eval_page_id = self.extract_page_id_from_url(self.eval_page_url)

        # Protected page IDs and their expected titles
        self.PROTECTED_PAGES = {
            self.source_page_id: "Notion Source Page",
            self.eval_page_id: "Notion Eval Page",
        }

        # Protected page URLs (with various formats)
        self.PROTECTED_URLS = self._generate_protected_urls()

    def _generate_protected_urls(self) -> Set[str]:
        """Generate all variations of protected URLs."""
        urls = set()
        for url in [self.source_page_url, self.eval_page_url]:
            if url:
                urls.add(url)
                # Add without https://
                urls.add(url.replace("https://", ""))
                # Add without www
                urls.add(url.replace("https://www.", "https://"))
                urls.add(url.replace("www.", ""))
                # Add just the notion.so part
                if "notion.so" in url:
                    urls.add(url.split("//")[-1])
        return urls

    @staticmethod
    def extract_page_id_from_url(url: str) -> str:
        """Extract page ID from a Notion URL."""
        # Remove query parameters and fragments
        slug = url.split("?")[0].split("#")[0].rstrip("/").split("/")[-1]

        # Extract alphanumeric characters
        compact = "".join(c for c in slug if c.isalnum())

        if len(compact) < 32:
            return ""

        # Take last 32 characters and format as UUID
        compact = compact[-32:]
        return f"{compact[:8]}-{compact[8:12]}-{compact[12:16]}-{compact[16:20]}-{compact[20:]}"

    def is_protected_page_id(self, page_id: str) -> bool:
        """Check if a page ID is protected."""
        return page_id in self.PROTECTED_PAGES

    def is_protected_url(self, url: str) -> bool:
        """Check if a URL refers to a protected page."""
        # Check direct URL match
        for protected_url in self.PROTECTED_URLS:
            if protected_url in url:
                return True

        # Check by extracted page ID
        page_id = self.extract_page_id_from_url(url)
        return self.is_protected_page_id(page_id)

    def get_expected_title(self, page_id: str) -> Optional[str]:
        """Get the expected title for a protected page."""
        return self.PROTECTED_PAGES.get(page_id)

    def validate_rename_operation(self, page_id: str, current_title: str, new_title: str) -> Tuple[bool, str]:
        """
        Validate a rename operation on a page.

        Args:
            page_id: The ID of the page being renamed
            current_title: The current title of the page
            new_title: The new title to set

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.is_protected_page_id(page_id):
            # Not a protected page, allow rename
            return True, ""

        expected_title = self.get_expected_title(page_id)

        # Check if current title matches expected (if it doesn't, page might already be corrupted)
        if current_title != expected_title:
            return False, (
                f"CRITICAL: Protected page {page_id} has unexpected title!\n"
                f"Expected: '{expected_title}'\n"
                f"Current: '{current_title}'\n"
                f"This page should not be renamed!"
            )

        # Don't allow renaming protected pages
        if new_title != expected_title:
            return False, (
                f"CRITICAL: Cannot rename protected page!\n"
                f"Page ID: {page_id}\n"
                f"Expected title: '{expected_title}'\n"
                f"Attempted new title: '{new_title}'\n"
                f"This operation is blocked to prevent corruption of parent pages."
            )

        return True, ""

    def validate_delete_operation(self, page_id: str, page_title: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validate a delete operation on a page.

        Args:
            page_id: The ID of the page being deleted
            page_title: Optional title of the page

        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.is_protected_page_id(page_id):
            expected_title = self.get_expected_title(page_id)
            return False, (
                f"CRITICAL: Cannot delete protected page!\n"
                f"Page ID: {page_id}\n"
                f"Page title: '{page_title or expected_title}'\n"
                f"This is a protected parent page and must not be deleted!"
            )

        return True, ""

    def validate_move_operation(self, page_id: str, source_parent_id: str) -> Tuple[bool, str]:
        """
        Validate a move operation on a page.

        Args:
            page_id: The ID of the page being moved
            source_parent_id: The ID of the current parent
            target_parent_id: The ID of the target parent

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Don't allow moving protected pages
        if self.is_protected_page_id(page_id):
            return False, (
                f"CRITICAL: Cannot move protected page!\n"
                f"Page ID: {page_id}\n"
                f"This is a protected parent page and must not be moved!"
            )

        # Warn if moving away from a protected parent (might be unintentional)
        if self.is_protected_page_id(source_parent_id):
            expected_title = self.get_expected_title(source_parent_id)
            print(f"WARNING: Moving page away from protected parent '{expected_title}'")

        return True, ""

    def validate_url_operation(self, url: str, operation: str) -> Tuple[bool, str]:
        """
        Validate an operation on a URL.

        Args:
            url: The URL being operated on
            operation: The operation being performed (delete, rename, move)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.is_protected_url(url):
            page_id = self.extract_page_id_from_url(url)
            expected_title = self.get_expected_title(page_id) if page_id else "Protected Page"
            return False, (
                f"CRITICAL: Cannot {operation} protected page!\n"
                f"URL: {url}\n"
                f"Page: '{expected_title}'\n"
                f"This is a protected parent page!"
            )

        return True, ""

    def verify_page_integrity(self, page_id: str, current_title: str) -> Tuple[bool, str]:
        """
        Verify that a protected page has the expected title.

        Args:
            page_id: The page ID to verify
            current_title: The current title of the page

        Returns:
            Tuple of (is_valid, warning_message)
        """
        if not self.is_protected_page_id(page_id):
            return True, ""

        expected_title = self.get_expected_title(page_id)
        if current_title != expected_title:
            return False, (
                f"WARNING: Protected page integrity check failed!\n"
                f"Page ID: {page_id}\n"
                f"Expected title: '{expected_title}'\n"
                f"Current title: '{current_title}'\n"
                f"The page may have been corrupted in a previous operation."
            )

        return True, ""