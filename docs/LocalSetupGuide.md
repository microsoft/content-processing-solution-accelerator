# Local Development Setup Guide

This guide provides comprehensive instructions for setting up the Content Processing Solution Accelerator for local development across Windows and Linux platforms.

## Important Setup Notes

### Multi-Service Architecture

This application consists of three separate services that run independently:

1. **ContentProcessorAPI** - REST API server for the frontend
2. **ContentProcessor** - Background processor that handles document processing from Azure Storage Queue
3. **ContentProcessorWeb** - React-based user interface

> ⚠️ **Critical**: Each service must run in its own terminal/console window
> 
> - Do NOT close terminals while services are running
> - Open 3 separate terminal windows for local development
> - Each service will occupy its terminal and show live logs
> 
> **Terminal Organization:**
> - Terminal 1: ContentProcessorAPI - HTTP server on port 8000
> - Terminal 2: ContentProcessor - Runs continuously, polls Azure Storage Queue
> - Terminal 3: ContentProcessorWeb - Development server on port 3000

### Path Conventions

All paths in this guide are relative to the repository root directory:

```
content-processing-solution-accelerator/    ← Repository root (start here)
├── src/
│   ├── ContentProcessorAPI/
│   │   ├── .venv/                          ← Virtual environment
│   │   └── app/
│   │       ├── main.py                     ← API entry point
│   │       └── .env                        ← API config file
│   ├── ContentProcessor/
│   │   ├── .venv/                          ← Virtual environment
│   │   └── src/
│   │       ├── main.py                     ← Processor entry point
│   │       └── .env.dev                    ← Processor config file
│   └── ContentProcessorWeb/
│       ├── node_modules/
│       └── .env                            ← Frontend config file
└── docs/                                   ← Documentation (you are here)
```

Before starting any step, ensure you are in the repository root directory:

```powershell
# Verify you're in the correct location
pwd  # Linux/macOS - should show: .../content-processing-solution-accelerator
Get-Location  # Windows PowerShell - should show: ...\content-processing-solution-accelerator

# If not, navigate to repository root
cd path/to/content-processing-solution-accelerator
```

### Configuration Files

This project uses separate `.env` files in each service directory with different configuration requirements:

- **ContentProcessorAPI**: `src/ContentProcessorAPI/app/.env` - Azure App Configuration URL, Cosmos DB endpoint
- **ContentProcessor**: `src/ContentProcessor/src/.env.dev` - Azure App Configuration URL, Cosmos DB endpoint (note `.dev` suffix)
- **ContentProcessorWeb**: `src/ContentProcessorWeb/.env` - API base URL, authentication settings

When copying `.env` samples, always navigate to the specific service directory first.

## Step 1: Prerequisites - Install Required Tools

### Windows Development

```powershell
# Install Python 3.11+ and Git
winget install Python.Python.3.11
winget install Git.Git

# Install Node.js for frontend
winget install OpenJS.NodeJS.LTS

# Verify installations
python --version  # Should show Python 3.11.x
node --version    # Should show v18.x or higher
npm --version
```

### Linux Development

#### Ubuntu/Debian

```bash
# Install prerequisites
sudo apt update && sudo apt install python3.11 python3.11-venv python3-pip git curl nodejs npm -y

# Verify installations
python3.11 --version
node --version
npm --version
```

#### RHEL/CentOS/Fedora

```bash
# Install prerequisites
sudo dnf install python3.11 python3.11-devel git curl gcc nodejs npm -y

# Verify installations
python3.11 --version
node --version
npm --version
```

### Clone the Repository

```bash
git clone https://github.com/microsoft/content-processing-solution-accelerator.git
cd content-processing-solution-accelerator
```

## Step 2: Azure Authentication Setup

Before configuring services, authenticate with Azure:

```bash
# Login to Azure CLI
az login

# Set your subscription
az account set --subscription "your-subscription-id"

# Verify authentication
az account show
```

### Get Azure Resource Information

After deploying Azure resources (using `azd up` or Bicep template), gather the following information:

```bash
# List resources in your resource group
az resource list -g <resource-group-name> -o table

# Get App Configuration endpoint
az appconfig show -n <appconfig-name> -g <resource-group-name> --query endpoint -o tsv

# Get Cosmos DB endpoint
az cosmosdb show -n <cosmos-name> -g <resource-group-name> --query documentEndpoint -o tsv
```

Example resource names from deployment:
- App Configuration: `appcs-{suffix}.azconfig.io`
- Cosmos DB: `cosmos-{suffix}.documents.azure.com`
- Storage Account: `st{suffix}.queue.core.windows.net`
- Content Understanding: `aicu-{suffix}.cognitiveservices.azure.com`

### Required Azure RBAC Permissions

To run the application locally, your Azure account needs the following role assignments on the deployed resources:

#### Get Your Principal ID

```bash
# Get your principal ID for role assignments
PRINCIPAL_ID=$(az ad signed-in-user show --query id -o tsv)
echo $PRINCIPAL_ID

# Get your subscription ID
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo $SUBSCRIPTION_ID
```

#### Assign Required Roles

```bash
# 1. App Configuration Data Reader
az role assignment create \
  --role "App Configuration Data Reader" \
  --assignee $PRINCIPAL_ID \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/<resource-group>/providers/Microsoft.AppConfiguration/configurationStores/<appconfig-name>"

# 2. Cosmos DB Built-in Data Contributor
az role assignment create \
  --role "Cosmos DB Built-in Data Contributor" \
  --assignee $PRINCIPAL_ID \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/<resource-group>/providers/Microsoft.DocumentDB/databaseAccounts/<cosmos-name>"

# 3. Storage Queue Data Contributor
az role assignment create \
  --role "Storage Queue Data Contributor" \
  --assignee $PRINCIPAL_ID \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/<resource-group>/providers/Microsoft.Storage/storageAccounts/<storage-account-name>"

# 4. Cognitive Services User
az role assignment create \
  --role "Cognitive Services User" \
  --assignee $PRINCIPAL_ID \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/<resource-group>/providers/Microsoft.CognitiveServices/accounts/<content-understanding-name>"
```

> **Note:** RBAC permission changes can take 5-10 minutes to propagate. If you encounter "Forbidden" errors after assigning roles, wait a few minutes and try again.

## Step 3: ContentProcessorAPI Setup & Run Instructions

> 📋 **Terminal Reminder**: Open a dedicated terminal window (Terminal 1) for the ContentProcessorAPI service. All commands in this section assume you start from the repository root directory.

The ContentProcessorAPI provides REST endpoints for the frontend and handles API requests.

### 3.1. Navigate to API Directory

```bash
# From repository root
cd src/ContentProcessorAPI
```

### 3.2. Create Virtual Environment

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1  # Windows PowerShell
# or
source .venv/bin/activate  # Linux/macOS
```

**Note for PowerShell Users:** If you get an error about scripts being disabled, run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 3.3. Install Dependencies

```bash
pip install -r requirements.txt
```

**If you encounter compilation errors** on Windows (cffi, pydantic-core, or cryptography):

These packages often fail to build from source on Windows. Use this workaround to install precompiled wheels:

```powershell
# Create temporary requirements without problematic packages
Get-Content requirements.txt | Where-Object { $_ -notmatch "cffi==1.17.1|pydantic==2.11.7|pydantic-core==2.33.2" } | Out-File temp_requirements.txt -Encoding utf8

# Install other dependencies first
pip install -r temp_requirements.txt

# Install problematic packages with newer precompiled versions
pip install cffi==2.0.0 pydantic==2.12.5 pydantic-core==2.41.5

# Upgrade typing-extensions if needed
pip install --upgrade "typing-extensions>=4.14.1" "typing-inspection>=0.4.2"

# Clean up temporary file
Remove-Item temp_requirements.txt
```

### 3.4. Configure Environment Variables

Create a `.env` file in the `src/ContentProcessorAPI/app/` directory:

```bash
cd app

# Create .env file
New-Item .env  # Windows PowerShell
# or
touch .env  # Linux/macOS
```

Add the following to the `.env` file:

```bash
# App Configuration endpoint from your Azure deployment
APP_CONFIG_ENDPOINT=https://<your-appconfig-name>.azconfig.io

# Cosmos DB endpoint from your Azure deployment
AZURE_COSMOS_ENDPOINT=https://<your-cosmos-name>.documents.azure.com:443/
AZURE_COSMOS_DATABASE=contentprocess

# Local development settings - CRITICAL for local authentication
APP_ENV=dev
APP_AUTH_ENABLED=False
AZURE_IDENTITY_EXCLUDE_MANAGED_IDENTITY_CREDENTIAL=True
```

> ⚠️ **Important**:
> - Replace `<your-appconfig-name>` and `<your-cosmos-name>` with your actual Azure resource names
> - `APP_ENV=dev` is **REQUIRED** for local development - it enables Azure CLI credential usage instead of Managed Identity
> - Get your resource names from the Azure Portal or by running: `az resource list -g <resource-group-name>`

### 3.5. Configure CORS for Local Development

Edit `src/ContentProcessorAPI/app/main.py` and add the CORS middleware configuration.

Add the import at the top:

```python
from fastapi.middleware.cors import CORSMiddleware
```

Then after the line `app = FastAPI(redirect_slashes=False)`, add:

```python
# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)
```

> **Note:** This CORS configuration is only needed for local development. Azure deployment handles CORS at the infrastructure level.

### 3.6. Run the API

```bash
# Make sure you're in the ContentProcessorAPI directory with activated venv
cd ..  # Go back to ContentProcessorAPI root if in app/

# Run with uvicorn
python -m uvicorn app.main:app --reload --port 8000
```

The ContentProcessorAPI will start at:
- API: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

**Keep this terminal open** - the API server will continue running and show request logs.

## Step 4: ContentProcessor Setup & Run Instructions

> 📋 **Terminal Reminder**: Open a second dedicated terminal window (Terminal 2) for the ContentProcessor. Keep Terminal 1 (API) running. All commands assume you start from the repository root directory.

The ContentProcessor handles background document processing from Azure Storage Queue.

### 4.1. Navigate to Processor Directory

```bash
# From repository root
cd src/ContentProcessor
```

### 4.2. Create Virtual Environment

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1  # Windows PowerShell
# or
source .venv/bin/activate  # Linux/macOS
```

### 4.3. Install Dependencies

```bash
pip install -r requirements.txt
```

**If you encounter errors**, upgrade problematic packages:

```powershell
pip install --upgrade cffi cryptography pydantic pydantic-core numpy pandas
```

### 4.4. Configure Environment Variables

Create a `.env.dev` file (note the `.dev` suffix) in the `src/ContentProcessor/src/` directory:

```bash
cd src

# Create .env.dev file
New-Item .env.dev  # Windows PowerShell
# or
touch .env.dev  # Linux/macOS
```

Add the following to the `.env.dev` file:

```bash
# App Configuration endpoint
APP_CONFIG_ENDPOINT=https://<your-appconfig-name>.azconfig.io

# Cosmos DB endpoint
AZURE_COSMOS_ENDPOINT=https://<your-cosmos-name>.documents.azure.com:443/
AZURE_COSMOS_DATABASE=contentprocess

# Local development settings
APP_ENV=dev
APP_AUTH_ENABLED=False
AZURE_IDENTITY_EXCLUDE_MANAGED_IDENTITY_CREDENTIAL=True

# Logging settings
APP_LOGGING_LEVEL=INFO
APP_LOGGING_ENABLE=True
```

> ⚠️ **Important**: The `.env.dev` file must be located in `src/ContentProcessor/src/` directory, not in `src/ContentProcessor/` root. The application looks for the `.env.dev` file in the same directory as `main.py`.

### 4.5. Run the Processor

```bash
# Make sure you're in the src directory
python main.py
```

The ContentProcessor will start and begin polling the Azure Storage Queue for messages.

**Expected behavior:**
- You may see Storage Queue authorization errors if roles haven't propagated (wait 5-10 minutes)
- The processor will show continuous polling activity
- Document processing will begin when files are uploaded via the frontend

**Keep this terminal open** - the processor will continue running and show processing logs.

## Step 5: ContentProcessorWeb Setup & Run Instructions

> 📋 **Terminal Reminder**: Open a third dedicated terminal window (Terminal 3) for the ContentProcessorWeb. Keep Terminals 1 (API) and 2 (Processor) running. All commands assume you start from the repository root directory.

The ContentProcessorWeb provides the React-based user interface.

### 5.1. Navigate to Frontend Directory

```bash
# From repository root
cd src/ContentProcessorWeb
```

### 5.2. Install Dependencies

```bash
# Install dependencies with legacy peer deps flag
npm install --legacy-peer-deps

# Install additional required FluentUI packages
npm install @fluentui/react-dialog @fluentui/react-button --legacy-peer-deps
```

> **Note:** Always use the `--legacy-peer-deps` flag for npm commands in this project to avoid dependency conflicts with @azure/msal-react.

### 5.3. Configure Environment Variables

Update the `.env` file in the `src/ContentProcessorWeb/` directory:

```bash
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_AUTH_ENABLED=false
REACT_APP_CONSOLE_LOG_ENABLED=true
```

### 5.4. Start Development Server

```bash
npm start
```

The ContentProcessorWeb will start at: `http://localhost:3000`

**Keep this terminal open** - the React development server will continue running with hot reload.

## Step 6: Verify All Services Are Running

Before using the application, confirm all three services are running in separate terminals:

### Terminal Status Checklist

| Terminal | Service | Command | Expected Output | URL |
|----------|---------|---------|-----------------|-----|
| Terminal 1 | ContentProcessorAPI | `python -m uvicorn app.main:app --reload --port 8000` | `Application startup complete` | http://localhost:8000 |
| Terminal 2 | ContentProcessor | `python main.py` | Polling messages, no fatal errors | N/A |
| Terminal 3 | ContentProcessorWeb | `npm start` | `Compiled successfully!` | http://localhost:3000 |

### Quick Verification

1. **Check Backend API**:
   ```bash
   # In a new terminal (Terminal 4)
   curl http://localhost:8000/health
   # Expected: {"message":"I'm alive!"}
   ```

2. **Check Frontend**:
   - Open browser to http://localhost:3000
   - Should see the Content Processing UI
   - No "Unable to connect to the server" errors

3. **Check Processor**:
   - Look at Terminal 2 output
   - Should see processing activity or queue polling
   - No authorization errors (if roles have propagated)

## Step 7: Next Steps

Once all services are running (as confirmed in Step 6), you can:

1. **Access the Application**: Open `http://localhost:3000` in your browser to explore the frontend UI
2. **Upload Documents**: Use the UI to upload documents for processing
3. **View API Documentation**: Navigate to `http://localhost:8000/docs` to explore API endpoints
4. **Check Processing Status**: Monitor Terminal 2 for document processing logs

## Troubleshooting

### Common Issues

#### Python Compilation Errors (Windows)

If you see errors like "Microsoft Visual C++ 14.0 is required" or "error: metadata-generation-failed" when installing cffi, pydantic-core, or cryptography:

```powershell
# Create temporary requirements excluding problematic packages
Get-Content requirements.txt | Where-Object { $_ -notmatch "cffi==1.17.1|pydantic==2.11.7|pydantic-core==2.33.2" } | Out-File temp_requirements.txt -Encoding utf8

# Install other dependencies first
pip install -r temp_requirements.txt

# Install problematic packages with newer precompiled versions
pip install cffi==2.0.0 pydantic==2.12.5 pydantic-core==2.41.5

# Upgrade typing-extensions if needed
pip install --upgrade "typing-extensions>=4.14.1" "typing-inspection>=0.4.2"

# Clean up
Remove-Item temp_requirements.txt
```

**Explanation:** Older versions of cffi (1.17.1) and pydantic-core (2.33.2) require compilation from source, which fails on Windows without Visual Studio build tools. Newer versions have precompiled wheels that install without compilation.

#### pydantic_core ImportError

If you see "PyO3 modules compiled for CPython 3.8 or older may only be initialized once" or "ImportError: pydantic_core._pydantic_core":

```powershell
# Uninstall and reinstall with compatible versions
pip uninstall -y pydantic pydantic-core
pip install pydantic==2.12.5 pydantic-core==2.41.5
pip install --upgrade "typing-extensions>=4.14.1"
```

**Explanation:** Version mismatch between pydantic and pydantic-core causes runtime errors. The compatible versions above work reliably together.

#### Node.js Dependencies Issues

```powershell
# Clear npm cache and reinstall with legacy peer deps
npm cache clean --force
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
Remove-Item -Force package-lock.json -ErrorAction SilentlyContinue
npm install --legacy-peer-deps

# Install missing FluentUI packages if needed
npm install @fluentui/react-dialog @fluentui/react-button --legacy-peer-deps
```

**Explanation:** The `--legacy-peer-deps` flag is required due to peer dependency conflicts with @azure/msal-react. Some FluentUI packages may not be included in the initial install and need to be added separately.

#### Azure Authentication Issues

If you get "Forbidden" errors when accessing App Configuration or Cosmos DB:

```bash
# Check your current Azure account
az account show

# Get your principal ID for role assignments
az ad signed-in-user show --query id -o tsv

# Verify you have the correct role assignments
az role assignment list --assignee $(az ad signed-in-user show --query id -o tsv) --resource-group <resource-group-name>

# Refresh your access token
az account get-access-token --resource https://azconfig.io
```

If roles are missing, assign them as shown in Step 2.

> **Note:** Role assignments can take 5-10 minutes to propagate through Azure AD. If you just assigned roles, wait a few minutes before retrying.

#### Cognitive Services Permission Errors

If you see "401 Client Error: PermissionDenied" for Content Understanding service:

```bash
# Assign Cognitive Services User role
az role assignment create --role "Cognitive Services User" \
  --assignee <principal-id> \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg-name>/providers/Microsoft.CognitiveServices/accounts/<content-understanding-name>
```

This error occurs when processing documents. Wait 5-10 minutes after assigning the role, then restart the ContentProcessor service.

#### ManagedIdentityCredential Errors

If you see "ManagedIdentityCredential authentication unavailable" or "No managed identity endpoint found":

```bash
# Ensure your .env files have these settings:
APP_ENV=dev
AZURE_IDENTITY_EXCLUDE_MANAGED_IDENTITY_CREDENTIAL=True
```

**Locations to check:**
- `src/ContentProcessorAPI/app/.env`
- `src/ContentProcessor/src/.env.dev` (note: must be `.env.dev` in the `src/` subdirectory, not `.env` in root)

**Explanation:** Managed Identity is used in Azure deployments but doesn't work locally. Setting `APP_ENV=dev` switches to Azure CLI credential authentication.

#### CORS Issues

If the frontend loads but shows "Unable to connect to the server" error:

1. Verify CORS is configured in `src/ContentProcessorAPI/app/main.py`:
   ```python
   from fastapi.middleware.cors import CORSMiddleware

   app = FastAPI(redirect_slashes=False)

   # Configure CORS for local development
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:3000"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

2. Restart the API service (Terminal 1) after adding CORS configuration
3. Check browser console (F12) for CORS errors
4. Verify API is running on port 8000 and frontend on port 3000

**Explanation:** CORS (Cross-Origin Resource Sharing) blocks requests between different origins by default. The frontend (localhost:3000) needs explicit permission to call the API (localhost:8000).

#### Environment Variables Not Loading

- Verify `.env` file is in the correct directory:
  - ContentProcessorAPI: `src/ContentProcessorAPI/app/.env`
  - ContentProcessor: `src/ContentProcessor/src/.env.dev` (must be `.env.dev`, not `.env`)
  - ContentProcessorWeb: `src/ContentProcessorWeb/.env`
- Check file permissions (especially on Linux/macOS)
- Ensure no extra spaces in variable assignments
- Restart the service after changing `.env` files

#### PowerShell Script Execution Policy Error

If you get "cannot be loaded because running scripts is disabled" when activating venv:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Port Conflicts

```bash
# Check what's using the port
netstat -ano | findstr :8000  # Windows
netstat -tulpn | grep :8000   # Linux/Mac

# Kill the process using the port if needed
# Windows: taskkill /PID <PID> /F
# Linux: kill -9 <PID>
```

### Debug Mode

Enable detailed logging by setting these environment variables in your `.env` files:

```bash
APP_LOGGING_LEVEL=DEBUG
APP_LOGGING_ENABLE=True
```

## Related Documentation

- [Deployment Guide](./DeploymentGuide.md) - Production deployment instructions
- [Technical Architecture](./TechnicalArchitecture.md) - System architecture overview
- [API Documentation](./API.md) - API endpoint details
- [README](../README.md) - Project overview and getting started

---

For additional support, please submit issues to the [GitHub repository](https://github.com/microsoft/content-processing-solution-accelerator/issues).
