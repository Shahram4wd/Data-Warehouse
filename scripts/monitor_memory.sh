#!/bin/bash
# Memory monitoring script for Data Warehouse application
# Usage: ./monitor_memory.sh

echo "=== Data Warehouse Memory Monitor ==="
echo "Timestamp: $(date)"
echo

# Check overall system memory
echo "=== System Memory ==="
free -h
echo

# Check Docker container memory (if running in Docker)
if command -v docker &> /dev/null; then
    echo "=== Docker Container Memory ==="
    docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}" | head -10
    echo
fi

# Check Python processes
echo "=== Python/Gunicorn Processes ==="
ps aux | grep -E "(python|gunicorn)" | grep -v grep | head -10
echo

# Check database connections
echo "=== Database Connections ==="
if command -v docker &> /dev/null; then
    docker-compose exec -T db psql -U postgres -d data_warehouse -c "SELECT count(*) as active_connections FROM pg_stat_activity WHERE state = 'active';" 2>/dev/null || echo "Database not accessible"
else
    echo "Docker not available"
fi
echo

# Check disk space
echo "=== Disk Space ==="
df -h | head -5
echo

echo "=== Monitor Complete ==="