// ============================================================================
// Module: App Configuration
// Description: AVM wrapper for Azure App Configuration
// AVM Module: avm/res/app-configuration/configuration-store:0.9.2
// ============================================================================

@description('Name of the App Configuration store.')
param name string

@description('Azure region for the resource.')
param location string

@description('Whether purge protection is enabled.')
param enablePurgeProtection bool = false

@description('Tags to apply to the resource.')
param tags object = {}

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('Managed identity configuration.')
param managedIdentities object?

@description('SKU for the App Configuration store.')
param sku string = 'Standard'

@description('Optional. Diagnostic settings to apply to the App Configuration store.')
param diagnosticSettings array?

@description('Whether local authentication is disabled.')
param disableLocalAuth bool = false

@description('Optional. Replica locations for the App Configuration store.')
param replicaLocations array = []

@description('Role assignments for the App Configuration store.')
param roleAssignments array = []

@description('Key-values to create in the App Configuration store.')
param keyValues array = []

@description('Public network access setting.')
param publicNetworkAccess string = 'Enabled'

@description('Optional. Private endpoint configuration.')
param privateEndpoints array = []

module appConfiguration 'br/public:avm/res/app-configuration/configuration-store:0.9.2' = {
  name: take('avm.res.app-configuration.configuration-store.${name}', 64)
  params: {
    name: name
    location: location
    enablePurgeProtection: enablePurgeProtection
    tags: tags
    enableTelemetry: enableTelemetry
    managedIdentities: managedIdentities
    sku: sku
    diagnosticSettings: diagnosticSettings
    disableLocalAuth: disableLocalAuth
    replicaLocations: replicaLocations
    roleAssignments: roleAssignments
    keyValues: keyValues
    publicNetworkAccess: publicNetworkAccess
    privateEndpoints: privateEndpoints
  }
}

@description('Resource ID of the App Configuration store.')
output resourceId string = appConfiguration.outputs.resourceId

@description('Name of the App Configuration store.')
output name string = appConfiguration.outputs.name

@description('Endpoint of the App Configuration store.')
output endpoint string = appConfiguration.outputs.endpoint
