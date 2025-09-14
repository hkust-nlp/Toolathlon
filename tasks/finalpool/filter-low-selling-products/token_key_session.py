from addict import Dict
import os

all_token_key_session = Dict(
    # WooCommerce配置
    woocommerce_api_key = "ck_woocommerce_token_Vgarcia128jr",
    woocommerce_api_secret = "cs_woocommerce_token_Vgarcia128jr",
    woocommerce_site_url = "http://localhost:10003/store82",
    
    # 邮件配置 (poste/emails)
    emails_config_file = os.path.join(os.path.dirname(__file__), "emails_config.json"),
    
    # 邮件服务器配置 (如果需要直接配置)
    email_smtp_server = "localhost",
    email_imap_server = "localhost",
    email_imap_port = 1143,
    email_smtp_port = 1587,
    email_username = "vgarcia@mcp.com",
    email_password = "Vgarcia128jr",
    email_from_address = "vgarcia@mcp.com",
    email_from_name = "Store82 Team",
)