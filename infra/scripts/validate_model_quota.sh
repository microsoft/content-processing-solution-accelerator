#!/bin/bash

LOCATION=""
MODEL=""
DEPLOYMENT_TYPE="Standard"
CAPACITY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      MODEL="$2"
      shift 2
      ;;
    --capacity)
      CAPACITY="$2"
      shift 2
      ;;
    --deployment-type)
      DEPLOYMENT_TYPE="$2"
      shift 2
      ;;
    --location)
      LOCATION="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Verify all required parameters are provided and echo missing ones
MISSING_PARAMS=()

if [[ -z "$LOCATION" ]]; then
    MISSING_PARAMS+=("location")
fi

if [[ -z "$MODEL" ]]; then
    MISSING_PARAMS+=("model")
fi

if [[ -z "$CAPACITY" ]]; then
    MISSING_PARAMS+=("capacity")
fi

if [[ -z "$DEPLOYMENT_TYPE" ]]; then
    MISSING_PARAMS+=("deployment-type")
fi

if [[ ${#MISSING_PARAMS[@]} -ne 0 ]]; then
    echo "❌ ERROR: Missing required parameters: ${MISSING_PARAMS[*]}"
    echo "Usage: $0 --location <LOCATION> --model <MODEL> --capacity <CAPACITY> [--deployment-type <DEPLOYMENT_TYPE>]"
    exit 1
fi

if [[ "$DEPLOYMENT_TYPE" != "Standard" && "$DEPLOYMENT_TYPE" != "GlobalStandard" ]]; then
    echo "❌ ERROR: Invalid deployment type: $DEPLOYMENT_TYPE. Allowed values are 'Standard' or 'GlobalStandard'."
    exit 1
fi

MODEL_TYPE="OpenAI.$DEPLOYMENT_TYPE.$MODEL"

echo "🔍 Checking quota for $MODEL_TYPE in $LOCATION ..."

MODEL_INFO=$(az cognitiveservices usage list --location "$LOCATION" --query "[?name.value=='$MODEL_TYPE']" --output json | tr '[:upper:]' '[:lower:]')

if [ -z "$MODEL_INFO" ]; then
    echo "❌ ERROR: No quota information found for model: $MODEL in location: $LOCATION for model type: $MODEL_TYPE."
    exit 1
fi

if [ -n "$MODEL_INFO" ]; then
    CURRENT_VALUE=$(echo "$MODEL_INFO" | awk -F': ' '/"currentvalue"/ {print $2}' | tr -d ',' | tr -d ' ')
    LIMIT=$(echo "$MODEL_INFO" | awk -F': ' '/"limit"/ {print $2}' | tr -d ',' | tr -d ' ')

    CURRENT_VALUE=${CURRENT_VALUE:-0}
    LIMIT=${LIMIT:-0}

    CURRENT_VALUE=$(echo "$CURRENT_VALUE" | cut -d'.' -f1)
    LIMIT=$(echo "$LIMIT" | cut -d'.' -f1)

    AVAILABLE=$((LIMIT - CURRENT_VALUE))
    echo "✅ Model available - Model: $MODEL_TYPE | Used: $CURRENT_VALUE | Limit: $LIMIT | Available: $AVAILABLE"

    if [ "$AVAILABLE" -lt "$CAPACITY" ]; then
        echo "❌ ERROR: Insufficient quota for model: $MODEL in location: $LOCATION. Available: $AVAILABLE, Requested: $CAPACITY."
        exit 1
    else
        echo "✅ Sufficient quota for model: $MODEL in location: $LOCATION. Available: $AVAILABLE, Requested: $CAPACITY."
    fi
fi
