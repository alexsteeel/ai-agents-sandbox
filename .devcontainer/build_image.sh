#!/bin/bash

cp /home/$USER/.p10k.zsh .
docker build -t claude-code-devcontainer -f Dockerfile .