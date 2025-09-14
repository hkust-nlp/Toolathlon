from datasets import load_dataset
import pandas as pd

dataset = load_dataset("Elliott/Openr1-Math-48k-Complement", split="train")

print(dataset[0])

ret_dict = []
for item in dataset:
    ret_dict.append(item)

train_df = pd.DataFrame(ret_dict)
train_df.to_parquet("../data/openr1.complement.parquet")