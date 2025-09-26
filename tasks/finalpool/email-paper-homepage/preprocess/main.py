from re import A
import sys
import os
from argparse import ArgumentParser
import json
import random
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import asyncio
from pathlib import Path
from utils.general.helper import read_json
# Add utils to path
sys.path.append(os.path.dirname(__file__))
from configs.token_key_session import all_token_key_session as global_token_key_session
# from utils.app_specific.notion_page_duplicator import NotionPageDuplicator
from utils.general.helper import print_color, fork_repo, forked_repo_to_independent
from utils.app_specific.github.helper_funcs import get_user_name
from utils.app_specific.poste.local_email_manager import LocalEmailManager

file_path = os.path.abspath(__file__)
EMAILS_CONFIG_FILE = os.path.join(os.path.dirname(file_path), "..", "emails_config.json")

RECEIVER_EMAIL_ADDR = read_json(EMAILS_CONFIG_FILE)['email']
GITHUB_TOKEN = global_token_key_session.github_token
READONLY = False
FORKING_LIST = [
    # source repo, fork_default_branch_only
    ("Toolathlon-Archive/My-Homepage", True),
    ("Toolathlon-Archive/optimizing-llms-contextual-reasoning", True),
    ("Toolathlon-Archive/llm-adaptive-learning", True),
    ("Toolathlon-Archive/ipsum-lorem-all-you-need", True),
    ("Toolathlon-Archive/enhancing-llms", True),
]

def to_importable_emails_format(legacy_emails, receiver_email: str, today_file_path: str):
    """
    将 legacy 格式的邮件转换为可导入格式。

    规则：
    - 发件人统一为 <noreply@mcp.com>，显示名为原 sender_name
    - 最后一封邮件时间= today_file_path 中的时间；若仅有日期，则设为 18:00:00 UTC
    - 从后往前，每封邮件相对下一封随机减去 4-8 小时
    - 收件人统一为 receiver_email
    - message_id 形如 <email{email_id}@mcp.com>
    - 根据内容类型在 body_text/body_html 之间二选一，另一项为空串
    - 附件列表设为空
    """
    # 读取 today 基准时间
    today_text = None
    try:
        with open(today_file_path, "r", encoding="utf-8") as f:
            today_text = f.read().strip()
    except Exception:
        today_text = None

    base_dt = None
    if today_text:
        # 尝试解析完整 ISO；否则仅日期
        try:
            base_dt = datetime.fromisoformat(today_text)
            if base_dt.tzinfo is None:
                base_dt = base_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                # 仅日期
                y, m, d = [int(x) for x in today_text.split("-")]
                base_dt = datetime(y, m, d, 18, 0, 0, tzinfo=timezone.utc)
            except Exception:
                base_dt = None
    if base_dt is None:
        # 兜底：使用当前 UTC 时间
        base_dt = datetime.now(timezone.utc)

    # 随机种子固定（可复现）
    random.seed(42)

    total = len(legacy_emails)
    # 从最后一封开始累积时间
    timestamps = [None] * total
    if total > 0:
        timestamps[-1] = base_dt
        for i in range(total - 2, -1, -1):
            delta_hours = random.randint(4, 8)
            timestamps[i] = timestamps[i + 1] - timedelta(hours=delta_hours)

    def detect_is_html(content: str) -> bool:
        if not isinstance(content, str):
            return False
        lower = content.lower()
        return ("<html" in lower) or ("<body" in lower) or ("<p" in lower) or ("<div" in lower)

    emails_out = []
    for idx, item in enumerate(legacy_emails, start=1):
        email_id = str(idx)
        sender_name = item.get("sender_name", "")
        subject = item.get("subject", "")
        content = item.get("content", "")
        content_type = item.get("content_type", "auto")

        is_html = (content_type == "html") or (content_type == "auto" and detect_is_html(content))
        body_text = "" if is_html else content
        body_html = content if is_html else ""

        dt = timestamps[idx - 1] if total > 0 else base_dt
        rfc2822_date = format_datetime(dt)

        emails_out.append({
            "email_id": email_id,
            "subject": subject,
            "from_addr": f"{sender_name} <noreply@mcp.com>",
            "to_addr": receiver_email,
            "cc_addr": None,
            "bcc_addr": None,
            "date": rfc2822_date,
            "message_id": f"<email{email_id}@mcp.com>",
            "body_text": body_text,
            "body_html": body_html,
            "attachments": []
        })

    export = {
        "export_date": datetime.now(timezone.utc).isoformat(),
        "total_emails": total,
        "emails": emails_out
    }
    return export

async def import_emails_via_mcp(backup_file: str):
    """
    使用MCP emails server导入邮件
    """
    from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry, ToolCallError

    print(f"使用MCP emails server导入邮件...")

    agent_workspace = "./"
    mcp_manager = MCPServerManager(agent_workspace=agent_workspace, local_token_key_session={"emails_config_file": EMAILS_CONFIG_FILE})
    emails_server = mcp_manager.servers['emails']

    async with emails_server as server:
        try:
            result = await call_tool_with_retry(
                server,
                "import_emails",
                {
                    "import_path": backup_file,
                    "folder": "INBOX"
                }
            )

            if result.content:
                print(f"✅ Email import process completed: {result.content[0].text}")
                return True
            else:
                print(f"❌ Email import process failed: no return content")
                return False

        except ToolCallError as e:
            print(f"❌ Email import process failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Email import process failed: unknown error {e}")
            return False

async def prepare_one_repo(source_repo, target_repo, fork_default_branch_only, readonly):
    github_user = get_user_name(GITHUB_TOKEN)
    await fork_repo(source_repo, f"{github_user}/{target_repo}", fork_default_branch_only, readonly)
    tmpdir = Path(os.path.dirname(__file__)) / ".." / "tmp" / target_repo
    tmpdir.mkdir(parents=True, exist_ok=True)
    await forked_repo_to_independent(target_repo, str(tmpdir), False)

async def process_emails():
    # 初始化本地邮件管理器
    email_manager = LocalEmailManager(EMAILS_CONFIG_FILE, verbose=True)
    
    # 清理邮箱
    print("Mailbox clearing...")
    email_manager.clear_all_emails('INBOX')
    email_manager.clear_all_emails('Sent')

    email_jsonl_file = Path(__file__).parent / ".." / "files" / "emails.jsonl"
    placeholder_file_path = Path(__file__).parent / ".." / "files" / "placeholder_values.json"
    
    # 保存今天时间的文件路径
    today_file_path = Path(__file__).parent / ".." / "groundtruth_workspace" / "today.txt"
    
    # 加载邮件数据
    print("Loading emails...")
    legacy_format_emails = email_manager.load_emails_from_jsonl(
        str(email_jsonl_file), 
        str(placeholder_file_path),
        str(today_file_path)
    )

    # become emails import format!
    # the emails var is [{"sender_name","subject","content","content_type"}] 从上到下发送时间越来越晚

    # the desired format is , the sender should all be <noreply@mcp.com>
    # 最后一封邮件的发送时间应该是today_file_path的时间， 它的'email_id'也应该是最大的 = len(emails)
    # 然后从后往前，每个邮件的时间在上一个邮件的基础上随机4-8小时
    # 收件人都是 RECEIVER_EMAIL_ADDR
    # message_id 就是 <email{email_id}@mcp.com>
    # type 如果是 html, body_html就填上，否则空着一个""; type是text的话也同理

    # 最后我们要得到一个变量叫importable_format_emails 存在 importable_emails_file_path = Path(__file__).parent / ".." / "files" / "importable_emails.json"
    """
    {
  "export_date": "2025-09-15T19:01:19.793374",
  "total_emails": 18,
  "emails": [
    {
      "email_id": "1",
      "subject": "[COML 2025] Camera-ready instructions for accepted papers",
      "from_addr": "COML 2025 <noreply@mcp.com>",
      "to_addr": "jsmith@mcp.com",
      "cc_addr": null,
      "bcc_addr": null,
      "date": "Wed, 10 Sep 2025 18:31:19 +0000",
      "message_id": "<email1@mcp.com>",
      "body_text": "<html><body style=\"font-family: Arial, sans-serif; line-height: 1.6; color: #333;\"><p>Dear <strong>Dr. John Smith</strong>,</p><p><strong style=\"color: #2c5aa0;\">Congratulations on your accepted COML 2025 paper!</strong></p><p>The camera-ready submission is due on <strong>2025-09-19 (11:59pm AoE)</strong>. Please make sure to follow the steps below before this deadline to avoid your paper being withdrawn from COML. Detailed instructions are given below, with the main <strong>mandatory actions</strong> being the following:</p><ol><li>At least one author must register for the conference with the <strong>'Conference'</strong> option checked in the registration form; <em>'Virtual Pass' alone is not sufficient</em> (see item 4 below).</li><li>At least one author needs to digitally sign the publication consent form (see item 5 below)</li><li>The presenting author needs to digitally sign the consent form (see item 5 below).</li><li>The corresponding author needs to sign the PMLR publication agreement form and upload it in pdf format together with the camera-ready submission (see item 6 below). <em>(Note: Maximum file sizes 20MB)</em></li><li>Your camera-ready pdf should include a mandatory impact statement just before the bibliography (see the call for papers for instructions). Acknowledgments, the impact statement, and references are excluded from the 9 page limit.</li><li>Complete the camera-ready form on OpenReview (see items 7-10 below).</li></ol><p><strong>Please follow the guidelines below:</strong></p><ol><li>In the camera-ready version, you have an <strong>extra page</strong> to address reviewer comments, so the length limit of the paper body is <strong>9 pages</strong>, followed by any acknowledgements, the impact statement, and references.</li><li>You should include any appendices of the paper as part of the camera-ready pdf. There is <strong>NO</strong> camera-ready supplementary material of any kind, as these will not be listed on PMLR nor on OpenReview. If you have code or other material that you want the readers to have access to, please upload it to a repository (e.g., GitHub) and include a link in your paper. We also encourage you to include the url link to the code in the optional \"code url\" box on OpenReview – this will appear on the OpenReview entry of the paper as well as on PMLR.</li><li>You are allowed to change the author order on the camera-ready submission page, but <strong>no author additions are allowed</strong>. You are also allowed to change the title and abstract slightly. If you want to change the title significantly with a good reason (for instance, it was suggested by the meta reviewer), then you should get permission from the program chairs.</li><li><strong>Register for the conference:</strong> go to <a href=\"https://coml.cc\">coml.cc</a> and click \"Registration 2025\". From there, you can log in if you have an existing profile, or create a new profile. At least one author must register with the checkbox <strong>'Conference'</strong> ticked under the 'Sessions' list in the registration form; selecting 'Virtual Pass' alone is <strong>not sufficient</strong>.</li><li>At least one author needs to digitally sign the <strong>COML 2025 Publishing Release form</strong>, and the presenting author needs to sign the <strong>COML 2025 Recording Release and License form</strong>, both at <a href=\"https://coml.cc/ConsentForm\">https://coml.cc/ConsentForm</a> (you will need to log in to coml.cc to see your paper(s)).</li><li>The <strong>PMLR Publication Agreement form</strong> (available at <a href=\"http://proceedings.mlr.press/pmlr-license-agreement.pdf\">http://proceedings.mlr.press/pmlr-license-agreement.pdf</a>) should be filled and signed by the corresponding author and uploaded as part of the camera-ready form.</li><li>The camera-ready version should be prepared using the LaTeX style file from <a href=\"https://media.coml.cc/Conferences/COML2025/Styles/coml2025.zip\">https://media.coml.cc/Conferences/COML2025/Styles/coml2025.zip</a> with the <code>\\usepackage[accepted]{coml2025}</code> option. Please note that for camera-ready there is a <strong>mandatory impact statement</strong> in an unnumbered section just before the bibliography. Acknowledgments can also optionally be included in another unnumbered section. Both Acknowledgments and Impact Statement are excluded from the 9-page limit.</li><li>Check the pdf file of your paper with the <strong>COML format checker</strong>. Read the instructions at <a href=\"https://papercheck.coml.cc/papercheck.html\">https://papercheck.coml.cc/papercheck.html</a>, and upload your camera-ready paper for automatic checking of the guidelines (if there are errors, you can upload again until all detected violations are resolved). Upon successful completion of the paper checker, you will obtain a <strong>5-letter submission code</strong> which you will enter in the camera-ready form.</li><li>Upload the required files to the camera-ready form, which you can access via your OpenReview console. Enter your title and abstract in the camera-ready form, exactly matching the paper. You can use TeX math (we suggest sparingly), but no custom macros or other TeX commands. Please make sure that accents, special characters, etc., are entered using TeX commands and not using non-English characters.</li><li><strong style=\"color: #d9534f;\">New this year</strong>, you will be asked to enter a \"lay summary\" of your paper (also called \"plain language summary\") in the OpenReview form. See <a href=\"https://medium.com/@coml2025pc/lay-summaries-at-coml-2025-8d15e395b7f3\">https://medium.com/@coml2025pc/lay-summaries-at-coml-2025-8d15e395b7f3</a> for additional guidelines and examples.</li></ol><p><strong style=\"color: #d9534f;\">Please do not wait until the last day</strong>, as fixes might require some time. Pay special attention to the following:</p><ul><li>The main paper itself must contain no more than <strong>9 pages</strong> (note the extra page compared to the length at submission time). Acknowledgements, impact statement, references, and appendices should follow the main paper in the same pdf file.</li><li>Enter author details as in the TeX file (<code>example_paper.tex</code> in <code>coml2025_style.zip</code> in step 7 above). Check that the affiliations footnote renders correctly. Make sure you have called <code>\\printAffiliationsAndNotice{\\comlEqualContribution}</code> if multiple authors have made equal contributions, or <code>\\printAffiliationsAndNotice{}</code> otherwise (see comments in the file <code>example_paper.tex</code> near line 113).</li><li>The title and section headings should have content words capitalized, not all caps. For instance, \"Deep Learning for Artificial Intelligence\", and not \"DEEP LEARNING FOR ARTIFICIAL INTELLIGENCE\". For further guidance on capitalization rules, please see here: <a href=\"https://grammar.yourdictionary.com/capitalization/rules-for-capitalization-in-titles.html\">https://grammar.yourdictionary.com/capitalization/rules-for-capitalization-in-titles.html</a>.</li><li>Carefully check your references and replace arXiv citations with peer-reviewed papers where possible (arXiv is generally not peer-reviewed). Please also check that capitalization in your references appears as you intended (for example, use braces like <code>{Markov}</code> in Bibtex entries to make sure that Markov (proper name) keeps its capitalization in the reference).</li><li>We kindly ask all authors to follow our guidelines for writing accessible papers. In particular, we expect that authors (1) review guidelines for accessibility to color-blind and visually impaired; (2) ensure their bibliography is up-to-date, including up-to-date names and venues; (3) use inclusive and respectful language throughout when talking about people.</li><li>This year, there is no Type 3 font check, so you do not have to use TrueType font to pass the check or convert eps figures to png figures to bypass the check. If possible, please use vector graphics (eps or pdf figures) for experimental results such as line plots and bar plots to maximize readability, and only use bitmap graphics for certain illustrations and visualizations that cannot be easily represented by vector graphics.</li><li>Abstracts should be a single paragraph and ideally <strong>4-6 sentences</strong>.</li><li>The citation font size should be the same as that in the main body of the paper.</li><li>Your paper must be in <strong>US letter size</strong> (i.e., not A4 or other sizes).</li><li>Full paper (including appendices) in pdf format (max size <strong>20 MB</strong>; please reduce the size/quality of large images if you exceed this).</li><li>Publication agreement form (max size <strong>10 MB</strong>).</li><li>Please double-check the order of authors in OpenReview to make sure it is consistent with that in the camera-ready version.</li></ul><p>After this year's conference, there will be another window where you may upload small corrections to the paper following the feedback received at the conference. More information on this will follow after the conference.</p><p>If you experience any problems, please email the publication chairs at: <a href=\"mailto:coml2025publication@gmail.com\">coml2025publication@gmail.com</a></p><p>Thank you again for working with us through this process; we look forward to seeing you in July.</p><p>Sincerely,</p><p><strong>Dr. Sarah Chen and Prof. Michael Rodriguez</strong>, COML 2025 Publications Chairs<br><strong>Prof. Emily Wang, Dr. James Kim, Prof. Lisa Thompson and Dr. Robert Davis</strong>, COML 2025 Program Chairs</p></body></html>",
      "body_html": "<html><body style=\"font-family: Arial, sans-serif; line-height: 1.6; color: #333;\"><p>Dear <strong>Dr. John Smith</strong>,</p><p><strong style=\"color: #2c5aa0;\">Congratulations on your accepted COML 2025 paper!</strong></p><p>The camera-ready submission is due on <strong>2025-09-19 (11:59pm AoE)</strong>. Please make sure to follow the steps below before this deadline to avoid your paper being withdrawn from COML. Detailed instructions are given below, with the main <strong>mandatory actions</strong> being the following:</p><ol><li>At least one author must register for the conference with the <strong>'Conference'</strong> option checked in the registration form; <em>'Virtual Pass' alone is not sufficient</em> (see item 4 below).</li><li>At least one author needs to digitally sign the publication consent form (see item 5 below)</li><li>The presenting author needs to digitally sign the consent form (see item 5 below).</li><li>The corresponding author needs to sign the PMLR publication agreement form and upload it in pdf format together with the camera-ready submission (see item 6 below). <em>(Note: Maximum file sizes 20MB)</em></li><li>Your camera-ready pdf should include a mandatory impact statement just before the bibliography (see the call for papers for instructions). Acknowledgments, the impact statement, and references are excluded from the 9 page limit.</li><li>Complete the camera-ready form on OpenReview (see items 7-10 below).</li></ol><p><strong>Please follow the guidelines below:</strong></p><ol><li>In the camera-ready version, you have an <strong>extra page</strong> to address reviewer comments, so the length limit of the paper body is <strong>9 pages</strong>, followed by any acknowledgements, the impact statement, and references.</li><li>You should include any appendices of the paper as part of the camera-ready pdf. There is <strong>NO</strong> camera-ready supplementary material of any kind, as these will not be listed on PMLR nor on OpenReview. If you have code or other material that you want the readers to have access to, please upload it to a repository (e.g., GitHub) and include a link in your paper. We also encourage you to include the url link to the code in the optional \"code url\" box on OpenReview – this will appear on the OpenReview entry of the paper as well as on PMLR.</li><li>You are allowed to change the author order on the camera-ready submission page, but <strong>no author additions are allowed</strong>. You are also allowed to change the title and abstract slightly. If you want to change the title significantly with a good reason (for instance, it was suggested by the meta reviewer), then you should get permission from the program chairs.</li><li><strong>Register for the conference:</strong> go to <a href=\"https://coml.cc\">coml.cc</a> and click \"Registration 2025\". From there, you can log in if you have an existing profile, or create a new profile. At least one author must register with the checkbox <strong>'Conference'</strong> ticked under the 'Sessions' list in the registration form; selecting 'Virtual Pass' alone is <strong>not sufficient</strong>.</li><li>At least one author needs to digitally sign the <strong>COML 2025 Publishing Release form</strong>, and the presenting author needs to sign the <strong>COML 2025 Recording Release and License form</strong>, both at <a href=\"https://coml.cc/ConsentForm\">https://coml.cc/ConsentForm</a> (you will need to log in to coml.cc to see your paper(s)).</li><li>The <strong>PMLR Publication Agreement form</strong> (available at <a href=\"http://proceedings.mlr.press/pmlr-license-agreement.pdf\">http://proceedings.mlr.press/pmlr-license-agreement.pdf</a>) should be filled and signed by the corresponding author and uploaded as part of the camera-ready form.</li><li>The camera-ready version should be prepared using the LaTeX style file from <a href=\"https://media.coml.cc/Conferences/COML2025/Styles/coml2025.zip\">https://media.coml.cc/Conferences/COML2025/Styles/coml2025.zip</a> with the <code>\\usepackage[accepted]{coml2025}</code> option. Please note that for camera-ready there is a <strong>mandatory impact statement</strong> in an unnumbered section just before the bibliography. Acknowledgments can also optionally be included in another unnumbered section. Both Acknowledgments and Impact Statement are excluded from the 9-page limit.</li><li>Check the pdf file of your paper with the <strong>COML format checker</strong>. Read the instructions at <a href=\"https://papercheck.coml.cc/papercheck.html\">https://papercheck.coml.cc/papercheck.html</a>, and upload your camera-ready paper for automatic checking of the guidelines (if there are errors, you can upload again until all detected violations are resolved). Upon successful completion of the paper checker, you will obtain a <strong>5-letter submission code</strong> which you will enter in the camera-ready form.</li><li>Upload the required files to the camera-ready form, which you can access via your OpenReview console. Enter your title and abstract in the camera-ready form, exactly matching the paper. You can use TeX math (we suggest sparingly), but no custom macros or other TeX commands. Please make sure that accents, special characters, etc., are entered using TeX commands and not using non-English characters.</li><li><strong style=\"color: #d9534f;\">New this year</strong>, you will be asked to enter a \"lay summary\" of your paper (also called \"plain language summary\") in the OpenReview form. See <a href=\"https://medium.com/@coml2025pc/lay-summaries-at-coml-2025-8d15e395b7f3\">https://medium.com/@coml2025pc/lay-summaries-at-coml-2025-8d15e395b7f3</a> for additional guidelines and examples.</li></ol><p><strong style=\"color: #d9534f;\">Please do not wait until the last day</strong>, as fixes might require some time. Pay special attention to the following:</p><ul><li>The main paper itself must contain no more than <strong>9 pages</strong> (note the extra page compared to the length at submission time). Acknowledgements, impact statement, references, and appendices should follow the main paper in the same pdf file.</li><li>Enter author details as in the TeX file (<code>example_paper.tex</code> in <code>coml2025_style.zip</code> in step 7 above). Check that the affiliations footnote renders correctly. Make sure you have called <code>\\printAffiliationsAndNotice{\\comlEqualContribution}</code> if multiple authors have made equal contributions, or <code>\\printAffiliationsAndNotice{}</code> otherwise (see comments in the file <code>example_paper.tex</code> near line 113).</li><li>The title and section headings should have content words capitalized, not all caps. For instance, \"Deep Learning for Artificial Intelligence\", and not \"DEEP LEARNING FOR ARTIFICIAL INTELLIGENCE\". For further guidance on capitalization rules, please see here: <a href=\"https://grammar.yourdictionary.com/capitalization/rules-for-capitalization-in-titles.html\">https://grammar.yourdictionary.com/capitalization/rules-for-capitalization-in-titles.html</a>.</li><li>Carefully check your references and replace arXiv citations with peer-reviewed papers where possible (arXiv is generally not peer-reviewed). Please also check that capitalization in your references appears as you intended (for example, use braces like <code>{Markov}</code> in Bibtex entries to make sure that Markov (proper name) keeps its capitalization in the reference).</li><li>We kindly ask all authors to follow our guidelines for writing accessible papers. In particular, we expect that authors (1) review guidelines for accessibility to color-blind and visually impaired; (2) ensure their bibliography is up-to-date, including up-to-date names and venues; (3) use inclusive and respectful language throughout when talking about people.</li><li>This year, there is no Type 3 font check, so you do not have to use TrueType font to pass the check or convert eps figures to png figures to bypass the check. If possible, please use vector graphics (eps or pdf figures) for experimental results such as line plots and bar plots to maximize readability, and only use bitmap graphics for certain illustrations and visualizations that cannot be easily represented by vector graphics.</li><li>Abstracts should be a single paragraph and ideally <strong>4-6 sentences</strong>.</li><li>The citation font size should be the same as that in the main body of the paper.</li><li>Your paper must be in <strong>US letter size</strong> (i.e., not A4 or other sizes).</li><li>Full paper (including appendices) in pdf format (max size <strong>20 MB</strong>; please reduce the size/quality of large images if you exceed this).</li><li>Publication agreement form (max size <strong>10 MB</strong>).</li><li>Please double-check the order of authors in OpenReview to make sure it is consistent with that in the camera-ready version.</li></ul><p>After this year's conference, there will be another window where you may upload small corrections to the paper following the feedback received at the conference. More information on this will follow after the conference.</p><p>If you experience any problems, please email the publication chairs at: <a href=\"mailto:coml2025publication@gmail.com\">coml2025publication@gmail.com</a></p><p>Thank you again for working with us through this process; we look forward to seeing you in July.</p><p>Sincerely,</p><p><strong>Dr. Sarah Chen and Prof. Michael Rodriguez</strong>, COML 2025 Publications Chairs<br><strong>Prof. Emily Wang, Dr. James Kim, Prof. Lisa Thompson and Dr. Robert Davis</strong>, COML 2025 Program Chairs</p></body></html>",
      "is_read": false,
      "is_important": false,
      "folder": "INBOX",
      "attachments": []
    },...
    ]
    }
    """

    importable_format_emails = to_importable_emails_format(
        legacy_emails=legacy_format_emails,
        receiver_email=RECEIVER_EMAIL_ADDR,
        today_file_path=str(today_file_path)
    )

    importable_emails_file_path = Path(__file__).parent / ".." / "files" / "importable_emails.json"
    importable_emails_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(importable_emails_file_path, "w", encoding="utf-8") as f:
        json.dump(importable_format_emails, f, ensure_ascii=False, indent=2)
    print_color(f"Saved importable emails to {importable_emails_file_path}", "green")

    return importable_emails_file_path

async def main():
    parser = ArgumentParser(description="Example code for notion tasks preprocess")
    parser.add_argument("--agent_workspace", required=False, 
                       help="Agent workspace path")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    # 用协程并发多个fork_repo && form2independent
    # 从source_repo自动解析新的target_repo名称

    real_forking_list = []
    for source_repo, fork_default_branch_only in FORKING_LIST:
        target_repo = source_repo.split("/")[1]
        real_forking_list.append((source_repo, target_repo, fork_default_branch_only, READONLY))

    tasks = [prepare_one_repo(source_repo, target_repo, fork_default_branch_only, readonly) for source_repo, target_repo, fork_default_branch_only, readonly in real_forking_list]
    await asyncio.gather(*tasks)

    print_color("Forking and becoming independent for all repos successfully!","green")

    importable_emails_file_path = await process_emails()

    await import_emails_via_mcp(importable_emails_file_path)

if __name__ == "__main__":
    asyncio.run(main())

