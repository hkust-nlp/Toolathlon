把所有的中文名和邮箱替换成最新的可用信息。
增加一点难度，在tasks/finalpool/course-assistant/files/emails.jsonl 中把Michelle Brooks 的邮件主题从prezatation换成了assginment，也就是他发错作业了，所以他也算未完成作业。
在preprocess中清空该任务设计的所有邮箱（ tasks/finalpool/course-assistant/emails_all_config.json）
并且在check_local 中添加negative email的检查，也就是除了检查三个需要发送邮件外，还要检查agent是否给其他人多发送了邮件。
检查了prompt

在发送邮件中，注意，课程一共有16人，其中两人不需要发邮件，两人（Steven Morgan ，Carolyn Alvarez）是未完成作业的人。所以一共要发12封邮件。
"运行结果: 成功=True, 已发送账户数=12/15, 跳过同址=1, 无匹配内容=2, 收件人=virginia_diaz@mcp.com" 是正确的log