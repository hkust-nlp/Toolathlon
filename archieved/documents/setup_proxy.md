## 如何terminal中配置代理
由于各开发者本地环境不同，具体细节还需要自行配置，遇到问题时可多谷歌或使用大模型寻找答案
### Mac OS
#### 创建代理开关函数 (推荐)

在配置文件（~/.bashrc）中添加便捷的开关函数(直接vim打开后复制在文件末尾，然后wq!保存)：

```bash
# 开启代理
function proxy_on() {
    export http_proxy=http://127.0.0.1:7890
    export HTTP_PROXY=http://127.0.0.1:7890
    export https_proxy=$http_proxy
    export HTTPS_PROXY=$http_proxy
    export all_proxy=socks5://127.0.0.1:7891
    export no_proxy=localhost,127.0.0.1,localaddress,.localdomain.com
    echo "代理已开启"
}

# 关闭代理
function proxy_off() {
    unset http_proxy
    unset https_proxy
    unset all_proxy
    unset HTTP_PROXY
    unset HTTPS_PROXY
    unset ALL_PROXY
    echo "代理已关闭"
}

# 查看当前代理状态
function proxy_status() {
    echo "http_proxy: $http_proxy"
    echo "HTTP_PROXY: $HTTP_PROXY"
    echo "https_proxy: $https_proxy"
    echo "HTTPS_PROXY: $HTTPS_PROXY"
    echo "all_proxy: $all_proxy"
    echo "no_proxy: $no_proxy"
}
```

**使配置生效**
```bash
# 对于 zsh
source ~/.zshrc

# 对于 bash
source ~/.bash_profile
```

**使用方法**
```bash
proxy_on      # 开启代理
proxy_off     # 关闭代理
proxy_status  # 查看代理状态
```

### Windows
#### 临时使用 (每次打开cmd新窗口后都要重新设置)

```
set http_proxy=http://127.0.0.1:7890
set https_proxy=http://127.0.0.1:7890
set all_proxy=socks5://127.0.0.1:7891
set no_proxy=localhost,127.0.0.1,localaddress,.localdomain.com
```
```
echo %http_proxy%
echo %https_proxy%
```
---------------
#### 验证代理是否生效 （对mac/windows通用）

```bash
# 测试 Google 连接
curl https://www.google.com （不开代理时应该无法返回任何内容）
```

#### 注意事项

1. **端口号**：上述示例中的 `7890`、`7891` 需要替换为你实际的代理端口，**请参看你所使用的代理软件，如clash，通常会向你展示所用的端口号**
2. **代理地址**：如果代理不在本机，将 `127.0.0.1` 替换为代理服务器地址
3. **认证代理**：如需认证，格式为 `http://username:password@proxy_host:port`
4. **大小写**：某些程序只识别小写环境变量，某些只识别大写，建议都设置