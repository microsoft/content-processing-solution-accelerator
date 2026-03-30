FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm

# Keep Python/uv behavior predictable in containers
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

# Runtime OS deps:
# - poppler-utils: required by pdf2image (pdftoppm)
# - curl/ca-certificates: required for downloading + installing uv
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install uv without using an external container image layer.
# Note: this still downloads uv from the internet during build.
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && if [ -f /root/.local/bin/uvx ]; then mv /root/.local/bin/uvx /usr/local/bin/uvx; fi

# Install Python deps first (better layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy only the app code (keep image smaller than copying the whole repo)
COPY src/ ./src/

# Create non-root user and fix permissions
RUN useradd --create-home --shell /bin/bash gsauser \
    && chown -R gsauser:gsauser /app

USER gsauser
ENV PATH="/app/.venv/bin:$PATH"

# Expose port for controller api (Container Apps ingress is disabled in azure_cicd.yml)
EXPOSE 8080

CMD ["uv", "run", "src/main.py"]