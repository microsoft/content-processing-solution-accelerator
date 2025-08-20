## [Optional]: Customizing resource names 

By default this template will use the environment name as the prefix to prevent naming collisions within Azure. The parameters below show the default values. You only need to run the statements below if you need to change the values. 


> To override any of the parameters, run `azd env set <PARAMETER_NAME> <VALUE>` before running `azd up`. On the first azd command, it will prompt you for the environment name. Be sure to choose 3-20 characters alphanumeric unique name. 

## Parameters

| Name                                   | Type    | Example Value               | Purpose                                                                               |
| -------------------------------------- | ------- | --------------------------- | ------------------------------------------------------------------------------------- |
| `AZURE_ENV_NAME`                       | string  | `cps`                     | Sets the environment name prefix for all Azure resources.                             |
| `AZURE_ENV_SECONDARY_LOCATION`         | string  | `eastus2`                 | Specifies a secondary Azure region.                                                   |
| `AZURE_ENV_CU_LOCATION`                | string  | `WestUS`                  | Sets the location for the Azure Content Understanding service.                        |
| `AZURE_ENV_MODEL_DEPLOYMENT_TYPE`      | string  | `GlobalStandard`          | Defines the model deployment type (allowed values: `Standard`, `GlobalStandard`).     |
| `AZURE_ENV_MODEL_NAME`                 | string  | `gpt-4o`                  | Specifies the GPT model name (allowed values: `gpt-4o`).       
| `AZURE_ENV_MODEL_VERSION`                 | string  | `2024-08-06`                  | Specifies the GPT model version (allowed values: `2024-08-06`).                       |
| `AZURE_ENV_MODEL_CAPACITY`             | integer | `30`                        | Sets the model capacity (choose based on your subscription's available GPT capacity). |
| `AZURE_ENV_IMAGETAG`                      | boolean | `latest`                     | Set the Image tag Like (allowed values: latest, dev, hotfix)                       |
| `AZURE_ENV_LOG_ANALYTICS_WORKSPACE_ID` | string  | Guide to get your [Existing Workspace ID](/docs/re-use-log-analytics.md) | Reuses an existing Log Analytics Workspace instead of provisioning a new one.         |
| `AZURE_EXISTING_AI_PROJECT_RESOURCE_ID`    | string  | `<Existing AI Project resource Id>`            | Reuses an existing AIFoundry and AIFoundryProject instead of creating a new one.  |

## How to Set a Parameter

To customize any of the above values, run the following command **before** `azd up`:

```bash
azd env set <PARAMETER_NAME> <VALUE>
```

**Example:**

```bash
azd env set AZURE_LOCATION westus2
```
