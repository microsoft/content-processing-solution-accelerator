@description('The name of the environment. Use alphanumeric characters only.')
param name string

@description('Specifies the location for all the Azure resources. Defaults to the location of the resource group.')
param location string

@description('Foundry Account Name')
param aiServicesName string

@description('Name of the first project')
param defaultProjectName string = name
param defaultProjectDisplayName string = name
param defaultProjectDescription string = 'This is a sample project for AI Foundry.'

resource foundryAccount 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: aiServicesName
  }

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  name: defaultProjectName
  parent: foundryAccount
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: defaultProjectDisplayName
    description: defaultProjectDescription
  }
}

output projectName string = project.name
output projectEndpoint string = project.properties.endpoints['AI Foundry API']
