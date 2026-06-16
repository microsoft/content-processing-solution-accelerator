@description('Unique solution suffix used to derive resource names.')
param solutionSuffix string

@description('Azure region for the resource.')
param location string

@description('Resource ID of the container app environment.')
param environmentResourceId string

@description('Container registry endpoint hosting the web image.')
param containerRegistryEndpoint string

@description('Image tag to deploy.')
param imageTag string

@description('Whether additional scale-out should be enabled.')
param enableScalability bool

@description('Tags to apply to the resource.')
param tags object = {}

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('User-assigned managed identity resource IDs to attach to the container app.')
param userAssignedResourceIds array = []

@description('API application FQDN used by the frontend.')
param apiAppFqdn string

var containerAppName = 'ca-${solutionSuffix}-web'
var scaleSettings = {
  maxReplicas: enableScalability ? 3 : 2
  minReplicas: enableScalability ? 2 : 1
  rules: [
    {
      name: 'http-scaler'
      http: {
        metadata: {
          concurrentRequests: '100'
        }
      }
    }
  ]
}

module containerApp './container-app.bicep' = {
  name: take('module.container-app-web.${solutionSuffix}', 64)
  params: {
    name: containerAppName
    location: location
    environmentResourceId: environmentResourceId
    workloadProfileName: 'Consumption'
    enableTelemetry: enableTelemetry
    tags: tags
    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: userAssignedResourceIds
    }
    ingressExternal: true
    ingressTargetPort: 3000
    activeRevisionsMode: 'Single'
    ingressTransport: 'auto'
    ingressAllowInsecure: false
    scaleSettings: scaleSettings
    containers: [
      {
        name: containerAppName
        image: '${containerRegistryEndpoint}/contentprocessorweb:${imageTag}'
        resources: {
          cpu: 4
          memory: '8.0Gi'
        }
        env: [
          {
            name: 'APP_API_BASE_URL'
            value: 'https://${apiAppFqdn}'
          }
          {
            name: 'APP_WEB_CLIENT_ID'
            value: '<APP_REGISTRATION_CLIENTID>'
          }
          {
            name: 'APP_WEB_AUTHORITY'
            value: '${environment().authentication.loginEndpoint}/${tenant().tenantId}'
          }
          {
            name: 'APP_WEB_SCOPE'
            value: '<FRONTEND_API_SCOPE>'
          }
          {
            name: 'APP_API_SCOPE'
            value: '<BACKEND_API_SCOPE>'
          }
          {
            name: 'APP_REDIRECT_URL'
            value: '/'
          }
          {
            name: 'APP_POST_REDIRECT_URL'
            value: '/'
          }
          {
            name: 'APP_CONSOLE_LOG_ENABLED'
            value: 'false'
          }
        ]
      }
    ]
  }
}

@description('Resource ID of the container app.')
output resourceId string = containerApp.outputs.resourceId

@description('Name of the container app.')
output name string = containerApp.outputs.name

@description('Fully qualified domain name of the container app.')
output fqdn string = containerApp.outputs.fqdn

@description('Principal ID of the system-assigned managed identity.')
output systemAssignedMIPrincipalId string? = containerApp.outputs.?systemAssignedMIPrincipalId
