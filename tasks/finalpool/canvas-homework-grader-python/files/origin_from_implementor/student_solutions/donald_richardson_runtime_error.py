def twoSum(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums) + 1):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []

# Test the solution
if __name__ == "__main__":
    nums = [2, 7, 11, 15]
    target = 9
    result = twoSum(nums, target)
    print(f"Result: {result}")
    print("Tests completed!")