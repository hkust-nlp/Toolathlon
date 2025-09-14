from datasets import load_dataset
import pandas as pd
import logging

# Setup logging for better monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dataset = load_dataset("Elliott/Openr1-Math-46k-8192", split="train")

logger.info(f"Loaded dataset with {len(dataset)} samples")
print(dataset[0])

ret_dict = []
for i, item in enumerate(dataset):
    if i % 10000 == 0:
        logger.info(f"Processed {i} samples")
    ret_dict.append(item)

train_df = pd.DataFrame(ret_dict)
logger.info(f"Converting {len(train_df)} samples to parquet format")
train_df.to_parquet("../data/openr1.parquet")