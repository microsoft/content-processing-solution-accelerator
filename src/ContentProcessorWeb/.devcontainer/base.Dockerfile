ARG VARIANT=24-bookworm
FROM mcr.microsoft.com/devcontainers/javascript-node:${VARIANT}

# Install tslint, typescript. eslint is installed by javascript image
# ARG NODE_MODULES="tslint-to-eslint-config typescript"
# COPY library-scripts/meta.env /usr/local/etc/vscode-dev-containers
# RUN su node -c "umask 0002 && npm install -g --registry=https://packagefeedproxy.microsoft.io/npm/ ${NODE_MODULES}" \
#     && npm cache clean --force > /dev/null 2>&1
# RUN su node -c "npm install -g --registry=https://packagefeedproxy.microsoft.io/npm/ yarn"
# RUN su node -c "npm install --registry=https://packagefeedproxy.microsoft.io/npm/ yarn react-app-rewired"

RUN npm install -g --registry=https://packagefeedproxy.microsoft.io/npm/ tslint-to-eslint-config typescript
RUN npm install -g --registry=https://packagefeedproxy.microsoft.io/npm/ pnpm@10.28.2
# # Install Python
# RUN apt-get update && apt-get install -y python3 python3-pip

# # Install pre-commit
# RUN pip3 install pre-commit


# [Optional] Uncomment this section to install additional OS packages.
# RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
#     && apt-get -y install --no-install-recommends <your-package-list-here>

# [Optional] Uncomment if you want to install an additional version of node using nvm
# ARG EXTRA_NODE_VERSION=10
# RUN su node -c "source /usr/local/share/nvm/nvm.sh && nvm install ${EXTRA_NODE_VERSION}"