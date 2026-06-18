// ============================================================================
// main.bicep — Deployment Router
// Description: Routes deployment to the appropriate infrastructure flavor.
//   - 'bicep'   → Vanilla Bicep modules (Docker deployment)
//   - 'avm'     → AVM-based modules (non-WAF)
//   - 'avm-waf' → AVM-based modules with WAF-aligned features
//              (monitoring, private networking, scalability, redundancy)
// ============================================================================
targetScope = 'resourceGroup'

// ============================================================================
// Routing Parameter
// ============================================================================

@allowed(['bicep', 'avm', 'avm-waf'])
@description('Required. Deployment flavor: bicep (vanilla Docker), avm (AVM non-WAF), or avm-waf (AVM WAF-aligned).')
param deploymentFlavor string

// ============================================================================
// Parameters — Core (shared across all flavors)
// ============================================================================

@minLength(3)
@maxLength(16)
@description('Optional. A unique application/solution name used as base for all resource naming.')
param solutionName string = 'cps'

@maxLength(5)
@description('Optional. A unique text suffix appended to resource names for uniqueness.')
param solutionUniqueText string = substring(uniqueString(subscription().id, resourceGroup().name, solutionName), 0, 5)

@metadata({ azd: { type: 'location' } })
@description('Required. Azure region for all services. Regions are restricted to guarantee compatibility with paired regions and replica locations for data redundancy and failover scenarios based on articles [Azure regions list](https://learn.microsoft.com/azure/reliability/regions-list) and [Azure Database for MySQL Flexible Server - Azure Regions](https://learn.microsoft.com/azure/mysql/flexible-server/overview#azure-regions).')
@allowed(['australiaeast', 'centralus', 'eastasia', 'eastus2', 'japaneast', 'northeurope', 'southeastasia', 'swedencentral', 'uksouth'])
param location string

@allowed(['australiaeast', 'eastus', 'eastus2', 'japaneast', 'southcentralus', 'southeastasia', 'swedencentral', 'uksouth', 'westeurope', 'westus', 'westus3'])
@metadata({
  azd:{
    type: 'location'
    usageName: [
      'OpenAI.GlobalStandard.gpt-5.1,300'
    ]
  }
})
@description('Required. Location for AI Foundry and model deployments.')
param azureAiServiceLocation string

// ============================================================================
// Parameters — WAF Feature Flags
// ============================================================================

@description('Optional. Tags to apply to all resources.')
param tags object = {}

@description('Optional. Enable/Disable usage telemetry for AVM modules.')
param enableTelemetry bool = true

@description('Optional. Enable monitoring for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enableMonitoring bool = false

@description('Optional. Enable private networking for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enablePrivateNetworking bool = false

@description('Optional. Enable scalability for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enableScalability bool = false

@description('Optional. Enable redundancy for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enableRedundancy bool = false

// ============================================================================
// Parameters — VM (applicable when enablePrivateNetworking = true)
// ============================================================================

@secure()
@description('Optional. The user name for the administrator account of the virtual machine. Required by Azure at provisioning time but not used for login when Entra ID is enabled.')
param vmAdminUsername string?

@secure()
@description('Optional. The password for the administrator account of the virtual machine. Auto-generated if not provided. Not used for login when Entra ID is enabled.')
param vmAdminPassword string?

@description('Optional. The size of the virtual machine. Defaults to Standard_D2s_v5.')
param vmSize string = 'Standard_D2s_v5'

// ============================================================================
// Parameters — AI Configuration
// ============================================================================

@allowed(['Standard', 'GlobalStandard'])
@description('Optional. GPT model deployment type.')
param deploymentType string = 'GlobalStandard'

@description('Optional. Name of the GPT model to deploy.')
param gptModelName string = 'gpt-5.1'

@description('Optional. Version of the GPT model to deploy.')
param gptModelVersion string = '2025-11-13'

@minValue(10)
@description('Optional. Capacity of the GPT deployment (TPM in thousands).')
param gptDeploymentCapacity int = 300

// ============================================================================
// Parameters — Compute
// ============================================================================

@description('Optional. The container registry login server/endpoint for the container images (for example, an Azure Container Registry endpoint).')
param containerRegistryEndpoint string = 'cpscontainerreg.azurecr.io'

@description('Optional. The image tag for the container images.')
param imageTag string = 'latest_v2'

// ============================================================================
// Parameters — Existing Resources
// ============================================================================

@description('Optional. Resource ID of an existing Log Analytics workspace (empty = create new).')
param existingLogAnalyticsWorkspaceId string = ''

@description('Optional. Resource ID of an existing AI Foundry project (empty = create new).')
param existingFoundryProjectResourceId string = ''

// ============================================================================
// Parameters — Identity
// ============================================================================

@allowed(['User', 'ServicePrincipal'])
@description('Optional. Principal type of the deploying user.')
param deployingUserPrincipalType string = 'User'

// ============================================================================
// Derived Variables
// ============================================================================

var isAvm = deploymentFlavor == 'avm' || deploymentFlavor == 'avm-waf'
var isBicep = deploymentFlavor == 'bicep'

// ============================================================================
// Module: AVM Deployment (non-WAF and WAF)
// Activated when deploymentFlavor = 'avm' or 'avm-waf'
// WAF features (monitoring, private networking, scalability, redundancy)
// are enabled automatically for 'avm-waf'.
// ============================================================================

module avmDeployment './avm/main.bicep' = if (isAvm) {
  name: take('module.avm.${solutionName}', 64)
  params: {
    solutionName: solutionName
    solutionUniqueText: solutionUniqueText
    location: location
    azureAiServiceLocation: azureAiServiceLocation
    gptModelName: gptModelName
    deploymentType: deploymentType
    gptModelVersion: gptModelVersion
    gptDeploymentCapacity: gptDeploymentCapacity
    existingLogAnalyticsWorkspaceId: existingLogAnalyticsWorkspaceId
    existingFoundryProjectResourceId: existingFoundryProjectResourceId
    containerRegistryEndpoint: containerRegistryEndpoint
    imageTag: imageTag
    enablePrivateNetworking: enablePrivateNetworking
    enableMonitoring: enableMonitoring
    enableRedundancy: enableRedundancy
    enableScalability: enableScalability
    enableTelemetry: enableTelemetry
    vmAdminUsername: vmAdminUsername
    vmAdminPassword: vmAdminPassword
    vmSize: vmSize
    tags: tags
  }
}

// ============================================================================
// Module: Vanilla Bicep Deployment (Docker)
// Activated when deploymentFlavor = 'bicep'
// ============================================================================

module bicepDeployment './bicep/main.bicep' = if (isBicep) {
  name: take('module.bicep.${solutionName}', 64)
  params: {
    solutionName: solutionName
    solutionUniqueText: solutionUniqueText
    location: location
    azureAiServiceLocation: azureAiServiceLocation
    gptModelName: gptModelName
    deploymentType: deploymentType
    gptModelVersion: gptModelVersion
    gptDeploymentCapacity: gptDeploymentCapacity
    existingLogAnalyticsWorkspaceId: existingLogAnalyticsWorkspaceId
    existingFoundryProjectResourceId: existingFoundryProjectResourceId
    containerRegistryEndpoint: containerRegistryEndpoint
    imageTag: imageTag
    tags: tags
  }
}

// ============================================================================
// Outputs — Coalesced from whichever flavor was deployed
// ============================================================================

@description('The name of the Container App used for Web App.')
output CONTAINER_WEB_APP_NAME string = isAvm ? avmDeployment!.outputs.CONTAINER_WEB_APP_NAME : bicepDeployment!.outputs.CONTAINER_WEB_APP_NAME

@description('The name of the Container App used for API.')
output CONTAINER_API_APP_NAME string = isAvm ? avmDeployment!.outputs.CONTAINER_API_APP_NAME : bicepDeployment!.outputs.CONTAINER_API_APP_NAME

@description('The FQDN of the Container App.')
output CONTAINER_WEB_APP_FQDN string = isAvm ? avmDeployment!.outputs.CONTAINER_WEB_APP_FQDN : bicepDeployment!.outputs.CONTAINER_WEB_APP_FQDN

@description('The FQDN of the Container App API.')
output CONTAINER_API_APP_FQDN string = isAvm ? avmDeployment!.outputs.CONTAINER_API_APP_FQDN : bicepDeployment!.outputs.CONTAINER_API_APP_FQDN

// @description('The name of the Container App used for APP.')
// output CONTAINER_APP_NAME string = isAvm ? avmDeployment!.outputs.CONTAINER_APP_NAME : bicepDeployment!.outputs.CONTAINER_APP_NAME

@description('The name of the Container App used for Workflow.')
output CONTAINER_WORKFLOW_APP_NAME string = isAvm ? avmDeployment!.outputs.CONTAINER_WORKFLOW_APP_NAME : bicepDeployment!.outputs.CONTAINER_WORKFLOW_APP_NAME

// @description('The user identity resource ID used fot the Container APP.')
// output CONTAINER_APP_USER_IDENTITY_ID string = isAvm ? avmDeployment!.outputs.CONTAINER_APP_USER_IDENTITY_ID : bicepDeployment!.outputs.CONTAINER_APP_USER_IDENTITY_ID

// @description('The user identity Principal ID used fot the Container APP.')
// output CONTAINER_APP_USER_PRINCIPAL_ID string = isAvm ? avmDeployment!.outputs.CONTAINER_APP_USER_PRINCIPAL_ID : bicepDeployment!.outputs.CONTAINER_APP_USER_PRINCIPAL_ID

// @description('The name of the Azure Container Registry.')
// output CONTAINER_REGISTRY_NAME string = isAvm ? avmDeployment!.outputs.CONTAINER_REGISTRY_NAME : bicepDeployment!.outputs.CONTAINER_REGISTRY_NAME

// @description('The login server of the Azure Container Registry.')
// output CONTAINER_REGISTRY_LOGIN_SERVER string = isAvm ? avmDeployment!.outputs.CONTAINER_REGISTRY_LOGIN_SERVER : bicepDeployment!.outputs.CONTAINER_REGISTRY_LOGIN_SERVER

@description('The name of the AI Services account that hosts both Azure OpenAI and Content Understanding GA.')
output CONTENT_UNDERSTANDING_ACCOUNT_NAME string = isAvm ? avmDeployment!.outputs.CONTENT_UNDERSTANDING_ACCOUNT_NAME : bicepDeployment!.outputs.CONTENT_UNDERSTANDING_ACCOUNT_NAME

@description('The resource group the resources were deployed into.')
output AZURE_RESOURCE_GROUP string = resourceGroup().name
