// modules/app-insights-avm.bicep
metadata name = 'AVM Application Insights and Log Analytics Workspace Module'
// AVM-compliant Application Insights and Log Analytics Workspace deployment
// param applicationInsightsName string
// param logAnalyticsWorkspaceName string
// param location string
// param dataRetention int = 30
// param skuName string = 'PerGB2018'
// param kind string = 'web'
// param disableIpMasking bool = false
// param flowType string = 'Bluefield'

import {
  app_insights_param_type
  default_deployment_param_type
} from './types.bicep'


param appInsights_param app_insights_param_type
param deployment_param default_deployment_param_type

module avmLogAnalyticsWorkspace 'br/public:avm/res/operational-insights/workspace:0.11.2' = {
  name: 'deploy_log_analytics_workspace'
  params: {
    name: appInsights_param.logAnalyticsWorkspaceName
    location: appInsights_param.location
    skuName: appInsights_param.skuName
    dataRetention: appInsights_param.retentionInDays
    diagnosticSettings: [ { useThisWorkspace: true }] //TODO: Add as a parameter
    // features: {
    //   searchVersion: appInsights_param.features.searchVersion
    // }
  }
}

module avmApplicationInsights 'br/public:avm/res/insights/component:0.6.0' = {
  name: 'deploy_application_insights'
  params: {
    name: appInsights_param.appInsightsName
    location: appInsights_param.location
    workspaceResourceId: avmLogAnalyticsWorkspace.outputs.resourceId
    kind: appInsights_param.kind
    applicationType: appInsights_param.applicationType
    disableIpMasking: appInsights_param.disableIpMasking
    disableLocalAuth: appInsights_param.disableLocalAuth
    flowType: appInsights_param.flowType
    //forceCustomerStorageForProfiler: appInsights_param.forceCustomerStorageForProfiler
    //immediatePurgeDataOn30Days: false
    //IngestionMode: 'LogAnalytics'
    //publicNetworkAccessForIngestion: appInsights_param.publicNetworkAccessForIngestion
    publicNetworkAccessForQuery: appInsights_param.publicNetworkAccessForQuery
    requestSource: appInsights_param.requestSource

  }
}

output applicationInsightsId string = avmApplicationInsights.outputs.resourceId
output logAnalyticsWorkspaceId string = avmLogAnalyticsWorkspace.outputs.logAnalyticsWorkspaceId
output logAnalyticsWorkspaceResourceId string = avmLogAnalyticsWorkspace.outputs.resourceId
output logAnalyticsWorkspaceName string = avmLogAnalyticsWorkspace.outputs.name
@secure()
output logAnalyticsWorkspacePrimaryKey string = avmLogAnalyticsWorkspace.outputs.primarySharedKey
