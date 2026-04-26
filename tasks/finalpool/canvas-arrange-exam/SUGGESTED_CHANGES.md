# Suggested Task Fix Notes

## What We Plan to Change
- Update the task text so the agent is told to check related exam-notification emails as well as Canvas announcements.
- Let preprocessing continue until the exam email injection step is complete.

## Why This Change May Be Needed
The evaluator expects exam information that is provided through email, especially for `NET101`. If the task text only points to Canvas announcements, the agent may never know that email is also required.

## Original Logic and Suggested New Logic
- Original: the task text asked the agent to check Canvas announcements.
- Suggested: the visible task should mention both Canvas announcements and related exam-notification emails.
- Original: the preprocessing script exited after publishing Canvas courses and announcements, before injecting the exam notification email.
- Suggested: preprocessing should publish the Canvas data and then inject the email data before the agent starts.
