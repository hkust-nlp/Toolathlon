import pandas as pd
import json
path = "./"

train_df = pd.read_parquet(f'{path}/openr1.parquet')

output_path = "./openrlhf_sft/"
os.makedirs(output_path, exist_ok=True)

with open(f'{output_path}/train.jsonl', 'w') as f:
    for i in range(len(train_df)):
        if train_df.iloc[i]['target'] is not None:
            train_df.iloc[i]['target'][0]['content'] = train_df.iloc[i]['target'][0]['content'][len('<think>\n'):]
            item = {
                'prompt': train_df.iloc[i]['prompt'].tolist(),
                'target': train_df.iloc[i]['target'].tolist(),
            }
            f.write(json.dumps(item))
            f.write('\n')
