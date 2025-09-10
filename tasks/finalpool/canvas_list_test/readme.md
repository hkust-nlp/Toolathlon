本任务的主角是 ryan.brown93@mcp.com ，token是 canvas_token_BryapivvLK7C
初始化
会自动清除原有的quiz和assignments，然后根据 files/course_config.json 信息创建带问题的quiz
assignments任务重cs101 cs201课程已经提交作业，所以不应该出现在答案

答案获取在
 preprocess/extract_quiz_info.py  直接从course_config.json 获取信息，生成gt的表格。