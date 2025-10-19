### NPM/NPX常见问题

> 代理相关问题

将npm命令传入python程序在其内部运行时，外部设置的代理似乎不起作用，此时需要通过npm提供的接口设置其默认代理

#### 设置HTTP代理
npm config set proxy http://your-proxy-address:port

#### 设置HTTPS代理
npm config set https-proxy http://your-proxy-address:port

#### 如果需要认证的代理
npm config set proxy http://username:password@proxy-address:port
npm config set https-proxy http://username:password@proxy-address:port

#### 查看当前npm代理设置
npm config get proxy
npm config get https-proxy

#### 删除代理设置
npm config delete proxy
npm config delete https-proxy

> npx包的安装问题 （以MCP官方实现的文件系统为例）

一般来说，npx包是随用随装，每次用完会自动删除，下次再用会重新安装。

```
npx some-package
```

为避免每次安装的时间开销，可以先安装在 全局/本地项目， 具体见如下

全局安装
```
# 设置全局安装路径
npm config set prefix '/your/custom/path'

# 全局安装包
npm install -g @modelcontextprotocol/server-filesystem

# 使用已安装的包
npx --no-install @modelcontextprotocol/server-filesystem ./sample_files
```

本地安装
```
# 进入特定项目目录
cd /path/to/your/project

# 在该目录中本地安装包
npm install @modelcontextprotocol/server-filesystem

# 使用本地安装的包
npx --no-install @modelcontextprotocol/server-filesystem ./sample_files
```


可以通过以下方式确认包的安装位置
```
# 检查是否全局安装
npm list -g @modelcontextprotocol/server-filesystem

# 检查是否本地安装
npm list @modelcontextprotocol/server-filesystem

# 查看包的可执行文件位置
which npx  # 在Linux/macOS上
where npx  # 在Windows上

# 增加 npx 的调试信息
NPX_DEBUG=1 npx --no-install @modelcontextprotocol/server-filesystem ./sample_files
```