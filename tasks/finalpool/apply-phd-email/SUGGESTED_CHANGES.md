# Suggested Task Fix Notes

## What We Plan to Change
- Clear the receiver mailbox during preprocessing, in addition to preparing the sender mailbox.
- During evaluation, only accept emails whose subject exactly matches `PhD Application Materials Submission (Student ID: 2201210606)`.
- If several exact-subject emails exist, check the newest one.

## Why This Change May Be Needed
The evaluator checks the receiver mailbox. If older application emails are still present there, an empty or partial run may pass for the wrong reason, or old attachments may be mixed with new ones.

## Original Logic and Suggested New Logic
- Original: preprocessing prepared the sender-side email environment, while the receiver mailbox could still contain old emails.
- Suggested: preprocessing should also clean the receiver mailbox used by the evaluator.
- Original: evaluation searched for emails with attachments using a broad subject keyword match.
- Suggested: evaluation should select the latest email with the exact task-required subject before checking attachments.
