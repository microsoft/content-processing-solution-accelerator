// ========== main.bicep ========== //
targetScope = 'resourceGroup'

import {
  default_deployment_param_type
  content_understanding_available_location_type
  gpt_deployment_type
  gpt_model_name_type
  ai_deployment_param_type
  container_app_deployment_info_type
  make_solution_prefix
} from './modules/types.bicep'

// ========== get up parameters from parameter file ========== //
@description('Name of the environment to deploy the solution into:')
param environmentName string
@description('Location for the content understanding service: WestUS | SwedenCentral | AustraliaEast')
param contentUnderstandingLocation content_understanding_available_location_type
@description('Type of GPT deployment to use: Standard | GlobalStandard')
param deploymentType gpt_deployment_type = 'GlobalStandard'
@description('Name of the GPT model to deploy: gpt-4o-mini | gpt-4o | gpt-4')
param gptModelName gpt_model_name_type = 'gpt-4o'
@minLength(1)
@description('Version of the GPT model to deploy:')
@allowed([
  '2024-08-06'
])
param gptModelVersion string = '2024-08-06'
@minValue(10)
@description('Capacity of the GPT deployment: (minimum 10)')
param gptDeploymentCapacity int
param useLocalBuild string = 'false'

// ============ make up Parameters from bicep parameter module ========== //

// =========== Build Parameters ========== //
param deployment_param default_deployment_param_type = {
  environment_name: environmentName
  unique_id: toLower(uniqueString(subscription().id, environmentName, resourceGroup().location))
  use_local_build: useLocalBuild == 'true' ? 'localbuild' : 'usecontainer'
  solution_prefix: make_solution_prefix(toLower(uniqueString(
    subscription().id,
    environmentName,
    resourceGroup().location
  )))
  secondary_location: 'EastUs2'
  public_container_image_endpoint: 'cpscontainerreg.azurecr.io'
  resource_group_location: resourceGroup().location
  resource_name_prefix: {}
  resource_name_format_string: 'avm.ptn.sa.cps.{0}'
  enable_waf: true
  enable_telemetry: true
  naming_abbrs: loadJsonContent('./abbreviations.json')
  tags: {
    app: 'Content Processing Solution Accelerator'
    location: resourceGroup().location
  }
}

param ai_deployment ai_deployment_param_type = {
  gpt_deployment_type_name: deploymentType
  gpt_model_name: gptModelName
  gpt_model_version: gptModelVersion
  gpt_deployment_capacity: gptDeploymentCapacity
  content_understanding_available_location: contentUnderstandingLocation
}

param container_app_deployment container_app_deployment_info_type = {
  container_app: {
    maxReplicas: 1
    minReplicas: 1
  }
  container_web: {
    maxReplicas: 1
    minReplicas: 1
  }
  container_api: {
    maxReplicas: 1
    minReplicas: 1
  }
}

// ============== //
// WAF Resources      //
// ============== //

// ========== WAF Aligned ========== //
// When default_deployment_param.enable_waf is true, the WAF related module(virtual network, private network endpoints) will be deployed
//

// ========== Network Security Group definition ========== //
module avmNetworkSecurityGroup 'br/public:avm/res/network/network-security-group:0.5.1' = if (deployment_param.enable_waf) {
  name: format(
    deployment_param.resource_name_format_string,
    '${deployment_param.naming_abbrs.networking.networkSecurityGroup}backend'
  )
  params: {
    name: '${deployment_param.naming_abbrs.networking.networkSecurityGroup}${deployment_param.solution_prefix}-backend'
    location: deployment_param.resource_group_location
    tags: deployment_param.tags
    enableTelemetry: deployment_param.enable_telemetry
    diagnosticSettings: [
      { workspaceResourceId: avmAppInsightsLogAnalyticsWorkspace.outputs.logAnalyticsWorkspaceResourceId }
    ]
    securityRules: []
  }
}

// Securing a custom VNET in Azure Container Apps with Network Security Groups 
// https://learn.microsoft.com/en-us/azure/container-apps/firewall-integration?tabs=workload-profiles
module avmNetworkSecurityGroup_Containers 'br/public:avm/res/network/network-security-group:0.5.1' = if (deployment_param.enable_waf) {
  name: format(
    deployment_param.resource_name_format_string,
    '${deployment_param.naming_abbrs.networking.networkSecurityGroup}containers'
  )
  params: {
    name: '${deployment_param.naming_abbrs.networking.networkSecurityGroup}${deployment_param.solution_prefix}-containers'
    location: deployment_param.resource_group_location
    tags: deployment_param.tags
    enableTelemetry: deployment_param.enable_telemetry
    diagnosticSettings: [
      { workspaceResourceId: avmAppInsightsLogAnalyticsWorkspace.outputs.logAnalyticsWorkspaceResourceId }
    ]
    securityRules: [
      //Inbound Rules
      {
        name: 'AllowHttpsInbound'
        properties: {
          access: 'Allow'
          direction: 'Inbound'
          priority: 100
          protocol: 'Tcp'
          sourceAddressPrefix: 'Internet'
          sourcePortRange: '*'
          destinationPortRanges: ['443', '80']
          destinationAddressPrefixes: ['10.0.2.0/24']
        }
      }
      {
        name: 'AllowAzureLoadBalancerInbound'
        properties: {
          access: 'Allow'
          direction: 'Inbound'
          priority: 102
          protocol: '*'
          sourceAddressPrefix: 'AzureLoadBalancer'
          sourcePortRange: '*'
          destinationPortRanges: ['30000-32767']
          destinationAddressPrefixes: ['10.0.2.0/24']
        }
      }
      {
        name: 'AllowSideCarsInbound'
        properties: {
          access: 'Allow'
          direction: 'Inbound'
          priority: 103
          protocol: '*'
          sourcePortRange: '*'
          sourceAddressPrefixes: ['10.0.2.0/24']
          destinationPortRange: '*'
          destinationAddressPrefix: '*'
        }
      }
      //Outbound Rules
      {
        name: 'AllowOutboundToAzureServices'
        properties: {
          access: 'Allow'
          direction: 'Outbound'
          priority: 100
          protocol: '*'
          sourceAddressPrefixes: ['10.0.2.0/24']
          sourcePortRange: '*'
          destinationPortRange: '*'
          destinationAddressPrefix: '*'
        }
      }
    ]
  }
}

module avmNetworkSecurityGroup_Bastion 'br/public:avm/res/network/network-security-group:0.5.1' = if (deployment_param.enable_waf) {
  name: format(
    deployment_param.resource_name_format_string,
    '${deployment_param.naming_abbrs.networking.networkSecurityGroup}bastion'
  )
  params: {
    name: '${deployment_param.naming_abbrs.networking.networkSecurityGroup}${deployment_param.solution_prefix}-bastion'
    location: deployment_param.resource_group_location
    tags: deployment_param.tags
    enableTelemetry: deployment_param.enable_telemetry
    diagnosticSettings: [
      { workspaceResourceId: avmAppInsightsLogAnalyticsWorkspace.outputs.logAnalyticsWorkspaceResourceId }
    ]
    securityRules: []
  }
}

module avmNetworkSecurityGroup_Admin 'br/public:avm/res/network/network-security-group:0.5.1' = if (deployment_param.enable_waf) {
  name: format(
    deployment_param.resource_name_format_string,
    '${deployment_param.naming_abbrs.networking.networkSecurityGroup}admin'
  )
  params: {
    name: '${deployment_param.naming_abbrs.networking.networkSecurityGroup}${deployment_param.solution_prefix}-admin'
    location: deployment_param.resource_group_location
    tags: deployment_param.tags
    enableTelemetry: deployment_param.enable_telemetry
    diagnosticSettings: [
      { workspaceResourceId: avmAppInsightsLogAnalyticsWorkspace.outputs.logAnalyticsWorkspaceResourceId }
    ]
    securityRules: []
  }
}

// ========== Virtual Network definition ========== //
// Azure Resources(Backend) : 10.0.0.0/24 - 10.0.0.255
// Containers :  10.0.2.0/24 - 10.0.2.255
// Admin : 10.0.1.0/27 - 10.0.1.31
// Bastion Hosts : 10.0.1.32/27 - 10.0.1.63
// VM(s) :

module avmVirtualNetwork 'br/public:avm/res/network/virtual-network:0.6.1' = if (deployment_param.enable_waf) {
  name: format(deployment_param.resource_name_format_string, deployment_param.naming_abbrs.networking.virtualNetwork)
  params: {
    name: '${deployment_param.naming_abbrs.networking.virtualNetwork}${deployment_param.solution_prefix}'
    location: deployment_param.resource_group_location
    tags: deployment_param.tags
    enableTelemetry: deployment_param.enable_telemetry
    addressPrefixes: ['10.0.0.0/8']
    diagnosticSettings: [
      { workspaceResourceId: avmAppInsightsLogAnalyticsWorkspace.outputs.logAnalyticsWorkspaceResourceId }
    ]
    subnets: [
      {
        name: 'backend'
        addressPrefix: '10.0.0.0/24'
        networkSecurityGroupResourceId: avmNetworkSecurityGroup.outputs.resourceId
      }
      {
        name: 'containers'
        addressPrefix: '10.0.2.0/24'
        networkSecurityGroupResourceId: avmNetworkSecurityGroup_Containers.outputs.resourceId
        delegation: 'Microsoft.App/environments'
        // privateEndpointNetworkPolicies: 'Disabled'
        // privateLinkServiceNetworkPolicies: 'Enabled'
      }
      {
        name: 'admin'
        addressPrefix: '10.0.1.0/27'
        networkSecurityGroupResourceId: avmNetworkSecurityGroup_Admin.outputs.resourceId
      }
      {
        name: 'bastion'
        addressPrefix: '10.0.1.32/27'
        networkSecurityGroupResourceId: avmNetworkSecurityGroup_Bastion.outputs.resourceId
      }
    ]
  }
}

// ========== Private DNS Zones ========== //

// Private DNS Zones for AI Services
var openAiPrivateDnsZones = {
  'privatelink.cognitiveservices.azure.com': 'account'
  'privatelink.openai.azure.com': 'account'
  'privatelink.services.ai.azure.com': 'account'
  'privatelink.contentunderstanding.ai.azure.com': 'account'
}
module avmPrivateDnsZoneAiServices 'br/public:avm/res/network/private-dns-zone:0.7.1' = [
  for zone in items(openAiPrivateDnsZones): if (deployment_param.enable_waf) {
    name: zone.key
    params: {
      name: zone.key
      tags: deployment_param.tags
      enableTelemetry: deployment_param.enable_telemetry
      virtualNetworkLinks: [{ virtualNetworkResourceId: avmVirtualNetwork.outputs.resourceId }]
    }
  }
]

// Private DNS Zone for AI foundry Storage Blob
var storagePrivateDnsZones = {
  'privatelink.blob.${environment().suffixes.storage}': 'blob'
  'privatelink.queue.${environment().suffixes.storage}': 'queue'
  'privatelink.file.${environment().suffixes.storage}': 'file'
}

module avmPrivateDnsZoneStorage 'br/public:avm/res/network/private-dns-zone:0.7.1' = [
  for zone in items(storagePrivateDnsZones): if (deployment_param.enable_waf) {
    name: 'private-dns-zone-storage-${zone.value}'
    params: {
      name: zone.key
      tags: deployment_param.tags
      enableTelemetry: deployment_param.enable_telemetry
      virtualNetworkLinks: [{ virtualNetworkResourceId: avmVirtualNetwork.outputs.resourceId }]
    }
  }
]

// Private DNS Zone for AI Foundry Workspace
var aiHubPrivateDnsZones = {
  'privatelink.api.azureml.ms': 'amlworkspace'
  'privatelink.notebooks.azure.net': 'amlworkspace'
}

module avmPrivateDnsZoneAiFoundryWorkspace 'br/public:avm/res/network/private-dns-zone:0.7.1' = [
  for (zone, i) in items(aiHubPrivateDnsZones): if (deployment_param.enable_waf) {
    name: 'private-dns-zone-aifoundry-workspace-${zone.value}-${i}'
    params: {
      name: zone.key
      tags: deployment_param.tags
      enableTelemetry: deployment_param.enable_telemetry
      virtualNetworkLinks: [{ virtualNetworkResourceId: avmVirtualNetwork.outputs.resourceId }]
    }
  }
]

// Private DNS Zone for Azure Cosmos DB
var cosmosdbMongoPrivateDnsZones = {
  'privatelink.mongo.cosmos.azure.com': 'cosmosdb'
}
module avmPrivateDnsZoneCosmosMongoDB 'br/public:avm/res/network/private-dns-zone:0.7.1' = if (deployment_param.enable_waf) {
  name: 'private-dns-zone-cosmos-mongo'
  params: {
    name: items(cosmosdbMongoPrivateDnsZones)[0].key
    tags: deployment_param.tags
    enableTelemetry: deployment_param.enable_telemetry
    virtualNetworkLinks: [{ virtualNetworkResourceId: avmVirtualNetwork.outputs.resourceId }]
  }
}

// // Private DNS Zone for Application Storage Account
// var appStoragePrivateDnsZones = {
//   'privatelink.blob.${environment().suffixes.storage}': 'blob'
//   'privatelink.queue.${environment().suffixes.storage}': 'queue'
// }

// module avmPrivateDnsZonesAppStorage 'br/public:avm/res/network/private-dns-zone:0.7.1' = [
//   for (zone, i) in items(appStoragePrivateDnsZones): if (deployment_param.enable_waf) {
//     name: 'private-dns-zone-app-storage-${zone.value}-${i}'
//     params: {
//       name: zone.key
//       tags: deployment_param.tags
//       enableTelemetry: deployment_param.enable_telemetry
//       virtualNetworkLinks: [{ virtualNetworkResourceId: avmVirtualNetwork.outputs.resourceId }]
//     }
//   }
// ]

// Private DNS Zone for App Configuration
var appConfigPrivateDnsZones = {
  'privatelink.azconfig.io': 'appconfig'
}

module avmPrivateDnsZoneAppConfig 'br/public:avm/res/network/private-dns-zone:0.7.1' = if (deployment_param.enable_waf) {
  name: 'private-dns-zone-app-config'
  params: {
    name: items(appConfigPrivateDnsZones)[0].key
    tags: deployment_param.tags
    enableTelemetry: deployment_param.enable_telemetry
    virtualNetworkLinks: [{ virtualNetworkResourceId: avmVirtualNetwork.outputs.resourceId }]
  }
}

// private DNS Zone for Key Vault
var keyVaultPrivateDnsZones = {
  'privatelink.vaultcore.azure.net': 'keyvault'
}

module avmPrivateDnsZoneKeyVault 'br/public:avm/res/network/private-dns-zone:0.7.1' = if (deployment_param.enable_waf) {
  name: 'private-dns-zone-key-vault'
  params: {
    name: items(keyVaultPrivateDnsZones)[0].key
    tags: deployment_param.tags
    enableTelemetry: deployment_param.enable_telemetry
    virtualNetworkLinks: [{ virtualNetworkResourceId: avmVirtualNetwork.outputs.resourceId }]
  }
}

// private DNS Zone for Container Registry
var containerRegistryPrivateDnsZones = {
  'privatelink.azurecr.io': 'containerregistry'
}

module avmPrivateDnsZoneContainerRegistry 'br/public:avm/res/network/private-dns-zone:0.7.1' = if (deployment_param.enable_waf) {
  name: 'private-dns-zone-container-registry'
  params: {
    name: items(containerRegistryPrivateDnsZones)[0].key
    tags: deployment_param.tags
    enableTelemetry: deployment_param.enable_telemetry
    virtualNetworkLinks: [{ virtualNetworkResourceId: avmVirtualNetwork.outputs.resourceId }]
  }
}

// ============== //
// Resources      //
// ============== //

// ========== Application insights ========== //
module avmAppInsightsLogAnalyticsWorkspace './modules/app-insights.bicep' = {
  //name: format(deployment_param.resource_name_format_string, abbrs.managementGovernance.logAnalyticsWorkspace)
  params: {
    appInsights_param: {
      appInsightsName: '${deployment_param.naming_abbrs.managementGovernance.applicationInsights}${deployment_param.solution_prefix}'
      location: deployment_param.resource_group_location
      //diagnosticSettings: [{ useThisWorkspace: true }]
      skuName: 'PerGB2018'
      applicationType: 'web'
      disableIpMasking: false
      disableLocalAuth: false
      flowType: 'Bluefield'
      kind: 'web'
      logAnalyticsWorkspaceName: '${deployment_param.naming_abbrs.managementGovernance.logAnalyticsWorkspace}${deployment_param.solution_prefix}'
      publicNetworkAccessForQuery: 'Enabled'
      requestSource: 'rest'
      retentionInDays: 30
    }
    deployment_param: deployment_param
  }
}

// ========== Managed Identity ========== //
module avmManagedIdentity './modules/managed-identity.bicep' = {
  name: format(deployment_param.resource_name_format_string, deployment_param.naming_abbrs.security.managedIdentity)
  params: {
    name: '${deployment_param.naming_abbrs.security.managedIdentity}${deployment_param.solution_prefix}'
    location: deployment_param.resource_group_location
    tags: deployment_param.tags
  }
}

// Assign Owner role to the managed identity in the resource group
module avmRoleAssignment 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: format(deployment_param.resource_name_format_string, 'rbac-owner')
  params: {
    resourceId: avmManagedIdentity.outputs.resourceId
    principalId: avmManagedIdentity.outputs.principalId
    roleDefinitionId: '8e3af657-a8ff-443c-a75c-2fe8c4bcb635'
    principalType: 'ServicePrincipal'
  }
  scope: resourceGroup(resourceGroup().name)
}

// ========== Key Vault Module ========== //
module avmKeyVault './modules/key-vault.bicep' = {
  name: format(deployment_param.resource_name_format_string, deployment_param.naming_abbrs.security.keyVault)
  params: {
    //name: format(deployment_param.resource_name_format_string, abbrs.security.keyVault)
    keyVaultParams: {
      keyvaultName: '${deployment_param.naming_abbrs.security.keyVault}${deployment_param.solution_prefix}'
      location: deployment_param.resource_group_location
      tags: deployment_param.tags
      roleAssignments: [
        {
          principalId: avmManagedIdentity.outputs.principalId
          roleDefinitionIdOrName: 'Key Vault Administrator'
        }
      ]
      enablePurgeProtection: false
      enableSoftDelete: true
      keyvaultsku: 'standard'
      // Add missing AVM parameters for parity with classic resource
      enableRbacAuthorization: true
      createMode: 'default'
      enableTelemetry: false
      // networkAcls, privateEndpoints, diagnosticSettings, keys, secrets, lock can be added if needed
      enableVaultForDiskEncryption: true
      enableVaultForTemplateDeployment: true
      softDeleteRetentionInDays: 7

      //<=== WAF related parameters
      publicNetworkAccess: (deployment_param.enable_waf) ? 'Disabled' : 'Enabled'
      privateEndpoints: (deployment_param.enable_waf)
        ? [
            {
              name: 'keyvault-private-endpoint'
              privateEndpointResourceId: avmVirtualNetwork.outputs.resourceId
              privateDnsZoneGroup: {
                privateDnsZoneGroupConfigs: [
                  {
                    name: 'keyvault-dns-zone-group'
                    privateDnsZoneResourceId: avmPrivateDnsZoneKeyVault.outputs.resourceId
                  }
                ]
              }
              subnetResourceId: avmVirtualNetwork.outputs.subnetResourceIds[0] // Use the backend subnet
            }
          ]
        : []
    }
    deployment_param: deployment_param
  }
  scope: resourceGroup(resourceGroup().name)
}

module avmKeyVault_RoleAssignment_appConfig 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: format(deployment_param.resource_name_format_string, 'rbac-keyvault-app-config')
  params: {
    resourceId: avmKeyVault.outputs.resourceId
    principalId: avmAppConfig.outputs.systemAssignedMIPrincipalId
    roleDefinitionId: 'b86a8fe4-44ce-4948-aee5-eccb2c155cd7' // 'Key Vault Secrets User'
    roleName: 'Key Vault Secret User'
    principalType: 'ServicePrincipal'
  }
}

// ========== Container Registry ========== //
module avmContainerRegistry 'modules/container-registry.bicep' = {
  //name: format(deployment_param.resource_name_format_string, abbrs.containers.containerRegistry)
  params: {
    containerRegistryParams: {
      acrName: '${deployment_param.naming_abbrs.containers.containerRegistry}${replace(deployment_param.solution_prefix, '-', '')}'
      location: deployment_param.resource_group_location
      acrSku: 'Basic'
      publicNetworkAccess: 'Enabled'
      zoneRedundancy: 'Disabled'

      //<======================= WAF related parameters
      privateEndpoints: (deployment_param.enable_waf)
        ? [
            {
              name: 'container-registry-private-endpoint'
              privateEndpointResourceId: avmVirtualNetwork.outputs.resourceId
              privateDnsZoneGroup: {
                privateDnsZoneGroupConfigs: [
                  {
                    name: 'container-registry-dns-zone-group'
                    privateDnsZoneResourceId: avmPrivateDnsZoneContainerRegistry.outputs.resourceId
                  }
                ]
              }
              subnetResourceId: avmVirtualNetwork.outputs.subnetResourceIds[0] // Use the backend subnet
            }
          ]
        : []
    }
    defaultDeploymentParams: deployment_param
  }
}

// // ========== Storage Account ========== //
module avmStorageAccount 'br/public:avm/res/storage/storage-account:0.20.0' = {
  name: format(deployment_param.resource_name_format_string, deployment_param.naming_abbrs.storage.storageAccount)
  params: {
    name: '${deployment_param.naming_abbrs.storage.storageAccount}${replace(deployment_param.solution_prefix, '-', '')}'
    location: deployment_param.resource_group_location
    skuName: 'Standard_LRS'
    kind: 'StorageV2'
    managedIdentities: { systemAssigned: true }
    minimumTlsVersion: 'TLS1_2'
    roleAssignments: [
      {
        principalId: avmManagedIdentity.outputs.principalId
        roleDefinitionIdOrName: 'Storage Blob Data Contributor'
      }
    ]
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
      ipRules: []
    }
    supportsHttpsTrafficOnly: true
    accessTier: 'Hot'

    //<======================= WAF related parameters
    allowBlobPublicAccess: (!deployment_param.enable_waf) // Disable public access when WAF is enabled
    publicNetworkAccess: (deployment_param.enable_waf) ? 'Disabled' : 'Enabled'
    privateEndpoints: (deployment_param.enable_waf)
      ? [
          {
            name: 'storage-private-endpoint-blob'
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                {
                  name: 'storage-dns-zone-group-blob'
                  privateDnsZoneResourceId: avmPrivateDnsZoneStorage[0].outputs.resourceId
                }
              ]
            }
            subnetResourceId: avmVirtualNetwork.outputs.subnetResourceIds[0] // Use the backend subnet
            service: 'blob'
          }
          {
            name: 'storage-private-endpoint-queue'
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                {
                  name: 'storage-dns-zone-group-queue'
                  privateDnsZoneResourceId: avmPrivateDnsZoneStorage[1].outputs.resourceId
                }
              ]
            }
            subnetResourceId: avmVirtualNetwork.outputs.subnetResourceIds[0] // Use the backend subnet
            service: 'queue'
          }
        ]
      : []

    // privateEndpoints: (deployment_param.enable_waf)
    //   ? map(items(appStoragePrivateDnsZones), zone => {
    //       name: 'storage-${zone.value}'
    //       privateEndpointResourceId: avmVirtualNetwork.outputs.resourceId
    //       service: zone.key
    //       privateDnsZoneGroup: {
    //         privateDnsZoneGroupConfigs: [
    //           {
    //             name: 'storage-dns-zone-group-${zone.value}'
    //             privateDnsZoneResourceId: zone.value
    //           }
    //         ]
    //       }
    //       subnetResourceId: avmVirtualNetwork.outputs.subnetResourceIds[0] // Use the backend subnet
    //     })
    //   : []
  }
}

module avmStorageAccount_RoleAssignment_avmContainerApp_blob 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: format(deployment_param.resource_name_format_string, 'rbac-storage-data-contributor-container-app')
  params: {
    resourceId: avmStorageAccount.outputs.resourceId
    principalId: avmContainerApp.outputs.?systemAssignedMIPrincipalId
    roleName: 'Storage Blob Data Contributor'
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' //'Storage Blob Data Contributor'
    principalType: 'ServicePrincipal'
  }
}

module avmStorageAccount_RoleAssignment_avmContainerApp_API_blob 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: format(deployment_param.resource_name_format_string, 'rbac-storage-data-contributor-container-api')
  params: {
    resourceId: avmStorageAccount.outputs.resourceId
    principalId: avmContainerApp_API.outputs.?systemAssignedMIPrincipalId
    roleName: 'Storage Blob Data Contributor'
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' //'Storage Blob Data Contributor'
    principalType: 'ServicePrincipal'
  }
}

module avmStorageAccount_RoleAssignment_avmContainerApp_queue 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: format(deployment_param.resource_name_format_string, 'rbac-storage-contributor-container-app-queue')
  params: {
    resourceId: avmStorageAccount.outputs.resourceId
    principalId: avmContainerApp.outputs.?systemAssignedMIPrincipalId
    roleName: 'Storage Queue Data Contributor'
    roleDefinitionId: '974c5e8b-45b9-4653-ba55-5f855dd0fb88' //'Storage Queue Data Contributor'
    principalType: 'ServicePrincipal'
  }
}

module avmStorageAccount_RoleAssignment_avmContainerApp_API_queue 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: format(deployment_param.resource_name_format_string, 'rbac-storage-data-contributor-container-api-queue')
  params: {
    resourceId: avmStorageAccount.outputs.resourceId
    principalId: avmContainerApp_API.outputs.?systemAssignedMIPrincipalId
    roleName: 'Storage Queue Data Contributor'
    roleDefinitionId: '974c5e8b-45b9-4653-ba55-5f855dd0fb88' //'Storage Queue Data Contributor'
    principalType: 'ServicePrincipal'
  }
}

// // ========== AI Foundry and related resources ========== //
module avmAiServices 'br/public:avm/res/cognitive-services/account:0.10.2' = {
  name: format(deployment_param.resource_name_format_string, deployment_param.naming_abbrs.ai.aiServices)
  params: {
    name: '${deployment_param.naming_abbrs.ai.aiServices}${deployment_param.solution_prefix}'
    location: deployment_param.resource_group_location
    sku: 'S0'
    managedIdentities: { systemAssigned: true }
    kind: 'AIServices'
    tags: {
      app: deployment_param.solution_prefix
      location: deployment_param.resource_group_location
    }
    customSubDomainName: '${deployment_param.naming_abbrs.ai.aiServices}${deployment_param.solution_prefix}'
    diagnosticSettings: [
      {
        workspaceResourceId: avmAppInsightsLogAnalyticsWorkspace.outputs.logAnalyticsWorkspaceResourceId
      }
    ]
    disableLocalAuth: true

    deployments: [
      {
        name: ai_deployment.gpt_model_name
        model: {
          format: 'OpenAI'
          name: ai_deployment.gpt_model_name
          version: ai_deployment.gpt_model_version
        }
        sku: {
          name: ai_deployment.gpt_deployment_type_name
          capacity: ai_deployment.gpt_deployment_capacity
        }
        raiPolicyName: 'Microsoft.Default'
      }
    ]

    // WAF related parameters
    //publicNetworkAccess: (deployment_param.enable_waf) ? 'Disabled' : 'Enabled'
    publicNetworkAccess: 'Enabled' // Always enabled for AI Services
    // privateEndpoints: (deployment_param.enable_waf)
    //   ? [
    //       {
    //         name: 'ai-services-private-endpoint'
    //         privateEndpointResourceId: avmVirtualNetwork.outputs.resourceId
    //         privateDnsZoneGroup: {
    //           privateDnsZoneGroupConfigs: [
    //             {
    //               name: 'ai-services-dns-zone-cognitiveservices'
    //               privateDnsZoneResourceId: avmPrivateDnsZoneAiServices[0].outputs.resourceId
    //             }
    //             {
    //               name: 'ai-services-dns-zone-openai'
    //               privateDnsZoneResourceId: avmPrivateDnsZoneAiServices[1].outputs.resourceId
    //             }
    //             {
    //               name: 'ai-services-dns-zone-azure'
    //               privateDnsZoneResourceId: avmPrivateDnsZoneAiServices[2].outputs.resourceId
    //             }
    //             {
    //               name: 'ai-services-dns-zone-contentunderstanding'
    //               privateDnsZoneResourceId: avmPrivateDnsZoneAiServices[3].outputs.resourceId
    //             }
    //           ]
    //         }
    //         subnetResourceId: avmVirtualNetwork.outputs.subnetResourceIds[0] // Use the backend subnet
    //       }
    //     ]
    //   : []
  }
}

// Role Assignment
module avmAiServices_roleAssignment 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: format(deployment_param.resource_name_format_string, 'rbac-ai-services')
  params: {
    resourceId: avmAiServices.outputs.resourceId
    principalId: avmContainerApp.outputs.?systemAssignedMIPrincipalId
    roleName: 'Cognitive Services OpenAI User'
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' //'Cognitive Services OpenAI User'
    principalType: 'ServicePrincipal'
  }
}

module avmAiServices_cu 'br/public:avm/res/cognitive-services/account:0.10.2' = {
  name: format(deployment_param.resource_name_format_string, 'aicu-')

  params: {
    name: 'aicu-${deployment_param.solution_prefix}'
    location: contentUnderstandingLocation
    sku: 'S0'
    managedIdentities: { systemAssigned: true }
    kind: 'AIServices'
    tags: {
      app: deployment_param.solution_prefix
      location: deployment_param.resource_group_location
    }
    customSubDomainName: 'aicu-${deployment_param.solution_prefix}'
    disableLocalAuth: true

    publicNetworkAccess: 'Enabled' // Always enabled for AI Services
    // WAF related parameters
    //   publicNetworkAccess: (deployment_param.enable_waf) ? 'Disabled' : 'Enabled'
    //   privateEndpoints: (deployment_param.enable_waf)
    //     ? [
    //         {
    //           name: 'aicu-private-endpoint'
    //           privateEndpointResourceId: avmVirtualNetwork.outputs.resourceId
    //           privateDnsZoneGroup: {
    //             privateDnsZoneGroupConfigs: [
    //               {
    //                 name: 'aicu-dns-zone-cognitiveservices'
    //                 privateDnsZoneResourceId: avmPrivateDnsZoneAiServices[0].outputs.resourceId
    //               }
    //               {
    //                 name: 'aicu-dns-zone-contentunderstanding'
    //                 privateDnsZoneResourceId: avmPrivateDnsZoneAiServices[3].outputs.resourceId
    //               }
    //             ]
    //           }
    //           subnetResourceId: avmVirtualNetwork.outputs.subnetResourceIds[0] // Use the backend subnet
    //         }
    //       ]
    //     : []
  }
}

module avmAiServices_cu_roleAssignment 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: format(deployment_param.resource_name_format_string, 'rbac-ai-services-cu')
  params: {
    resourceId: avmAiServices_cu.outputs.resourceId
    principalId: avmContainerApp.outputs.?systemAssignedMIPrincipalId
    roleDefinitionId: 'a97b65f3-24c7-4388-baec-2e87135dc908' //'Cognitive Services User'
    principalType: 'ServicePrincipal'
  }
}

module avmAiServices_storage_hub 'br/public:avm/res/storage/storage-account:0.20.0' = {
  name: format(deployment_param.resource_name_format_string, 'aistoragehub-')
  params: {
    name: 'aisthub${replace(deployment_param.solution_prefix, '-', '')}'
    location: deployment_param.resource_group_location
    skuName: 'Standard_LRS'
    kind: 'StorageV2'
    managedIdentities: { systemAssigned: true }
    minimumTlsVersion: 'TLS1_2'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
    supportsHttpsTrafficOnly: true
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowCrossTenantReplication: false
    allowSharedKeyAccess: false
    diagnosticSettings: [
      {
        //workspaceResourceId: avmLogAnalyticsWorkspace.outputs.resourceId
        workspaceResourceId: avmAppInsightsLogAnalyticsWorkspace.outputs.logAnalyticsWorkspaceResourceId
      }
    ]
    blobServices: {
      deleteRetentionPolicyEnabled: false
      containerDeleteRetentionPolicyDays: 7
      containerDeleteRetentionPoloicyEnabled: false
      diagnosticSettings: [
        {
          //workspaceResourceId: avmLogAnalyticsWorkspace.outputs.resourceId
          workspaceResourceId: avmAppInsightsLogAnalyticsWorkspace.outputs.logAnalyticsWorkspaceResourceId
        }
      ]
    }

    roleAssignments: [
      {
        principalId: avmManagedIdentity.outputs.principalId
        roleDefinitionIdOrName: 'Storage Blob Data Contributor'
      }
    ]

    publicNetworkAccess: 'Enabled' // Always enabled for AI Storage Hub
    // WAF related parameters
    // publicNetworkAccess: (deployment_param.enable_waf) ? 'Disabled' : 'Enabled'
    // privateEndpoints: (deployment_param.enable_waf)
    //   ? [
    //       {
    //         name: 'aistoragehub-private-endpoint-blob'
    //         privateEndpointResourceId: avmVirtualNetwork.outputs.resourceId
    //         service: 'blob'
    //         privateDnsZoneGroup: {
    //           privateDnsZoneGroupConfigs: [
    //             {
    //               name: 'aistoragehub-dns-zone-blob'
    //               privateDnsZoneResourceId: avmPrivateDnsZoneStorage[0].outputs.resourceId
    //             }
    //           ]
    //         }
    //         subnetResourceId: avmVirtualNetwork.outputs.subnetResourceIds[0] // Use the backend subnet
    //       }
    //       {
    //         name: 'aistoragehub-private-endpoint-file'
    //         privateEndpointResourceId: avmVirtualNetwork.outputs.resourceId
    //         service: 'file'
    //         privateDnsZoneGroup: {
    //           privateDnsZoneGroupConfigs: [
    //             {
    //               name: 'aistoragehub-dns-zone-file'
    //               privateDnsZoneResourceId: avmPrivateDnsZoneStorage[2].outputs.resourceId
    //             }
    //           ]
    //         }
    //         subnetResourceId: avmVirtualNetwork.outputs.subnetResourceIds[0] // Use the backend subnet
    //       }
    //     ]
    //   : []
  }
}

module avmAiHub 'br/public:avm/res/machine-learning-services/workspace:0.12.1' = {
  name: format(deployment_param.resource_name_format_string, deployment_param.naming_abbrs.ai.aiHub)
  params: {
    name: '${deployment_param.naming_abbrs.ai.aiHub}${deployment_param.solution_prefix}'
    friendlyName: '${deployment_param.naming_abbrs.ai.aiHub}${deployment_param.solution_prefix}'
    description: 'AI Hub for CPS template'
    location: deployment_param.resource_group_location
    sku: 'Basic'
    managedIdentities: { systemAssigned: true }
    tags: {
      app: deployment_param.solution_prefix
      location: deployment_param.resource_group_location
    }
    // dependent resources
    associatedKeyVaultResourceId: avmKeyVault.outputs.resourceId
    associatedStorageAccountResourceId: avmAiServices_storage_hub.outputs.resourceId
    associatedContainerRegistryResourceId: avmContainerRegistry.outputs.resourceId
    associatedApplicationInsightsResourceId: avmAppInsightsLogAnalyticsWorkspace.outputs.applicationInsightsId

    kind: 'Hub'
    connections: [
      {
        name: 'AzureOpenAI-Connection'
        category: 'AIServices'
        target: avmAiServices.outputs.endpoint
        connectionProperties: {
          authType: 'AAD'
        }
        isSharedToAll: true

        metadata: {
          description: 'Connection to Azure OpenAI'
          ApiType: 'Azure'
          resourceId: avmAiServices.outputs.resourceId
        }
      }
    ]

    publicNetworkAccess: 'Enabled' // Always enabled for AI Hub
    //<======================= WAF related parameters
    // publicNetworkAccess: (deployment_param.enable_waf) ? 'Disabled' : 'Enabled'
    // privateEndpoints: (deployment_param.enable_waf)
    //   ? [
    //       {
    //         name: 'ai-hub-private-endpoint'
    //         privateEndpointResourceId: avmVirtualNetwork.outputs.resourceId
    //         privateDnsZoneGroup: {
    //           privateDnsZoneGroupConfigs: [
    //             {
    //               name: 'ai-hub-dns-zone-amlworkspace'
    //               privateDnsZoneResourceId: avmPrivateDnsZoneAiFoundryWorkspace[0].outputs.resourceId
    //             }
    //             {
    //               name: 'ai-hub-dns-zone-notebooks'
    //               privateDnsZoneResourceId: avmPrivateDnsZoneAiFoundryWorkspace[1].outputs.resourceId
    //             }
    //           ]
    //         }
    //         subnetResourceId: avmVirtualNetwork.outputs.subnetResourceIds[0] // Use the backend subnet
    //       }
    //     ]
    //   : []
  }
}

module avmAiProject 'br/public:avm/res/machine-learning-services/workspace:0.12.1' = {
  name: format(deployment_param.resource_name_format_string, deployment_param.naming_abbrs.ai.aiHubProject)
  params: {
    name: '${deployment_param.naming_abbrs.ai.aiHubProject}${deployment_param.solution_prefix}'
    location: deployment_param.resource_group_location
    managedIdentities: { systemAssigned: true }
    kind: 'Project'
    sku: 'Basic'
    friendlyName: '${deployment_param.naming_abbrs.ai.aiHubProject}${deployment_param.solution_prefix}'
    hubResourceId: avmAiHub.outputs.resourceId
  }
}

// ========== Container App Environment ========== //
module avmContainerAppEnv 'br/public:avm/res/app/managed-environment:0.11.1' = {
  name: format(
    deployment_param.resource_name_format_string,
    deployment_param.naming_abbrs.containers.containerAppsEnvironment
  )
  params: {
    name: '${deployment_param.naming_abbrs.containers.containerAppsEnvironment}${deployment_param.solution_prefix}'
    location: deployment_param.resource_group_location
    tags: {
      app: deployment_param.solution_prefix
      location: deployment_param.resource_group_location
    }
    managedIdentities: { systemAssigned: true }
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: avmAppInsightsLogAnalyticsWorkspace.outputs.logAnalyticsWorkspaceId
        sharedKey: avmAppInsightsLogAnalyticsWorkspace.outputs.logAnalyticsWorkspacePrimaryKey
      }
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
    publicNetworkAccess: (deployment_param.enable_waf) ? 'Disabled' : 'Enabled'

    // <========== WAF related parameters
    zoneRedundant: (deployment_param.enable_waf) ? false : true
    infrastructureSubnetResourceId: (deployment_param.enable_waf)
      ? avmVirtualNetwork.outputs.subnetResourceIds[1] // Use the container app subnet
      : null // Use the container app subnet
  }
}

//=========== Managed Identity for Container Registry ========== //
module avmContainerRegistryReader 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.1' = {
  name: format(deployment_param.resource_name_format_string, 'acr-reader-mid-')
  params: {
    name: 'acr-reader-mid${deployment_param.solution_prefix}'
    location: deployment_param.resource_group_location
  }
  scope: resourceGroup(resourceGroup().name)
}

module bicepAcrPullRoleAssignment 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: format(deployment_param.resource_name_format_string, 'rabc-acr-pull')
  params: {
    resourceId: avmContainerRegistry.outputs.resourceId
    principalId: avmContainerRegistryReader.outputs.principalId
    roleDefinitionId: '7f951dda-4ed3-4680-a7ca-43fe172d538d' // AcrPull role
    principalType: 'ServicePrincipal'
  }
  scope: resourceGroup(resourceGroup().name)
}

// ========== Container App  ========== //
module avmContainerApp 'br/public:avm/res/app/container-app:0.16.0' = {
  name: format(deployment_param.resource_name_format_string, 'caapp-')
  params: {
    name: '${deployment_param.naming_abbrs.containers.containerApp}${deployment_param.solution_prefix}-app'
    location: deployment_param.resource_group_location
    environmentResourceId: avmContainerAppEnv.outputs.resourceId
    workloadProfileName: 'Consumption'
    registries: deployment_param.use_local_build == 'localbuild'
      ? [
          {
            server: deployment_param.public_container_image_endpoint
            identity: avmContainerRegistryReader.outputs.principalId
          }
        ]
      : null

    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [
        avmContainerRegistryReader.outputs.resourceId
      ]
    }

    containers: [
      {
        name: '${deployment_param.naming_abbrs.containers.containerApp}${deployment_param.solution_prefix}'
        image: '${deployment_param.public_container_image_endpoint}/contentprocessor:latest'

        resources: {
          cpu: '4'
          memory: '8.0Gi'
        }
        env: [
          {
            name: 'APP_CONFIG_ENDPOINT'
            value: ''
          }
        ]
      }
    ]
    activeRevisionsMode: 'Single'
    ingressExternal: false
    disableIngress: true
    scaleSettings: {
      minReplicas: container_app_deployment.container_app.minReplicas
      maxReplicas: container_app_deployment.container_app.maxReplicas
    }
  }
}

// ========== Container App API ========== //
module avmContainerApp_API 'br/public:avm/res/app/container-app:0.16.0' = {
  name: format(deployment_param.resource_name_format_string, 'caapi-')
  params: {
    name: '${deployment_param.naming_abbrs.containers.containerApp}${deployment_param.solution_prefix}-api'
    location: deployment_param.resource_group_location
    environmentResourceId: avmContainerAppEnv.outputs.resourceId
    workloadProfileName: 'Consumption'
    registries: deployment_param.use_local_build == 'localbuild'
      ? [
          {
            server: deployment_param.public_container_image_endpoint
            image: 'contentprocessorapi'
            imageTag: 'latest'
          }
        ]
      : null

    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [
        avmContainerRegistryReader.outputs.resourceId
      ]
    }

    containers: [
      {
        name: '${deployment_param.naming_abbrs.containers.containerApp}${deployment_param.solution_prefix}-api'
        image: '${deployment_param.public_container_image_endpoint}/contentprocessorapi:latest'
        resources: {
          cpu: '4'
          memory: '8.0Gi'
        }
        env: [
          {
            name: 'APP_CONFIG_ENDPOINT'
            value: ''
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
      minReplicas: container_app_deployment.container_api.minReplicas
      maxReplicas: container_app_deployment.container_api.maxReplicas
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
    ingressAllowInsecure: true
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
module avmContainerApp_Web 'br/public:avm/res/app/container-app:0.16.0' = {
  name: format(deployment_param.resource_name_format_string, 'caweb-')
  params: {
    name: '${deployment_param.naming_abbrs.containers.containerApp}${deployment_param.solution_prefix}-web'
    location: deployment_param.resource_group_location
    environmentResourceId: avmContainerAppEnv.outputs.resourceId
    workloadProfileName: 'Consumption'
    registries: deployment_param.use_local_build == 'localbuild'
      ? [
          {
            server: deployment_param.public_container_image_endpoint
            image: 'contentprocessorweb'
            imageTag: 'latest'
          }
        ]
      : null

    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [
        avmContainerRegistryReader.outputs.resourceId
      ]
    }
    ingressExternal: true
    activeRevisionsMode: 'Single'
    ingressTransport: 'auto'
    ingressAllowInsecure: true
    scaleSettings: {
      minReplicas: container_app_deployment.container_web.minReplicas
      maxReplicas: container_app_deployment.container_web.maxReplicas
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
        name: '${deployment_param.naming_abbrs.containers.containerApp}${deployment_param.solution_prefix}-web'
        image: '${deployment_param.public_container_image_endpoint}/contentprocessorweb:latest'
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
  name: format(deployment_param.resource_name_format_string, deployment_param.naming_abbrs.databases.cosmosDBDatabase)
  params: {
    name: '${deployment_param.naming_abbrs.databases.cosmosDBDatabase}${deployment_param.solution_prefix}'
    location: deployment_param.resource_group_location
    mongodbDatabases: [
      {
        name: 'default'
        tag: 'default database'
      }
    ]
    tags: deployment_param.tags
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
      publicNetworkAccess: (deployment_param.enable_waf) ? 'Disabled' : 'Enabled'
      ipRules: []
      virtualNetworkRules: []
    }

    privateEndpoints: (deployment_param.enable_waf)
      ? [
          {
            name: 'cosmosdb-private-endpoint'
            privateEndpointResourceId: avmVirtualNetwork.outputs.resourceId
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                {
                  name: 'cosmosdb-dns-zone-group'
                  privateDnsZoneResourceId: avmPrivateDnsZoneCosmosMongoDB.outputs.resourceId
                }
              ]
            }
            service: 'MongoDB'
            subnetResourceId: avmVirtualNetwork.outputs.subnetResourceIds[0] // Use the backend subnet
          }
        ]
      : []
  }
}

// ========== App Configuration ========== //
module avmAppConfig 'br/public:avm/res/app-configuration/configuration-store:0.6.3' = {
  name: format(
    deployment_param.resource_name_format_string,
    deployment_param.naming_abbrs.developerTools.appConfigurationStore
  )
  params: {
    name: '${deployment_param.naming_abbrs.developerTools.appConfigurationStore}${deployment_param.solution_prefix}'
    location: deployment_param.resource_group_location

    tags: {
      app: deployment_param.solution_prefix
      location: deployment_param.resource_group_location
    }
    managedIdentities: { systemAssigned: true }
    sku: 'Standard'

    disableLocalAuth: false
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
        value: (deployment_param.enable_waf)
          ? replace(
              avmStorageAccount.outputs.serviceEndpoints.blob,
              'blob.core.windows.net',
              'privatelink.blob.core.windows.net'
            )
          : avmStorageAccount.outputs.serviceEndpoints.blob //TODO: replace with actual blob URL
      }
      {
        name: 'APP_STORAGE_QUEUE_URL'
        value: (deployment_param.enable_waf)
          ? replace(
              avmStorageAccount.outputs.serviceEndpoints.queue,
              'queue.core.windows.net',
              'privatelink.queue.core.windows.net'
            )
          : avmStorageAccount.outputs.serviceEndpoints.queue //TODO: replace with actual queue URL
      }
      {
        name: 'APP_AI_PROJECT_CONN_STR'
        value: '${deployment_param.resource_group_location}.api.azureml.ms;${subscription().subscriptionId};${resourceGroup().name};${avmAiProject.name}'
        //TODO: replace with actual AI project connection string
      }
      {
        name: 'APP_COSMOS_CONNSTR'
        value: (deployment_param.enable_waf)
          ? replace(
              avmCosmosDB.outputs.primaryReadWriteConnectionString,
              'mongo.cosmos.azure.com',
              'privatelink.mongo.cosmos.azure.com'
            )
          : avmCosmosDB.outputs.primaryReadWriteConnectionString
      }
    ]

    publicNetworkAccess: 'Enabled' // Always enabled for App Configuration
    // WAF related parameters
    //   publicNetworkAccess: (deployment_param.enable_waf) ? 'Disabled' : 'Enabled'
    //   privateEndpoints: (deployment_param.enable_waf)
    //     ? [
    //         {
    //           name: 'appconfig-private-endpoint'
    //           privateEndpointResourceId: avmVirtualNetwork.outputs.resourceId
    //           privateDnsZoneGroup: {
    //             privateDnsZoneGroupConfigs: [
    //               {
    //                 name: 'appconfig-dns-zone-group'
    //                 privateDnsZoneResourceId: avmPrivateDnsZoneAppConfig.outputs.resourceId
    //               }
    //             ]
    //           }
    //           subnetResourceId: avmVirtualNetwork.outputs.subnetResourceIds[0] // Use the backend subnet
    //         }
    //       ]
    //     : []
  }
}

module avmAppConfig_update 'br/public:avm/res/app-configuration/configuration-store:0.6.3' = if (deployment_param.enable_waf) {
  name: format(
    deployment_param.resource_name_format_string,
    '${deployment_param.naming_abbrs.developerTools.appConfigurationStore}-update'
  )
  params: {
    name: '${deployment_param.naming_abbrs.developerTools.appConfigurationStore}${deployment_param.solution_prefix}'
    location: deployment_param.resource_group_location

    publicNetworkAccess: 'Disabled'
    privateEndpoints: [
      {
        name: 'appconfig-private-endpoint'
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            {
              name: 'appconfig-dns-zone-group'
              privateDnsZoneResourceId: avmPrivateDnsZoneAppConfig.outputs.resourceId
            }
          ]
        }
        subnetResourceId: avmVirtualNetwork.outputs.subnetResourceIds[0] // Use the backend subnet
      }
    ]
  }

  dependsOn: [
    avmAppConfig
  ]
}

module avmRoleAssignment_container_app 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: format(deployment_param.resource_name_format_string, 'rbac-app-config-data-reader')
  params: {
    resourceId: avmAppConfig.outputs.resourceId
    principalId: avmContainerApp.outputs.?systemAssignedMIPrincipalId
    roleDefinitionId: '516239f1-63e1-4d78-a4de-a74fb236a071' // Built-in
    roleName: 'App Configuration Data Reader'
    principalType: 'ServicePrincipal'
  }
}

module avmRoleAssignment_container_app_api 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: format(deployment_param.resource_name_format_string, 'rbac-app-config-data-reader-api')
  params: {
    resourceId: avmAppConfig.outputs.resourceId
    principalId: avmContainerApp_API.outputs.?systemAssignedMIPrincipalId
    roleDefinitionId: '516239f1-63e1-4d78-a4de-a74fb236a071' // Built-in
    roleName: 'App Configuration Data Reader'
    principalType: 'ServicePrincipal'
  }
}
module avmRoleAssignment_container_app_web 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: format(deployment_param.resource_name_format_string, 'rbac-app-config-data-reader-web')
  params: {
    resourceId: avmAppConfig.outputs.resourceId
    principalId: avmContainerApp_Web.outputs.?systemAssignedMIPrincipalId
    roleDefinitionId: '516239f1-63e1-4d78-a4de-a74fb236a071' // Built-in
    roleName: 'App Configuration Data Reader'
    principalType: 'ServicePrincipal'
  }
}

// ========== Container App Update Modules ========== //
module avmContainerApp_update 'br/public:avm/res/app/container-app:0.16.0' = {
  name: format(deployment_param.resource_name_format_string, 'caapp-update-')
  params: {
    name: '${deployment_param.naming_abbrs.containers.containerApp}${deployment_param.solution_prefix}-app'
    location: deployment_param.resource_group_location
    environmentResourceId: avmContainerAppEnv.outputs.resourceId
    workloadProfileName: 'Consumption'
    registries: deployment_param.use_local_build == 'localbuild'
      ? [
          {
            server: deployment_param.public_container_image_endpoint
            identity: avmContainerRegistryReader.outputs.principalId
          }
        ]
      : null

    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [
        avmContainerRegistryReader.outputs.resourceId
      ]
    }

    containers: [
      {
        name: '${deployment_param.naming_abbrs.containers.containerApp}${deployment_param.solution_prefix}'
        image: '${deployment_param.public_container_image_endpoint}/contentprocessor:latest'

        resources: {
          cpu: '4'
          memory: '8.0Gi'
        }
        env: [
          {
            name: 'APP_CONFIG_ENDPOINT'
            value: (deployment_param.enable_waf)
              ? replace(avmAppConfig.outputs.endpoint, 'azconfig.io', 'privatelink.azconfig.io')
              : avmAppConfig.outputs.endpoint
          }
        ]
      }
    ]
    activeRevisionsMode: 'Single'
    ingressExternal: false
    disableIngress: true
    scaleSettings: {
      minReplicas: container_app_deployment.container_app.minReplicas
      maxReplicas: container_app_deployment.container_app.maxReplicas
    }
  }
  dependsOn: [
    avmStorageAccount_RoleAssignment_avmContainerApp_blob
    avmStorageAccount_RoleAssignment_avmContainerApp_queue
    avmRoleAssignment_container_app
  ]
}

module avmContainerApp_API_update 'br/public:avm/res/app/container-app:0.16.0' = {
  name: format(deployment_param.resource_name_format_string, 'caapi-update-')
  params: {
    name: '${deployment_param.naming_abbrs.containers.containerApp}${deployment_param.solution_prefix}-api'
    location: deployment_param.resource_group_location
    environmentResourceId: avmContainerAppEnv.outputs.resourceId
    workloadProfileName: 'Consumption'
    registries: deployment_param.use_local_build == 'localbuild'
      ? [
          {
            server: deployment_param.public_container_image_endpoint
            image: 'contentprocessorapi'
            imageTag: 'latest'
          }
        ]
      : null

    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [
        avmContainerRegistryReader.outputs.resourceId
      ]
    }

    containers: [
      {
        name: '${deployment_param.naming_abbrs.containers.containerApp}${deployment_param.solution_prefix}-api'
        image: '${deployment_param.public_container_image_endpoint}/contentprocessorapi:latest'
        resources: {
          cpu: '4'
          memory: '8.0Gi'
        }
        env: [
          {
            name: 'APP_CONFIG_ENDPOINT'
            value: replace(avmAppConfig.outputs.endpoint, 'azconfig.io', 'privatelink.azconfig.io')
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
      minReplicas: container_app_deployment.container_api.minReplicas
      maxReplicas: container_app_deployment.container_api.maxReplicas
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
    ingressAllowInsecure: true
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
  dependsOn: [
    avmStorageAccount_RoleAssignment_avmContainerApp_API_blob
    avmStorageAccount_RoleAssignment_avmContainerApp_API_queue
    avmRoleAssignment_container_app_api
  ]
}

output CONTAINER_WEB_APP_NAME string = avmContainerApp_Web.outputs.name
output CONTAINER_API_APP_NAME string = avmContainerApp_API.outputs.name
output CONTAINER_WEB_APP_FQDN string = avmContainerApp_Web.outputs.fqdn
output CONTAINER_API_APP_FQDN string = avmContainerApp_API.outputs.fqdn
