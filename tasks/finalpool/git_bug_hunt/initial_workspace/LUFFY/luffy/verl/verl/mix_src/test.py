from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained('/mnt/petrelfs/yanjianhao/hf_models/Qwen2.5-1.5B-Instruct-ds-tok')

messages = [
    {
        'role': 'system',
        'content': 'You are a helpful assistant.'
    },
    {
        'role': 'user',
        'content': 'Hello, how are you?'
    }
]

print(tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False))