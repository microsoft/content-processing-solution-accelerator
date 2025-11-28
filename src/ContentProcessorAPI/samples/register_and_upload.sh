#!/bin/bash

# Merged script: Register schemas and upload sample data
# This script combines schema registration and sample data upload into a single process

# Set Python path
PYTHON="/c/Program Files/Python311/python"

# Check if the correct number of arguments is provided
if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "Usage: $0 <API_BASE_URL> [API_CLIENT_ID]"
    echo "Example: $0 https://your-api-endpoint.com"
    echo "         $0 https://your-api-endpoint.com 007d2642-4420-4541-b7e8-8646c2fd4319"
    exit 1
fi

# Assign arguments to variables
API_BASE_URL=$1
API_CLIENT_ID=$2

# Get access token if API_CLIENT_ID is provided
ACCESS_TOKEN=""
AUTH_HEADER=""
if [ -n "$API_CLIENT_ID" ]; then
    echo "🔐 Authenticating with Azure AD..."
    ACCESS_TOKEN=$(az account get-access-token --resource "api://$API_CLIENT_ID" --query accessToken -o tsv 2>/dev/null)
    
    if [ -z "$ACCESS_TOKEN" ]; then
        echo "⚠️  Warning: Failed to get access token. Attempting without authentication..."
        echo "   If the API requires authentication, the requests will fail."
        echo ""
    else
        AUTH_HEADER="Authorization: Bearer $ACCESS_TOKEN"
        echo "✓ Successfully authenticated"
        echo ""
    fi
fi
SCHEMA_VAULT_URL="${API_BASE_URL}/schemavault/"
CONTENT_PROCESSOR_URL="${API_BASE_URL}/contentprocessor/submit"
SAMPLES_DIR="$(cd "$(dirname "$0")" && pwd)"
SCHEMA_DIR="$SAMPLES_DIR/schemas"
SCHEMA_INFO_JSON="$SCHEMA_DIR/schema_info_sh.json"

# Arrays to store schema IDs mapped to their descriptions
declare -A SCHEMA_IDS

echo "=========================================="
echo "Step 1: Registering Schemas"
echo "=========================================="
echo ""

# Validate if the JSON file exists
if [ ! -f "$SCHEMA_INFO_JSON" ]; then
    echo "Error: JSON file '$SCHEMA_INFO_JSON' does not exist."
    exit 1
fi

# Change to the schemas directory
cd "$SCHEMA_DIR" || exit 1

# Parse the JSON file and process each schema entry using Python
"$PYTHON" -c "import json; [print(json.dumps(item)) for item in json.load(open('schema_info_sh.json'))]" | while read -r schema_entry; do
    # Extract file, class name, and description from the JSON entry using Python
    SCHEMA_FILE=$(echo "$schema_entry" | "$PYTHON" -c "import sys, json; print(json.load(sys.stdin)['File'])")
    CLASS_NAME=$(echo "$schema_entry" | "$PYTHON" -c "import sys, json; print(json.load(sys.stdin)['ClassName'])")
    DESCRIPTION=$(echo "$schema_entry" | "$PYTHON" -c "import sys, json; print(json.load(sys.stdin)['Description'])")

    # Validate if the schema file exists
    if [ ! -f "$SCHEMA_FILE" ]; then
        echo "Error: Schema file '$SCHEMA_FILE' does not exist. Skipping..."
        continue
    fi

    # Extract the filename from the file path
    FILENAME=$(basename "$SCHEMA_FILE")

    # Create the JSON payload for the data field using Python
    DATA_JSON=$("$PYTHON" -c "import json; print(json.dumps({'ClassName': '$CLASS_NAME', 'Description': '$DESCRIPTION'}))")

    # Invoke the API with multipart/form-data
    if [ -n "$AUTH_HEADER" ]; then
        RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$SCHEMA_VAULT_URL" \
            -H "$AUTH_HEADER" \
            -H "Content-Type: multipart/form-data" \
            -F "file=@$SCHEMA_FILE;filename=$FILENAME;type=text/x-python" \
            -F "data=$DATA_JSON")
    else
        RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$SCHEMA_VAULT_URL" \
            -H "Content-Type: multipart/form-data" \
            -F "file=@$SCHEMA_FILE;filename=$FILENAME;type=text/x-python" \
            -F "data=$DATA_JSON")
    fi

    # Extract HTTP status code
    HTTP_STATUS=$(echo "$RESPONSE" | sed -n 's/.*HTTP_STATUS://p')
    RESPONSE_BODY=$(echo "$RESPONSE" | sed 's/HTTP_STATUS:.*//')

    # Print the API response
    if [ "$HTTP_STATUS" -eq 200 ]; then
        # Extract Id and Description from the response JSON using Python
        ID=$(echo "$RESPONSE_BODY" | "$PYTHON" -c "import sys, json; data=json.load(sys.stdin); print(data.get('Id', ''))")
        DESC=$(echo "$RESPONSE_BODY" | "$PYTHON" -c "import sys, json; data=json.load(sys.stdin); print(data.get('Description', ''))")
        echo "✓ $DESC's Schema Id - $ID"
        
        # Store the schema ID for later use
        echo "$DESC|$ID" >> /tmp/schema_ids.txt
    else
        echo "✗ Failed to upload '$SCHEMA_FILE'. HTTP Status: $HTTP_STATUS"
        echo "Error Response: $RESPONSE_BODY"
    fi
done

# Wait a moment for the file to be written
sleep 1

echo ""
echo "=========================================="
echo "Step 2: Uploading Sample Data"
echo "=========================================="
echo ""

# Go back to the samples directory
cd "$SAMPLES_DIR" || exit 1

# Read schema IDs from temporary file
if [ ! -f /tmp/schema_ids.txt ]; then
    echo "Error: No schema IDs found. Schema registration may have failed."
    exit 1
fi

# Process each schema and upload corresponding files
while IFS='|' read -r DESCRIPTION SCHEMA_ID; do
    # Determine the folder path based on description
    if [[ "$DESCRIPTION" == "Invoice" ]]; then
        FOLDER_PATH="./invoices"
        FOLDER_NAME="invoices"
    elif [[ "$DESCRIPTION" == "Property Loss Damage Claim Form" ]]; then
        FOLDER_PATH="./propertyclaims"
        FOLDER_NAME="property claims"
    else
        echo "Warning: Unknown description '$DESCRIPTION'. Skipping..."
        continue
    fi

    # Validate if the folder exists
    if [ ! -d "$FOLDER_PATH" ]; then
        echo "Error: Folder '$FOLDER_PATH' does not exist. Skipping..."
        continue
    fi

    echo "Uploading $FOLDER_NAME files using Schema ID: $SCHEMA_ID"
    echo "------------------------------------------"

    # Iterate over all files in the folder
    FILE_COUNT=0
    SUCCESS_COUNT=0
    
    for FILE in "$FOLDER_PATH"/*; do
        # Skip if no files are found
        if [ ! -f "$FILE" ]; then
            echo "No files found in the folder '$FOLDER_PATH'."
            continue
        fi

        FILE_COUNT=$((FILE_COUNT + 1))

        # Extract the filename
        FILENAME=$(basename "$FILE")

        # Create the JSON payload for the data field using Python
        DATA_JSON=$("$PYTHON" -c "import json; print(json.dumps({'Metadata_Id': 'Meta 001', 'Schema_Id': '$SCHEMA_ID'}))")

        # Invoke the API with multipart/form-data
        if [ -n "$AUTH_HEADER" ]; then
            RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$CONTENT_PROCESSOR_URL" \
                -H "$AUTH_HEADER" \
                -H "Content-Type: multipart/form-data" \
                -F "file=@$FILE;filename=$FILENAME" \
                -F "data=$DATA_JSON")
        else
            RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$CONTENT_PROCESSOR_URL" \
                -H "Content-Type: multipart/form-data" \
                -F "file=@$FILE;filename=$FILENAME" \
                -F "data=$DATA_JSON")
        fi

        # Extract HTTP status code
        HTTP_STATUS=$(echo "$RESPONSE" | sed -n 's/.*HTTP_STATUS://p')
        RESPONSE_BODY=$(echo "$RESPONSE" | sed 's/HTTP_STATUS:.*//')

        # Print the API response
        if [ "$HTTP_STATUS" -eq 202 ]; then
            echo "  ✓ Uploaded $FILENAME"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            echo "  ✗ Failed to upload '$FILENAME'. HTTP Status: $HTTP_STATUS"
            echo "    Error Response: $RESPONSE_BODY"
        fi
    done
    
    echo "Uploaded $SUCCESS_COUNT/$FILE_COUNT files for $FOLDER_NAME"
    echo ""
done < /tmp/schema_ids.txt

# Clean up temporary file
rm -f /tmp/schema_ids.txt

echo "=========================================="
echo "Process Complete!"
echo "=========================================="
