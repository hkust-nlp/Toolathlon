def isValid(s: str) -> bool:
    # Stack to keep track of opening brackets
    stack = []
    
    # Mapping of closing to opening brackets
    mapping = {')': '(', '}': '{', ']': '['}
    
    for char in s:
        if char in mapping:
            # Pop the top element from stack if it's not empty, otherwise assign a dummy value
            top_element = stack.pop() if stack else '#'
            
            # If the mapping doesn't match, return False
            if mapping[char] != top_element:
                return False
        else:
            # Push opening brackets onto stack
            stack.append(char)
    
    # If stack is empty, all brackets were matched
    return not stack


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