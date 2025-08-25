远端账号

- google account x 1
- github account x 1 -> github token
- linkedin account x 1 -> email and password
- wandb account x 1 -> wandb token
- notion account x 1 -> ???
- snowflake account x 1 -> ???
- huggingface account x 1 -> hf token

=======
Google
username mcptest0606@gmail.com
password MCPtest0606!!

Github
username mcptest-user
password MCPtest0606!!

Linkedin
email mcptest0606@gmail.com
password MCPtest0606!!

Wandb
login via google

Notion
login via google

Snowflake
mcptest0606
MCPtest0606!!!

Huggingface
username mcptest0606@gmail.com
password MCPtest0606!!

// Two auxliary google accounts 👇
username mcpllm.bench@gmail.com
password T1wQS843xeGrnkn
app password ikby ivzj sfwn bydu

username kewincpt93@gmail.com
password kewincpt-9393
app password xjxw qdjs bgln njgb //
==========


本地账号
- 500个固定邮箱 configs/users_data.json
可用于poste邮件服务(默认前100个), canvas服务（默认前100个），woocommerce服务(默认第81-100个)

- poste 服务 管理员
email: mcpposte_admin@mcp.com
password: mcpposte

- canvas 服务 管理员
email: canvas@example.edu
password: canvas-docker
token: canvas-docker

追加三个管理员
    to yz
  📧 Email: mcpcanvasadmin1@mcp.com
  🔑 Password: mcpcanvasadminpass1
  🎫 Token: mcpcanvasadmintoken1
  👤 Role: admin
    
    to xc
  📧 Email: mcpcanvasadmin2@mcp.com
  🔑 Password: mcpcanvasadminpass2
  🎫 Token: mcpcanvasadmintoken2
  👤 Role: admin

    to hz
  📧 Email: mcpcanvasadmin3@mcp.com
  🔑 Password: mcpcanvasadminpass3
  🎫 Token: mcpcanvasadmintoken3
  👤 Role: admin

- woocommerce 服务 管理员
email: woocommerce@mcp.com
username: mcpwoocommerce
password: mcpwoocommerce
consumer_key: ck_woocommerce_token_admin
consumer_secret: cs_woocommerce_token_admin




账号注册及配置指南
1. google cloud project

1.1 你需要有一个谷歌账户（推荐新注册一个）

1.2 在该账号的谷歌云控制台启动一个gcp

1.3 启动如下api
```
YouTube Data API v3
Gmail API
Google Sheets API
Google Calendar API
Google Drive API
Google Forms API
Analytics Hub API					
BigQuery API					
BigQuery Connection API					
BigQuery Data Policy API					
BigQuery Migration API					
BigQuery Reservation API					
BigQuery Storage API					
Cloud Dataplex API					
Cloud Datastore API					
Cloud Logging API					
Cloud Monitoring API					
Cloud OS Login API					
Cloud SQL					
Cloud Storage					
Cloud Storage API					
Cloud Trace API					
Compute Engine API					
Custom Search API					
Dataform API					
Directions API					
Distance Matrix API					
Drive Activity API					
Google Cloud APIs					
Google Cloud Storage JSON API					
Google Docs API					
Google Slides API					
Maps Grounding API					
Places API					
Privileged Access Manager API					
Routes API					
Service Management API					
Service Usage API
```
1.4 Oauth2.0认证

- Go to "APIs & Services" > "Credentials"
- Click "Create Credentials" > "OAuth client ID"
- Choose "Web application" as application type
- Give it a name and click "Create"
- For Web application, add http://localhost:3000/oauth2callback to the authorized redirect URIs
- Download the JSON file of your client's OAuth keys
- Rename the key file to gcp-oauth.keys.json
- please it to `configs/gcp-oauth.keys.json`

1.5 生成credentials
```
uv run install_records/create_google_credentials.py
```
根据提示操作即可，若PC浏览器不跳转，可复制链接地址到移动端获取所需内容
会自动根据1.4中的`configs/gcp-oauth.keys.json`生成`configs/google_credentials.json`

2. 获取google map api凭据
https://developers.google.com/maps/documentation/javascript/get-api-key?hl=zh-cn&setupProd=configure#create-api-keys

3. TBD