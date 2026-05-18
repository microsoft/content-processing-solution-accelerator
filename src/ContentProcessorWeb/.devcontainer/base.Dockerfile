# [Choice] Node.js version (use -bullseye variants on local arm64/Apple Silicon): 18, 16, 14, 18-bullseye, 16-bullseye, 14-bullseye, 18-buster, 16-buster, 14-buster
ARG VARIANT=latest
FROM mcr.microsoft.com/vscode/devcontainers/javascript-node:${VARIANT}

# Install tslint, typescript. eslint is installed by javascript image
# ARG NODE_MODULES="tslint-to-eslint-config typescript"
# COPY library-scripts/meta.env /usr/local/etc/vscode-dev-containers
# RUN su node -c "umask 0002 && npm install -g ${NODE_MODULES}" \
#     && npm cache clean --force > /dev/null 2>&1
# RUN su node -c "npm install -g yarn"
# RUN su node -c "npm install yarn react-app-rewired"

RUN npm install -g tslint-to-eslint-config typescript
RUN npm install -g pnpm@10.28.2
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