# Guide to Local Development

## Requirements

- Python 3.11 or higher + PIP
- Node.js 18+ and npm
- Azure CLI and an Azure Subscription
- Docker Desktop (optional, for containerized development)
- Visual Studio Code IDE (recommended)

## Local Setup

**Note for macOS Developers:** If you are using macOS on Apple Silicon (ARM64), you may experience compatibility issues with some Azure services. We recommend testing thoroughly and using alternative approaches if needed.

The easiest way to run this accelerator is in a VS Code Dev Container, which will open the project in your local VS Code using the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers):

1. Start Docker Desktop (install it if not already installed)
2. Open the project: [Open in Dev Containers](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/microsoft/content-processing-solution-accelerator)
3. In the VS Code window that opens, once the project files show up (this may take several minutes), open a terminal window

## Detailed Development Container Setup Instructions

The solution contains a [development container](https://code.visualstudio.com/docs/remote/containers) with all the required tooling to develop and deploy the accelerator. To deploy the Content Processing Solution Accelerator using the provided development container you will also need:

• [Visual Studio Code](https://code.visualstudio.com/)
• [Remote containers extension for Visual Studio Code](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

If you are running this on Windows, we recommend you clone this repository in [WSL](https://code.visualstudio.com/docs/remote/wsl):

```bash
git clone https://github.com/microsoft/content-processing-solution-accelerator
```

Open the cloned repository in Visual Studio Code and connect to the development container:

```bash
code .
```

!!! tip
    Visual Studio Code should recognize the available development container and ask you to open the folder using it. For additional details on connecting to remote containers, please see the [Open an existing folder in a container](https://code.visualstudio.com/docs/remote/containers#_quick-start-open-an-existing-folder-in-a-container) quickstart.

When you start the development container for the first time, the container will be built. This usually takes a few minutes. Please use the development container for all further steps.

The files for the dev container are located in `/.devcontainer/` folder.

## Local Deployment and Debugging

1. **Clone the repository.**

2. **Log into the Azure CLI:**
   • Check your login status using: `az account show`
   • If not logged in, use: `az login`
   • To specify a tenant, use: `az login --tenant <tenant_id>`

3. **Create a Resource Group:**
   • You can create it either through the Azure Portal or the Azure CLI:
   ```bash
   az group create --name <resource-group-name> --location EastUS2
   ```

4. **Deploy the Bicep template:**
   • You can use the Bicep extension for VSCode (Right-click the `.bicep` file, then select "Show deployment pane") or use the Azure CLI:
   ```bash
   az deployment group create -g <resource-group-name> -f infra/main.bicep --query 'properties.outputs'
   ```
   
   **Note:** You will be prompted for a `principalId`, which is the ObjectID of your user in Entra ID. To find it, use the Azure Portal or run:
   ```bash
   az ad signed-in-user show --query id -o tsv
   ```
   
   You will also be prompted for locations for Azure OpenAI and Azure AI Content Understanding services. This is to allow separate regions where there may be service quota restrictions.

   **Additional Notes:**
   
   **Role Assignments in Bicep Deployment:**
   
   The main.bicep deployment includes the assignment of the appropriate roles to Azure OpenAI and Cosmos services. If you want to modify an existing implementation—for example, to use resources deployed as part of the simple deployment for local debugging—you will need to add your own credentials to access the Cosmos and Azure OpenAI services. You can add these permissions using the following commands:
   
   ```bash
   az cosmosdb sql role assignment create --resource-group <solution-accelerator-rg> --account-name <cosmos-db-account-name> --role-definition-name "Cosmos DB Built-in Data Contributor" --principal-id <aad-user-object-id> --scope /subscriptions/<subscription-id>/resourceGroups/<solution-accelerator-rg>/providers/Microsoft.DocumentDB/databaseAccounts/<cosmos-db-account-name>
   
   az role assignment create --assignee <aad-user-upn> --role "Cognitive Services OpenAI User" --scope /subscriptions/<subscription-id>/resourceGroups/<solution-accelerator-rg>/providers/Microsoft.CognitiveServices/accounts/<azure-openai-name>
   ```
   
   **Using a Different Database in Cosmos:**
   
   You can set the solution up to use a different database in Cosmos. For example, you can name it something like `contentprocess-dev`. To do this:
   
   i. Change the environment variable `AZURE_COSMOS_DATABASE` to the new database name.
   
   ii. You will need to create the database in the Cosmos DB account. You can do this from the Data Explorer pane in the portal, click on the drop down labeled "+ New Container" and provide all the necessary details.

5. **Create `.env` files:**
   • Navigate to the root folder and each component folder (`src/ContentProcessor`, `src/ContentProcessorAPI`, `src/ContentProcessorWeb`) and create `.env` files based on the provided `.env.sample` files.

6. **Fill in the `.env` files:**
   • Use the output from the deployment or check the Azure Portal under "Deployments" in the resource group.

7. **(Optional) Set up virtual environments:**
   • If you are using `venv`, create and activate your virtual environment for both the backend components:
   
   **Content Processor API:**
   
   PowerShell:
   ```powershell
   cd src\ContentProcessorAPI
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
   
   Command Prompt:
   ```cmd
   cd src\ContentProcessorAPI
   python -m venv .venv
   .venv\Scripts\activate.bat
   ```
   
   Git Bash / Linux / macOS:
   ```bash
   cd src/ContentProcessorAPI
   python -m venv .venv
   source .venv/bin/activate
   ```
   
   **Content Processor:**
   
   PowerShell:
   ```powershell
   cd src\ContentProcessor
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
   
   Command Prompt:
   ```cmd
   cd src\ContentProcessor
   python -m venv .venv
   .venv\Scripts\activate.bat
   ```
   
   Git Bash / Linux / macOS:
   ```bash
   cd src/ContentProcessor
   python -m venv .venv
   source .venv/bin/activate
   ```
   
   **Note for PowerShell Users:** If you get an error about scripts being disabled, run:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

8. **Install requirements - Backend components:**
   
   **ContentProcessorAPI:**
   
   Navigate to `src/ContentProcessorAPI` and install dependencies:
   ```bash
   cd src\ContentProcessorAPI
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
   
   **ContentProcessor:**
   
   Navigate to `src/ContentProcessor` and install dependencies:
   ```bash
   cd src\ContentProcessor
   pip install -r requirements.txt
   ```
   
   **If you encounter errors**, upgrade problematic packages:
   ```powershell
   pip install --upgrade cffi cryptography pydantic pydantic-core numpy pandas
   ```
   
   **Note:** Python 3.11+ has better precompiled wheel support. Avoid Python 3.12 as some packages may not be compatible yet.

9. **Configure environment variables:**
   
   **ContentProcessorAPI:**
   
   Create a `.env` file in `src/ContentProcessorAPI/app/` directory with the following content:
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
   
   **ContentProcessor:**
   
   Create a `.env.dev` file (note the `.dev` suffix) in `src/ContentProcessor/src/` directory:
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
   
   **ContentProcessorWeb:**
   
   Update the `.env` file in `src/ContentProcessorWeb/` directory:
   ```bash
   REACT_APP_API_BASE_URL=http://localhost:8000
   REACT_APP_AUTH_ENABLED=false
   REACT_APP_CONSOLE_LOG_ENABLED=true
   ```
   
   **Important Notes:**
   - Replace `<your-appconfig-name>` and `<your-cosmos-name>` with your actual Azure resource names from deployment
   - `APP_ENV=dev` is **REQUIRED** for local development - it enables Azure CLI credential usage instead of Managed Identity
   - ContentProcessor requires `.env.dev` (not `.env`) in the `src/` subdirectory
   - Get your resource names from Azure Portal or by running: `az resource list -g <your-resource-group-name>`

10. **Assign Azure RBAC roles:**
    Before running the application locally, you need proper Azure permissions:
    
    ```bash
    # Get your Azure principal ID (user object ID)
    az ad signed-in-user show --query id -o tsv
    
    # Get your subscription ID
    az account show --query id -o tsv
    
    # Assign App Configuration Data Reader role
    az role assignment create --role "App Configuration Data Reader" \
      --assignee <your-principal-id> \
      --scope /subscriptions/<subscription-id>/resourceGroups/<resource-group-name>/providers/Microsoft.AppConfiguration/configurationStores/<appconfig-name>
    
    # Assign Cosmos DB Data Contributor role
    az role assignment create --role "Cosmos DB Built-in Data Contributor" \
      --assignee <your-principal-id> \
      --scope /subscriptions/<subscription-id>/resourceGroups/<resource-group-name>/providers/Microsoft.DocumentDB/databaseAccounts/<cosmos-name>
    
    # Assign Storage Queue Data Contributor role (for full file processing)
    az role assignment create --role "Storage Queue Data Contributor" \
      --assignee <your-principal-id> \
      --scope /subscriptions/<subscription-id>/resourceGroups/<resource-group-name>/providers/Microsoft.Storage/storageAccounts/<storage-account-name>
    
    # Assign Cognitive Services User role (for Content Understanding)
    az role assignment create --role "Cognitive Services User" \
      --assignee <your-principal-id> \
      --scope /subscriptions/<subscription-id>/resourceGroups/<resource-group-name>/providers/Microsoft.CognitiveServices/accounts/<content-understanding-name>
    ```
    
    **Note:** Azure role assignments can take 5-10 minutes to propagate. If you get "Forbidden" errors when starting the API, wait a few minutes and try again.

11. **Install requirements - Frontend:**
   • Navigate to the frontend folder:
   ```bash
   cd src\ContentProcessorWeb
   ```
   
   • Install dependencies with `--legacy-peer-deps` flag (required for @azure/msal-react compatibility):
   ```powershell
   npm install --legacy-peer-deps
   ```
   
   • Install additional required FluentUI packages:
   ```powershell
   npm install @fluentui/react-dialog @fluentui/react-button --legacy-peer-deps
   ```
   
   **Note:** Always use the `--legacy-peer-deps` flag for npm commands in this project to avoid dependency conflicts.

12. **Configure CORS for local development:**
    
    The FastAPI backend needs CORS configuration to allow requests from the React frontend during local development.
    
    Edit `src/ContentProcessorAPI/app/main.py` and add the CORS middleware configuration:
    
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
    
    **Note:** This CORS configuration is only needed for local development. Azure deployment handles CORS at the infrastructure level.

13. **Run the application:**
    
    Open three separate terminal windows and run each component:
    
    **Terminal 1 - API (ContentProcessorAPI):**
    
    PowerShell:
    ```powershell
    cd src\ContentProcessorAPI
    .venv\Scripts\Activate.ps1
    python -m uvicorn app.main:app --reload --port 8000
    ```
    
    Command Prompt:
    ```cmd
    cd src\ContentProcessorAPI
    .venv\Scripts\activate.bat
    python -m uvicorn app.main:app --reload --port 8000
    ```
    
    Git Bash / Linux / macOS:
    ```bash
    cd src/ContentProcessorAPI
    source .venv/bin/activate
    python -m uvicorn app.main:app --reload --port 8000
    ```
    
    **Terminal 2 - Background Processor (ContentProcessor):**
    
    PowerShell:
    ```powershell
    cd src\ContentProcessor
    .venv\Scripts\Activate.ps1
    python src/main.py
    ```
    
    Command Prompt:
    ```cmd
    cd src\ContentProcessor
    .venv\Scripts\activate.bat
    python src/main.py
    ```
    
    Git Bash / Linux / macOS:
    ```bash
    cd src/ContentProcessor
    source .venv/bin/activate
    python src/main.py
    ```
    
    **Terminal 3 - Frontend (ContentProcessorWeb):**
    ```bash
    cd src\ContentProcessorWeb
    npm start
    ```
    
    **Troubleshooting startup:**
    - If you get "Forbidden" errors from App Configuration or Cosmos DB, ensure your Azure role assignments have propagated (wait 5-10 minutes after creating them)
    - If you see "ManagedIdentityCredential" errors, verify `.env` files have `APP_ENV=dev` set
    - If frontend shows "Unable to connect to the server", verify you added CORS configuration in `main.py` (step 12) and restart the API
    - Storage Queue errors in ContentProcessor are expected if you haven't assigned the Storage Queue Data Contributor role - the processor will keep retrying
    - Content Understanding 401 errors are expected if you haven't assigned the Cognitive Services User role

14. **Open a browser and navigate to `http://localhost:3000`**

15. **To see Swagger API documentation, you can navigate to `http://localhost:8000/docs`**

## Debugging the Solution Locally

You can debug the API backend running locally with VSCode using the following launch.json entry:

```json
{
  "name": "Python Debugger: Content Processor API",
  "type": "debugpy",
  "request": "launch",
  "cwd": "${workspaceFolder}/src/ContentProcessorAPI",
  "module": "uvicorn",
  "args": ["app.main:app", "--reload"],
  "jinja": true
}
```

To debug the Content Processor service, add the following launch.json entry:

```json
{
  "name": "Python Debugger: Content Processor",
  "type": "debugpy",
  "request": "launch",
  "cwd": "${workspaceFolder}/src/ContentProcessor",
  "program": "src/main.py",
  "jinja": true
}
```

For debugging the React frontend, you can use the browser's developer tools or set up debugging in VS Code with the appropriate extensions.

## Troubleshooting

### Common Issues

**Python Module Not Found:**

PowerShell:
```powershell
# Ensure virtual environment is activated
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Command Prompt:
```cmd
# Ensure virtual environment is activated
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

Git Bash / Linux / macOS:
```bash
# Ensure virtual environment is activated
source .venv/bin/activate
pip install -r requirements.txt
```

**Python Dependency Compilation Errors (Windows):**

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

**pydantic_core ImportError:**

If you see "PyO3 modules compiled for CPython 3.8 or older may only be initialized once" or "ImportError: pydantic_core._pydantic_core":
```powershell
# Uninstall and reinstall with compatible versions
pip uninstall -y pydantic pydantic-core
pip install pydantic==2.12.5 pydantic-core==2.41.5
pip install --upgrade "typing-extensions>=4.14.1"
```

**Explanation:** Version mismatch between pydantic and pydantic-core causes runtime errors. The compatible versions above work reliably together.

**pandas/numpy Import Errors:**

If you see "Error importing numpy from its source directory":
```powershell
# Force reinstall all requirements to resolve conflicts
pip install --upgrade --force-reinstall -r requirements.txt
```

**Node.js Dependencies Issues:**

PowerShell:
```powershell
# Clear npm cache and reinstall with legacy peer deps
npm cache clean --force
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
Remove-Item -Force package-lock.json -ErrorAction SilentlyContinue
npm install --legacy-peer-deps

# Install missing FluentUI packages if needed
npm install @fluentui/react-dialog @fluentui/react-button --legacy-peer-deps
```

Bash / Linux / macOS:
```bash
# Clear npm cache and reinstall with legacy peer deps
npm cache clean --force
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps

# Install missing FluentUI packages if needed
npm install @fluentui/react-dialog @fluentui/react-button --legacy-peer-deps
```

**Explanation:** The `--legacy-peer-deps` flag is required due to peer dependency conflicts with @azure/msal-react. Some FluentUI packages may not be included in the initial install and need to be added separately.

**Port Conflicts:**
```bash
# Check what's using the port
netstat -tulpn | grep :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows
```

**Azure Authentication Issues:**

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

# If roles are missing, assign them (replace <principal-id> with your ID from above)
az role assignment create --role "App Configuration Data Reader" \
  --assignee <principal-id> \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg-name>/providers/Microsoft.AppConfiguration/configurationStores/<appconfig-name>

az role assignment create --role "Cosmos DB Built-in Data Contributor" \
  --assignee <principal-id> \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg-name>/providers/Microsoft.DocumentDB/databaseAccounts/<cosmos-name>

az role assignment create --role "Storage Queue Data Contributor" \
  --assignee <principal-id> \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg-name>/providers/Microsoft.Storage/storageAccounts/<storage-name>

az role assignment create --role "Cognitive Services User" \
  --assignee <principal-id> \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg-name>/providers/Microsoft.CognitiveServices/accounts/<content-understanding-name>
```

**Note:** Role assignments can take 5-10 minutes to propagate through Azure AD. If you just assigned roles, wait a few minutes before retrying.

**Cognitive Services Permission Errors:**

If you see "401 Client Error: PermissionDenied" for Content Understanding service:
```bash
# Assign Cognitive Services User role
az role assignment create --role "Cognitive Services User" \
  --assignee <principal-id> \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg-name>/providers/Microsoft.CognitiveServices/accounts/<content-understanding-name>
```

This error occurs when processing documents. Wait 5-10 minutes after assigning the role, then restart the ContentProcessor service.

**ManagedIdentityCredential Errors:**

If you see "ManagedIdentityCredential authentication unavailable" or "No managed identity endpoint found":
```bash
# Ensure your .env files have these settings:
APP_ENV=dev
AZURE_IDENTITY_EXCLUDE_MANAGED_IDENTITY_CREDENTIAL=True

# This tells the app to use Azure CLI credentials instead of Managed Identity
```

**Locations to check:**
- `src/ContentProcessorAPI/app/.env`
- `src/ContentProcessor/src/.env.dev` (note: must be `.env.dev` in the `src/` subdirectory, not `.env` in root)

**Explanation:** Managed Identity is used in Azure deployments but doesn't work locally. Setting `APP_ENV=dev` switches to Azure CLI credential authentication.

**General authentication reset:**
```bash
# Re-authenticate with Azure CLI
az logout
az login
```

**CORS Issues:**

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

2. Restart the API service after adding CORS configuration
3. Check browser console (F12) for CORS errors
4. Verify API is running on port 8000 and frontend on port 3000

**Explanation:** CORS (Cross-Origin Resource Sharing) blocks requests between different origins by default. The frontend (localhost:3000) needs explicit permission to call the API (localhost:8000).

**PowerShell Script Execution Policy Error:**

If you get "cannot be loaded because running scripts is disabled" when activating venv:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Environment Variables Not Loading:**
• Verify `.env` file is in the correct directory:
  - ContentProcessorAPI: `src/ContentProcessorAPI/app/.env`
  - ContentProcessor: `src/ContentProcessor/src/.env.dev` (must be `.env.dev`, not `.env`)
  - ContentProcessorWeb: `src/ContentProcessorWeb/.env`
• Check file permissions (especially on Linux/macOS)
• Ensure no extra spaces in variable assignments
• Restart the service after changing `.env` files

### Debug Mode

Enable detailed logging by setting these environment variables in your `.env` files:

```bash
APP_LOGGING_LEVEL=DEBUG
APP_LOGGING_ENABLE=True
```

### Getting Help

• Check the [Technical Architecture](./TechnicalArchitecture.md) documentation
• Review the [API Documentation](./API.md) for endpoint details
• Submit issues to the [GitHub repository](https://github.com/microsoft/content-processing-solution-accelerator/issues)
• Check existing issues for similar problems

---

For additional support, please refer to the [main README](../README.md) or the [Deployment Guide](./DeploymentGuide.md) for production deployment instructions.
