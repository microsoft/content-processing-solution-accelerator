#!/bin/bash

# Check if the correct number of arguments is provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <API_ENDPOINT_URL> <SCHEMA_INFO_JSON>"
    exit 1
fi

# Assign arguments to variables
API_ENDPOINT_URL=$1
SCHEMA_INFO_JSON=$2

# Validate if the JSON file exists
if [ ! -f "$SCHEMA_INFO_JSON" ]; then
    echo "Error: JSON file '$SCHEMA_INFO_JSON' does not exist."
    exit 1
fi

# Parse the JSON file and process each schema entry
jq -c '.[]' "$SCHEMA_INFO_JSON" | while read -r schema_entry; do
    # Extract file, class name, and description from the JSON entry
    SCHEMA_FILE=$(echo "$schema_entry" | jq -r '.File')
    CLASS_NAME=$(echo "$schema_entry" | jq -r '.ClassName')
    DESCRIPTION=$(echo "$schema_entry" | jq -r '.Description')

    # Validate if the schema file exists
    if [ ! -f "$SCHEMA_FILE" ]; then
        echo "Error: Schema file '$SCHEMA_FILE' does not exist. Skipping..."
        continue
    fi

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
        ID=$(echo "$RESPONSE_BODY" | jq -r '.Id')
        DESC=$(echo "$RESPONSE_BODY" | jq -r '.Description')
        echo "$DESC's Schema Id - $ID"
    else
        echo "Failed to upload '$SCHEMA_FILE'. HTTP Status: $HTTP_STATUS"
        echo "Error Response: $RESPONSE_BODY"
    fi
done
