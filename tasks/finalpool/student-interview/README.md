# Student Interview Scheduling Task

This task simulates a professor's workflow of scheduling interviews with students based on their research qualifications and calendar availability.

> 关于无关邮件注入：在`student-interview/preprocess/files/fake_emails_300_manual.json`下有300个构造好的无关邮件，所有内容均为虚构，含有mcp.com的邮件名称和当前实际部署的503个无冲突，可以在preprocess中随机抽取并用IMAP和任务邮件一起注入到INBOX当中，注意在注入前最好先根据send_time排序
> 
> 另外关于邮件中涉及的时间：`student-interview/preprocess/files/fake_emails_300_manual.json`当中的所有时间都使用占位符`xx days before current date`代替，可以通过指定当前时间来批量替换，具体实现过程可以直接使用Claude Code解析本任务的预处理过程，迁移到其他任务上

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