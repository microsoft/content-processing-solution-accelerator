// ============================================================================
// Module: Bastion Host
// Description: AVM wrapper for Azure Bastion Host
// AVM Module: avm/res/network/bastion-host:0.8.2
// ============================================================================

@description('Name of the Bastion host.')
param name string

@description('Azure region for the resource.')
param location string

@description('SKU name for the Bastion host.')
param skuName string = 'Standard'

@description('Resource ID of the virtual network hosting the AzureBastionSubnet.')
param virtualNetworkResourceId string

@description('Optional. Diagnostic settings to apply to the Bastion host.')
param diagnosticSettings array?

@description('Tags to apply to the resource.')
param tags object = {}

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('Public IP configuration object for the Bastion host.')
param publicIPAddressObject object

module bastionHost 'br/public:avm/res/network/bastion-host:0.8.2' = {
  name: take('avm.res.network.bastion-host.${name}', 64)
  params: {
    name: name
    location: location
    skuName: skuName
    virtualNetworkResourceId: virtualNetworkResourceId
    diagnosticSettings: diagnosticSettings
    tags: tags
    enableTelemetry: enableTelemetry
    publicIPAddressObject: publicIPAddressObject
  }
}

@description('Resource ID of the Bastion host.')
output resourceId string = bastionHost.outputs.resourceId

@description('Name of the Bastion host.')
output name string = bastionHost.outputs.name
