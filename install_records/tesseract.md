# Tesseract AppImage 安装指南

本指南介绍如何在没有sudo权限的Linux系统上安装Tesseract 5.5.1 AppImage版本。

**TLDR 你可以直接跳到最后，有一个一键安装脚本**

**默认只安装了英文的语言包，不确定能不能用中文的**

## 目录
1. [准备工作](#准备工作)
2. [下载和安装](#下载和安装)
3. [创建包装脚本](#创建包装脚本)
4. [安装语言数据包](#安装语言数据包)
5. [配置环境变量](#配置环境变量)
6. [验证安装](#验证安装)
7. [Python集成](#python集成)
8. [故障排除](#故障排除)

## 准备工作

### 确定安装路径
本指南使用 `/ssddata/{username}` 作为基础路径。请将 `{username}` 替换为你的实际用户名。

### 检查shell类型
```bash
echo $SHELL
```

## 下载和安装

### 步骤1：创建目录并下载AppImage

```bash
# 创建目录
mkdir -p /ssddata/{username}/local/bin
cd /ssddata/{username}/local/bin

# 下载 Tesseract 5.5.1 AppImage
wget https://github.com/AlexanderP/tesseract-appimage/releases/download/v5.5.1/tesseract-5.5.1-x86_64.AppImage

# 给文件添加执行权限
chmod +x tesseract-5.5.1-x86_64.AppImage

# 验证文件
ls -la tesseract-5.5.1-x86_64.AppImage
```

期望输出：文件大小约34MB，权限为 `-rwx------`

### 步骤2：测试AppImage

```bash
# 直接运行AppImage查看版本
./tesseract-5.5.1-x86_64.AppImage --version

# 查看帮助信息
./tesseract-5.5.1-x86_64.AppImage --help | head -10
```

期望输出：
- 版本信息显示 `tesseract 5.5.1`
- 包含各种库的版本信息（leptonica, libgif等）

**注意**：AppImage运行时会临时解压到 `/tmp/.mount_XXX` 目录，这是正常现象。

## 创建包装脚本

### 步骤3：创建便捷的包装脚本

```bash
# 确保在正确目录
cd /ssddata/{username}/local/bin

# 创建名为 tesseract 的包装脚本
cat > tesseract << 'EOF'
#!/bin/bash
# Tesseract 5.5.1 AppImage 包装脚本
exec "/ssddata/{username}/local/bin/tesseract-5.5.1-x86_64.AppImage" "$@"
EOF

# 替换{username}为实际用户名
sed -i 's/{username}/你的实际用户名/g' tesseract

# 给脚本添加执行权限
chmod +x tesseract

# 测试包装脚本
./tesseract --version | head -1
```

## 安装语言数据包

### 步骤4：下载语言数据文件

由于AppImage的临时挂载特性，我们需要将语言数据放在固定位置：

```bash
# 创建语言数据目录
mkdir -p /ssddata/{username}/local/share/tessdata

# 切换到该目录
cd /ssddata/{username}/local/share/tessdata

# 下载英文语言包
wget https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata

# 下载中文简体语言包（可选）
wget https://github.com/tesseract-ocr/tessdata/raw/main/chi_sim.traineddata

# 查看下载的文件
ls -la
```

期望文件大小：
- `eng.traineddata`: 约 23MB
- `chi_sim.traineddata`: 约 44MB

## 配置环境变量

### 步骤5：设置环境变量

根据你的shell类型选择相应的配置方法：

#### Bash用户
```bash
echo '' >> ~/.bashrc
echo '# Tesseract configuration' >> ~/.bashrc
echo 'export PATH="/ssddata/{username}/local/bin:$PATH"' >> ~/.bashrc
echo 'export TESSDATA_PREFIX="/ssddata/{username}/local/share/tessdata"' >> ~/.bashrc
source ~/.bashrc
```

#### Zsh用户（包括Oh My Zsh）
```bash
echo '' >> ~/.zshrc
echo '# Tesseract configuration' >> ~/.zshrc
echo 'export PATH="/ssddata/{username}/local/bin:$PATH"' >> ~/.zshrc
echo 'export TESSDATA_PREFIX="/ssddata/{username}/local/share/tessdata"' >> ~/.zshrc
source ~/.zshrc
```

#### Tcsh/Csh用户
```bash
echo '' >> ~/.cshrc
echo '# Tesseract configuration' >> ~/.cshrc
echo 'setenv PATH /ssddata/{username}/local/bin:${PATH}' >> ~/.cshrc
echo 'setenv TESSDATA_PREFIX /ssddata/{username}/local/share/tessdata' >> ~/.cshrc
source ~/.cshrc
```

#### Fish用户
```bash
echo '' >> ~/.config/fish/config.fish
echo '# Tesseract configuration' >> ~/.config/fish/config.fish
echo 'set -gx PATH /ssddata/{username}/local/bin $PATH' >> ~/.config/fish/config.fish
echo 'set -gx TESSDATA_PREFIX /ssddata/{username}/local/share/tessdata' >> ~/.config/fish/config.fish
source ~/.config/fish/config.fish
```

### 验证环境变量设置

```bash
# 验证PATH
echo $PATH | grep -o '/ssddata/{username}/local/bin'

# 验证TESSDATA_PREFIX
echo $TESSDATA_PREFIX

# 验证tesseract命令可用
which tesseract
```

## 验证安装

### 步骤6：测试OCR功能

```bash
# 1. 查看可用语言
tesseract --list-langs

# 2. 创建测试图片（使用Python）
python3 -c "
from PIL import Image, ImageDraw
img = Image.new('RGB', (200, 50), color='white')
d = ImageDraw.Draw(img)
d.text((10,10), 'Hello World 123', fill='black')
img.save('/tmp/test.png')
print('测试图片已创建: /tmp/test.png')
"

# 3. 执行OCR识别
cd /tmp
tesseract test.png output
cat output.txt

# 4. 测试中文识别（如果安装了中文包）
tesseract test.png output_chi -l chi_sim
```

## Python集成

### 使用pytesseract

```python
import pytesseract
import os

# 方法1：如果环境变量设置正确，直接使用
text = pytesseract.image_to_string('image.png')

# 方法2：显式指定路径（替换{username}）
pytesseract.pytesseract.tesseract_cmd = '/ssddata/{username}/local/bin/tesseract'
text = pytesseract.image_to_string('image.png')
```

### 创建Python包装类（推荐）

```python
# tesseract_wrapper.py
import os
import pytesseract

class TesseractWrapper:
    def __init__(self, username):
        self.base_path = f'/ssddata/{username}'
        self.tesseract_path = f'{self.base_path}/local/bin/tesseract'
        self.tessdata_path = f'{self.base_path}/local/share/tessdata'
        
        # 设置环境变量
        os.environ['TESSDATA_PREFIX'] = self.tessdata_path
        
        # 设置pytesseract路径
        if os.path.exists(self.tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
    
    def ocr(self, image_path, lang='eng'):
        return pytesseract.image_to_string(image_path, lang=lang)

# 使用示例
ocr = TesseractWrapper('your_username')
text = ocr.ocr('image.png')
```

## 故障排除

### 常见问题

1. **找不到tesseract命令**
   - 确保PATH环境变量设置正确
   - 使用完整路径：`/ssddata/{username}/local/bin/tesseract`

2. **语言数据找不到**
   ```bash
   export TESSDATA_PREFIX="/ssddata/{username}/local/share/tessdata"
   ```

3. **Permission denied错误**
   ```bash
   chmod +x /ssddata/{username}/local/bin/tesseract*
   ```

4. **AppImage相关错误**
   - 确保系统支持FUSE
   - 尝试提取AppImage：
   ```bash
   ./tesseract-5.5.1-x86_64.AppImage --appimage-extract
   ./squashfs-root/usr/bin/tesseract --version
   ```

### 诊断脚本

创建 `diagnose_tesseract.sh`：

```bash
#!/bin/bash
echo "=== Tesseract 安装诊断 ==="
echo ""
echo "1. Shell类型: $SHELL"
echo "2. PATH包含tesseract: $(echo $PATH | grep -c '/ssddata/{username}/local/bin')"
echo "3. TESSDATA_PREFIX: ${TESSDATA_PREFIX:-未设置}"
echo "4. Tesseract位置: $(which tesseract 2>/dev/null || echo '未找到')"
echo "5. AppImage文件: $(ls -la /ssddata/{username}/local/bin/tesseract*.AppImage 2>/dev/null || echo '未找到')"
echo "6. 语言文件: $(ls /ssddata/{username}/local/share/tessdata/*.traineddata 2>/dev/null | wc -l) 个"
echo ""
echo "7. 测试运行:"
tesseract --version 2>&1 | head -3
```

## 一键安装脚本

创建 `install_tesseract.sh`：

```bash
#!/bin/bash
# 一键安装Tesseract AppImage

# 配置
USERNAME="${1:-$USER}"
BASE_DIR="/ssddata/${USERNAME}"
APPIMAGE_URL="https://github.com/AlexanderP/tesseract-appimage/releases/download/v5.5.1/tesseract-5.5.1-x86_64.AppImage"

echo "=== 安装 Tesseract 5.5.1 到 $BASE_DIR ==="

# 创建目录
mkdir -p "$BASE_DIR/local/bin"
mkdir -p "$BASE_DIR/local/share/tessdata"

# 下载AppImage
cd "$BASE_DIR/local/bin"
if [ ! -f "tesseract-5.5.1-x86_64.AppImage" ]; then
    echo "下载 Tesseract AppImage..."
    wget "$APPIMAGE_URL"
    chmod +x tesseract-5.5.1-x86_64.AppImage
fi

# 创建包装脚本
cat > tesseract << EOF
#!/bin/bash
exec "$BASE_DIR/local/bin/tesseract-5.5.1-x86_64.AppImage" "\$@"
EOF
chmod +x tesseract

# 下载语言数据
cd "$BASE_DIR/local/share/tessdata"
for lang in eng chi_sim; do
    if [ ! -f "${lang}.traineddata" ]; then
        echo "下载 $lang 语言包..."
        wget "https://github.com/tesseract-ocr/tessdata/raw/main/${lang}.traineddata"
    fi
done

echo ""
echo "安装完成！请添加以下内容到你的shell配置文件："
echo ""
echo "# Bash/Zsh:"
echo "export PATH=\"$BASE_DIR/local/bin:\$PATH\""
echo "export TESSDATA_PREFIX=\"$BASE_DIR/local/share/tessdata\""
echo ""
echo "# Tcsh/Csh:"
echo "setenv PATH $BASE_DIR/local/bin:\$PATH"
echo "setenv TESSDATA_PREFIX $BASE_DIR/local/share/tessdata"
```

使用方法：
```bash
chmod +x install_tesseract.sh
./install_tesseract.sh your_username
```