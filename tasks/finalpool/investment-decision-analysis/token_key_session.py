from addict import Dict
import os

# 读取动态生成的folder_id
file_path = os.path.abspath(__file__)
folder_id_file = os.path.join(os.path.dirname(file_path), "files", "folder_id.txt")

# 检查folder_id文件是否存在
if os.path.exists(folder_id_file):
    with open(folder_id_file, "r") as f:
        dynamic_folder_id = f.read().strip()


all_token_key_session = Dict( 
    # 动态生成的folder_id
    google_sheets_folder_id = dynamic_folder_id,
)