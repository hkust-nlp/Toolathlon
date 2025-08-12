from argparse import ArgumentParser
from pathlib import Path
from configs.token_key_session import all_token_key_session

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    args = parser.parse_args()

    hf_token = all_token_key_session.huggingface_token
    
    with open(Path(args.agent_workspace)/"hf_token.txt", "w") as f:
        f.write(hf_token)

    
