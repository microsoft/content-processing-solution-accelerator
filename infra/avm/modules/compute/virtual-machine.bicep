// ============================================================================
// Module: Virtual Machine
// Description: AVM wrapper for Azure Virtual Machine
// AVM Module: avm/res/compute/virtual-machine:0.22.0
// ============================================================================

@description('Name of the virtual machine.')
param name string

@description('Azure region for the resource.')
param location string

@description('Tags to apply to the resource.')
param tags object = {}

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('Optional. Computer name of the virtual machine.')
param computerName string = ''

@description('Operating system type.')
param osType string

@description('Virtual machine size.')
param vmSize string

@description('Administrator username for the virtual machine.')
param adminUsername string

@description('Administrator password for the virtual machine.')
@secure()
param adminPassword string

@description('Optional. Managed identity configuration.')
param managedIdentities object?

@description('Optional. Patch mode for the virtual machine.')
param patchMode string = ''

@description('Optional. Whether platform safety checks should be bypassed for user schedules.')
param bypassPlatformSafetyChecksOnUserSchedule bool = false

@description('Optional. Maintenance configuration resource ID.')
param maintenanceConfigurationResourceId string = ''

@description('Optional. Whether automatic updates are enabled.')
param enableAutomaticUpdates bool = false

@description('Whether to enable encryption at host.')
param encryptionAtHost bool = false

@description('Optional. Availability zone for the virtual machine.')
param availabilityZone int = -1

@description('Image reference used to create the virtual machine.')
param imageReference object

@description('OS disk configuration for the virtual machine.')
param osDisk object

@description('Network interface configurations for the virtual machine.')
param nicConfigurations array

@description('Optional. Azure AD join extension configuration.')
param extensionAadJoinConfig object?

@description('Optional. Anti-malware extension configuration.')
param extensionAntiMalwareConfig object?

@description('Optional. Monitoring agent extension configuration.')
param extensionMonitoringAgentConfig object?

@description('Optional. Network watcher extension configuration.')
param extensionNetworkWatcherAgentConfig object?

module virtualMachine 'br/public:avm/res/compute/virtual-machine:0.22.0' = {
  name: take('avm.res.compute.virtual-machine.${name}', 64)
  params: {
    name: name
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    computerName: !empty(computerName) ? computerName : null
    osType: osType
    vmSize: vmSize
    adminUsername: adminUsername
    adminPassword: adminPassword
    managedIdentities: managedIdentities
    patchMode: !empty(patchMode) ? patchMode : null
    bypassPlatformSafetyChecksOnUserSchedule: bypassPlatformSafetyChecksOnUserSchedule
    maintenanceConfigurationResourceId: !empty(maintenanceConfigurationResourceId) ? maintenanceConfigurationResourceId : null
    enableAutomaticUpdates: enableAutomaticUpdates
    encryptionAtHost: encryptionAtHost
    availabilityZone: availabilityZone
    imageReference: imageReference
    osDisk: osDisk
    nicConfigurations: nicConfigurations
    extensionAadJoinConfig: extensionAadJoinConfig
    extensionAntiMalwareConfig: extensionAntiMalwareConfig
    extensionMonitoringAgentConfig: extensionMonitoringAgentConfig
    extensionNetworkWatcherAgentConfig: extensionNetworkWatcherAgentConfig
  }
}

@description('Resource ID of the virtual machine.')
output resourceId string = virtualMachine.outputs.resourceId

@description('Name of the virtual machine.')
output name string = virtualMachine.outputs.name
