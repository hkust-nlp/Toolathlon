def check_log(res_log: dict):
    # 检查日志中是否包含关键的市场研究信息
    needed_contents = {
        "Appliance": False,           # 目标门类
        "Electric": False,            # 组件类别1
        "Construction": False,        # 组件类别2  
        "Furniture": False,           # 组件类别3
    }
    
    messages = res_log['messages']
    
    for turn in messages:
        if turn['role'] != 'assistant':
            continue
        content = turn['content']
        if content is None:
            continue
            
        # 检查是否提到了关键信息
        content_lower = content.lower()
        for key in needed_contents:
            if key.lower() in content_lower:
                needed_contents[key] = True
    
    # 检查是否所有关键信息都被提及
    missing_items = [key for key, found in needed_contents.items() if not found]
    
    if missing_items:
        error_msg = f"日志中缺少以下关键信息: {', '.join(missing_items)}"
        return False, error_msg
    
    return True, None 