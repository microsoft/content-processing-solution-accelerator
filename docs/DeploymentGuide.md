# Deployment Guide

## **🚀 Quick Start**

Ready to deploy? Follow these essential steps:

1. **Check Prerequisites** - Verify your Azure permissions (Owner + User Access Administrator) and quota availability
2. **Create Environment** - Use `azd env new <environment-name>` (max 14 chars, alphanumeric only)
3. **Deploy** - Run `azd up` and follow the prompts
4. **Validate** - Use our [deployment validation checklist](#-deployment-success-validation) to ensure success

> **⚠️ Prerequisites Check:** Ensure you have **Owner + User Access Administrator** roles in your Azure subscription for smooth deployment. See [Prerequisites](#pre-requisites) below for details.

> **🛠️ Need Help?** Check our [Troubleshooting Guide](./TroubleShootingSteps.md) for solutions to 25+ common deployment issues.

---

## **Pre-requisites**

### Required Permissions & Access

To deploy this solution accelerator, you need **Azure subscription access** with the following permissions:

**✅ Recommended Permissions (Simplest Setup):**
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

### **Cost Estimation**

Pricing varies per region and usage, so it isn't possible to predict exact costs for your usage. The majority of the Azure resources used in this infrastructure are on usage-based pricing tiers. However, Azure Container Registry has a fixed cost per registry per day.

Use the [Azure pricing calculator](https://azure.microsoft.com/en-us/pricing/calculator) to calculate the cost of this solution in your subscription. [Review a sample pricing sheet for the architecture](https://azure.com/e/0a9a1459d1a2440ca3fd274ed5b53397).

| Product | Description | Cost |
|---|---|---|
| [Azure AI Foundry](https://learn.microsoft.com/en-us/azure/ai-foundry/) | Build generative AI applications on an enterprise-grade platform | [Pricing](https://azure.microsoft.com/pricing/details/ai-studio/) |
| [Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/) | Provides REST API access to OpenAI's powerful language models including o3-mini, o1, o1-mini, GPT-4o, GPT-4o mini | [Pricing](https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/) |
| [Azure AI Content Understanding Service](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/) | Analyzes various media content—such as audio, video, text, and images—transforming it into structured, searchable data | [Pricing](https://azure.microsoft.com/en-us/pricing/details/content-understanding/) |
| [Azure Blob Storage](https://learn.microsoft.com/en-us/azure/storage/blobs/) | Microsoft's object storage solution for the cloud. Blob storage is optimized for storing massive amounts of unstructured data | [Pricing](https://azure.microsoft.com/pricing/details/storage/blobs/) |
| [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/) | Allows you to run containerized applications without worrying about orchestration or infrastructure. | [Pricing](https://azure.microsoft.com/pricing/details/container-apps/) |
| [Azure Container Registry](https://learn.microsoft.com/en-us/azure/container-registry/) | Build, store, and manage container images and artifacts in a private registry for all types of container deployments | [Pricing](https://azure.microsoft.com/pricing/details/container-registry/) |
| [Azure Cosmos DB](https://learn.microsoft.com/en-us/azure/cosmos-db/) | Fully managed, distributed NoSQL, relational, and vector database for modern app development | [Pricing](https://azure.microsoft.com/en-us/pricing/details/cosmos-db/autoscale-provisioned/) |
| [Azure Queue Storage](https://learn.microsoft.com/en-us/azure/storage/queues/) | Store large numbers of messages and access messages from anywhere in the world via HTTP or HTTPS. | [Pricing](https://azure.microsoft.com/pricing/details/storage/queues/) |
| [GPT Model Capacity](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models) | The latest most capable Azure OpenAI models with multimodal versions, accepting both text and images as input | [Pricing](https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/) |

>⚠️ **Important:** To avoid unnecessary costs, remember to take down your app if it's no longer in use, either by deleting the resource group in the Portal or running `azd down`.

### **Important: Note for PowerShell Users**

If you encounter issues running PowerShell scripts due to the policy of not being digitally signed, you can temporarily adjust the `ExecutionPolicy` by running the following command in an elevated PowerShell session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

This will allow the scripts to run for the current session without permanently changing your system's policy.

<br>

### **Important: Check Azure OpenAI Quota Availability**

⚠️ To ensure sufficient quota is available in your subscription, please follow [quota check instructions guide](./quota_check.md) before you deploy the solution.

### **🛠️ Troubleshooting & Common Issues**

**Before you start deployment**, be aware of these common issues and solutions:

| **Common Issue** | **Quick Solution** | **Full Guide Link** |
|-----------------|-------------------|---------------------|
| **ReadOnlyDisabledSubscription** | Check if you have an active subscription | [Troubleshooting Guide](./TroubleShootingSteps.md#readonlydisabledsubscription) |
| **InsufficientQuota** | Verify quota availability | [Quota Check Guide](./quota_check.md) |
| **ResourceGroupNotFound** | Create new environment with `azd env new` | [Troubleshooting Guide](./TroubleShootingSteps.md#resourcegroupnotfound) |
| **InvalidParameter (Workspace Name)** | Use compliant names (3-33 chars, alphanumeric) | [Troubleshooting Guide](./TroubleShootingSteps.md#workspace-name---invalidparameter) |
| **ResourceNameInvalid** | Follow Azure naming conventions | [Troubleshooting Guide](./TroubleShootingSteps.md#resourcenameinvalid) |

> **🚨 If you encounter deployment errors:** Check the [complete troubleshooting guide](./TroubleShootingSteps.md) with 25+ common error solutions.

<br/>   


## Deployment Options & Steps

Pick from the options below to see step-by-step instructions for GitHub Codespaces, VS Code Dev Containers, and Local Environments.

| [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/microsoft/content-processing-solution-accelerator) | [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/microsoft/content-processing-solution-accelerator) |
|---|---|

<details>
  <summary><b>Deploy in GitHub Codespaces</b></summary>

### GitHub Codespaces

You can run this solution using [GitHub Codespaces](https://docs.github.com/en/codespaces). The button will open a web-based VS Code instance in your browser:

1. Open the solution accelerator (this may take several minutes):

    [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/microsoft/content-processing-solution-accelerator)

2. Accept the default values on the create Codespaces page.
3. Open a terminal window if it is not already open.
4. Continue with the [deploying steps](#deploying-with-azd).

</details>

<details>
  <summary><b>Deploy in VS Code Dev Containers</b></summary>

### VS Code Dev Containers

You can run this solution in [VS Code Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers), which will open the project in your local VS Code using the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers):

1. Start Docker Desktop (install it if not already installed).
2. Open the project:

    [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/microsoft/content-processing-solution-accelerator)

3. In the VS Code window that opens, once the project files show up (this may take several minutes), open a terminal window.
4. Continue with the [deploying steps](#deploying-with-azd).

</details>

<details>
  <summary><b>Deploy in your local Environment</b></summary>

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

<br/>

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

Once you've opened the project in [Codespaces](#github-codespaces), [Dev Containers](#vs-code-dev-containers), or [locally](#local-environment), you can deploy it to Azure by following these steps:

#### **🔄 Important: Environment Management for Redeployments**

> **⚠️ CRITICAL:** If you're redeploying or have deployed this solution before, you **MUST** create a fresh environment to avoid conflicts and deployment failures.

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

#### **📝 Environment Naming Requirements**

When creating your environment name, follow these rules:
- **Maximum 14 characters** (will be expanded to meet Azure resource naming requirements)
- **Only lowercase letters and numbers** (a-z, 0-9)
- **No special characters** (-, _, spaces, etc.)
- **Must start with a letter**
- **Examples:** `cpsapp01`, `mycontentapp`, `devtest123`

❌ **Invalid names:** `cps-app`, `CPS_App`, `content-processing`, `my app`  
✅ **Valid names:** `cpsapp01`, `mycontentapp`, `devtest123`

> **� Tips for generating compliant names:**
> - Start with a descriptive prefix like `cps`, `content`, `docproc`, `myapp`
> - Add a suffix like `dev`, `test`, `prod`, or numbers `01`, `02`
> - Keep it memorable and relevant to your use case
> - Examples: `cpsdev01`, `contentprod`, `myapptest`, `docproc123`

#### **🧹 Environment Cleanup**

> **💡 Tip:** If you have old environments that failed deployment or are no longer needed:
> 
> **To clean up azd environments:**
> ```powershell
> # List all environments
> azd env list
> 
> # Clean up a specific environment
> azd env select <old-environment-name>
> azd down --force --purge
> ```
> 
> **To clean up Azure resource groups (if needed):**
> ```powershell
> # List resource groups
> az group list --output table
> 
> # Delete a specific resource group
> az group delete --name <resource-group-name> --yes --no-wait
> ```

#### **🚀 Deployment Steps**

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
    > 2. Navigate to **Azure Active Directory** from the left-hand menu.
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

7. If you are done trying out the application, you can delete the resources by running `azd down`.

### 🛠️ Troubleshooting
 If you encounter any issues during the deployment process, please refer  [troubleshooting](../docs/TroubleShootingSteps.md) document for detailed steps and solutions

## Post Deployment Steps
1. Optional: Publishing Local Build Container to Azure Container Registry 

   If you need to rebuild the source code and push the updated container to the deployed Azure Container Registry, follow these steps:

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

    This will create a new Azure Container Registry, rebuild the source code, package it into a container, and push it to the Container Registry created.

2. **Register Schema Files**

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

3. **Add Authentication Provider**  
    - Follow steps in [App Authentication](./ConfigureAppAuthentication.md) to configure authenitcation in app service. Note that Authentication changes can take up to 10 minutes.  

4. **Deleting Resources After a Failed Deployment**  

     - Follow steps in [Delete Resource Group](./DeleteResourceGroup.md) if your deployment fails and/or you need to clean up the resources.
  
## Running the application

To help you get started, here's the [Sample Workflow](./SampleWorkflow.md) you can follow to try it out.

## Environment configuration for local development & debugging
**Creating env file**

> Navigate to the `src` folder of the project.

1. Locate the `.env` file inside the `src` directory.
2. To fill in the required values, follow these steps
- Go to the Azure Portal.
- Navigate to your **Resource Group**.
- Open the **Web Container** resource.
- In the left-hand menu, select **Containers**.
- Go to the **Environment Variables** tab.
- Copy the necessary environment variable values and paste them into your local `.env` file.
  

## 🎯 Deployment Success Validation

After deployment completes, use this checklist to verify everything is working correctly:

### **✅ Deployment Validation Checklist**

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

**3. Authentication Configuration**
- [ ] App authentication is configured (see [App Authentication Guide](./ConfigureAppAuthentication.md))
- [ ] You can access the web application without errors
- [ ] Login flow works correctly

**4. Sample Data Processing Test**
```powershell
# Navigate to API samples directory
cd src/ContentProcessorAPI/samples/schemas

# Register sample schemas (use your API endpoint)
./register_schema.ps1 https://<your-api-endpoint>/schemavault/ .\schema_info_ps1.json

# Upload sample documents (use returned schema IDs)
cd ../
./upload_files.ps1 https://<your-api-endpoint>/contentprocessor/submit .\invoices <Invoice-Schema-ID>
```
**Expected Result:** Files upload successfully and appear in the web interface

**5. End-to-End Workflow Test**
- [ ] Can select a schema in the web interface
- [ ] Can upload a document successfully
- [ ] Document processes to "Completed" status
- [ ] Can view extracted data in the web interface
- [ ] Can modify and save extracted data
- [ ] Can view process steps and logs

### **🧪 Sample Test Commands**

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

### **📊 Success Indicators**

**Deployment is successful when:**
- ✅ Web app loads without errors
- ✅ API health endpoint returns `{"status": "healthy"}`
- ✅ Sample schemas register successfully
- ✅ Sample documents upload and process completely
- ✅ Authentication works (after configuration)
- ✅ All container apps show "Running" status in Azure Portal

### **🔍 Troubleshooting Failed Validation**

**If any checks fail:**
1. Check Azure Portal → Resource Group → Container Apps for error logs
2. Review deployment logs: `azd show`
3. Verify all post-deployment steps are completed
4. Check [Troubleshooting Guide](./TroubleShootingSteps.md) for specific error solutions

## Next Steps

Now that you've validated your deployment, you can start using the solution:

### **🚀 Getting Started**
* **Try the Sample Workflow:** Follow our [Sample Workflow Guide](./SampleWorkflow.md) for a step-by-step walkthrough
* **Upload Your Own Documents:** Open the web container app URL and explore the user interface
* **Create Custom Schemas:** [Learn how to add your own document schemas](./CustomizeSchemaData.md)
* **API Integration:** [Explore programmatic document processing](API.md)

### **🎯 Golden Path Workflows**

For the best experience, follow our **[Golden Path Workflows Guide](./GoldenPathWorkflows.md)** which includes:

1. **Invoice Processing Golden Path:**
   - Complete step-by-step invoice processing workflow
   - Learn confidence scoring and validation features
   - Practice data modification and approval processes

2. **Property Claims Golden Path:**
   - Advanced form processing with complex data structures
   - Multi-modal content extraction (text, images, tables)
   - Validation rule application and quality assurance

3. **Custom Document Processing:**
   - Create and test your own document schemas
   - Optimize extraction quality through iterative refinement
   - Scale to production volumes with best practices

> **📖 [Complete Golden Path Workflows Guide](./GoldenPathWorkflows.md)** - Detailed step-by-step instructions, expected outcomes, and best practices.

> **💡 Pro Tip:** The solution includes confidence scoring and human-in-the-loop validation. Use the confidence thresholds to determine which documents need manual review. The golden path workflows will teach you how to interpret and act on these scores effectively.
