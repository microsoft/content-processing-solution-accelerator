# Infrastructure — Content Processing Solution Accelerator

This folder contains the Bicep/ARM infrastructure-as-code for the Content Processing Solution Accelerator.

## Deployment Flavors

| Flavor | Description |
|--------|-------------|
| `avm` | Azure Verified Modules — production-grade, non-WAF |
| `avm-waf` | AVM with WAF-aligned features (monitoring, private networking, scalability, redundancy) |
| `bicep` | Vanilla Bicep — direct ARM resource definitions |

## Folder Structure

```
infra/
├── main.bicep                  ← Deployment router (selects flavor)
├── main.json                   ← Compiled ARM template (used by CI/CD)
├── main.parameters.json        ← Standard deployment parameters
├── main.waf.parameters.json    ← WAF deployment parameters
├── main_custom.bicep           ← Oryx source-code build variant (azd deploy)
├── avm/
│   ├── main.bicep              ← AVM orchestrator
│   ├── main.json               ← Compiled ARM
│   └── modules/
│       ├── ai/                 ← AI Services, AI Search
│       ├── compute/            ← Container Registry
│       ├── identity/           ← Managed Identity
│       ├── monitoring/         ← Log Analytics
│       └── networking/         ← VNet, Bastion, Private DNS
├── bicep/
│   ├── main.bicep              ← Vanilla Bicep orchestrator
│   ├── main.json               ← Compiled ARM
│   └── modules/
│       ├── ai/                 ← AI Services, Project, Model, Search
│       ├── compute/            ← Container Apps, Environment, Registry
│       ├── data/               ← Storage, Cosmos DB, App Configuration
│       ├── identity/           ← Managed Identity
│       └── monitoring/         ← Log Analytics, App Insights
├── scripts/
│   ├── build/                  ← Build-time scripts
│   ├── post-provision/         ← Post-provisioning hooks
│   ├── pre-provision/          ← Pre-provisioning hooks
│   └── utilities/              ← Utility scripts
└── azure.yaml                  ← azd infrastructure config
```

## Usage

### Deploy with Azure Developer CLI (azd)

```bash
# Standard deployment (AVM flavor)
azd up

# WAF deployment
azd up --environment-values DEPLOYMENT_FLAVOR=avm-waf
```

### Deploy with Azure CLI

```bash
az deployment group create \
  --resource-group <rg-name> \
  --template-file infra/main.json \
  --parameters infra/main.parameters.json
```

### Build ARM template from Bicep

```bash
az bicep build --file infra/main.bicep --outfile infra/main.json
```

## Parameters

| Parameter | Required | Description |
|-----------|:--------:|-------------|
| `deploymentFlavor` | No | `avm` (default), `bicep`, or `avm-waf` |
| `solutionName` | No | Solution name (3-20 chars), default: `cps` |
| `location` | Yes | Azure region for resources |
| `azureAiServiceLocation` | Yes | Azure region for AI Services |
| `gptModelName` | No | GPT model name, default: `gpt-5.1` |
| `deploymentType` | No | `GlobalStandard` (default) or `Standard` |
| `gptModelVersion` | No | Model version, default: `2025-11-13` |
| `gptDeploymentCapacity` | No | TPM capacity, default: `300` |
| `imageTag` | No | Container image tag, default: `latest_v2` |
| `enablePrivateNetworking` | No | Enable VNet/private endpoints |
| `enableMonitoring` | No | Enable Log Analytics + App Insights |
| `enableRedundancy` | No | Enable zone redundancy |
| `enableScalability` | No | Enable higher scale defaults |
