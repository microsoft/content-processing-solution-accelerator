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

@allowed([
  'bicep'
  'avm'
  'avm-waf'
])
@description('Required. Deployment flavor: bicep (vanilla Docker), avm (AVM non-WAF), or avm-waf (AVM WAF-aligned).')
param deploymentFlavor string = 'avm'

// ============================================================================
// Parameters — Core
// ============================================================================

@minLength(3)
@maxLength(20)
@description('Optional. Name of the solution to deploy.')
param solutionName string = 'cps'

@metadata({ azd: { type: 'location' } })
@description('Required. Azure region for the deployment.')
param location string

@metadata({ azd: { type: 'location' } })
@description('Required. Azure region for Azure AI services resources.')
param azureAiServiceLocation string

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
param gptDeploymentCapacity int = 300

// ============================================================================
// Parameters — Existing Resources
// ============================================================================

@description('Optional. Resource ID of an existing Log Analytics workspace. Leave empty to create a new one.')
param existingLogAnalyticsWorkspaceId string = ''

@description('Optional. Resource ID of an existing AI Foundry project. Leave empty to create a new one.')
param existingFoundryProjectResourceId string = ''

// ============================================================================
// Parameters — Compute
// ============================================================================

@description('Optional. Container registry endpoint. Leave empty to use the deployed ACR login server.')
param containerRegistryEndpoint string = ''

@description('Optional. Image tag for all container images.')
param imageTag string = 'latest_v2'

// ============================================================================
// Parameters — Feature Flags
// ============================================================================

@description('Optional. Enable private networking.')
param enablePrivateNetworking bool = false

@description('Optional. Enable monitoring resources.')
param enableMonitoring bool = false

@description('Optional. Enable redundancy for supported resources.')
param enableRedundancy bool = false

@description('Optional. Enable higher scale defaults for supported resources.')
param enableScalability bool = false

@description('Optional. Enable AVM telemetry.')
param enableTelemetry bool = true

@description('Optional. Enable purge protection for App Configuration.')
param enablePurgeProtection bool = false

// ============================================================================
// Parameters — WAF (AVM-WAF only)
// ============================================================================

@description('Optional. VM admin username for WAF jumpbox (avm-waf only).')
param vmAdminUsername string = ''

@secure()
@description('Optional. VM admin password for WAF jumpbox (avm-waf only).')
param vmAdminPassword string = ''

@description('Optional. VM size for WAF jumpbox (avm-waf only).')
param vmSize string = ''

// ============================================================================
// Parameters — Tags
// ============================================================================

@description('Optional. Tags to be applied to resources.')
param tags object = {
  app: 'Content Processing Solution Accelerator'
  location: resourceGroup().location
}

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
// Module: AVM Deployment
// ============================================================================

module avmDeployment './avm/main.bicep' = if (isAvm) {
  name: take('module.avm.${solutionName}', 64)
  params: {
    solutionName: solutionName
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

// ============================================================================
// Module: Vanilla Bicep Deployment
// ============================================================================

module bicepDeployment './bicep/main.bicep' = if (isBicep) {
  name: take('module.bicep.${solutionName}', 64)
  params: {
    solutionName: solutionName
    location: location
    azureAiServiceLocation: azureAiServiceLocation
    gptModelName: gptModelName
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
// Outputs — Coalesced from whichever flavor was deployed
// ============================================================================

output SOLUTION_NAME string = isAvm ? avmDeployment!.outputs.SOLUTION_NAME : bicepDeployment!.outputs.SOLUTION_NAME
output CONTAINER_WEB_APP_NAME string = isAvm ? avmDeployment!.outputs.CONTAINER_WEB_APP_NAME : bicepDeployment!.outputs.CONTAINER_WEB_APP_NAME
output CONTAINER_API_APP_NAME string = isAvm ? avmDeployment!.outputs.CONTAINER_API_APP_NAME : bicepDeployment!.outputs.CONTAINER_API_APP_NAME
output CONTAINER_WEB_APP_FQDN string = isAvm ? avmDeployment!.outputs.CONTAINER_WEB_APP_FQDN : bicepDeployment!.outputs.CONTAINER_WEB_APP_FQDN
output CONTAINER_API_APP_FQDN string = isAvm ? avmDeployment!.outputs.CONTAINER_API_APP_FQDN : bicepDeployment!.outputs.CONTAINER_API_APP_FQDN
output CONTAINER_APP_NAME string = isAvm ? avmDeployment!.outputs.CONTAINER_APP_NAME : bicepDeployment!.outputs.CONTAINER_APP_NAME
output CONTAINER_WORKFLOW_APP_NAME string = isAvm ? avmDeployment!.outputs.CONTAINER_WORKFLOW_APP_NAME : bicepDeployment!.outputs.CONTAINER_WORKFLOW_APP_NAME
output CONTAINER_APP_USER_IDENTITY_ID string = isAvm ? avmDeployment!.outputs.CONTAINER_APP_USER_IDENTITY_ID : bicepDeployment!.outputs.CONTAINER_APP_USER_IDENTITY_ID
output CONTAINER_APP_USER_PRINCIPAL_ID string = isAvm ? avmDeployment!.outputs.CONTAINER_APP_USER_PRINCIPAL_ID : bicepDeployment!.outputs.CONTAINER_APP_USER_PRINCIPAL_ID
output CONTAINER_REGISTRY_NAME string = isAvm ? avmDeployment!.outputs.CONTAINER_REGISTRY_NAME : bicepDeployment!.outputs.CONTAINER_REGISTRY_NAME
output CONTAINER_REGISTRY_LOGIN_SERVER string = isAvm ? avmDeployment!.outputs.CONTAINER_REGISTRY_LOGIN_SERVER : bicepDeployment!.outputs.CONTAINER_REGISTRY_LOGIN_SERVER
output CONTENT_UNDERSTANDING_ACCOUNT_NAME string = isAvm ? avmDeployment!.outputs.CONTENT_UNDERSTANDING_ACCOUNT_NAME : bicepDeployment!.outputs.CONTENT_UNDERSTANDING_ACCOUNT_NAME
output AZURE_RESOURCE_GROUP string = isAvm ? avmDeployment!.outputs.AZURE_RESOURCE_GROUP : bicepDeployment!.outputs.AZURE_RESOURCE_GROUP
