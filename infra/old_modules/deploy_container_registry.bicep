// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.
targetScope = 'resourceGroup'

param environmentName string
 
var uniqueId = toLower(uniqueString(subscription().id, environmentName, resourceGroup().location))
var solutionName = 'cps-${padLeft(take(uniqueId, 12), 12, '0')}'
 
var containerNameCleaned = replace('cr${solutionName }', '-', '')
 
@description('Provide a location for the registry.')
param location string = resourceGroup().location
 
@description('Provide a tier of your Azure Container Registry.')
param acrSku string = 'Basic'

@description('List of Principal Ids to which ACR pull role assignment is required')
param acrPullPrincipalIds array = []
 
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2021-09-01' = {
  name: containerNameCleaned
  location: location
  sku: {
    name: acrSku
  }
  properties: {
    publicNetworkAccess: 'Enabled'
    zoneRedundancy: 'Disabled'
  }
}

// Add Role assignments for required principal id's
resource acrPullRoleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for principalId in acrPullPrincipalIds: {
  name: guid(principalId, 'acrpull')
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '7f951dda-4ed3-4680-a7ca-43fe172d538d'
    )
    principalId: principalId
  }
}]
 
output createdAcrName string = containerNameCleaned
output createdAcrId string = containerRegistry.id
output acrEndpoint string = containerRegistry.properties.loginServer
 