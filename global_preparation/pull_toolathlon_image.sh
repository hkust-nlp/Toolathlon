# pull image
# check use podman or docker from configs/global_configs.py
podman_or_docker=$(uv run python -c "import sys; sys.path.append('configs'); from global_configs import global_configs; print(global_configs.podman_or_docker)")
image_url="docker.io/lockon0927/toolathlon-task-image:1016beta"
if [ "$podman_or_docker" = "podman" ]; then
    podman pull $image_url
else
    docker pull $image_url
fi