#!/bin/bash

# Stop script on any error
set -e

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║   Post-Deployment Configuration                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

echo "🔍 Fetching container app info from azd environment..."

# Load values from azd env
CONTAINER_WEB_APP_NAME=$(azd env get-value CONTAINER_WEB_APP_NAME)
CONTAINER_WEB_APP_FQDN=$(azd env get-value CONTAINER_WEB_APP_FQDN)

CONTAINER_API_APP_NAME=$(azd env get-value CONTAINER_API_APP_NAME)
CONTAINER_API_APP_FQDN=$(azd env get-value CONTAINER_API_APP_FQDN)

# Get subscription and resource group (assuming same for both)
SUBSCRIPTION_ID=$(azd env get-value AZURE_SUBSCRIPTION_ID)
RESOURCE_GROUP=$(azd env get-value AZURE_RESOURCE_GROUP)

# Construct Azure Portal URLs
WEB_APP_PORTAL_URL="https://portal.azure.com/#resource/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$CONTAINER_WEB_APP_NAME"
API_APP_PORTAL_URL="https://portal.azure.com/#resource/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$CONTAINER_API_APP_NAME"

echo "✅ Fetched container app info."
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Go from infra/scripts → root → src
DATA_SCRIPT_PATH="$SCRIPT_DIR/../../src/ContentProcessorAPI/samples"

# Normalize the path (optional, in case of ../..)
DATA_SCRIPT_PATH="$(realpath "$DATA_SCRIPT_PATH")"

# Output
echo ""
echo "🧭 Web App Details:"
echo "  ✅ Name: $CONTAINER_WEB_APP_NAME"
echo "  🌐 Endpoint: https://$CONTAINER_WEB_APP_FQDN"
echo "  🔗 Portal URL: $WEB_APP_PORTAL_URL"

echo ""
echo "🧭 API App Details:"
echo "  ✅ Name: $CONTAINER_API_APP_NAME"
echo "  🌐 Endpoint: https://$CONTAINER_API_APP_FQDN"
echo "  🔗 Portal URL: $API_APP_PORTAL_URL"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ═══════════════════════════════════════════════════════
# STEP 1: Configure Authentication (Manual for Bash)
# ═══════════════════════════════════════════════════════
echo "🔐 STEP 1: Authentication Configuration"
echo ""
echo "⚠️  Note: For automated authentication setup, please use PowerShell:"
echo "    ./infra/scripts/configure_auth_automated.ps1"
echo ""
echo "Or configure manually via Azure Portal:"
echo "  1. Web App Authentication: $WEB_APP_PORTAL_URL/authV2"
echo "  2. API App Authentication: $API_APP_PORTAL_URL/authV2"
echo ""

read -p "Press Enter to continue to schema registration..."

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ═══════════════════════════════════════════════════════
# STEP 2: Register Schemas and Upload Sample Data
# ═══════════════════════════════════════════════════════
echo "📦 STEP 2: Schema Registration & Sample Data Upload"
echo ""

read -p "Would you like to register schemas and upload sample data now? (yes/no): " upload_data

if [ "$upload_data" = "yes" ]; then
    echo ""
    echo "Starting schema registration and data upload..."
    
    REGISTER_SCRIPT_PATH="$DATA_SCRIPT_PATH/register_and_upload.sh"
    
    if [ -f "$REGISTER_SCRIPT_PATH" ]; then
        cd "$DATA_SCRIPT_PATH"
        
        echo "Executing: bash register_and_upload.sh https://$CONTAINER_API_APP_FQDN"
        bash register_and_upload.sh "https://$CONTAINER_API_APP_FQDN"
        
        echo ""
        echo "✅ Schema registration and data upload completed!"
    else
        echo "⚠️  Registration script not found at: $REGISTER_SCRIPT_PATH"
    fi
else
    echo ""
    echo "⏭  Skipping schema registration and data upload."
    echo "To register schemas later, run:"
    echo "  cd $DATA_SCRIPT_PATH"
    echo "  bash register_and_upload.sh https://$CONTAINER_API_APP_FQDN"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎉 Post-deployment configuration completed!"
echo ""
echo "📋 Summary:"
echo "  • Web App: https://$CONTAINER_WEB_APP_FQDN"
echo "  • API App: https://$CONTAINER_API_APP_FQDN"
echo ""
echo "Next steps:"
echo "  1. Test your web application"
echo "  2. Verify authentication is working"
echo "  3. Check schema processing functionality"
echo ""
