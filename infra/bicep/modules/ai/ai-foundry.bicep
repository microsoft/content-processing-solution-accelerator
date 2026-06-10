// ============================================================================
// Module: Azure AI Foundry (Cognitive Services Account)
// Description: Deploys an Azure AI Services account with AI Foundry capabilities.
// ============================================================================

@description('Required. Name of the AI Services account.')
param name string

@description('Required. Azure region for the resource.')
param location string

@description('Optional. Principal IDs to assign Cognitive Services OpenAI User role.')
param principalIds array = []

@description('Optional. Whether public network access is allowed.')
@allowed([
  'Enabled'
  'Disabled'
])
param publicNetworkAccess string = 'Enabled'

@description('Optional. Tags to apply to the resource.')
param tags object = {}

resource aiServices 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: name
  location: location
  tags: tags
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: name
    publicNetworkAccess: publicNetworkAccess
    disableLocalAuth: true
    allowProjectManagement: true
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: publicNetworkAccess == 'Enabled' ? 'Allow' : 'Deny'
    }
  }
}

// Assign Cognitive Services OpenAI User role to provided principal IDs
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for principalId in principalIds: {
    name: guid(aiServices.id, principalId, 'Cognitive Services OpenAI User')
    scope: aiServices
    properties: {
      principalId: principalId
      roleDefinitionId: subscriptionResourceId(
        'Microsoft.Authorization/roleDefinitions',
        'a97b65f3-24c7-4388-baec-2e87135dc908' // Cognitive Services OpenAI User
      )
      principalType: 'ServicePrincipal'
    }
  }
]

@description('The name of the deployed AI Services account.')
output name string = aiServices.name

@description('The resource ID of the AI Services account.')
output resourceId string = aiServices.id

@description('The endpoint of the AI Services account.')
output endpoint string = aiServices.properties.endpoint

@description('The principal ID of the system-assigned managed identity.')
output systemAssignedPrincipalId string = aiServices.identity.principalId
