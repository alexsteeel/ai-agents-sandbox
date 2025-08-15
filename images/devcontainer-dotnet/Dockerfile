# .NET 9 DevContainer
# Based on the devcontainer-base image with .NET 9 SDK installed

ARG IMAGE_TAG=latest
FROM ai-agents-sandbox/devcontainer:${IMAGE_TAG}

# Switch to root for installations
USER root

# Install .NET 9 dependencies and tools
RUN apt-get update && apt-get install -y \
    wget \
    apt-transport-https \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Add Microsoft package repository for Debian 12
RUN wget https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb -O packages-microsoft-prod.deb \
    && dpkg -i packages-microsoft-prod.deb \
    && rm packages-microsoft-prod.deb

# Install .NET 9 SDK
RUN apt-get update && apt-get install -y \
    dotnet-sdk-9.0 \
    && rm -rf /var/lib/apt/lists/*

# Install useful .NET tools globally
RUN dotnet tool install --global dotnet-ef \
    && dotnet tool install --global dotnet-aspnet-codegenerator \
    && dotnet tool install --global dotnet-format

# Add .NET tools to PATH for claude user
ENV PATH="/home/claude/.dotnet/tools:${PATH}"

# Set environment variables for .NET
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1 \
    DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1 \
    DOTNET_NOLOGO=true \
    DOTNET_GENERATE_ASPNET_CERTIFICATE=false \
    DOTNET_ADD_GLOBAL_TOOLS_TO_PATH=true \
    DOTNET_MULTILEVEL_LOOKUP=false

# Create NuGet cache directory with proper permissions
RUN mkdir -p /home/claude/.nuget/packages \
    && chown -R claude:dev /home/claude/.nuget

# Switch back to claude user
USER claude
WORKDIR /workspace

# Verify installation
RUN dotnet --version && dotnet --list-sdks

# Set the default command
CMD ["/usr/local/bin/devcontainer-init"]