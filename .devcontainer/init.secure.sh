#!/bin/bash
# Secure initialization script for devcontainer
# This file contains credentials and sensitive data - NEVER commit to git!
#
# To use:
# 1. Copy this file to init.secure.sh
# 2. Add your credentials and sensitive configuration
# 3. The file will be automatically copied to new worktrees
# 4. init.secure.sh is in .gitignore and won't be committed

echo "Running secure initialization..."

# Example: Set API keys and tokens
# export GITHUB_TOKEN="ghp_your_token_here"
# export OPENAI_API_KEY="sk-your-key-here"
# export DATABASE_PASSWORD="your-password"
# export AWS_ACCESS_KEY_ID="your-key"
# export AWS_SECRET_ACCESS_KEY="your-secret"

# Example: Configure git with credentials
# git config --global user.name "Your Name"
# git config --global user.email "your.email@example.com"
# git config --global credential.helper store

# Example: Setup SSH keys
# if [ ! -f ~/.ssh/id_rsa ]; then
#     ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
# fi

# Example: Login to registries
# echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
# npm config set //registry.npmjs.org/:_authToken=$NPM_TOKEN

echo "Secure initialization complete"