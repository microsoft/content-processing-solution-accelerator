// Standalone deployment for LLM Token Usage Workbook
// Connects to an existing Application Insights instance from any content processing RG

targetScope = 'resourceGroup'

@description('Full resource ID of the Application Insights instance to query.')
param appInsightsResourceId string

@description('Azure region for the workbook resource.')
param location string = resourceGroup().location

var workbookId = guid(resourceGroup().id, 'token-usage-workbook')
var workbookTemplate = loadTextContent('token-usage-workbook.json')
var workbookContent = replace(workbookTemplate, '__APP_INSIGHTS_RESOURCE_ID__', appInsightsResourceId)

resource workbook 'Microsoft.Insights/workbooks@2022-04-01' = {
  name: workbookId
  location: location
  kind: 'shared'
  properties: {
    displayName: 'LLM Token Usage Dashboard'
    category: 'workbook'
    sourceId: appInsightsResourceId
    serializedData: workbookContent
  }
}

output workbookName string = workbook.name
output workbookId string = workbook.id
