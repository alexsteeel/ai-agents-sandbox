# AI Agents Sandbox - Python Development Image
# Extends the base image with Python development tools

FROM ai-agents-sandbox/base:latest

# Switch to root for installations
USER root

# Install Python and development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

# Install Python linting and formatting tools
RUN pip3 install --break-system-packages \
    black \
    ruff \
    mypy \
    pytest \
    ipython

# Install common development packages
RUN pip3 install --break-system-packages \
    requests \
    pyyaml \
    python-dotenv \
    click \
    rich \
    pydantic

# Switch back to non-root user
USER claude

# Set Python environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/home/claude/.local/bin:${PATH}"

WORKDIR /workspace

# Initialization script for Python projects
COPY --chown=claude:local-ai-team <<'EOF' /home/claude/init-python.sh
#!/bin/bash
set -euo pipefail

echo "Initializing Python environment..."

# Install project dependencies if they exist
if [ -f "requirements.txt" ]; then
    echo "Installing requirements.txt..."
    pip install --user -r requirements.txt
fi

if [ -f "pyproject.toml" ]; then
    echo "Installing project in editable mode..."
    pip install --user -e .
fi

echo "Python environment ready!"
EOF

RUN chmod +x /home/claude/init-python.sh

CMD ["sleep", "infinity"]