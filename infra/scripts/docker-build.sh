#!/bin/bash

echo "In shell script"

echo $1
echo $2
echo $3
echo $4
echo $5
echo $6

# Check if the required arguments are provided
if [ "$#" -ne 5 ]; then
    echo "Usage: docker-build.sh <AZURE_SUBSCRIPTION_ID> <ENV_NAME> <AZURE_LOCATION> <AZURE_RESOURCE_GROUP> <USE_LOCAL_BUILD> <AZURE_ENV_IMAGETAG>"
    exit 1
fi

AZURE_SUBSCRIPTION_ID=$1
ENV_NAME=$2
AZURE_LOCATION=$3
AZURE_RESOURCE_GROUP=$4
USE_LOCAL_BUILD=$5
AZURE_ENV_IMAGETAG=$6

USE_LOCAL_BUILD=$(echo "$USE_LOCAL_BUILD" | grep -iq "^true$" && echo "true" || echo "false")

if [ "$USE_LOCAL_BUILD" = "true" ]; then
    echo "Local Build enabled. Starting build process."
    az account set --subscription "$AZURE_SUBSCRIPTION_ID"

    # Deploy container registry
    echo "Deploying container registry in location: $AZURE_LOCATION"
    OUTPUTS=$(az deployment group create --resource-group "$AZURE_RESOURCE_GROUP" \
        --template-file "./infra/deploy_container_registry.bicep" \
        --parameters environmentName="$ENV_NAME" --query "properties.outputs" --output json)

    ACR_NAME=$(echo "$OUTPUTS" | jq -r '.createdAcrName.value')
    ACR_ENDPOINT=$(echo "$OUTPUTS" | jq -r '.acrEndpoint.value')

    echo "Extracted ACR Name: $ACR_NAME"
    echo "Extracted ACR Endpoint: $ACR_ENDPOINT"

    # Store outputs in a .env file
    echo -e "ACR_NAME=$ACR_NAME\nACR_ENDPOINT=$ACR_ENDPOINT" > .env

    # Set AZD environment variables
    azd env set ACR_NAME "$ACR_NAME"
    azd env set ACR_ENDPOINT "$ACR_ENDPOINT"

    echo "Saved ACR details to AZD environment variables."
    echo "Deployed container registry in location."

    # Construct full image names
    CONTENTPROCESSOR_IMAGE_URI="$ACR_NAME.azurecr.io/contentprocessor:$AZURE_ENV_IMAGETAG"
    CONTENTPROCESSORAPI_IMAGE_URI="$ACR_NAME.azurecr.io/contentprocessorapi:$AZURE_ENV_IMAGETAG"
    CONTENTPROCESSORWEB_IMAGE_URI="$ACR_NAME.azurecr.io/contentprocessorweb:$AZURE_ENV_IMAGETAG"

    # Azure login
    echo "Logging into Azure Container Registry: $ACR_NAME"
    if ! az acr login -n "$ACR_NAME"; then
        echo "Failed to log in to ACR"
        exit 1
    fi

    # Build and push Docker images
    for service in "ContentProcessor" "ContentProcessorAPI" "ContentProcessorWeb"; do
        IMAGE_VAR_NAME="${service^^}_IMAGE_URI"
        IMAGE_URI=${!IMAGE_VAR_NAME}

        echo "Building Docker image: $IMAGE_URI"
        if ! docker build "./src/$service/." --no-cache -t "$IMAGE_URI"; then
            echo "Failed to build Docker image"
            exit 1
        fi

        echo "Pushing Docker image to ACR: $IMAGE_URI"
        if ! docker push "$IMAGE_URI"; then
            echo "Failed to push Docker image"
            exit 1
        fi

        echo "Docker image pushed successfully: $IMAGE_URI"
    done
else
    echo "Local Build not enabled. Using prebuilt image."
fi
