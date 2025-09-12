def twoSum(nums, target):
    num_map = {}
    for i, num in enumerate(nums)
        complement = target - num
        if complement in num_map:
            return [num_map[complement], i]
        num_map[num] = i
    return []

# Test the solution
if __name__ == "__main__":
    nums = [2, 7, 11, 15]
    target = 9
    result = twoSum(nums, target)
    print(f"Result: {result}")
    print("Tests completed!")