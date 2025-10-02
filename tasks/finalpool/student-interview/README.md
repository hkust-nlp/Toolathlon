# Student Interview Scheduling Task

This task simulates a professor's workflow of scheduling interviews with students based on their research qualifications and calendar availability.

> About irrelevant email injection: There are 300 pre-constructed irrelevant emails in `student-interview/preprocess/files/fake_emails_300_manual.json`. All content is fictional, with email addresses using the mcp.com domain. These emails are guaranteed to have no conflicts with the 503 currently deployed addresses. You can randomly sample from them in the preprocess step and inject them into the INBOX together with the task-related emails via IMAP. Note: It is recommended to sort all emails by `send_time` before injection.
>
> Regarding the timestamps in these emails: All dates in `student-interview/preprocess/files/fake_emails_300_manual.json` use the placeholder `xx days before current date`. You can batch-replace these placeholders by specifying the current date. For implementation details, you can directly use Claude Code to parse the preprocessing logic of this task and migrate it to other tasks if needed.

## Email System Design

### Student Emails (20 emails)

- **Source**: `preprocess/files/emails.jsonl`
- **Email addresses**: Mapped to actual `@mcp.com` addresses from `user_list.csv`
- **Timestamps**: Random dates 1-60 days before current date
- **Content**: Detailed academic backgrounds, publications, and contact information

#### Fake Email Characteristics

- **Source**: `preprocess/files/fake_emails_300_manual.json`
- **Timestamps**: Random dates 1-30 days before current date (more recent than most student emails)
- **Sender patterns**: Generic corporate/service email formats
- **Content**: Non-academic subjects that should be ignored
- **Date placeholders**: Dynamic content with resolved relative dates

## Preprocessing System

### Simple Email Processing Method

#### Step 1: Load All Emails

```python
# Load student emails from JSONL
student_emails = load_student_emails("emails.jsonl")

# Load fake emails from JSON  
fake_emails = load_fake_emails("fake_emails_300_manual.json", count=50-100)
```

#### Step 2: Assign Timestamps

```python
# Student emails: 1-60 days before current date
for email in student_emails:
    email['send_time'] = current_date - random(1-60 days)

# Fake emails: 1-30 days before current date  
for email in fake_emails:
    email['send_time'] = current_date - random(1-30 days)
```

#### Step 3: Combine and Sort

```python
# Mix all emails together
all_emails = student_emails + fake_emails

# Sort by timestamp (newest first - like real inbox)
all_emails.sort(key=lambda x: x['send_time'], reverse=True)
```

#### Step 4: Inject to IMAP

```python
# Clean existing emails
clean_inbox()

# Inject all emails in sorted order
for email in all_emails:
    inject_to_imap(email)
```

## Evaluation Logic

The evaluation checks three key checkpoints:

### Checkpoint 1 (50 points): Correct Student Selection

- Agent must identify the 3 qualified students with first-author publications
- Points awarded only for correctly identified students

### Checkpoint 2 (30 points): Valid Scheduling

- Interview times must not conflict with existing calendar events
- Times must be within reasonable hours
- No overlapping appointments

### Checkpoint 3 (20 points): Complete Coverage

- All 3 qualified students must be scheduled
- No qualified student should be missed