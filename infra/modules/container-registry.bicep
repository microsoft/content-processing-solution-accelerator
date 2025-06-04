metadata name = 'Container Registry Module'
// AVM-compliant Azure Container Registry deployment

import {
  container_registry_param_type
  default_deployment_param_type
} from './types.bicep'

param containerRegistryParams container_registry_param_type
param defaultDeploymentParams default_deployment_param_type

module avmContainerRegistry 'br/public:avm/res/container-registry/registry:0.9.1' = {
  name: 'deploy_container_registry'
  params: {
    name: containerRegistryParams.acrName
    location: containerRegistryParams.location
    acrSku: containerRegistryParams.acrSku
    publicNetworkAccess: containerRegistryParams.publicNetworkAccess
    zoneRedundancy: containerRegistryParams.zoneRedundancy


  }
}



output resourceId string = avmContainerRegistry.outputs.resourceId
