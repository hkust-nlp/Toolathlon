#!/bin/bash

# 运行以下该脚本，已将本项目中所有原本使用podman的地方改为docker
# 涉及到的文件有
# configs/mcp_servers/github.yaml
# deployment/canvas/scripts/create_admin_accounts.py
# deployment/canvas/scripts/create_canvas_user.py
# deployment/canvas/scripts/setup.sh
# deployment/k8s/scripts/setup.sh
# deployment/poste/scripts/create_users.sh
# deployment/poste/scripts/setup.sh
# deployment/woocommerce/scripts/fix_permissions.sh
# deployment/woocommerce/scripts/setup.sh
# 只要将它们像纯文本一样打开并编辑就行了

# 切换到项目根目录
cd "$(dirname "$0")/.."

# 配置文件
file_paths=(
    "configs/mcp_servers/github.yaml"

    "deployment/canvas/scripts/create_admin_accounts.py"
    "deployment/canvas/scripts/create_canvas_user.py"
    "deployment/canvas/scripts/setup.sh"
    "deployment/k8s/scripts/setup.sh"
    "deployment/poste/scripts/create_users.sh"
    "deployment/poste/scripts/setup.sh"
    "deployment/woocommerce/scripts/fix_permissions.sh"
    "deployment/woocommerce/scripts/setup.sh"

)

# 遍历配置文件并进行替换
for file_path in "${file_paths[@]}"; do
    sed -i 's/podman/docker/g' "$file_path"
done

echo "Replaced `podman` with `docker` in all specified files"