// ============================================================================
// Module: Application Insights
// Description: AVM wrapper for Application Insights component
// AVM Module: avm/res/insights/component:0.7.1
// ============================================================================

@description('Name of the Application Insights component.')
param name string

@description('Azure region for the resource.')
param location string

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('Retention period in days.')
param retentionInDays int = 365

@description('Application type for the component.')
param kind string = 'web'

@description('Whether to disable IP masking.')
param disableIpMasking bool = false

@description('Flow type for the component.')
param flowType string = 'Bluefield'

@description('Resource ID of the Log Analytics workspace connected to the component.')
param workspaceResourceId string = ''

@description('Optional. Diagnostic settings to apply to the component.')
param diagnosticSettings array?

@description('Tags to apply to the resource.')
param tags object = {}

module appInsights 'br/public:avm/res/insights/component:0.7.1' = {
  name: take('avm.res.insights.component.${name}', 64)
  params: {
    name: name
    location: location
    enableTelemetry: enableTelemetry
    retentionInDays: retentionInDays
    kind: kind
    disableIpMasking: disableIpMasking
    flowType: flowType
    workspaceResourceId: workspaceResourceId
    diagnosticSettings: diagnosticSettings
    tags: tags
  }
}

@description('Resource ID of the Application Insights component.')
output resourceId string = appInsights.outputs.resourceId

@description('Name of the Application Insights component.')
output name string = appInsights.outputs.name

@description('Connection string of the Application Insights component.')
output connectionString string = appInsights.outputs.connectionString
