import asyncio
from argparse import ArgumentParser
from pathlib import Path
from utils.general.helper import run_command, get_module_path
from time import sleep
import sys
import os
import json
from typing import Dict, List, Union

# 添加当前目录到路径以便导入本地模块
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from clean_local_emails import clean_multiple_accounts

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    # # 本地邮箱配置
    # local_email_receiver_config = {
    #     "email": "virginia_diaz@mcp.com",
    #     "password": "virginia_85W", 
    #     "name": "NLP Course Assistant",
    #     "imap_server": "localhost", 
    #     "imap_port": 1143,
    #     "smtp_server": "localhost",
    #     "smtp_port": 1587, 
    #     "use_ssl": False,
    #     "use_starttls": False,
    #     "use_auth": False  # 本地服务器无需认证
    # }

    # local_email_config = {
    #     "email": "mcooper@mcp.com",
    #     "password": "maria_89vHV7", 
    #     "name": "NLP Course Student",
    #     "imap_server": "localhost", 
    #     "imap_port": 1143,
    #     "smtp_server": "localhost",
    #     "smtp_port": 1587, 
    #     "use_ssl": False,
    #     "use_starttls": False,
    #     "use_auth": False  # 本地服务器无需认证
    # }

    # # 学生邮箱配置 - Steven Morgan
    # local_email_config_zxz = {
    #     "email": "smorgan@mcp.com",
    #     "password": "Msteb9yvjMIY", 
    #     "name": "Steven Morgan",
    #     "imap_server": "localhost", 
    #     "imap_port": 1143,
    #     "smtp_server": "localhost",
    #     "smtp_port": 1587, 
    #     "use_ssl": False,
    #     "use_starttls": False,
    #     "use_auth": False
    # }

    # # 学生邮箱配置 - 韦杨珂
    # local_email_config_wyk = {
    #     "email": "calvarez@mcp.com",
    #     "password": "alvarez@c241", 
    #     "name": "Carolyn Alvarez",
    #     "imap_server": "localhost", 
    #     "imap_port": 1143,
    #     "smtp_server": "localhost",
    #     "smtp_port": 1587, 
    #     "use_ssl": False,
    #     "use_starttls": False,
    #     "use_auth": False
    # }

    print("发邮件以构建初始状态")
    
    # 首先清理所有相关的邮箱账户（包括学生邮箱）
    print("清理本地邮箱（包括学生邮箱）")
    # 使用clean_local_emails模块的逻辑：从emails_all_config.json读取并批量清理
    
    config_path = os.path.abspath(os.path.join(current_dir, '..', 'emails_all_config.json'))
    with open(config_path, 'r', encoding='utf-8') as f:
        accounts_to_clean: Union[Dict[str, str], List[Dict[str, str]]] = json.load(f)
    
    
    
    clean_success = clean_multiple_accounts(accounts_to_clean)
    if not clean_success:
        print("⚠️ 邮箱清理未完全成功，但继续执行邮件发送")
    else:
        print("✅ 邮箱清理完成")

    # 读取收件人配置（单个）
    receiver_config_path = os.path.abspath(os.path.join(current_dir, '..', 'emails_config.json'))
    with open(receiver_config_path, 'r', encoding='utf-8') as f:
        receiver_config: Dict[str, str] = json.load(f)
    receiver = receiver_config["email"]

    # 邮件数据文件路径
    email_jsonl_file = Path(__file__).parent / ".." / "files" / "emails.jsonl"
    placeholder_file_path = Path(__file__).parent / ".." / "files" / "placeholder_values.json"

    # 使用本地send_email.py模块
    send_email_path = Path(__file__).parent / "send_email.py"
    
    print(f"🚀 开始发送邮件...")
    print(f"   收件人: {receiver}")
    print(f"   邮件数据: {email_jsonl_file}")
    print(f"   占位符: {placeholder_file_path}")

    # 加载邮件内容
    emails_data: List[dict] = []
    with open(email_jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                emails_data.append(json.loads(line))
            except Exception:
                continue

    def _normalize_name(name: str) -> str:
        import re
        n = name or ""
        n = re.sub(r"[._-]+", " ", n)
        n = re.sub(r"\d+", "", n)
        n = re.sub(r"[^A-Za-z\s]", "", n)
        n = re.sub(r"\s+", " ", n).strip().lower()
        return n

    total_senders = len(accounts_to_clean)
    success_count = 0
    skipped_same_addr = 0
    no_match_count = 0

    temp_dir = (Path(__file__).parent / ".." / "temp_send").resolve()
    temp_dir.mkdir(parents=True, exist_ok=True)

    for idx, account in enumerate(accounts_to_clean, 1):
        sender_email = account.get("email")
        sender_password = account.get("password", "")
        sender_display = account.get("name", sender_email)

        # 跳过发件人与收件人相同
        if sender_email == receiver:
            print(f"\n↪️  [{idx}/{total_senders}] 跳过：发件人与收件人相同 -> {sender_email}")
            skipped_same_addr += 1
            continue

        candidates = set()
        candidates.add(_normalize_name(sender_display))
        local_part = (sender_email.split('@', 1)[0] if sender_email else "")
        candidates.add(_normalize_name(local_part))

        # 查找匹配的唯一邮件
        match_item = None
        for item in emails_data:
            sender_name_in_mail = item.get('sender_name')
            if _normalize_name(sender_name_in_mail) in candidates:
                match_item = item
                break

        if not match_item:
            print(f"\n⚠️  [{idx}/{total_senders}] 未找到匹配内容：发件人账户={sender_email}")
            no_match_count += 1
            continue

        # 写入临时jsonl，仅含该邮件
        tmp_jsonl = temp_dir / f"{sender_email.replace('@','_at_').replace('.', '_')}.jsonl"
        with open(tmp_jsonl, 'w', encoding='utf-8') as tf:
            tf.write(json.dumps(match_item, ensure_ascii=False) + "\n")

        print(f"\n➡️  [{idx}/{total_senders}] 从 {sender_email} ({sender_display}) 发送到 {receiver}")
        try:
            asyncio.run(run_command(
                f"timeout 60s uv run {send_email_path} -s {sender_email} "
                f"-p '{sender_password}' "
                f"-r {receiver} "
                f"-j {tmp_jsonl} "
                f"--delay 0.2 "
                f"--placeholder {placeholder_file_path} "
                f"--no-confirm",
                debug=True,
                show_output=True
            ))
            success_count += 1
        except Exception as e:
            print(f"❌ 发送失败: 发件人={sender_email}, 错误={e}")

    # 统一结果输出
    print(
        f"运行结果: 成功={success_count>0 and (success_count + no_match_count + skipped_same_addr)==total_senders}, "
        f"已发送账户数={success_count}/{total_senders}, 跳过同址={skipped_same_addr}, 无匹配内容={no_match_count}, 收件人={receiver}"
    )
    
    # 等待直到所有邮件都已收到
    print("等待10s以便邮件接收完成...")
    sleep(10)

    
    print("已通过发送邮件构建初始状态！")