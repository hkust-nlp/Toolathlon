import os
import re

base_path = "."
files = os.listdir(base_path)
hw3_os_files = [f for f in files if re.search(r"OperatingSystems|OS|OS-", f) and re.search(r"3|Assignment3|HW3", f)]
print(hw3_os_files)