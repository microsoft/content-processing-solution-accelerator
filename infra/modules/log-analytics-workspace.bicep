@description('The name of Log analytics Workspace')
param name string

@description('Location for the Resource.')
param location string = resourceGroup().location

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('Optional. Tags to be applied to the resources.')
param tags resourceInput<'Microsoft.Resources/resourceGroups@2025-04-01'>.tags = {
  app: 'Content Processing Solution Accelerator'
  location: resourceGroup().location
}

@description('Optional: Existing Log Analytics Workspace Resource ID')
param existingLogAnalyticsWorkspaceId string = '' 

var useExistingWorkspace = !empty(existingLogAnalyticsWorkspaceId)

var existingLawSubscription = useExistingWorkspace ? split(existingLogAnalyticsWorkspaceId, '/')[2] : ''
var existingLawResourceGroup = useExistingWorkspace ? split(existingLogAnalyticsWorkspaceId, '/')[4] : ''
var existingLawName = useExistingWorkspace ? split(existingLogAnalyticsWorkspaceId, '/')[8] : ''

module logAnalyticsWorkspace 'br/public:avm/res/operational-insights/workspace:0.11.2' = if(!useExistingWorkspace) {
  name: take('avm.res.operational-insights.workspace-${name}', 24)
  params: {
    name: name
    location: location
    skuName: 'PerGB2018'
    dataRetention: 30
    diagnosticSettings: [{ useThisWorkspace: true }]
    tags: tags
    enableTelemetry: enableTelemetry
  }
}

resource existingLogAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = if (useExistingWorkspace) {
  name: existingLawName
  scope: resourceGroup(existingLawSubscription, existingLawResourceGroup)
}

var lawKeys = useExistingWorkspace ? listKeys(existingLogAnalyticsWorkspace.id, '2020-08-01') : logAnalyticsWorkspace.outputs.primarySharedKey

output resourceId string = useExistingWorkspace ? existingLogAnalyticsWorkspace.id : logAnalyticsWorkspace.outputs.resourceId 
output logAnalyticsWorkspaceId string = useExistingWorkspace ? existingLogAnalyticsWorkspace.properties.customerId : logAnalyticsWorkspace.outputs.logAnalyticsWorkspaceId
@secure()
output primarySharedKey string = useExistingWorkspace ? lawKeys.primarySharedKey : logAnalyticsWorkspace.outputs.primarySharedKey
