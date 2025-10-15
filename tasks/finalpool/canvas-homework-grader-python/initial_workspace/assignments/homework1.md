# Homework 1: Valid Parentheses

**Course:** CS5123 Programming Fundamentals  
**Due Date:** 2 weeks after assignment  
**Points:** 10 points  

## Problem Description

Given a string `s` containing just the characters `'('`, `')'`, `'{'`, `'}'`, `'['` and `']'`, determine if the input string is valid.

An input string is valid if:
1. Open brackets must be closed by the same type of brackets.
2. Open brackets must be closed in the correct order.
3. Every close bracket has a corresponding open bracket of the same type.

## Examples

### Example 1:
```
Input: s = "()"
Output: true
```

### Example 2:
```
Input: s = "()[]{}"
Output: true
```

### Example 3:
```
Input: s = "(]"
Output: false
```

### Example 4:
```
Input: s = "([)]"
Output: false
```

### Example 5:
```
Input: s = "{[]}"
Output: true
```

## Constraints

- `1 <= s.length <= 10^4`
- `s` consists of parentheses only `'()[]{}'`.

## Function Signature

```python
def isValid(s: str) -> bool:
    """
    Determine if the input string has valid parentheses.
    
    Args:
        s: String containing parentheses
        
    Returns:
        bool: True if valid, False otherwise
    """
    pass
```

## Test Cases

Your solution should handle these test cases correctly:

```python
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
```

## Submission Guidelines

1. Name your file: `{firstname}_{lastname}_parentheses.py`
2. Include the test cases in your submission
3. Add comments explaining your approach
4. Submit via email with subject line including "[CS5123] Homework 1"

## Grading Criteria

- **10 points:** Solution passes all test cases and runs without errors
- **0 points:** Solution has syntax errors, runtime errors, or produces incorrect results