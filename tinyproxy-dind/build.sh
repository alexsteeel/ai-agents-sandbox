#!/bin/bash
set -e

echo "Building tinyproxy-dind image..."
docker build -t tinyproxy-dind:latest .

echo "Build complete: tinyproxy-dind:latest"