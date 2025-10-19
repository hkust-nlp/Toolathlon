#!/bin/bash

# read out `podman_or_docker` from global_configs.py
podman_or_docker=$(uv run python -c "import sys; sys.path.append('configs'); from global_configs import global_configs; print(global_configs.podman_or_docker)")

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(pwd)"

# Configure ports
http_port=${4:-10001}
https_port=${5:-20001}
USERS_COUNT=${3:-503}
# Check operation parameter
operation=${1:-start}
container_name=${2:-canvas-docker}

logsfolder=${6:-logs}

case $operation in
  "start")
    echo "Starting Canvas service..."

    echo "Stopping any existing Canvas services..."
    $0 stop $2 $3 $4 $5 $6
    sleep 2

    # Start Canvas Docker container
    echo "Starting Canvas Docker container (port: $http_port)..."
    $podman_or_docker run --name $container_name -p ${http_port}:3000 -d lbjay/canvas-docker

    # Wait for container to start
    echo "Waiting for Canvas container to start..."
    sleep 5

    # Check if container started successfully
    if $podman_or_docker ps | grep $container_name > /dev/null; then
      echo "Canvas Docker container started successfully"
    else
      echo "Canvas Docker container failed to start"
      exit 1
    fi

    # Configure Canvas domain to use the correct external port
    echo "Configuring Canvas domain to use port ${http_port}..."
    $podman_or_docker exec $container_name bash -c "sed -i 's/domain: \"localhost:3000\"/domain: \"localhost:${http_port}\"/' /opt/canvas/canvas-lms/config/domain.yml"

    # Restart Canvas services inside container to apply config
    echo "Restarting Canvas services to apply domain configuration..."
    $podman_or_docker exec $container_name supervisorctl restart all 2>/dev/null || true

    # Wait for services to restart
    echo "Waiting for Canvas services to fully restart..."
    sleep 10
    
    # Start HTTPS proxy (using nohup)
    echo "Starting HTTPS proxy (port: $https_port)..."
    cd "$PROJECT_ROOT"
    
    mkdir -p deployment/canvas/$logsfolder
    
    # Start in background using nohup
    nohup node deployment/utils/build_proxy.mjs ${https_port} ${http_port} localhost http deployment/canvas/$logsfolder > deployment/canvas/$logsfolder/proxy.log 2>&1 &
    PROXY_PID=$!
    echo $PROXY_PID > deployment/canvas/$logsfolder/proxy.pid
    
    # Wait for proxy to start
    sleep 2
    
    # Check if proxy started successfully
    if kill -0 $PROXY_PID 2>/dev/null; then
      echo "HTTPS proxy started successfully (PID: $PROXY_PID)"
      echo ""
      echo "Canvas service startup completed!"
      echo "HTTP access: http://localhost:${http_port}"
      echo "HTTPS access: https://localhost:${https_port}"
    else
      echo "HTTPS proxy failed to start"
      # Cleanup
      $podman_or_docker stop $container_name 2>/dev/null || true
      $podman_or_docker rm $container_name 2>/dev/null || true
      exit 1
    fi

    echo "Start creating users ..."
    uv run -m deployment.canvas.scripts.create_canvas_user --count $USERS_COUNT --skip-test --batch-size 100 --container-name $container_name

    echo "Start creating admin accounts ..."
    uv run -m deployment.canvas.scripts.create_admin_accounts --container-name $container_name
    ;;
    
  "stop")
    echo "Stopping Canvas service..."
    
    # Stop HTTPS proxy
    echo "Stopping HTTPS proxy..."
    cd "$PROJECT_ROOT"
    if [ -f deployment/canvas/$logsfolder/proxy.pid ]; then
      PROXY_PID=$(cat deployment/canvas/$logsfolder/proxy.pid)
      if kill -0 $PROXY_PID 2>/dev/null; then
        kill $PROXY_PID
        echo "HTTPS proxy stopped (PID: $PROXY_PID)"
      else
        echo "HTTPS proxy process does not exist"
      fi
      rm -f deployment/canvas/$logsfolder/proxy.pid
    else
      echo "Proxy PID file not found"
    fi
    
    # Stop Canvas Docker container
    echo "Stopping Canvas Docker container..."
    $podman_or_docker stop $container_name 2>/dev/null || true
    $podman_or_docker rm $container_name 2>/dev/null || true
    
    echo "Canvas service has been stopped"

    echo "Deleting tmp and configs..."
    rm -rf deployment/canvas/tmp
    rm -rf deployment/canvas/configs
    ;;
    
  "status")
    echo "Checking Canvas service status..."
    
    # Check Docker container status
    echo "Canvas Docker container status:"
    if $podman_or_docker ps | grep $container_name > /dev/null; then
      echo "  ✓ Running (port: $http_port)"
    else
      echo "  ✗ Not running"
    fi
    
    # Check proxy status
    echo "HTTPS proxy status:"
    cd "$PROJECT_ROOT"
    if [ -f deployment/canvas/$logsfolder/proxy.pid ]; then
      PROXY_PID=$(cat deployment/canvas/$logsfolder/proxy.pid)
      if kill -0 $PROXY_PID 2>/dev/null; then
        echo "  ✓ Running (PID: $PROXY_PID)"
        echo "  Proxy port: $https_port"
        echo "  Target service: http://localhost:$http_port"
      else
        echo "  ✗ Not running (PID file exists but process does not exist)"
        rm -f deployment/canvas/$logsfolder/proxy.pid
      fi
    else
      echo "  ✗ Not running"
    fi
    ;;
    
  "restart")
    echo "Restarting Canvas service..."
    $0 stop $2 $3 $4 $5 $6
    sleep 2
    $0 start $2 $3 $4 $5 $6
    ;;
    
  "logs")
    echo "Showing proxy service logs:"
    cd "$PROJECT_ROOT"
    if [ -f deployment/canvas/$logsfolder/proxy.log ]; then
      tail -f deployment/canvas/$logsfolder/proxy.log
    else
      echo "Log file does not exist: $PROJECT_ROOT/deployment/canvas/$logsfolder/proxy.log"
    fi
    ;;
    
  "debug")
    echo "Debug mode: running proxy service in foreground..."
    cd "$PROJECT_ROOT"

    mkdir -p deployment/canvas/$logsfolder

    node deployment/utils/build_proxy.mjs ${https_port} ${http_port} localhost http deployment/canvas/$logsfolder
    ;;
    
  *)
    echo "Usage: $0 {start|stop|status|restart|logs|debug}"
    echo "  start   - Start all services"
    echo "  stop    - Stop all services"
    echo "  status  - Check service status"
    echo "  restart - Restart all services"
    echo "  logs    - View proxy service logs"
    echo "  debug   - Run proxy service in foreground (for debugging)"
    exit 1
    ;;
esac

