#!/bin/bash

# List of valid Azure regions for AI Services (must match Bicep @allowed values)
# These are the only regions where GPT-5.1 GlobalStandard is available
ALLOWED_REGIONS=("australiaeast" "centralus" "eastasia" "eastus2" "japaneast" "northeurope" "southeastasia" "swedencentral" "uksouth")

# Get requested regions from environment variable, default to all allowed regions
# Supports comma-separated or space-separated (or mixed) AZURE_REGIONS values.
if [[ -n "$AZURE_REGIONS" ]]; then
    IFS=', ' read -ra REQUESTED_REGIONS <<< "$AZURE_REGIONS"
    # Filter requested regions to only include those in ALLOWED_REGIONS
    REGIONS=()
    for req_region in "${REQUESTED_REGIONS[@]}"; do
        req_region=$(echo "$req_region" | xargs)  # trim whitespace
        [[ -z "$req_region" ]] && continue  # skip empty tokens from double-delimiters
        for allowed in "${ALLOWED_REGIONS[@]}"; do
            if [[ "$req_region" == "$allowed" ]]; then
                REGIONS+=("$req_region")
                break
            fi
        done
    done
    if [[ ${#REGIONS[@]} -eq 0 ]]; then
        echo "⚠️ WARNING: No valid regions found in AZURE_REGIONS. Using all allowed regions."
        REGIONS=("${ALLOWED_REGIONS[@]}")
    fi
else
    REGIONS=("${ALLOWED_REGIONS[@]}")
fi

SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID}"
GPT_MIN_CAPACITY="${GPT_MIN_CAPACITY}"

# Verify Azure CLI is already authenticated (via OIDC in the workflow)
echo "Verifying Azure CLI authentication..."
if ! az account show > /dev/null 2>&1; then
   echo "❌ Error: Azure CLI is not authenticated. Please log in using 'az login'"
   exit 1
fi

echo "🔄 Validating required environment variables..."
if [[ -z "$SUBSCRIPTION_ID" || -z "$GPT_MIN_CAPACITY" || -z "$REGIONS" ]]; then
    echo "❌ ERROR: Missing required environment variables."
    exit 1
fi

echo "🔄 Setting Azure subscription..."
if ! az account set --subscription "$SUBSCRIPTION_ID"; then
    echo "❌ ERROR: Invalid subscription ID or insufficient permissions."
    exit 1
fi
echo "✅ Azure subscription set successfully."

# Define models and their minimum required capacities
declare -A MIN_CAPACITY=(
    ["OpenAI.GlobalStandard.gpt-5.1"]=$GPT_MIN_CAPACITY
)

VALID_REGION=""
for REGION in "${REGIONS[@]}"; do
    echo "----------------------------------------"
    echo "🔍 Checking region: $REGION"

    QUOTA_INFO=$(az cognitiveservices usage list --location "$REGION" --output json)
    if [ -z "$QUOTA_INFO" ]; then
        echo "⚠️ WARNING: Failed to retrieve quota for region $REGION. Skipping."
        continue
    fi

    INSUFFICIENT_QUOTA=false
    for MODEL in "${!MIN_CAPACITY[@]}"; do
        MODEL_INFO=$(echo "$QUOTA_INFO" | awk -v model="\"value\": \"$MODEL\"" '
            BEGIN { RS="},"; FS="," }
            $0 ~ model { print $0 }
        ')

        if [ -z "$MODEL_INFO" ]; then
            echo "⚠️ WARNING: No quota information found for model: $MODEL in $REGION. Skipping."
            INSUFFICIENT_QUOTA=true
            continue
        fi

        CURRENT_VALUE=$(echo "$MODEL_INFO" | awk -F': ' '/"currentValue"/ {print $2}' | tr -d ',' | tr -d ' ')
        LIMIT=$(echo "$MODEL_INFO" | awk -F': ' '/"limit"/ {print $2}' | tr -d ',' | tr -d ' ')

        CURRENT_VALUE=${CURRENT_VALUE:-0}
        LIMIT=${LIMIT:-0}

        CURRENT_VALUE=$(echo "$CURRENT_VALUE" | cut -d'.' -f1)
        LIMIT=$(echo "$LIMIT" | cut -d'.' -f1)

        AVAILABLE=$((LIMIT - CURRENT_VALUE))

        echo "✅ Model: $MODEL | Used: $CURRENT_VALUE | Limit: $LIMIT | Available: $AVAILABLE"

        if [ "$AVAILABLE" -lt "${MIN_CAPACITY[$MODEL]}" ]; then
            echo "❌ ERROR: $MODEL in $REGION has insufficient quota."
            INSUFFICIENT_QUOTA=true
            break
        fi
    done

    if [ "$INSUFFICIENT_QUOTA" = false ]; then
        VALID_REGION="$REGION"
        VALID_REGION_AVAILABLE_CAPACITY=$AVAILABLE
        break
    fi

done

if [ -z "$VALID_REGION" ]; then
    echo "❌ No region with sufficient quota found. Blocking deployment."
    echo "QUOTA_FAILED=true" >> "$GITHUB_ENV"
    exit 1
else
    echo "✅ Suggested Region: $VALID_REGION"
    echo "✅ Available Capacity: $VALID_REGION_AVAILABLE_CAPACITY"
    echo "VALID_REGION=$VALID_REGION" >> "$GITHUB_ENV"
    echo "AVAILABLE_CAPACITY=$VALID_REGION_AVAILABLE_CAPACITY" >> "$GITHUB_ENV"
    exit 0
fi
