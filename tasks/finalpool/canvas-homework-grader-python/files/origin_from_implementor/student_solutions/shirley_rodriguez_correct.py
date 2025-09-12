def twoSum(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []

# Test the solution
if __name__ == "__main__":
    # Test case 1
    nums1 = [2, 7, 11, 15]
    target1 = 9
    result1 = twoSum(nums1, target1)
    print(f"Test 1: {result1}")
    
    # Test case 2
    nums2 = [3, 2, 4]
    target2 = 6
    result2 = twoSum(nums2, target2)
    print(f"Test 2: {result2}")
    
    print("Tests completed successfully!")