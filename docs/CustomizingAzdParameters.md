## [Optional]: Customizing resource names 

By default this template will use the environment name as the prefix to prevent naming collisions within Azure. The parameters below show the default values. You only need to run the statements below if you need to change the values. 


> To override any of the parameters, run `azd env set <PARAMETER_NAME> <VALUE>` before running `azd up`. On the first azd command, it will prompt you for the environment name. Be sure to choose 3-20 characters alphanumeric unique name. 

## Parameters

| Name                                   | Type    | Example Value               | Purpose                                                                               |
| -------------------------------------- | ------- | --------------------------- | ------------------------------------------------------------------------------------- |
| `AZURE_ENV_NAME`                       | string  | `cps`                     | Sets the environment name prefix for all Azure resources (3-20 characters).            |
| `AZURE_LOCATION`                       | string  | `eastus2`                  | Sets the primary Azure region for resource deployment. Allowed: `australiaeast`, `centralus`, `eastasia`, `eastus2`, `japaneast`, `northeurope`, `southeastasia`, `uksouth`. |
| `AZURE_ENV_AI_SERVICE_LOCATION`    | string  | `eastus2`                  | Sets the location for Azure AI Services. This single account hosts both Azure OpenAI and Content Understanding. Allowed: `australiaeast`, `eastus`, `eastus2`, `japaneast`, `southcentralus`, `southeastasia`, `swedencentral`, `uksouth`, `westeurope`, `westus`, `westus3`. |
| `AZURE_ENV_MODEL_DEPLOYMENT_TYPE`      | string  | `GlobalStandard`          | Defines the model deployment type. Allowed: `Standard`, `GlobalStandard`.<br>**Note:** the `azd` location-picker filters regions using the `usageName` metadata on `azureAiServiceLocation` in `infra/main.bicep` (currently `OpenAI.GlobalStandard.gpt-5.1,300`). If you set this parameter to `Standard`, also edit that metadata to `OpenAI.Standard.gpt-5.1,300` so the picker shows the correct subset of regions. |
| `AZURE_ENV_GPT_MODEL_NAME`                 | string  | `gpt-5.1`                 | Specifies the GPT model name. Default: `gpt-5.1`.                                     |
| `AZURE_ENV_GPT_MODEL_VERSION`              | string  | `2025-11-13`              | Specifies the GPT model version.                                                      |
| `AZURE_ENV_GPT_MODEL_CAPACITY`             | integer | `300`                       | Sets the model capacity (minimum 1). Default: 300. Optimal: 500 for multi-document claim processing. |
| `AZURE_ENV_CONTAINER_REGISTRY_ENDPOINT` | string  | `cpscontainerreg.azurecr.io` | Sets the public container image endpoint for pulling pre-built images.                |
| `AZURE_ENV_IMAGETAG`        | string  | `latest_v2`                 | Sets the container image tag (e.g., `latest_v2`, `dev`, `demo`, `hotfix`).                    |
| `AZURE_ENV_EXISTING_LOG_ANALYTICS_WORKSPACE_RID` | string  | Guide to get your [Existing Workspace Resource ID](re-use-log-analytics.md) | Reuses an existing Log Analytics Workspace instead of provisioning a new one.         |
| `AZURE_EXISTING_AIPROJECT_RESOURCE_ID`         | string  | Guide to get your [Existing AI Project Resource ID](re-use-foundry-project.md) | Reuses an existing AI Foundry and AI Foundry Project instead of creating a new one.   |
| `AZURE_ENV_VM_SIZE` | string | `Standard_D2s_v5` | Overrides the jumpbox VM size (private networking only). Default: `Standard_D2s_v5`. |

## How to Set a Parameter

To customize any of the above values, run the following command **before** `azd up`:

```bash
azd env set <PARAMETER_NAME> <VALUE>
```

**Example:**

```bash
azd env set AZURE_LOCATION westus2
```
