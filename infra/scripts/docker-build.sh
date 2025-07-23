#!/bin/bash

set -e

# Get all environment values
echo "Fetching environment values from azd..."
ENV_VALUES_JSON=$(azd env get-values --output json)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_FILE="$SCRIPT_DIR/../deploy_container_registry.bicep"

get_azd_env_value_or_default() {
    local key="$1"
    local default="$2"
    local required="${3:-false}"

    local value
    value=$(azd env get-value "$key" 2>/dev/null)
    local exit_code=$?

    if [ $exit_code -ne 0 ] || [ -z "$value" ]; then
        if [ "$required" = "true" ]; then
            echo "❌ Required environment key '$key' not found." >&2
            exit 1
        else
            value="$default"
        fi
    fi

    echo "$value"
}

# Required env variables
AZURE_SUBSCRIPTION_ID=$(get_azd_env_value_or_default "AZURE_SUBSCRIPTION_ID" "" true)
ENV_NAME=$(get_azd_env_value_or_default "AZURE_ENV_NAME" "" true)
CONTAINER_APP_USER_IDENTITY_ID=$(get_azd_env_value_or_default "CONTAINER_APP_USER_IDENTITY_ID" "" true)
AZURE_RESOURCE_GROUP=$(get_azd_env_value_or_default "AZURE_RESOURCE_GROUP" "" true)
CONTAINER_APP_USER_PRINCIPAL_ID=$(get_azd_env_value_or_default "CONTAINER_APP_USER_PRINCIPAL_ID" "" true)
AZURE_ENV_IMAGETAG=$(get_azd_env_value_or_default "AZURE_ENV_IMAGETAG" "latest" false)
CONTAINER_WEB_APP_NAME=$(get_azd_env_value_or_default "CONTAINER_WEB_APP_NAME" "" true)
CONTAINER_API_APP_NAME=$(get_azd_env_value_or_default "CONTAINER_API_APP_NAME" "" true)
CONTAINER_APP_NAME=$(get_azd_env_value_or_default "CONTAINER_APP_NAME" "" true)
ACR_NAME=$(get_azd_env_value_or_default "CONTAINER_REGISTRY_NAME" "" true)
ACR_ENDPOINT=$(get_azd_env_value_or_default "CONTAINER_REGISTRY_LOGIN_SERVER" "" true)

echo "Using the following parameters:"
echo "AZURE_SUBSCRIPTION_ID = $AZURE_SUBSCRIPTION_ID"
echo "ENV_NAME = $ENV_NAME"
echo "AZURE_RESOURCE_GROUP = $AZURE_RESOURCE_GROUP"
echo "AZURE_ENV_IMAGETAG = $AZURE_ENV_IMAGETAG"

# Ensure Azure login
echo "Checking Azure login status..."
if ! az account show --only-show-errors &>/dev/null; then
    echo "No active Azure session found. Logging in..."
    az login --only-show-errors
    az account set --subscription "$AZURE_SUBSCRIPTION_ID"
fi

# Deploy container registry
# echo "Deploying container registry..."
# DEPLOY_OUTPUT=$(az deployment group create \
#     --resource-group "$AZURE_RESOURCE_GROUP" \
#     --template-file "$TEMPLATE_FILE" \
#     --parameters environmentName="$ENV_NAME" acrPullPrincipalIds="['$CONTAINER_APP_USER_PRINCIPAL_ID']" \
#     --query "properties.outputs" \
#     --output json)

# ACR_NAME=$(echo "$DEPLOY_OUTPUT" | jq -r '.createdAcrName.value')
# ACR_ENDPOINT=$(echo "$DEPLOY_OUTPUT" | jq -r '.acrEndpoint.value')

# echo "Extracted ACR Name: $ACR_NAME"
# echo "Extracted ACR Endpoint: $ACR_ENDPOINT"

# azd env set ACR_NAME "$ACR_NAME"
# azd env set ACR_ENDPOINT "$ACR_ENDPOINT"

echo "Logging into Azure Container Registry: $ACR_NAME with endpoint $ACR_ENDPOINT"
az acr login -n "$ACR_NAME"

# Build and push function
build_and_push_image() {
    IMAGE_NAME="$1"
    BUILD_PATH="$2"
    CONTAINER_APP="$3"

    IMAGE_URI="$ACR_NAME.azurecr.io/$IMAGE_NAME:$AZURE_ENV_IMAGETAG"
    echo "Building image: $IMAGE_URI"
    docker build "$BUILD_PATH" --no-cache -t "$IMAGE_URI"
    
    echo "Pushing image: $IMAGE_URI"
    docker push "$IMAGE_URI"

    if [ -n "$CONTAINER_APP" ]; then
        echo "Updating container app: $CONTAINER_APP"
        az containerapp registry set \
            --name "$CONTAINER_APP" \
            --resource-group "$AZURE_RESOURCE_GROUP" \
            --server "$ACR_NAME.azurecr.io" \
            --identity "$CONTAINER_APP_USER_IDENTITY_ID" \
            --only-show-errors

        az containerapp update \
            --name "$CONTAINER_APP" \
            --resource-group "$AZURE_RESOURCE_GROUP" \
            --image "$IMAGE_URI" \
            --set-env-vars REFRESH_TIMESTAMP=$(date +%Y%m%d%H%M%S) \
            --only-show-errors

        echo "Updated registry for container app: $CONTAINER_APP"
    fi
}

# Build and push all images
build_and_push_image "contentprocessor" "$SCRIPT_DIR/../../src/ContentProcessor/" "$CONTAINER_APP_NAME"

build_and_push_image "contentprocessorapi" "$SCRIPT_DIR/../../src/ContentProcessorAPI/" "$CONTAINER_API_APP_NAME"

build_and_push_image "contentprocessorweb" "$SCRIPT_DIR/../../src/ContentProcessorWeb/" "$CONTAINER_WEB_APP_NAME"

echo "All Docker images built and pushed successfully."
