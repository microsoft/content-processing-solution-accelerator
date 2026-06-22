// ============================================================================
// main.bicep — Orchestrator
// Description: Pure orchestrator for Content Processing solution
//              All resource names are derived from params — no hardcoded names.
//              This file only calls modules; no inline resource definitions.
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

@description('Optional. Tags to apply to all resources.')
param tags object = {}

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
  Type: 'Non-WAF'
})

// ============================================================================
// Resource Group Tags (matching old infra)
// ============================================================================

resource resourceGroupTags 'Microsoft.Resources/tags@2024-11-01' = {
  name: 'default'
  properties: {
    tags: resourceTags
  }
}

// ========== Monitoring (Log Analytics + Application Insights) ========== //
var useExistingLogAnalytics = !empty(existingLogAnalyticsWorkspaceId)

// ========== Log Analytics module ========== //
module log_analytics './modules/monitoring/log-analytics.bicep' = if (!useExistingLogAnalytics) {
  name: take('module.log-analytics.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: azureAiServiceLocation
  }
  scope: resourceGroup(resourceGroup().name)
}

var logAnalyticsWorkspaceResourceId = useExistingLogAnalytics
  ? existingLogAnalyticsWorkspaceId
  : log_analytics!.outputs.resourceId

// ========== Application Insights module ========== //
module app_insights './modules/monitoring/app-insights.bicep' = {
  name: take('module.app-insights.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: azureAiServiceLocation
    workspaceResourceId: logAnalyticsWorkspaceResourceId
  }
  scope: resourceGroup(resourceGroup().name)
}

// ============================================================================
// Module: AI Services (conditional — skip if using existing project)
// ============================================================================
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

var aiFoundryResourceName = useExistingAIProject ? split(existingFoundryProjectResourceId, '/')[8] : ai_foundry_project!.outputs.name
var aiProjectResourceName = useExistingAIProject ? split(existingFoundryProjectResourceId, '/')[10] : ai_foundry_project!.outputs.projectName
var aiFoundrySubscriptionId = useExistingAIProject ? split(existingFoundryProjectResourceId, '/')[2] : subscription().subscriptionId
var aiFoundryResourceGroupName = useExistingAIProject ? split(existingFoundryProjectResourceId, '/')[4] : resourceGroup().name

// ========== Storage Account module ========== //
module storage_account './modules/data/storage-account.bicep' = {
  name: take('module.storage-account.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: {}
    enableHierarchicalNamespace: true
  }
  scope: resourceGroup(resourceGroup().name)
}

// ========== Cosmos DB module ========== //
module cosmosDBModule './modules/data/cosmos-db-mongo.bicep' = {
  name: take('module.cosmos-db-nosql.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
  }
  scope: resourceGroup(resourceGroup().name)
}

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

// ========== Container Registry ========== //
module containerRegistry './modules/compute/container-registry.bicep' = {
  name: take('module.container-registry.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    sku: 'Standard'
    publicNetworkAccess: 'Enabled'
    tags: tags
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
    logAnalyticsWorkspaceResourceId: logAnalyticsWorkspaceResourceId
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
            value: app_insights!.outputs.connectionString
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
      maxReplicas: 2
      minReplicas: 1
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
            value: app_insights!.outputs.connectionString
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
    scaleSettings: {
      maxReplicas: 2
      minReplicas: 1
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
      maxReplicas: 2
      minReplicas: 1
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
            value: app_insights!.outputs.connectionString
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
      maxReplicas: 2
      minReplicas: 1
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
        value: cosmosDBModule.outputs.connectionString
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
        value: ai_foundry_project!.outputs.cognitiveServicesEndpoint
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
        value: ai_foundry_project!.outputs.cognitiveServicesEndpoint
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
        value: ai_foundry_project!.outputs.cognitiveServicesEndpoint
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
        value: ai_foundry_project!.outputs.cognitiveServicesEndpoint
      }
    ]
    disableLocalAuth: false
  }
}

// ========== Container App API Update Modules ========== //
module containerApp_API_update './modules/compute/container-app.bicep' = {
  name: take('module.container-app-api-update.${solutionSuffix}', 64)
  params: {
    name: 'ca-api-${solutionSuffix}'
    location: location
    environmentResourceId: containerAppEnv.outputs.resourceId
    tags: tags
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
            value: app_insights!.outputs.connectionString
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
  dependsOn:[
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
    containerRegistryResourceId: containerRegistry.outputs.resourceId
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
