#!/bin/bash

# Enhanced Quota Check Script - Finds available region for GPT-5.1 deployment
# Automatically falls back to next available region if first choice has insufficient quota

# Configuration
SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID}"
# AZURE_ENV_GPT_MODEL_CAPACITY is the value used by deployment parameters; default stays at 300.
DEPLOYMENT_CAPACITY="${AZURE_ENV_GPT_MODEL_CAPACITY:-300}"
# GPT_MIN_CAPACITY remains supported for backward compatibility in workflows.
GPT_MIN_CAPACITY="${GPT_MIN_CAPACITY:-0}"

# Prevent quota check/deployment mismatch by always checking at least deployment capacity.
if [[ "$GPT_MIN_CAPACITY" =~ ^[0-9]+$ ]] && [[ "$DEPLOYMENT_CAPACITY" =~ ^[0-9]+$ ]]; then
    if [ "$GPT_MIN_CAPACITY" -gt "$DEPLOYMENT_CAPACITY" ]; then
        REQUIRED_CAPACITY="$GPT_MIN_CAPACITY"
    else
        REQUIRED_CAPACITY="$DEPLOYMENT_CAPACITY"
    fi
else
    echo "❌ ERROR: GPT_MIN_CAPACITY and AZURE_ENV_GPT_MODEL_CAPACITY must be integers."
    exit 1
fi

# List of valid Azure regions for GPT-5.1 GlobalStandard (must match Bicep @allowed values)
ALLOWED_REGIONS=("australiaeast" "centralus" "eastasia" "eastus2" "japaneast" "northeurope" "southeastasia" "swedencentral" "uksouth")

# Parse user-provided regions or use defaults.
# If user provides preferred regions, keep that priority and then append any
# remaining allowed regions as automatic fallback candidates.
if [[ -n "$AZURE_REGIONS" ]]; then
    IFS=',' read -ra USER_REGIONS <<< "$AZURE_REGIONS"
    REGIONS=()

    # Keep user preference order first.
    for region in "${USER_REGIONS[@]}"; do
        clean_region="$(echo "$region" | xargs | tr '[:upper:]' '[:lower:]')"
        if [[ -n "$clean_region" ]]; then
            REGIONS+=("$clean_region")
        fi
    done

    # Append remaining allowed regions for fallback.
    for allowed_region in "${ALLOWED_REGIONS[@]}"; do
        exists=false
        for current_region in "${REGIONS[@]}"; do
            if [[ "$current_region" == "$allowed_region" ]]; then
                exists=true
                break
            fi
        done

        if [[ "$exists" == false ]]; then
            REGIONS+=("$allowed_region")
        fi
    done
else
    REGIONS=("${ALLOWED_REGIONS[@]}")
fi

# Verify Azure CLI is authenticated
echo "🔐 Verifying Azure CLI authentication..."
if ! az account show > /dev/null 2>&1; then
    echo "❌ Error: Azure CLI is not authenticated. Please log in using 'az login'"
    exit 1
fi

# Validate required environment variables
echo "🔄 Validating required environment variables..."
if [[ -z "$SUBSCRIPTION_ID" ]]; then
    echo "❌ ERROR: AZURE_SUBSCRIPTION_ID environment variable is not set."
    exit 1
fi

# Set the subscription
echo "🔄 Setting Azure subscription to: $SUBSCRIPTION_ID"
if ! az account set --subscription "$SUBSCRIPTION_ID"; then
    echo "❌ ERROR: Invalid subscription ID or insufficient permissions."
    exit 1
fi
echo "✅ Azure subscription set successfully."

# Model configuration
declare -A MIN_CAPACITY=(
    ["OpenAI.GlobalStandard.gpt-5.1"]=$REQUIRED_CAPACITY
)

echo "=========================================="
echo "🔍 Quota Check Summary"
echo "=========================================="
echo "Subscription: $SUBSCRIPTION_ID"
echo "Required Model: OpenAI.GlobalStandard.gpt-5.1"
echo "Deployment Capacity: $DEPLOYMENT_CAPACITY TPM"
echo "Minimum Quota Threshold Input: $GPT_MIN_CAPACITY TPM"
echo "Effective Required Capacity: $REQUIRED_CAPACITY TPM"
echo "Checking Regions: ${REGIONS[@]}"
echo "=========================================="

# Function to check quota for a region
check_region_quota() {
    local region=$1
    echo ""
    echo "🔍 Checking region: $region"

    QUOTA_INFO=$(az cognitiveservices usage list --location "$region" --output json 2>/dev/null)
    if [ -z "$QUOTA_INFO" ]; then
        echo "⚠️  WARNING: Failed to retrieve quota info for $region (service may be unavailable)"
        return 1
    fi

    local insufficient_quota=false
    for MODEL in "${!MIN_CAPACITY[@]}"; do
        MODEL_INFO=$(echo "$QUOTA_INFO" | awk -v model="\"value\": \"$MODEL\"" '
            BEGIN { RS="},"; FS="," }
            $0 ~ model { print $0 }
        ')

        if [ -z "$MODEL_INFO" ]; then
            echo "⚠️  WARNING: Model $MODEL not available in $region"
            insufficient_quota=true
            return 1
        fi

        CURRENT_VALUE=$(echo "$MODEL_INFO" | awk -F': ' '/"currentValue"/ {print $2}' | tr -d ',' | tr -d ' ')
        LIMIT=$(echo "$MODEL_INFO" | awk -F': ' '/"limit"/ {print $2}' | tr -d ',' | tr -d ' ')

        CURRENT_VALUE=${CURRENT_VALUE:-0}
        LIMIT=${LIMIT:-0}

        CURRENT_VALUE=$(echo "$CURRENT_VALUE" | cut -d'.' -f1)
        LIMIT=$(echo "$LIMIT" | cut -d'.' -f1)

        AVAILABLE=$((LIMIT - CURRENT_VALUE))

        echo "   Model: $MODEL"
        echo "   Used: $CURRENT_VALUE | Limit: $LIMIT | Available: $AVAILABLE TPM"

        if [ "$AVAILABLE" -lt "${MIN_CAPACITY[$MODEL]}" ]; then
            echo "   ❌ INSUFFICIENT: Need $((MIN_CAPACITY[$MODEL] - AVAILABLE)) more TPM"
            insufficient_quota=true
        else
            echo "   ✅ SUFFICIENT: $AVAILABLE TPM available (Need: ${MIN_CAPACITY[$MODEL]} TPM)"
        fi
    done

    if [ "$insufficient_quota" = false ]; then
        return 0  # Region has sufficient quota
    else
        return 1  # Region has insufficient quota
    fi
}

# Search for a valid region
VALID_REGION=""
for REGION in "${REGIONS[@]}"; do
    if check_region_quota "$REGION"; then
        VALID_REGION="$REGION"
        break
    fi
done

# Output results
echo ""
echo "=========================================="
if [ -z "$VALID_REGION" ]; then
    echo "❌ DEPLOYMENT BLOCKED - No region with sufficient quota"
    echo "=========================================="
    echo ""
    echo "⚠️  All checked regions have insufficient quota for GPT-5.1 GlobalStandard"
    echo ""
    echo "Options:"
    echo "1. Request a quota increase: https://aka.ms/oai/quotarequest"
    echo "2. Reduce gptDeploymentCapacity parameter (currently set to $DEPLOYMENT_CAPACITY TPM)"
    echo "3. Try a different Azure subscription"
    echo ""
    echo "Deployment cannot proceed without sufficient quota."
    
    # Set failure flag for CI/CD pipelines
    if [ -n "$GITHUB_ENV" ]; then
        echo "QUOTA_FAILED=true" >> "$GITHUB_ENV"
        echo "VALID_REGION=" >> "$GITHUB_ENV"
    fi
    exit 0  # Exit cleanly so CI can handle the failure
else
    echo "✅ DEPLOYMENT APPROVED - Valid region found"
    echo "=========================================="
    echo ""
    echo "Selected Region: $VALID_REGION"
    echo "This region has sufficient quota for GPT-5.1 GlobalStandard deployment"
    echo ""
    
    # Export for CI/CD pipelines
    if [ -n "$GITHUB_ENV" ]; then
        echo "QUOTA_FAILED=false" >> "$GITHUB_ENV"
        echo "VALID_REGION=$VALID_REGION" >> "$GITHUB_ENV"
    fi
    
    # Also export as environment variable for immediate use
    export VALID_REGION
    echo "Environment variable set: VALID_REGION=$VALID_REGION"
    exit 0
fi
