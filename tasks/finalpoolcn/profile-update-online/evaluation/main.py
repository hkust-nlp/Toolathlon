from argparse import ArgumentParser
import os
import re
from typing import Tuple

def check_paper_info(agent_workspace: str) -> Tuple[bool, str]:
    """
    检查个人主页是否正确添加了ArXiv论文信息
    """
    about_file_path = os.path.join(agent_workspace, "HYZ17.github.io", "_pages", "about.md")
    
    # 检查文件是否存在
    if not os.path.exists(about_file_path):
        return False, f"about.md file not found at {about_file_path}"
    
    try:
        with open(about_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, f"Error reading about.md file: {str(e)}"
    
    # 检查必要的信息
    required_checks = []
    
    # ===== 第一篇文章：SimpleRL-Zoo =====
    paper1_title = "SimpleRL-Zoo: Investigating and Taming Zero Reinforcement Learning for Open Base Models in the Wild"
    if paper1_title not in content:
        required_checks.append("第一篇论文标题不匹配 (SimpleRL-Zoo)")
    
    # 检查第一篇文章的ArXiv链接
    arxiv1_pattern = r"https://arxiv\.org/abs/2503\.18892"
    if not re.search(arxiv1_pattern, content):
        required_checks.append("第一篇论文ArXiv链接不正确或缺失 (2503.18892)")
    
    # # 检查第一篇文章的GitHub链接
    # github1_pattern = r"https://github\.com/hkust-nlp/simpleRL-reason"
    # if not re.search(github1_pattern, content):
    #     required_checks.append("第一篇论文GitHub链接不正确或缺失")
    
    # 检查第一篇文章的其他作者
    paper1_authors = ["Qian Liu", "Wei Liu", "Keqing He", "Zejun Ma", "Junxian He"]
    for author in paper1_authors:
        if author not in content:
            required_checks.append(f"第一篇论文作者列表中缺少 {author}")
    
    # 检查第一篇文章概述
    title1_index = content.find(paper1_title)
    if title1_index != -1:
        after_title1 = content[title1_index + len(paper1_title):]
        
        # 跳过标题后的两行（作者行和链接行）
        lines = after_title1.split('\n')
        if len(lines) >= 3:
            # 从第三行开始寻找概述（跳过作者行和链接行）
            summary_start = '\n'.join(lines[2:])
            
            # 找到下一个论文标题作为结束点
            next_paper_pattern = r'\n\*\*[^*]+\*\*'
            next_section = re.search(next_paper_pattern, summary_start)
            
            if next_section:
                paper1_section = summary_start[:next_section.start()]
            else:
                paper1_section = summary_start[:500]
            
            if not re.search(r'\*\s+\w+', paper1_section):
                required_checks.append("第一篇论文概述缺失（没有找到bullet points描述）")
        else:
            required_checks.append("第一篇论文格式不正确，无法找到概述部分")
    else:
        required_checks.append("无法找到第一篇论文标题位置来验证概述")
    
    # ===== 第二篇文章：B-STaR =====
    paper2_title = "B-STaR: Monitoring and Balancing Exploration and Exploitation in Self-Taught Reasoners"
    if paper2_title not in content:
        required_checks.append("第二篇论文标题不匹配 (B-STaR)")
    
    # 检查第二篇文章的ArXiv链接
    arxiv2_pattern = r"https://arxiv\.org/abs/2412\.17256"
    if not re.search(arxiv2_pattern, content):
        required_checks.append("第二篇论文ArXiv链接不正确或缺失 (2412.17256)")
    
    # 检查第二篇文章发表在ICLR 2025
    iclr_pattern = r"ICLR 2025"
    if not re.search(iclr_pattern, content):
        required_checks.append("第二篇论文缺少ICLR 2025发表信息")
    
    # 检查第二篇文章的其他作者
    paper2_authors = ["Lulu Zhao", "Yijun Wang", "Zifei Shan", "Junxian He"]
    for author in paper2_authors:
        if author not in content:
            required_checks.append(f"第二篇论文作者列表中缺少 {author}")
    
    # 检查第二篇文章概述
    title2_index = content.find(paper2_title)
    if title2_index != -1:
        after_title2 = content[title2_index + len(paper2_title):]
        
        # 跳过标题后的两行（作者行和链接行）
        lines = after_title2.split('\n')
        if len(lines) >= 3:
            # 从第三行开始寻找概述（跳过作者行和链接行）
            summary_start = '\n'.join(lines[2:])
            
            # 找到下一个论文标题作为结束点
            next_paper_pattern = r'\n\*\*[^*]+\*\*'
            next_section = re.search(next_paper_pattern, summary_start)
            
            if next_section:
                paper2_section = summary_start[:next_section.start()]
            else:
                paper2_section = summary_start[:500]
            
            if not re.search(r'\*\s+\w+', paper2_section):
                required_checks.append("第二篇论文概述缺失（没有找到bullet points描述）")
        else:
            required_checks.append("第二篇论文格式不正确，无法找到概述部分")
    else:
        required_checks.append("无法找到第二篇论文标题位置来验证概述")
    
    # # ===== 通用作者信息检查 =====
    # # 检查 Weihao Zeng 在两篇文章中都有 \* 标记（至少出现2次）
    # weihao_matches = re.findall(r"Weihao Zeng\s*\\?\*", content)
    # if len(weihao_matches) < 2:
    #     required_checks.append("Weihao Zeng 在两篇论文中都应该有 co-author 标记 \\*")
    
    # 检查 Yuzhen Huang 在两篇文章中都使用正确格式（至少出现2次）
    yuzhen_matches = re.findall(r"\*<ins>Yuzhen Huang</ins>\*", content)
    if len(yuzhen_matches) < 2:
        required_checks.append("Yuzhen Huang 在两篇论文中都应该使用格式 *<ins>Yuzhen Huang</ins>* ")
    
    # ===== 论文顺序验证 =====
    # 检查论文是否按照ArXiv发表日期倒序排列 (SimpleRL-Zoo 2025年3月 应在 B-STaR 2024年12月 前面)
    simplerl_position = content.find(paper1_title)
    bstar_position = content.find(paper2_title)
    
    if simplerl_position != -1 and bstar_position != -1:
        if simplerl_position > bstar_position:
            required_checks.append("论文顺序错误：SimpleRL-Zoo (2025年3月) 应该在 B-STaR (2024年12月) 前面，请按ArXiv日期倒序排列")
    elif simplerl_position == -1 and bstar_position != -1:
        required_checks.append("找不到 SimpleRL-Zoo 论文位置")
    elif simplerl_position != -1 and bstar_position == -1:
        required_checks.append("找不到 B-STaR 论文位置")
    else:
        required_checks.append("找不到两篇论文的位置")
    
    # 返回检查结果
    if required_checks:
        return False, f"验证失败: {'; '.join(required_checks)}"
    
    return True, "两篇论文信息验证通过"

def check_log(res_log: dict) -> Tuple[bool, str]:
    """
    检查日志信息
    """
    # 基本的日志检查
    if not res_log:
        return False, "日志为空"
    
    # 可以根据需要添加更多日志检查逻辑
    return True, "日志检查通过"

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True, help="Agent工作空间路径")
    parser.add_argument("--groundtruth_workspace", required=False, help="Ground truth工作空间路径")
    parser.add_argument("--res_log_file", required=False, help="结果日志文件路径")
    args = parser.parse_args()

    # 如果提供了日志文件，进行日志检查
    if args.res_log_file:
        try:
            import json
            with open(args.res_log_file, 'r', encoding='utf-8') as f:
                res_log = json.load(f)
            
            log_pass, log_error = check_log(res_log)
            if not log_pass:
                print("日志检查失败:", log_error)
                exit(1)
        except Exception as e:
            print(f"读取日志文件失败: {str(e)}")
            exit(1)
    
    # 检查论文信息
    paper_pass, paper_error = check_paper_info(args.agent_workspace)
    if not paper_pass:
        print("论文信息检查失败:", paper_error)
        exit(1)
    
    print("所有检查通过！任务完成验证成功。")
