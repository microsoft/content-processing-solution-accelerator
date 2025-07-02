param conainerAppPrincipalIds array // List of user/service principal IDs
param containerApiPrincipalId string // API principal ID
param containerAppPrincipalId string // APP principal ID

param appConfigResourceId string // Resource ID of the App Configuration instance
param storageResourceId string // Resource ID of the Storage account
param storagePrincipalId string // Resource ID of the Storage account

param aiServiceCUId string // Resource ID of the Azure AI Content Understanding Service
param aiServiceId string // Resource ID of the Azure Open AI service

resource appConfigDataReader 'Microsoft.Authorization/roleDefinitions@2018-01-01-preview' existing = {
  scope: resourceGroup()
  name: '516239f1-63e1-4d78-a4de-a74fb236a071'
}

resource storageBlobDataContributor 'Microsoft.Authorization/roleDefinitions@2018-01-01-preview' existing = {
  scope: resourceGroup()
  name: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
}

resource storageQueueDataContributor 'Microsoft.Authorization/roleDefinitions@2018-01-01-preview' existing = {
  scope: resourceGroup()
  name: '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
}

resource cognitiveServicesUserRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: 'a97b65f3-24c7-4388-baec-2e87135dc908'
  scope: resourceGroup()
}

resource cognitiveServicesOpenAIUserRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
  scope: resourceGroup()
}

resource roleAssignments 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = [
  for principalId in conainerAppPrincipalIds: {
    name: guid('${appConfigResourceId}-${principalId}', appConfigDataReader.id)
    scope: resourceGroup()
    properties: {
      roleDefinitionId: appConfigDataReader.id
      principalId: principalId
    }
  }
]

resource storageQueueRoleAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(storageResourceId, storagePrincipalId, storageQueueDataContributor.id)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: storageQueueDataContributor.id
    principalId: storagePrincipalId
  }
}

resource storageBlobRoleAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(storageResourceId, storagePrincipalId, storageBlobDataContributor.id)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: storageBlobDataContributor.id
    principalId: storagePrincipalId
  }
}

resource containerApiQueueRoleAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(storageResourceId, containerApiPrincipalId, storageQueueDataContributor.id)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: storageQueueDataContributor.id
    principalId: containerApiPrincipalId
  }
}

resource containerApiBlobRoleAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(storageResourceId, containerApiPrincipalId, storageBlobDataContributor.id)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: storageBlobDataContributor.id
    principalId: containerApiPrincipalId
  }
}

resource containerAppQueueRoleAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(storageResourceId, containerAppPrincipalId, storageQueueDataContributor.id)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: storageQueueDataContributor.id
    principalId: containerAppPrincipalId
  }
}

resource containerAppBlobRoleAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(storageResourceId, containerAppPrincipalId, storageBlobDataContributor.id)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: storageBlobDataContributor.id
    principalId: containerAppPrincipalId
  }
}

resource cognitiveServicesOpenAIApiRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: resourceGroup()
  name: guid(aiServiceId, cognitiveServicesOpenAIUserRole.id, 'api')
  properties: {
    principalId: containerApiPrincipalId
    roleDefinitionId: cognitiveServicesOpenAIUserRole.id
    principalType: 'ServicePrincipal'
  }
}

resource cognitiveServicesOpenAIUAppRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: resourceGroup()
  name: guid(aiServiceId, cognitiveServicesOpenAIUserRole.id, 'app')
  properties: {
    principalId: containerAppPrincipalId
    roleDefinitionId: cognitiveServicesOpenAIUserRole.id
    principalType: 'ServicePrincipal'
  }
}

resource cognitiveServicesUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: resourceGroup()
  name: guid(aiServiceCUId, cognitiveServicesUserRole.id)
  properties: {
    principalId: containerAppPrincipalId
    roleDefinitionId: cognitiveServicesUserRole.id
    principalType: 'ServicePrincipal'
  }
}
