import non_existent_module

def twoSum(nums, target):
    result = non_existent_module.solve_two_sum(nums, target)
    return result

# Test the solution
if __name__ == "__main__":
    nums = [2, 7, 11, 15]
    target = 9
    result = twoSum(nums, target)
    print(f"Result: {result}")
    print("Tests completed!")