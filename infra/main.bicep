// ========== main.bicep ========== //
targetScope = 'resourceGroup'

@minLength(3)
@maxLength(20)
@description('A unique prefix for all resources in this deployment. This should be 3-20 characters long:')
param environmentName string

var uniqueId = toLower(uniqueString(subscription().id, environmentName, resourceGroup().location))
var solutionPrefix = 'cps-${padLeft(take(uniqueId, 12), 12, '0')}'

@description('Location used for Azure Cosmos DB, Azure Container App deployment')
param secondaryLocation string = 'EastUs2'

@minLength(1)
@description('Location for the Azure AI Content Understanding service deployment:')
@allowed(['WestUS', 'SwedenCentral', 'AustraliaEast'])
@metadata({
  azd: {
    type: 'location'
  }
})
param contentUnderstandingLocation string = 'WestUS'

@metadata({azd: {
    type: 'location'
    usageName: [
      'OpenAI.GlobalStandard.gpt-4o,100'
    ]
  }
})
param aiDeploymentsLocation string

@minLength(1)
@description('GPT model deployment type:')
@allowed([
  'Standard'
  'GlobalStandard'
])
param deploymentType string = 'GlobalStandard'

@description('Name of the GPT model to deploy:')
param gptModelName string = 'gpt-4o'

@description('Version of the GPT model to deploy:')
param gptModelVersion string = '2024-08-06'

@minValue(10)
@description('Capacity of the GPT deployment:')
// You can increase this, but capacity is limited per model/region, so you will get errors if you go over
// https://learn.microsoft.com/en-us/azure/ai-services/openai/quotas-limits
param gptDeploymentCapacity int = 100

@description('Minimum number of replicas to be added for Container App')
param minReplicaContainerApp int = 1

@description('Maximum number of replicas to be added for Container App')
param maxReplicaContainerApp int = 1

@description('Minimum number of replicas to be added for Container Api')
param minReplicaContainerApi int = 1

@description('Maximum number of replicas to be added for Container Api')
param maxReplicaContainerApi int = 1

@description('Minimum number of replicas to be added for Container Web App')
param minReplicaContainerWeb int = 1

@description('Maximum number of replicas to be added for Container Web App')
param maxReplicaContainerWeb int = 1

@description('Optional: Existing Log Analytics Workspace Resource ID')
param existingLogAnalyticsWorkspaceId string = ''

param imageTag string = 'latest'

var containerImageEndPoint = 'cpscontainerreg.azurecr.io'
var resourceGroupLocation = resourceGroup().location

// Load the abbrevations file required to name the azure resources.
var abbrs = loadJsonContent('./abbreviations.json')

// ========== Resource Group Tag ========== //
resource resourceGroupTags 'Microsoft.Resources/tags@2021-04-01' = {
  name: 'default'
  properties: {
    tags: {
      TemplateName: 'Content Processing'
    }
  }
}

// ========== Managed Identity ========== //
module managedIdentityModule 'deploy_managed_identity.bicep' = {
  name: 'deploy_managed_identity'
  params: {
    solutionName: solutionPrefix
    miName: '${abbrs.security.managedIdentity}${solutionPrefix}'
    solutionLocation: resourceGroupLocation
  }
  scope: resourceGroup(resourceGroup().name)
}

// ========== Key Vault Module ========== //
module kvault 'deploy_keyvault.bicep' = {
  name: 'deploy_keyvault'
  params: {
    solutionLocation: resourceGroupLocation
    keyvaultName: '${abbrs.security.keyVault}${solutionPrefix}'
    managedIdentityObjectId: managedIdentityModule.outputs.managedIdentityOutput.objectId
  }
  scope: resourceGroup(resourceGroup().name)
}

// ========== Application insights ========== //
module applicationInsights 'deploy_app_insights.bicep' = {
  name: 'deploy_app_insights'
  params: {
    existingLogAnalyticsWorkspaceId: existingLogAnalyticsWorkspaceId
    applicationInsightsName: '${abbrs.managementGovernance.applicationInsights}${solutionPrefix}'
    logAnalyticsWorkspaceName: '${abbrs.managementGovernance.logAnalyticsWorkspace}${solutionPrefix}'
  }
}

// // ========== Container Registry ========== //
// module containerRegistry 'deploy_container_registry.bicep' = {
//   name: 'deploy_container_registry'
//   params: {
//     environmentName: environmentName
//   }
// }

// ========== Storage Account ========== //
module storage 'deploy_storage_account.bicep' = {
  name: 'deploy_storage_account'
  params: {
    solutionLocation: resourceGroupLocation
    managedIdentityObjectId: managedIdentityModule.outputs.managedIdentityOutput.objectId
    saName: '${abbrs.storage.storageAccount}${solutionPrefix}'
  }
}

// ========== AI Foundry and related resources ========== //
module aifoundry 'deploy_ai_foundry.bicep' = {
  name: 'deploy_ai_foundry'
  params: {
    solutionName: solutionPrefix
    solutionLocation: aiDeploymentsLocation
    cuLocation: contentUnderstandingLocation
    deploymentType: deploymentType
    gptModelName: gptModelName
    gptModelVersion: gptModelVersion
    gptDeploymentCapacity: gptDeploymentCapacity
  }
  scope: resourceGroup(resourceGroup().name)
}

module containerAppEnv './container_app/deploy_container_app_env.bicep' = {
  name: 'deploy_container_app_env'
  params: {
    solutionName: solutionPrefix
    containerEnvName: '${abbrs.containers.containerAppsEnvironment}${solutionPrefix}'
    location: secondaryLocation
    logAnalyticsWorkspaceName: applicationInsights.outputs.logAnalyticsWorkspaceName
    logAnalyticsWorkspaceResourceGroup: applicationInsights.outputs.logAnalyticsWorkspaceResourceGroup
    logAnalyticsWorkspaceSubscription: applicationInsights.outputs.logAnalyticsWorkspaceSubscription
  }
}

module containerApps './container_app/deploy_container_app_api_web.bicep' = {
  name: 'deploy_container_app_api_web'
  params: {
    solutionName: solutionPrefix
    location: secondaryLocation
    appConfigEndPoint: ''
    containerAppApiEndpoint: ''
    containerAppWebEndpoint: ''
    azureContainerRegistry: containerImageEndPoint
    containerAppEnvId: containerAppEnv.outputs.containerEnvId
    containerRegistryReaderId: containerAppEnv.outputs.containerRegistryReaderId
    minReplicaContainerApp: minReplicaContainerApp
    maxReplicaContainerApp: maxReplicaContainerApp
    minReplicaContainerApi: minReplicaContainerApi
    maxReplicaContainerApi: maxReplicaContainerApi
    minReplicaContainerWeb: minReplicaContainerWeb
    maxReplicaContainerWeb: maxReplicaContainerWeb
    imageTag: 'latest'
  }
}

// ========== Cosmos Database for Mongo DB ========== //
module cosmosdb './deploy_cosmos_db.bicep' = {
  name: 'deploy_cosmos_db'
  params: {
    cosmosAccountName: '${abbrs.databases.cosmosDBDatabase}${solutionPrefix}'
    solutionLocation: secondaryLocation
    kind: 'MongoDB'
  }
}

// ========== App Configuration ========== //
module appconfig 'deploy_app_config_service.bicep' = {
  name: 'deploy_app_config_service'
  scope: resourceGroup(resourceGroup().name)
  params: {
    appConfigName: '${abbrs.developerTools.appConfigurationStore}${solutionPrefix}'
    storageBlobUrl: storage.outputs.storageBlobUrl
    storageQueueUrl: storage.outputs.storageQueueUrl
    openAIEndpoint: aifoundry.outputs.aiServicesTarget
    contentUnderstandingEndpoint: aifoundry.outputs.aiServicesCUEndpoint
    gptModelName: gptModelName
    keyVaultId: kvault.outputs.keyvaultId
    aiProjectConnectionString: aifoundry.outputs.aiProjectConnectionString
    cosmosDbName: cosmosdb.outputs.cosmosAccountName
  }
}

// ========== Role Assignments ========== //
module roleAssignments 'deploy_role_assignments.bicep' = {
  name: 'deploy_role_assignments'
  params: {
    appConfigResourceId: appconfig.outputs.appConfigId
    conainerAppPrincipalIds: [
      containerApps.outputs.containerAppPrincipalId
      containerApps.outputs.containerAppApiPrincipalId
      containerApps.outputs.containerAppWebPrincipalId
    ]
    storageResourceId: storage.outputs.storageId
    storagePrincipalId: storage.outputs.storagePrincipalId
    containerApiPrincipalId: containerApps.outputs.containerAppApiPrincipalId
    containerAppPrincipalId: containerApps.outputs.containerAppPrincipalId
    aiServiceCUId: aifoundry.outputs.aiServicesCuId
    aiServiceId: aifoundry.outputs.aiServicesId
  }
}

module updateContainerApp './container_app/deploy_container_app_api_web.bicep' = {
  name: 'deploy_update_container_app_update'
  params: {
    solutionName: solutionPrefix
    location: secondaryLocation
    azureContainerRegistry: containerImageEndPoint
    appConfigEndPoint: appconfig.outputs.appConfigEndpoint
    containerAppEnvId: containerAppEnv.outputs.containerEnvId
    containerRegistryReaderId: containerAppEnv.outputs.containerRegistryReaderId
    containerAppWebEndpoint: containerApps.outputs.containweAppWebEndPoint
    containerAppApiEndpoint: containerApps.outputs.containweAppApiEndPoint
    minReplicaContainerApp: minReplicaContainerApp
    maxReplicaContainerApp: maxReplicaContainerApp
    minReplicaContainerApi: minReplicaContainerApi
    maxReplicaContainerApi: maxReplicaContainerApi
    minReplicaContainerWeb: minReplicaContainerWeb
    maxReplicaContainerWeb: maxReplicaContainerWeb
    imageTag: imageTag
  }
  dependsOn: [roleAssignments]
}

output CONTAINER_WEB_APP_NAME string = containerApps.outputs.containerAppWebName
output CONTAINER_API_APP_NAME string = containerApps.outputs.containerAppApiName
output CONTAINER_WEB_APP_FQDN string = containerApps.outputs.containweAppWebEndPoint
output CONTAINER_APP_NAME string = containerApps.outputs.containerAppName
output CONTAINER_API_APP_FQDN string = containerApps.outputs.containweAppApiEndPoint
output CONTAINER_APP_USER_IDENTITY_ID string = containerAppEnv.outputs.containerRegistryReaderId
output CONTAINER_APP_USER_PRINCIPAL_ID string = containerAppEnv.outputs.containerRegistryReaderPrincipalId
output AZURE_ENV_IMAGETAG string = imageTag
output SOLUTION_NAME string = solutionPrefix
