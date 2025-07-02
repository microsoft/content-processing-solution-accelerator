// Creates Azure dependent resources for Azure AI studio
param solutionName string
param solutionLocation string
param cuLocation string
param deploymentType string
param gptModelName string
param gptModelVersion string
param gptDeploymentCapacity int

// Load the abbrevations file required to name the azure resources.
var abbrs = loadJsonContent('./abbreviations.json')

var aiFoundaryName = '${abbrs.ai.aiFoundry}${solutionName}'
var aiServicesName_cu = '${abbrs.ai.aiServices}${solutionName}-cu'
var location_cu = cuLocation

var location = solutionLocation 
var aiProjectDescription = 'AI foundary project for CPS template'
var aiProjectName = '${abbrs.ai.aiFoundryProject}${solutionName}'
var aiModelDeployments = [
  {
    name: gptModelName
    model: gptModelName
    version: gptModelVersion
    sku: {
      name: deploymentType
      capacity: gptDeploymentCapacity
    }
    raiPolicyName: 'Microsoft.Default'
  }
  // {
  //   name: embeddingModel
  //   model: embeddingModel
  //   sku: {
  //     name: 'Standard'
  //     capacity: embeddingDeploymentCapacity
  //   }
  //   raiPolicyName: 'Microsoft.Default'
  // }
]

resource aiFoundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: aiFoundaryName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  properties: {
    allowProjectManagement: true
    customSubDomainName: aiFoundaryName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true
  }
}

resource aiFoundryProject 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: aiFoundry
  name: aiProjectName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    description: aiProjectDescription
    displayName: aiProjectName
  }
}

resource aiServices_CU 'Microsoft.CognitiveServices/accounts@2021-10-01' = {
  name: aiServicesName_cu
  location: location_cu
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  properties: {
    customSubDomainName: aiServicesName_cu
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true
  }
}

@batchSize(1)
resource aiServicesDeployments 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = [for aiModeldeployment in aiModelDeployments: {
  parent: aiFoundry //aiServices_m
  name: aiModeldeployment.name
  properties: {
    model: {
      format: 'OpenAI'
      name: aiModeldeployment.model
      version: aiModeldeployment.version
    }
    raiPolicyName: aiModeldeployment.raiPolicyName
  }
  sku:{
    name: aiModeldeployment.sku.name
    capacity: aiModeldeployment.sku.capacity
  }
}]

output aiServicesTarget string = aiFoundry.properties.endpoint //aiServices_m.properties.endpoint
output aiServicesCUEndpoint string = aiServices_CU.properties.endpoint //aiServices_m.properties.endpoint
output aiFoundaryName string = aiFoundaryName //aiFoundaryName
output aiServicesId string = aiFoundry.id //aiServices_m.id
output aiServicesCuId string = aiServices_CU.id //aiServices_cu.id
output aiServicePrincipalId string = aiFoundry.identity.principalId
output aiServiceCuPrincipalId string = aiServices_CU.identity.principalId

// output aiInfereceEndpoint string = phiserverless.properties.inferenceEndpoint.uri
output aiProjectPrincipalId string = aiFoundry.identity.principalId
output aiProjectConnectionString string = aiFoundryProject.properties.endpoints['AI Foundry API']
output aiProjectName string = aiFoundryProject.name
output aiProjectId string = aiFoundryProject.id
