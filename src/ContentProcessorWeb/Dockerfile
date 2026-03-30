# Stage 1: Build the React application
FROM mcr.microsoft.com/vscode/devcontainers/javascript-node:22-bookworm AS builder

# Set working directory
WORKDIR /app

# Copy package.json and pnpm lockfile
COPY package.json pnpm-lock.yaml ./

# Ensure pnpm is available
RUN corepack enable && corepack prepare pnpm@10.28.2 --activate

# Install project dependencies
RUN pnpm install --frozen-lockfile

# Copy the rest of the application code
COPY . .

# Set placeholder values for REACT_APP_* env vars so CRA inlines them
# into the JS bundle. At container startup, env.sh replaces these
# placeholder strings with real values from the container environment.
ENV REACT_APP_WEB_CLIENT_ID=APP_WEB_CLIENT_ID \
    REACT_APP_WEB_AUTHORITY=APP_WEB_AUTHORITY \
    REACT_APP_REDIRECT_URL=APP_REDIRECT_URL \
    REACT_APP_POST_REDIRECT_URL=APP_POST_REDIRECT_URL \
    REACT_APP_WEB_SCOPE=APP_WEB_SCOPE \
    REACT_APP_API_SCOPE=APP_API_SCOPE \
    REACT_APP_API_BASE_URL=APP_API_BASE_URL \
    REACT_APP_AUTH_ENABLED=APP_AUTH_ENABLED \
    REACT_APP_CONSOLE_LOG_ENABLED=APP_CONSOLE_LOG_ENABLED

# Build the application
RUN pnpm build

# Stage 2: Serve the application with NGINX
FROM mcr.microsoft.com/azurelinux/base/nginx:1.25

# Copy the built files from the previous stage
COPY --from=builder /app/build /usr/share/nginx/html

#https://mcr.microsoft.com/en-us/artifact/mar/azurelinux/base/nginx/about
COPY /nginx-custom.conf /etc/nginx/nginx.conf

COPY env.sh /docker-entrypoint.d/env.sh
RUN chmod +x /docker-entrypoint.d/env.sh
RUN sed -i 's/\r$//' /docker-entrypoint.d/env.sh

# Expose the application port
EXPOSE 3000

# Start NGINX and run env.sh
CMD ["/bin/sh", "-c", "/docker-entrypoint.d/env.sh && nginx -g 'daemon off;'"]
