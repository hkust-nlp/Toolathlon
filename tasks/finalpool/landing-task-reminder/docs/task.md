Today we have 3 new employees joining us, and each employee's information is stored in the Snowflake database.

Based on the employee's group assignment and related document in workspace, automatically generate training task lists, send emails to the employee's email address, and update the task content and planned completion dates to the database.

For new employees, send onboarding emails in the following format:

```
Dear xxx, You have the following training tasks to complete:
xxx
xxx
xxx
Please complete them as soon as possible.
```

Additionally, you need to check for employee records where the current date has exceeded the training completion deadline but the task status is still "incomplete", send reminder emails to the employees themselves in the same format.

The order of the tasks in the email should be based on the order in the document.

And remember to CC their direct supervisor.