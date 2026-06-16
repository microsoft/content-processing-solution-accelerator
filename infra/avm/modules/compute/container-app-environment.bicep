// ============================================================================
// Module: Container App Environment
// Description: AVM wrapper for Azure Container Apps managed environment
// AVM Module: avm/res/app/managed-environment:0.13.2
// ============================================================================

@description('Name of the container app environment.')
param name string

@description('Azure region for the resource.')
param location string

@description('Tags to apply to the resource.')
param tags object = {}

@description('Managed identity configuration.')
param managedIdentities object

@description('Optional. Application logs configuration.')
param appLogsConfiguration object?

@description('Workload profiles for the environment.')
param workloadProfiles array

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('Public network access setting.')
param publicNetworkAccess string = 'Enabled'

@description('Optional. Platform reserved CIDR block.')
param platformReservedCidr string = ''

@description('Optional. Platform reserved DNS IP.')
param platformReservedDnsIP string = ''

@description('Whether the environment is zone redundant.')
param zoneRedundant bool = false

@description('Optional. Infrastructure subnet resource ID.')
param infrastructureSubnetResourceId string = ''

module containerAppEnvironment 'br/public:avm/res/app/managed-environment:0.13.2' = {
  name: take('avm.res.app.managed-environment.${name}', 64)
  params: {
    name: name
    location: location
    tags: tags
    managedIdentities: managedIdentities
    appLogsConfiguration: appLogsConfiguration
    workloadProfiles: workloadProfiles
    enableTelemetry: enableTelemetry
    publicNetworkAccess: publicNetworkAccess
    platformReservedCidr: !empty(platformReservedCidr) ? platformReservedCidr : null
    platformReservedDnsIP: !empty(platformReservedDnsIP) ? platformReservedDnsIP : null
    zoneRedundant: zoneRedundant
    infrastructureSubnetResourceId: !empty(infrastructureSubnetResourceId) ? infrastructureSubnetResourceId : null
  }
}

@description('Resource ID of the container app environment.')
output resourceId string = containerAppEnvironment.outputs.resourceId

@description('Name of the container app environment.')
output name string = containerAppEnvironment.outputs.name
