# Deployment Guide

## **Pre-requisites**

To deploy this solution accelerator, ensure you have access to an [Azure subscription](https://azure.microsoft.com/free/) with the necessary permissions to create **resource groups, resources, app registrations, and assign roles at the resource group level**. This should include Contributor role at the subscription level and Role Based Access Control role on the subscription and/or resource group level. Follow the steps in [Azure Account Set Up](./AzureAccountSetup.md).

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

<br>

### **Important: Check Azure OpenAI Quota Availability**

⚠️ To ensure sufficient quota is available in your subscription, please follow [quota check instructions guide](./quota_check.md) before you deploy the solution.

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

3. Provide an `azd` environment name (e.g., "cpsapp").
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
  

## Next Steps

Now that you've completed your deployment, you can start using the solution. Try out these things to start getting familiar with the capabilities:
* Open the web container app URL in your browser and explore the web user interface and upload your own invoices.
* [Create your own schema definition](./CustomizeSchemaData.md), so you can upload and process your own types of documents.
* [Ingest the API](API.md) for processing documents programmatically.
