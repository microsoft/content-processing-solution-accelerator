#!/bin/sh

echo "Pull latest code for the current branch"
git fetch
git pull

set -e  # Exit on error

echo "Setting up ContentProcessor..."
cd ./src/ContentProcessor
uv sync --frozen
cd ../../

echo "Setting up ContentProcessorApi..."
cd ./src/ContentProcessorAPI
uv sync --frozen
cd ../../

echo "Installing dependencies for ContentProcessorWeb..."
cd ./src/ContentProcessorWeb
pnpm install

cd ../../

echo "Setting up executable permission for shell scripts"
sed -i 's/\r$//' infra/scripts/post_deployment.sh
sudo chmod +x infra/scripts/docker-build.sh
sudo chmod +x infra/scripts/post_deployment.sh
sudo chmod +x src/ContentProcessorAPI/samples/upload_files.sh
# register_schema.py is cross-platform and does not need chmod

echo "Setup complete! 🎉"
