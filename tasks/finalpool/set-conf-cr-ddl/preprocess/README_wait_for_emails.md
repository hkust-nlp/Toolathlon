# 邮件等待功能说明

## 概述

`wait_for_emails.py` 是一个用于等待Gmail邮件接收完成的工具。在发送邮件后，该工具会定期检查收件箱，确保所有预期的邮件都已收到。

## 功能特性

- ✅ 自动加载邮件数据文件（JSONL格式）
- ✅ 通过Gmail API检查邮件接收状态
- ✅ 实时显示等待进度
- ✅ 可配置的最大等待时间和检查间隔
- ✅ 超时保护机制
- ✅ 详细的日志输出

## 使用方法

### 命令行使用

```bash
uv run -m tasks.jl.gmail_calendar_001.preprocess.wait_for_emails \
    --credentials_file configs/credentials.json \
    --email_jsonl_file tasks/jl/gmail_calendar_001/files/emails.jsonl \
    --max_wait_minutes 30 \
    --check_interval 10
```

### 参数说明

- `--credentials_file`: Gmail API凭证文件路径（必需）
- `--email_jsonl_file`: 邮件数据JSONL文件路径（必需）
- `--max_wait_minutes`: 最大等待时间，单位分钟（默认: 30）
- `--check_interval`: 检查间隔，单位秒（默认: 10）

### 在main.py中的集成

该功能已经集成到 `main.py` 中，在发送邮件后会自动调用：

```python
# 等待直到所有邮件都已收到
print("等待邮件接收完成...")
asyncio.run(run_command(
            f"uv run -m tasks.jl.gmail_calendar_001.preprocess.wait_for_emails "
            f"--credentials_file {args.credentials_file} "
            f"--email_jsonl_file {email_jsonl_file} "
            f"--max_wait_minutes 30 "
            f"--check_interval 10"
            ,debug=True,show_output=True))
```

## 工作原理

1. **加载邮件数据**: 从JSONL文件中读取预期的邮件列表
2. **获取Gmail服务**: 使用凭证文件初始化Gmail API服务
3. **定期检查**: 每隔指定时间检查收件箱中来自指定发件人的邮件数量
4. **进度显示**: 实时显示已收到的邮件数量和等待时间
5. **完成判断**: 当收到的邮件数量达到预期数量时，认为接收完成
6. **超时保护**: 如果超过最大等待时间仍未完成，则退出并报错

## 输出示例

```
============================================================
等待邮件接收完成
============================================================
正在加载邮件数据...
期望接收 6 封邮件
发件人邮箱: sender@gmail.com
收件人邮箱: receiver@gmail.com

开始等待邮件接收...
检查间隔: 10 秒
最大等待时间: 30 分钟
------------------------------------------------------------
[00:00:10] 已收到 2/6 封邮件
[00:00:20] 已收到 4/6 封邮件
[00:00:30] 已收到 6/6 封邮件

✅ 所有邮件都已收到！
   期望: 6 封
   实际: 6 封
   耗时: 0 分 30 秒

✅ 邮件接收等待完成！
```

## 错误处理

- **文件不存在**: 如果凭证文件或邮件数据文件不存在，会显示错误并退出
- **API错误**: 如果Gmail API调用失败，会显示具体错误信息
- **超时错误**: 如果超过最大等待时间，会显示超时信息并退出
- **用户中断**: 支持Ctrl+C中断操作

## 测试

运行测试脚本验证功能：

```bash
python tasks/jl/gmail_calendar_001/preprocess/test_wait_for_emails.py
```

## 注意事项

1. 确保Gmail API凭证文件有效且具有读取邮件的权限
2. 检查间隔不宜过短，建议至少10秒，避免API调用过于频繁
3. 最大等待时间应根据网络环境和邮件服务器响应时间合理设置
4. 该工具只检查最近10分钟内的邮件，确保在发送邮件后及时运行 