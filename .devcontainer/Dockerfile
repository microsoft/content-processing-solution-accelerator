ARG UV_VERSION=latest
ARG DEBIAN_VERSION=bookworm

# Use UV package as a base layer
FROM ghcr.io/astral-sh/uv:$UV_VERSION AS uv

# Use Debian-based VS Code Dev Container as base
FROM mcr.microsoft.com/vscode/devcontainers/base:$DEBIAN_VERSION

# Install dependencies and Node.js 20+ from NodeSource
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       python3-numpy poppler-utils build-essential python3-dev curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://aka.ms/install-azd.sh | bash

# Copy UV binaries
COPY --from=uv --chown=vscode: /uv /uvx /bin/

# Install global NPM packages
RUN npm install -g tslint-to-eslint-config typescript yarn react-app-rewired

# Set default shell
SHELL ["/bin/bash", "-c"]