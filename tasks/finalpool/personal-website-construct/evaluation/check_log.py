from argparse import ArgumentParser
from utils.general.helper import read_json
import re

def check_person_info_in_content(content):
    """检查内容中是否包含个人信息相关的关键词"""
    content_lower = content.lower()
    person_keywords = [
        "junteng", "liu", "phd", "candidate", "hkust", "nlp",
        "shanghai jiao tong", "sjtu", "research", "publication",
        "internship", "minimax", "tencent", "shanghai ai lab",
        "email", "github", "scholar", "twitter"
    ]
    
    return any(keyword in content_lower for keyword in person_keywords)

def check_log(res_log):
    """检查代理是否执行了适当的个人网站构建行动"""
    
    found_website_actions = False
    found_person_info = False
    found_file_operations = False
    
    # 检查工具使用
    tool_usage = []
    
    for entry in res_log.get('messages', []):
        if 'tool_calls' in entry:
            for tool_call in entry['tool_calls']:
                tool_name = tool_call.get('function', {}).get('name', '')
                tool_usage.append(tool_name)
        
        # 检查内容中的行动和关键词
        if 'content' in entry and entry['content']:
            content = entry['content']
            
            
            # 检查个人信息
            if not found_person_info:
                if check_person_info_in_content(content):
                    found_person_info = True
    


    # 验证代理处理了个人信息
    if not found_person_info:
        return False, "Agent did not process personal information from memory"
    

    return True, "Personal website construction log check passed"

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--res_log_file", required=True)
    args = parser.parse_args()

    try:
        data = read_json(args.res_log_file)
        success, message = check_log(data)
        
        if success:
            print("Pass test! " + message)
        else:
            print("Test failed: " + message)
            exit(1)
            
    except Exception as e:
        print(f"Error checking log: {str(e)}")
        exit(1) 