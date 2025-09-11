def isValid(s: str) -> bool:
    """
    Determine if the input string has valid parentheses.
    
    Args:
        s: String containing parentheses
        
    Returns:
        bool: True if valid, False otherwise
    """
    # Use a stack approach with list
    stack = []
    
    # Dictionary to map closing brackets to opening ones
    bracket_map = {')': '(', '}': '{', ']': '['}
    
    for char in s:
        if char in bracket_map.values():
            # Opening bracket - push to stack
            stack.append(char)
        elif char in bracket_map.keys():
            # Closing bracket - check if it matches
            if not stack or stack.pop() != bracket_map[char]:
                return False
    
    # Valid if stack is empty (all brackets matched)
    return len(stack) == 0


# Test your solution
if __name__ == "__main__":
    # Test cases
    test_cases = [
        ("()", True),
        ("()[]{}", True),
        ("(]", False),
        ("([)]", False),
        ("{[]}", True),
        ("", True),
        ("(", False),
        (")", False),
        ("((", False),
        ("))", False)
    ]
    
    for s, expected in test_cases:
        result = isValid(s)
        status = "PASS" if result == expected else "FAIL"
        print(f"Input: '{s}' -> Output: {result}, Expected: {expected} [{status}]")