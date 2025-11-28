# Automated Authentication Configuration Flow

## Overview

This document describes the new automated authentication configuration approach that integrates with the infrastructure deployment using Azure Developer CLI (azd) and stores credentials securely in Azure Key Vault.

## Architecture Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. azd provision (Bicep Deployment)                             │
│    • Deploys Container Apps (Web & API)                         │
│    • Creates Key Vault                                          │
│    • Sets up basic infrastructure                               │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Post-Provision Hook (azure.yaml)                             │
│    • Triggers: ./infra/scripts/post_deployment.ps1              │
│    • Interactive prompt for configuration                       │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Authentication Configuration (Optional but Recommended)       │
│    • Script: configure_auth_automated.ps1                       │
│    • Automates auth provider setup                              │
│    • Configures app registrations                               │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Credential Storage (Key Vault)                               │
│    • Stores: WEB-APP-CLIENT-ID                                  │
│    • Stores: WEB-APP-SCOPE                                      │
│    • Stores: API-APP-CLIENT-ID                                  │
│    • Stores: API-APP-SCOPE                                      │
│    • Stores: TENANT-ID                                          │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Environment Variable Update                                   │
│    • Updates Web Container App with:                            │
│      - APP_WEB_CLIENT_ID                                        │
│      - APP_WEB_SCOPE                                            │
│      - APP_API_SCOPE                                            │
│    • Triggers new revision deployment                           │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. Schema Registration (Optional)                                │
│    • Script: register_and_upload.sh                             │
│    • Registers schemas via API                                  │
│    • Uploads sample data                                        │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. **Post-Deployment Script** (`post_deployment.ps1` / `post_deployment.sh`)

**Purpose**: Entry point for post-provision configuration

**Features**:
- Displays deployed resource information
- Prompts user for authentication configuration
- Prompts user for schema registration
- Orchestrates the configuration flow

**Execution**: Automatically triggered by azd via `azure.yaml` hooks

### 2. **Automated Authentication Script** (`configure_auth_automated.ps1`)

**Purpose**: Automates authentication provider setup and configuration

**What it automates**:
- ✅ Loads configuration from azd environment
- ✅ Retrieves Container App details
- ✅ Configures SPA redirect URIs
- ✅ Retrieves OAuth scopes
- ✅ Adds authorized client applications
- ✅ Stores credentials in Key Vault
- ✅ Updates Container App environment variables
- ✅ Saves configuration to azd environment

**What requires manual steps**:
- 👉 Initial authentication provider creation (one-time Portal action)
- 👉 Admin consent for API permissions (requires admin privileges)

**Key Vault Secrets Created**:
```
WEB-APP-CLIENT-ID      → Web App Registration Client ID
WEB-APP-SCOPE          → Web App OAuth Scope
API-APP-CLIENT-ID      → API App Registration Client ID
API-APP-SCOPE          → API App OAuth Scope
TENANT-ID              → Azure AD Tenant ID
```

### 3. **Schema Registration Script** (`register_and_upload.sh`)

**Purpose**: Registers schemas and uploads sample data

**Features**:
- Registers Invoice and Property Claim schemas
- Uploads sample PDF files for each schema
- Provides detailed progress feedback

## Usage

### Option 1: Full Automated Flow (Recommended)

```powershell
# 1. Deploy infrastructure
azd provision

# 2. Follow interactive prompts
#    - Choose "yes" for authentication configuration
#    - Choose "yes" for schema registration

# 3. Complete manual steps when prompted
#    - Add authentication providers in Portal
#    - Grant admin consent for API permissions

# Done! Everything is configured automatically
```

### Option 2: Manual Step-by-Step

```powershell
# 1. Deploy infrastructure
azd provision

# 2. Skip interactive prompts (choose "no")

# 3. Later, run authentication configuration manually
./infra/scripts/configure_auth_automated.ps1

# 4. Later, run schema registration manually
cd src/ContentProcessorAPI/samples
bash register_and_upload.sh https://your-api-endpoint.com
```

### Option 3: Re-run Configuration Anytime

```powershell
# Re-configure authentication
./infra/scripts/configure_auth_automated.ps1

# Re-register schemas
cd src/ContentProcessorAPI/samples
bash register_and_upload.sh https://your-api-endpoint.com
```

## Configuration Flow Details

### Step 1: Load Environment Variables

The script loads configuration from azd environment:
- `AZURE_RESOURCE_GROUP` → Resource Group name
- `CONTAINER_WEB_APP_NAME` → Web Container App name
- `CONTAINER_API_APP_NAME` → API Container App name
- `AZURE_KEY_VAULT_NAME` → Key Vault name
- `AZURE_SUBSCRIPTION_ID` → Azure Subscription ID
- `AZURE_TENANT_ID` → Azure AD Tenant ID

### Step 2: Verify Azure CLI Login

Ensures user is logged in to Azure CLI and sets the correct subscription.

### Step 3: Get Container App Details

Retrieves:
- Container App URLs (FQDNs)
- Existing authentication configuration
- App Registration Client IDs (if auth is configured)

### Step 4: Configure Authentication Providers

**Automated**:
- Detects existing authentication configuration
- Retrieves App Registration details

**Manual (if needed)**:
- Prompts user to create authentication providers in Portal
- Waits for confirmation before proceeding

### Step 5: Configure App Registrations

**Automated**:
- Adds SPA redirect URIs for Web App
- Retrieves OAuth scopes for both apps
- Adds Web App to API's authorized clients

**Uses Microsoft Graph API** for:
- Getting app registration details
- Updating redirect URIs
- Configuring pre-authorized applications

### Step 6: Store Credentials in Key Vault

**Automated**:
- Stores all authentication credentials as Key Vault secrets
- Uses Azure CLI to set secrets

**Secrets stored**:
```powershell
az keyvault secret set --vault-name $KeyVaultName --name "WEB-APP-CLIENT-ID" --value <value>
az keyvault secret set --vault-name $KeyVaultName --name "WEB-APP-SCOPE" --value <value>
az keyvault secret set --vault-name $KeyVaultName --name "API-APP-CLIENT-ID" --value <value>
az keyvault secret set --vault-name $KeyVaultName --name "API-APP-SCOPE" --value <value>
az keyvault secret set --vault-name $KeyVaultName --name "TENANT-ID" --value <value>
```

### Step 7: Update Container App Environment Variables

**Automated**:
- Updates Web Container App with environment variables
- Creates new revision with updated configuration
- Waits for revision to become active

**Environment variables set**:
```
APP_WEB_CLIENT_ID → Client ID for Web App
APP_WEB_SCOPE     → OAuth scope for Web App
APP_API_SCOPE     → OAuth scope for API App
```

### Step 8: Save to azd Environment

**Automated**:
- Saves configuration to azd environment for future reference
- Allows re-running scripts without re-fetching values

## Benefits of This Approach

### 1. **Infrastructure as Code Integration**
- Integrated with azd deployment flow
- Consistent with Bicep-based infrastructure

### 2. **Secure Credential Management**
- Credentials stored in Key Vault
- Never exposed in code or logs
- Can be retrieved by applications at runtime

### 3. **Automation Where Possible**
- Reduces manual configuration steps
- Minimizes human error
- Faster deployment cycles

### 4. **Clear Manual Step Guidance**
- Steps that require Portal access are clearly marked
- Detailed instructions provided
- Can be completed by less technical users

### 5. **Idempotent Operations**
- Scripts can be re-run safely
- No duplicate configurations
- Updates existing resources

### 6. **Environment Consistency**
- Same configuration across Dev/Test/Prod
- Values stored in azd environment
- Easy to replicate environments

## Troubleshooting

### Authentication Not Working

```powershell
# Check if credentials are in Key Vault
az keyvault secret list --vault-name <your-keyvault-name> --query "[?starts_with(name, 'WEB-APP') || starts_with(name, 'API-APP')].name"

# Check Container App environment variables
az containerapp show --name <web-app-name> --resource-group <rg-name> --query "properties.template.containers[0].env[?starts_with(name, 'APP_')].{name:name,value:value}" -o table

# Re-run authentication configuration
./infra/scripts/configure_auth_automated.ps1
```

### Schema Registration Failed

```bash
# Check API endpoint is accessible
curl https://your-api-endpoint.com/health

# Re-run schema registration
cd src/ContentProcessorAPI/samples
bash register_and_upload.sh https://your-api-endpoint.com
```

### Missing Permissions

If you see permission errors:
1. Ensure you have Owner or Contributor role on the subscription
2. Ensure you have Application Administrator role in Azure AD
3. Contact your tenant administrator for admin consent

## Next Steps

After completing the authentication configuration:

1. **Test Web Application**
   - Navigate to Web App URL
   - Verify sign-in works
   - Check API calls are successful

2. **Test Schema Processing**
   - Upload test documents
   - Verify schema extraction works
   - Check results in the UI

3. **Configure Additional Settings**
   - Add custom schemas
   - Configure monitoring alerts
   - Set up CI/CD pipelines

## Related Files

- `azure.yaml` - Defines post-provision hooks
- `infra/scripts/post_deployment.ps1` - Main post-deployment script
- `infra/scripts/post_deployment.sh` - Bash version of post-deployment
- `infra/scripts/configure_auth_automated.ps1` - Automated auth configuration
- `src/ContentProcessorAPI/samples/register_and_upload.sh` - Schema registration
- `infra/main.bicep` - Main infrastructure template
- `infra/modules/key-vault.bicep` - Key Vault module

## Support

For issues or questions:
1. Check the [Troubleshooting Guide](./TroubleShootingSteps.md)
2. Review the [Deployment Guide](./DeploymentGuide.md)
3. Open an issue in the repository
