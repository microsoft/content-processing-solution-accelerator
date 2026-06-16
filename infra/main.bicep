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
param deploymentFlavor string = 'avm'

// ============================================================================
// Parameters — Core (shared across all flavors)
// ============================================================================

@minLength(3)
@maxLength(20)
@description('Optional. Name of the solution to deploy.')
param solutionName string = 'cps'

@maxLength(5)
@description('Optional. A unique text suffix appended to resource names for uniqueness.')
param solutionUniqueText string = substring(uniqueString(subscription().id, resourceGroup().name, solutionName), 0, 5)

@description('Required. Azure region for the deployment.')
param location string = resourceGroup().location

@metadata({ azd: { type: 'location' } })
@description('Required. Azure region for Azure AI services resources.')
param azureAiServiceLocation string

@description('Optional. Secondary Azure region for redundancy scenarios.')
param secondaryLocation string = ''

// ============================================================================
// Parameters — AI Configuration
// ============================================================================

@description('Optional. Name of the GPT model deployment.')
param gptModelName string = 'gpt-5.1'

@allowed([
  'Standard'
  'GlobalStandard'
])
@description('Optional. Type of GPT deployment: Standard | GlobalStandard.')
param deploymentType string = 'GlobalStandard'

@description('Optional. Version of the GPT model.')
param gptModelVersion string = '2025-11-13'

@description('Optional. Capacity (TPM) for the GPT deployment.')
param gptDeploymentCapacity int = 50

@description('Optional. Azure OpenAI API version.')
param azureOpenaiAPIVersion string = '2025-01-01-preview'

@description('Optional. Capacity for the embedding model deployment.')
param embeddingDeploymentCapacity int = 80

@description('Optional. Location for Azure AI Search service. Leave empty to use primary location.')
param searchServiceLocation string = ''

// ============================================================================
// Parameters — Compute
// ============================================================================

@description('Optional. Container registry endpoint. Leave empty to use the deployed ACR login server.')
param containerRegistryEndpoint string = 'cpscontainerreg.azurecr.io'

@description('Optional. Name of the Azure Container Registry. Leave empty to create a new one.')
param containerRegistryName string = ''

@allowed(['python', 'dotnet'])
@description('Optional. Backend runtime stack.')
param backendRuntimeStack string = 'python'

@description('Optional. Image tag for all container images.')
param imageTag string = 'latest_v2'

// ============================================================================
// Parameters — Feature Flags
// ============================================================================

@description('Optional. Enable purge protection for App Configuration.')
param enablePurgeProtection bool = false

@description('Optional. Enable user access token forwarding.')
param useUserAccessToken bool = false

// ============================================================================
// Parameters — Existing Resources
// ============================================================================

@description('Optional. Resource ID of an existing Log Analytics workspace. Leave empty to create a new one.')
param existingLogAnalyticsWorkspaceId string = ''

@description('Optional. Resource ID of an existing AI Foundry project. Leave empty to create a new one.')
param existingFoundryProjectResourceId string = ''

@allowed(['User', 'ServicePrincipal'])
@description('Optional. Principal type of the deploying user.')
param deployingUserPrincipalType string = 'User'

// ============================================================================
// Parameters — Fabric
// ============================================================================

@description('Optional. Existing Fabric Workspace ID. Leave empty to skip.')
param fabricWorkspaceId string = ''

@description('Optional. Name of an existing Fabric capacity. Leave empty to skip.')
param azureFabricCapacityName string = ''

@allowed(['F2', 'F4', 'F8', 'F16', 'F32', 'F64', 'F128', 'F256', 'F512', 'F1024', 'F2048'])
@description('Optional. SKU of the Fabric capacity.')
param fabricCapacitySku string = 'F2'

@description('Optional. Fabric Capacity admin members.')
param fabricAdminMembers array = []

// ============================================================================
// Parameters — AVM-specific (ignored when deploymentFlavor = 'bicep')
// ============================================================================

@description('Optional. Tags to apply to all resources.')
param tags object = {}

@description('Optional. Enable/Disable usage telemetry for AVM modules.')
param enableTelemetry bool = true

@description('Optional. Enable monitoring resources.')
param enableMonitoring bool = false

@description('Optional. Enable private networking.')
param enablePrivateNetworking bool = false

@description('Optional. Enable higher scale defaults for supported resources.')
param enableScalability bool = false

@description('Optional. Enable redundancy for supported resources.')
param enableRedundancy bool = false

@secure()
@description('Optional. VM admin username for WAF jumpbox (avm-waf only).')
param vmAdminUsername string?

@secure()
@description('Optional. VM admin password for WAF jumpbox (avm-waf only).')
param vmAdminPassword string?

@description('Optional. VM size for WAF jumpbox (avm-waf only).')
param vmSize string = 'Standard_D2s_v5'

// ============================================================================
// Derived Variables
// ============================================================================

var isAvm = deploymentFlavor == 'avm' || deploymentFlavor == 'avm-waf'
var isBicep = deploymentFlavor == 'bicep'
var useWafDefaults = deploymentFlavor == 'avm-waf'

var effectiveEnablePrivateNetworking = useWafDefaults ? true : enablePrivateNetworking
var effectiveEnableMonitoring = useWafDefaults ? true : enableMonitoring
var effectiveEnableRedundancy = useWafDefaults ? true : enableRedundancy
var effectiveEnableScalability = useWafDefaults ? true : enableScalability

// ============================================================================
// Module calls
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
    enablePrivateNetworking: effectiveEnablePrivateNetworking
    enableMonitoring: effectiveEnableMonitoring
    enableRedundancy: effectiveEnableRedundancy
    enableScalability: effectiveEnableScalability
    enableTelemetry: enableTelemetry
    enablePurgeProtection: enablePurgeProtection
    vmAdminUsername: vmAdminUsername
    vmAdminPassword: vmAdminPassword
    vmSize: vmSize
    tags: tags
  }
}

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
    enablePrivateNetworking: effectiveEnablePrivateNetworking
    enableMonitoring: effectiveEnableMonitoring
    enableRedundancy: effectiveEnableRedundancy
    enableScalability: effectiveEnableScalability
    enableTelemetry: enableTelemetry
    enablePurgeProtection: enablePurgeProtection
    tags: tags
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('Solution name output from the selected deployment flavor.')
output SOLUTION_NAME string = isAvm ? avmDeployment!.outputs.SOLUTION_NAME : bicepDeployment!.outputs.SOLUTION_NAME

@description('Container web app name from the selected deployment flavor.')
output CONTAINER_WEB_APP_NAME string = isAvm ? avmDeployment!.outputs.CONTAINER_WEB_APP_NAME : bicepDeployment!.outputs.CONTAINER_WEB_APP_NAME

@description('Container API app name from the selected deployment flavor.')
output CONTAINER_API_APP_NAME string = isAvm ? avmDeployment!.outputs.CONTAINER_API_APP_NAME : bicepDeployment!.outputs.CONTAINER_API_APP_NAME

@description('Container web app FQDN from the selected deployment flavor.')
output CONTAINER_WEB_APP_FQDN string = isAvm ? avmDeployment!.outputs.CONTAINER_WEB_APP_FQDN : bicepDeployment!.outputs.CONTAINER_WEB_APP_FQDN

@description('Container API app FQDN from the selected deployment flavor.')
output CONTAINER_API_APP_FQDN string = isAvm ? avmDeployment!.outputs.CONTAINER_API_APP_FQDN : bicepDeployment!.outputs.CONTAINER_API_APP_FQDN

@description('Container app name from the selected deployment flavor.')
output CONTAINER_APP_NAME string = isAvm ? avmDeployment!.outputs.CONTAINER_APP_NAME : bicepDeployment!.outputs.CONTAINER_APP_NAME

@description('Container workflow app name from the selected deployment flavor.')
output CONTAINER_WORKFLOW_APP_NAME string = isAvm ? avmDeployment!.outputs.CONTAINER_WORKFLOW_APP_NAME : bicepDeployment!.outputs.CONTAINER_WORKFLOW_APP_NAME

@description('Container app user-assigned identity resource ID from the selected deployment flavor.')
output CONTAINER_APP_USER_IDENTITY_ID string = isAvm ? avmDeployment!.outputs.CONTAINER_APP_USER_IDENTITY_ID : bicepDeployment!.outputs.CONTAINER_APP_USER_IDENTITY_ID

@description('Container app user-assigned identity principal ID from the selected deployment flavor.')
output CONTAINER_APP_USER_PRINCIPAL_ID string = isAvm ? avmDeployment!.outputs.CONTAINER_APP_USER_PRINCIPAL_ID : bicepDeployment!.outputs.CONTAINER_APP_USER_PRINCIPAL_ID

@description('Container registry name from the selected deployment flavor.')
output CONTAINER_REGISTRY_NAME string = isAvm ? avmDeployment!.outputs.CONTAINER_REGISTRY_NAME : bicepDeployment!.outputs.CONTAINER_REGISTRY_NAME

@description('Container registry login server from the selected deployment flavor.')
output CONTAINER_REGISTRY_LOGIN_SERVER string = isAvm ? avmDeployment!.outputs.CONTAINER_REGISTRY_LOGIN_SERVER : bicepDeployment!.outputs.CONTAINER_REGISTRY_LOGIN_SERVER

@description('Content Understanding account name from the selected deployment flavor.')
output CONTENT_UNDERSTANDING_ACCOUNT_NAME string = isAvm ? avmDeployment!.outputs.CONTENT_UNDERSTANDING_ACCOUNT_NAME : bicepDeployment!.outputs.CONTENT_UNDERSTANDING_ACCOUNT_NAME

@description('Azure resource group output from the selected deployment flavor.')
output AZURE_RESOURCE_GROUP string = isAvm ? avmDeployment!.outputs.AZURE_RESOURCE_GROUP : bicepDeployment!.outputs.AZURE_RESOURCE_GROUP
