import numpy as np

def calculate_mean_std_pass(data):
    return np.mean(data), np.std(data)

if __name__ == "__main__":
    data = [1, 2, 3, 4, 5]
    print(calculate_mean_std_pass(data))