#!/bin/bash

# Usage: ./set_conns_env_vars.sh [--tenant TENANT] [--subscription SUBSCRIPTION] [--resource-group RESOURCE_GROUP] [--workspace WORKSPACE] [--include-verbose]

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tenant)
      TENANT="$2"
      shift 2
      ;;
    --subscription)
      SUBSCRIPTION="$2"
      shift 2
      ;;
    --resource-group)
      RESOURCE_GROUP="$2"
      shift 2
      ;;
    --workspace)
      WORKSPACE="$2"
      shift 2
      ;;
    --include-verbose)
      INCLUDE_VERBOSE=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

TENANT="${TENANT:-$AZURE_ORIGINAL_TENANT_ID}"
SUBSCRIPTION="${SUBSCRIPTION:-$AZURE_ORIGINAL_SUBSCRIPTION_ID}"
RESOURCE_GROUP="${RESOURCE_GROUP:-$AZURE_ORIGINAL_RESOURCE_GROUP}"
WORKSPACE="${WORKSPACE:-$AZURE_ORIGINAL_WORKSPACE_NAME}"

if [[ -z "$TENANT" || -z "$SUBSCRIPTION" || -z "$RESOURCE_GROUP" || -z "$WORKSPACE" ]]; then
  read -p "Start with existing Project connections? [NOTE: This action cannot be undone after executing. To revert, create a new AZD environment and run the process again.] (yes/no) " response
  if [[ "$response" == "yes" ]]; then
    [[ -z "$TENANT" ]] && read -p "Enter Tenant ID: " TENANT
    [[ -z "$SUBSCRIPTION" ]] && read -p "Enter Subscription ID: " SUBSCRIPTION
    [[ -z "$RESOURCE_GROUP" ]] && read -p "Enter Resource Group: " RESOURCE_GROUP
    [[ -z "$WORKSPACE" ]] && read -p "Enter Workspace / Project Name: " WORKSPACE
  else
    echo "Not starting with existing Project. Exiting script."
    exit 0
  fi
else
  echo "All parameters provided. Starting with existing Project ${WORKSPACE}."
fi

if [[ -z "$TENANT" || -z "$SUBSCRIPTION" || -z "$RESOURCE_GROUP" || -z "$WORKSPACE" ]]; then
  echo "Unable to start with existing Project: One or more required parameters are missing."
  exit 1
fi

az account set --subscription "$SUBSCRIPTION"

TOKEN=$(az account get-access-token --resource https://management.azure.com --query accessToken -o tsv)
if [[ -z "$TOKEN" ]]; then
  echo "Failed to get Azure access token."
  exit 1
fi

CONNECTIONS_URL="https://management.azure.com/subscriptions/$SUBSCRIPTION/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.MachineLearningServices/workspaces/$WORKSPACE/connections?api-version=2024-10-01"
CONNECTIONS_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" "$CONNECTIONS_URL")
CONNECTIONS=$(echo "$CONNECTIONS_RESPONSE" | jq '.value')

echo "Connections in workspace ${WORKSPACE}"
echo "----------------------------------"
CONNECTION_COUNT=$(echo "$CONNECTIONS" | jq 'length')
echo "Connection count: $CONNECTION_COUNT"
if [[ "$CONNECTION_COUNT" -eq 0 ]]; then
  echo "No connections found in the workspace."
  exit 0
fi

if [[ "$INCLUDE_VERBOSE" == true ]]; then
  echo "Connections response:"
  echo "$CONNECTIONS"
fi
echo "----------------------------------"

COGSVC_URL="https://management.azure.com/subscriptions/$SUBSCRIPTION/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/?api-version=2023-05-01"
COGSVC_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" "$COGSVC_URL")
COGSVC_ACCOUNTS=$(echo "$COGSVC_RESPONSE" | jq '.value')

echo "Cognitive Service Accounts in resource group ${RESOURCE_GROUP}"
echo "----------------------------------"
COGSVC_COUNT=$(echo "$COGSVC_ACCOUNTS" | jq 'length')
echo "Cognitive Service Account count: $COGSVC_COUNT"
if [[ "$COGSVC_COUNT" -eq 0 ]]; then
  echo "No Cognitive Service Accounts found in the resource group."
  exit 0
fi

if [[ "$INCLUDE_VERBOSE" == true ]]; then
  echo "Cognitive Service Accounts response:"
  echo "$COGSVC_ACCOUNTS"
fi

for i in $(seq 0 $(($COGSVC_COUNT - 1))); do
  ACCOUNT_NAME=$(echo "$COGSVC_ACCOUNTS" | jq -r ".[$i].name")
  NORMALIZED_ACCOUNT_NAME=$(echo "$ACCOUNT_NAME" | tr -d '-_')
  echo "Normalized Cognitive Service Account Name: $NORMALIZED_ACCOUNT_NAME"
done
echo "----------------------------------"

echo "Connections details:"
echo "----------------------------------"
for i in $(seq 0 $(($CONNECTION_COUNT - 1))); do
  NAME=$(echo "$CONNECTIONS" | jq -r ".[$i].name")
  AUTHTYPE=$(echo "$CONNECTIONS" | jq -r ".[$i].properties.authType")
  CATEGORY=$(echo "$CONNECTIONS" | jq -r ".[$i].properties.category")
  TARGET=$(echo "$CONNECTIONS" | jq -r ".[$i].properties.target")

  echo "Name: $NAME"
  echo "AuthType: $AUTHTYPE"
  echo "Category: $CATEGORY"
  echo "Target: $TARGET"

  if [[ "$CATEGORY" == "CognitiveSearch" ]]; then
    azd env set 'AZURE_AI_SEARCH_ENABLED' 'true'
    echo "Environment variable AZURE_AI_SEARCH_ENABLED set to true"
  fi

  if [[ "$CATEGORY" == "CognitiveService" ]]; then
    for j in $(seq 0 $(($COGSVC_COUNT - 1))); do
      ACCOUNT_NAME=$(echo "$COGSVC_ACCOUNTS" | jq -r ".[$j].name")
      NORMALIZED_ACCOUNT_NAME=$(echo "$ACCOUNT_NAME" | tr -d '-_')
      if [[ "$NORMALIZED_ACCOUNT_NAME" == "$NAME" ]]; then
        RESOURCE_NAME="$ACCOUNT_NAME"
        KIND=$(echo "$COGSVC_ACCOUNTS" | jq -r ".[$j].kind")
        echo "Matched Cognitive Service Account - Connection: '$NAME' Resource: $RESOURCE_NAME"
        case "$KIND" in
          ContentSafety)
            azd env set 'AZURE_AI_CONTENT_SAFETY_ENABLED' 'true'
            echo "Environment variable AZURE_AI_CONTENT_SAFETY_ENABLED set to true"
            ;;
          SpeechServices)
            azd env set 'AZURE_AI_SPEECH_ENABLED' 'true'
            echo "Environment variable AZURE_AI_SPEECH_ENABLED set to true"
            ;;
          FormRecognizer)
            azd env set 'AZURE_AI_DOC_INTELLIGENCE_ENABLED' 'true'
            echo "Environment variable AZURE_AI_DOC_INTELLIGENCE_ENABLED set to true"
            ;;
          ComputerVision)
            azd env set 'AZURE_AI_VISION_ENABLED' 'true'
            echo "Environment variable AZURE_AI_VISION_ENABLED set to true"
            ;;
          TextAnalytics)
            azd env set 'AZURE_AI_LANGUAGE_ENABLED' 'true'
            echo "Environment variable AZURE_AI_LANGUAGE_ENABLED set to true"
            ;;
          TextTranslation)
            azd env set 'AZURE_AI_TRANSLATOR_ENABLED' 'true'
            echo "Environment variable AZURE_AI_TRANSLATOR_ENABLED set to true"
            ;;
          *)
            echo "Unknown resource kind: $KIND"
            ;;
        esac
      fi
    done
  fi
  echo "-------------------------"
done
echo "----------------------------------"