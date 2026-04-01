ARG DEBIAN_VERSION=bookworm

FROM mcr.microsoft.com/vscode/devcontainers/base:$DEBIAN_VERSION

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    tar \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://aka.ms/install-azd.sh | bash \
    && UV_NO_MODIFY_PATH=1 curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && if [ -f /root/.local/bin/uvx ]; then mv /root/.local/bin/uvx /usr/local/bin/uvx; fi