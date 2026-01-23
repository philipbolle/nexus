#!/bin/bash
#
# NEXUS Celery Worker Startup Script
#
# Starts Celery workers and beat scheduler for distributed task processing.
# Supports multiple queues, concurrency settings, and process management.
#
# Usage:
#   ./start_celery.sh [command] [options]
#
# Commands:
#   start [worker_type]    - Start worker(s) (default: all)
#   stop                   - Stop all Celery workers and beat
#   restart [worker_type]  - Restart worker(s)
#   status                 - Show status of Celery processes
#   logs [worker_type]     - Show logs for worker(s)
#
# Worker Types:
#   all                    - All workers and beat scheduler (default)
#   default                - Default queue worker
#   agent_tasks            - Agent tasks queue worker
#   system_tasks           - System tasks queue worker
#   beat                   - Beat scheduler only
#   multi                  - All workers in single process (concurrency > 1)
#
# Examples:
#   ./start_celery.sh start              # Start all workers and beat
#   ./start_celery.sh start agent_tasks  # Start only agent tasks worker
#   ./start_celery.sh stop               # Stop all processes
#   ./start_celery.sh status             # Show process status
#   ./start_celery.sh logs beat          # Show beat scheduler logs
#

set -e

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PATH="$PROJECT_ROOT/venv"
PYTHON_PATH="$VENV_PATH/bin/python"
CELERY_PATH="$VENV_PATH/bin/celery"
CELERY_APP="app.celery_app:app"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/.celery"
CELERY_BROKER="${CELERY_BROKER:-redis://localhost:6379/0}"

# Queue configurations
declare -A QUEUE_CONFIGS=(
    ["default"]="--queues=default --concurrency=2"
    ["agent_tasks"]="--queues=agent_tasks --concurrency=4"
    ["system_tasks"]="--queues=system_tasks --concurrency=2"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ensure required directories exist
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

# Print colored output
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if virtual environment exists
check_venv() {
    if [ ! -f "$PYTHON_PATH" ]; then
        log_error "Virtual environment not found at $VENV_PATH"
        log_error "Please create it with: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
        exit 1
    fi
}

# Check if Redis is running
check_redis() {
    if ! command -v redis-cli &> /dev/null; then
        log_warning "redis-cli not found. Cannot check Redis status."
        return 0
    fi

    if ! redis-cli -u "$CELERY_BROKER" ping &> /dev/null; then
        log_error "Redis not responding at $CELERY_BROKER"
        log_error "Please ensure Redis is running: docker-compose up -d redis"
        exit 1
    fi
}

# Get PID file path
get_pid_file() {
    local worker_type=$1
    echo "$PID_DIR/${worker_type}.pid"
}

# Get log file path
get_log_file() {
    local worker_type=$1
    echo "$LOG_DIR/celery_${worker_type}.log"
}

# Start a worker
start_worker() {
    local worker_type=$1
    local pid_file=$(get_pid_file "$worker_type")
    local log_file=$(get_log_file "$worker_type")

    log_info "Starting $worker_type worker..."

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_warning "$worker_type worker already running (PID: $pid)"
            return 0
        else
            log_warning "Stale PID file found for $worker_type, removing..."
            rm -f "$pid_file"
        fi
    fi

    # Build command based on worker type
    local cmd=""
    case "$worker_type" in
        "default"|"agent_tasks"|"system_tasks")
            cmd="$CELERY_PATH -A $CELERY_APP worker ${QUEUE_CONFIGS[$worker_type]} --loglevel=info --hostname=%h.$worker_type --pidfile=$pid_file"
            ;;
        "multi")
            cmd="$CELERY_PATH -A $CELERY_APP worker --queues=default,agent_tasks,system_tasks --concurrency=8 --loglevel=info --hostname=%h.multi --pidfile=$pid_file"
            ;;
        *)
            log_error "Unknown worker type: $worker_type"
            return 1
            ;;
    esac

    # Start in background and log output
    nohup $cmd >> "$log_file" 2>&1 &
    local worker_pid=$!

    # Wait a bit for startup
    sleep 2

    if kill -0 "$worker_pid" 2>/dev/null; then
        echo "$worker_pid" > "$pid_file"
        log_success "$worker_type worker started (PID: $worker_pid)"
        log_info "Logs: $log_file"
    else
        log_error "Failed to start $worker_type worker"
        log_error "Check logs: $log_file"
        tail -20 "$log_file"
        return 1
    fi
}

# Start beat scheduler
start_beat() {
    local pid_file=$(get_pid_file "beat")
    local log_file=$(get_log_file "beat")

    log_info "Starting beat scheduler..."

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_warning "Beat scheduler already running (PID: $pid)"
            return 0
        else
            log_warning "Stale PID file found for beat, removing..."
            rm -f "$pid_file"
        fi
    fi

    # Start beat scheduler
    nohup $CELERY_PATH -A $CELERY_APP beat --loglevel=info --pidfile="$pid_file" >> "$log_file" 2>&1 &
    local beat_pid=$!

    sleep 2

    if kill -0 "$beat_pid" 2>/dev/null; then
        echo "$beat_pid" > "$pid_file"
        log_success "Beat scheduler started (PID: $beat_pid)"
        log_info "Logs: $log_file"
    else
        log_error "Failed to start beat scheduler"
        log_error "Check logs: $log_file"
        tail -20 "$log_file"
        return 1
    fi
}

# Stop a process
stop_process() {
    local worker_type=$1
    local pid_file=$(get_pid_file "$worker_type")

    if [ ! -f "$pid_file" ]; then
        log_warning "No PID file found for $worker_type"
        return 0
    fi

    local pid=$(cat "$pid_file")

    if kill -0 "$pid" 2>/dev/null; then
        log_info "Stopping $worker_type (PID: $pid)..."
        kill -TERM "$pid"

        # Wait for process to terminate
        local timeout=10
        while kill -0 "$pid" 2>/dev/null && [ $timeout -gt 0 ]; do
            sleep 1
            ((timeout--))
        done

        if kill -0 "$pid" 2>/dev/null; then
            log_warning "$worker_type not stopping, forcing..."
            kill -9 "$pid"
            sleep 1
        fi

        rm -f "$pid_file"
        log_success "$worker_type stopped"
    else
        log_warning "$worker_type not running (stale PID: $pid)"
        rm -f "$pid_file"
    fi
}

# Show process status
show_status() {
    log_info "Celery Process Status:"
    echo ""

    local found_processes=0

    for pid_file in "$PID_DIR"/*.pid; do
        [ -e "$pid_file" ] || continue

        local worker_type=$(basename "$pid_file" .pid)
        local pid=$(cat "$pid_file" 2>/dev/null)

        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} $worker_type: running (PID: $pid)"
            found_processes=1
        else
            echo -e "  ${RED}✗${NC} $worker_type: not running (stale PID file)"
            rm -f "$pid_file" 2>/dev/null
        fi
    done

    if [ $found_processes -eq 0 ]; then
        log_warning "No Celery processes found running"
    fi

    echo ""

    # Show Redis status
    log_info "Redis Status:"
    if command -v redis-cli &> /dev/null; then
        if redis-cli -u "$CELERY_BROKER" ping &> /dev/null; then
            echo -e "  ${GREEN}✓${NC} Redis: responding at $CELERY_BROKER"
        else
            echo -e "  ${RED}✗${NC} Redis: not responding"
        fi
    else
        echo -e "  ${YELLOW}?${NC} Redis: redis-cli not available"
    fi
}

# Show logs
show_logs() {
    local worker_type=$1

    if [ -z "$worker_type" ]; then
        log_error "Please specify a worker type to view logs"
        echo "Available types: default, agent_tasks, system_tasks, beat, multi"
        return 1
    fi

    local log_file=$(get_log_file "$worker_type")

    if [ ! -f "$log_file" ]; then
        log_error "No log file found for $worker_type: $log_file"
        return 1
    fi

    log_info "Showing last 50 lines of $worker_type logs ($log_file):"
    echo ""
    tail -50 "$log_file"
}

# Clean up old log files
cleanup_logs() {
    local max_logs=10
    for worker_type in default agent_tasks system_tasks beat multi; do
        local log_file=$(get_log_file "$worker_type")
        if [ -f "$log_file" ]; then
            # Keep only last 10,000 lines
            tail -10000 "$log_file" > "${log_file}.tmp" && mv "${log_file}.tmp" "$log_file"
        fi
    done
}

# Main command handler
main() {
    local command=$1
    local worker_type=$2

    check_venv
    check_redis

    case "$command" in
        "start")
            case "${worker_type:-all}" in
                "all")
                    start_worker "multi"
                    start_beat
                    ;;
                "beat")
                    start_beat
                    ;;
                "multi")
                    start_worker "multi"
                    ;;
                "default"|"agent_tasks"|"system_tasks")
                    start_worker "$worker_type"
                    ;;
                *)
                    log_error "Unknown worker type: $worker_type"
                    echo "Valid types: all, default, agent_tasks, system_tasks, beat, multi"
                    exit 1
                    ;;
            esac

            # Show status after starting
            sleep 3
            show_status
            ;;

        "stop")
            log_info "Stopping all Celery processes..."

            # Stop in reverse order
            stop_process "beat"
            for wt in multi system_tasks agent_tasks default; do
                stop_process "$wt"
            done

            show_status
            ;;

        "restart")
            log_info "Restarting $worker_type..."

            case "${worker_type:-all}" in
                "all")
                    ./start_celery.sh stop
                    sleep 2
                    ./start_celery.sh start
                    ;;
                "beat")
                    stop_process "beat"
                    sleep 1
                    start_beat
                    ;;
                "multi"|"default"|"agent_tasks"|"system_tasks")
                    stop_process "$worker_type"
                    sleep 1
                    start_worker "$worker_type"
                    ;;
                *)
                    log_error "Unknown worker type: $worker_type"
                    exit 1
                    ;;
            esac

            show_status
            ;;

        "status")
            show_status
            ;;

        "logs")
            show_logs "$worker_type"
            ;;

        "cleanup")
            cleanup_logs
            log_success "Logs cleaned up"
            ;;

        *)
            echo "NEXUS Celery Worker Management"
            echo "=============================="
            echo ""
            echo "Usage: $0 [command] [worker_type]"
            echo ""
            echo "Commands:"
            echo "  start [type]    - Start worker(s) (default: all)"
            echo "  stop            - Stop all workers and beat"
            echo "  restart [type]  - Restart worker(s)"
            echo "  status          - Show process status"
            echo "  logs [type]     - Show logs for worker"
            echo "  cleanup         - Clean up old log entries"
            echo ""
            echo "Worker Types:"
            echo "  all            - All workers and beat (default)"
            echo "  default        - Default queue worker"
            echo "  agent_tasks    - Agent tasks queue worker"
            echo "  system_tasks   - System tasks queue worker"
            echo "  beat           - Beat scheduler only"
            echo "  multi          - All queues in single process"
            echo ""
            echo "Examples:"
            echo "  $0 start                # Start all workers"
            echo "  $0 start agent_tasks    # Start agent tasks worker"
            echo "  $0 stop                 # Stop all processes"
            echo "  $0 status               # Show status"
            echo "  $0 logs beat            # Show beat logs"
            echo ""
            exit 1
            ;;
    esac
}

# Run main function
main "$@"