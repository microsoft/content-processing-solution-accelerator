// ============================================================================
// Module: Storage Account
// Description: AVM wrapper for Azure Storage Account
// AVM Module: avm/res/storage/storage-account:0.32.0
// ============================================================================

@description('Name of the storage account.')
param name string

@description('Azure region for the resource.')
param location string

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('Managed identity configuration.')
param managedIdentities object

@description('Minimum TLS version.')
param minimumTlsVersion string = 'TLS1_2'

@description('Role assignments for the storage account.')
param roleAssignments array

@description('Network ACL configuration.')
param networkAcls object

@description('Whether infrastructure encryption is required.')
param requireInfrastructureEncryption bool = false

@description('Whether HTTPS traffic only is enforced.')
param supportsHttpsTrafficOnly bool = true

@description('Access tier for the storage account.')
param accessTier string = 'Hot'

@description('Tags to apply to the resource.')
param tags object = {}

@description('Whether blob public access is allowed.')
param allowBlobPublicAccess bool = false

@description('Public network access setting.')
param publicNetworkAccess string = 'Enabled'

@description('Optional. Private endpoint configuration.')
param privateEndpoints array = []

module storageAccount 'br/public:avm/res/storage/storage-account:0.32.0' = {
  name: take('avm.res.storage.storage-account.${name}', 64)
  params: {
    name: name
    location: location
    enableTelemetry: enableTelemetry
    managedIdentities: managedIdentities
    minimumTlsVersion: minimumTlsVersion
    roleAssignments: roleAssignments
    networkAcls: networkAcls
    requireInfrastructureEncryption: requireInfrastructureEncryption
    supportsHttpsTrafficOnly: supportsHttpsTrafficOnly
    accessTier: accessTier
    tags: tags
    allowBlobPublicAccess: allowBlobPublicAccess
    publicNetworkAccess: publicNetworkAccess
    privateEndpoints: privateEndpoints
  }
}

@description('Resource ID of the storage account.')
output resourceId string = storageAccount.outputs.resourceId

@description('Name of the storage account.')
output name string = storageAccount.outputs.name

@description('Service endpoints exposed by the storage account.')
output serviceEndpoints object = storageAccount.outputs.serviceEndpoints
