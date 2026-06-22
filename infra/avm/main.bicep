// ============================================================================
// main.bicep — Orchestrator
// Description: Pure orchestrator for Content Processing solution. Calls modules to deploy resources.
//              All resource names are derived from params — no hardcoded names.
//              This file only calls modules; no inline resource definitions.
//              Supports WAF-aligned deployment via feature flags.
// ============================================================================
targetScope = 'resourceGroup'

// ============================================================================
// Parameters — Core
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
// Variables
// ============================================================================

var solutionSuffix = toLower(trim(replace(replace(replace(replace(replace(replace('${solutionName}${solutionUniqueText}', '-', ''), '_', ''), '.', ''), '/', ''), ' ', ''), '*', '')))
var deployerInfo = deployer()
var deployingUserPrincipalId = deployerInfo.objectId
var createdBy = contains(deployerInfo, 'userPrincipalName') ? split(deployerInfo.userPrincipalName, '@')[0] : deployerInfo.objectId
var useExistingAIProject = !empty(existingFoundryProjectResourceId)

// ========== Tags: merge caller-supplied tags with standard metadata (matching old infra) ========== //
var existingTags = resourceGroup().tags ?? {}
var resourceTags = union(existingTags, tags, {
  TemplateName: 'Content Processing Solution Accelerator'
  CreatedBy: createdBy
  DeploymentName: deployment().name
  Type: enablePrivateNetworking ? 'WAF' : 'Non-WAF'
})

// ========== WAF: Region pairs for redundancy (Log Analytics replication) ========== //
var replicaRegionPairs = {
  australiaeast: 'australiasoutheast'
  centralus: 'westus'
  eastasia: 'japaneast'
  eastus: 'centralus'
  eastus2: 'centralus'
  japaneast: 'eastasia'
  northeurope: 'westeurope'
  southeastasia: 'eastasia'
  swedencentral: 'northeurope'
  uksouth: 'westeurope'
  westeurope: 'northeurope'
}
var replicaLocation = replicaRegionPairs[location]

// ========== WAF: Diagnostic settings helper — reused across modules ========== //
var monitoringDiagnosticSettings = enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : []

// ========== WAF: Private DNS zones for private endpoints ========== //
var privateDnsZones = [
  'privatelink.cognitiveservices.azure.com'
  'privatelink.openai.azure.com'
  'privatelink.services.ai.azure.com'
  'privatelink.contentunderstanding.ai.azure.com'
  'privatelink.blob.${environment().suffixes.storage}'
  'privatelink.queue.${environment().suffixes.storage}'
  'privatelink.mongo.cosmos.azure.com'
  'privatelink.azconfig.io'
  'privatelink.azurecr.io'
]
var dnsZoneIndex = {
  cognitiveServices: 0
  openAI: 1
  aiServices: 2
  contentUnderstanding: 3
  storageBlob: 4
  storageQueue: 5
  cosmosDB: 6
  appConfig: 7
  containerRegistry: 8
}

// ========== Resource naming (parameterized — no abbreviations.json dependency) ========== //
// Resource names for generic modules are now derived inside each module from solutionName/solutionSuffix.

// ========== Model deployments configuration ========== //
var aiModelDeployments = [
  {
    name: gptModelName
    model: gptModelName
    sku: { name: deploymentType, capacity: gptDeploymentCapacity }
    version: gptModelVersion
    raiPolicyName: 'Microsoft.Default'
  }
]

// ============================================================================
// Resource Group Tags (matching old infra)
// ============================================================================

resource resourceGroupTags 'Microsoft.Resources/tags@2024-11-01' = {
  name: 'default'
  properties: {
    tags: resourceTags
  }
}

// ============================================================================
// Module: Monitoring
// ============================================================================

var useExistingLogAnalytics = !empty(existingLogAnalyticsWorkspaceId)

// Existing workspace reference (for cross-subscription support)
resource existingLogAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2025-07-01' existing = if (useExistingLogAnalytics) {
  name: split(existingLogAnalyticsWorkspaceId, '/')[8]
  scope: resourceGroup(split(existingLogAnalyticsWorkspaceId, '/')[2], split(existingLogAnalyticsWorkspaceId, '/')[4])
}

 //  ========== Log Analytics Workspace module ========== //
module log_analytics './modules/monitoring/log-analytics.bicep' = if (enableMonitoring && !useExistingLogAnalytics) {
  name: take('module.log-analytics.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    retentionInDays: 365
    publicNetworkAccessForIngestion: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    publicNetworkAccessForQuery: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    enableReplication: enableRedundancy
    replicationLocation: enableRedundancy ? replicaLocation : ''
    dailyQuotaGb: enableRedundancy ? '150' : ''
    dataSources: enablePrivateNetworking ? [
      {
        tags: tags
        eventLogName: 'Application'
        eventTypes: [{ eventType: 'Error' }, { eventType: 'Warning' }, { eventType: 'Information' }]
        kind: 'WindowsEvent'
        name: 'applicationEvent'
      }
      {
        counterName: '% Processor Time'
        instanceName: '*'
        intervalSeconds: 60
        kind: 'WindowsPerformanceCounter'
        name: 'windowsPerfCounter1'
        objectName: 'Processor'
      }
      {
        kind: 'IISLogs'
        name: 'sampleIISLog1'
        state: 'OnPremiseEnabled'
      }
    ] : []
  }
}

// ========== Resolve workspace resource ID and name — existing or new ========== //
var logAnalyticsWorkspaceResourceId = useExistingLogAnalytics
  ? existingLogAnalyticsWorkspace.id
  : (enableMonitoring ? log_analytics!.outputs.resourceId : '')
var logAnalyticsWorkspaceName = useExistingLogAnalytics
  ? split(existingLogAnalyticsWorkspaceId, '/')[8]
  : (enableMonitoring ? log_analytics!.outputs.name : '')

// ========== App Insights module ========== //
module app_insights './modules/monitoring/app-insights.bicep' = if (enableMonitoring) {
  name: take('module.app-insights.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: azureAiServiceLocation
    tags: tags
    enableTelemetry: enableTelemetry
    workspaceResourceId: logAnalyticsWorkspaceResourceId
    retentionInDays: 365
    disableIpMasking: false
  }
}

// ============================================================================
// Module: Networking (WAF — conditional on enablePrivateNetworking)
// ============================================================================

module virtualNetwork './modules/networking/virtual-network.bicep' = if (enablePrivateNetworking) {
  name: take('module.virtual-network.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
        location: location
    tags: tags
    enableTelemetry: enableTelemetry
    addressPrefixes: ['10.0.0.0/8']
    logAnalyticsWorkspaceId: logAnalyticsWorkspaceResourceId
    resourceSuffix: solutionSuffix
  }
}

// ========== Bastion Host — secure access to jumpbox VM ========== //
module bastionHost './modules/networking/bastion-host.bicep' = if (enablePrivateNetworking) {
  name: take('module.bastion-host.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    virtualNetworkResourceId: virtualNetwork!.outputs.resourceId
    publicIPDiagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : null
    diagnosticSettings: enableMonitoring
      ? [
          {
            name: 'bastionDiagnostics'
            workspaceResourceId: logAnalyticsWorkspaceResourceId
            logCategoriesAndGroups: [
              {
                categoryGroup: 'allLogs'
                enabled: true
              }
            ]
          }
        ]
      : null
  }
}

// ========== WAF: Maintenance Configuration for VM patching ========== //
module maintenanceConfiguration './modules/compute/maintenance-configuration.bicep' = if (enablePrivateNetworking) {
  name: take('module.maintenance-configuration.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
  }
}

// ========== WAF: Data Collection Rules for VM monitoring ========== //
var dataCollectionRulesLocation = useExistingLogAnalytics
  ? existingLogAnalyticsWorkspace!.location
  : (enableMonitoring ? log_analytics!.outputs.location : location)
module windowsVmDataCollectionRules './modules/monitoring/data-collection-rule.bicep' = if (enablePrivateNetworking && enableMonitoring) {
  name: take('module.data-collection-rule.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: dataCollectionRulesLocation
    tags: tags
    enableTelemetry: enableTelemetry
    logAnalyticsWorkspaceResourceId: logAnalyticsWorkspaceResourceId
  }
}

// ========== WAF: Proximity Placement Group for VM ========== //
var virtualMachineAvailabilityZone = 1
module proximityPlacementGroup './modules/compute/proximity-placement-group.bicep' = if (enablePrivateNetworking) {
  name: take('module.proximity-placement-group.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    availabilityZone: virtualMachineAvailabilityZone
    vmSizes: [vmSize]
  }
}

// ========== Jumpbox VM — administration access when private networking is enabled ========== //
// ========== Login is via Microsoft Entra ID through Azure Bastion (not local credentials) ========== //
module virtualMachine './modules/compute/virtual-machine.bicep' = if (enablePrivateNetworking) {
  name: take('module.virtual-machine.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    vmSize: vmSize
    availabilityZone: virtualMachineAvailabilityZone
    adminUsername: vmAdminUsername ?? 'testvmuser'
    adminPassword: vmAdminPassword ?? 'Vm!${uniqueString(subscription().subscriptionId, solutionName)}${guid(subscription().subscriptionId, solutionName, 'vm-admin-password')}'
    subnetResourceId: virtualNetwork!.outputs.administrationSubnetResourceId
    deployingUserPrincipalId: deployingUserPrincipalId
    deployingUserPrincipalType: deployingUserPrincipalType
    roleAssignments: [
      {
        roleDefinitionIdOrName: '1c0163c0-47e6-4577-8991-ea5c82e286e4' // Virtual Machine Administrator Login
        principalId: deployingUserPrincipalId
        principalType: deployingUserPrincipalType
      }
    ]
    diagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : null
    maintenanceConfigurationResourceId: maintenanceConfiguration!.outputs.resourceId
    proximityPlacementGroupResourceId: proximityPlacementGroup!.outputs.resourceId
    extensionMonitoringAgentConfig: enableMonitoring ? {
      dataCollectionRuleAssociations: [
        {
          dataCollectionRuleResourceId: windowsVmDataCollectionRules!.outputs.resourceId
          name: 'send-${logAnalyticsWorkspaceName}'
        }
      ]
      enabled: true
      tags: tags
    } : null
  }
}

// ========== Private DNS Zones — one per service, linked to VNet ========== //
@batchSize(5)
module privateDnsZoneDeployments './modules/networking/private-dns-zone.bicep' = [
  for (zone, i) in privateDnsZones: if (enablePrivateNetworking) {
    name: take('module.private-dns-zone.${split(zone, '.')[1]}.${solutionName}', 64)
    params: {
      name: zone
      tags: tags
      enableTelemetry: enableTelemetry
      virtualNetworkLinks: [
        {
          name: take('vnetlink-${virtualNetwork!.outputs.name}-${split(zone, '.')[1]}', 80)
          virtualNetworkResourceId: virtualNetwork!.outputs.resourceId
        }
      ]
    }
  }
]

// // ========== Storage Account ========== //
module storage_account './modules/data/storage-account.bicep' = {
  name: take('module.storage-account.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableHierarchicalNamespace: true
    enableTelemetry: enableTelemetry
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    diagnosticSettings: monitoringDiagnosticSettings
    privateEndpoints: (enablePrivateNetworking)
      ? [
          {
            name: 'pep-blob-${solutionSuffix}'
            customNetworkInterfaceName: 'nic-blob-${solutionSuffix}'
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                {
                  name: 'storage-dns-zone-group-blob'
                  privateDnsZoneResourceId: privateDnsZoneDeployments[dnsZoneIndex.storageBlob]!.outputs.resourceId
                }
              ]
            }
            subnetResourceId: virtualNetwork!.outputs.backendSubnetResourceId // Use the backend subnet
            service: 'blob'
          }
          {
            name: 'pep-queue-${solutionSuffix}'
            customNetworkInterfaceName: 'nic-queue-${solutionSuffix}'
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                {
                  name: 'storage-dns-zone-group-queue'
                  privateDnsZoneResourceId: privateDnsZoneDeployments[dnsZoneIndex.storageQueue]!.outputs.resourceId
                }
              ]
            }
            subnetResourceId: virtualNetwork!.outputs.backendSubnetResourceId // Use the backend subnet
            service: 'queue'
          }
        ]
      : []
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: enablePrivateNetworking ? 'Deny' : 'Allow'
      virtualNetworkRules: []
    }
  }
}

// ========== Cosmos DB module ========== //
module cosmosDB './modules/data/cosmos-db-mongo.bicep' = {
  name: take('module.cosmos-db-mongo.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    zoneRedundant: enableRedundancy
    enableAutomaticFailover: enableRedundancy
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    privateEndpoints: (enablePrivateNetworking)
      ? [
          {
            name: 'pep-cosmosdb-${solutionSuffix}'
            customNetworkInterfaceName: 'nic-cosmosdb-${solutionSuffix}'
            privateEndpointResourceId: virtualNetwork!.outputs.resourceId
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                {
                  name: 'cosmosdb-dns-zone-group'
                  privateDnsZoneResourceId: privateDnsZoneDeployments[dnsZoneIndex.cosmosDB]!.outputs.resourceId
                }
              ]
            }
            service: 'MongoDB'
            subnetResourceId: virtualNetwork!.outputs.backendSubnetResourceId // Use the backend subnet
          }
        ]
      : []
  }
}

// ============================================================================
// Module: AI Services (conditional — skip if using existing project)
// ============================================================================

// ========== Existing AI Foundry reference (for cross-subscription support when using existing project) ========== //
var aiFoundryResourceGroupName = useExistingAIProject
  ? split(existingFoundryProjectResourceId, '/')[4]
  : resourceGroup().name
var aiFoundrySubscriptionId = useExistingAIProject
  ? split(existingFoundryProjectResourceId, '/')[2]
  : subscription().subscriptionId
var aiFoundryResourceName = useExistingAIProject
  ? split(existingFoundryProjectResourceId, '/')[8]
  : ai_foundry_project!.outputs.name
var aiProjectResourceName = useExistingAIProject
  ? (length(split(existingFoundryProjectResourceId, '/')) > 10 ? split(existingFoundryProjectResourceId, '/')[10] : '')
  : ai_foundry_project!.outputs.projectName

// ========== Reference existing AI Foundry project (identity only) ========== //
module existing_project_setup './modules/ai/existing-project-setup.bicep' = if (useExistingAIProject) {
  name: take('module.existing-project-setup.${solutionName}', 64)
  scope: resourceGroup(aiFoundrySubscriptionId, aiFoundryResourceGroupName)
  params: {
    name: aiFoundryResourceName
    projectName: aiProjectResourceName
  }
}

// ========== Deploy new AI Services account + AI Foundry project (no connections, no deployments) ========== //
module ai_foundry_project './modules/ai/ai-foundry-project.bicep' = if (!useExistingAIProject) {
  name: take('module.ai-foundry-project.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: azureAiServiceLocation
    tags: tags
    enableTelemetry: enableTelemetry
    publicNetworkAccess: enableMonitoring ? 'Disabled' : 'Enabled'
    diagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : null
    roleAssignments: [
      {
        roleDefinitionIdOrName: 'a97b65f3-24c7-4388-baec-2e87135dc908' // Cognitive Services User
        principalId: deployingUserPrincipalId
        principalType: deployingUserPrincipalType
      }
      {
        roleDefinitionIdOrName: '53ca6127-db72-4b80-b1b0-d745d6d5456d' // Foundry User
        principalId: deployingUserPrincipalId
        principalType: deployingUserPrincipalType
      }
    ]
  }
}

// ========== Model deployments (single loop for both existing and new paths) ========== //
@batchSize(1)
module model_deployments './modules/ai/ai-foundry-model-deployment.bicep' = [for (deployment, i) in aiModelDeployments: {
  name: take('module.model-deployment-${i}.${solutionName}', 64)
  scope: resourceGroup(aiFoundrySubscriptionId, aiFoundryResourceGroupName)
  params: {
    aiServicesAccountName: aiFoundryResourceName
    deploymentName: deployment.name
    modelName: deployment.model
    modelVersion: deployment.version
    raiPolicyName: deployment.raiPolicyName
    skuName: deployment.sku.name
    skuCapacity: deployment.sku.capacity
  }
}]

// ========== Separate PE for AI Foundry to avoid AccountProvisioningStateInvalid race condition ========== //
module aifoundry_private_endpoint './modules/networking/private-endpoint.bicep' = if (!useExistingAIProject && enablePrivateNetworking) {
  name: take('module.pe-ai-foundry.${solutionName}', 64)
  dependsOn: [model_deployments,privateDnsZoneDeployments]
  params: {
    name: 'pep-aif-${solutionSuffix}'
    location: location
    tags: tags
    subnetResourceId: virtualNetwork!.outputs.backendSubnetResourceId
    customNetworkInterfaceName: 'nic-aif-${solutionSuffix}'
    privateLinkServiceConnections: [
      {
        name: 'pep-aif-${solutionSuffix}-connection'
        properties: {
          privateLinkServiceId: ai_foundry_project!.outputs.resourceId
          groupIds: ['account']
        }
      }
    ]
    privateDnsZoneGroup: {
      privateDnsZoneGroupConfigs: [
        {
          name: 'ai-services-dns-zone-cognitiveservices'
          privateDnsZoneResourceId: privateDnsZoneDeployments[dnsZoneIndex.cognitiveServices]!.outputs.resourceId
        }
        {
          name: 'ai-services-dns-zone-openai'
          privateDnsZoneResourceId: privateDnsZoneDeployments[dnsZoneIndex.openAI]!.outputs.resourceId
        }
        {
          name: 'ai-services-dns-zone-aiservices'
          privateDnsZoneResourceId: privateDnsZoneDeployments[dnsZoneIndex.aiServices]!.outputs.resourceId
        }
        {
          name: 'ai-services-dns-zone-contentunderstanding'
          privateDnsZoneResourceId: privateDnsZoneDeployments[dnsZoneIndex.contentUnderstanding]!.outputs.resourceId
        }
      ]
    }
  }
}

// ========== Container Registry ========== //
module containerRegistry './modules/compute/container-registry.bicep' = {
  name: take('module.container-registry.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    sku: enableRedundancy || enablePrivateNetworking ? 'Premium' : 'Standard'
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    tags: tags
    enableTelemetry: enableTelemetry
    privateEndpoints: (enablePrivateNetworking)
      ? [
          {
            name: 'pep-containerreg-${solutionSuffix}'
            customNetworkInterfaceName: 'nic-containerreg-${solutionSuffix}'
            privateEndpointResourceId: virtualNetwork!.outputs.resourceId
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                {
                  name: 'containerreg-dns-zone-group'
                  privateDnsZoneResourceId: privateDnsZoneDeployments[dnsZoneIndex.containerRegistry]!.outputs.resourceId
                }
              ]
            }
            service: 'registry'
            subnetResourceId: virtualNetwork!.outputs.backendSubnetResourceId // Use the backend subnet
          }
        ]
      : []
  }
}

// ========== Container App Environment ========== //
module containerAppEnv './modules/compute/container-app-environment.bicep' = {
  name: take('module.container-app-environment.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: {
      ...resourceGroup().tags
      ...tags
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
    enableTelemetry: enableTelemetry
    enableMonitoring: enableMonitoring
    platformReservedCidr: '172.17.17.0/24'
    platformReservedDnsIP: '172.17.17.17'
    publicNetworkAccess: 'Enabled'
    zoneRedundant: (enablePrivateNetworking) ? true : false
    infrastructureSubnetId: (enablePrivateNetworking) ? virtualNetwork!.outputs.containerSubnetResourceId : null
  }
}

// ========== Container App  ========== //
module containerApp './modules/compute/container-app.bicep' = {
  name: take('module.container-app.${solutionSuffix}', 64)
  params: {
    name: 'ca-app-${solutionSuffix}'
    location: location
    environmentResourceId: containerAppEnv.outputs.resourceId
    tags: tags
    enableTelemetry: enableTelemetry
    workloadProfileName: 'Consumption'
    containers: [
      {
        name: 'ca-${solutionSuffix}'
        image: '${containerRegistryEndpoint}/contentprocessor:${imageTag}'

        resources: {
          cpu: 4
          memory: '8.0Gi'
        }
        env: [
          {
            name: 'APP_CONFIG_ENDPOINT'
            value: appConfig.outputs.endpoint
          }
          {
            name: 'APP_ENV'
            value: 'prod'
          }
          {
            name: 'APP_LOGGING_LEVEL'
            value: 'INFO'
          }
          {
            name: 'AZURE_PACKAGE_LOGGING_LEVEL'
            value: 'WARNING'
          }
          {
            name: 'AZURE_LOGGING_PACKAGES'
            value: ''
          }
          {
            name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
            value: enableMonitoring ? app_insights!.outputs.connectionString : ''
          }
          {
            name: 'OTEL_SERVICE_NAME'
            value: 'ContentProcessor'
          }
        ]
      }
    ]
    ingressExternal: false
    disableIngress: true
    scaleSettings: {
      maxReplicas: enableScalability ? 3 : 2
      minReplicas: enableScalability ? 2 : 1
    }
  }
}

// ========== Container App API ========== //
module containerApp_API './modules/compute/container-app.bicep' = {
  name: take('module.container-app-api.${solutionSuffix}', 64)
  params: {
    name: 'ca-api-${solutionSuffix}'
    location: location
    environmentResourceId: containerAppEnv.outputs.resourceId
    tags: tags
    enableTelemetry: enableTelemetry
    workloadProfileName: 'Consumption'
    containers: [
      {
        name: 'ca-${solutionSuffix}-api'
        image: '${containerRegistryEndpoint}/contentprocessorapi:${imageTag}'
        resources: {
          cpu: 4
          memory: '8.0Gi'
        }
        env: [
          {
            name: 'APP_CONFIG_ENDPOINT'
            value: ''
          }
          {
            name: 'APP_ENV'
            value: 'prod'
          }
          {
            name: 'APP_LOGGING_LEVEL'
            value: 'INFO'
          }
          {
            name: 'AZURE_PACKAGE_LOGGING_LEVEL'
            value: 'WARNING'
          }
          {
            name: 'AZURE_LOGGING_PACKAGES'
            value: ''
          }
          {
            name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
            value: enableMonitoring ? app_insights!.outputs.connectionString : ''
          }
          {
            name: 'OTEL_SERVICE_NAME'
            value: 'ContentProcessorAPI'
          }
        ]
        probes: [
          // Liveness Probe - Checks if the app is still running
          {
            type: 'Liveness'
            httpGet: {
              path: '/startup' // Your app must expose this endpoint
              port: 80
              scheme: 'HTTP'
            }
            initialDelaySeconds: 5
            periodSeconds: 10
            failureThreshold: 3
          }
          // Readiness Probe - Checks if the app is ready to receive traffic
          {
            type: 'Readiness'
            httpGet: {
              path: '/startup'
              port: 80
              scheme: 'HTTP'
            }
            initialDelaySeconds: 5
            periodSeconds: 10
            failureThreshold: 3
          }
          {
            type: 'Startup'
            httpGet: {
              path: '/startup'
              port: 80
              scheme: 'HTTP'
            }
            initialDelaySeconds: 20 // Wait 10s before checking
            periodSeconds: 5 // Check every 15s
            failureThreshold: 10 // Restart if it fails 5 times
          }
        ]
      }
    ]
    scaleSettings: {
      maxReplicas: enableScalability ? 3 : 2
      minReplicas: enableScalability ? 2 : 1
      rules: [
        {
          name: 'http-scaler'
          http: {
            metadata: {
              concurrentRequests: '100'
            }
          }
        }
      ]
    }
    corsPolicy: {
      allowedOrigins: [
        '*'
      ]
      allowedMethods: [
        'GET'
        'POST'
        'PUT'
        'DELETE'
        'OPTIONS'
      ]
      allowedHeaders: [
        'Authorization'
        'Content-Type'
        '*'
      ]
    }
  }
}

//========== Container App Web ========== //
module containerApp_Web './modules/compute/container-app.bicep' = {
  name: take('module.container-app-web.${solutionSuffix}', 64)
  params: {
    name: 'ca-web-${solutionSuffix}'
    location: location
    environmentResourceId: containerAppEnv.outputs.resourceId
    tags: tags
    enableTelemetry: enableTelemetry
    workloadProfileName: 'Consumption'
    ingressTargetPort: 3000
    containers: [
      {
        name: 'ca-${solutionSuffix}-web'
        image: '${containerRegistryEndpoint}/contentprocessorweb:${imageTag}'
        resources: {
          cpu: 4
          memory: '8.0Gi'
        }
        env: [
          {
            name: 'APP_API_BASE_URL'
            value: 'https://${containerApp_API.outputs.fqdn}'
          }
          {
            name: 'APP_WEB_CLIENT_ID'
            value: '<APP_REGISTRATION_CLIENTID>'
          }
          {
            name: 'APP_WEB_AUTHORITY'
            value: '${environment().authentication.loginEndpoint}/${tenant().tenantId}'
          }
          {
            name: 'APP_WEB_SCOPE'
            value: '<FRONTEND_API_SCOPE>'
          }
          {
            name: 'APP_API_SCOPE'
            value: '<BACKEND_API_SCOPE>'
          }
          {
            name: 'APP_REDIRECT_URL'
            value: '/'
          }
          {
            name: 'APP_POST_REDIRECT_URL'
            value: '/'
          }
          {
            name: 'APP_CONSOLE_LOG_ENABLED'
            value: 'false'
          }
        ]
      }
    ]
    scaleSettings: {
      maxReplicas: enableScalability ? 3 : 2
      minReplicas: enableScalability ? 2 : 1
      rules: [
        {
          name: 'http-scaler'
          http: {
            metadata: {
              concurrentRequests: '100'
            }
          }
        }
      ]
    }
  }
}

// ========== Container App Workflow ========== //
module containerApp_Workflow './modules/compute/container-app.bicep' = {
  name: take('module.container-app-workflow.${solutionSuffix}', 64)
  params: {
    name: 'ca-workflow-${solutionSuffix}'
    location: location
    environmentResourceId: containerAppEnv.outputs.resourceId
    tags: tags
    enableTelemetry: enableTelemetry
    workloadProfileName: 'Consumption'
    containers: [
      {
        name: 'ca-${solutionSuffix}-wkfl'
        image: '${containerRegistryEndpoint}/contentprocessorworkflow:${imageTag}'
        resources: {
          cpu: 4
          memory: '8.0Gi'
        }
        env: [
          {
            name: 'APP_CONFIG_ENDPOINT'
            value: appConfig.outputs.endpoint
          }
          {
            name: 'APP_ENV'
            value: 'prod'
          }
          {
            name: 'APP_LOGGING_LEVEL'
            value: 'INFO'
          }
          {
            name: 'AZURE_PACKAGE_LOGGING_LEVEL'
            value: 'WARNING'
          }
          {
            name: 'AZURE_LOGGING_PACKAGES'
            value: ''
          }
          {
            name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
            value: enableMonitoring ? app_insights!.outputs.connectionString : ''
          }
          {
            name: 'OTEL_SERVICE_NAME'
            value: 'ContentProcessorWorkflow'
          }
        ]
      }
    ]
    ingressExternal: false
    disableIngress: true
    scaleSettings: {
      maxReplicas: enableScalability ? 3 : 2
      minReplicas: enableScalability ? 2 : 1
    }
  }
}


// ========== App Configuration ========== //
module appConfig './modules/data/app-configuration.bicep' = {
  name: take('module.app-configuration.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    keyValues: [
      {
        name: 'APP_AZURE_OPENAI_ENDPOINT'
        value: ai_foundry_project!.outputs.cognitiveServicesEndpoint
      }
      {
        name: 'APP_AZURE_OPENAI_MODEL'
        value: gptModelName
      }
      {
        name: 'APP_CONTENT_UNDERSTANDING_ENDPOINT'
        value: ai_foundry_project!.outputs.azureOpenAiCuEndpoint
      }
      {
        name: 'APP_COSMOS_CONTAINER_PROCESS'
        value: 'Processes'
      }
      {
        name: 'APP_COSMOS_CONTAINER_SCHEMA'
        value: 'Schemas'
      }
      {
        name: 'APP_COSMOS_DATABASE'
        value: 'ContentProcess'
      }
      {
        name: 'APP_CPS_CONFIGURATION'
        value: 'cps-configuration'
      }
      {
        name: 'APP_CPS_MAX_FILESIZE_MB'
        value: '20'
      }
      {
        name: 'APP_CPS_PROCESSES'
        value: 'cps-processes'
      }
      {
        name: 'APP_MESSAGE_QUEUE_EXTRACT'
        value: 'content-pipeline-extract-queue'
      }
      {
        name: 'APP_MESSAGE_QUEUE_INTERVAL'
        value: '5'
      }
      {
        name: 'APP_MESSAGE_QUEUE_PROCESS_TIMEOUT'
        value: '180'
      }
      {
        name: 'APP_MESSAGE_QUEUE_VISIBILITY_TIMEOUT'
        value: '10'
      }
      {
        name: 'APP_PROCESS_STEPS'
        value: 'extract,map,evaluate,save'
      }
      {
        name: 'APP_STORAGE_BLOB_URL'
        value: storage_account.outputs.serviceEndpoints.blob
      }
      {
        name: 'APP_STORAGE_QUEUE_URL'
        value: storage_account.outputs.serviceEndpoints.queue
      }
      {
        name: 'APP_AI_PROJECT_ENDPOINT'
        value: ai_foundry_project!.outputs.projectEndpoint
      }
      {
        name: 'APP_COSMOS_CONNSTR'
        value: cosmosDB.outputs.connectionString
      }
      // ===== v2 Workflow Keys ===== //
      {
        name: 'APP_COSMOS_CONTAINER_BATCH_PROCESS'
        value: 'claimprocesses'
      }
      {
        name: 'APP_COSMOS_CONTAINER_BATCHES'
        value: 'batches'
      }
      {
        name: 'APP_COSMOS_CONTAINER_SCHEMASET'
        value: 'Schemasets'
      }
      {
        name: 'APP_CPS_PROCESS_BATCH'
        value: 'process-batch'
      }
      {
        name: 'APP_CPS_CONTENT_PROCESS_ENDPOINT'
        value: 'http://${containerApp_API.outputs.name}/'
      }
      {
        name: 'APP_CPS_POLL_INTERVAL_SECONDS'
        value: '3'
      }
      {
        name: 'APP_STORAGE_ACCOUNT_NAME'
        value: storage_account.outputs.name
      }
      {
        name: 'CLAIM_PROCESS_QUEUE_NAME'
        value: 'claim-process-queue'
      }
      {
        name: 'DEAD_LETTER_QUEUE_NAME'
        value: 'claim-process-dead-letter-queue'
      }
      {
        name: 'AZURE_OPENAI_ENDPOINT'
        value: ai_foundry_project!.outputs.endpoint
      }
      {
        name: 'AZURE_OPENAI_CHAT_DEPLOYMENT_NAME'
        value: gptModelName
      }
      {
        name: 'AZURE_OPENAI_API_VERSION'
        value: '2025-03-01-preview'
      }
      {
        name: 'AZURE_OPENAI_ENDPOINT_BASE'
        value: ai_foundry_project!.outputs.endpoint
      }
      // ===== Agent Framework Keys ===== //
      {
        name: 'AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME'
        value: ''
      }
      {
        name: 'AZURE_AI_AGENT_PROJECT_CONNECTION_STRING'
        value: ''
      }
      {
        name: 'AZURE_TRACING_ENABLED'
        value: 'True'
      }
      {
        name: 'GLOBAL_LLM_SERVICE'
        value: 'AzureOpenAI'
      }
      // ===== GPT-5 Service Prefix Keys ===== //
      {
        name: 'GPT5_API_VERSION'
        value: '2025-03-01-preview'
      }
      {
        name: 'GPT5_CHAT_DEPLOYMENT_NAME'
        value: 'gpt-5'
      }
      {
        name: 'GPT5_ENDPOINT'
        value: ai_foundry_project!.outputs.endpoint
      }
      // ===== PHI-4 Service Prefix Keys ===== //
      {
        name: 'PHI4_API_VERSION'
        value: '2024-05-01-preview'
      }
      {
        name: 'PHI4_CHAT_DEPLOYMENT_NAME'
        value: 'phi-4'
      }
      {
        name: 'PHI4_ENDPOINT'
        value: ai_foundry_project!.outputs.endpoint
      }
    ]
    diagnosticSettings: enableMonitoring
      ? [
          {
            workspaceResourceId: enableMonitoring ? logAnalyticsWorkspaceResourceId : ''
            logCategoriesAndGroups: [
              {
                categoryGroup: 'allLogs'
                enabled: true
              }
            ]
          }
        ]
      : null
    disableLocalAuth: false
    replicaLocations: enableRedundancy? [{ replicaLocation: replicaLocation }] : []
    publicNetworkAccess: 'Enabled'
  }
}

module appConfig_update './modules/data/app-configuration.bicep' = if (enablePrivateNetworking) {
  name: take('module.app-configuration-update.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    publicNetworkAccess: 'Disabled'
    enableTelemetry: enableTelemetry
    privateEndpoints: [
      {
        name: 'pep-appconfig-${solutionSuffix}'
        customNetworkInterfaceName: 'nic-appconfig-${solutionSuffix}'
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            {
              name: 'appconfig-dns-zone-group'
              privateDnsZoneResourceId: privateDnsZoneDeployments[dnsZoneIndex.appConfig]!.outputs.resourceId
            }
          ]
        }
        subnetResourceId: virtualNetwork!.outputs.backendSubnetResourceId // Use the backend subnet
      }
    ]
  }
  dependsOn: [
    appConfig
  ]
}


// ========== Container App API Update Modules ========== //
module containerApp_API_update './modules/compute/container-app.bicep' = {
  name: take('module.container-app-api-update.${solutionSuffix}', 64)
  params: {
    name: 'ca-api-${solutionSuffix}'
    location: location
    environmentResourceId: containerAppEnv.outputs.resourceId
    tags: tags
    enableTelemetry: enableTelemetry
    workloadProfileName: 'Consumption'
    containers: [
      {
        name: 'ca-${solutionSuffix}-api'
        image: '${containerRegistryEndpoint}/contentprocessorapi:${imageTag}'
        resources: {
          cpu: 4
          memory: '8.0Gi'
        }
        env: [
          {
            name: 'APP_CONFIG_ENDPOINT'
            value: appConfig.outputs.endpoint
          }
          {
            name: 'APP_ENV'
            value: 'prod'
          }
          {
            name: 'APP_LOGGING_LEVEL'
            value: 'INFO'
          }
          {
            name: 'AZURE_PACKAGE_LOGGING_LEVEL'
            value: 'WARNING'
          }
          {
            name: 'AZURE_LOGGING_PACKAGES'
            value: ''
          }
          {
            name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
            value: enableMonitoring ? app_insights!.outputs.connectionString : ''
          }
          {
            name: 'OTEL_SERVICE_NAME'
            value: 'ContentProcessorAPI'
          }
        ]
        probes: [
          // Liveness Probe - Checks if the app is still running
          {
            type: 'Liveness'
            httpGet: {
              path: '/startup' // Your app must expose this endpoint
              port: 80
              scheme: 'HTTP'
            }
            initialDelaySeconds: 5
            periodSeconds: 10
            failureThreshold: 3
          }
          // Readiness Probe - Checks if the app is ready to receive traffic
          {
            type: 'Readiness'
            httpGet: {
              path: '/startup'
              port: 80
              scheme: 'HTTP'
            }
            initialDelaySeconds: 5
            periodSeconds: 10
            failureThreshold: 3
          }
          {
            type: 'Startup'
            httpGet: {
              path: '/startup'
              port: 80
              scheme: 'HTTP'
            }
            initialDelaySeconds: 20 // Wait 10s before checking
            periodSeconds: 5 // Check every 15s
            failureThreshold: 10 // Restart if it fails 5 times
          }
        ]
      }
    ]
    scaleSettings: {
      maxReplicas: enableScalability ? 3 : 2
      minReplicas: enableScalability ? 2 : 1
      rules: [
        {
          name: 'http-scaler'
          http: {
            metadata: {
              concurrentRequests: '100'
            }
          }
        }
      ]
    }
    corsPolicy: {
      allowedOrigins: [
        '*'
      ]
      allowedMethods: [
        'GET'
        'POST'
        'PUT'
        'DELETE'
        'OPTIONS'
      ]
      allowedHeaders: [
        'Authorization'
        'Content-Type'
        '*'
      ]
    }
  }
  dependsOn: [
    aifoundry_private_endpoint
    containerApp_API
  ]
}


// ========== Role Assignments (centralized)  ========== //
module role_assignments './modules/identity/role-assignments.bicep' = {
  name: take('module.role-assignments.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    useExistingAIProject: useExistingAIProject
    existingFoundryProjectResourceId: existingFoundryProjectResourceId
    aiFoundryResourceId: ai_foundry_project!.outputs.resourceId
    appConfigurationResourceId: appConfig.outputs.resourceId
    storageAccountResourceId: storage_account.outputs.resourceId
    containerAppServicePrincipalId: containerApp.outputs.principalId
    containerAppAPIServicePrincipalId: containerApp_API.outputs.principalId
    containerAppWebServicePrincipalId: containerApp_Web.outputs.principalId
    containerAppWorkFlowServicePrincipalId: containerApp_Workflow.outputs.principalId
    deployerPrincipalId: deployingUserPrincipalId
    deployerPrincipalType: deployingUserPrincipalType
  }
  scope: resourceGroup(resourceGroup().name)
}

// ============ //
// Outputs      //
// ============ //

@description('The name of the Container App used for Web App.')
output CONTAINER_WEB_APP_NAME string = containerApp_Web.outputs.name

@description('The name of the Container App used for API.')
output CONTAINER_API_APP_NAME string = containerApp_API.outputs.name

@description('The FQDN of the Container App.')
output CONTAINER_WEB_APP_FQDN string = containerApp_Web.outputs.fqdn

@description('The FQDN of the Container App API.')
output CONTAINER_API_APP_FQDN string = containerApp_API.outputs.fqdn

@description('The name of the Container App used for APP.')
output CONTAINER_APP_NAME string = containerApp.outputs.name

@description('The name of the Container App used for Workflow.')
output CONTAINER_WORKFLOW_APP_NAME string = containerApp_Workflow.outputs.name

@description('The name of the Azure Container Registry.')
output CONTAINER_REGISTRY_NAME string = containerRegistry.outputs.name

@description('The login server of the Azure Container Registry.')
output CONTAINER_REGISTRY_LOGIN_SERVER string = containerRegistry.outputs.loginServer

@description('The name of the AI Services account that hosts both Azure OpenAI and Content Understanding GA.')
output CONTENT_UNDERSTANDING_ACCOUNT_NAME string = ai_foundry_project!.outputs.name

@description('The resource group the resources were deployed into.')
output AZURE_RESOURCE_GROUP string = resourceGroup().name
