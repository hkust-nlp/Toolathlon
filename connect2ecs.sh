# 加 -v 看SSH的详细信息
AUTOSSH_DEBUG=1 \
AUTOSSH_GATETIME=0 \
AUTOSSH_POLL=30 \
~/local/bin/autossh -M 0 -N -v \
  -o "ServerAliveInterval=10" \
  -o "ServerAliveCountMax=3" \
  -o "StrictHostKeyChecking=no" \
  -o "UserKnownHostsFile=/dev/null" \
  -L 12345:localhost:12345 \
  root@47.84.80.161