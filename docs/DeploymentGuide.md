# Deployment Guide

## **🚀 Quick Start**

Get your Content Processing Solution up and running in Azure with this streamlined process:

1. **🔐 Verify Access** - Confirm you have the right Azure permissions and quota
2. **🏗️ Set Up Environment** - Create a fresh deployment environment 
3. **🚀 Deploy to Azure** - Let Azure Developer CLI handle the infrastructure provisioning
4. **✅ Configure & Validate** - Complete setup and verify everything works

> **🛠️ Having Issues?** Our [Troubleshooting Guide](./TroubleShootingSteps.md) has solutions for common deployment problems.

---

## **Pre-requisites**

### Required Permissions & Access

To deploy this solution accelerator, you need **Azure subscription access** with the following permissions:

**✅ Recommended Permissions:**
- **Owner** role at the subscription or resource group level
- **User Access Administrator** role at the subscription or resource group level

> **Note:** These elevated permissions are required because the deployment creates Managed Identities and assigns roles to them automatically.

**⚠️ Alternative Least-Privilege Setup:**
If you cannot use Owner + User Access Administrator roles, you'll need the following minimum permissions:

| Permission | Required For | Scope |
|------------|-------------|-------|
| **Contributor** | Creating and managing Azure resources | Subscription or Resource Group |
| **User Access Administrator** | Assigning roles to Managed Identities | Resource Group |
| **Application Administrator** (Azure AD) | Creating app registrations for authentication | Tenant |
| **Role Based Access Control Administrator** | Managing role assignments | Resource Group |

> **Important:** With least-privilege setup, you may need to perform some manual steps during deployment. Follow the steps in [Azure Account Set Up](./AzureAccountSetup.md) for detailed guidance.

Check the [Azure Products by Region](https://azure.microsoft.com/en-us/explore/global-infrastructure/products-by-region/?products=all&regions=all) page and select a **region** where the following services are available:

- [Azure AI Foundry](https://learn.microsoft.com/en-us/azure/ai-foundry/)
- [Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [Azure AI Content Understanding Service](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/)
- [Azure Blob Storage](https://learn.microsoft.com/en-us/azure/storage/blobs/)
- [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/)
- [Azure Container Registry](https://learn.microsoft.com/en-us/azure/container-registry/)
- [Azure Cosmos DB](https://learn.microsoft.com/en-us/azure/cosmos-db/)
- [Azure Queue Storage](https://learn.microsoft.com/en-us/azure/storage/queues/)
- [GPT Model Capacity](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models)

Here are some example regions where the services are available: East US, East US2, Australia East, UK South, France Central.

### **Important: Note for PowerShell Users**

If you encounter issues running PowerShell scripts due to the policy of not being digitally signed, you can temporarily adjust the `ExecutionPolicy` by running the following command in an elevated PowerShell session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

This will allow the scripts to run for the current session without permanently changing your system's policy.

### **Important: Check Azure OpenAI Quota Availability**

⚠️ To ensure sufficient quota is available in your subscription, please follow [quota check instructions guide](./quota_check.md) before you deploy the solution.

### 🛠️ Troubleshooting & Common Issues

**Before starting deployment**, be aware of these common issues and solutions:

| **Common Issue** | **Quick Solution** | **Full Guide Link** |
|-----------------|-------------------|---------------------|
| **ReadOnlyDisabledSubscription** | Check if you have an active subscription | [Troubleshooting Guide](./TroubleShootingSteps.md#readonlydisabledsubscription) |
| **InsufficientQuota** | Verify quota availability | [Quota Check Guide](./quota_check.md) |
| **ResourceGroupNotFound** | Create new environment with `azd env new` | [Troubleshooting Guide](./TroubleShootingSteps.md#resourcegroupnotfound) |
| **InvalidParameter (Workspace Name)** | Use compliant names (3-33 chars, alphanumeric) | [Troubleshooting Guide](./TroubleShootingSteps.md#workspace-name---invalidparameter) |
| **ResourceNameInvalid** | Follow Azure naming conventions | [Troubleshooting Guide](./TroubleShootingSteps.md#resourcenameinvalid) |

> **If you encounter deployment errors:** Refer to the [complete troubleshooting guide](./TroubleShootingSteps.md) with comprehensive error solutions.


## Choose Your Deployment Environment

Select one of the following options to deploy the Accelerator:

### Environment Comparison

| **Option** | **Best For** | **Prerequisites** | **Setup Time** |
|------------|--------------|-------------------|----------------|
| **GitHub Codespaces** | Quick deployment, no local setup required | GitHub account with Codespace enabled | ~3-5 minutes |
| **VS Code Dev Containers** | Fast deployment with local tools | Docker Desktop, VS Code | ~5-10 minutes |
| **Visual Studio Code (WEB)** | Quick deployment, no local setup required | Azure account | ~2-4 minutes |
| **Local Environment** | Enterprise environments, full control | All tools individually | ~15-30 minutes |

**💡 Recommendation:** For fastest deployment, start with **GitHub Codespaces** - no local installation required.

---

<details>
  <summary><b>Option 1: Deploy in GitHub Codespaces</b></summary>

### GitHub Codespaces

You can run this solution using [GitHub Codespaces](https://docs.github.com/en/codespaces). The button will open a web-based VS Code instance in your browser:

1. Open the solution accelerator (this may take several minutes):

    [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/microsoft/content-processing-solution-accelerator)

2. Accept the default values on the create Codespaces page.
3. Open a terminal window if it is not already open.
4. Continue with the [deploying steps](#deploying-with-azd).

</details>

<details>
  <summary><b>Option 2: Deploy in VS Code Dev Containers</b></summary>

### VS Code Dev Containers

You can run this solution in [VS Code Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers), which will open the project in your local VS Code using the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers):

1. Start Docker Desktop (install it if not already installed).
2. Open the project:

    [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/microsoft/content-processing-solution-accelerator)

3. In the VS Code window that opens, once the project files show up (this may take several minutes), open a terminal window.
4. Continue with the [deploying steps](#deploying-with-azd).

</details>

<details>
  <summary><b>Option 3:Deploy in Visual Studio Code (WEB)</b></summary>

### Visual Studio Code (WEB)

You can run this solution in VS Code Web. The button will open a web-based VS Code instance in your browser:

1. Open the solution accelerator (this may take several minutes):

    [![Open in Visual Studio Code Web](https://img.shields.io/static/v1?style=for-the-badge&label=Visual%20Studio%20Code%20(Web)&message=Open&color=blue&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/azure/?vscode-azure-exp=foundry&agentPayload=eyJiYXNlVXJsIjogImh0dHBzOi8vcmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbS9taWNyb3NvZnQvY29udGVudC1wcm9jZXNzaW5nLXNvbHV0aW9uLWFjY2VsZXJhdG9yL3JlZnMvaGVhZHMvbWFpbi9pbmZyYS92c2NvZGVfd2ViIiwgImluZGV4VXJsIjogIi9pbmRleC5qc29uIiwgInZhcmlhYmxlcyI6IHsiYWdlbnRJZCI6ICIiLCAiY29ubmVjdGlvblN0cmluZyI6ICIiLCAidGhyZWFkSWQiOiAiIiwgInVzZXJNZXNzYWdlIjogIiIsICJwbGF5Z3JvdW5kTmFtZSI6ICIiLCAibG9jYXRpb24iOiAiIiwgInN1YnNjcmlwdGlvbklkIjogIiIsICJyZXNvdXJjZUlkIjogIiIsICJwcm9qZWN0UmVzb3VyY2VJZCI6ICIiLCAiZW5kcG9pbnQiOiAiIn0sICJjb2RlUm91dGUiOiBbImFpLXByb2plY3RzLXNkayIsICJweXRob24iLCAiZGVmYXVsdC1henVyZS1hdXRoIiwgImVuZHBvaW50Il19)

2. When prompted, sign in using your Microsoft account linked to your Azure subscription.
    
    Select the appropriate subscription to continue.

3. Once the solution opens, the **AI Foundry terminal** will automatically start running the following command to install the required dependencies:

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
 
4. Continue with the [deploying steps](#deploying-with-azd).


</details>

<details>
  <summary><b>Option 4: Deploy in your local Environment</b></summary>

### Local Environment

If you're not using one of the above options for opening the project, then you'll need to:

1. Make sure the following tools are installed:
    - [PowerShell](https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell?view=powershell-7.5) <small>(v7.0+)</small> - available for Windows, macOS, and Linux.
    - [Azure Developer CLI (azd)](https://aka.ms/install-azd) <small>(v1.18.0+)</small> - version
    - [Python 3.9+](https://www.python.org/downloads/)
    - [Docker Desktop](https://www.docker.com/products/docker-desktop/)
    - [Git](https://git-scm.com/downloads)

2. Clone the repository or download the project code via command-line:

    ```shell
    azd init -t microsoft/content-processing-solution-accelerator/
    ```

3. Open the project folder in your terminal or editor.
4. Continue with the [deploying steps](#deploying-with-azd).

</details>

### Choose Deployment Type (Optional)

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

<details>
<summary><b>Option 1: Manual Copy (Recommended for beginners)</b></summary>

1. Navigate to the `infra` folder in your project
2. Open `main.waf.parameters.json` in a text editor (like Notepad, VS Code, etc.)
3. Select all content (Ctrl+A) and copy it (Ctrl+C)
4. Open `main.parameters.json` in the same text editor
5. Select all existing content (Ctrl+A) and paste the copied content (Ctrl+V)
6. Save the file (Ctrl+S)

</details>

<details>
<summary><b>Option 2: Using Command Line</b></summary>

**For Linux/macOS/Git Bash:**
```bash
# Copy contents from production file to main parameters file
cat infra/main.waf.parameters.json > infra/main.parameters.json
```

**For Windows PowerShell:**
```powershell
# Copy contents from production file to main parameters file
Get-Content infra/main.waf.parameters.json | Set-Content infra/main.parameters.json
```

</details>

### Set VM Credentials (Optional - Production Deployment Only)

> **Note:** This section only applies if you selected **Production** deployment type in section 3.1. VMs are not deployed in the default Development/Testing configuration.

By default, random GUIDs are generated for VM credentials. To set custom credentials:

```shell
azd env set AZURE_ENV_VM_ADMIN_USERNAME <your-username>
azd env set AZURE_ENV_VM_ADMIN_PASSWORD <your-password>
```

Consider the following settings during your deployment to modify specific settings:

<details>
  <summary><b>Configurable Deployment Settings</b></summary>

When you start the deployment, most parameters will have **default values**, but you can update the following settings by following the steps [here](../docs/CustomizingAzdParameters.md)

</details>

<details>
  <summary><b>[Optional] Quota Recommendations</b></summary>

By default, the **GPT model capacity** in deployment is set to **30k tokens**.  
> **We recommend increasing the capacity to 100k tokens, if available, for optimal performance.**

To adjust quota settings, follow these [steps](./AzureGPTQuotaSettings.md).

**⚠️ Warning:** Insufficient quota can cause deployment errors. Please ensure you have the recommended capacity or request additional capacity before deploying this solution.

</details>

<details>

  <summary><b>Reusing an Existing Log Analytics Workspace</b></summary>

  Guide to get your [Existing Workspace ID](/docs/re-use-log-analytics.md)

</details>

<details>

  <summary><b>Reusing an Existing Azure AI Foundry Project</b></summary>

  Guide to get your [Existing Project ID](/docs/re-use-foundry-project.md)

</details>

### Deploying with AZD

Once you've opened the project in [Codespaces](#github-codespaces), [Dev Containers](#vs-code-dev-containers), [Visual Studio Code (WEB)](#visual-studio-code-web), or [locally](#local-environment), you can deploy it to Azure by following these steps:

#### Important: Environment Management for Redeployments

> **⚠️ Critical:** If you're redeploying or have deployed this solution before, you **must** create a fresh environment to avoid conflicts and deployment failures.

**Choose one of the following before deployment:**

**Option A: Create a completely new environment (Recommended)**
```shell
azd env new <new-environment-name>
```

**Option B: Reinitialize in a new directory**
```shell
# Navigate to a new directory
cd ../my-new-deployment
azd init -t microsoft/content-processing-solution-accelerator
```

> **💡 Why is this needed?** Azure resources maintain state information tied to your environment. Reusing an old environment can cause naming conflicts, permission issues, and deployment failures.

#### Environment Naming Requirements

When creating your environment name, follow these rules:
- **Maximum 14 characters** (will be expanded to meet Azure resource naming requirements)
- **Only lowercase letters and numbers** (a-z, 0-9)
- **No special characters** (-, _, spaces, etc.)
- **Examples:** `cpsapp01`, `mycontentapp`, `devtest123`

> **💡 Tip:** Use a descriptive prefix + environment + suffix to form a a unique string

#### Deployment Steps

> If you encounter any issues during the deployment process, refer to the [troubleshooting guide](../docs/TroubleShootingSteps.md) for detailed steps and solutions.

1. Login to Azure:

    ```shell
    azd auth login
    ```

    #### To authenticate with Azure Developer CLI (`azd`), use the following command with your **Tenant ID**:

    ```sh
    azd auth login --tenant-id <tenant-id>
    ```

    > **Note:** To retrieve the Tenant ID required for local deployment, you can go to **Tenant Properties** in [Azure Portal](https://portal.azure.com/) from the resource list. Alternatively, follow these steps:
    >
    > 1. Open the [Azure Portal](https://portal.azure.com/).
    > 2. Navigate to **Microsoft Entra ID** from the left-hand menu.
    > 3. Under the **Overview** section, locate the **Tenant ID** field. Copy the value displayed.

2. Provision and deploy all the resources:

    ```shell
    azd up
    ```
    > **Note:** This solution accelerator requires **Azure Developer CLI (azd) version 1.18.0 or higher**. Please ensure you have the latest version installed before proceeding with deployment. [Download azd here](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd).

3. **Provide an `azd` environment name** - Use the naming requirements above (e.g., "cpsapp01").
4. Select a subscription from your Azure account and choose a location that has quota for all the resources. 
    - This deployment will take *4-6 minutes* to provision the resources in your account and set up the solution with sample data.
    - If you encounter an error or timeout during deployment, changing the location may help, as there could be availability constraints for the resources.

5. Once the deployment has completed successfully:
    > Please check the terminal or console output for details of the successful deployment. It will display the Name, Endpoint (Application URL), and Azure Portal URL for both the Web and API Azure Container Apps.

    ![](./images/cp-post-deployment.png)

    - You can find the Azure portal link in the screenshot above. Click on it to navigate to the corresponding resource group in the Azure portal.

    > #### Important Note : Before accessing the application, ensure that all **[Post Deployment Steps](#post-deployment-steps)** are fully completed, as they are critical for the proper configuration of **Data Ingestion** and **Authentication** functionalities.

> If you encounter any issues during the deployment process, refer to the [troubleshooting guide](../docs/TroubleShootingSteps.md) for detailed steps and solutions.

## Post Deployment Steps
1. **Register Schema Files**

     > Want to customize the schemas for your own documents? [Learn more about adding your own schemas here.](./CustomizeSchemaData.md)

    The below steps will add two sample schemas to the solution: _Invoice_ and _Property Loss Damage Claim Form_:

    - **Get API Service's Endpoint**
        - Get API Service Endpoint Url from your container app for API  
          Name is **ca-**<< your environmentName >>-**api**  
          ![Check API Service Url](./images/CheckAPIService.png)  

        - Copy the URL  
    - **Execute Script to registering Schemas**
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

    - **Verify Results**
    
        ![schema file registration](./images/SchemaFileRegistration.png)  

3. **Import Sample Data**  
    - Grab the Schema IDs for Invoice and Property Damage Claim Form's Schema from first step
    - Move to the folder location to samples in ContentProcessorApi - [/src/ContentProcessorApi/samples/](/src/ContentProcessorApi/samples/)
    - Execute the script with Schema IDs  

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

2. **Add Authentication Provider**  
    - Follow steps in [App Authentication](./ConfigureAppAuthentication.md) to configure authentication in app service. Note that Authentication changes can take up to 10 minutes.  

## Deployment Success Validation

After deployment completes, use this checklist to verify everything is working correctly:

### Deployment Validation Checklist

**1. Basic Deployment Verification**
- [ ] `azd up` completed successfully without errors
- [ ] All Azure resources are created in the resource group
- [ ] Both Web and API container apps are running

**2. Container Apps Health Check**
```powershell
# Test Web App (replace <your-web-app-url> with actual URL from deployment output)
curl -I https://<your-web-app-url>/

# Test API App (replace <your-api-app-url> with actual URL)
curl -I https://<your-api-app-url>/health
```
**Expected Result:** Both should return HTTP 200 status


### Sample Test Commands

**API Health Check:**
```bash
curl https://<your-api-endpoint>/health
```

**Web App Accessibility:**
```bash
curl -I https://<your-web-endpoint>/
```

**Schema Registration Verification:**
```bash
curl https://<your-api-endpoint>/schemavault/schemas
```

## Running the application

To help you get started, here's the [Sample Workflow](./SampleWorkflow.md) you can follow to try it out.

## Clean Up Resources

When you're done testing the solution or need to clean up after deployment issues, you have several options:

### 🧹 Environment Cleanup

**To clean up azd environments:**
```powershell
# List all environments
azd env list

# Clean up a specific environment
azd env select <old-environment-name>
azd down --force --purge
```

> **Tip:** If you have old environments that failed deployment or are no longer needed, use the commands above to clean them up before creating new ones.

> **Note:** If you deployed with `enableRedundancy=true` and Log Analytics workspace replication is enabled, you must first disable replication before running `azd down` else resource group delete will fail. Follow the steps in [Handling Log Analytics Workspace Deletion with Replication Enabled](./LogAnalyticsReplicationDisable.md), wait until replication returns `false`, then run `azd down`.

### 🗑️ Azure Resource Group Cleanup

**To clean up Azure resource groups (if needed):**
```powershell
# List resource groups
az group list --output table

# Delete a specific resource group
az group delete --name <resource-group-name> --yes --no-wait
```

### 📝 Deleting Resources After a Failed Deployment

- Follow detailed steps in [Delete Resource Group](./DeleteResourceGroup.md) if your deployment fails and/or you need to clean up the resources.

> **⚠️ Important:** Always ensure you want to permanently delete resources before running cleanup commands. These operations cannot be undone.

### Troubleshooting Failed Validation

**If any checks fail:**
1. Check Azure Portal → Resource Group → Container Apps for error logs
2. Review deployment logs: `azd show`
3. Verify all post-deployment steps are completed
4. Check [Troubleshooting Guide](./TroubleShootingSteps.md) for specific error solutions

## Next Steps

Now that you've validated your deployment, you can start add your own schema or modify the existing one to meet your requirements:

### Getting Started
* **Create Custom Schemas:** [Learn how to add your own document schemas](./CustomizeSchemaData.md)

* **API Integration:** [Explore programmatic document processing](API.md)

## Local Development

If you need to modify the source code and test changes locally, follow these steps:

### Publishing Local Build Container to Azure Container Registry

To rebuild the source code and push the updated container to the deployed Azure Container Registry:

- **Linux/macOS**:
  ```bash
  cd ./infra/scripts/

  ./docker-build.sh
  ```

- **Windows (PowerShell)**:
  ```powershell
  cd .\infra\scripts\

  .\docker-build.ps1
  ```

This will rebuild the source code, package it into a container, and push it to the Azure Container Registry created during deployment.

### Environment Configuration for Local Development & Debugging

**Creating env file**

> Navigate to the `src` folder of the project.

1. Locate the `.env` file inside the `src` directory.
2. To fill in the required values, follow these steps:
   - Go to the Azure Portal.
   - Navigate to your **Resource Group**.
   - Open the **Web Container** resource.
   - In the left-hand menu, select **Containers**.
   - Go to the **Environment Variables** tab.
   - Copy the necessary environment variable values and paste them into your local `.env` file.
  
