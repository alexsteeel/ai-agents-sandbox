# Example custom Dockerfile (optional)
# Only needed if you want to extend the base image

FROM claudecode/devcontainer:latest

# This project doesn't need customization, but here's how you would do it:

# Example: Add project-specific tools
# RUN npm install -g @ai-tools/cli

# Example: Add SSL certificates for corporate environment
# USER root
# COPY ssl-certs/corporate-ca.crt /usr/local/share/ca-certificates/
# RUN update-ca-certificates
# USER claude

# Stay as non-root user
USER claude
WORKDIR /workspace