#!/bin/bash

# Ensure we are in the project root directory where this script is located
cd "$(dirname "$0")"

set -e

# Load environment variables from .env file
if [ -f .env ]; then
    set -a
    source .env
    set +a
    echo "✅ Loaded environment variables from .env"
else
    echo "⚠️  No .env file found, using defaults"
fi

# Define compose file locations relative to 'docker' directory
COMPOSE_BASE="docker-compose.yml"
COMPOSE_DEV="docker-compose.override.yml"
COMPOSE_MONITOR="docker-compose.monitoring.yml"

usage() {
    echo "Usage: ./manage.sh [command]"
    echo ""
    echo "Available commands:"
    echo "  dev             Start Development environment in Docker (hot-reload, volume mounts, detached)"
    echo "  prod            Start Production environment in Docker (detached, no reload)"
    echo "  local           Run application directly with local Python (no Docker, hot-reload)"
    echo "  down            Stop all application containers (backend)"
    echo "  build           Build/Rebuild Docker Image"
    echo "  logs            View live backend logs"
    echo "  monitor-up      Start monitoring stack (Prometheus, Grafana, cAdvisor, Node Exporter)"
    echo "  monitor-down    Stop monitoring stack"
    echo "  status          View status of running containers"
    echo "  help            Show this help message"
    exit 1
}

# Check if no arguments provided
if [ -z "$1" ]; then
    usage
fi

case "$1" in
    "dev")
        echo "🚀 Starting all services in DEVELOPMENT mode (Docker)..."
        cd docker
        docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_DEV" --env-file ../.env up --build -d
        cd ..
        echo ""
        echo "✅ Started successfully in Development mode!"
        echo "  - Backend (reload): http://localhost:8000"
        echo ""
        echo "📝 Useful commands:"
        echo "  - View logs: ./manage.sh logs"
        echo "  - Stop services: ./manage.sh down"
        ;;
    "prod")
        echo "🚀 Starting all services in PRODUCTION mode (Docker)..."
        cd docker
        docker compose -f "$COMPOSE_BASE" --env-file ../.env up --build -d
        cd ..
        echo ""
        echo "✅ Started successfully in Production mode!"
        echo "  - Backend: http://localhost:8000"
        echo ""
        echo "📝 Useful commands:"
        echo "  - View logs: ./manage.sh logs"
        echo "  - Stop services: ./manage.sh down"
        ;;
    "local")
        echo "🚀 Starting application LOCAL (without Docker)..."
        if [ ! -d ".venv" ]; then
            echo "❌ .venv directory does not exist. Please run 'python3 -m venv .venv && pip install -r requirements.txt' first."
            exit 1
        fi
        echo "Activating virtual environment (.venv)..."
        source .venv/bin/activate

        # Determine app module
        DEFAULT_MODULE_NAME="src.main"
        VARIABLE_NAME="app"
        APP_MODULE="$DEFAULT_MODULE_NAME:$VARIABLE_NAME"

        HOST=${HOST:-0.0.0.0}
        PORT=${PORT:-8000}

        echo "Starting Uvicorn with auto-reload on http://$HOST:$PORT..."
        exec python3 -m uvicorn --reload --host $HOST --port $PORT "$APP_MODULE"
        ;;
    "down")
        echo "🛑 Stopping application containers..."
        cd docker
        docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_DEV" down
        cd ..
        echo "✅ Application stopped successfully."
        ;;
    "build")
        echo "🛠️ Rebuilding Docker image (no cache)..."
        cd docker
        docker compose -f "$COMPOSE_BASE" build --no-cache
        cd ..
        echo "✅ Build complete."
        ;;
    "logs")
        cd docker
        docker compose -f "$COMPOSE_BASE" logs -f backend
        cd ..
        ;;
    "monitor-up")
        echo "📈 Starting monitoring system (Monitoring Stack)..."
        cd docker
        docker compose -f "$COMPOSE_MONITOR" up -d
        cd ..
        echo ""
        echo "✅ Monitoring system started successfully!"
        echo "  - Grafana: http://localhost:3000 (Credentials: admin/admin)"
        echo "  - Prometheus: http://localhost:9090"
        echo "  - cAdvisor: http://localhost:8080"
        echo "  - Node Exporter metrics: http://localhost:9100/metrics"
        echo ""
        echo "📝 Quick Grafana guide:"
        echo "  1. Open Grafana: http://localhost:3000"
        echo "  2. Login with admin/admin"
        echo "  3. Import sample dashboards:"
        echo "     - Docker monitoring (cAdvisor): ID 193"
        echo "     - Node Exporter (System): ID 1860"
        ;;
    "monitor-down")
        echo "🛑 Stopping monitoring system..."
        cd docker
        docker compose -f "$COMPOSE_MONITOR" down
        cd ..
        echo "✅ Monitoring system stopped."
        ;;
    "status")
        echo "📊 Container status:"
        cd docker
        docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_DEV" -f "$COMPOSE_MONITOR" ps
        cd ..
        ;;
    *)
        usage
        ;;
esac