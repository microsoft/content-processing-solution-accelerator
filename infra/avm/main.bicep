// ============================================================================
// main.bicep — Orchestrator
// Description: Pure orchestrator for Content Processing Solution Accelerator
//              All resource names are derived from params — no hardcoded names.
//              This file only calls modules; no inline resource definitions.
//              Supports WAF-aligned deployment via feature flags.
// ============================================================================
targetScope = 'resourceGroup'

// ============================================================================
// Parameters — Core
// ============================================================================

@minLength(3)
@maxLength(20)
@description('Optional. Name of the solution to deploy. This should be 3-20 characters long.')
param solutionName string = 'cps'

@metadata({ azd: { type: 'location' } })
@description('Required. Azure region for all services. Regions are restricted to guarantee compatibility with paired regions and replica locations for data redundancy and failover scenarios based on articles [Azure regions list](https://learn.microsoft.com/azure/reliability/regions-list) and [Azure Database for MySQL Flexible Server - Azure Regions](https://learn.microsoft.com/azure/mysql/flexible-server/overview#azure-regions).')
@allowed([
  'australiaeast'
  'centralus'
  'eastasia'
  'eastus2'
  'japaneast'
  'northeurope'
  'southeastasia'
  'uksouth'
])
param location string

@description('Optional. Tags to be applied to the resources.')
param tags resourceInput<'Microsoft.Resources/resourceGroups@2025-04-01'>.tags = {
  app: 'Content Processing Solution Accelerator'
  location: resourceGroup().location
}

@description('Optional. Tag, Created by user name.')
param createdBy string = contains(deployer(), 'userPrincipalName')
  ? split(deployer().userPrincipalName, '@')[0]
  : deployer().objectId

@maxLength(5)
@description('Optional. A unique text value for the solution. This is used to ensure resource names are unique for global resources. Defaults to a 5-character substring of the unique string generated from the subscription ID, resource group name, and solution name.')
param solutionUniqueText string = substring(uniqueString(subscription().id, resourceGroup().name, solutionName), 0, 5)

// ============================================================================
// Parameters — WAF Feature Flags
// ============================================================================

@description('Optional. Enable WAF for the deployment.')
param enablePrivateNetworking bool = false

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('Optional. Enable monitoring applicable resources, aligned with the Well Architected Framework recommendations. This setting enables Application Insights and Log Analytics and configures all the resources applicable resources to send logs. Defaults to false.')
param enableMonitoring bool = false

@description('Optional. Enable redundancy for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enableRedundancy bool = false

@description('Optional. Enable scalability for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enableScalability bool = false

@description('Optional. Enable purge protection. Defaults to false.')
param enablePurgeProtection bool = false

// ============================================================================
// Parameters — VM
// ============================================================================

@description('Optional. Size of the Jumpbox Virtual Machine when created. Set to custom value if enablePrivateNetworking is true.')
param vmSize string = ''

@description('Optional. Admin username for the Jumpbox Virtual Machine. Set to custom value if enablePrivateNetworking is true.')
@secure()
param vmAdminUsername string = ''

@description('Optional. Admin password for the Jumpbox Virtual Machine. Set to custom value if enablePrivateNetworking is true.')
@secure()
param vmAdminPassword string = ''

// ============================================================================
// Parameters — AI Configuration
// ============================================================================

@minLength(1)
@allowed([
  'australiaeast'
  'eastus'
  'eastus2'
  'japaneast'
  'southcentralus'
  'southeastasia'
  'swedencentral'
  'uksouth'
  'westeurope'
  'westus'
  'westus3'
])
@description('Required. Location for the Azure AI Services deployment. Must support both Azure OpenAI gpt-5.1 (GlobalStandard) and Azure AI Content Understanding GA. If the deploymentType param is set to Standard, override the metadata.azd.usageName below to reference OpenAI.Standard.gpt-5.1 instead.')
@metadata({
  azd: {
    type: 'location'
    usageName: [
      'OpenAI.GlobalStandard.gpt-5.1,300'
    ]
  }
})
param azureAiServiceLocation string

@description('Optional. Type of GPT deployment to use: Standard | GlobalStandard.')
@minLength(1)
@allowed([
  'Standard'
  'GlobalStandard'
])
param deploymentType string = 'GlobalStandard'

@description('Optional. Name of the GPT model to deploy: gpt-5.1')
param gptModelName string = 'gpt-5.1'

@minLength(1)
@description('Optional. Version of the GPT model to deploy:.')
@allowed([
  '2025-11-13'
])
param gptModelVersion string = '2025-11-13'

@minValue(1)
@description('Optional. Capacity of the GPT deployment: (minimum 10).')
param gptDeploymentCapacity int = 300

// ============================================================================
// Parameters — Compute
// ============================================================================

@description('Optional. The container registry login server/endpoint for the container images (for example, an Azure Container Registry endpoint).')
param containerRegistryEndpoint string = 'cpscontainerreg.azurecr.io'

@description('Optional. The image tag for the container images.')
param imageTag string = 'latest_v2'

// ============================================================================
// Parameters — Existing Resources
// ============================================================================

@description('Optional: Existing Log Analytics Workspace Resource ID')
param existingLogAnalyticsWorkspaceId string = ''

@description('Use this parameter to use an existing AI project resource ID')
param existingFoundryProjectResourceId string = ''

// ============================================================================
// Variables
// ============================================================================

var solutionSuffix = toLower(trim(replace(
  replace(
    replace(replace(replace(replace('${solutionName}${solutionUniqueText}', '-', ''), '_', ''), '.', ''), '/', ''),
    ' ',
    ''
  ),
  '*',
  ''
)))

var existingProjectResourceId = trim(existingFoundryProjectResourceId)

// Replica regions list based on article in [Azure regions list](https://learn.microsoft.com/azure/reliability/regions-list) and [Enhance resilience by replicating your Log Analytics workspace across regions](https://learn.microsoft.com/azure/azure-monitor/logs/workspace-replication#supported-regions) for supported regions for Log Analytics Workspace.
var replicaRegionPairs = {
  australiaeast: 'australiasoutheast'
  centralus: 'westus'
  eastasia: 'japaneast'
  eastus: 'centralus'
  eastus2: 'centralus'
  japaneast: 'eastasia'
  northeurope: 'westeurope'
  southeastasia: 'eastasia'
  uksouth: 'westeurope'
  westeurope: 'northeurope'
}
var replicaLocation = replicaRegionPairs[?location]

var bastionHostName = 'bas-${solutionSuffix}'

var jumpboxVmName = take('vm-${solutionSuffix}', 15)

var dataCollectionRulesResourceName = 'dcr-${solutionSuffix}'
var dataCollectionRulesLocation = logAnalyticsWorkspace!.outputs.location
var logAnalyticsWorkspaceResourceName = 'log-${solutionSuffix}'
var dcrLogAnalyticsDestinationName = 'la-${logAnalyticsWorkspaceResourceName}-destination'

var privateDnsZones = [
  'privatelink.cognitiveservices.azure.com'
  'privatelink.openai.azure.com'
  'privatelink.services.ai.azure.com'
  'privatelink.contentunderstanding.ai.azure.com'
  'privatelink.blob.${environment().suffixes.storage}'
  'privatelink.queue.${environment().suffixes.storage}'
  'privatelink.mongo.cosmos.azure.com'
  'privatelink.azconfig.io'
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
  cosmosDB: 6
  appConfig: 7
  containerRegistry: 8
}

// ============================================================================
// Resource Group Tags
// ============================================================================

resource resourceGroupTags 'Microsoft.Resources/tags@2025-04-01' = {
  name: 'default'
  properties: {
    tags: {
      ...resourceGroup().tags
      ...tags
      TemplateName: 'Content Processing'
      Type: enablePrivateNetworking ? 'WAF' : 'Non-WAF'
      CreatedBy: createdBy
      DeploymentName: deployment().name
    }
  }
}

// ============================================================================
// Module: Monitoring
// ============================================================================

#disable-next-line no-deployments-resources
resource avmTelemetry 'Microsoft.Resources/deployments@2025-04-01' = if (enableTelemetry) {
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

module logAnalyticsWorkspace './modules/monitoring/log-analytics.bicep' = if (enableMonitoring) {
  name: take('module.log-analytics-workspace.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    name: logAnalyticsWorkspaceResourceName
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    enableReplication: enableRedundancy
    replicationLocation: replicaLocation
  }
}

module applicationInsights './modules/monitoring/app-insights.bicep' = if (enableMonitoring) {
  name: take('module.app-insights.${solutionSuffix}', 64)
  params: {
    name: 'appi-${solutionSuffix}'
    location: location
    enableTelemetry: enableTelemetry
    retentionInDays: 365
    kind: 'web'
    disableIpMasking: false
    flowType: 'Bluefield'
    // WAF aligned configuration for Monitoring
    workspaceResourceId: enableMonitoring ? logAnalyticsWorkspace!.outputs.resourceId : ''
    diagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspace!.outputs.resourceId }] : null
    tags: tags
  }
}

module windowsVmDataCollectionRules './modules/monitoring/data-collection-rule.bicep' = if (enablePrivateNetworking && enableMonitoring) {
  name: take('module.data-collection-rule.${solutionSuffix}', 64)
  params: {
    name: dataCollectionRulesResourceName
    tags: tags
    enableTelemetry: enableTelemetry
    location: dataCollectionRulesLocation
    dataCollectionRuleProperties: {
      kind: 'Windows'
      dataSources: {
        performanceCounters: [
          {
            streams: [
              'Microsoft-Perf'
            ]
            samplingFrequencyInSeconds: 60
            counterSpecifiers: [
              '\\Processor Information(_Total)\\% Processor Time'
              '\\Processor Information(_Total)\\% Privileged Time'
              '\\Processor Information(_Total)\\% User Time'
              '\\Processor Information(_Total)\\Processor Frequency'
              '\\System\\Processes'
              '\\Process(_Total)\\Thread Count'
              '\\Process(_Total)\\Handle Count'
              '\\System\\System Up Time'
              '\\System\\Context Switches/sec'
              '\\System\\Processor Queue Length'
              '\\Memory\\% Committed Bytes In Use'
              '\\Memory\\Available Bytes'
              '\\Memory\\Committed Bytes'
              '\\Memory\\Cache Bytes'
              '\\Memory\\Pool Paged Bytes'
              '\\Memory\\Pool Nonpaged Bytes'
              '\\Memory\\Pages/sec'
              '\\Memory\\Page Faults/sec'
              '\\Process(_Total)\\Working Set'
              '\\Process(_Total)\\Working Set - Private'
              '\\LogicalDisk(_Total)\\% Disk Time'
              '\\LogicalDisk(_Total)\\% Disk Read Time'
              '\\LogicalDisk(_Total)\\% Disk Write Time'
              '\\LogicalDisk(_Total)\\% Idle Time'
              '\\LogicalDisk(_Total)\\Disk Bytes/sec'
              '\\LogicalDisk(_Total)\\Disk Read Bytes/sec'
              '\\LogicalDisk(_Total)\\Disk Write Bytes/sec'
              '\\LogicalDisk(_Total)\\Disk Transfers/sec'
              '\\LogicalDisk(_Total)\\Disk Reads/sec'
              '\\LogicalDisk(_Total)\\Disk Writes/sec'
              '\\LogicalDisk(_Total)\\Avg. Disk sec/Transfer'
              '\\LogicalDisk(_Total)\\Avg. Disk sec/Read'
              '\\LogicalDisk(_Total)\\Avg. Disk sec/Write'
              '\\LogicalDisk(_Total)\\Avg. Disk Queue Length'
              '\\LogicalDisk(_Total)\\Avg. Disk Read Queue Length'
              '\\LogicalDisk(_Total)\\Avg. Disk Write Queue Length'
              '\\LogicalDisk(_Total)\\% Free Space'
              '\\LogicalDisk(_Total)\\Free Megabytes'
              '\\Network Interface(*)\\Bytes Total/sec'
              '\\Network Interface(*)\\Bytes Sent/sec'
              '\\Network Interface(*)\\Bytes Received/sec'
              '\\Network Interface(*)\\Packets/sec'
              '\\Network Interface(*)\\Packets Sent/sec'
              '\\Network Interface(*)\\Packets Received/sec'
              '\\Network Interface(*)\\Packets Outbound Errors'
              '\\Network Interface(*)\\Packets Received Errors'
            ]
            name: 'perfCounterDataSource60'
          }
        ]
        windowsEventLogs: [
          {
            name: 'SecurityAuditEvents'
            streams: [
              'Microsoft-Event'
            ]
            xPathQueries: [
              'Security!*[System[(band(Keywords,13510798882111488)) and (EventID != 4624)]]'
            ]
          }
        ]
      }
      destinations: {
        logAnalytics: [
          {
            workspaceResourceId: logAnalyticsWorkspace!.outputs.resourceId
            name: dcrLogAnalyticsDestinationName
          }
        ]
      }
      dataFlows: [
        {
          streams: [
            'Microsoft-Perf'
          ]
          destinations: [
            dcrLogAnalyticsDestinationName
          ]
          transformKql: 'source'
          outputStream: 'Microsoft-Perf'
        }
        {
          streams: [
            'Microsoft-Event'
          ]
          destinations: [
            dcrLogAnalyticsDestinationName
          ]
          transformKql: 'source'
          outputStream: 'Microsoft-Event'
        }
      ]
    }
  }
}

// ============================================================================
// Module: Networking (WAF - conditional)
// ============================================================================

module virtualNetwork './modules/networking/virtual-network.bicep' = if (enablePrivateNetworking) {
  name: take('module.virtual-network.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    addressPrefixes: ['10.0.0.0/8']
    location: location
    tags: tags
    logAnalyticsWorkspaceId: enableMonitoring ? logAnalyticsWorkspace!.outputs.resourceId : ''
    resourceSuffix: solutionSuffix
    enableTelemetry: enableTelemetry
  }
}

module bastionHost './modules/networking/bastion-host.bicep' = if (enablePrivateNetworking) {
  name: take('module.bastion-host.${solutionSuffix}', 64)
  params: {
    name: bastionHostName
    skuName: 'Standard'
    location: location
    virtualNetworkResourceId: virtualNetwork!.outputs.resourceId
    diagnosticSettings: enableMonitoring
      ? [
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
        ]
      : null
    tags: tags
    enableTelemetry: enableTelemetry
    publicIPAddressObject: {
      name: 'pip-${bastionHostName}'
    }
  }
}

module jumpboxVM './modules/compute/virtual-machine.bicep' = if (enablePrivateNetworking) {
  name: take('module.virtual-machine.${solutionSuffix}', 64)
  params: {
    name: jumpboxVmName
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    computerName: take(jumpboxVmName, 15)
    osType: 'Windows'
    vmSize: empty(vmSize) ? 'Standard_D2s_v5' : vmSize
    adminUsername: empty(vmAdminUsername) ? 'JumpboxAdminUser' : vmAdminUsername
    adminPassword: empty(vmAdminPassword) ? 'JumpboxAdminP@ssw0rd1234!' : vmAdminPassword
    managedIdentities: {
      systemAssigned: true
    }
    patchMode: 'AutomaticByPlatform'
    bypassPlatformSafetyChecksOnUserSchedule: true
    maintenanceConfigurationResourceId: maintenanceConfiguration!.outputs.resourceId
    enableAutomaticUpdates: true
    encryptionAtHost: false
    availabilityZone: enableRedundancy ? 1 : -1
    imageReference: {
      publisher: 'microsoft-dsvm'
      offer: 'dsvm-win-2022'
      sku: 'winserver-2022'
      version: 'latest'
    }
    osDisk: {
      name: 'osdisk-${jumpboxVmName}'
      caching: 'ReadWrite'
      createOption: 'FromImage'
      deleteOption: 'Delete'
      diskSizeGB: 128
      managedDisk: {
        // WAF aligned configuration - use Premium storage for better SLA when redundancy is enabled
        storageAccountType: enableRedundancy ? 'Premium_LRS' : 'Standard_LRS'
      }
    }
    nicConfigurations: [
      {
        name: 'nic-${jumpboxVmName}'
        tags: tags
        deleteOption: 'Delete'
        diagnosticSettings: enableMonitoring
          ? [{ workspaceResourceId: logAnalyticsWorkspace!.outputs.resourceId }]
          : null
        ipConfigurations: [
          {
            name: '${jumpboxVmName}-nic01-ipconfig01'
            subnetResourceId: virtualNetwork!.outputs.administrationSubnetResourceId
            diagnosticSettings: enableMonitoring
              ? [{ workspaceResourceId: logAnalyticsWorkspace!.outputs.resourceId }]
              : null
          }
        ]
      }
    ]
    extensionAadJoinConfig: {
      enabled: true
      tags: tags
      typeHandlerVersion: '1.0'
      settings: {
        mdmId:''
      }
    }
    extensionAntiMalwareConfig: {
      enabled: true
      settings: {
        AntimalwareEnabled: 'true'
        Exclusions: {}
        RealtimeProtectionEnabled: 'true'
        ScheduledScanSettings: {
          day: '7'
          isEnabled: 'true'
          scanType: 'Quick'
          time: '120'
        }
      }
      tags: tags
    }
    extensionMonitoringAgentConfig: enableMonitoring
      ? {
          dataCollectionRuleAssociations: [
            {
              dataCollectionRuleResourceId: windowsVmDataCollectionRules!.outputs.resourceId
              name: 'send-${logAnalyticsWorkspace!.outputs.name}'
            }
          ]
          enabled: true
          tags: tags
        }
      : null
    extensionNetworkWatcherAgentConfig: {
      enabled: true
      tags: tags
    }
  }
}

module maintenanceConfiguration './modules/compute/maintenance-configuration.bicep' = if (enablePrivateNetworking) {
  name: take('module.maintenance-configuration.${solutionSuffix}', 64)
  params: {
    name: 'mc-${jumpboxVmName}'
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    extensionProperties: {
      InGuestPatchMode: 'User'
    }
    maintenanceScope: 'InGuestPatch'
    maintenanceWindow: {
      startDateTime: '2024-06-16 00:00'
      duration: '03:55'
      timeZone: 'W. Europe Standard Time'
      recurEvery: '1Day'
    }
    visibility: 'Custom'
    installPatches: {
      rebootSetting: 'IfRequired'
      windowsParameters: {
        classificationsToInclude: [
          'Critical'
          'Security'
        ]
      }
      linuxParameters: {
        classificationsToInclude: [
          'Critical'
          'Security'
        ]
      }
    }
  }
}

@batchSize(5)
module avmPrivateDnsZones './modules/networking/private-dns-zone.bicep' = [
  for (zone, i) in privateDnsZones: if (enablePrivateNetworking) {
    name: take('module.private-dns-zone.${solutionSuffix}.${i}', 64)
    params: {
      name: zone
      tags: tags
      enableTelemetry: enableTelemetry
      virtualNetworkLinks: [{ virtualNetworkResourceId: virtualNetwork!.outputs.resourceId }]
    }
  }
]

module cognitiveServicePrivateEndpoint './modules/networking/private-endpoint.bicep' = if (enablePrivateNetworking && empty(existingProjectResourceId)) {
  name: take('module.private-endpoint.${solutionSuffix}', 64)
  params: {
    name: 'pep-aiservices-${solutionSuffix}'
    location: location
    tags: tags
    customNetworkInterfaceName: 'nic-aiservices-${solutionSuffix}'
    privateLinkServiceConnections: [
      {
        name: 'pep-aiservices-${solutionSuffix}-cognitiveservices-connection'
        properties: {
          privateLinkServiceId: avmAiServices.outputs.resourceId
          groupIds: ['account']
        }
      }
    ]
    privateDnsZoneGroup: {
      privateDnsZoneGroupConfigs: [
        {
          name: 'ai-services-dns-zone-cognitiveservices'
          privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.cognitiveServices]!.outputs.resourceId
        }
        {
          name: 'ai-services-dns-zone-openai'
          privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.openAI]!.outputs.resourceId
        }
        {
          name: 'ai-services-dns-zone-aiservices'
          privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.aiServices]!.outputs.resourceId
        }
        {
          name: 'ai-services-dns-zone-contentunderstanding'
          privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.contentUnderstanding]!.outputs.resourceId
        }
      ]
    }
    subnetResourceId: virtualNetwork!.outputs.backendSubnetResourceId
  }
}

// ============================================================================
// Module: Identity
// ============================================================================

module avmManagedIdentity './modules/identity/managed-identity.bicep' = {
  name: take('module.managed-identity.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    identityName: 'id-${solutionSuffix}'
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
  }
}

module avmContainerRegistryReader './modules/identity/managed-identity.bicep' = {
  name: take('module.managed-identity-acr.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    identityName: 'id-acr-${solutionSuffix}'
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
  }
}

// ============================================================================
// Module: Compute (Container Registry, Container App Env, Container Apps)
// ============================================================================

module avmContainerRegistry './modules/compute/container-registry.bicep' = {
  name: take('module.container-registry.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    name: 'cr${replace(solutionSuffix, '-', '')}'
    location: location
    sku: enableRedundancy || enablePrivateNetworking ? 'Premium' : 'Standard'
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    acrPullPrincipalIds: [
      avmContainerRegistryReader.outputs.principalId
    ]
    tags: tags
    enableTelemetry: enableTelemetry
    enablePrivateNetworking: enablePrivateNetworking
    privateEndpointSubnetId: enablePrivateNetworking ? virtualNetwork!.outputs.backendSubnetResourceId : ''
    privateDnsZoneResourceIds: enablePrivateNetworking
      ? [avmPrivateDnsZones[dnsZoneIndex.containerRegistry]!.outputs.resourceId]
      : []
  }
}

module avmContainerAppEnv './modules/compute/container-app-environment.bicep' = {
  name: take('module.container-app-environment.${solutionSuffix}', 64)
  params: {
    name: 'cae-${solutionSuffix}'
    location: location
    tags: {
      ...resourceGroup().tags
      ...tags
    }
    managedIdentities: { systemAssigned: true }
    appLogsConfiguration: enableMonitoring
      ? {
          destination: 'log-analytics'
          logAnalyticsWorkspaceResourceId: logAnalyticsWorkspace!.outputs.resourceId
        }
      : null
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
    enableTelemetry: enableTelemetry
    publicNetworkAccess: 'Enabled'
    platformReservedCidr: '172.17.17.0/24'
    platformReservedDnsIP: '172.17.17.17'
    zoneRedundant: (enablePrivateNetworking) ? true : false
    infrastructureSubnetResourceId: (enablePrivateNetworking)
      ? virtualNetwork!.outputs.webserverfarmSubnetResourceId
      : null
  }
}

module avmContainerApp './modules/compute/container-app-processor.bicep' = {
  name: take('module.container-app-processor.${solutionSuffix}', 64)
  params: {
    solutionSuffix: solutionSuffix
    location: location
    environmentResourceId: avmContainerAppEnv.outputs.resourceId
    containerRegistryEndpoint: containerRegistryEndpoint
    imageTag: imageTag
    enableScalability: enableScalability
    enableMonitoring: enableMonitoring
    appInsightsConnectionString: enableMonitoring ? applicationInsights.outputs.connectionString : ''
    tags: tags
    enableTelemetry: enableTelemetry
    userAssignedResourceIds: [
      avmContainerRegistryReader.outputs.resourceId
    ]
  }
}

module avmContainerApp_API './modules/compute/container-app-api.bicep' = {
  name: take('module.container-app-api.${solutionSuffix}', 64)
  params: {
    solutionSuffix: solutionSuffix
    location: location
    environmentResourceId: avmContainerAppEnv.outputs.resourceId
    containerRegistryEndpoint: containerRegistryEndpoint
    imageTag: imageTag
    enableScalability: enableScalability
    enableMonitoring: enableMonitoring
    appInsightsConnectionString: enableMonitoring ? applicationInsights.outputs.connectionString : ''
    tags: tags
    enableTelemetry: enableTelemetry
    userAssignedResourceIds: [
      avmContainerRegistryReader.outputs.resourceId
    ]
  }
}

module avmContainerApp_Web './modules/compute/container-app-web.bicep' = {
  name: take('module.container-app-web.${solutionSuffix}', 64)
  params: {
    solutionSuffix: solutionSuffix
    location: location
    environmentResourceId: avmContainerAppEnv.outputs.resourceId
    containerRegistryEndpoint: containerRegistryEndpoint
    imageTag: imageTag
    enableScalability: enableScalability
    tags: tags
    enableTelemetry: enableTelemetry
    userAssignedResourceIds: [
      avmContainerRegistryReader.outputs.resourceId
    ]
    apiAppFqdn: avmContainerApp_API.outputs.fqdn
  }
}

module avmContainerApp_Workflow './modules/compute/container-app-workflow.bicep' = {
  name: take('module.container-app-workflow.${solutionSuffix}', 64)
  params: {
    solutionSuffix: solutionSuffix
    location: location
    environmentResourceId: avmContainerAppEnv.outputs.resourceId
    containerRegistryEndpoint: containerRegistryEndpoint
    imageTag: imageTag
    enableScalability: enableScalability
    enableMonitoring: enableMonitoring
    appInsightsConnectionString: enableMonitoring ? applicationInsights.outputs.connectionString : ''
    tags: tags
    enableTelemetry: enableTelemetry
    userAssignedResourceIds: [
      avmContainerRegistryReader.outputs.resourceId
    ]
  }
}

module avmContainerApp_update './modules/compute/container-app-processor.bicep' = {
  name: take('module.container-app-processor.update.${solutionSuffix}', 64)
  params: {
    solutionSuffix: solutionSuffix
    location: location
    environmentResourceId: avmContainerAppEnv.outputs.resourceId
    containerRegistryEndpoint: containerRegistryEndpoint
    imageTag: imageTag
    enableScalability: enableScalability
    enableMonitoring: enableMonitoring
    appInsightsConnectionString: enableMonitoring ? applicationInsights.outputs.connectionString : ''
    tags: tags
    enableTelemetry: enableTelemetry
    userAssignedResourceIds: [
      avmContainerRegistryReader.outputs.resourceId
    ]
    appConfigEndpoint: avmAppConfig.outputs.endpoint
  }
}

module avmContainerApp_API_update './modules/compute/container-app-api.bicep' = {
  name: take('module.container-app-api.update.${solutionSuffix}', 64)
  params: {
    solutionSuffix: solutionSuffix
    location: location
    environmentResourceId: avmContainerAppEnv.outputs.resourceId
    containerRegistryEndpoint: containerRegistryEndpoint
    imageTag: imageTag
    enableScalability: enableScalability
    enableMonitoring: enableMonitoring
    appInsightsConnectionString: enableMonitoring ? applicationInsights.outputs.connectionString : ''
    tags: tags
    enableTelemetry: enableTelemetry
    userAssignedResourceIds: [
      avmContainerRegistryReader.outputs.resourceId
    ]
    appConfigEndpoint: avmAppConfig.outputs.endpoint
  }
}

module avmContainerApp_Workflow_update './modules/compute/container-app-workflow.bicep' = {
  name: take('module.container-app-workflow.update.${solutionSuffix}', 64)
  params: {
    solutionSuffix: solutionSuffix
    location: location
    environmentResourceId: avmContainerAppEnv.outputs.resourceId
    containerRegistryEndpoint: containerRegistryEndpoint
    imageTag: imageTag
    enableScalability: enableScalability
    enableMonitoring: enableMonitoring
    appInsightsConnectionString: enableMonitoring ? applicationInsights.outputs.connectionString : ''
    tags: tags
    enableTelemetry: enableTelemetry
    userAssignedResourceIds: [
      avmContainerRegistryReader.outputs.resourceId
    ]
    appConfigEndpoint: avmAppConfig.outputs.endpoint
  }
}

// ============================================================================
// Module: AI Services
// ============================================================================

module avmAiServices './modules/ai/ai-foundry.bicep' = {
  name: take('module.ai-services.${solutionSuffix}', 64)
  params: {
    name: 'aif-${solutionSuffix}'
    projectName: 'proj-${solutionSuffix}'
    projectDescription: 'proj-${solutionSuffix}'
    existingFoundryProjectResourceId: existingProjectResourceId
    location: azureAiServiceLocation
    sku: 'S0'
    allowProjectManagement: true
    managedIdentities: { systemAssigned: true }
    kind: 'AIServices'
    tags: {
      app: solutionSuffix
      location: azureAiServiceLocation
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
      {
        principalId: avmContainerApp.outputs.systemAssignedMIPrincipalId!
        roleDefinitionIdOrName: 'Azure AI Developer'
        principalType: 'ServicePrincipal'
      }
      {
        principalId: avmContainerApp_Workflow.outputs.systemAssignedMIPrincipalId!
        roleDefinitionIdOrName: 'Cognitive Services OpenAI User'
        principalType: 'ServicePrincipal'
      }
      {
        principalId: avmContainerApp_Workflow.outputs.systemAssignedMIPrincipalId!
        roleDefinitionIdOrName: 'Azure AI Developer'
        principalType: 'ServicePrincipal'
      }
      {
        principalId: avmContainerApp.outputs.systemAssignedMIPrincipalId!
        roleDefinitionIdOrName: 'Cognitive Services User'
        principalType: 'ServicePrincipal'
      }
      {
        principalId: avmContainerApp_Workflow.outputs.systemAssignedMIPrincipalId!
        roleDefinitionIdOrName: 'Cognitive Services User'
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
  }
}

module avmAiSearch './modules/ai/ai-search.bicep' = {
  name: take('module.ai-search.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    name: 'srch-${solutionSuffix}'
    location: location
    skuName: 'basic'
    replicaCount: enableRedundancy ? 2 : 1
    partitionCount: enableScalability ? 2 : 1
    tags: tags
    enableTelemetry: enableTelemetry
  }
}

// ============================================================================
// Module: Data (Storage, Cosmos DB, App Configuration)
// ============================================================================

module avmStorageAccount './modules/data/storage-account.bicep' = {
  name: take('module.storage-account.${solutionSuffix}', 64)
  params: {
    name: 'st${replace(solutionSuffix, '-', '')}'
    location: location
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
      {
        roleDefinitionIdOrName: 'Storage Blob Data Contributor'
        principalId: avmContainerApp_Workflow.outputs.systemAssignedMIPrincipalId!
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: 'Storage Queue Data Contributor'
        principalId: avmContainerApp_Workflow.outputs.systemAssignedMIPrincipalId!
        principalType: 'ServicePrincipal'
      }
    ]
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: (enablePrivateNetworking) ? 'Deny' : 'Allow'
      ipRules: []
    }
    requireInfrastructureEncryption: true
    supportsHttpsTrafficOnly: true
    accessTier: 'Hot'
    tags: tags
    allowBlobPublicAccess: false
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
                  privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.storageBlob]!.outputs.resourceId
                }
              ]
            }
            subnetResourceId: virtualNetwork!.outputs.backendSubnetResourceId
            service: 'blob'
          }
          {
            name: 'pep-queue-${solutionSuffix}'
            customNetworkInterfaceName: 'nic-queue-${solutionSuffix}'
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                {
                  name: 'storage-dns-zone-group-queue'
                  privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.storageQueue]!.outputs.resourceId
                }
              ]
            }
            subnetResourceId: virtualNetwork!.outputs.backendSubnetResourceId
            service: 'queue'
          }
        ]
      : []
  }
}

module avmCosmosDB './modules/data/cosmos-db-mongo.bicep' = {
  name: take('module.cosmos-db-mongo.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    name: 'cosmos-${solutionSuffix}'
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    databaseName: 'default'
    collections: []
    serverVersion: '7.0'
    consistencyLevel: 'Session'
    zoneRedundant: enableRedundancy
    enableAutomaticFailover: enableRedundancy
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    enablePrivateNetworking: enablePrivateNetworking
    privateEndpointSubnetId: enablePrivateNetworking ? virtualNetwork!.outputs.backendSubnetResourceId : ''
    privateDnsZoneResourceIds: enablePrivateNetworking ? [
      avmPrivateDnsZones[dnsZoneIndex.cosmosDB]!.outputs.resourceId
    ] : []
  }
}

module avmAppConfig './modules/data/app-configuration.bicep' = {
  name: take('module.app-configuration.${solutionSuffix}', 64)
  params: {
    name: 'appcs-${solutionSuffix}'
    location: location
    enablePurgeProtection: enablePurgeProtection
    tags: {
      app: solutionSuffix
      location: location
    }
    enableTelemetry: enableTelemetry
    managedIdentities: { systemAssigned: true }
    sku: 'Standard'
    diagnosticSettings: enableMonitoring
      ? [
          {
            workspaceResourceId: enableMonitoring ? logAnalyticsWorkspace!.outputs.resourceId : ''
            logCategoriesAndGroups: [
              {
                categoryGroup: 'allLogs'
                enabled: true
              }
            ]
          }
        ]
      : null
    disableLocalAuth: false
    replicaLocations: enableRedundancy ? [{ replicaLocation: replicaLocation }] : []
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
      {
        principalId: avmContainerApp_Workflow.outputs.?systemAssignedMIPrincipalId!
        roleDefinitionIdOrName: 'App Configuration Data Reader'
        principalType: 'ServicePrincipal'
      }
    ]
    keyValues: [
      {
        name: 'APP_AZURE_OPENAI_ENDPOINT'
        value: avmAiServices.outputs.endpoint
      }
      {
        name: 'APP_AZURE_OPENAI_MODEL'
        value: gptModelName
      }
      {
        name: 'APP_CONTENT_UNDERSTANDING_ENDPOINT'
        value: avmAiServices.outputs.endpoint
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
        value: avmAiServices.outputs.aiProjectInfo.?apiEndpoint ?? ''
      }
      {
        name: 'APP_COSMOS_CONNSTR'
        value: avmCosmosDB.outputs.primaryReadWriteConnectionString
      }
      {
        name: 'APP_COSMOS_CONTAINER_BATCH_PROCESS'
        value: 'claimprocesses'
      }
      {
        name: 'APP_COSMOS_CONTAINER_BATCHES'
        value: 'batches'
      }
      {
        name: 'APP_COSMOS_CONTAINER_SCHEMASET'
        value: 'Schemasets'
      }
      {
        name: 'APP_CPS_PROCESS_BATCH'
        value: 'process-batch'
      }
      {
        name: 'APP_CPS_CONTENT_PROCESS_ENDPOINT'
        value: 'http://${avmContainerApp_API.outputs.name}/'
      }
      {
        name: 'APP_CPS_POLL_INTERVAL_SECONDS'
        value: '3'
      }
      {
        name: 'APP_STORAGE_ACCOUNT_NAME'
        value: avmStorageAccount.outputs.name
      }
      {
        name: 'CLAIM_PROCESS_QUEUE_NAME'
        value: 'claim-process-queue'
      }
      {
        name: 'DEAD_LETTER_QUEUE_NAME'
        value: 'claim-process-dead-letter-queue'
      }
      {
        name: 'AZURE_OPENAI_ENDPOINT'
        value: avmAiServices.outputs.endpoint
      }
      {
        name: 'AZURE_OPENAI_CHAT_DEPLOYMENT_NAME'
        value: gptModelName
      }
      {
        name: 'AZURE_OPENAI_API_VERSION'
        value: '2025-03-01-preview'
      }
      {
        name: 'AZURE_OPENAI_ENDPOINT_BASE'
        value: avmAiServices.outputs.endpoint
      }
      {
        name: 'AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME'
        value: ''
      }
      {
        name: 'AZURE_AI_AGENT_PROJECT_CONNECTION_STRING'
        value: ''
      }
      {
        name: 'AZURE_TRACING_ENABLED'
        value: 'True'
      }
      {
        name: 'GLOBAL_LLM_SERVICE'
        value: 'AzureOpenAI'
      }
      {
        name: 'GPT5_API_VERSION'
        value: '2025-03-01-preview'
      }
      {
        name: 'GPT5_CHAT_DEPLOYMENT_NAME'
        value: 'gpt-5'
      }
      {
        name: 'GPT5_ENDPOINT'
        value: avmAiServices.outputs.endpoint
      }
      {
        name: 'PHI4_API_VERSION'
        value: '2024-05-01-preview'
      }
      {
        name: 'PHI4_CHAT_DEPLOYMENT_NAME'
        value: 'phi-4'
      }
      {
        name: 'PHI4_ENDPOINT'
        value: avmAiServices.outputs.endpoint
      }
    ]
    publicNetworkAccess: 'Enabled'
  }
}

module avmAppConfig_update './modules/data/app-configuration.bicep' = if (enablePrivateNetworking) {
  name: take('module.app-configuration.update.${solutionSuffix}', 64)
  params: {
    name: 'appcs-${solutionSuffix}'
    location: location
    enablePurgeProtection: enablePurgeProtection
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
              privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.appConfig]!.outputs.resourceId
            }
          ]
        }
        subnetResourceId: virtualNetwork!.outputs.backendSubnetResourceId
      }
    ]
  }

  dependsOn: [
    avmAppConfig
  ]
}

// ============================================================================
// Module: Role Assignments
// ============================================================================

// Access control is configured inline through module roleAssignments and
// principal assignment parameters to preserve existing deployment behavior.

// ============================================================================
// Outputs
// ============================================================================

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

@description('The name of the Container App used for Workflow.')
output CONTAINER_WORKFLOW_APP_NAME string = avmContainerApp_Workflow.outputs.name

@description('The user identity resource ID used fot the Container APP.')
output CONTAINER_APP_USER_IDENTITY_ID string = avmContainerRegistryReader.outputs.resourceId

@description('The user identity Principal ID used fot the Container APP.')
output CONTAINER_APP_USER_PRINCIPAL_ID string = avmContainerRegistryReader.outputs.principalId

@description('The name of the Azure Container Registry.')
output CONTAINER_REGISTRY_NAME string = avmContainerRegistry.outputs.name

@description('The login server of the Azure Container Registry.')
output CONTAINER_REGISTRY_LOGIN_SERVER string = avmContainerRegistry.outputs.loginServer

@description('The name of the AI Services account that hosts both Azure OpenAI and Content Understanding GA.')
output CONTENT_UNDERSTANDING_ACCOUNT_NAME string = avmAiServices.outputs.name

@description('The resource group the resources were deployed into.')
output AZURE_RESOURCE_GROUP string = resourceGroup().name

@description('The solution name.')
output SOLUTION_NAME string = solutionName
