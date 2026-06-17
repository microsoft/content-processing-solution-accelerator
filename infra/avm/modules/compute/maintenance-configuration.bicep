// ============================================================================
// Module: Maintenance Configuration
// Description: AVM wrapper for Azure Maintenance Configuration
// AVM Module: avm/res/maintenance/maintenance-configuration:0.4.0
// ============================================================================

@description('Name of the maintenance configuration.')
param name string

@description('Azure region for the resource.')
param location string

@description('Tags to apply to the resource.')
param tags object = {}

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('Optional. Extension properties for the maintenance configuration.')
param extensionProperties object = {}

@description('Maintenance scope for the configuration.')
param maintenanceScope string

@description('Maintenance window configuration.')
param maintenanceWindow object

@description('Visibility of the maintenance configuration.')
param visibility string = 'Custom'

@description('Install patches configuration.')
param installPatches object

module maintenanceConfiguration 'br/public:avm/res/maintenance/maintenance-configuration:0.4.0' = {
  name: take('avm.res.maintenance.maintenance-configuration.${name}', 64)
  params: {
    name: name
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    extensionProperties: extensionProperties
    maintenanceScope: maintenanceScope
    maintenanceWindow: maintenanceWindow
    visibility: visibility
    installPatches: installPatches
  }
}

@description('Resource ID of the maintenance configuration.')
output resourceId string = maintenanceConfiguration.outputs.resourceId

@description('Name of the maintenance configuration.')
output name string = maintenanceConfiguration.outputs.name
