#!/bin/bash

# ===== CONFIG =====
REPO_DIR="$HOME/docker/gimbal_detection_system/SNJ-Drone-System"
BRANCH="main"

echo "=== SNJ Drone System Update Start ==="

# 1. 進入專案目錄
cd "$REPO_DIR" || {
    echo "ERROR: Repo directory not found"
    exit 1
}

# 2. Pull 最新版本
echo "[1/2] Git pulling..."
git pull origin $BRANCH

if [ $? -ne 0 ]; then
    echo "ERROR: git pull failed"
    exit 1
fi
