#!/bin/bash


REPO_DIR=/home/jetson/deploy/SNJ-Drone-System

# 3. Restart containers
echo "[2/2] Restart docker containers..."


cd "$REPO_DIR" || {
    echo "ERROR: Repo directory not found"
    exit 1
}

docker compose restart

if [ $? -ne 0 ]; then
    echo "ERROR: docker restart failed"
    exit 1
fi

echo "=== Deploy OK ==="