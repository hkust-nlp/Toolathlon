The main user for this task is ryan.brown93@mcp.com. The token is canvas_token_BryapivvLK7C.

Initialization:
The system will automatically clear any existing quizzes and assignments, and then create new quizzes with questions based on information from files/course_config.json.
For assignments in courses cs101 and cs201, the assignments have already been submitted, so they should not appear in the answers.

How to get the ground-truth answers:
Use preprocess/extract_quiz_info.py to extract information directly from course_config.json and generate the ground-truth table.

final_xiaochen_dev updates:
- Refactored preprocess/setup_courses_with_mcp.py to reuse shared tools.
- Fixed the issue in finalpool_dev’s extract_quiz_info.py where the generated ground truth file format differed from that of initial-workspace.
- Fixed evaluation/check_local.py to check for missing key columns and ensure item order is correct.
- Fixed utils/app_specific/canvas/api_client.py by adding missing submission_types and allowed_extensions parameters to the create_assignment function, so that assignments can be submitted successfully.

the initial state and groundtruth ius dynamically generated in this task!

According to the ENG class info, I do not need to attend this quiz.
