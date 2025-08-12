# Guide to Local Development

## Requirements

• **Python 3.11 or higher** + PIP
• **Node.js 18+** and npm
• **Azure CLI** and an Azure Subscription
• **Docker Desktop** (optional, for containerized development)
• **Visual Studio Code IDE** (recommended)

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
   ```bash
   cd src/ContentProcessorAPI
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```
   
   **Content Processor:**
   ```bash
   cd src/ContentProcessor
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

8. **Install requirements - Backend components:**
   • In each of the backend folders, open a terminal and run:
   ```bash
   pip install -r requirements.txt
   ```

9. **Install requirements - Frontend:**
   • In the frontend folder:
   ```bash
   cd src/ContentProcessorWeb
   npm install
   ```

10. **Run the application:**
    • From the `src/ContentProcessorAPI` directory:
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```
    
    • In a new terminal from the `src/ContentProcessor` directory:
    ```bash
    python src/main.py
    ```
    
    • In a new terminal from the `src/ContentProcessorWeb` directory:
    ```bash
    npm start
    ```

11. **Open a browser and navigate to `http://localhost:3000`**

12. **To see Swagger API documentation, you can navigate to `http://localhost:8000/docs`**

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

## Alternative: Deploy with Azure Developer CLI

If you prefer to use Azure Developer CLI for a more automated deployment:

### Prerequisites
• Ensure you have the [Azure Developer CLI](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd) installed.
• Check [Azure OpenAI quota availability](./quota_check.md) before deployment.

### Deployment Steps

1. **Initialize the project:**
   ```bash
   azd init
   ```

2. **Configure environment:**
   ```bash
   azd env set AZURE_ENV_NAME "your-environment-name"
   azd env set AZURE_LOCATION "eastus"
   azd env set AZURE_OPENAI_GPT_DEPLOYMENT_CAPACITY "10"
   azd env set AZURE_OPENAI_GPT_MODEL_NAME "gpt-4o"
   ```

3. **Deploy infrastructure and applications:**
   ```bash
   azd up
   ```

4. **Verify deployment:**
   ```bash
   azd show
   azd browse
   ```

## Troubleshooting

### Common Issues

**Python Module Not Found:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Node.js Dependencies Issues:**
```bash
# Clear npm cache and reinstall
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

**Port Conflicts:**
```bash
# Check what's using the port
netstat -tulpn | grep :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows
```

**Azure Authentication Issues:**
```bash
# Re-authenticate
az logout
az login
```

**CORS Issues:**
• Ensure API CORS settings include the web app URL
• Check browser network tab for CORS errors
• Verify API is running on the expected port

**Environment Variables Not Loading:**
• Verify `.env` file is in the correct directory
• Check file permissions (especially on Linux/macOS)
• Ensure no extra spaces in variable assignments

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
