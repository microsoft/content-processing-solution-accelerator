@description('Unique solution suffix used to derive resource names.')
param solutionSuffix string

@description('Azure region for the resource.')
param location string

@description('Resource ID of the container app environment.')
param environmentResourceId string

@description('Container registry endpoint hosting the API image.')
param containerRegistryEndpoint string

@description('Image tag to deploy.')
param imageTag string

@description('Whether additional scale-out should be enabled.')
param enableScalability bool

@description('Whether monitoring is enabled.')
param enableMonitoring bool = false

@description('Optional. Application Insights connection string.')
param appInsightsConnectionString string = ''

@description('Tags to apply to the resource.')
param tags object = {}

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('User-assigned managed identity resource IDs to attach to the container app.')
param userAssignedResourceIds array = []

@description('Optional. App Configuration endpoint for post-bootstrap updates.')
param appConfigEndpoint string = ''

var containerAppName = 'ca-${solutionSuffix}-api'
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
var corsPolicy = {
  allowedOrigins: [
    '*'
  ]
  allowedMethods: [
    'GET'
    'POST'
    'PUT'
    'DELETE'
    'OPTIONS'
  ]
  allowedHeaders: [
    'Authorization'
    'Content-Type'
    '*'
  ]
}

module containerApp './container-app.bicep' = {
  name: take('module.container-app-api.${solutionSuffix}', 64)
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
    containers: [
      {
        name: containerAppName
        image: '${containerRegistryEndpoint}/contentprocessorapi:${imageTag}'
        resources: {
          cpu: 4
          memory: '8.0Gi'
        }
        env: [
          {
            name: 'APP_CONFIG_ENDPOINT'
            value: appConfigEndpoint
          }
          {
            name: 'APP_ENV'
            value: 'prod'
          }
          {
            name: 'APP_LOGGING_LEVEL'
            value: 'INFO'
          }
          {
            name: 'AZURE_PACKAGE_LOGGING_LEVEL'
            value: 'WARNING'
          }
          {
            name: 'AZURE_LOGGING_PACKAGES'
            value: ''
          }
          {
            name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
            value: enableMonitoring ? appInsightsConnectionString : ''
          }
          {
            name: 'OTEL_SERVICE_NAME'
            value: 'ContentProcessorAPI'
          }
        ]
        probes: [
          {
            type: 'Liveness'
            httpGet: {
              path: '/startup'
              port: 80
              scheme: 'HTTP'
            }
            initialDelaySeconds: 5
            periodSeconds: 10
            failureThreshold: 3
          }
          {
            type: 'Readiness'
            httpGet: {
              path: '/startup'
              port: 80
              scheme: 'HTTP'
            }
            initialDelaySeconds: 5
            periodSeconds: 10
            failureThreshold: 3
          }
          {
            type: 'Startup'
            httpGet: {
              path: '/startup'
              port: 80
              scheme: 'HTTP'
            }
            initialDelaySeconds: 20
            periodSeconds: 5
            failureThreshold: 10
          }
        ]
      }
    ]
    scaleSettings: scaleSettings
    ingressExternal: true
    activeRevisionsMode: 'Single'
    ingressTransport: 'auto'
    ingressAllowInsecure: false
    corsPolicy: corsPolicy
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
