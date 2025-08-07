#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(pwd)"

# Configure ports
http_port=10001
https_port=20001
USERS_COUNT=100
# Check operation parameter
operation=${1:-start}

case $operation in
  "start")
    echo "Starting Canvas service..."

    echo "Stopping any existing Canvas services..."
    $0 stop
    sleep 2

    # Start Canvas Docker container
    echo "Starting Canvas Docker container (port: $http_port)..."
    podman run --name canvas-docker -p ${http_port}:3000 -d lbjay/canvas-docker
    
    # Wait for container to start
    echo "Waiting for Canvas container to start..."
    sleep 5
    
    # Check if container started successfully
    if podman ps | grep canvas-docker > /dev/null; then
      echo "Canvas Docker container started successfully"
    else
      echo "Canvas Docker container failed to start"
      exit 1
    fi
    
    # Start HTTPS proxy (using nohup)
    echo "Starting HTTPS proxy (port: $https_port)..."
    cd "$PROJECT_ROOT"
    
    mkdir -p deployment/canvas/logs
    
    # Start in background using nohup
    nohup node deployment/utils/build_proxy.mjs ${https_port} ${http_port} localhost http deployment/canvas/logs > deployment/canvas/logs/proxy.log 2>&1 &
    PROXY_PID=$!
    echo $PROXY_PID > deployment/canvas/logs/proxy.pid
    
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
      podman stop canvas-docker 2>/dev/null || true
      podman rm canvas-docker 2>/dev/null || true
      exit 1
    fi

    echo "Start creating users ..."
    uv run deployment/canvas/scripts/create_canvas_user.py --count $USERS_COUNT --skip-test --batch-size 100
    ;;
    
  "stop")
    echo "Stopping Canvas service..."
    
    # Stop HTTPS proxy
    echo "Stopping HTTPS proxy..."
    cd "$PROJECT_ROOT"
    if [ -f deployment/canvas/logs/proxy.pid ]; then
      PROXY_PID=$(cat deployment/canvas/logs/proxy.pid)
      if kill -0 $PROXY_PID 2>/dev/null; then
        kill $PROXY_PID
        echo "HTTPS proxy stopped (PID: $PROXY_PID)"
      else
        echo "HTTPS proxy process does not exist"
      fi
      rm -f deployment/canvas/logs/proxy.pid
    else
      echo "Proxy PID file not found"
    fi
    
    # Stop Canvas Docker container
    echo "Stopping Canvas Docker container..."
    podman stop canvas-docker 2>/dev/null || true
    podman rm canvas-docker 2>/dev/null || true
    
    echo "Canvas service has been stopped"

    echo "Deleting tmp and configs..."
    rm -rf deployment/canvas/tmp
    rm -rf deployment/canvas/configs
    ;;
    
  "status")
    echo "Checking Canvas service status..."
    
    # Check Docker container status
    echo "Canvas Docker container status:"
    if podman ps | grep canvas-docker > /dev/null; then
      echo "  ✓ Running (port: $http_port)"
    else
      echo "  ✗ Not running"
    fi
    
    # Check proxy status
    echo "HTTPS proxy status:"
    cd "$PROJECT_ROOT"
    if [ -f deployment/canvas/logs/proxy.pid ]; then
      PROXY_PID=$(cat deployment/canvas/logs/proxy.pid)
      if kill -0 $PROXY_PID 2>/dev/null; then
        echo "  ✓ Running (PID: $PROXY_PID)"
        echo "  Proxy port: $https_port"
        echo "  Target service: http://localhost:$http_port"
      else
        echo "  ✗ Not running (PID file exists but process does not exist)"
        rm -f deployment/canvas/logs/proxy.pid
      fi
    else
      echo "  ✗ Not running"
    fi
    ;;
    
  "restart")
    echo "Restarting Canvas service..."
    $0 stop
    sleep 2
    $0 start
    ;;
    
  "logs")
    echo "Showing proxy service logs:"
    cd "$PROJECT_ROOT"
    if [ -f deployment/canvas/logs/proxy.log ]; then
      tail -f deployment/canvas/logs/proxy.log
    else
      echo "Log file does not exist: $PROJECT_ROOT/deployment/canvas/logs/proxy.log"
    fi
    ;;
    
  "debug")
    echo "Debug mode: running proxy service in foreground..."
    cd "$PROJECT_ROOT"

    mkdir -p deployment/canvas/logs

    node deployment/utils/build_proxy.mjs ${https_port} ${http_port} localhost http deployment/canvas/logs
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

