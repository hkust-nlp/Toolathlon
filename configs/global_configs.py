# 请将该文件填写上实际内容后，复制一份，去掉_example的后缀
# _ds后缀代表这是用于deepseek model的
from addict import Dict
global_configs = Dict(
    proxy='', # 如果是使用自己购买的代理，见FAQs/setup_proxy.md以获取你当前使用的代理url，一般是http://127.0.0.1:port
    proxy_backup='', # 有一些服务器需要另一个代理
    base_url_ds="", # 使用aihubmix时此项不填
    base_url_non_ds="https://aihubmix.com/v1", # 填写aihubmix的url
    ds_key="", # 使用aihubmix时此项不填
    non_ds_key= "sk-UBbKO40bAotY5ss3DaC4D0A940Bf49D4B3Ed0dB6Ac12B0D1", # 填写aihubmix的key
)
