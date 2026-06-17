// ============================================================================
// Module: Data Collection Rule
// Description: AVM wrapper for Azure Monitor data collection rules
// AVM Module: avm/res/insights/data-collection-rule:0.11.0
// ============================================================================

@description('Name of the data collection rule.')
param name string

@description('Azure region for the resource.')
param location string

@description('Tags to apply to the resource.')
param tags object = {}

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('Properties block for the data collection rule.')
param dataCollectionRuleProperties object

module dataCollectionRule 'br/public:avm/res/insights/data-collection-rule:0.11.0' = {
  name: take('avm.res.insights.data-collection-rule.${name}', 64)
  params: {
    name: name
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    dataCollectionRuleProperties: dataCollectionRuleProperties
  }
}

@description('Resource ID of the data collection rule.')
output resourceId string = dataCollectionRule.outputs.resourceId

@description('Name of the data collection rule.')
output name string = dataCollectionRule.outputs.name
