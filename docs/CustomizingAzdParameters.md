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
| `AZURE_ENV_MODEL_NAME`                 | string  | `gpt-4.1`                  | Specifies the GPT model name (allowed values: `gpt-4.1`).       
| `AZURE_ENV_MODEL_VERSION`                 | string  | `2025-04-14`                  | Specifies the GPT model version (allowed values: `2025-04-14`).                       |
| `AZURE_ENV_MODEL_CAPACITY`             | integer | `30`                        | Sets the model capacity (choose based on your subscription's available GPT capacity). |
| `USE_LOCAL_BUILD`                      | boolean | `false`                     | Indicates whether to use a local container build for deployment.                      |
| `AZURE_ENV_IMAGETAG`                      | boolean | `latest`                     | Set the Image tag Like (allowed values: latest, dev, hotfix)                       |
| `AZURE_ENV_LOG_ANALYTICS_WORKSPACE_ID` | string  | `<Existing Workspace Id>` | Reuses an existing Log Analytics Workspace instead of provisioning a new one.         |


## How to Set a Parameter

To customize any of the above values, run the following command **before** `azd up`:

```bash
azd env set <PARAMETER_NAME> <VALUE>
```

**Example:**

```bash
azd env set AZURE_LOCATION westus2
```