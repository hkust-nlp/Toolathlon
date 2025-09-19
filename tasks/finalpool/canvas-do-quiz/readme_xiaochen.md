这个任务的难点在于课程太多了。模型没做完所有course的题目就认为已经做完且退出了。  
对于检测quiz中的题目是否正确。 通过两个模型 claude4，gemini共同保证。然后在测试运行的时候会查看模型做错的题。  
比如  
QUIZ 2: PHIL201 Advanced Logical Reasoning and Argumentation Quiz**  
Question 1 ，手动检查了这个答案没问题。


Student: Stephen Gomez (stepheng@mcp.com)
Total quizzes: 14
Full score quizzes: 1
Success rate: 7.1%

Detailed Results:
  MATH201-2: MATH201 Calculus and Linear Algebra Quiz
    Score: 100.0/200.0 - ✗ NOT FULL SCORE (Attempt 1)
  PHIL201-2: PHIL201 Advanced Logical Reasoning and Argumentation Quiz
    Score: 0/180.0 - ✗ NOT FULL SCORE (Attempt 1) [No score recorded]
  CS201-2: CS201 Algorithm Analysis Quiz
    Score: 150.0/150.0 - ✓ FULL SCORE (Attempt 1)
