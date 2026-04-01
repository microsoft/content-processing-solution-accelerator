FROM mcr.microsoft.com/azurelinux/base/python:3.12 

WORKDIR /app

# Install system dependencies and UV using tdnf (Azure Linux package manager)
RUN tdnf update -y && tdnf install -y \
	tar \
	ca-certificates \
	curl \
	gawk \
	shadow-utils \
	&& tdnf clean all \
	&& curl -LsSf https://astral.sh/uv/install.sh | sh \
	&& mv /root/.local/bin/uv /usr/local/bin/uv

# Copy the application into the container.
COPY . /app

# Install the application dependencies.
WORKDIR /app
RUN uv sync --frozen --no-cache

# Run the application.
CMD [".venv/bin/uvicorn", "app.main:app", "--port", "80", "--host", "0.0.0.0", "--workers", "4"]