def twoSum(nums, target)
    num_map = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in num_map:
            return [num_map[complement], i]
        num_map[num] = i
    return []

# Test the solution
if __name__ == "__main__":
    # Test case 1
    nums1 = [2, 7, 11, 15]
    target1 = 9
    result1 = twoSum(nums1, target1)
    print(f"Test 1: {result1}")  # Should be [0, 1]
    
    # Test case 2
    nums2 = [3, 2, 4]
    target2 = 6
    result2 = twoSum(nums2, target2)
    print(f"Test 2: {result2}")  # Should be [1, 2]
    
    # Test case 3
    nums3 = [3, 3]
    target3 = 6
    result3 = twoSum(nums3, target3)
    print(f"Test 3: {result3}")  # Should be [0, 1]
    
    print("All tests passed!")