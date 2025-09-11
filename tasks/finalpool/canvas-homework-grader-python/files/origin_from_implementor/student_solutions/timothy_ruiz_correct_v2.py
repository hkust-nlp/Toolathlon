def twoSum(nums, target):
    # Use hash map for O(n) time complexity
    num_to_index = {}
    
    for current_index, current_num in enumerate(nums):
        # Calculate what number we need to find
        complement = target - current_num
        
        # Check if we've seen the complement before
        if complement in num_to_index:
            # Found the pair! Return indices
            return [num_to_index[complement], current_index]
        
        # Store current number and its index for future lookups
        num_to_index[current_num] = current_index
    
    # This should never happen given problem constraints
    return []

# Comprehensive test suite
if __name__ == "__main__":
    print("Running comprehensive tests for Two Sum solution...")
    
    # Test case 1: Basic example
    nums1 = [2, 7, 11, 15]
    target1 = 9
    result1 = twoSum(nums1, target1)
    print(f"Test 1: nums={nums1}, target={target1}")
    print(f"Result: {result1}")  # Should be [0, 1]
    assert result1 == [0, 1], f"Expected [0, 1], got {result1}"
    
    # Test case 2: Different order
    nums2 = [3, 2, 4]
    target2 = 6
    result2 = twoSum(nums2, target2)
    print(f"Test 2: nums={nums2}, target={target2}")
    print(f"Result: {result2}")  # Should be [1, 2]
    assert result2 == [1, 2], f"Expected [1, 2], got {result2}"
    
    # Test case 3: Same values
    nums3 = [3, 3]
    target3 = 6
    result3 = twoSum(nums3, target3)
    print(f"Test 3: nums={nums3}, target={target3}")
    print(f"Result: {result3}")  # Should be [0, 1]
    assert result3 == [0, 1], f"Expected [0, 1], got {result3}"
    
    print("All tests passed successfully! ✅")
    print("Time complexity: O(n)")
    print("Space complexity: O(n)")