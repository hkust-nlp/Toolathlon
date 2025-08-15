我正在尝试使用verl框架在自己训练的语言模型上复现DeepSeek-R1的"aha-moment"，为此我需要你帮我将hugging face上下载数目最多的DeepScaleR数据集下载到本地，并将其转化为parquet格式以便我后续使用，命名为verl_deepscaler.parquet。

格式要求如下：
{
    "data_source": "DeepScaleR",
    "prompt": [{
        "role": "user",
        "content": question
    }],
    "ability": "math",
    "reward_model": {
        "style": "rule",
        "ground_truth": answer
    },
    "extra_info": {
        'index': idx,
        'solution': solution,
    }
}