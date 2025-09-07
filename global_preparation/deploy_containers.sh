# launch local servers
bash deployment/k8s/scripts/prepare.sh --no-sudo # or no-sudo if you cannot use sudo
bash deployment/k8s/scripts/setup.sh

bash deployment/canvas/scripts/setup.sh # port 10001 20001

bash deployment/poste/scripts/setup.sh # port 10005 2525 1143 2587

bash deployment/woocommerce/scripts/setup.sh start 81 20 # port 10003