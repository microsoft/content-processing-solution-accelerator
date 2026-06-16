// ============================================================================
// Module: Container App
// Description: AVM wrapper for Azure Container Apps
// AVM Module: avm/res/app/container-app:0.22.1
// ============================================================================

@description('Name of the container app.')
param name string

@description('Azure region for the resource.')
param location string

@description('Tags to apply to the resource.')
param tags object = {}

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('Resource ID of the container app environment.')
param environmentResourceId string

@description('Optional. Managed identity configuration.')
param managedIdentities object = {}

@description('Optional. Container registry configuration.')
param registries array = []

@description('Container definitions for the container app.')
param containers array

@description('Optional. Active revisions mode.')
param activeRevisionsMode string = 'Single'

@description('Optional. Minimum replica count alias used when scaleSettings is not supplied.')
param scaleMinReplicas int = -1

@description('Optional. Maximum replica count alias used when scaleSettings is not supplied.')
param scaleMaxReplicas int = -1

@description('Optional. Full scale settings object.')
param scaleSettings object = {}

@description('Optional. Ingress target port.')
param ingressTargetPort int = -1

@description('Whether ingress is external.')
param ingressExternal bool = false

@description('Optional. Ingress transport setting.')
param ingressTransport string = ''

@description('Optional. Secret definitions for the container app.')
param secrets array = []

@description('Optional. Workload profile name.')
param workloadProfileName string = ''

@description('Optional. Whether ingress is disabled.')
param disableIngress bool = false

@description('Optional. Whether insecure ingress traffic is allowed.')
param ingressAllowInsecure bool = false

@description('Optional. CORS policy configuration.')
param corsPolicy object = {}

var resolvedScaleSettings = !empty(scaleSettings)
  ? scaleSettings
  : (scaleMinReplicas != -1 || scaleMaxReplicas != -1
      ? union(
          scaleMinReplicas != -1 ? { minReplicas: scaleMinReplicas } : {},
          scaleMaxReplicas != -1 ? { maxReplicas: scaleMaxReplicas } : {}
        )
      : null)

// ============================================================================
// AVM Module Deployment
// ============================================================================
module containerApp 'br/public:avm/res/app/container-app:0.22.1' = {
  name: take('avm.res.app.container-app.${name}', 64)
  params: {
    name: name
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    environmentResourceId: environmentResourceId
    managedIdentities: empty(managedIdentities) ? null : managedIdentities
    registries: !empty(registries) ? registries : null
    containers: containers
    activeRevisionsMode: !empty(activeRevisionsMode) ? activeRevisionsMode : null
    scaleSettings: resolvedScaleSettings
    ingressTargetPort: ingressTargetPort != -1 ? ingressTargetPort : null
    ingressExternal: ingressExternal
    ingressTransport: !empty(ingressTransport) ? ingressTransport : null
    secrets: !empty(secrets) ? secrets : null
    workloadProfileName: !empty(workloadProfileName) ? workloadProfileName : null
    disableIngress: disableIngress
    ingressAllowInsecure: ingressAllowInsecure
    corsPolicy: empty(corsPolicy) ? null : corsPolicy
  }
}

// ============================================================================
// Outputs
// ============================================================================
@description('Resource ID of the container app.')
output resourceId string = containerApp.outputs.resourceId

@description('Name of the container app.')
output name string = containerApp.outputs.name

@description('Fully qualified domain name of the container app.')
output fqdn string = containerApp.outputs.fqdn

@description('Principal ID of the system-assigned managed identity.')
output systemAssignedMIPrincipalId string? = containerApp.outputs.?systemAssignedMIPrincipalId
