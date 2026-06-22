// ============================================================================
// Module: Role Assignments (centralized — all cross-service + data plane RBAC)
// Description: RG-level, cross-service, and data-plane role assignments.
//              One place to audit "who has access to what".
// ============================================================================

// ============================================================================
// Parameters
// ============================================================================

@description('Solution name suffix for generating unique role assignment GUIDs.')
param solutionName string = ''

@description('Whether to use an existing AI project (true) or create new (false).')
param useExistingAIProject bool = false

@description('Resource ID of the existing AI project (for deriving AI Services name/sub/RG).')
param existingFoundryProjectResourceId string = ''

// --- Identity Principal IDs ---

@description('Principal ID of the Container App Processor Service system-assigned identity (empty if not deployed).')
param containerAppServicePrincipalId string = ''

@description('Principal ID of the Container App API Service system-assigned identity (empty if not deployed).')
param containerAppAPIServicePrincipalId string = ''

@description('Principal ID of the Container App Web Service system-assigned identity (empty if not deployed).')
param containerAppWebServicePrincipalId string = ''

@description('Principal ID of the Container App Workflow Service system-assigned identity (empty if not deployed).')
param containerAppWorkFlowServicePrincipalId string = ''

@description('Resource ID of the Container Registry')
param containerRegistryResourceId string = ''

@description('Principal ID of the deploying user (for user access roles).')
param deployerPrincipalId string = ''

@description('Principal type of the deploying user.')
@allowed(['User', 'ServicePrincipal'])
param deployerPrincipalType string = 'User'

// --- Resource References ---

@description('Resource ID of the AI Foundry account (empty if not deployed — new project path).')
param aiFoundryResourceId string = ''

@description('Resource ID of the App Configuration (empty if not deployed).')
param appConfigurationResourceId string = ''

@description('Resource ID of the Storage Account (empty if not deployed).')
param storageAccountResourceId string = ''

// ============================================================================
// Derived Variables
// ============================================================================

var existingAIFoundryName = useExistingAIProject ? split(existingFoundryProjectResourceId, '/')[8] : ''
var existingAIFoundrySubscription = useExistingAIProject ? split(existingFoundryProjectResourceId, '/')[2] : subscription().subscriptionId
var existingAIFoundryResourceGroup = useExistingAIProject ? split(existingFoundryProjectResourceId, '/')[4] : resourceGroup().name

// ============================================================================
// Role Definitions
// ============================================================================

var roleDefinitions = {
  azureAiUser: '53ca6127-db72-4b80-b1b0-d745d6d5456d' // Foundry User
  cognitiveServicesUser: 'a97b65f3-24c7-4388-baec-2e87135dc908'
  cognitiveServicesOpenAIUser: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
  storageBlobDataContributor: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
  storageBlobDataReader: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
  storageQueueDataContributor: '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
  appConfigurationDataReader: '516239f1-63e1-4d78-a4de-a74fb236a071'
  acrPull: '7f951dda-4ed3-4680-a7ca-43fe172d538d'
}

// ============================================================================
// Existing Resource References
// ============================================================================

resource aiFoundryAccount 'Microsoft.CognitiveServices/accounts@2025-12-01' existing = if (!empty(aiFoundryResourceId)) {
  name: last(split(aiFoundryResourceId, '/'))
}

resource appConfiguration 'Microsoft.AppConfiguration/configurationStores@2023-03-01' existing = if (!empty(appConfigurationResourceId)) {
  name: last(split(appConfigurationResourceId, '/'))
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2025-08-01' existing = if (!empty(storageAccountResourceId)) {
  name: last(split(storageAccountResourceId, '/'))
}

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2025-04-01' existing = if (!empty(containerRegistryResourceId)) {
  name: last(split(containerRegistryResourceId, '/'))
}

// ============================================================================
// 1. AI SERVICES ROLE ASSIGNMENTS
//    Cross-service roles scoped to AI Foundry account
// ============================================================================

// ContainerAppWorkflow → Cognitive Services OpenAI User on AI Foundry (new project, same RG)
resource assignOpenAIRoleToContainerAppWorkflow 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingAIProject && !empty(containerAppWorkFlowServicePrincipalId) && !empty(aiFoundryResourceId)) {
  name: guid(solutionName, aiFoundryAccount.id, containerAppWorkFlowServicePrincipalId, roleDefinitions.cognitiveServicesOpenAIUser)
  scope: aiFoundryAccount
  properties: {
    principalId: containerAppWorkFlowServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesOpenAIUser)
    principalType: 'ServicePrincipal'
  }
}

// ContainerAppWorkflow → Cognitive Services OpenAI User on existing AI Foundry (cross-scope)
module assignOpenAIToContainerAppWorkflowExisting './cross-scope-role-assignment.bicep' = if (useExistingAIProject && !empty(containerAppWorkFlowServicePrincipalId)) {
  name: 'assignOpenAIToContainerAppWorkflowExisting'
  scope: resourceGroup(existingAIFoundrySubscription, existingAIFoundryResourceGroup)
  params: {
    principalId: containerAppWorkFlowServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesOpenAIUser)
    roleAssignmentName: guid(solutionName, existingAIFoundryName, containerAppWorkFlowServicePrincipalId, roleDefinitions.cognitiveServicesOpenAIUser)
    aiFoundryName: existingAIFoundryName
  }
}

// ContainerAppWorkflow → Foundry User on AI Foundry (new project, same RG)
resource containerAppWorkflowAiUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingAIProject && !empty(aiFoundryResourceId) && !empty(containerAppWorkFlowServicePrincipalId)) {
  name: guid(solutionName, aiFoundryAccount.id, containerAppWorkFlowServicePrincipalId, roleDefinitions.azureAiUser)
  scope: aiFoundryAccount
  properties: {
    principalId: containerAppWorkFlowServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.azureAiUser)
    principalType: 'ServicePrincipal'
  }
}

// ContainerAppWorkflow → Foundry User on existing AI Foundry (cross-scope)
module containerAppWorkflowAiUserAssignmentExisting './cross-scope-role-assignment.bicep' = if (useExistingAIProject && !empty(containerAppWorkFlowServicePrincipalId)) {
  name: 'assignAiUserRoleToBackendExisting'
  scope: resourceGroup(existingAIFoundrySubscription, existingAIFoundryResourceGroup)
  params: {
    principalId: containerAppWorkFlowServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.azureAiUser)
    roleAssignmentName: guid(solutionName, existingAIFoundryName, containerAppWorkFlowServicePrincipalId, roleDefinitions.azureAiUser)
    aiFoundryName: existingAIFoundryName
  }
}

// ContainerAppWorkflow → Cognitive Services User (new project, same RG)
resource containerAppWorkflowCognitiveServicesUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingAIProject && !empty(aiFoundryResourceId) && !empty(containerAppWorkFlowServicePrincipalId)) {
  name: guid(solutionName, aiFoundryAccount.id, containerAppWorkFlowServicePrincipalId, roleDefinitions.cognitiveServicesUser)
  scope: aiFoundryAccount
  properties: {
    principalId: containerAppWorkFlowServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesUser)
    principalType: 'ServicePrincipal'
  }
}

// ContainerAppWorkflow → Cognitive Services User on existing AI Foundry (cross-scope)
module containerAppWorkflowCognitiveServicesUserAssignmentExisting './cross-scope-role-assignment.bicep' = if (useExistingAIProject && !empty(containerAppWorkFlowServicePrincipalId)) {
  name: 'assignAiUserRoleToBackendExisting'
  scope: resourceGroup(existingAIFoundrySubscription, existingAIFoundryResourceGroup)
  params: {
    principalId: containerAppWorkFlowServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesUser)
    roleAssignmentName: guid(solutionName, existingAIFoundryName, containerAppWorkFlowServicePrincipalId, roleDefinitions.cognitiveServicesUser)
    aiFoundryName: existingAIFoundryName
  }
}

// ContainerAppProcessor → Cognitive Services OpenAI User on AI Foundry (new project, same RG)
resource assignOpenAIRoleToContainerApp 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingAIProject && !empty(containerAppServicePrincipalId) && !empty(aiFoundryResourceId)) {
  name: guid(solutionName, aiFoundryAccount.id, containerAppServicePrincipalId, roleDefinitions.cognitiveServicesOpenAIUser)
  scope: aiFoundryAccount
  properties: {
    principalId: containerAppServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesOpenAIUser)
    principalType: 'ServicePrincipal'
  }
}

// ContainerAppProcessor → Cognitive Services OpenAI User on existing AI Foundry (cross-scope)
module assignOpenAIToContainerAppExisting './cross-scope-role-assignment.bicep' = if (useExistingAIProject && !empty(containerAppServicePrincipalId)) {
  name: 'assignOpenAIToContainerAppExisting'
  scope: resourceGroup(existingAIFoundrySubscription, existingAIFoundryResourceGroup)
  params: {
    principalId: containerAppServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesOpenAIUser)
    roleAssignmentName: guid(solutionName, existingAIFoundryName, containerAppServicePrincipalId, roleDefinitions.cognitiveServicesOpenAIUser)
    aiFoundryName: existingAIFoundryName
  }
}

// ContainerAppProcessor → Foundry User on AI Foundry (new project, same RG)
resource containerAppAiUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingAIProject && !empty(aiFoundryResourceId) && !empty(containerAppServicePrincipalId)) {
  name: guid(solutionName, aiFoundryAccount.id, containerAppServicePrincipalId, roleDefinitions.azureAiUser)
  scope: aiFoundryAccount
  properties: {
    principalId: containerAppServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.azureAiUser)
    principalType: 'ServicePrincipal'
  }
}

// ContainerAppProcessor → Foundry User on existing AI Foundry (cross-scope)
module containerAppAiUserAssignmentExisting './cross-scope-role-assignment.bicep' = if (useExistingAIProject && !empty(containerAppServicePrincipalId)) {
  name: 'assignAiUserRoleToBackendExisting'
  scope: resourceGroup(existingAIFoundrySubscription, existingAIFoundryResourceGroup)
  params: {
    principalId: containerAppServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.azureAiUser)
    roleAssignmentName: guid(solutionName, existingAIFoundryName, containerAppServicePrincipalId, roleDefinitions.azureAiUser)
    aiFoundryName: existingAIFoundryName
  }
}

// ContainerAppProcessor → Cognitive Services User (new project, same RG)
resource containerAppCognitiveServicesUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingAIProject && !empty(aiFoundryResourceId) && !empty(containerAppServicePrincipalId)) {
  name: guid(solutionName, aiFoundryAccount.id, containerAppServicePrincipalId, roleDefinitions.cognitiveServicesUser)
  scope: aiFoundryAccount
  properties: {
    principalId: containerAppServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesUser)
    principalType: 'ServicePrincipal'
  }
}

// ContainerAppProcessor → Cognitive Services User on existing AI Foundry (cross-scope)
module containerAppCognitiveServicesUserAssignmentExisting './cross-scope-role-assignment.bicep' = if (useExistingAIProject && !empty(containerAppServicePrincipalId)) {
  name: 'assignAiUserRoleToBackendExisting'
  scope: resourceGroup(existingAIFoundrySubscription, existingAIFoundryResourceGroup)
  params: {
    principalId: containerAppServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesUser)
    roleAssignmentName: guid(solutionName, existingAIFoundryName, containerAppServicePrincipalId, roleDefinitions.cognitiveServicesUser)
    aiFoundryName: existingAIFoundryName
  }
}

// ============================================================================
// 2. App Configuration ROLE ASSIGNMENTS
//    Container Apps → Container registry
// ============================================================================

// Container App Processor → Acr Pull on Container registry
resource containerAppContainerRegistryAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(containerRegistryResourceId) && !empty(containerAppServicePrincipalId)) {
  name: guid(solutionName, containerRegistry.id, containerAppServicePrincipalId, roleDefinitions.acrPull)
  scope: containerRegistry
  properties: {
    principalId: containerAppServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.acrPull)
    principalType: 'ServicePrincipal'
  }
}

// Container App API → Acr Pull on Container registry
resource containerAppAPIContainerRegistryAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(containerRegistryResourceId) && !empty(containerAppAPIServicePrincipalId)) {
  name: guid(solutionName, containerRegistry.id, containerAppAPIServicePrincipalId, roleDefinitions.acrPull)
  scope: containerRegistry
  properties: {
    principalId: containerAppAPIServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.acrPull)
    principalType: 'ServicePrincipal'
  }
}

// Container App Web → Acr Pull on Container registry
resource containerAppWebContainerRegistryAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(containerRegistryResourceId) && !empty(containerAppWebServicePrincipalId)) {
  name: guid(solutionName, containerRegistry.id, containerAppWebServicePrincipalId, roleDefinitions.acrPull)
  scope: containerRegistry
  properties: {
    principalId: containerAppWebServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.acrPull)
    principalType: 'ServicePrincipal'
  }
}

// Container App Workflow → Acr Pull on Container registry
resource containerAppWorkflowContainerRegistryAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(containerRegistryResourceId) && !empty(containerAppWorkFlowServicePrincipalId)) {
  name: guid(solutionName, containerRegistry.id, containerAppWorkFlowServicePrincipalId, roleDefinitions.acrPull)
  scope: containerRegistry
  properties: {
    principalId: containerAppWorkFlowServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.acrPull)
    principalType: 'ServicePrincipal'
  }
}

// ============================================================================
// 2. App Configuration ROLE ASSIGNMENTS
//    Container Apps → App Configuration
// ============================================================================

// Container App Processor → App Configuration Data Reader on App Configuration
resource containerAppAppConfigurationDataReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(appConfigurationResourceId) && !empty(containerAppServicePrincipalId)) {
  name: guid(solutionName, appConfiguration.id, containerAppServicePrincipalId, roleDefinitions.appConfigurationDataReader)
  scope: appConfiguration
  properties: {
    principalId: containerAppServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.appConfigurationDataReader)
    principalType: 'ServicePrincipal'
  }
}

// Container App API → App Configuration Data Reader on App Configuration
resource containerAppAPIAppConfigurationDataReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(appConfigurationResourceId) && !empty(containerAppAPIServicePrincipalId)) {
  name: guid(solutionName, appConfiguration.id, containerAppAPIServicePrincipalId, roleDefinitions.appConfigurationDataReader)
  scope: appConfiguration
  properties: {
    principalId: containerAppAPIServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.appConfigurationDataReader)
    principalType: 'ServicePrincipal'
  }
}

// Container App Web → App Configuration Data Reader on App Configuration
resource containerAppWebAppConfigurationDataReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(appConfigurationResourceId) && !empty(containerAppWebServicePrincipalId)) {
  name: guid(solutionName, appConfiguration.id, containerAppWebServicePrincipalId, roleDefinitions.appConfigurationDataReader)
  scope: appConfiguration
  properties: {
    principalId: containerAppWebServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.appConfigurationDataReader)
    principalType: 'ServicePrincipal'
  }
}

// Container App Workflow → App Configuration Data Reader on App Configuration
resource containerAppWorkflowAppConfigurationDataReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(appConfigurationResourceId) && !empty(containerAppWorkFlowServicePrincipalId)) {
  name: guid(solutionName, appConfiguration.id, containerAppWorkFlowServicePrincipalId, roleDefinitions.appConfigurationDataReader)
  scope: appConfiguration
  properties: {
    principalId: containerAppWorkFlowServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.appConfigurationDataReader)
    principalType: 'ServicePrincipal'
  }
}

// ============================================================================
// 3. STORAGE ROLE ASSIGNMENTS
//    Container Apps → Storage
// ============================================================================

// ContainerAppWorkflow → Storage Blob Data Contributor
resource containerAppWorkflowStorageBlobDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(storageAccountResourceId) && !empty(containerAppWorkFlowServicePrincipalId)) {
  name: guid(solutionName, storageAccount.id, containerAppWorkFlowServicePrincipalId, roleDefinitions.storageBlobDataContributor)
  scope: storageAccount
  properties: {
    principalId: containerAppWorkFlowServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageBlobDataContributor)
    principalType: 'ServicePrincipal'
  }
}

// ContainerAppWorkflow → Storage Queue Data Contributor
resource containerAppWorkflowStorageQueueDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(storageAccountResourceId) && !empty(containerAppWorkFlowServicePrincipalId)) {
  name: guid(solutionName, storageAccount.id, containerAppWorkFlowServicePrincipalId, roleDefinitions.storageQueueDataContributor)
  scope: storageAccount
  properties: {
    principalId: containerAppWorkFlowServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageQueueDataContributor)
    principalType: 'ServicePrincipal'
  }
}

// ContainerAppProcessor → Storage Blob Data Contributor
resource containerAppStorageBlobDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(storageAccountResourceId) && !empty(containerAppServicePrincipalId)) {
  name: guid(solutionName, storageAccount.id, containerAppServicePrincipalId, roleDefinitions.storageBlobDataContributor)
  scope: storageAccount
  properties: {
    principalId: containerAppServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageBlobDataContributor)
    principalType: 'ServicePrincipal'
  }
}

// ContainerAppProcessor → Storage Queue Data Contributor
resource containerAppStorageQueueDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(storageAccountResourceId) && !empty(containerAppServicePrincipalId)) {
  name: guid(solutionName, storageAccount.id, containerAppServicePrincipalId, roleDefinitions.storageQueueDataContributor)
  scope: storageAccount
  properties: {
    principalId: containerAppServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageQueueDataContributor)
    principalType: 'ServicePrincipal'
  }
}

// ContainerAppAPI → Storage Blob Data Contributor
resource containerAppAPIStorageBlobDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(storageAccountResourceId) && !empty(containerAppAPIServicePrincipalId)) {
  name: guid(solutionName, storageAccount.id, containerAppAPIServicePrincipalId, roleDefinitions.storageBlobDataContributor)
  scope: storageAccount
  properties: {
    principalId: containerAppAPIServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageBlobDataContributor)
    principalType: 'ServicePrincipal'
  }
}

// ContainerAppAPI → Storage Queue Data Contributor
resource containerAppAPIStorageQueueDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(storageAccountResourceId) && !empty(containerAppAPIServicePrincipalId)) {
  name: guid(solutionName, storageAccount.id, containerAppAPIServicePrincipalId, roleDefinitions.storageQueueDataContributor)
  scope: storageAccount
  properties: {
    principalId: containerAppAPIServicePrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageQueueDataContributor)
    principalType: 'ServicePrincipal'
  }
}

// ============================================================================
// 5. DEPLOYER (USER) ROLE ASSIGNMENTS
//    Deploying user → AI Services, App Configuration, Storage (Bicep-only)
// ============================================================================

// Deploying User → Storage Blob Data Contributor
resource deployerStorageBlobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerPrincipalId) && !empty(storageAccountResourceId)) {
  scope: storageAccount
  name: guid(solutionName, storageAccount.id, deployerPrincipalId, roleDefinitions.storageBlobDataContributor)
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageBlobDataContributor)
    principalType: deployerPrincipalType
  }
}

// Deploying User → Storage Queue Data Contributor
resource deployerStorageQueueDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerPrincipalId) && !empty(storageAccountResourceId)) {
  scope: storageAccount
  name: guid(solutionName, storageAccount.id, deployerPrincipalId, roleDefinitions.storageQueueDataContributor)
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageQueueDataContributor)
    principalType: deployerPrincipalType
  }
}

// Deploying User → App Configuration Data Reader on App Configuration
resource deployerAppConfigurationDataReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(appConfigurationResourceId) && !empty(deployerPrincipalId)) {
  name: guid(solutionName, appConfiguration.id, deployerPrincipalId, roleDefinitions.appConfigurationDataReader)
  scope: appConfiguration
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.appConfigurationDataReader)
    principalType: deployerPrincipalType
  }
}

// Deploying User → Cognitive Services OpenAI User on AI Foundry (new project, same RG)
resource assignOpenAIRoleToDeployer 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingAIProject && !empty(deployerPrincipalId) && !empty(aiFoundryResourceId)) {
  name: guid(solutionName, aiFoundryAccount.id, deployerPrincipalId, roleDefinitions.cognitiveServicesOpenAIUser)
  scope: aiFoundryAccount
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesOpenAIUser)
    principalType: deployerPrincipalType
  }
}

// Deploying User → Foundry User on AI Foundry (new project, same RG)
resource DeployerAiUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingAIProject && !empty(aiFoundryResourceId) && !empty(deployerPrincipalId)) {
  name: guid(solutionName, aiFoundryAccount.id, deployerPrincipalId, roleDefinitions.azureAiUser)
  scope: aiFoundryAccount
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.azureAiUser)
    principalType: deployerPrincipalType
  }
}

// Deploying User → Cognitive Services User (new project, same RG)
resource DeployerCognitiveServicesUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingAIProject && !empty(aiFoundryResourceId) && !empty(deployerPrincipalId)) {
  name: guid(solutionName, aiFoundryAccount.id, deployerPrincipalId, roleDefinitions.cognitiveServicesUser)
  scope: aiFoundryAccount
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesUser)
    principalType: deployerPrincipalType
  }
}

// NOTE: Deployer roles on existing AI Foundry (cross-scope) not assigned to avoid conflicts when the deployer already has the roles.
