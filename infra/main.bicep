// ========== main.bicep ========== //
targetScope = 'resourceGroup'

metadata name = 'Content Processing Solution Accelerator'
metadata description = 'Bicep template to deploy the Content Processing Solution Accelerator with AVM compliance.'

// ========== Parameters ========== //
@description('Required. Name of the solution to deploy.')
param solutionName string = 'cps'
@description('Optional. Location for all Resources.')
param location string = resourceGroup().location

@minLength(1)
@description('Location for the Azure AI Content Understanding service deployment:')
@allowed(['WestUS', 'SwedenCentral', 'AustraliaEast'])
@metadata({
  azd: {
    type: 'location'
  }
})
param contentUnderstandingLocation string = 'WestUS'

@metadata({
  azd: {
    type: 'location'
    usageName: [
      'OpenAI.GlobalStandard.gpt-4o,100'
    ]
  }
})
param aiServiceLocation string

@description('Optional. Type of GPT deployment to use: Standard | GlobalStandard.')
@minLength(1)
@allowed([
  'Standard'
  'GlobalStandard'
])
param deploymentType string = 'GlobalStandard'

@description('Optional. Name of the GPT model to deploy: gpt-4o-mini | gpt-4o | gpt-4.')
param gptModelName string = 'gpt-4o'

@minLength(1)
@description('Optional. Version of the GPT model to deploy:.')
@allowed([
  '2024-08-06'
])
param gptModelVersion string = '2024-08-06'

@minValue(1)
@description('Required. Capacity of the GPT deployment: (minimum 10).')
param gptDeploymentCapacity int = 100

@description('Optional. Location used for Azure Cosmos DB, Azure Container App deployment.')
param secondaryLocation string = (location == 'eastus2') ? 'westus2' : 'eastus2'

@description('Optional. The public container image endpoint.')
param publicContainerImageEndpoint string = 'cpscontainerreg.azurecr.io'

@description('Optional. The resource group location.')
param resourceGroupLocation string = resourceGroup().location

@description('Optional. The resource name format string.')
param resourceNameFormatString string = '{0}avm-cps'

@description('Optional. Enable private networking for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enablePrivateNetworking bool = false

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('Optional. Enable monitoring applicable resources, aligned with the Well Architected Framework recommendations. This setting enables Application Insights and Log Analytics and configures all the resources applicable resources to send logs. Defaults to false.')
param enableMonitoring bool =  false

@description('Optional. Enable redundancy for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enableRedundancy bool = false

@description('Optional. Enable scalability for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enableScalability bool = false

@description('Optional. Tags to be applied to the resources.')
param tags resourceInput<'Microsoft.Resources/resourceGroups@2025-04-01'>.tags = {
  app: 'Content Processing Solution Accelerator'
  location: resourceGroup().location
}

@description('Optional: Existing Log Analytics Workspace Resource ID')
param existingLogAnalyticsWorkspaceId string = '' 

@description('Use this parameter to use an existing AI project resource ID')
param existingFoundryProjectResourceId string = ''

@description('Optional. Size of the Jumpbox Virtual Machine when created. Set to custom value if enablePrivateNetworking is true.')
param vmSize string? 

@description('Optional. Admin username for the Jumpbox Virtual Machine. Set to custom value if enablePrivateNetworking is true.')
@secure()
param vmAdminUsername string?

@description('Optional. Admin password for the Jumpbox Virtual Machine. Set to custom value if enablePrivateNetworking is true.')
@secure()
param vmAdminPassword string?

@maxLength(5)
@description('Optional. A unique text value for the solution. This is used to ensure resource names are unique for global resources. Defaults to a 5-character substring of the unique string generated from the subscription ID, resource group name, and solution name.')
param solutionUniqueText string = substring(uniqueString(subscription().id, resourceGroup().name, solutionName), 0, 5)

var solutionSuffix = toLower(trim(replace(
  replace(
    replace(replace(replace(replace('${solutionName}${solutionUniqueText}', '-', ''), '_', ''), '.', ''), '/', ''),
    ' ',
    ''
  ),
  '*',
  ''
)))
// ============== //
// Resources      //
// ============== //

var existingProjectResourceId = trim(existingFoundryProjectResourceId)

// ========== AVM Telemetry ========== //
#disable-next-line no-deployments-resources
resource avmTelemetry 'Microsoft.Resources/deployments@2024-03-01' = if (enableTelemetry) {
  //name: '46d3xbcp.ptn.sa-contentprocessing-${replace(replace(deployment().name, ' ', '-'), '_', '-')}.${substring(uniqueString(deployment().name, location), 0, 4)}'
  name: take(
    '46d3xbcp.ptn.sa-contentprocessing.${replace('-..--..-', '.', '-')}.${substring(uniqueString(deployment().name, location), 0, 4)}',
    64
  )
  properties: {
    mode: 'Incremental'
    template: {
      '$schema': 'https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#'
      contentVersion: '1.0.0.0'
      resources: []
      outputs: {
        telemetry: {
          type: 'String'
          value: 'For more information, see https://aka.ms/avm/TelemetryInfo'
        }
      }
    }
  }
}

// ========== Virtual Network ========== //
module virtualNetwork './modules/virtualNetwork.bicep' = if (enablePrivateNetworking) {
  name: take('module.virtual-network.${solutionSuffix}', 64)
  params: {
    name: 'vnet-${solutionSuffix}'
    addressPrefixes: ['10.0.0.0/8']
    location: resourceGroupLocation
    tags: tags
    logAnalyticsWorkspaceId: enableMonitoring ? logAnalyticsWorkspace!.outputs.resourceId : ''
    resourceSuffix: solutionSuffix
    enableTelemetry: enableTelemetry
  }
}

// Azure Bastion Host
var bastionHostName = 'bas-${solutionSuffix}'
module bastionHost 'br/public:avm/res/network/bastion-host:0.6.1' = if (enablePrivateNetworking) {
  name: take('avm.res.network.bastion-host.${bastionHostName}', 64)
  params: {
    name: bastionHostName
    skuName: 'Standard'
    location: resourceGroupLocation
    virtualNetworkResourceId: virtualNetwork!.outputs.resourceId
    diagnosticSettings: enableMonitoring ? [
      {
        name: 'bastionDiagnostics'
        workspaceResourceId: logAnalyticsWorkspace!.outputs.resourceId
        logCategoriesAndGroups: [
          {
            categoryGroup: 'allLogs'
            enabled: true
          }
        ]
      }
    ] : null
    tags: tags
    enableTelemetry: enableTelemetry
    publicIPAddressObject: {
      name: 'pip-${bastionHostName}'
      zones: []
    }
  }
}
// Jumpbox Virtual Machine
var jumpboxVmName = take('vm-jumpbox-${solutionSuffix}', 15)
module jumpboxVM 'br/public:avm/res/compute/virtual-machine:0.15.0' = if (enablePrivateNetworking) {
  name: take('avm.res.compute.virtual-machine.${jumpboxVmName}', 64)
  params: {
    name: take(jumpboxVmName, 15) // Shorten VM name to 15 characters to avoid Azure limits
    vmSize: vmSize ?? 'Standard_DS2_v2'
    location: resourceGroupLocation
    adminUsername: vmAdminUsername ?? 'JumpboxAdminUser'
    adminPassword: vmAdminPassword ?? 'JumpboxAdminP@ssw0rd1234!'
    tags: tags
    zone: 0
    imageReference: {
      offer: 'WindowsServer'
      publisher: 'MicrosoftWindowsServer'
      sku: '2019-datacenter'
      version: 'latest'
    }
    osType: 'Windows'
    osDisk: {
      name: 'osdisk-${jumpboxVmName}'
      managedDisk: {
        storageAccountType: 'Standard_LRS'
      }
    }
    encryptionAtHost: false // Some Azure subscriptions do not support encryption at host
    nicConfigurations: [
      {
        name: 'nic-${jumpboxVmName}'
        ipConfigurations: [
          {
            name: 'ipconfig1'
            subnetResourceId: virtualNetwork!.outputs.adminSubnetResourceId
          }
        ]
        diagnosticSettings: enableMonitoring ? [
          {
            name: 'jumpboxDiagnostics'
            workspaceResourceId: logAnalyticsWorkspace!.outputs.resourceId
            logCategoriesAndGroups: [
              {
                categoryGroup: 'allLogs'
                enabled: true
              }
            ]
            metricCategories: [
              {
                category: 'AllMetrics'
                enabled: true
              }
            ]
          }
        ] : null
      }
    ]
    enableTelemetry: enableTelemetry
  }
}

// ========== Private DNS Zones ========== //
var privateDnsZones = [
  'privatelink.cognitiveservices.azure.com'
  'privatelink.openai.azure.com'
  'privatelink.services.ai.azure.com'
  'privatelink.contentunderstanding.ai.azure.com'
  'privatelink.blob.${environment().suffixes.storage}'
  'privatelink.queue.${environment().suffixes.storage}'
  'privatelink.file.${environment().suffixes.storage}'
  'privatelink.api.azureml.ms'
  'privatelink.notebooks.azure.net'
  'privatelink.mongo.cosmos.azure.com'
  'privatelink.azconfig.io'
  'privatelink.vaultcore.azure.net'
  'privatelink.azurecr.io'
]

// DNS Zone Index Constants
var dnsZoneIndex = {
  cognitiveServices: 0
  openAI: 1
  aiServices: 2
  contentUnderstanding: 3
  storageBlob: 4
  storageQueue: 5
  storageFile: 6
  aiFoundry: 7
  notebooks: 8
  cosmosDB: 9
  appConfig: 10
  keyVault: 11
  containerRegistry: 12
}

@batchSize(5)
module avmPrivateDnsZones 'br/public:avm/res/network/private-dns-zone:0.7.1' = [
  for (zone, i) in privateDnsZones: if (enablePrivateNetworking) {
    name: take('avm.res.network.private-dns-zone.${split(zone, '.')[1]}', 64)
    params: {
      name: zone
      tags: tags
      enableTelemetry: enableTelemetry
      virtualNetworkLinks: [{ virtualNetworkResourceId: virtualNetwork.outputs.resourceId }]
    }
  }
]


// ============== //
// Resources      //
// ============== //

// ========== Log Analytics & Application Insights ========== //
module logAnalyticsWorkspace 'modules/log-analytics-workspace.bicep' = if (enableMonitoring) {
  name: take('module.log-analytics-workspace.${solutionSuffix}', 64)
  params: {
    name: 'log-${solutionSuffix}'
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    existingLogAnalyticsWorkspaceId: existingLogAnalyticsWorkspaceId
  }
}

module applicationInsights 'br/public:avm/res/insights/component:0.6.0' = if (enableMonitoring) {
  name: take('avm.res.insights.component.${solutionSuffix}', 64)
  params: {
    name: 'appi-${solutionSuffix}'
    location: location
    workspaceResourceId: enableMonitoring ? logAnalyticsWorkspace!.outputs.resourceId : ''
    diagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspace!.outputs.resourceId }] : null
    tags: tags
    enableTelemetry: enableTelemetry
    disableLocalAuth: true
  }
}
@description('Tag, Created by user name')
param createdBy string = contains(deployer(), 'userPrincipalName')? split(deployer().userPrincipalName, '@')[0]: deployer().objectId

// ========== Resource Group Tag ========== //
resource resourceGroupTags 'Microsoft.Resources/tags@2021-04-01' = {
  name: 'default'
  properties: {
    tags: {
      TemplateName: 'Content Processing'
      Type: enablePrivateNetworking ? 'WAF' : 'Non-WAF'
      CreatedBy: createdBy
    }
  }
}

// ========== Managed Identity ========== //
module avmManagedIdentity './modules/managed-identity.bicep' = {
  name: take('module.managed-identity.${solutionSuffix}', 64)
  params: {
    name: 'id-${solutionSuffix}'
    location: resourceGroupLocation
    tags: tags
  }
}

// ========== Key Vault Module ========== //
module avmKeyVault './modules/key-vault.bicep' = {
  name: take('module.key-vault.${solutionSuffix}', 64)
  params: {
    keyvaultName: 'kv-${solutionSuffix}'
    location: resourceGroupLocation
    tags: tags
    roleAssignments: [
      {
        principalId: avmManagedIdentity.outputs.principalId
        roleDefinitionIdOrName: 'Key Vault Administrator'
        principalType: 'ServicePrincipal'
      }
    ]
    enablePurgeProtection: false
    enableSoftDelete: true
    keyvaultsku: 'standard'
    enableRbacAuthorization: true
    createMode: 'default'
    enableTelemetry: enableTelemetry
    enableVaultForDiskEncryption: true
    enableVaultForTemplateDeployment: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: (enablePrivateNetworking) ? 'Disabled' : 'Enabled'
    logAnalyticsWorkspaceResourceId: enableMonitoring ? logAnalyticsWorkspace!.outputs.resourceId : ''
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Deny'
    }
    // privateEndpoints omitted for now, as not in strongly-typed params
  }
}

module avmContainerRegistry 'modules/container-registry.bicep' = {
  name: take('module.container-registry.${solutionSuffix}', 64)
  params: {
    acrName: 'cr${replace(solutionSuffix, '-', '')}'
    location: resourceGroupLocation
    acrSku: 'Standard'
    publicNetworkAccess: 'Enabled'
    zoneRedundancy: 'Disabled'
    roleAssignments: [
      {
        principalId: avmContainerRegistryReader.outputs.principalId
        roleDefinitionIdOrName: 'AcrPull'
        principalType: 'ServicePrincipal'
      }
    ]
    tags: tags
  }
}

// // ========== Storage Account ========== //
module avmStorageAccount 'br/public:avm/res/storage/storage-account:0.20.0' = {
  name: take('module.storage-account.${solutionSuffix}', 64)
  params: {
    name: 'st${replace(solutionSuffix, '-', '')}'
    location: resourceGroupLocation
    //skuName: 'Standard_GRS'
    //kind: 'StorageV2'
    managedIdentities: { systemAssigned: true }
    minimumTlsVersion: 'TLS1_2'
    enableTelemetry: enableTelemetry
    roleAssignments: [
      {
        principalId: avmManagedIdentity.outputs.principalId
        roleDefinitionIdOrName: 'Storage Blob Data Contributor'
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: 'Storage Blob Data Contributor'
        principalId: avmContainerApp.outputs.systemAssignedMIPrincipalId!
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: 'Storage Blob Data Contributor'
        principalId: avmContainerApp_API.outputs.systemAssignedMIPrincipalId!
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: 'Storage Queue Data Contributor'
        principalId: avmContainerApp.outputs.systemAssignedMIPrincipalId!
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: 'Storage Queue Data Contributor'
        principalId: avmContainerApp_API.outputs.systemAssignedMIPrincipalId!
        principalType: 'ServicePrincipal'
      }
    ]
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: (enablePrivateNetworking) ? 'Deny' : 'Allow'
      ipRules: []
    }
    supportsHttpsTrafficOnly: true
    accessTier: 'Hot'
    tags: tags

    //<======================= WAF related parameters
    allowBlobPublicAccess: (enablePrivateNetworking) ? true : false // Disable public access when WAF is enabled
    publicNetworkAccess: (enablePrivateNetworking) ? 'Disabled' : 'Enabled'
    privateEndpoints: (enablePrivateNetworking)
      ? [
          {
            name: 'pep-blob-${solutionSuffix}'
            customNetworkInterfaceName: 'nic-blob-${solutionSuffix}'
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                {
                  name: 'storage-dns-zone-group-blob'
                  privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.storageBlob].outputs.resourceId
                }
              ]
            }
            subnetResourceId: virtualNetwork.outputs.backendSubnetResourceId // Use the backend subnet
            service: 'blob'
          }
          {
            name: 'pep-queue-${solutionSuffix}'
            customNetworkInterfaceName: 'nic-queue-${solutionSuffix}'
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                {
                  name: 'storage-dns-zone-group-queue'
                  privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.storageQueue].outputs.resourceId
                  //privateDnsZoneResourceId: avmPrivateDnsZoneStorages[2].outputs.resourceId
                }
              ]
            }
            subnetResourceId: virtualNetwork.outputs.backendSubnetResourceId // Use the backend subnet
            service: 'queue'
          }
        ]
      : []
  }
}

// // ========== AI Foundry and related resources ========== //
module avmAiServices 'modules/account/main.bicep' = {
  name: take('module.ai-services.${solutionSuffix}', 64)
  params: {
    name: 'aif-${solutionSuffix}'
    projectName: 'proj-${solutionSuffix}'
    projectDescription: 'proj-${solutionSuffix}'
    existingFoundryProjectResourceId: existingProjectResourceId
    location: aiServiceLocation
    sku: 'S0'
    allowProjectManagement: true
    managedIdentities: { systemAssigned: true }
    kind: 'AIServices'
    tags: {
      app: solutionSuffix
      location: aiServiceLocation
    }
    customSubDomainName: 'aif-${solutionSuffix}'
    diagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspace!.outputs.resourceId }] : null
    roleAssignments: [
      {
        principalId: avmManagedIdentity.outputs.principalId
        roleDefinitionIdOrName: '8e3af657-a8ff-443c-a75c-2fe8c4bcb635' // Owner role
        principalType: 'ServicePrincipal'
      }
      {
        principalId: avmContainerApp.outputs.systemAssignedMIPrincipalId!
        roleDefinitionIdOrName: 'Cognitive Services OpenAI User'
        principalType: 'ServicePrincipal'
      }
    ]
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: (enablePrivateNetworking) ? 'Deny' : 'Allow'
    }
    disableLocalAuth: true
    enableTelemetry: enableTelemetry
    deployments: [
      {
        name: gptModelName
        model: {
          format: 'OpenAI'
          name: gptModelName
          version: gptModelVersion
        }
        sku: {
          name: deploymentType
          capacity: gptDeploymentCapacity
        }
        raiPolicyName: 'Microsoft.Default'
      }
    ]

    // WAF related parameters
    publicNetworkAccess: (enablePrivateNetworking) ? 'Disabled' : 'Enabled'
    //publicNetworkAccess: 'Enabled' // Always enabled for AI Services
    privateEndpoints: (enablePrivateNetworking && empty(existingProjectResourceId))
      ? [
          {
            name: 'pep-aiservices-${solutionSuffix}'
            customNetworkInterfaceName: 'nic-aiservices-${solutionSuffix}'
            privateEndpointResourceId: virtualNetwork.outputs.resourceId
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                {
                  name: 'ai-services-dns-zone-cognitiveservices'
                  privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.cognitiveServices].outputs.resourceId
                  //privateDnsZoneResourceId: avmPrivateDnsZoneAiServices[0].outputs.resourceId
                }
                {
                  name: 'ai-services-dns-zone-openai'
                  privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.openAI].outputs.resourceId
                  //privateDnsZoneResourceId: avmPrivateDnsZoneAiServices[2].outputs.resourceId
                }
                {
                  name: 'ai-services-dns-zone-aiservices'
                  privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.aiServices].outputs.resourceId
                  //privateDnsZoneResourceId: avmPrivateDnsZoneAiServices[3].outputs.resourceId
                }
                {
                  name: 'ai-services-dns-zone-contentunderstanding'
                  privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.contentUnderstanding].outputs.resourceId
                  //privateDnsZoneResourceId: avmPrivateDnsZoneAiServices[1].outputs.resourceId
                }
              ]
            }
            subnetResourceId: virtualNetwork.outputs.backendSubnetResourceId // Use the backend subnet
          }
        ]
      : []
  }
}

// ========== Private Endpoint for Existing AI Services ========== //
var useExistingService = !empty(existingProjectResourceId)
var existingCognitiveServiceDetails = split(existingProjectResourceId, '/')

resource existingAiFoundryAiServices 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = if(useExistingService) {
  name: existingCognitiveServiceDetails[8]
  scope: resourceGroup(existingCognitiveServiceDetails[2], existingCognitiveServiceDetails[4])
}

// ========== Private Endpoint for Existing AI Services ========== //
var shouldCreatePrivateEndpoint = useExistingService && enablePrivateNetworking
var isProjectPrivate = existingAiFoundryAiServices!.properties.publicNetworkAccess == 'Enabled' ? false : true
module existingAiServicesPrivateEndpoint './modules/existing-aif-private-endpoint.bicep' = if (shouldCreatePrivateEndpoint){
  name: take('module.proj-private-endpoint.${existingAiFoundryAiServices.name}', 64)
  params: {
    isPrivate: isProjectPrivate
    aiServicesName: existingAiFoundryAiServices.name
    subnetResourceId: virtualNetwork!.outputs.backendSubnetResourceId
    aiServicesId: existingAiFoundryAiServices.id
    location: location
    cognitiveServicesDnsZoneId: avmPrivateDnsZones[dnsZoneIndex.cognitiveServices]!.outputs.resourceId
    openAiDnsZoneId: avmPrivateDnsZones[dnsZoneIndex.openAI]!.outputs.resourceId
    aiServicesDnsZoneId: avmPrivateDnsZones[dnsZoneIndex.aiServices]!.outputs.resourceId
    contentUnderstandingDnsZoneId: avmPrivateDnsZones[dnsZoneIndex.contentUnderstanding]!.outputs.resourceId
    tags: tags
  }
  dependsOn: [
    avmPrivateDnsZones
  ]
}

module avmAiServices_cu 'br/public:avm/res/cognitive-services/account:0.11.0' = {
  name: take('avm.res.cognitive-services.account.content-understanding.${solutionSuffix}', 64)

  params: {
    name: 'aicu-${solutionSuffix}'
    location: contentUnderstandingLocation
    sku: 'S0'
    managedIdentities: {
      systemAssigned: false
      userAssignedResourceIds: [
        avmManagedIdentity.outputs.resourceId // Use the managed identity created above
      ]
    }
    kind: 'AIServices'
    tags: {
      app: solutionSuffix
      location: resourceGroupLocation
    }
    customSubDomainName: 'aicu-${solutionSuffix}'
    disableLocalAuth: true
    enableTelemetry: enableTelemetry
    networkAcls: {
      bypass: 'AzureServices'
      //defaultAction: (enablePrivateNetworking) ? 'Deny' : 'Allow'
      defaultAction: 'Allow' // Always allow for AI Services
    }
    roleAssignments: [
      {
        principalId: avmContainerApp.outputs.systemAssignedMIPrincipalId!
        roleDefinitionIdOrName: 'a97b65f3-24c7-4388-baec-2e87135dc908'
        principalType: 'ServicePrincipal'
      }
    ]

    publicNetworkAccess: (enablePrivateNetworking) ? 'Disabled' : 'Enabled'
    privateEndpoints: (enablePrivateNetworking)
      ? [
          {
            name: 'pep-aicu-${solutionSuffix}'
            customNetworkInterfaceName: 'nic-aicu-${solutionSuffix}'
            privateEndpointResourceId: virtualNetwork.outputs.resourceId
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                {
                  name: 'aicu-dns-zone-cognitiveservices'
                  privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.cognitiveServices].outputs.resourceId
                  //privateDnsZoneResourceId: avmPrivateDnsZoneAiServices[0].outputs.resourceId
                }
                {
                  name: 'aicu-dns-zone-contentunderstanding'
                  privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.contentUnderstanding].outputs.resourceId
                  //privateDnsZoneResourceId: avmPrivateDnsZoneAiServices[1].outputs.resourceId
                }
              ]
            }
            subnetResourceId: virtualNetwork.outputs.backendSubnetResourceId // Use the backend subnet
          }
        ]
      : []
  }
}

// ========== Container App Environment ========== //
module avmContainerAppEnv 'br/public:avm/res/app/managed-environment:0.11.2' = {
  name: take('avm.res.app.managed-environment.${solutionSuffix}', 64)
  params: {
    name: 'cae-${solutionSuffix}'
    location: resourceGroupLocation
    tags: {
      app: solutionSuffix
      location: resourceGroupLocation
    }
    managedIdentities: { systemAssigned: true }
    appLogsConfiguration: enableMonitoring ? {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace!.outputs.logAnalyticsWorkspaceId
        sharedKey: logAnalyticsWorkspace.outputs.primarySharedKey
      }
    } : null
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
    enableTelemetry: enableTelemetry
    publicNetworkAccess: 'Enabled' // Always enabled for Container Apps Environment

    // <========== WAF related parameters

    platformReservedCidr: '172.17.17.0/24'
    platformReservedDnsIP: '172.17.17.17'
    zoneRedundant: (enablePrivateNetworking) ? true : false // Enable zone redundancy if private networking is enabled
    infrastructureSubnetResourceId: (enablePrivateNetworking)
      ? virtualNetwork.outputs.containersSubnetResourceId // Use the container app subnet
      : null // Use the container app subnet
  }
}

// //=========== Managed Identity for Container Registry ========== //
module avmContainerRegistryReader 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.1' = {
  name: take('avm.res.managed-identity.user-assigned-identity.${solutionSuffix}', 64)
  params: {
    name: 'id-acr-${solutionSuffix}'
    location: resourceGroupLocation
    tags: tags
    enableTelemetry: enableTelemetry
  }
}

// ========== Container App  ========== //
module avmContainerApp 'br/public:avm/res/app/container-app:0.17.0' = {
  name: take('avm.res.app.container-app.${solutionSuffix}', 64)
  params: {
    name: 'ca-${solutionSuffix}-app'
    location: resourceGroupLocation
    environmentResourceId: avmContainerAppEnv.outputs.resourceId
    workloadProfileName: 'Consumption'
    enableTelemetry: enableTelemetry
    registries: null
    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [
        avmContainerRegistryReader.outputs.resourceId
      ]
    }

    containers: [
      {
        name: 'ca-${solutionSuffix}'
        image: '${publicContainerImageEndpoint}/contentprocessor:latest'

        resources: {
          cpu: '4'
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
        ]
      }
    ]
    activeRevisionsMode: 'Single'
    ingressExternal: false
    disableIngress: true
    scaleSettings: {
      maxReplicas: enableScalability ? 3 : 2
      minReplicas: enableScalability ? 2 : 1
    }
    tags: tags
  }
}

// ========== Container App API ========== //
module avmContainerApp_API 'br/public:avm/res/app/container-app:0.17.0' = {
  name: take('avm.res.app.container-app-api.${solutionSuffix}', 64)
  params: {
    name: 'ca-${solutionSuffix}-api'
    location: resourceGroupLocation
    environmentResourceId: avmContainerAppEnv.outputs.resourceId
    workloadProfileName: 'Consumption'
    enableTelemetry: enableTelemetry
    registries: null
    tags: tags
    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [
        avmContainerRegistryReader.outputs.resourceId
      ]
    }
    containers: [
      {
        name: 'ca-${solutionSuffix}-api'
        image: '${publicContainerImageEndpoint}/contentprocessorapi:latest'
        resources: {
          cpu: '4'
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
    scaleSettings: {
      maxReplicas: enableScalability ? 3 : 2
      minReplicas: enableScalability ? 2 : 1
      rules: [
        {
          name: 'http-scaler'
          http: {
            metadata: {
              concurrentRequests: '100'
            }
          }
        }
      ]
    }
    ingressExternal: true
    activeRevisionsMode: 'Single'
    ingressTransport: 'auto'
    //ingressAllowInsecure: true
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
}

//========== Container App Web ========== //
module avmContainerApp_Web 'br/public:avm/res/app/container-app:0.17.0' = {
  name: take('avm.res.app.container-app-web.${solutionSuffix}', 64)
  params: {
    name: 'ca-${solutionSuffix}-web'
    location: resourceGroupLocation
    environmentResourceId: avmContainerAppEnv.outputs.resourceId
    workloadProfileName: 'Consumption'
    enableTelemetry: enableTelemetry
    registries: null
    tags: tags
    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [
        avmContainerRegistryReader.outputs.resourceId
      ]
    }
    ingressExternal: true
    activeRevisionsMode: 'Single'
    ingressTransport: 'auto'
    //ingressAllowInsecure: true
    scaleSettings: {
      maxReplicas: enableScalability ? 3 : 2
      minReplicas: enableScalability ? 2 : 1
      rules: [
        {
          name: 'http-scaler'
          http: {
            metadata: {
              concurrentRequests: '100'
            }
          }
        }
      ]
    }
    containers: [
      {
        name: 'ca-${solutionSuffix}-web'
        image: '${publicContainerImageEndpoint}/contentprocessorweb:latest'
        resources: {
          cpu: '4'
          memory: '8.0Gi'
        }
        env: [
          {
            name: 'APP_API_BASE_URL'
            value: 'https://${avmContainerApp_API.outputs.fqdn}'
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
            name: 'APP_CONSOLE_LOG_ENABLED'
            value: 'false'
          }
        ]
      }
    ]
  }
}

// ========== Cosmos Database for Mongo DB ========== //
module avmCosmosDB 'br/public:avm/res/document-db/database-account:0.15.0' = {
  name: take('avm.res.document-db.database-account.${solutionSuffix}', 64)
  params: {
    name: 'cosmos-${solutionSuffix}'
    location: resourceGroupLocation
    mongodbDatabases: [
      {
        name: 'default'
        tag: 'default database'
      }
    ]
    tags: tags
    enableTelemetry: enableTelemetry
    databaseAccountOfferType: 'Standard'
    automaticFailover: false
    serverVersion: '7.0'
    capabilitiesToAdd: [
      'EnableMongo'
    ]
    enableAnalyticalStorage: true
    defaultConsistencyLevel: 'Session'
    maxIntervalInSeconds: 5
    maxStalenessPrefix: 100
    zoneRedundant: false

    // WAF related parameters
    networkRestrictions: {
      publicNetworkAccess: (enablePrivateNetworking) ? 'Disabled' : 'Enabled'
      ipRules: []
      virtualNetworkRules: []
    }

    privateEndpoints: (enablePrivateNetworking)
      ? [
          {
            name: 'pep-cosmosdb-${solutionSuffix}'
            customNetworkInterfaceName: 'nic-cosmosdb-${solutionSuffix}'
            privateEndpointResourceId: virtualNetwork.outputs.resourceId
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                {
                  name: 'cosmosdb-dns-zone-group'
                  privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.cosmosDB].outputs.resourceId
                  //privateDnsZoneResourceId: avmPrivateDnsZoneCosmosMongoDB.outputs.resourceId
                }
              ]
            }
            service: 'MongoDB'
            subnetResourceId: virtualNetwork.outputs.backendSubnetResourceId // Use the backend subnet
          }
        ]
      : []
  }
}

// ========== App Configuration ========== //
module avmAppConfig 'br/public:avm/res/app-configuration/configuration-store:0.6.3' = {
  name: take('avm.res.app.configuration-store.${solutionSuffix}', 64)
  params: {
    name: 'appcs-${solutionSuffix}'
    location: resourceGroupLocation
    enablePurgeProtection: false
    tags: {
      app: solutionSuffix
      location: resourceGroupLocation
    }
    enableTelemetry: enableTelemetry
    managedIdentities: { systemAssigned: true }
    sku: 'Standard'
    diagnosticSettings: enableMonitoring ? [
      {
        workspaceResourceId: enableMonitoring ? logAnalyticsWorkspace!.outputs.resourceId : ''
        logCategoriesAndGroups: [
          {
            categoryGroup: 'allLogs'
            enabled: true
          }
        ]
      }
    ] : null
    disableLocalAuth: false
    replicaLocations: (resourceGroupLocation != secondaryLocation) ? [secondaryLocation] : []
    roleAssignments: [
      {
        principalId: avmContainerApp.outputs.?systemAssignedMIPrincipalId!
        roleDefinitionIdOrName: 'App Configuration Data Reader'
        principalType: 'ServicePrincipal'
      }
      {
        principalId: avmContainerApp_API.outputs.?systemAssignedMIPrincipalId!
        roleDefinitionIdOrName: 'App Configuration Data Reader'
        principalType: 'ServicePrincipal'
      }
      {
        principalId: avmContainerApp_Web.outputs.?systemAssignedMIPrincipalId!
        roleDefinitionIdOrName: 'App Configuration Data Reader'
        principalType: 'ServicePrincipal'
      }
    ]
    keyValues: [
      {
        name: 'APP_AZURE_OPENAI_ENDPOINT'
        value: avmAiServices.outputs.endpoint //TODO: replace with actual endpoint
      }
      {
        name: 'APP_AZURE_OPENAI_MODEL'
        value: gptModelName
      }
      {
        name: 'APP_CONTENT_UNDERSTANDING_ENDPOINT'
        value: avmAiServices_cu.outputs.endpoint //TODO: replace with actual endpoint
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
        name: 'APP_LOGGING_ENABLE'
        value: 'False'
      }
      {
        name: 'APP_LOGGING_LEVEL'
        value: 'INFO'
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
        value: avmStorageAccount.outputs.serviceEndpoints.blob
      }
      {
        name: 'APP_STORAGE_QUEUE_URL'
        value: avmStorageAccount.outputs.serviceEndpoints.queue
      }
      {
        name: 'APP_AI_PROJECT_ENDPOINT'
        value: avmAiServices.outputs.aiProjectInfo.apiEndpoint
      }
      {
        name: 'APP_COSMOS_CONNSTR'
        value: avmCosmosDB.outputs.primaryReadWriteConnectionString
      }
    ]

    publicNetworkAccess: 'Enabled'
    // WAF related parameters

    // privateEndpoints: (enablePrivateNetworking)
    //   ? [
    //       {
    //         name: 'appconfig-private-endpoint'
    //         privateEndpointResourceId: avmVirtualNetwork.outputs.resourceId
    //         privateDnsZoneGroup: {
    //           privateDnsZoneGroupConfigs: [
    //             {
    //               name: 'appconfig-dns-zone-group'
    //               privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.appConfig].outputs.resourceId
    //               //privateDnsZoneResourceId: avmPrivateDnsZoneAppConfig.outputs.resourceId
    //             }
    //           ]
    //         }
    //         subnetResourceId: avmVirtualNetwork.outputs.subnetResourceIds[0] // Use the backend subnet
    //       }
    //     ]
    //   : []
  }
}

module avmAppConfig_update 'br/public:avm/res/app-configuration/configuration-store:0.6.3' = if (enablePrivateNetworking) {
  name: take('avm.res.app.configuration-store.update.${solutionSuffix}', 64)
  params: {
    name: 'appcs-${solutionSuffix}'
    location: resourceGroupLocation
    enableTelemetry: enableTelemetry
    tags: tags
    publicNetworkAccess: 'Disabled'
    privateEndpoints: [
      {
        name: 'pep-appconfig-${solutionSuffix}'
        customNetworkInterfaceName: 'nic-appconfig-${solutionSuffix}'
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            {
              name: 'appconfig-dns-zone-group'
              privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.appConfig].outputs.resourceId
              //privateDnsZoneResourceId: avmPrivateDnsZoneAppConfig.outputs.resourceId
            }
          ]
        }
        subnetResourceId: virtualNetwork.outputs.backendSubnetResourceId // Use the backend subnet
      }
    ]
  }

  dependsOn: [
    avmAppConfig
  ]
}

// ========== Container App Update Modules ========== //
module avmContainerApp_update 'br/public:avm/res/app/container-app:0.17.0' = {
  name: take('avm.res.app.container-app-update.${solutionSuffix}', 64)
  params: {
    name: 'ca-${solutionSuffix}-app'
    location: resourceGroupLocation
    enableTelemetry: enableTelemetry
    environmentResourceId: avmContainerAppEnv.outputs.resourceId
    workloadProfileName: 'Consumption'
    registries: null
    tags: tags
    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [
        avmContainerRegistryReader.outputs.resourceId
      ]
    }
    containers: [
      {
        name: 'ca-${solutionSuffix}'
        image: '${publicContainerImageEndpoint}/contentprocessor:latest'

        resources: {
          cpu: '4'
          memory: '8.0Gi'
        }
        env: [
          {
            name: 'APP_CONFIG_ENDPOINT'
            value: avmAppConfig.outputs.endpoint
          }
          {
            name: 'APP_ENV'
            value: 'prod'
          }
        ]
      }
    ]
    activeRevisionsMode: 'Single'
    ingressExternal: false
    disableIngress: true
    scaleSettings: {
      maxReplicas: enableScalability ? 3 : 2
      minReplicas: enableScalability ? 2 : 1
      rules: enableScalability
        ? [
            {
              name: 'http-scaler'
              http: {
                metadata: {
                  concurrentRequests: 100
                }
              }
            }
          ]
        : []
    }
  }
}

module avmContainerApp_API_update 'br/public:avm/res/app/container-app:0.17.0' = {
  name: take('avm.res.app.container-app-api.update.${solutionSuffix}', 64)
  params: {
    name: 'ca-${solutionSuffix}-api'
    location: resourceGroupLocation
    enableTelemetry: enableTelemetry
    environmentResourceId: avmContainerAppEnv.outputs.resourceId
    workloadProfileName: 'Consumption'
    registries: null
    tags: tags
    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [
        avmContainerRegistryReader.outputs.resourceId
      ]
    }

    containers: [
      {
        name: 'ca-${solutionSuffix}-api'
        image: '${publicContainerImageEndpoint}/contentprocessorapi:latest'
        resources: {
          cpu: '4'
          memory: '8.0Gi'
        }
        env: [
          {
            name: 'APP_CONFIG_ENDPOINT'
            value: avmAppConfig.outputs.endpoint
          }
          {
            name: 'APP_ENV'
            value: 'prod'
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
    scaleSettings: {
      maxReplicas: enableScalability ? 3 : 2
      minReplicas: enableScalability ? 2 : 1
      rules: [
        {
          name: 'http-scaler'
          http: {
            metadata: {
              concurrentRequests: '100'
            }
          }
        }
      ]
    }
    ingressExternal: true
    activeRevisionsMode: 'Single'
    ingressTransport: 'auto'
    //ingressAllowInsecure: true
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
}

// ============ //
// Outputs      //
// ============ //

@description('The name of the Container App used for Web App.')
output CONTAINER_WEB_APP_NAME string = avmContainerApp_Web.outputs.name

@description('The name of the Container App used for API.')
output CONTAINER_API_APP_NAME string = avmContainerApp_API.outputs.name

@description('The FQDN of the Container App.')
output CONTAINER_WEB_APP_FQDN string = avmContainerApp_Web.outputs.fqdn

@description('The FQDN of the Container App API.')
output CONTAINER_API_APP_FQDN string = avmContainerApp_API.outputs.fqdn

@description('The name of the Container App used for APP.')
output CONTAINER_APP_NAME string = avmContainerApp.outputs.name

@description('The user identity resource ID used fot the Container APP.')
output CONTAINER_APP_USER_IDENTITY_ID string = avmContainerRegistryReader.outputs.resourceId

@description('The user identity Principal ID used fot the Container APP.')
output CONTAINER_APP_USER_PRINCIPAL_ID string = avmContainerRegistryReader.outputs.principalId

@description('The name of the Azure Container Registry.')
output CONTAINER_REGISTRY_NAME string = avmContainerRegistry.outputs.name

@description('The login server of the Azure Container Registry.')
output CONTAINER_REGISTRY_LOGIN_SERVER string = avmContainerRegistry.outputs.loginServer

@description('The resource group the resources were deployed into.')
output resourceGroupName string = resourceGroup().name
