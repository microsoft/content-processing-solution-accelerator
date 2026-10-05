#!/bin/bash

# Check if the correct number of arguments is provided
if [ "$#" -lt 3 ] || [ "$#" -gt 4 ]; then
    echo "Usage: $0 <API_ENDPOINT_URL> <FOLDER_PATH> <SCHEMA_ID> [ACCESS_TOKEN]"
    exit 1
fi

# Assign arguments to variables
API_ENDPOINT_URL=$1
FOLDER_PATH=$2
SCHEMA_ID=$3
# Optional bearer token, from the 4th positional arg or the ACCESS_TOKEN env var,
# used when the API has authentication enabled. Acquire with:
#   az account get-access-token --resource api://<API_CLIENT_ID> --query accessToken -o tsv
ACCESS_TOKEN="${4:-${ACCESS_TOKEN:-}}"

AUTH_ARGS=()
if [ -n "$ACCESS_TOKEN" ]; then
    AUTH_ARGS=(-H "Authorization: Bearer $ACCESS_TOKEN")
fi

# Validate if the folder exists
if [ ! -d "$FOLDER_PATH" ]; then
    echo "Error: Folder '$FOLDER_PATH' does not exist."
    exit 1
fi

# Iterate over all files in the folder
for FILE in "$FOLDER_PATH"/*; do
    # Skip if no files are found
    if [ ! -f "$FILE" ]; then
        echo "No files found in the folder '$FOLDER_PATH'."
        continue
    fi

    # Extract the filename
    FILENAME=$(basename "$FILE")

    # Create the JSON payload for the data field
    DATA_JSON=$(jq -n --arg Metadata_Id "Meta 001" --arg Schema_Id "$SCHEMA_ID" \
        '{Metadata_Id: $Metadata_Id, Schema_Id: $Schema_Id}')

    # Invoke the API with multipart/form-data
    RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$API_ENDPOINT_URL" \
        "${AUTH_ARGS[@]+"${AUTH_ARGS[@]}"}" \
        -H "Content-Type: multipart/form-data" \
        -F "file=@$FILE;filename=$FILENAME" \
        -F "data=$DATA_JSON")

    # Extract HTTP status code
    HTTP_STATUS=$(echo "$RESPONSE" | sed -n 's/.*HTTP_STATUS://p')
    RESPONSE_BODY=$(echo "$RESPONSE" | sed 's/HTTP_STATUS:.*//')

    # Print the API response
    if [ "$HTTP_STATUS" -eq 202 ]; then
        echo "Uploaded '$FILENAME' successfully."
        echo "API Response: $RESPONSE_BODY"
    else
        echo "Failed to upload '$FILENAME'. HTTP Status: $HTTP_STATUS"
        echo "Error Response: $RESPONSE_BODY"
    fi
done
