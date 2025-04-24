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
 
output createdAcrName string = containerNameCleaned
output createdAcrId string = containerRegistry.id
output acrEndpoint string = containerRegistry.properties.loginServer
 