本任务的主角是 ryan.brown93@mcp.com ，token是 canvas_token_BryapivvLK7C
初始化
会自动清除原有的quiz和assignments，然后根据 files/course_config.json 信息创建带问题的quiz
assignments任务重cs101 cs201课程已经提交作业，所以不应该出现在答案

答案获取在
 preprocess/extract_quiz_info.py  直接从course_config.json 获取信息，生成gt的表格。

final_xiaochen_dev
 修改 preprocess/setup_courses_with_mcp.py 中复用中定义的工具。
 修复 finalpool_dev中的 extract_quiz_info.py 处理得到的gt文件跟inital-workspace中的文件模板不一样问题。
 修复 evaluation/check_local.py 中对关键列缺失和item顺序的检查。
 修复 utils/app_specific/canvas/api_client.py 中 create_assignment函数缺少 submission_types 和 allowed_extensions 参数，导致assignment无法提交的问题
