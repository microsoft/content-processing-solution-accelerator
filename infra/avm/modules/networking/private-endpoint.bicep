// ============================================================================
// Module: Private Endpoint
// Description: AVM wrapper for Azure Private Endpoint
// AVM Module: avm/res/network/private-endpoint:0.12.0
// ============================================================================

@description('Name of the private endpoint.')
param name string

@description('Azure region for the resource.')
param location string

@description('Tags to apply to the resource.')
param tags object = {}

@description('Optional. Name of the custom network interface.')
param customNetworkInterfaceName string = ''

@description('Private link service connections.')
param privateLinkServiceConnections array

@description('Optional. Private DNS zone group configuration.')
param privateDnsZoneGroup object?

@description('Resource ID of the subnet used by the private endpoint.')
param subnetResourceId string

module privateEndpoint 'br/public:avm/res/network/private-endpoint:0.12.0' = {
  name: take('avm.res.network.private-endpoint.${name}', 64)
  params: {
    name: name
    location: location
    tags: tags
    customNetworkInterfaceName: !empty(customNetworkInterfaceName) ? customNetworkInterfaceName : null
    privateLinkServiceConnections: privateLinkServiceConnections
    privateDnsZoneGroup: privateDnsZoneGroup
    subnetResourceId: subnetResourceId
  }
}

@description('Resource ID of the private endpoint.')
output resourceId string = privateEndpoint.outputs.resourceId

@description('Name of the private endpoint.')
output name string = privateEndpoint.outputs.name
