Today, we have three new employees onboarding. Each new employee's onboarding information is stored in the Snowflake database. According to each employee’s group, generate an onboarding task list automatically (the agent needs to read the employee handbook, which is a PDF, including both default common training tasks and group-specific training tasks), send the task list via email to the employee, and automatically update the task content and planned completion date in the database. Additionally, the agent must check for any employees whose training plan due dates have passed and whose tasks remain "Incomplete", and send them a reminder email in the format: “Dear xxx, you still have the following onboarding training tasks to complete:\nxx\nxx\nxx\nxx Please complete them as soon as possible.” The reminder email should also CC the employee’s direct manager.

Workflow for constructing the evaluation agent task:

- Create a configuration JSON:
    - 3 new employees, 20 existing employees (among which 4 have pending tasks), 4 managers corresponding to 4 groups
    - Each employee has their own training task completion status
    - Task status includes: "Incomplete" (all tasks are incomplete for new employees, and some tasks past their deadline ("ddl") are incomplete for some existing employees), or "Complete" (all tasks finished)
    - Due to the dynamic nature of date calculations, set the overdue tasks according to the current date. For example, if the ddl is current date minus 10 days, then tasks assigned more than 10 days ago are overdue.
        - All times should use a negative number to indicate "current date - x days"
        - Managers’ start dates: current date - ~1000 days
        - Existing employees’ start dates: current date - between 365 and 1000 days
        - New employees’ start date: current date - 0 days (i.e., today)
    
    - Each employee has their own direct manager and email address.
        For managers, the "report-to" could be the boss.

        Table: employee-id, name, email, report-to-(id)
        Table: employee-id, landing-date, landing-task-assigned

    - Each group has its own training tasks. Training tasks include both common training tasks and group-specific tasks. Each table for group tasks and common tasks is separate and needs to be read separately. The structure is as follows:
        Table: task-id, task-name, employee-id, create-date, ddl, finished-flag

- Preprocessing:
    - Load the configuration JSON, delete the existing database, and then write the configuration JSON into the database.
    - Generate an employee handbook (PDF) including both common onboarding training tasks and each group’s training tasks.
    - Specifically, the tasks are:
        - Common onboarding training tasks:
            - Orientation
            - Safety training
            - Confidentiality training
            - Company culture
            - Company strategy
        - Group-1 (Backend) training tasks:
            - Backend development process
            - Backend development standards
            - Backend development environment
        - Group-2 (Frontend) training tasks:
            - Frontend development process
            - Frontend development standards
            - Frontend development environment
        - Group-3 (QA) training tasks:
            - Testing development process
            - Testing development standards
            - Testing development environment
        - Group-4 (Data) training tasks:
            - Data development process
            - Data development standards
            - Data development environment

- Evaluation:
    - Check whether the emails are sent to the correct employees and CC’d to the correct direct managers
    - Check for duplicate or extra email notifications
    - Verify the content of the emails
    - Verify whether the new onboarding tasks for the three new employees are added correctly in the database
    - Confirm that the database contains exactly the newly assigned tasks, no more and no less

