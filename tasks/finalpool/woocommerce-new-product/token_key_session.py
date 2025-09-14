from addict import Dict
import os

all_token_key_session = Dict(
    # WooCommerce配置 - 恢复原有的工作API密钥
    woocommerce_api_key = "ck_woocommerce_token_walkers147a",
    woocommerce_api_secret = "cs_woocommerce_token_walkers147a",
    woocommerce_site_url = "http://localhost:10003/store97",

    # 管理员账号信息（备用）
    woocommerce_admin_email = "woocommerce@mcp.com",
    woocommerce_admin_username = "mcpwoocommerce",
    woocommerce_admin_password = "mcpwoocommerce",
    woocommerce_admin_key = "ck_woocommerce_token_admin",
    woocommerce_admin_secret = "cs_woocommerce_token_admin",

    # 邮件配置 (poste/emails)
    emails_config_file = os.path.join(os.path.dirname(__file__), "emails_config.json"),

)


