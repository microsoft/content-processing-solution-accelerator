#!/bin/bash

# Stop script on any error
set -e

echo "🔍 Fetching container app info from azd environment..."

# Load values from azd env
CONTAINER_WEB_APP_NAME=$(azd env get-value CONTAINER_WEB_APP_NAME)
CONTAINER_WEB_APP_FQDN=$(azd env get-value CONTAINER_WEB_APP_FQDN)

CONTAINER_API_APP_NAME=$(azd env get-value CONTAINER_API_APP_NAME)
CONTAINER_API_APP_FQDN=$(azd env get-value CONTAINER_API_APP_FQDN)

CONTAINER_WORKFLOW_APP_NAME=$(azd env get-value CONTAINER_WORKFLOW_APP_NAME)

# Get subscription and resource group (assuming same for both)
SUBSCRIPTION_ID=$(azd env get-value AZURE_SUBSCRIPTION_ID)
RESOURCE_GROUP=$(azd env get-value AZURE_RESOURCE_GROUP)

# Construct Azure Portal URLs
WEB_APP_PORTAL_URL="https://portal.azure.com/#resource/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$CONTAINER_WEB_APP_NAME"
API_APP_PORTAL_URL="https://portal.azure.com/#resource/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$CONTAINER_API_APP_NAME"
WORKFLOW_APP_PORTAL_URL="https://portal.azure.com/#resource/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$CONTAINER_WORKFLOW_APP_NAME"

echo "✅ Fetched container app info."
echo "Values are as follows:"
echo "  🕒 Started at: $(date)"
echo "  🌍 Web App FQDN: $CONTAINER_WEB_APP_FQDN"
echo "  🌍 API App FQDN: $CONTAINER_API_APP_FQDN"
echo "  🔗 Web App Portal URL: $WEB_APP_PORTAL_URL"
echo "  🔗 API App Portal URL: $API_APP_PORTAL_URL"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Go from infra/scripts → root → src
DATA_SCRIPT_PATH="$SCRIPT_DIR/../../src/ContentProcessorAPI/samples/schemas"

# Normalize the path (optional, in case of ../..)
DATA_SCRIPT_PATH="$(realpath "$DATA_SCRIPT_PATH")"

# Output
echo ""
echo "🧭 Web App Details:"
echo "  ✅ Name: $CONTAINER_WEB_APP_NAME"
echo "  🌐 Endpoint: $CONTAINER_WEB_APP_FQDN"
echo "  🔗 Portal URL: $WEB_APP_PORTAL_URL"

echo ""
echo "🧭 API App Details:"
echo "  ✅ Name: $CONTAINER_API_APP_NAME"
echo "  🌐 Endpoint: $CONTAINER_API_APP_FQDN"
echo "  🔗 Portal URL: $API_APP_PORTAL_URL"

echo ""
echo "🧭 Workflow App Details:"
echo "  ✅ Name: $CONTAINER_WORKFLOW_APP_NAME"
echo "  🔗 Portal URL: $WORKFLOW_APP_PORTAL_URL"

echo ""
echo "📦 Registering schemas and creating schema set..."
echo "  ⏳ Waiting for API to be ready..."

MAX_RETRIES=10
RETRY_INTERVAL=15
API_BASE_URL="https://$CONTAINER_API_APP_FQDN"

for i in $(seq 1 $MAX_RETRIES); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE_URL/schemavault/" 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ]; then
    echo "  ✅ API is ready."
    break
  fi
  echo "  Attempt $i/$MAX_RETRIES – API returned HTTP $STATUS, retrying in ${RETRY_INTERVAL}s..."
  sleep $RETRY_INTERVAL
done

if [ "$STATUS" != "200" ]; then
  echo "  API did not become ready after $MAX_RETRIES attempts. Skipping schema registration."
  echo "  Run manually after the API is ready."
else
  # ---------- Schema registration (no Python dependency) ----------
  SCHEMA_INFO_FILE="$DATA_SCRIPT_PATH/schema_info.json"
  SCHEMAVAULT_URL="$API_BASE_URL/schemavault/"
  SCHEMASETVAULT_URL="$API_BASE_URL/schemasetvault/"

  # --- Step 1: Register schemas ---
  echo ""
  echo "============================================================"
  echo "Step 1: Register schemas"
  echo "============================================================"

  # Fetch existing schemas
  EXISTING_SCHEMAS=$(curl -s "$SCHEMAVAULT_URL" 2>/dev/null || echo "[]")
  EXISTING_COUNT=$(echo "$EXISTING_SCHEMAS" | grep -o '"Id"' | wc -l)
  echo "Fetched $EXISTING_COUNT existing schema(s)."

  # Read schema entries from manifest
  SCHEMA_COUNT=$(cat "$SCHEMA_INFO_FILE" | grep -o '"File"' | wc -l)
  REGISTERED_IDS=()
  REGISTERED_NAMES=()

  for idx in $(seq 0 $((SCHEMA_COUNT - 1))); do
    # Parse entry fields using grep/sed (no python needed)
    ENTRY=$(cat "$SCHEMA_INFO_FILE")
    FILE_NAME=$(echo "$ENTRY" | grep -o '"File"[[:space:]]*:[[:space:]]*"[^"]*"' | sed -n "$((idx + 1))p" | sed 's/.*"File"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
    CLASS_NAME=$(echo "$ENTRY" | grep -o '"ClassName"[[:space:]]*:[[:space:]]*"[^"]*"' | sed -n "$((idx + 1))p" | sed 's/.*"ClassName"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
    DESCRIPTION=$(echo "$ENTRY" | grep -o '"Description"[[:space:]]*:[[:space:]]*"[^"]*"' | sed -n "$((idx + 1))p" | sed 's/.*"Description"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')

    SCHEMA_FILE="$DATA_SCRIPT_PATH/$FILE_NAME"

    echo ""
    echo "Processing schema: $CLASS_NAME"

    if [ ! -f "$SCHEMA_FILE" ]; then
      echo "Error: Schema file '$SCHEMA_FILE' does not exist. Skipping..."
      continue
    fi

    # Check if already registered
    EXISTING_ID=""
    # Use a simple approach: look for the ClassName in the existing schemas response
    if echo "$EXISTING_SCHEMAS" | grep -q "\"ClassName\"[[:space:]]*:[[:space:]]*\"$CLASS_NAME\""; then
      # Extract the Id for this ClassName – find the object containing it
      EXISTING_ID=$(echo "$EXISTING_SCHEMAS" | sed 's/},/}\n/g' | grep "\"ClassName\"[[:space:]]*:[[:space:]]*\"$CLASS_NAME\"" | grep -o '"Id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
    fi

    if [ -n "$EXISTING_ID" ]; then
      echo "  Schema '$CLASS_NAME' already exists with ID: $EXISTING_ID"
      REGISTERED_IDS+=("$EXISTING_ID")
      REGISTERED_NAMES+=("$CLASS_NAME")
      continue
    fi

    echo "  Registering new schema '$CLASS_NAME'..."
    DATA_PAYLOAD="{\"ClassName\": \"$CLASS_NAME\", \"Description\": \"$DESCRIPTION\"}"

    RESPONSE=$(curl -s -w "\n%{http_code}" \
      -X POST "$SCHEMAVAULT_URL" \
      -F "data=$DATA_PAYLOAD" \
      -F "file=@$SCHEMA_FILE;type=text/x-python" \
      --connect-timeout 60)

    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
      SCHEMA_ID=$(echo "$BODY" | sed 's/.*"Id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
      echo "  Successfully registered: $DESCRIPTION's Schema Id - $SCHEMA_ID"
      REGISTERED_IDS+=("$SCHEMA_ID")
      REGISTERED_NAMES+=("$CLASS_NAME")
    else
      echo "  Failed to upload '$FILE_NAME'. HTTP Status: $HTTP_CODE"
      echo "  Error Response: $BODY"
    fi
  done

  # --- Step 2: Create schema set ---
  echo ""
  echo "============================================================"
  echo "Step 2: Create schema set"
  echo "============================================================"

  # Parse schemaset config from manifest
  SET_NAME=$(cat "$SCHEMA_INFO_FILE" | grep -A2 '"schemaset"' | grep '"Name"' | sed 's/.*"Name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
  SET_DESC=$(cat "$SCHEMA_INFO_FILE" | grep -A3 '"schemaset"' | grep '"Description"' | sed 's/.*"Description"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')

  # Fetch existing schema sets
  EXISTING_SETS=$(curl -s "$SCHEMASETVAULT_URL" 2>/dev/null || echo "[]")

  SCHEMASET_ID=""
  if echo "$EXISTING_SETS" | grep -q "\"Name\"[[:space:]]*:[[:space:]]*\"$SET_NAME\""; then
    SCHEMASET_ID=$(echo "$EXISTING_SETS" | sed 's/},/}\n/g' | grep "\"Name\"[[:space:]]*:[[:space:]]*\"$SET_NAME\"" | grep -o '"Id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
    echo "  Schema set '$SET_NAME' already exists with ID: $SCHEMASET_ID"
  else
    echo "  Creating schema set '$SET_NAME'..."
    RESPONSE=$(curl -s -w "\n%{http_code}" \
      -X POST "$SCHEMASETVAULT_URL" \
      -H "Content-Type: application/json" \
      -d "{\"Name\": \"$SET_NAME\", \"Description\": \"$SET_DESC\"}" \
      --connect-timeout 30)

    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
      SCHEMASET_ID=$(echo "$BODY" | sed 's/.*"Id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
      echo "  Created schema set '$SET_NAME' with ID: $SCHEMASET_ID"
    else
      echo "  Failed to create schema set. HTTP Status: $HTTP_CODE"
      echo "  Error Response: $BODY"
    fi
  fi

  if [ -z "$SCHEMASET_ID" ]; then
    echo "Error: Could not create or find schema set. Aborting step 3."
  else
    # --- Step 3: Add schemas to schema set ---
    echo ""
    echo "============================================================"
    echo "Step 3: Add schemas to schema set"
    echo "============================================================"

    ALREADY_IN_SET=$(curl -s "${SCHEMASETVAULT_URL}${SCHEMASET_ID}/schemas" 2>/dev/null || echo "[]")

    # Iterate over registered schemas
    for i in "${!REGISTERED_IDS[@]}"; do
      SCHEMA_ID="${REGISTERED_IDS[$i]}"
      CLASS_NAME="${REGISTERED_NAMES[$i]}"

      if echo "$ALREADY_IN_SET" | grep -q "\"Id\"[[:space:]]*:[[:space:]]*\"$SCHEMA_ID\""; then
        echo "  Schema '$CLASS_NAME' ($SCHEMA_ID) already in schema set - skipped"
        continue
      fi

      RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST "${SCHEMASETVAULT_URL}${SCHEMASET_ID}/schemas" \
        -H "Content-Type: application/json" \
        -d "{\"SchemaId\": \"$SCHEMA_ID\"}" \
        --connect-timeout 30)

      HTTP_CODE=$(echo "$RESPONSE" | tail -1)

      if [ "$HTTP_CODE" = "200" ]; then
        echo "  Added '$CLASS_NAME' ($SCHEMA_ID) to schema set"
      else
        BODY=$(echo "$RESPONSE" | sed '$d')
        echo "  Failed to add '$CLASS_NAME' to schema set. HTTP $HTTP_CODE"
        echo "    Error Response: $BODY"
      fi
    done
  fi

  echo ""
  echo "============================================================"
  echo "Schema registration process completed."
  echo "  Schemas registered: ${#REGISTERED_IDS[@]}"
  echo "============================================================"

  # --- Step 4: Process sample file bundles ---
  if [ -n "$SCHEMASET_ID" ] && [ -n "$REGISTERED_IDS" ]; then
    echo ""
    echo "============================================================"
    echo "Step 4: Process sample file bundles"
    echo "============================================================"

    SAMPLES_DIR="$(realpath "$SCRIPT_DIR/../../src/ContentProcessorAPI/samples")"
    CLAIM_PROCESSOR_URL="$API_BASE_URL/claimprocessor/claims"

    for BUNDLE in claim_date_of_loss claim_hail; do
      BUNDLE_DIR="$SAMPLES_DIR/$BUNDLE"
      BUNDLE_INFO="$BUNDLE_DIR/bundle_info.json"

      if [ ! -f "$BUNDLE_INFO" ]; then
        echo "  Skipping '$BUNDLE' - no bundle_info.json found."
        continue
      fi

      echo ""
      echo "  📂 Processing bundle: $BUNDLE"

      # Step 4a: Create claim batch with schemaset ID
      echo "    - Creating claim batch..."
      RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X PUT "$CLAIM_PROCESSOR_URL" \
        -H "Content-Type: application/json" \
        -d "{\"schema_collection_id\": \"$SCHEMASET_ID\"}" \
        --connect-timeout 30)

      HTTP_CODE=$(echo "$RESPONSE" | tail -1)
      BODY=$(echo "$RESPONSE" | sed '$d')

      if [ "$HTTP_CODE" != "200" ]; then
        echo "    ❌ Failed to create claim batch. HTTP $HTTP_CODE"
        echo "    Error: $BODY"
        continue
      fi

      CLAIM_ID=$(echo "$BODY" | grep -o '"claim_id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
      echo "    ✅ Claim batch created with ID: $CLAIM_ID"

      # Step 4b: Upload each file with its mapped schema ID
      UPLOAD_SUCCESS=true
      FILE_COUNT=$(cat "$BUNDLE_INFO" | grep -o '"file_name"' | wc -l)

      for fidx in $(seq 0 $((FILE_COUNT - 1))); do
        FILE_NAME=$(cat "$BUNDLE_INFO" | grep -o '"file_name"[[:space:]]*:[[:space:]]*"[^"]*"' | sed -n "$((fidx + 1))p" | sed 's/.*"\([^"]*\)"$/\1/')
        SCHEMA_CLASS=$(cat "$BUNDLE_INFO" | grep -o '"schema_class"[[:space:]]*:[[:space:]]*"[^"]*"' | sed -n "$((fidx + 1))p" | sed 's/.*"\([^"]*\)"$/\1/')

        FILE_PATH="$BUNDLE_DIR/$FILE_NAME"

        if [ ! -f "$FILE_PATH" ]; then
          echo "    - File '$FILE_NAME' not found. Skipping."
          continue
        fi

        # Look up schema ID from registered schemas
        SCHEMA_ID=""
        RIDX=0
        for RID in $REGISTERED_IDS; do
          RIDX=$((RIDX + 1))
          RNAME=$(echo "$REGISTERED_NAMES" | tr ' ' '\n' | sed -n "${RIDX}p")
          if [ "$RNAME" = "$SCHEMA_CLASS" ]; then
            SCHEMA_ID="$RID"
            break
          fi
        done

        if [ -z "$SCHEMA_ID" ]; then
          echo "    - No schema ID found for '$SCHEMA_CLASS'. Skipping '$FILE_NAME'."
          continue
        fi

        echo "    - Uploading '$FILE_NAME' (schema: $SCHEMA_CLASS)..."

        DATA_JSON="{\"Claim_Id\": \"$CLAIM_ID\", \"Schema_Id\": \"$SCHEMA_ID\", \"Metadata_Id\": \"sample-$BUNDLE\"}"

        RESPONSE=$(curl -s -w "\n%{http_code}" \
          -X POST "$CLAIM_PROCESSOR_URL/$CLAIM_ID/files" \
          -F "data=$DATA_JSON" \
          -F "file=@$FILE_PATH" \
          --connect-timeout 60)

        HTTP_CODE=$(echo "$RESPONSE" | tail -1)

        if [ "$HTTP_CODE" = "200" ]; then
          echo "    ✅ Uploaded '$FILE_NAME' successfully."
        else
          BODY=$(echo "$RESPONSE" | sed '$d')
          echo "    ❌ Failed to upload '$FILE_NAME'. HTTP $HTTP_CODE"
          echo "    Error: $BODY"
          UPLOAD_SUCCESS=false
        fi
      done

      # Step 4c: Launch processing
      if [ "$UPLOAD_SUCCESS" = true ]; then
        echo "    - Submitting claim batch for processing..."
        RESPONSE=$(curl -s -w "\n%{http_code}" \
          -X POST "$CLAIM_PROCESSOR_URL" \
          -H "Content-Type: application/json" \
          -d "{\"claim_process_id\": \"$CLAIM_ID\"}" \
          --connect-timeout 30)

        HTTP_CODE=$(echo "$RESPONSE" | tail -1)

        if [ "$HTTP_CODE" = "202" ]; then
          echo "    ✅ Claim batch '$CLAIM_ID' submitted for processing."
        else
          BODY=$(echo "$RESPONSE" | sed '$d')
          echo "    ❌ Failed to submit claim batch. HTTP $HTTP_CODE"
          echo "    Error: $BODY"
        fi
      else
        echo "    - Skipping batch submission due to upload failures."
      fi
    done

    echo ""
    echo "============================================================"
    echo "Sample file processing completed."
    echo "============================================================"
  fi
fi

# --- Refresh Content Understanding Cognitive Services account ---
echo ""
echo "============================================================"
echo "Refreshing Content Understanding Cognitive Services account..."
echo "============================================================"

CU_ACCOUNT_NAME=$(azd env get-value CONTENT_UNDERSTANDING_ACCOUNT_NAME 2>/dev/null || echo "")

if [ -z "$CU_ACCOUNT_NAME" ]; then
  echo "  ⚠️ CONTENT_UNDERSTANDING_ACCOUNT_NAME not found in azd env. Skipping refresh."
else
  echo "  Refreshing account: $CU_ACCOUNT_NAME in resource group: $RESOURCE_GROUP"
  if az cognitiveservices account update \
    -g "$RESOURCE_GROUP" \
    -n "$CU_ACCOUNT_NAME" \
    --tags refresh=true \
    --output none; then
    echo "  ✅ Successfully refreshed Cognitive Services account '$CU_ACCOUNT_NAME'."
  else
    echo "  ❌ Failed to refresh Cognitive Services account '$CU_ACCOUNT_NAME'."
  fi
fi


# --- Configure Entra ID authentication (app registrations + EasyAuth) ---
SCRIPT_DIR_SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR_SELF/configure_auth.sh" ]; then
  sed -i 's/\r$//' "$SCRIPT_DIR_SELF/configure_auth.sh"
  bash "$SCRIPT_DIR_SELF/configure_auth.sh" || echo "⚠️ Auth configuration had errors — see output above."
fi
