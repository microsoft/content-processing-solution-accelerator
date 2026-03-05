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
  echo "  ⚠️  API did not become ready after $MAX_RETRIES attempts. Skipping schema registration."
  echo "  👉 Run manually: cd $DATA_SCRIPT_PATH && python register_schema.py $API_BASE_URL schema_info.json"
else
  python "$DATA_SCRIPT_PATH/register_schema.py" "$API_BASE_URL" "$DATA_SCRIPT_PATH/schema_info.json"
  echo "  ✅ Schema registration complete."
fi
