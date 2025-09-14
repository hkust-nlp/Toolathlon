from argparse import ArgumentParser
import os
import yaml
import re
from utils.general.helper import read_json

def extract_person_info_from_memory(memory_file):
    """从内存文件中提取Junteng Liu的个人信息"""
    person_info = {}
    
    try:
        with open(memory_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    data = eval(line)  # 使用eval解析JSON行
                    if data.get("type") == "entity" and data.get("entityType") == "Person" and data.get("name") == "Junteng Liu":
                        observations = data.get("observations", [])
                        for obs in observations:
                            # 提取基本信息
                            if "PhD candidate" in obs:
                                person_info["current_position"] = obs
                            elif "Graduated from" in obs:
                                person_info["education"] = obs
                            elif "Research focuses" in obs:
                                person_info["research_focus"] = obs
                            elif "Research interests include" in obs:
                                if "research_interests" not in person_info:
                                    person_info["research_interests"] = []
                                person_info["research_interests"].append(obs)
                            elif "Ph.D." in obs and "2024-Present" in obs:
                                person_info["phd_program"] = obs
                            elif "B.Eng." in obs and "2020-2024" in obs:
                                person_info["bachelor_program"] = obs
                            elif "Research Intern" in obs:
                                if "internships" not in person_info:
                                    person_info["internships"] = []
                                person_info["internships"].append(obs)
                            elif "Published" in obs and "First author" in obs:
                                if "publications_first_author" not in person_info:
                                    person_info["publications_first_author"] = []
                                person_info["publications_first_author"].append(obs)
                            elif "Co-authored" in obs:
                                if "publications_co_author" not in person_info:
                                    person_info["publications_co_author"] = []
                                person_info["publications_co_author"].append(obs)
                            elif "Received" in obs and "Scholarship" in obs:
                                person_info["awards"] = obs
                            elif "Email:" in obs:
                                person_info["email"] = obs.split("Email: ")[1]
                            elif "GitHub:" in obs:
                                person_info["github"] = obs
                            elif "Google Scholar profile:" in obs:
                                person_info["google_scholar"] = obs
                            elif "X (Twitter) account:" in obs:
                                person_info["twitter"] = obs
                except:
                    continue
    except Exception as e:
        print(f"Error reading memory file: {e}")
        return {}
    
    return person_info

def check_config_yaml(config_file, person_info):
    """检查_config.yaml文件是否包含正确的个人信息"""
    if not os.path.exists(config_file):
        return False, f"Config file not found: {config_file}"
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        return False, f"Error reading config file: {str(e)}"
    
    # 检查基本信息
    required_fields = {
        "name": "Junteng Liu",
        "email": person_info.get("email", "jliugi@connect.ust.hk"),
        "github": "Vicent0205"
    }
    
    for field, expected_value in required_fields.items():
        if field not in config:
            return False, f"Missing field '{field}' in _config.yaml"
        
        actual_value = config[field]
        if field == "github":
            # GitHub字段可能包含完整URL或用户名
            if expected_value not in str(actual_value):
                return False, f"GitHub mismatch: expected containing '{expected_value}', got '{actual_value}'"
        else:
            if str(actual_value).lower() != str(expected_value).lower():
                return False, f"{field} mismatch: expected '{expected_value}', got '{actual_value}'"
    
    return True, "Config file verification passed"

def check_about_md(about_file, person_info):
    """检查_pages/about.md文件是否包含正确的个人信息"""
    if not os.path.exists(about_file):
        return False, f"About file not found: {about_file}"
    
    try:
        with open(about_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, f"Error reading about file: {str(e)}"
    
    # 检查基本信息
    required_info = [
        "Junteng Liu",
        "PhD candidate",
        "HKUST",
        "NLP",
        "Shanghai Jiao Tong University"
    ]
    
    for info in required_info:
        if info.lower() not in content.lower():
            return False, f"Missing required information '{info}' in about.md"
    
    # 检查研究兴趣
    research_interests = person_info.get("research_interests", [])
    for interest in research_interests:
        # 提取研究兴趣的关键词
        if "LLM Reasoning" in interest or "Reinforcement Learning" in interest:
            if "reasoning" not in content.lower() and "reinforcement" not in content.lower():
                return False, f"Missing research interest about LLM Reasoning/Reinforcement Learning"
        elif "Hallucination" in interest or "VLM" in interest:
            if "hallucination" not in content.lower() and "vlm" not in content.lower():
                return False, f"Missing research interest about Hallucination in VLM"
        elif "Truthfulness" in interest or "Interpretability" in interest:
            if "truthfulness" not in content.lower() and "interpretability" not in content.lower():
                return False, f"Missing research interest about LLM Truthfulness/Interpretability"
    
    # 检查教育背景
    if "Ph.D." not in content or "Computer Science" not in content:
        return False, "Missing PhD program information"
    
    if "B.Eng." not in content or "Shanghai Jiao Tong University" not in content:
        return False, "Missing Bachelor's degree information"
    
    # 检查实习经历
    internships = person_info.get("internships", [])
    for internship in internships:
        if "MINIMAX" in internship or "Tencent" in internship or "Shanghai AI Lab" in internship:
            company_name = "MINIMAX" if "MINIMAX" in internship else "Tencent" if "Tencent" in internship else "Shanghai AI Lab"
            if company_name.lower() not in content.lower():
                return False, f"Missing internship information about {company_name}"
    
    # 检查出版物
    publications = person_info.get("publications_first_author", []) + person_info.get("publications_co_author", [])
    for pub in publications:
        if "SynLogic" in pub or "Perception Bottleneck" in pub or "Universal Truthfulness" in pub:
            pub_keyword = "SynLogic" if "SynLogic" in pub else "Perception" if "Perception" in pub else "Truthfulness"
            if pub_keyword.lower() not in content.lower():
                return False, f"Missing publication information about {pub_keyword}"
    
    # 检查联系方式
    if "jliugi@connect.ust.hk" not in content:
        return False, "Missing email contact information"
    
    if "github.com" not in content.lower() and "vicent0205" not in content.lower():
        return False, "Missing GitHub profile information"
    
    return True, "About file verification passed"

def check_local(agent_workspace, groundtruth_workspace):
    """检查代理生成的个人网站是否正确集成了内存中的个人信息"""
    
    # 构建文件路径
    memory_file = os.path.join(groundtruth_workspace, "memory", "memory.json")
    config_file = os.path.join(agent_workspace, "_config.yaml")
    about_file = os.path.join(agent_workspace, "_pages", "about.md")
    
    # 检查内存文件是否存在
    if not os.path.exists(memory_file):
        return False, f"Memory file not found: {memory_file}"
    
    # 从内存中提取个人信息
    person_info = extract_person_info_from_memory(memory_file)
    if not person_info:
        return False, "Failed to extract person information from memory"
    
    # 检查_config.yaml文件
    config_success, config_message = check_config_yaml(config_file, person_info)
    if not config_success:
        return False, f"Config file check failed: {config_message}"
    
    # 检查_pages/about.md文件
    about_success, about_message = check_about_md(about_file, person_info)
    if not about_success:
        return False, f"About file check failed: {about_message}"
    
    return True, "Personal website verification passed! All required information correctly integrated."

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--groundtruth_workspace", required=True)
    args = parser.parse_args()

    success, message = check_local(args.agent_workspace, args.groundtruth_workspace)
    
    if success:
        print("Pass test! " + message)
    else:
        print("Test failed: " + message)
        exit(1) 