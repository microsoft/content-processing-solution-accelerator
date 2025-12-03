# Deployment Guide

## Overview

This guide walks you through deploying the Content Processing Solution Accelerator to Azure. The deployment process takes approximately 15-20 minutes for the default Development/Testing configuration and includes both infrastructure provisioning and application setup.

🆘 **Need Help?** If you encounter any issues during deployment, check our [Troubleshooting Guide](./TroubleShootingSteps.md) for solutions to common problems.

## Step 1: Prerequisites & Setup

### 1.1 Azure Account Requirements

Ensure you have access to an [Azure subscription](https://azure.microsoft.com/free/) with the following permissions:

| **Required Permission/Role** | **Scope** | **Purpose** |
|------------------------------|-----------|-------------|
| **Contributor** | Subscription or Resource Group | Create and manage Azure resources |
| **User Access Administrator** | Subscription or Resource Group | Manage user access and role assignments |
| **Role Based Access Control** | Subscription/Resource Group level | Configure RBAC permissions |
| **Application Administrator** | Tenant | Create app registrations for authentication |

**🔍 How to Check Your Permissions:**

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to **Subscriptions** (search for "subscriptions" in the top search bar)
3. Click on your target subscription
4. In the left menu, click **Access control (IAM)**
5. Scroll down to see the table with your assigned roles - you should see:
   - **Contributor** 
   - **User Access Administrator**
   - **Role Based Access Control Administrator** (or similar RBAC role)

**For App Registration permissions:**
1. Go to **Microsoft Entra ID** → **Manage** → **App registrations**
2. Try clicking **New registration** 
3. If you can access this page, you have the required permissions
4. Cancel without creating an app registration

📖 **Detailed Setup:** Follow [Azure Account Set Up](./AzureAccountSetup.md) for complete configuration.

### 1.2 Check Service Availability & Quota

⚠️ **CRITICAL:** Before proceeding, ensure your chosen region has all required services available:

**Required Azure Services:**
- [Azure AI Foundry](https://learn.microsoft.com/en-us/azure/ai-foundry/)
- [Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [Azure AI Content Understanding Service](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/)
- [Azure Blob Storage](https://learn.microsoft.com/en-us/azure/storage/blobs/)
- [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/)
- [Azure Container Registry](https://learn.microsoft.com/en-us/azure/container-registry/)
- [Azure Cosmos DB](https://learn.microsoft.com/en-us/azure/cosmos-db/)
- [Azure Queue Storage](https://learn.microsoft.com/en-us/azure/storage/queues/)
- [GPT Model Capacity](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models)

**Recommended Regions:** East US, East US2, Australia East, UK South, France Central.

🔍 **Check Availability:** Use [Azure Products by Region](https://azure.microsoft.com/en-us/explore/global-infrastructure/products-by-region/) to verify service availability.

### 1.3 Quota Check (Optional)

💡 **RECOMMENDED:** Check your Azure OpenAI quota availability before deployment for optimal planning.

📖 **Follow:** [Quota Check Instructions](./quota_check.md) to ensure sufficient capacity.

**Recommended Configuration:**
- **Default:** 100k tokens
- **Optimal:** 100k tokens (recommended for best performance)

> **Note:** When you run `azd up`, the deployment will automatically show you regions with available quota, so this pre-check is optional but helpful for planning purposes. You can customize these settings later in [Step 3.3: Advanced Configuration](#33-advanced-configuration-optional).

📖 **Adjust Quota:** Follow [Azure GPT Quota Settings](./AzureGPTQuotaSettings.md) if needed.

## Step 2: Choose Your Deployment Environment

Select one of the following options to deploy the Content Processing Solution Accelerator:

### Environment Comparison

| **Option** | **Best For** | **Prerequisites** | **Setup Time** |
|------------|--------------|-------------------|----------------|
| **GitHub Codespaces** | Quick deployment, no local setup required | GitHub account | ~3-5 minutes |
| **VS Code Dev Containers** | Fast deployment with local tools | Docker Desktop, VS Code | ~5-10 minutes |
| **VS Code Web** | Quick deployment, no local setup required | Azure account | ~2-4 minutes |
| **Local Environment** | Enterprise environments, full control | All tools individually | ~15-30 minutes |

**💡 Recommendation:** For fastest deployment, start with **GitHub Codespaces** - no local installation required.

---

<details>
<summary><b>Option A: GitHub Codespaces (Easiest)</b></summary>

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/microsoft/content-processing-solution-accelerator)

1. Click the badge above (may take several minutes to load)
2. Accept default values on the Codespaces creation page
3. Wait for the environment to initialize (includes all deployment tools)
4. Proceed to [Step 3: Configure Deployment Settings](#step-3-configure-deployment-settings)

</details>

<details>
<summary><b>Option B: VS Code Dev Containers</b></summary>

[![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/microsoft/content-processing-solution-accelerator)

**Prerequisites:**
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [VS Code](https://code.visualstudio.com/) with [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

**Steps:**
1. Start Docker Desktop
2. Click the badge above to open in Dev Containers
3. Wait for the container to build and start (includes all deployment tools)
4. Proceed to [Step 3: Configure Deployment Settings](#step-3-configure-deployment-settings)

</details>

<details>
<summary><b>Option C: Visual Studio Code Web</b></summary>

 [![Open in Visual Studio Code Web](https://img.shields.io/static/v1?style=for-the-badge&label=Visual%20Studio%20Code%20(Web)&message=Open&color=blue&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/azure/?vscode-azure-exp=foundry&agentPayload=eyJiYXNlVXJsIjogImh0dHBzOi8vcmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbS9taWNyb3NvZnQvY29udGVudC1wcm9jZXNzaW5nLXNvbHV0aW9uLWFjY2VsZXJhdG9yL3JlZnMvaGVhZHMvbWFpbi9pbmZyYS92c2NvZGVfd2ViIiwgImluZGV4VXJsIjogIi9pbmRleC5qc29uIiwgInZhcmlhYmxlcyI6IHsiYWdlbnRJZCI6ICIiLCAiY29ubmVjdGlvblN0cmluZyI6ICIiLCAidGhyZWFkSWQiOiAiIiwgInVzZXJNZXNzYWdlIjogIiIsICJwbGF5Z3JvdW5kTmFtZSI6ICIiLCAibG9jYXRpb24iOiAiIiwgInN1YnNjcmlwdGlvbklkIjogIiIsICJyZXNvdXJjZUlkIjogIiIsICJwcm9qZWN0UmVzb3VyY2VJZCI6ICIiLCAiZW5kcG9pbnQiOiAiIn0sICJjb2RlUm91dGUiOiBbImFpLXByb2plY3RzLXNkayIsICJweXRob24iLCAiZGVmYXVsdC1henVyZS1hdXRoIiwgImVuZHBvaW50Il19)

1. Click the badge above (may take a few minutes to load)
2. Sign in with your Azure account when prompted
3. Select the subscription where you want to deploy the solution
4. Wait for the environment to initialize (includes all deployment tools)
5. Once the solution opens, the **AI Foundry terminal** will automatically start running the following command to install the required dependencies:

    ```shell
    sh install.sh
    ```
    During this process, you’ll be prompted with the message:
    ```
    What would you like to do with these files?
    - Overwrite with versions from template
    - Keep my existing files unchanged
    ```
    Choose “**Overwrite with versions from template**” and provide a unique environment name when prompted.
6. Proceed to [Step 3: Configure Deployment Settings](#step-3-configure-deployment-settings)

</details>

<details>
<summary><b>Option D: Local Environment</b></summary>

**Required Tools:**
- [PowerShell 7.0+](https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell) 
- [Azure Developer CLI (azd) 1.18.0+](https://aka.ms/install-azd)
- [Python 3.9+](https://www.python.org/downloads/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Git](https://git-scm.com/downloads)

**Setup Steps:**
1. Install all required deployment tools listed above
2. Clone the repository:
   ```shell
   azd init -t microsoft/content-processing-solution-accelerator/
   ```
3. Open the project folder in your terminal
4. Proceed to [Step 3: Configure Deployment Settings](#step-3-configure-deployment-settings)

**PowerShell Users:** If you encounter script execution issues, run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

</details>

## Step 3: Configure Deployment Settings

Review the configuration options below. You can customize any settings that meet your needs, or leave them as defaults to proceed with a standard deployment.

### 3.1 Choose Deployment Type (Optional)

| **Aspect** | **Development/Testing (Default)** | **Production** |
|------------|-----------------------------------|----------------|
| **Configuration File** | `main.parameters.json` (sandbox) | Copy `main.waf.parameters.json` to `main.parameters.json` |
| **Security Controls** | Minimal (for rapid iteration) | Enhanced (production best practices) |
| **Cost** | Lower costs | Cost optimized |
| **Use Case** | POCs, development, testing | Production workloads |
| **Framework** | Basic configuration | [Well-Architected Framework](https://learn.microsoft.com/en-us/azure/well-architected/) |
| **Features** | Core functionality | Reliability, security, operational excellence |

**To use production configuration:**

Copy the contents from the production configuration file to your main parameters file:

1. Navigate to the `infra` folder in your project
2. Open `main.waf.parameters.json` in a text editor (like Notepad, VS Code, etc.)
3. Select all content (Ctrl+A) and copy it (Ctrl+C)
4. Open `main.parameters.json` in the same text editor
5. Select all existing content (Ctrl+A) and paste the copied content (Ctrl+V)
6. Save the file (Ctrl+S)

### 3.2 Set VM Credentials (Optional - Production Deployment Only)

> **Note:** This section only applies if you selected **Production** deployment type in section 3.1. VMs are not deployed in the default Development/Testing configuration.

By default, random GUIDs are generated for VM credentials. To set custom credentials:

```shell
azd env set AZURE_ENV_VM_ADMIN_USERNAME <your-username>
azd env set AZURE_ENV_VM_ADMIN_PASSWORD <your-password>
```

### 3.3 Advanced Configuration (Optional)

<details>
<summary><b>Configurable Parameters</b></summary>

You can customize various deployment settings before running `azd up`, including Azure regions, AI model configurations (deployment type, version, capacity), container registry settings, and resource names.

📖 **Complete Guide:** See [Parameter Customization Guide](../docs/CustomizingAzdParameters.md) for the full list of available parameters and their usage.

</details>

<details>
<summary><b>Reuse Existing Resources</b></summary>

To optimize costs and integrate with your existing Azure infrastructure, you can configure the solution to reuse compatible resources already deployed in your subscription.

**Supported Resources for Reuse:**

- **Log Analytics Workspace:** Integrate with your existing monitoring infrastructure by reusing an established Log Analytics workspace for centralized logging and monitoring. [Configuration Guide](./re-use-log-analytics.md)

- **Azure AI Foundry Project:** Leverage your existing AI Foundry project and deployed models to avoid duplication and reduce provisioning time. [Configuration Guide](./re-use-foundry-project.md)

**Key Benefits:**
- **Cost Optimization:** Eliminate duplicate resource charges
- **Operational Consistency:** Maintain unified monitoring and AI infrastructure
- **Faster Deployment:** Skip resource creation for existing compatible services
- **Simplified Management:** Reduce the number of resources to manage and monitor

**Important Considerations:**
- Ensure existing resources meet the solution's requirements and are in compatible regions
- Review access permissions and configurations before reusing resources
- Consider the impact on existing workloads when sharing resources

</details>

## Step 4: Deploy the Solution

💡 **Before You Start:** If you encounter any issues during deployment, check our [Troubleshooting Guide](./TroubleShootingSteps.md) for common solutions.

### 4.1 Authenticate with Azure

```shell
azd auth login
```

**For specific tenants:**
```shell
azd auth login --tenant-id <tenant-id>
```

> **Finding Tenant ID:** 
   > 1. Open the [Azure Portal](https://portal.azure.com/).
   > 2. Navigate to **Microsoft Entra ID** from the left-hand menu.
   > 3. Under the **Overview** section, locate the **Tenant ID** field. Copy the value displayed.

### 4.2 Start Deployment

```shell
azd up
```

**During deployment, you'll be prompted for:**
1. **Environment name** - Must be 3-20 characters, lowercase alphanumeric only (e.g., `cpsapp01`).
2. **Azure subscription** selection.
3. **Azure AI Foundry deployment region** - Select a region with available gpt-4o model quota for AI operations
4. **Primary location** - Select the region where your infrastructure resources will be deployed
5. **Resource group** selection (create new or use existing)

**Expected Duration:** 4-6 minutes for default configuration.

**⚠️ Deployment Issues:** If you encounter errors or timeouts, try a different region as there may be capacity constraints. For detailed error solutions, see our [Troubleshooting Guide](./TroubleShootingSteps.md).

### 4.3 Get Application URL

After successful deployment:
1. The terminal will display the Name, Endpoint (Application URL), and Azure Portal URL for both the Web and API Azure Container Apps.
  
    ![](./images/cp-post-deployment.png)

2. Copy the **Web App Endpoint** to access the application.

⚠️ **Important:** Complete [Post-Deployment Steps](#step-5-post-deployment-configuration) before accessing the application.

## Step 5: Post-Deployment Configuration

### 5.1 Register Schema Files

 > Want to customize the schemas for your own documents? [Learn more about adding your own schemas here.](./CustomizeSchemaData.md)

The below steps will add two sample schemas to the solution: _Invoice_ and _Property Loss Damage Claim Form_:

1. **Get API Service's Endpoint**
    - Get API Service Endpoint Url from your container app for API

      Name is **ca-**<< your environmentName >>-**api**  
      ![Check API Service Url](./images/CheckAPIService.png)  

    - Copy the URL

2. **Execute Script to registering Schemas**
    - Move the folder to samples/schemas in ContentProcessorApi - [/src/ContentProcessorApi/samples/schemas](/src/ContentProcessorApi/samples/schemas)  

    
      Git Bash

      ```bash
      cd src/ContentProcessorAPI/samples/schemas
      ```  

      Powershell

      ```Powershell
      cd .\src\ContentProcessorAPI\samples\schemas\
      ```  

    - Then use below command

      Git Bash

      ```bash
      ./register_schema.sh https://<< API Service Endpoint>>/schemavault/ schema_info_sh.json
      ```  

      Powershell

      ```Powershell
      ./register_schema.ps1 https://<< API Service Endpoint>>/schemavault/ .\schema_info_ps1.json
      ```  

3. **Verify Results**

    ![schema file registration](./images/SchemaFileRegistration.png)  

### 5.2 Import Sample Data
1. Grab the Schema IDs for Invoice and Property Damage Claim Form's Schema from first step
2. Move to the folder location to samples in ContentProcessorApi - [/src/ContentProcessorApi/samples/](/src/ContentProcessorApi/samples/)
3. Execute the script with Schema IDs  

    Bash  

    ```bash
    ./upload_files.sh https://<< API Service Endpoint >>/contentprocessor/submit ./invoices <<Invoice Schema Id>>
    ```

    ```bash
    ./upload_files.sh https://<< API Service Endpoint >>/contentprocessor/submit ./propertyclaims <<Property Loss Damage Claim Form Schema Id>>
    ```

    Windows

    ```powershell
    ./upload_files.ps1 https://<< API Service Endpoint >>/contentprocessor/submit .\invoices <<Invoice Schema Id>>
    ```

    ```powershell
    ./upload_files.ps1 https://<< API Service Endpoint >>/contentprocessor/submit .\propertyclaims <<Property Loss Damage Claim Form Schema Id>>
    ```

### 5.3 Configure Authentication (Required)

**This step is mandatory for application access:**

1. Follow [App Authentication Configuration](./ConfigureAppAuthentication.md).
2. Wait up to 10 minutes for authentication changes to take effect.

### 5.4 Verify Deployment

1. Access your application using the URL from [Step 4.3](#43-get-application-url).
2. Confirm the application loads successfully.
3. Verify you can sign in with your authenticated account.

### 5.5 Test the Application

**Quick Test Steps:**
1. **Download Samples**: Get sample files from the [samples directory](../src/ContentProcessorAPI/samples).
2. **Upload**: In the app, select a **Schema** (e.g., Invoice), click Import Content, and upload a sample file.
3. **Review**: Wait for completion (~1 min), then click the row to verify the extracted data against the source document.

📖 **Detailed Instructions:** See the complete [Sample Workflow](./SampleWorkflow.md) guide for step-by-step testing procedures.

## Step 6: Clean Up (Optional)

### Remove All Resources
```shell
azd down
```
> **Note:** If you deployed with `enableRedundancy=true` and Log Analytics workspace replication is enabled, you must first disable replication before running `azd down` else resource group delete will fail. Follow the steps in [Handling Log Analytics Workspace Deletion with Replication Enabled](./LogAnalyticsReplicationDisable.md), wait until replication returns `false`, then run `azd down`.

### Manual Cleanup (if needed)
If deployment fails or you need to clean up manually:
- Follow [Delete Resource Group Guide](./DeleteResourceGroup.md).

## Managing Multiple Environments

### Recover from Failed Deployment

If your deployment failed or encountered errors, here are the steps to recover:

<details>
<summary><b>Recover from Failed Deployment</b></summary>

**If your deployment failed or encountered errors:**

1. **Try a different region:** Create a new environment and select a different Azure region during deployment
2. **Clean up and retry:** Use `azd down` to remove failed resources, then `azd up` to redeploy
3. **Check troubleshooting:** Review [Troubleshooting Guide](./TroubleShootingSteps.md) for specific error solutions
4. **Fresh start:** Create a completely new environment with a different name

**Example Recovery Workflow:**
```shell
# Remove failed deployment (optional)
azd down

# Create new environment (3-20 chars, alphanumeric only)
azd env new conpro2

# Deploy with different settings/region
azd up
```

</details>

### Creating a New Environment

If you need to deploy to a different region, test different configurations, or create additional environments:

<details>
<summary><b>Create a New Environment</b></summary>

**Create Environment Explicitly:**
```shell
# Create a new named environment (3-20 characters, lowercase alphanumeric only)
azd env new <new-environment-name>

# Select the new environment
azd env select <new-environment-name>

# Deploy to the new environment
azd up
```

**Example:**
```shell
# Create a new environment for production (valid: 3-20 chars)
azd env new conproprod

# Switch to the new environment
azd env select conproprod

# Deploy with fresh settings
azd up
```

> **Environment Naming Requirements:**
> - **Length:** 3-20 characters
> - **Characters:** Lowercase alphanumeric only (a-z, 0-9)
> - **No special characters** (-, _, spaces, etc.)
> - **Valid examples:** `conmig`, `test123`, `myappdev`, `prod2024`
> - **Invalid examples:** `co` (too short), `my-very-long-environment-name` (too long), `test_env` (underscore not allowed), `myapp-dev` (hyphen not allowed)

</details>

<details>
<summary><b>Switch Between Environments</b></summary>

**List Available Environments:**
```shell
azd env list
```

**Switch to Different Environment:**
```shell
azd env select <environment-name>
```

**View Current Environment Variables:**
```shell
azd env get-values
```

</details>

### Best Practices for Multiple Environments

- **Use descriptive names:** `conprodev`, `conproprod`, `conprotest` (remember: 3-20 chars, alphanumeric only)
- **Different regions:** Deploy to multiple regions for testing quota availability
- **Separate configurations:** Each environment can have different parameter settings
- **Clean up unused environments:** Use `azd down` to remove environments you no longer need

## Next Steps

Now that your deployment is complete and tested, explore these resources:

- [Technical Architecture](./TechnicalArchitecture.md) - Understand the system design and components
- [Create Custom Schemas](./CustomizeSchemaData.md) - Learn how to add your own document schemas
- [API Integration](API.md) - Explore programmatic document processing
- [Local Development Setup](./LocalDevelopmentSetup.md) - Set up your local development environment

## Need Help?

- 🐛 **Issues:** Check [Troubleshooting Guide](./TroubleShootingSteps.md)
- 💬 **Support:** Review [Support Guidelines](../SUPPORT.md)
- 🔧 **Development:** See [Contributing Guide](../CONTRIBUTING.md)

---

## Advanced: Deploy Local Code Changes

Use this method to quickly deploy code changes from your local machine to your existing Azure deployment without re-provisioning infrastructure.

> **Note:** To set up and run the application locally for development, see the [Local Development Setup Guide](./LocalDevelopmentSetup.md).

### How it Works
This process will:
1. Rebuild the Docker containers locally using your modified source code.
2. Push the new images to your Azure Container Registry (ACR).
3. Restart the Azure Container Apps to pick up the new images.

### Prerequisites
- **Docker Desktop** must be installed and running.
- You must have an active deployment environment selected (`azd env select <env-name>`).

### Deployment Steps

Run the build and push script for your operating system:

**Linux/macOS:**
```bash
./infra/scripts/docker-build.sh
```

**Windows (PowerShell):**
```powershell
./infra/scripts/docker-build.ps1
```

> **Note:** These scripts will deploy your local code changes instead of pulling from the GitHub repository.
