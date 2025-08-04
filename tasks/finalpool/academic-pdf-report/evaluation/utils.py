#!/usr/bin/env python3
"""
Utility functions for evaluation tasks
"""

import re
from difflib import SequenceMatcher


def normalize_name(name):
    """Normalize a person's name for comparison (assumes full names without titles)"""
    # remove punctuation and whitespace and lowercase
    return re.sub(r'[^\w]', '', name).lower().strip()


def compare_names(name1, name2, similarity_threshold=1.0):
    """
    Strict comparison of two full person names
    
    Args:
        name1, name2: Full names to compare (assumed no titles/initials)
        similarity_threshold: Minimum similarity score (0-1) for match
    
    Returns:
        bool: True if names are sufficiently similar
    """
    if not name1 or not name2:
        return False
    
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)
    
    if not norm1 or not norm2:
        return False
    
    # Exact match after normalization
    if norm1 == norm2:
        return True
    
    # Calculate overall similarity using SequenceMatcher
    similarity = SequenceMatcher(None, norm1, norm2).ratio()
    
    return similarity >= similarity_threshold


def normalize_affiliation(affiliation):
    """Normalize affiliation text for comparison"""
    if not affiliation or affiliation is None or str(affiliation).strip() == "" or str(affiliation).lower() == "nan":
        return ""
    
    # Convert to string and normalize
    affiliation = str(affiliation).strip()
    # remove punctuation and whitespace and lowercase
    return re.sub(r'[^\w]', '', affiliation).lower().strip()


def check_affiliation_requirements(actual_affiliation, affiliation_requirements):
    """
    Check if affiliation meets should_contain and should_not_contain requirements
    
    Args:
        actual_affiliation: The affiliation text from Excel
        affiliation_requirements: Dict with "should_contain" and "should_not_contain" lists
    
    Returns:
        tuple: (is_valid, details_message)
    """
    if not actual_affiliation or str(actual_affiliation).strip() == "":
        return False, "Affiliation not filled"
    
    normalized_actual = normalize_affiliation(actual_affiliation)
    
    # Check should_contain requirements
    should_contain = affiliation_requirements.get("should_contain", [])
    should_not_contain = affiliation_requirements.get("should_not_contain", [])
    
    # All should_contain items must be present
    missing_required = []
    for required_item in should_contain:
        if required_item.strip():  # Skip empty strings
            normalized_required = normalize_affiliation(required_item)
            if normalized_required not in normalized_actual:
                missing_required.append(required_item)
    
    # None of should_not_contain items should be present
    found_forbidden = []
    for forbidden_item in should_not_contain:
        if forbidden_item.strip():  # Skip empty strings
            normalized_forbidden = normalize_affiliation(forbidden_item)
            if normalized_forbidden in normalized_actual:
                found_forbidden.append(forbidden_item)
    
    # Determine result
    if missing_required and found_forbidden:
        return False, f"Missing required: {missing_required}, Found forbidden: {found_forbidden}"
    elif missing_required:
        return False, f"Missing required: {missing_required}"
    elif found_forbidden:
        return False, f"Found forbidden: {found_forbidden}"
    else:
        return True, "Affiliation requirements met"


def compare_titles(title1, title2, similarity_threshold=1.0):
    """
    Compare academic paper titles with high similarity threshold
    
    Args:
        title1, title2: Paper titles to compare
        similarity_threshold: Minimum similarity score (0-1) for match
    
    Returns:
        bool: True if titles are sufficiently similar
    """
    if not title1 or not title2:
        return False
    
    # Normalize titles (same as names but for titles)
    norm1 = normalize_name(title1)  # Reuse normalize_name function
    norm2 = normalize_name(title2)
    
    if not norm1 or not norm2:
        return False
    
    # Exact match after normalization
    if norm1 == norm2:
        return True
    
    # Calculate overall similarity using SequenceMatcher
    similarity = SequenceMatcher(None, norm1, norm2).ratio()
    
    return similarity >= similarity_threshold


# Example usage and test cases
if __name__ == "__main__":
    test_cases = [
        ("John K Smith", "John K. Smith", True),
        ("Mary Jane Watson", "Mary Jane Watson", True),
        ("Robert Johnson", "Robert Johnson", True),
        ("Li Wei", "Li Wei", True),
        ("John Smith", "John Smyth", False),  # Minor spelling variation
        ("Maria Garcia", "Maria Garcia", True),
        ("John Smith", "Jane Smith", False),  # Different first name
        ("John Smith", "John Jones", False),  # Different last name
        ("", "John Smith", False),  # Empty name
        ("J", "John Smith", False),  # Too short
        ("Alexander Thompson", "Alexander Thomson", False),  # Minor spelling difference
        ("Catherine Williams", "Katherine Williams", False),  # Different first name spelling
    ]
    
    print("Testing simplified name comparison function:")
    for name1, name2, expected in test_cases:
        result = compare_names(name1, name2)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{name1}' vs '{name2}' -> {result} (expected {expected})")