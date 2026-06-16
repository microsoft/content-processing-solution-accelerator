// ============================================================================
// Module: Role Assignments (centralized — all cross-service + data plane RBAC)
// Description: Content Processing role assignments for Container Apps,
//              Storage, App Configuration, and AI Services.
//              One place to audit "who has access to what".
// ============================================================================

// ============================================================================
// Parameters
// ============================================================================

@description('Solution name suffix for generating unique role assignment GUIDs.')
param solutionName string

// --- Resource Names ---

@description('Name of the Container Registry.')
param containerRegistryName string

@description('Name of the Storage Account.')
param storageAccountName string

@description('Name of the App Configuration store.')
param appConfigurationName string

@description('Name of the AI Services account.')
param aiServicesName string

// --- Identity Principal IDs ---

@description('Principal ID of the system-assigned identity (for ACR pull).')
param managedIdentityPrincipalId string

@description('Principal ID of the Content Processor App.')
param contentProcessorAppPrincipalId string

@description('Principal ID of the Content Processor API.')
param contentProcessorApiPrincipalId string

@description('Principal ID of the Content Processor Web.')
param contentProcessorWebPrincipalId string

@description('Principal ID of the Content Processor Workflow.')
param contentProcessorWorkflowPrincipalId string

// ============================================================================
// Role Definitions
// ============================================================================

var roleDefinitions = {
  acrPull: '7f951dda-4ed3-4680-a7ca-43fe172d538d'
  storageBlobDataContributor: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
  storageQueueDataContributor: '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
  appConfigurationDataReader: '516239f1-63e1-4d78-a4de-a74fb236a071'
  cognitiveServicesOpenAiUser: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
  cognitiveServicesUser: 'a97b65f3-24c7-4388-baec-2e87135dc908'
  azureAiDeveloper: '64702f94-c441-49e6-a78b-ef80e0188fee'
}

// ============================================================================
// Existing Resource References
// ============================================================================

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2025-04-01' existing = {
  name: containerRegistryName
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2025-08-01' existing = {
  name: storageAccountName
}

resource appConfiguration 'Microsoft.AppConfiguration/configurationStores@2023-03-01' existing = {
  name: appConfigurationName
}

resource aiServicesAccount 'Microsoft.CognitiveServices/accounts@2025-12-01' existing = {
  name: aiServicesName
}

// ============================================================================
// 1. CONTAINER REGISTRY — ACR Pull
// ============================================================================

resource acrPullAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistryName, solutionName, 'acr-pull')
  scope: containerRegistry
  properties: {
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.acrPull)
  }
}

// ============================================================================
// 2. STORAGE — Blob Data Contributor
// ============================================================================

resource contentProcessorBlobRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountName, 'app', 'blob')
  scope: storageAccount
  properties: {
    principalId: contentProcessorAppPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageBlobDataContributor)
  }
}

resource contentProcessorApiBlobRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountName, 'api', 'blob')
  scope: storageAccount
  properties: {
    principalId: contentProcessorApiPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageBlobDataContributor)
  }
}

resource contentProcessorWorkflowBlobRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountName, 'workflow', 'blob')
  scope: storageAccount
  properties: {
    principalId: contentProcessorWorkflowPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageBlobDataContributor)
  }
}

// ============================================================================
// 3. STORAGE — Queue Data Contributor
// ============================================================================

resource contentProcessorQueueRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountName, 'app', 'queue')
  scope: storageAccount
  properties: {
    principalId: contentProcessorAppPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageQueueDataContributor)
  }
}

resource contentProcessorApiQueueRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountName, 'api', 'queue')
  scope: storageAccount
  properties: {
    principalId: contentProcessorApiPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageQueueDataContributor)
  }
}

resource contentProcessorWorkflowQueueRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountName, 'workflow', 'queue')
  scope: storageAccount
  properties: {
    principalId: contentProcessorWorkflowPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageQueueDataContributor)
  }
}

// ============================================================================
// 4. APP CONFIGURATION — Data Reader
// ============================================================================

resource contentProcessorAppConfigRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(appConfigurationName, 'app', 'appconfig')
  scope: appConfiguration
  properties: {
    principalId: contentProcessorAppPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.appConfigurationDataReader)
  }
}

resource contentProcessorApiAppConfigRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(appConfigurationName, 'api', 'appconfig')
  scope: appConfiguration
  properties: {
    principalId: contentProcessorApiPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.appConfigurationDataReader)
  }
}

resource contentProcessorWebAppConfigRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(appConfigurationName, 'web', 'appconfig')
  scope: appConfiguration
  properties: {
    principalId: contentProcessorWebPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.appConfigurationDataReader)
  }
}

resource contentProcessorWorkflowAppConfigRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(appConfigurationName, 'workflow', 'appconfig')
  scope: appConfiguration
  properties: {
    principalId: contentProcessorWorkflowPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.appConfigurationDataReader)
  }
}

// ============================================================================
// 5. AI SERVICES — OpenAI User, Cognitive Services User, AI Developer
// ============================================================================

// OpenAI User
resource contentProcessorOpenAiUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServicesName, 'app', 'openai-user')
  scope: aiServicesAccount
  properties: {
    principalId: contentProcessorAppPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesOpenAiUser)
  }
}

resource contentProcessorWorkflowOpenAiUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServicesName, 'workflow', 'openai-user')
  scope: aiServicesAccount
  properties: {
    principalId: contentProcessorWorkflowPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesOpenAiUser)
  }
}

// AI Developer
resource contentProcessorAiDeveloperRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServicesName, 'app', 'ai-developer')
  scope: aiServicesAccount
  properties: {
    principalId: contentProcessorAppPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.azureAiDeveloper)
  }
}

resource contentProcessorWorkflowAiDeveloperRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServicesName, 'workflow', 'ai-developer')
  scope: aiServicesAccount
  properties: {
    principalId: contentProcessorWorkflowPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.azureAiDeveloper)
  }
}

// Cognitive Services User
resource contentProcessorCogUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServicesName, 'app', 'cog-user')
  scope: aiServicesAccount
  properties: {
    principalId: contentProcessorAppPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesUser)
  }
}

resource contentProcessorWorkflowCogUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServicesName, 'workflow', 'cog-user')
  scope: aiServicesAccount
  properties: {
    principalId: contentProcessorWorkflowPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesUser)
  }
}
