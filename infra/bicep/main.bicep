// ============================================================================
// main.bicep — Orchestrator
// Description: Pure orchestrator for Content Processing Solution Accelerator
//              All resource names are derived from params — no hardcoded names.
//              This file only calls modules; no inline resource definitions.
// ============================================================================
targetScope = 'resourceGroup'

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
param location string = resourceGroup().location

@description('Optional. Tags to be applied to the resources.')
param tags object = {}

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
param containerRegistryEndpoint string = 'cpscontainerreg.azurecr.io'

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

var solutionSuffix = toLower(trim(replace(replace(replace(replace(replace(replace('${solutionName}${solutionUniqueText}', '-', ''), '_', ''), '.', ''), '/', ''), ' ', ''), '*', '')))

var deployerInfo = deployer()
var createdBy = contains(deployerInfo, 'userPrincipalName') ? split(deployerInfo.userPrincipalName, '@')[0] : deployerInfo.objectId
var existingTags = resourceGroup().tags ?? {}

// NOTE: managedIdentityName removed — migrated to system-assigned identity

var containerRegistryName = replace('cr${solutionSuffix}', '-', '')

var storageAccountName = take(replace('st${solutionSuffix}', '-', ''), 24)

var cosmosDbName = 'cosmos-${solutionSuffix}'

var cosmosDatabaseName = 'contentprocessing'

var cosmosContainerName = 'documents'

var aiServicesName = 'aif-${solutionSuffix}'

var aiProjectName = 'proj-${solutionSuffix}'

var appConfigurationName = 'appcs-${solutionSuffix}'

var containerAppEnvironmentName = 'cae-${solutionSuffix}'

var contentProcessorAppName = 'ca-${solutionSuffix}-app'

var contentProcessorApiName = 'ca-${solutionSuffix}-api'

var contentProcessorWebName = 'ca-${solutionSuffix}-web'

var contentProcessorWorkflowName = 'ca-${solutionSuffix}-wkfl'

var modelDeploymentName = 'gpt-${solutionSuffix}'

var storageContainerName = 'content'

var storageQueueName = 'content'

var effectiveContainerRegistryEndpoint = empty(containerRegistryEndpoint) ? container_registry.outputs.loginServer : containerRegistryEndpoint
var useExternalRegistry = !empty(containerRegistryEndpoint)

var apiAppFqdn = '${contentProcessorApiName}.${container_app_environment.outputs.defaultDomain}'

var webAppFqdn = '${contentProcessorWebName}.${container_app_environment.outputs.defaultDomain}'

var workflowAppFqdn = '${contentProcessorWorkflowName}.${container_app_environment.outputs.defaultDomain}'

var cosmosDbEndpoint = cosmos_db.outputs.endpoint

var sharedEnv = [
  {
    name: 'APP_CONFIG_ENDPOINT'
    value: app_configuration.outputs.endpoint
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
    value: enableMonitoring ? app_insights!.outputs.connectionString : ''
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
    value: ai_foundry.outputs.endpoint
  }
  {
    name: 'APP_AZURE_OPENAI_MODEL'
    value: gptModelName
  }
  {
    name: 'APP_CONTENT_UNDERSTANDING_ENDPOINT'
    value: ai_foundry.outputs.endpoint
  }
  {
    name: 'APP_AI_PROJECT_ENDPOINT'
    value: ai_foundry.outputs.projectEndpoint
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
    value: storage_account.outputs.name
  }
  {
    name: 'APP_STORAGE_BLOB_ENDPOINT'
    value: storage_account.outputs.blobEndpoint
  }
  {
    name: 'APP_STORAGE_QUEUE_ENDPOINT'
    value: storage_account.outputs.serviceEndpoints.queue
  }
  {
    name: 'APP_STORAGE_CONTAINER_NAME'
    value: storageContainerName
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

var resourceTags = union(existingTags, tags, {
  TemplateName: 'Content Processing'
  CreatedBy: createdBy
  DeploymentName: deployment().name
  Type: 'Non-WAF'
})

// ============================================================================
// Resource Group Tags
// ============================================================================

resource resourceGroupTags 'Microsoft.Resources/tags@2025-04-01' = {
  name: 'default'
  properties: {
    tags: resourceTags
  }
}

// ============================================================================
// Module: Monitoring
// ============================================================================

module log_analytics './modules/monitoring/log-analytics.bicep' = if (enableMonitoring) {
  name: take('module.log-analytics.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
  }
}

module app_insights './modules/monitoring/app-insights.bicep' = if (enableMonitoring) {
  name: take('module.app-insights.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    workspaceResourceId: log_analytics!.outputs.resourceId
    tags: tags
  }
}

// ============================================================================
// Module: AI Services
// ============================================================================

module ai_foundry './modules/ai/ai-foundry.bicep' = {
  name: take('module.ai-foundry.${solutionName}', 64)
  params: {
    name: aiServicesName
    location: azureAiServiceLocation
    principalIds: []
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    projectName: aiProjectName
    tags: union(tags, {
      location: azureAiServiceLocation
    })
  }
}

module model_deployment './modules/ai/ai-foundry-model-deployment.bicep' = {
  name: take('module.model-deployment.${solutionName}', 64)
  params: {
    aiServicesAccountName: ai_foundry.outputs.name
    deploymentName: modelDeploymentName
    modelName: gptModelName
    modelVersion: gptModelVersion
    skuName: deploymentType
    skuCapacity: gptDeploymentCapacity
  }
}

// ============================================================================
// Module: Data
// ============================================================================

module storage_account './modules/data/storage-account.bicep' = {
  name: take('module.storage-account.${solutionName}', 64)
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
    queues: [
      storageQueueName
    ]
    tags: tags
  }
}

module cosmos_db './modules/data/cosmos-db-mongo.bicep' = {
  name: take('module.cosmos-db-mongo.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    name: cosmosDbName
    location: location
    tags: tags
    databaseName: cosmosDatabaseName
    collections: [
      {
        name: cosmosContainerName
        shardKey: { id: 'Hash' }
        indexes: [
          { key: { keys: ['_id'] } }
        ]
      }
    ]
    serverVersion: '7.0'
    consistencyLevel: 'Session'
    zoneRedundant: enableRedundancy
    enableAutomaticFailover: false
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
  }
}

module app_configuration './modules/data/app-configuration.bicep' = {
  name: take('module.app-configuration.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    name: appConfigurationName
    location: location
    keyValues: appConfigurationValues
    tags: tags
  }
}

// ============================================================================
// Module: Compute
// NOTE: Migrated from user-assigned to system-assigned managed identity.
// Container Apps use their system-assigned identity for ACR pull and role assignments.
// ============================================================================

module container_registry './modules/compute/container-registry.bicep' = {
  name: take('module.container-registry.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    name: containerRegistryName
    location: location
    sku: enableRedundancy || enablePrivateNetworking ? 'Premium' : 'Standard'
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    tags: tags
  }
}

module container_app_environment './modules/compute/container-app-environment.bicep' = {
  name: take('module.container-app-environment.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    name: containerAppEnvironmentName
    location: location
    logAnalyticsWorkspaceResourceId: enableMonitoring ? log_analytics!.outputs.resourceId : ''
    zoneRedundant: enableRedundancy
    tags: tags
  }
}

module container_app_processor './modules/compute/container-app.bicep' = {
  name: take('module.content-processor-app.${solutionName}', 64)
  params: {
    name: contentProcessorAppName
    location: location
    environmentResourceId: container_app_environment.outputs.resourceId
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
    }
    registries: useExternalRegistry ? null : [
      {
        server: effectiveContainerRegistryEndpoint
        identity: 'system'
      }
    ]
    scaleSettings: {
      minReplicas: enableScalability ? 2 : 1
      maxReplicas: enableScalability ? 3 : 2
    }
    tags: tags
  }
}

module container_app_api './modules/compute/container-app.bicep' = {
  name: take('module.content-processor-api.${solutionName}', 64)
  params: {
    name: contentProcessorApiName
    location: location
    environmentResourceId: container_app_environment.outputs.resourceId
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
    }
    registries: useExternalRegistry ? null : [
      {
        server: effectiveContainerRegistryEndpoint
        identity: 'system'
      }
    ]
    scaleSettings: {
      minReplicas: 0
      maxReplicas: 10
    }
    tags: tags
  }
}

module container_app_web './modules/compute/container-app.bicep' = {
  name: take('module.content-processor-web.${solutionName}', 64)
  params: {
    name: contentProcessorWebName
    location: location
    environmentResourceId: container_app_environment.outputs.resourceId
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
    }
    registries: useExternalRegistry ? null : [
      {
        server: effectiveContainerRegistryEndpoint
        identity: 'system'
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

module container_app_workflow './modules/compute/container-app.bicep' = {
  name: take('module.content-processor-workflow.${solutionName}', 64)
  params: {
    name: contentProcessorWorkflowName
    location: location
    environmentResourceId: container_app_environment.outputs.resourceId
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
    }
    registries: useExternalRegistry ? null : [
      {
        server: effectiveContainerRegistryEndpoint
        identity: 'system'
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
// Module: Identity (Role Assignments)
// ============================================================================

module role_assignments './modules/identity/role-assignments.bicep' = {
  name: take('module.role-assignments.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    containerRegistryName: containerRegistryName
    storageAccountName: storageAccountName
    appConfigurationName: appConfigurationName
    aiServicesName: ai_foundry.outputs.name
    managedIdentityPrincipalId: container_app_processor.outputs.principalId
    contentProcessorAppPrincipalId: container_app_processor.outputs.principalId
    contentProcessorApiPrincipalId: container_app_api.outputs.principalId
    contentProcessorWebPrincipalId: container_app_web.outputs.principalId
    contentProcessorWorkflowPrincipalId: container_app_workflow.outputs.principalId
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('The solution name.')
output SOLUTION_NAME string = solutionName

@description('The name of the Container App used for Web App.')
output CONTAINER_WEB_APP_NAME string = container_app_web.outputs.name

@description('The name of the Container App used for API.')
output CONTAINER_API_APP_NAME string = container_app_api.outputs.name

@description('The FQDN of the Container App Web.')
output CONTAINER_WEB_APP_FQDN string = webAppFqdn

@description('The FQDN of the Container App API.')
output CONTAINER_API_APP_FQDN string = apiAppFqdn

@description('The name of the Container App used for APP.')
output CONTAINER_APP_NAME string = container_app_processor.outputs.name

@description('The name of the Container App used for Workflow.')
output CONTAINER_WORKFLOW_APP_NAME string = container_app_workflow.outputs.name

@description('The system-assigned identity resource ID used for the Container App.')
output CONTAINER_APP_USER_IDENTITY_ID string = container_app_processor.outputs.resourceId

@description('The system-assigned identity Principal ID used for the Container App.')
output CONTAINER_APP_USER_PRINCIPAL_ID string = container_app_processor.outputs.principalId

@description('The name of the Azure Container Registry.')
output CONTAINER_REGISTRY_NAME string = container_registry.outputs.name

@description('The login server of the Azure Container Registry.')
output CONTAINER_REGISTRY_LOGIN_SERVER string = container_registry.outputs.loginServer

@description('The name of the AI Services account that hosts both Azure OpenAI and Content Understanding.')
output CONTENT_UNDERSTANDING_ACCOUNT_NAME string = ai_foundry.outputs.name

@description('The resource group the resources were deployed into.')
output AZURE_RESOURCE_GROUP string = resourceGroup().name
