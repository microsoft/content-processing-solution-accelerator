// ============================================================================
// Main Deployment Template
// ============================================================================

targetScope = 'resourceGroup'

metadata name = 'Content Processing Solution Accelerator - Bicep'
metadata description = 'Deploys Content Processing resources using the restored private-repo module interfaces.'

// ============================================================================
// Parameters — Core
// ============================================================================

@minLength(3)
@maxLength(20)
@description('Optional. Name of the solution to deploy. This should be 3-20 characters long.')
param solutionName string = 'cps'

@maxLength(5)
@description('Optional. A unique text value for the solution. This is used to ensure resource names are unique for global resources.')
param solutionUniqueText string = substring(uniqueString(subscription().id, resourceGroup().name, solutionName), 0, 5)

@metadata({ azd: { type: 'location' } })
@description('Required. Azure region for all services.')
param location string

@description('Optional. Tags to be applied to the resources.')
param tags object = {
  app: 'Content Processing Solution Accelerator'
  location: resourceGroup().location
}

@minLength(1)
@allowed([
  'australiaeast'
  'eastus'
  'eastus2'
  'japaneast'
  'southcentralus'
  'southeastasia'
  'swedencentral'
  'uksouth'
  'westeurope'
  'westus'
  'westus3'
])
@description('Required. Location for the Azure AI Services deployment.')
@metadata({
  azd: {
    type: 'location'
    usageName: [
      'OpenAI.GlobalStandard.gpt-5.1,300'
    ]
  }
})
param azureAiServiceLocation string

// ============================================================================
// Parameters — AI Configuration
// ============================================================================

@description('Optional. Type of GPT deployment to use: Standard | GlobalStandard.')
@allowed([
  'Standard'
  'GlobalStandard'
])
param deploymentType string = 'GlobalStandard'

@description('Optional. Name of the GPT model to deploy.')
param gptModelName string = 'gpt-5.1'

@description('Optional. Version of the GPT model to deploy. Empty string uses the latest available version.')
param gptModelVersion string = ''

@minValue(1)
@description('Optional. Capacity of the GPT deployment.')
param gptDeploymentCapacity int = 10

// ============================================================================
// Parameters — Compute
// ============================================================================

@description('Optional. The container registry login server or endpoint for the container images.')
param containerRegistryEndpoint string = ''

@description('Optional. The image tag for the container images.')
param imageTag string = 'latest_v2'

// ============================================================================
// Parameters — WAF Feature Flags
// ============================================================================

@description('Optional. Enable private networking for the deployment.')
param enablePrivateNetworking bool = false

@description('Optional. Enable monitoring applicable resources.')
param enableMonitoring bool = false

@description('Optional. Enable redundancy for applicable resources.')
param enableRedundancy bool = false

@description('Optional. Enable scalability for applicable resources.')
param enableScalability bool = false

@description('Optional. Enable or disable usage telemetry for the deployment.')
param enableTelemetry bool = true

@description('Optional. Enable purge protection.')
param enablePurgeProtection bool = false

// ============================================================================
// Parameters — Existing Resources
// ============================================================================

@description('Optional. Existing Log Analytics Workspace resource ID.')
param existingLogAnalyticsWorkspaceId string = ''

@description('Optional. Existing Azure AI Foundry project resource ID.')
param existingFoundryProjectResourceId string = ''

// ============================================================================
// Variables
// ============================================================================

var solutionSuffix = toLower(trim(replace(
  replace(
    replace(replace(replace(replace('${solutionName}${solutionUniqueText}', '-', ''), '_', ''), '.', ''), '/', ''),
    ' ',
    ''
  ),
  '*',
  ''
)))

var managedIdentityName = 'id-${solutionSuffix}'
var containerRegistryName = replace('cr${solutionSuffix}', '-', '')
var storageAccountName = take(replace('st${solutionSuffix}', '-', ''), 24)
var cosmosDbName = 'cosmos-${solutionSuffix}'
var cosmosDatabaseName = 'contentprocessing'
var cosmosContainerName = 'documents'
var aiServicesName = 'aif-${solutionSuffix}'
var aiProjectName = 'proj-${solutionSuffix}'
var aiSearchName = 'srch-${solutionSuffix}'
var appConfigurationName = 'appcs-${solutionSuffix}'
var containerAppEnvironmentName = 'cae-${solutionSuffix}'
var contentProcessorAppName = 'ca-${solutionSuffix}-app'
var contentProcessorApiName = 'ca-${solutionSuffix}-api'
var contentProcessorWebName = 'ca-${solutionSuffix}-web'
var contentProcessorWorkflowName = 'ca-${solutionSuffix}-wkfl'
var modelDeploymentName = 'gpt-${solutionSuffix}'
var storageContainerName = 'content'
var storageQueueName = 'content'

var acrPullRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
var storageBlobDataContributorRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
var storageQueueDataContributorRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '974c5e8b-45b9-4653-ba55-5f855dd0fb88')
var appConfigurationDataReaderRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '516239f1-63e1-4d78-a4de-a74fb236a071')
var cognitiveServicesOpenAiUserRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
var cognitiveServicesUserRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908')
var azureAiDeveloperRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '64702f94-c441-49e6-a78b-ef80e0188fee')

var effectiveContainerRegistryEndpoint = empty(containerRegistryEndpoint) ? containerRegistry.outputs.loginServer : containerRegistryEndpoint
var apiAppFqdn = '${contentProcessorApiName}.${containerAppEnvironment.outputs.defaultDomain}'
var webAppFqdn = '${contentProcessorWebName}.${containerAppEnvironment.outputs.defaultDomain}'
var workflowAppFqdn = '${contentProcessorWorkflowName}.${containerAppEnvironment.outputs.defaultDomain}'
var cosmosDbEndpoint = 'https://${cosmosDb.name}.mongo.cosmos.azure.com:443/'

var sharedEnv = [
  {
    name: 'APP_CONFIG_ENDPOINT'
    value: appConfiguration.outputs.endpoint
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
    name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
    value: enableMonitoring ? appInsights!.outputs.connectionString : ''
  }
]

var apiProbes = [
  {
    type: 'Liveness'
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
    initialDelaySeconds: 20
    periodSeconds: 5
    failureThreshold: 10
  }
]

var appConfigurationValues = [
  {
    name: 'APP_AZURE_OPENAI_ENDPOINT'
    value: aiFoundry.outputs.endpoint
  }
  {
    name: 'APP_AZURE_OPENAI_MODEL'
    value: gptModelName
  }
  {
    name: 'APP_CONTENT_UNDERSTANDING_ENDPOINT'
    value: aiFoundry.outputs.endpoint
  }
  {
    name: 'APP_AI_PROJECT_ENDPOINT'
    value: aiProject.properties.endpoints['AI Foundry API']
  }
  {
    name: 'APP_COSMOS_DB_ENDPOINT'
    value: cosmosDbEndpoint
  }
  {
    name: 'APP_COSMOS_DB_NAME'
    value: cosmosDatabaseName
  }
  {
    name: 'APP_COSMOS_DB_CONTAINER'
    value: cosmosContainerName
  }
  {
    name: 'APP_STORAGE_ACCOUNT_NAME'
    value: storageAccount.outputs.name
  }
  {
    name: 'APP_STORAGE_BLOB_ENDPOINT'
    value: storageAccount.outputs.blobEndpoint
  }
  {
    name: 'APP_STORAGE_QUEUE_ENDPOINT'
    value: storageAccount.outputs.serviceEndpoints.queue
  }
  {
    name: 'APP_STORAGE_CONTAINER_NAME'
    value: storageContainerName
  }
  {
    name: 'APP_AI_SEARCH_ENDPOINT'
    value: aiSearch.outputs.endpoint
  }
  {
    name: 'APP_AI_SEARCH_INDEX'
    value: 'content-index'
  }
  {
    name: 'APP_WORKFLOW_APP_ENDPOINT'
    value: 'https://${workflowAppFqdn}'
  }
  {
    name: 'APP_API_ENDPOINT'
    value: 'https://${apiAppFqdn}'
  }
  {
    name: 'AZURE_OPENAI_API_VERSION'
    value: '2025-03-01-preview'
  }
  {
    name: 'AZURE_TRACING_ENABLED'
    value: 'True'
  }
]

// ============================================================================
// Module — Monitoring — Log Analytics
// ============================================================================

module logAnalytics './modules/monitoring/log-analytics.bicep' = if (enableMonitoring) {
  name: take('module.log-analytics.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
  }
}

// ============================================================================
// Module — Monitoring — Application Insights
// ============================================================================

module appInsights './modules/monitoring/app-insights.bicep' = if (enableMonitoring) {
  name: take('module.app-insights.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    workspaceResourceId: logAnalytics!.outputs.resourceId
    tags: tags
  }
}

// ============================================================================
// Module — Identity — Managed Identity
// ============================================================================

module managedIdentity './modules/identity/managed-identity.bicep' = {
  name: take('module.managed-identity.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    identityName: managedIdentityName
    location: location
    tags: tags
  }
}

// ============================================================================
// Module — Compute — Container Registry
// ============================================================================

module containerRegistry './modules/compute/container-registry.bicep' = {
  name: take('module.container-registry.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    name: containerRegistryName
    location: location
    sku: enableRedundancy ? 'Premium' : 'Standard'
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    tags: tags
  }
}

// ============================================================================
// Module — Data — Storage Account
// ============================================================================

module storageAccount './modules/data/storage-account.bicep' = {
  name: take('module.storage-account.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    name: storageAccountName
    location: location
    skuName: enableRedundancy ? 'Standard_ZRS' : 'Standard_LRS'
    containers: [
      {
        name: storageContainerName
        publicAccess: 'None'
      }
    ]
    tags: tags
  }
}

// ============================================================================
// Resources — Storage Queue
// ============================================================================

resource storageAccountResource 'Microsoft.Storage/storageAccounts@2025-08-01' existing = {
  name: storageAccountName
}

resource queueService 'Microsoft.Storage/storageAccounts/queueServices@2025-08-01' = {
  parent: storageAccountResource
  name: 'default'
}

resource storageQueue 'Microsoft.Storage/storageAccounts/queueServices/queues@2025-08-01' = {
  parent: queueService
  name: storageQueueName
}

// ============================================================================
// Resources — Cosmos DB
// ============================================================================

resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' = {
  name: cosmosDbName
  location: location
  kind: 'MongoDB'
  tags: tags
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: enableRedundancy
      }
    ]
    capabilities: [
      {
        name: 'EnableMongo'
      }
    ]
    apiProperties: {
      serverVersion: '7.0'
    }
    disableLocalAuth: false
    enableAutomaticFailover: false
    enableMultipleWriteLocations: false
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
  }
}

resource cosmosMongoDatabase 'Microsoft.DocumentDB/databaseAccounts/mongodbDatabases@2023-04-15' = {
  parent: cosmosDb
  name: cosmosDatabaseName
  properties: {
    resource: {
      id: cosmosDatabaseName
    }
    options: {}
  }
}

resource cosmosMongoCollection 'Microsoft.DocumentDB/databaseAccounts/mongodbDatabases/collections@2023-04-15' = {
  parent: cosmosMongoDatabase
  name: cosmosContainerName
  properties: {
    resource: {
      id: cosmosContainerName
      shardKey: {
        id: 'Hash'
      }
      indexes: [
        {
          key: {
            keys: [
              '_id'
            ]
          }
        }
      ]
    }
    options: {}
  }
}

// ============================================================================
// Module — AI — AI Foundry
// ============================================================================

module aiFoundry './modules/ai/ai-foundry.bicep' = {
  name: take('module.ai-foundry.${solutionSuffix}', 64)
  params: {
    name: aiServicesName
    location: azureAiServiceLocation
    principalIds: []
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    tags: union(tags, {
      location: azureAiServiceLocation
    })
  }
}

// ============================================================================
// Resources — AI Project
// ============================================================================

resource aiServicesAccount 'Microsoft.CognitiveServices/accounts@2025-12-01' existing = {
  name: aiServicesName
}

resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-12-01' = {
  parent: aiServicesAccount
  name: aiProjectName
  location: azureAiServiceLocation
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  tags: union(tags, {
    location: azureAiServiceLocation
  })
  properties: {}
}

// ============================================================================
// Module — AI — Model Deployment
// ============================================================================

module modelDeployment './modules/ai/ai-foundry-model-deployment.bicep' = {
  name: take('module.model-deployment.${solutionSuffix}', 64)
  params: {
    aiServicesAccountName: aiFoundry.outputs.name
    deploymentName: modelDeploymentName
    modelName: gptModelName
    modelVersion: gptModelVersion
    skuName: deploymentType
    skuCapacity: gptDeploymentCapacity
  }
}

// ============================================================================
// Module — AI — Search
// ============================================================================

module aiSearch './modules/ai/ai-search.bicep' = {
  name: take('module.ai-search.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    name: aiSearchName
    location: location
    replicaCount: enableRedundancy ? 2 : 1
    partitionCount: enableScalability ? 2 : 1
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    tags: tags
  }
}

// ============================================================================
// Module — Compute — Container App Environment
// ============================================================================

module containerAppEnvironment './modules/compute/container-app-environment.bicep' = {
  name: take('module.container-app-environment.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    name: containerAppEnvironmentName
    location: location
    logAnalyticsWorkspaceResourceId: enableMonitoring ? logAnalytics!.outputs.resourceId : ''
    zoneRedundant: enableRedundancy
    tags: tags
  }
}

// ============================================================================
// Module — Data — App Configuration
// ============================================================================

module appConfiguration './modules/data/app-configuration.bicep' = {
  name: take('module.app-configuration.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    name: appConfigurationName
    location: location
    keyValues: appConfigurationValues
    tags: tags
  }
}

// ============================================================================
// Module — Compute — Content Processor App
// ============================================================================

module contentProcessorApp './modules/compute/container-app.bicep' = {
  name: take('module.content-processor-app.${solutionSuffix}', 64)
  params: {
    name: contentProcessorAppName
    location: location
    environmentResourceId: containerAppEnvironment.outputs.resourceId
    disableIngress: true
    containers: [
      {
        name: contentProcessorAppName
        image: '${effectiveContainerRegistryEndpoint}/contentprocessor:${imageTag}'
        resources: {
          cpu: 4
          memory: '8Gi'
        }
        env: concat(sharedEnv, [
          {
            name: 'OTEL_SERVICE_NAME'
            value: 'ContentProcessor'
          }
        ])
      }
    ]
    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [
        managedIdentity.outputs.resourceId
      ]
    }
    registries: [
      {
        server: effectiveContainerRegistryEndpoint
        identity: managedIdentity.outputs.resourceId
      }
    ]
    scaleSettings: {
      minReplicas: enableScalability ? 2 : 1
      maxReplicas: enableScalability ? 3 : 2
    }
    tags: tags
  }
}

// ============================================================================
// Module — Compute — Content Processor API
// ============================================================================

module contentProcessorApi './modules/compute/container-app.bicep' = {
  name: take('module.content-processor-api.${solutionSuffix}', 64)
  params: {
    name: contentProcessorApiName
    location: location
    environmentResourceId: containerAppEnvironment.outputs.resourceId
    ingressExternal: true
    ingressTargetPort: 80
    containers: [
      {
        name: contentProcessorApiName
        image: '${effectiveContainerRegistryEndpoint}/contentprocessorapi:${imageTag}'
        resources: {
          cpu: 2
          memory: '4Gi'
        }
        env: concat(sharedEnv, [
          {
            name: 'OTEL_SERVICE_NAME'
            value: 'ContentProcessorAPI'
          }
        ])
        probes: apiProbes
      }
    ]
    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [
        managedIdentity.outputs.resourceId
      ]
    }
    registries: [
      {
        server: effectiveContainerRegistryEndpoint
        identity: managedIdentity.outputs.resourceId
      }
    ]
    scaleSettings: {
      minReplicas: 0
      maxReplicas: 10
    }
    tags: tags
  }
}

// ============================================================================
// Module — Compute — Content Processor Web
// ============================================================================

module contentProcessorWeb './modules/compute/container-app.bicep' = {
  name: take('module.content-processor-web.${solutionSuffix}', 64)
  params: {
    name: contentProcessorWebName
    location: location
    environmentResourceId: containerAppEnvironment.outputs.resourceId
    ingressExternal: true
    ingressTargetPort: 80
    containers: [
      {
        name: contentProcessorWebName
        image: '${effectiveContainerRegistryEndpoint}/contentprocessorweb:${imageTag}'
        resources: {
          cpu: 2
          memory: '4Gi'
        }
        env: concat(sharedEnv, [
          {
            name: 'APP_API_BASE_URL'
            value: 'https://${apiAppFqdn}'
          }
          {
            name: 'OTEL_SERVICE_NAME'
            value: 'ContentProcessorWeb'
          }
        ])
      }
    ]
    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [
        managedIdentity.outputs.resourceId
      ]
    }
    registries: [
      {
        server: effectiveContainerRegistryEndpoint
        identity: managedIdentity.outputs.resourceId
      }
    ]
    corsPolicy: {
      allowedOrigins: [
        'https://${apiAppFqdn}'
      ]
      allowedMethods: [
        'GET'
        'POST'
        'PUT'
        'DELETE'
        'OPTIONS'
      ]
      allowedHeaders: [
        '*'
      ]
    }
    scaleSettings: {
      minReplicas: 0
      maxReplicas: 10
    }
    tags: tags
  }
}

// ============================================================================
// Module — Compute — Content Processor Workflow
// ============================================================================

module contentProcessorWorkflow './modules/compute/container-app.bicep' = {
  name: take('module.content-processor-workflow.${solutionSuffix}', 64)
  params: {
    name: contentProcessorWorkflowName
    location: location
    environmentResourceId: containerAppEnvironment.outputs.resourceId
    ingressExternal: true
    ingressTargetPort: 80
    containers: [
      {
        name: contentProcessorWorkflowName
        image: '${effectiveContainerRegistryEndpoint}/contentprocessorworkflow:${imageTag}'
        resources: {
          cpu: 2
          memory: '4Gi'
        }
        env: concat(sharedEnv, [
          {
            name: 'OTEL_SERVICE_NAME'
            value: 'ContentProcessorWorkflow'
          }
        ])
      }
    ]
    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [
        managedIdentity.outputs.resourceId
      ]
    }
    registries: [
      {
        server: effectiveContainerRegistryEndpoint
        identity: managedIdentity.outputs.resourceId
      }
    ]
    scaleSettings: {
      minReplicas: 0
      maxReplicas: 10
    }
    tags: tags
  }
}

// ============================================================================
// Resources — Existing Resource References
// ============================================================================

resource containerRegistryResource 'Microsoft.ContainerRegistry/registries@2025-04-01' existing = {
  name: containerRegistryName
}

resource appConfigurationResource 'Microsoft.AppConfiguration/configurationStores@2023-03-01' existing = {
  name: appConfigurationName
}

// ============================================================================
// Resources — Role Assignments
// ============================================================================

resource acrPullAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistryName, managedIdentityName, 'acr-pull')
  scope: containerRegistryResource
  properties: {
    principalId: managedIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: acrPullRoleId
  }
}

resource contentProcessorBlobRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountName, contentProcessorAppName, 'blob')
  scope: storageAccountResource
  properties: {
    principalId: contentProcessorApp.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: storageBlobDataContributorRoleId
  }
}

resource contentProcessorApiBlobRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountName, contentProcessorApiName, 'blob')
  scope: storageAccountResource
  properties: {
    principalId: contentProcessorApi.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: storageBlobDataContributorRoleId
  }
}

resource contentProcessorWorkflowBlobRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountName, contentProcessorWorkflowName, 'blob')
  scope: storageAccountResource
  properties: {
    principalId: contentProcessorWorkflow.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: storageBlobDataContributorRoleId
  }
}

resource contentProcessorQueueRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountName, contentProcessorAppName, 'queue')
  scope: storageAccountResource
  properties: {
    principalId: contentProcessorApp.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: storageQueueDataContributorRoleId
  }
}

resource contentProcessorApiQueueRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountName, contentProcessorApiName, 'queue')
  scope: storageAccountResource
  properties: {
    principalId: contentProcessorApi.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: storageQueueDataContributorRoleId
  }
}

resource contentProcessorWorkflowQueueRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountName, contentProcessorWorkflowName, 'queue')
  scope: storageAccountResource
  properties: {
    principalId: contentProcessorWorkflow.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: storageQueueDataContributorRoleId
  }
}

resource contentProcessorAppConfigRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(appConfigurationName, contentProcessorAppName, 'appconfig')
  scope: appConfigurationResource
  properties: {
    principalId: contentProcessorApp.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: appConfigurationDataReaderRoleId
  }
}

resource contentProcessorApiAppConfigRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(appConfigurationName, contentProcessorApiName, 'appconfig')
  scope: appConfigurationResource
  properties: {
    principalId: contentProcessorApi.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: appConfigurationDataReaderRoleId
  }
}

resource contentProcessorWebAppConfigRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(appConfigurationName, contentProcessorWebName, 'appconfig')
  scope: appConfigurationResource
  properties: {
    principalId: contentProcessorWeb.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: appConfigurationDataReaderRoleId
  }
}

resource contentProcessorWorkflowAppConfigRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(appConfigurationName, contentProcessorWorkflowName, 'appconfig')
  scope: appConfigurationResource
  properties: {
    principalId: contentProcessorWorkflow.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: appConfigurationDataReaderRoleId
  }
}

resource contentProcessorOpenAiUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServicesName, contentProcessorAppName, 'openai-user')
  scope: aiServicesAccount
  properties: {
    principalId: contentProcessorApp.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: cognitiveServicesOpenAiUserRoleId
  }
}

resource contentProcessorWorkflowOpenAiUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServicesName, contentProcessorWorkflowName, 'openai-user')
  scope: aiServicesAccount
  properties: {
    principalId: contentProcessorWorkflow.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: cognitiveServicesOpenAiUserRoleId
  }
}

resource contentProcessorAiDeveloperAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServicesName, contentProcessorAppName, 'ai-developer')
  scope: aiServicesAccount
  properties: {
    principalId: contentProcessorApp.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: azureAiDeveloperRoleId
  }
}

resource contentProcessorWorkflowAiDeveloperAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServicesName, contentProcessorWorkflowName, 'ai-developer')
  scope: aiServicesAccount
  properties: {
    principalId: contentProcessorWorkflow.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: azureAiDeveloperRoleId
  }
}

resource contentProcessorAiUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServicesName, contentProcessorAppName, 'cog-user')
  scope: aiServicesAccount
  properties: {
    principalId: contentProcessorApp.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: cognitiveServicesUserRoleId
  }
}

resource contentProcessorWorkflowAiUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServicesName, contentProcessorWorkflowName, 'cog-user')
  scope: aiServicesAccount
  properties: {
    principalId: contentProcessorWorkflow.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: cognitiveServicesUserRoleId
  }
}

// ============================================================================
// Outputs
// ============================================================================

output SOLUTION_NAME string = solutionName
output CONTAINER_WEB_APP_NAME string = contentProcessorWeb.outputs.name
output CONTAINER_API_APP_NAME string = contentProcessorApi.outputs.name
output CONTAINER_WEB_APP_FQDN string = webAppFqdn
output CONTAINER_API_APP_FQDN string = apiAppFqdn
output CONTAINER_APP_NAME string = contentProcessorApp.outputs.name
output CONTAINER_WORKFLOW_APP_NAME string = contentProcessorWorkflow.outputs.name
output CONTAINER_APP_USER_IDENTITY_ID string = managedIdentity.outputs.resourceId
output CONTAINER_APP_USER_PRINCIPAL_ID string = managedIdentity.outputs.principalId
output CONTAINER_REGISTRY_NAME string = containerRegistry.outputs.name
output CONTAINER_REGISTRY_LOGIN_SERVER string = containerRegistry.outputs.loginServer
output CONTENT_UNDERSTANDING_ACCOUNT_NAME string = aiFoundry.outputs.name
output AZURE_RESOURCE_GROUP string = resourceGroup().name
