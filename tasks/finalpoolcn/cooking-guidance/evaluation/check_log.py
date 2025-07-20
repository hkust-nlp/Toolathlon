def check_log(res_log: dict):
    """
    检查对话日志中是否包含三道菜的推荐 (中英双语检测)
    """
    print("\n" + "="*80)
    print("对话日志内容检查")
    print("="*80)
    
    # 只检查是否提到了三道菜
    three_dishes_found = False
    evidence = []
    
    messages = res_log.get('messages', [])
    assistant_message_count = 0
    
    for turn in messages:
        if turn.get('role') != 'assistant':
            continue
        
        assistant_message_count += 1
        content = turn.get('content', '')
        if content is None:
            continue
            
        content_lower = content.lower()
        
        # 检查中文关键词
        chinese_dish_keywords = ["菜", "道菜", "菜肴", "菜谱", "推荐"]
        chinese_number_keywords = ["三", "3", "三道", "3道", "三个", "3个"]
        
        # 检查英文关键词  
        english_dish_keywords = ["dish", "dishes", "recipe", "recipes", "recommend", "cuisine"]
        english_number_keywords = ["three", "3", "third"]
        
        found_chinese_dish = any(kw in content for kw in chinese_dish_keywords)
        found_chinese_number = any(kw in content for kw in chinese_number_keywords)
        
        found_english_dish = any(kw in content_lower for kw in english_dish_keywords)
        found_english_number = any(kw in content_lower for kw in english_number_keywords)
        
        # 中文检测：需要同时包含菜肴词汇和数量词汇
        chinese_match = found_chinese_dish and found_chinese_number
        
        # 英文检测：需要同时包含菜肴词汇和数量词汇
        english_match = found_english_dish and found_english_number
        
        if chinese_match or english_match:
            three_dishes_found = True
            evidence.append({
                "message_index": assistant_message_count,
                "chinese_match": chinese_match,
                "english_match": english_match,
                "chinese_dish_found": [kw for kw in chinese_dish_keywords if kw in content] if found_chinese_dish else [],
                "chinese_number_found": [kw for kw in chinese_number_keywords if kw in content] if found_chinese_number else [],
                "english_dish_found": [kw for kw in english_dish_keywords if kw in content_lower] if found_english_dish else [],
                "english_number_found": [kw for kw in english_number_keywords if kw in content_lower] if found_english_number else []
            })
            break  # 找到第一个匹配就停止
    
    print(f"📊 助手回复消息数量: {assistant_message_count}")
    print(f"\n🔍 三道菜检测结果:")
    
    if three_dishes_found:
        ev = evidence[0]  # 取第一个匹配的证据
        print(f"✅ 检测到三道菜推荐")
        print(f"   出现位置: 第 {ev['message_index']} 条助手回复")
        
        if ev['chinese_match']:
            print(f"   🇨🇳 中文匹配:")
            print(f"      菜肴词汇: {ev['chinese_dish_found']}")
            print(f"      数量词汇: {ev['chinese_number_found']}")
        
        if ev['english_match']:
            print(f"   🇺🇸 英文匹配:")
            print(f"      菜肴词汇: {ev['english_dish_found']}")
            print(f"      数量词汇: {ev['english_number_found']}")
        
        print(f"\n 对话日志检查通过!")
        print("="*80)
        return True, None
    else:
        print(f"❌ 未检测到三道菜推荐")
        print(f"   需要同时包含:")
        print(f"   中文: 菜肴词汇(菜/道菜/菜肴/菜谱/推荐) + 数量词汇(三/3/三道/3道/三个/3个)")
        print(f"   或英文: 菜肴词汇(dish/dishes/recipe/recipes/recommend/cuisine) + 数量词汇(three/3/third)")
        print("="*80)
        return False, "对话日志中未检测到三道菜推荐" 