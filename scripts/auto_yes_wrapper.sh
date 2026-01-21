#!/bin/bash
# Auto-Yes Wrapper Script for Claude Code
# Starts auto-yes tool in background with timeout management

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTO_YES_PY="$SCRIPT_DIR/auto_yes.py"
LOG_FILE="$SCRIPT_DIR/auto_yes.log"
PID_FILE="$SCRIPT_DIR/auto_yes.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[auto-yes]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[auto-yes]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[auto-yes]${NC} $1"
}

print_error() {
    echo -e "${RED}[auto-yes]${NC} $1"
}

check_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0  # Running
        else
            # Stale PID file
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

start_auto_yes() {
    local timeout=${1:-15}  # Default 15 minutes

    if check_running; then
        print_error "Auto-yes is already running (PID: $(cat "$PID_FILE"))"
        print_error "Stop it first with: $0 stop"
        return 1
    fi

    # Check if auto_yes.py exists
    if [ ! -f "$AUTO_YES_PY" ]; then
        print_error "Auto-yes Python script not found: $AUTO_YES_PY"
        return 1
    fi

    # Check if Python is available
    if ! command -v python3 > /dev/null; then
        print_error "Python3 is not installed or not in PATH"
        return 1
    fi

    print_status "Starting auto-yes with timeout: ${timeout} minutes..."

    # Run in background, redirect output to log file
    nohup python3 "$AUTO_YES_PY" --timeout "$timeout" >> "$LOG_FILE" 2>&1 &
    PID=$!

    # Save PID
    echo "$PID" > "$PID_FILE"

    # Wait a moment to see if it starts successfully
    sleep 1
    if ps -p "$PID" > /dev/null 2>&1; then
        print_success "Auto-yes started successfully (PID: $PID)"
        print_success "Log file: $LOG_FILE"
        print_success "To stop: $0 stop"
        print_success "To view logs: tail -f $LOG_FILE"
    else
        print_error "Failed to start auto-yes. Check log file: $LOG_FILE"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop_auto_yes() {
    if ! check_running; then
        print_warning "Auto-yes is not running"
        return 0
    fi

    PID=$(cat "$PID_FILE")
    print_status "Stopping auto-yes (PID: $PID)..."

    # Kill the process
    kill "$PID" 2>/dev/null || true

    # Wait for process to terminate
    local max_wait=10
    local count=0
    while ps -p "$PID" > /dev/null 2>&1 && [ $count -lt $max_wait ]; do
        sleep 1
        count=$((count + 1))
    done

    # Force kill if still running
    if ps -p "$PID" > /dev/null 2>&1; then
        kill -9 "$PID" 2>/dev/null || true
        sleep 1
    fi

    rm -f "$PID_FILE"
    print_success "Auto-yes stopped"
}

status_auto_yes() {
    if check_running; then
        PID=$(cat "$PID_FILE")
        print_success "Auto-yes is running (PID: $PID)"
        print_status "Log file: $LOG_FILE"

        # Show recent logs
        if [ -f "$LOG_FILE" ]; then
            print_status "Recent logs:"
            tail -5 "$LOG_FILE" | while read line; do
                echo "  $line"
            done
        fi
    else
        print_warning "Auto-yes is not running"
    fi
}

show_usage() {
    echo "Usage: $0 {start [timeout]|stop|status|restart [timeout]}"
    echo ""
    echo "Commands:"
    echo "  start [timeout]    Start auto-yes with optional timeout in minutes (default: 15)"
    echo "  stop               Stop auto-yes"
    echo "  status             Show auto-yes status"
    echo "  restart [timeout]  Restart auto-yes with optional timeout"
    echo ""
    echo "Examples:"
    echo "  $0 start          # Start with 15 minute timeout"
    echo "  $0 start 5        # Start with 5 minute timeout"
    echo "  $0 stop           # Stop auto-yes"
    echo "  $0 status         # Show status"
}

case "${1:-}" in
    start)
        timeout=${2:-15}
        start_auto_yes "$timeout"
        ;;
    stop)
        stop_auto_yes
        ;;
    status)
        status_auto_yes
        ;;
    restart)
        timeout=${2:-15}
        stop_auto_yes
        sleep 1
        start_auto_yes "$timeout"
        ;;
    *)
        show_usage
        exit 1
        ;;
esac