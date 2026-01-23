#!/bin/bash
# Script to restart NEXUS API with swarm endpoints enabled
# Stops manual uvicorn process and restarts systemd service

set -e

echo "========================================="
echo "  NEXUS API Restart for Swarm Activation"
echo "========================================="
echo ""

# Step 1: Stop any existing uvicorn process on port 8080
echo "1. Stopping existing API process on port 8080..."
if ss -tlnp | grep -q ":8080"; then
    echo "   Found process listening on port 8080"
    # Try to kill using fuser
    if command -v fuser &> /dev/null; then
        sudo fuser -k 8080/tcp 2>/dev/null || true
        echo "   Killed using fuser"
    else
        # Alternative: kill using lsof
        PID=$(lsof -t -i:8080 2>/dev/null || echo "")
        if [ -n "$PID" ]; then
            kill $PID 2>/dev/null || true
            echo "   Killed PID: $PID"
        fi
    fi
    # Wait a moment
    sleep 2
else
    echo "   No process found on port 8080"
fi

# Step 2: Ensure systemd service is enabled and restart it
echo "2. Restarting nexus-api systemd service..."
if sudo systemctl is-active nexus-api --quiet; then
    echo "   Service is active, restarting..."
    sudo systemctl restart nexus-api
elif sudo systemctl is-enabled nexus-api --quiet; then
    echo "   Service is enabled but not active, starting..."
    sudo systemctl start nexus-api
else
    echo "   Service is not enabled, enabling and starting..."
    sudo systemctl enable --now nexus-api
fi

# Step 3: Wait for service to start
echo "3. Waiting for API to start..."
sleep 5

# Step 4: Verify service status
echo "4. Verifying service status..."
if sudo systemctl is-active nexus-api --quiet; then
    echo "   ✅ nexus-api service is active"
else
    echo "   ❌ nexus-api service failed to start"
    sudo systemctl status nexus-api --no-pager
    exit 1
fi

# Step 5: Test swarm endpoint
echo "5. Testing swarm endpoint..."
if curl -s http://localhost:8080/swarm/ >/dev/null 2>&1; then
    echo "   ✅ Swarm endpoint is accessible"
    echo ""
    echo "========================================="
    echo "  SUCCESS: Swarm endpoints activated!"
    echo "========================================="
    echo ""
    echo "Next: Create automation debate swarm with:"
    echo "  curl -X POST http://localhost:8080/swarm/ \\"
    echo "    -H \"Content-Type: application/json\" \\"
    echo "    -d '{\"name\": \"automation_audit_swarm\", \"description\": \"Swarm for debating automation improvements\", \"purpose\": \"Analyze uncertain automations and propose optimal solutions\", \"swarm_type\": \"collaborative\", \"consensus_protocol\": \"raft\", \"max_members\": 8}'"
else
    echo "   ❌ Swarm endpoint not accessible (check logs)"
    echo "   Testing health endpoint instead..."
    curl -s http://localhost:8080/health | head -1
    echo ""
    echo "   Note: Service may need more time to start or code may have issues."
fi

echo ""
echo "Script completed."