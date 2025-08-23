#GT的获得
procss_exam_data.py 脚本是用来处理json得到gt excel的。gt的xecel是在此基础上再加一些人为的小改动来增加难度。


# 考试通知邮件发送脚本

## 概述

这个脚本通过Poste.io邮件服务器（运行在10005端口）发送考试通知邮件，使用SMTP协议发送邮件并通过IMAP协议验证发送状态。

## 文件说明

- `send_exam_notification_smtp.py` - 主邮件发送脚本
- `test_config.py` - 配置文件测试脚本
- `email_config.json` - 邮件发送配置文件
- `exam_notification_template.txt` - 邮件模板文件

## 配置要求

### 1. Poste.io服务
- Web界面：http://localhost:10005
- SMTP端口：localhost:2525
- IMAP端口：localhost:1143

### 2. 账户信息
- 发件人：susan.parker@mcp.com
- 收件人：rkelly27@mcp.com

## 使用方法

### 1. 测试配置
```bash
cd tasks/xiaochen/canvas_arrange_exam/scripts
python test_config.py
```

### 2. 发送邮件
```bash
cd tasks/xiaochen/canvas_arrange_exam/scripts
python send_exam_notification_smtp.py
```

## 功能特性

- ✅ SMTP邮件发送
- ✅ IMAP邮件验证
- ✅ 详细的日志记录
- ✅ 错误处理和重试机制
- ✅ 邮件模板支持
- ✅ 配置化管理

## 输出说明

### 成功输出示例
```
✅ 邮件发送成功！
📧 发件人: susan.parker@mcp.com
📧 收件人: rkelly27@mcp.com
📝 主题: 考试通知 - 重要提醒
📅 考试时间: 2024年12月20日 上午9:00-11:00
📍 考试地点: 教学楼A座301教室

🎯 考试通知邮件处理完成！
```

### 日志文件
- 日志文件：`email_send.log`
- 包含详细的连接、认证、发送和验证信息

## 故障排除

### 常见问题

1. **SMTP连接失败**
   - 检查Poste.io服务是否运行
   - 确认端口2525是否开放

2. **认证失败**
   - 检查账户密码是否正确
   - 确认账户是否已在Poste.io中创建

3. **IMAP验证失败**
   - 检查端口1143是否开放
   - 确认发件箱权限设置

### 调试模式
脚本默认启用SMTP调试模式，会显示详细的连接信息。

## 注意事项

- 确保Poste.io服务正在运行
- 检查防火墙设置，确保端口2525和1143可访问
- 邮件发送后会在日志中记录详细信息
- 如果IMAP验证失败，邮件仍可能发送成功

## 技术支持

如遇到问题，请检查：
1. 配置文件格式是否正确
2. 网络连接是否正常
3. 日志文件中的错误信息

