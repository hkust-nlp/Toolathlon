from addict import Dict
import os

# 读取动态生成的folder_id
file_path = os.path.abspath(__file__)
folder_id_file = os.path.join(os.path.dirname(file_path), "files", "folder_id.txt")

# 检查folder_id文件是否存在
if os.path.exists(folder_id_file):
    with open(folder_id_file, "r") as f:
        dynamic_folder_id = f.read().strip()
else:
    # 如果文件不存在，使用默认的folder_id (向后兼容)
    dynamic_folder_id = "1Zy_Hczc1kY6HoaMXW52lJbl9w8ffn31R"
    print(f"警告：folder_id.txt 文件不存在，使用默认folder_id: {dynamic_folder_id}")

all_token_key_session = Dict( 
    google_cloud_console_api_key = "AIzaSyD8Q5ZPqCDZIgjOwBc9QtbdFLfGkijBmMU",
    google_search_engine_id = "d08f1d4bbe2294372",
    # 动态生成的folder_id
    google_sheets_folder_id = dynamic_folder_id,
    google_oauth2_credentials_path = "configs/credentials.json",
    google_oauth2_token_path = "configs/credentials.json", # I just put them all together in the same file

    gcp_project_id = "mcp-bench0606",
    gcp_service_account_path = "configs/mcp-bench0606-2b68b5487343.json",

)