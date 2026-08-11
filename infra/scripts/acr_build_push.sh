#!/bin/bash
 
# =============================================================================
# ACR Build and Push Script
# This script builds container images remotely using Azure Container Registry
# and updates the Container Apps to use the new images.
# =============================================================================
 
set -e

RESOURCE_GROUP_NAME="$1"
 
echo "============================================================"
echo "ACR Build and Push - Starting..."
echo "============================================================"
 
if [ -z "$RESOURCE_GROUP_NAME" ]; then

    echo "Using azd environment values..."

    ACR_NAME=$(azd env get-value CONTAINER_REGISTRY_NAME)
    ACR_LOGIN_SERVER=$(azd env get-value CONTAINER_REGISTRY_LOGIN_SERVER)
    RESOURCE_GROUP=$(azd env get-value AZURE_RESOURCE_GROUP)

    CONTAINER_APP_NAME=$(azd env get-value CONTAINER_APP_NAME)
    CONTAINER_API_APP_NAME=$(azd env get-value CONTAINER_API_APP_NAME)
    CONTAINER_WEB_APP_NAME=$(azd env get-value CONTAINER_WEB_APP_NAME)
    CONTAINER_WORKFLOW_APP_NAME=$(azd env get-value CONTAINER_WORKFLOW_APP_NAME)

else

    echo "Using existing deployment from Resource Group: $RESOURCE_GROUP_NAME"

    RESOURCE_GROUP="$RESOURCE_GROUP_NAME"

    ACR_NAME=$(az acr list \
        --resource-group "$RESOURCE_GROUP" \
        --query "[0].name" \
        -o tsv)

    ACR_LOGIN_SERVER=$(az acr show \
        --name "$ACR_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query loginServer \
        -o tsv)

    while read APP; do

            case "$APP" in

        *-app)
            CONTAINER_APP_NAME="$APP"
            ;;

        *-api)
            CONTAINER_API_APP_NAME="$APP"
            ;;

        *-web)
            CONTAINER_WEB_APP_NAME="$APP"
            ;;

        *-wkfl)
            CONTAINER_WORKFLOW_APP_NAME="$APP"
            ;;

    esac

    done < <(
        az containerapp list \
            --resource-group "$RESOURCE_GROUP" \
            --query "[].name" \
            -o tsv
    )

fi
 
IMAGE_TAG="latest"
DEPLOYMENT_TYPE=$(az group show \
    --name "$RESOURCE_GROUP" \
    --query "tags.Type" \
    -o tsv)

if [ "$DEPLOYMENT_TYPE" = "WAF" ]; then

    echo ""
    echo "WAF deployment detected. Temporarily relaxing ACR restrictions..."

    az acr update \
        --name "$ACR_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --allow-exports true

    az acr update \
        --name "$ACR_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --public-network-enabled true

    az acr update \
        --name "$ACR_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --default-action Allow

    echo "ACR restrictions temporarily relaxed."

fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Navigate to repo root (infra/scripts -> root)
REPO_ROOT="$(realpath "$SCRIPT_DIR/../..")"
 
echo ""
echo "  ACR Name: $ACR_NAME"
echo "  ACR Login Server: $ACR_LOGIN_SERVER"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Image Tag: $IMAGE_TAG"
echo ""
 
cleanup() {

    if [ "$DEPLOYMENT_TYPE" = "WAF" ]; then

        echo ""
        echo "Restoring WAF ACR configuration..."

        az acr update \
            --name "$ACR_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --default-action Deny

        az acr update \
            --name "$ACR_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --public-network-enabled false

        az acr update \
            --name "$ACR_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --allow-exports false

        echo "ACR configuration restored."

    fi
}

trap cleanup EXIT

# =============================================================================
# Step 1: Build and push images to ACR using az acr build
# =============================================================================
echo "============================================================"
echo "Step 1: Building and pushing images to ACR..."
echo "============================================================"
 
# --- ContentProcessor ---
echo ""
echo "  Building contentprocessor image..."
az acr build \
  --registry "$ACR_NAME" \
  --image "contentprocessor:$IMAGE_TAG" \
  --file "$REPO_ROOT/src/ContentProcessor/Dockerfile" \
  --platform linux \
  "$REPO_ROOT/src/ContentProcessor"
 
echo "  ✅ contentprocessor image built and pushed."
 
# --- ContentProcessorAPI ---
echo ""
echo "  Building contentprocessorapi image..."
az acr build \
  --registry "$ACR_NAME" \
  --image "contentprocessorapi:$IMAGE_TAG" \
  --file "$REPO_ROOT/src/ContentProcessorAPI/Dockerfile" \
  --platform linux \
  "$REPO_ROOT/src/ContentProcessorAPI"
 
echo "  ✅ contentprocessorapi image built and pushed."
 
# --- ContentProcessorWeb ---
echo ""
echo "  Building contentprocessorweb image..."
az acr build \
  --registry "$ACR_NAME" \
  --image "contentprocessorweb:$IMAGE_TAG" \
  --file "$REPO_ROOT/src/ContentProcessorWeb/Dockerfile" \
  --platform linux \
  "$REPO_ROOT/src/ContentProcessorWeb"
 
echo "  ✅ contentprocessorweb image built and pushed."
 
# --- ContentProcessorWorkflow ---
echo ""
echo "  Building contentprocessorworkflow image..."
az acr build \
  --registry "$ACR_NAME" \
  --image "contentprocessorworkflow:$IMAGE_TAG" \
  --file "$REPO_ROOT/src/ContentProcessorWorkflow/Dockerfile" \
  --platform linux \
  "$REPO_ROOT/src/ContentProcessorWorkflow"
 
echo "  ✅ contentprocessorworkflow image built and pushed."
 
echo ""
echo "  All images built and pushed successfully."
 
# =============================================================================
# Step 2: Update Container Apps to use the new images from ACR
# =============================================================================
echo ""
echo "============================================================"
echo "Step 2: Updating Container Apps with new images..."
echo "============================================================"
 
# --- Update ContentProcessor Container App ---
echo ""
echo "  Updating $CONTAINER_APP_NAME..."
az containerapp update \
  --name "$CONTAINER_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --image "$ACR_LOGIN_SERVER/contentprocessor:$IMAGE_TAG"
 
echo "  ✅ $CONTAINER_APP_NAME updated."
 
# --- Update ContentProcessorAPI Container App ---
echo ""
echo "  Updating $CONTAINER_API_APP_NAME..."
az containerapp update \
  --name "$CONTAINER_API_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --image "$ACR_LOGIN_SERVER/contentprocessorapi:$IMAGE_TAG"
 
echo "  ✅ $CONTAINER_API_APP_NAME updated."
 
# --- Update ContentProcessorWeb Container App ---
echo ""
echo "  Updating $CONTAINER_WEB_APP_NAME..."
az containerapp update \
  --name "$CONTAINER_WEB_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --image "$ACR_LOGIN_SERVER/contentprocessorweb:$IMAGE_TAG"
 
echo "  ✅ $CONTAINER_WEB_APP_NAME updated."
 
# --- Update ContentProcessorWorkflow Container App ---
echo ""
echo "  Updating $CONTAINER_WORKFLOW_APP_NAME..."
az containerapp update \
  --name "$CONTAINER_WORKFLOW_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --image "$ACR_LOGIN_SERVER/contentprocessorworkflow:$IMAGE_TAG"
 
echo "  ✅ $CONTAINER_WORKFLOW_APP_NAME updated."
 
echo ""
echo "============================================================"
echo "ACR Build and Push - Completed Successfully!"
echo "============================================================"