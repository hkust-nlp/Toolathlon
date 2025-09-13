我是旅行社的工作人员。需要分析这个旅游攻略视频（  https://youtu.be/5KTSd2jGYHo ）

步骤1：字幕提取

从提供的旅游攻略视频中提取完整原版字幕
将字幕保存为文本文件，文件名格式：video_subtitles.txt
保持原始时间戳和格式不变

步骤2：内容总结

仅总结前5天（第1天至第5天，包含第5天）的行程内容保存到markdown文件summary.md
严格按照以下格式输出：

Day X: Location A → Location B → Location C

Detailed stops for the day:
- Stop 1: [Location name] - [Brief description]
- Stop 2: [Location name] - [Brief description]
- Stop 3: [Location name] - [Brief description]

Recommended visiting order: [Specific sequence with timing if available]
格式要求：

每天必须独立成段
如果一个大地点里面有多个景点，则标题中只描述大地点
段落开头必须使用"Day X:"格式
箭头符号统一使用"→"
主要停留点用bullet points列出
建议游览顺序单独一行说明



输出约束：
所有文件和内容使用英文
文件命名严格按照指定格式
不允许格式变体或同义表达
地点名称使用官方名称
