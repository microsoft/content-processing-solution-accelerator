#!/bin/bash

# Check if the correct number of arguments is provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <API_ENDPOINT_URL> <SCHEMA_INFO_JSON>"
    exit 1
fi

# Assign arguments to variables
API_ENDPOINT_URL=$1
SCHEMA_INFO_JSON=$2
GITHUB_OUTPUT_FILE=${GITHUB_OUTPUT:-/tmp/schema_output.txt}

# Validate if the JSON file exists
if [ ! -f "$SCHEMA_INFO_JSON" ]; then
    echo "Error: JSON file '$SCHEMA_INFO_JSON' does not exist."
    exit 1
fi

# Ensure API_ENDPOINT_URL ends with /schemavault or /schemavault/
# Extract base URL and construct proper GET endpoint
if [[ "$API_ENDPOINT_URL" =~ /schemavault/?$ ]]; then
    # Remove trailing slash if present, then add it back
    BASE_URL="${API_ENDPOINT_URL%/}"
    GET_URL="$BASE_URL/"
else
    # Assume it's just the base URL
    GET_URL="${API_ENDPOINT_URL%/}/schemavault/"
fi

# Get all existing schemas
echo "Fetching existing schemas from: $GET_URL"
EXISTING_SCHEMAS=$(curl -s -X GET "$GET_URL")

# Check if curl succeeded and returned valid JSON
if [ $? -ne 0 ] || ! echo "$EXISTING_SCHEMAS" | jq empty 2>/dev/null; then
    echo "Warning: Could not fetch existing schemas or invalid JSON response. Proceeding with registration..."
    EXISTING_SCHEMAS="[]"
else
    SCHEMA_COUNT=$(echo "$EXISTING_SCHEMAS" | jq 'length')
    echo "Successfully fetched $SCHEMA_COUNT existing schema(s)."
fi

# Parse the JSON file and process each schema entry
jq -c '.[]' "$SCHEMA_INFO_JSON" | while read -r schema_entry; do
    # Extract file, class name, and description from the JSON entry
    SCHEMA_FILE=$(echo "$schema_entry" | jq -r '.File')
    CLASS_NAME=$(echo "$schema_entry" | jq -r '.ClassName')
    DESCRIPTION=$(echo "$schema_entry" | jq -r '.Description')

    echo ""
    echo "Processing schema: $CLASS_NAME"

    # Validate if the schema file exists
    if [ ! -f "$SCHEMA_FILE" ]; then
        echo "Error: Schema file '$SCHEMA_FILE' does not exist. Skipping..."
        continue
    fi

    # Check if schema with same ClassName already exists
    EXISTING_ID=$(echo "$EXISTING_SCHEMAS" | jq -r --arg className "$CLASS_NAME" '.[] | select(.ClassName == $className) | .Id' 2>/dev/null | head -n 1)
    
    if [ -n "$EXISTING_ID" ] && [ "$EXISTING_ID" != "null" ]; then
        EXISTING_DESC=$(echo "$EXISTING_SCHEMAS" | jq -r --arg className "$CLASS_NAME" '.[] | select(.ClassName == $className) | .Description' 2>/dev/null | head -n 1)
        echo "✓ Schema '$CLASS_NAME' already exists with ID: $EXISTING_ID"
        echo "  Description: $EXISTING_DESC"
        
        # Still output to GitHub output file
        SAFE_NAME=$(echo "$CLASS_NAME" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_')
        echo "${SAFE_NAME}_schema_id=$EXISTING_ID" >> "$GITHUB_OUTPUT_FILE"
        continue
    fi

    echo "Registering new schema '$CLASS_NAME'..."

    # Extract the filename from the file path
    FILENAME=$(basename "$SCHEMA_FILE")

    # Create the JSON payload for the data field
    DATA_JSON=$(jq -n --arg ClassName "$CLASS_NAME" --arg Description "$DESCRIPTION" \
        '{ClassName: $ClassName, Description: $Description}')

    # Invoke the API with multipart/form-data
    RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$API_ENDPOINT_URL" \
        -H "Content-Type: multipart/form-data" \
        -F "file=@$SCHEMA_FILE;filename=$FILENAME;type=text/x-python" \
        -F "data=$DATA_JSON")

    # Extract HTTP status code
    HTTP_STATUS=$(echo "$RESPONSE" | sed -n 's/.*HTTP_STATUS://p')
    RESPONSE_BODY=$(echo "$RESPONSE" | sed 's/HTTP_STATUS:.*//')

    # Print the API response
    if [ "$HTTP_STATUS" -eq 200 ]; then
        # Extract Id and Description from the response JSON
        SAFE_NAME=$(echo "$CLASS_NAME" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_')
        ID=$(echo "$RESPONSE_BODY" | jq -r '.Id')
        DESC=$(echo "$RESPONSE_BODY" | jq -r '.Description')
        echo "✓ Successfully registered: $DESC's Schema Id - $ID"
        echo "${SAFE_NAME}_schema_id=$ID" >> "$GITHUB_OUTPUT_FILE"
    else
        echo "✗ Failed to upload '$SCHEMA_FILE'. HTTP Status: $HTTP_STATUS"
        echo "Error Response: $RESPONSE_BODY"
    fi
done

echo ""
echo "Schema registration process completed."