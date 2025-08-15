# Go DevContainer
# Based on the devcontainer-base image with latest Go installed

ARG IMAGE_TAG=latest
FROM ai-agents-sandbox/devcontainer:${IMAGE_TAG}

# Switch to root for installations
USER root

# Go version - using latest stable
ARG GO_VERSION=1.23.4

# Install Go from official binary distribution
RUN wget -q https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go${GO_VERSION}.linux-amd64.tar.gz \
    && rm go${GO_VERSION}.linux-amd64.tar.gz \
    && ln -s /usr/local/go/bin/go /usr/local/bin/go \
    && ln -s /usr/local/go/bin/gofmt /usr/local/bin/gofmt

# Install additional development tools
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set up Go environment variables
ENV GOPATH=/home/claude/go \
    GOBIN=/home/claude/go/bin \
    GO111MODULE=on \
    CGO_ENABLED=1 \
    GOPROXY=https://proxy.golang.org,direct \
    GOSUMDB=sum.golang.org \
    PATH="/usr/local/go/bin:/home/claude/go/bin:${PATH}"

# Create Go workspace directories with proper permissions
RUN mkdir -p /home/claude/go/{bin,src,pkg} \
    && chown -R claude:dev /home/claude/go

# Switch back to claude user
USER claude
WORKDIR /workspace

# Install popular Go tools
RUN go install golang.org/x/tools/gopls@latest \
    && go install github.com/go-delve/delve/cmd/dlv@latest \
    && go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest \
    && go install golang.org/x/tools/cmd/goimports@latest \
    && go install github.com/fatih/gomodifytags@latest \
    && go install github.com/josharian/impl@latest \
    && go install github.com/cweill/gotests/gotests@latest \
    && go install github.com/ramya-rao-a/go-outline@latest \
    && go install github.com/uudashr/gopkgs/v2/cmd/gopkgs@latest \
    && go install honnef.co/go/tools/cmd/staticcheck@latest

# Verify installation
RUN go version && which go

# Set the default command
CMD ["/usr/local/bin/devcontainer-init"]