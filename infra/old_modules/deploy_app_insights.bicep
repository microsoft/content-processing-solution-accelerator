targetScope = 'resourceGroup'

param applicationInsightsName string
param logAnalyticsWorkspaceName string
param existingLogAnalyticsWorkspaceId string = ''

var useExisting = !empty(existingLogAnalyticsWorkspaceId)
var existingLawSubscriptionId = useExisting ? split(existingLogAnalyticsWorkspaceId, '/')[2] : ''
var existingLawResourceGroup = useExisting ? split(existingLogAnalyticsWorkspaceId, '/')[4] : ''
var existingLawName = useExisting ? split(existingLogAnalyticsWorkspaceId, '/')[8] : ''

resource existingLogAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2020-08-01' existing = if (useExisting) {
  name: existingLawName
  scope: resourceGroup(existingLawSubscriptionId, existingLawResourceGroup)
}

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = if (!useExisting) {
  name: logAnalyticsWorkspaceName
  location: resourceGroup().location
  properties: any({
    retentionInDays: 30
    features: {
      searchVersion: 1
    }
    sku: {
      name: 'PerGB2018'
    }
  })
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: applicationInsightsName
  location: resourceGroup().location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    DisableIpMasking: false
    DisableLocalAuth: false
    Flow_Type: 'Bluefield'
    ForceCustomerStorageForProfiler: false
    ImmediatePurgeDataOn30Days: true
    IngestionMode: 'LogAnalytics'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Disabled'
    Request_Source: 'rest'
    WorkspaceResourceId: useExisting ? existingLogAnalyticsWorkspace.id : logAnalyticsWorkspace.id
  }
}

output id string = applicationInsights.id
output logAnalyticsWorkspaceName string = useExisting ? existingLogAnalyticsWorkspace.name : logAnalyticsWorkspace.name
output logAnalyticsWorkspaceSubscription string = useExisting ? existingLawSubscriptionId : split(subscription().id, '/')[2]
output logAnalyticsWorkspaceResourceGroup string = useExisting ? existingLawResourceGroup : resourceGroup().name
