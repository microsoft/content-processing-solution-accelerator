// ========== main.bicep ========== //
targetScope = 'resourceGroup'

import {
  default_deployment_param_type
  content_understanding_available_location_type
  gpt_deployment_type
  gpt_model_name_type
  ai_deployment_param_type
  container_app_deployment_info_type
  make_solution_prefix
} from './modules/types.bicep'

// ========== get up parameters from parameter file ========== //
@description('Name of the environment to deploy the solution into:')
param environmentName string
@description('Location for the content understanding service: WestUS | SwedenCentral | AustraliaEast')
param contentUnderstandingLocation content_understanding_available_location_type
@description('Type of GPT deployment to use: Standard | GlobalStandard')
param deploymentType gpt_deployment_type = 'GlobalStandard'
@description('Name of the GPT model to deploy: gpt-4o-mini | gpt-4o | gpt-4')
param gptModelName gpt_model_name_type = 'gpt-4o'
@minLength(1)
@description('Version of the GPT model to deploy:')
@allowed([
  '2024-08-06'
])
param gptModelVersion string = '2024-08-06'
@minValue(10)
@description('Capacity of the GPT deployment: (minimum 10)')
param gptDeploymentCapacity int
param useLocalBuild string = 'false'

// ============ make up Parameters from bicep parameter module ========== //
// module parammaker 'modules/parameters.bicep' = {
//   name: 'parammaker'
//   params: {
//     environmentName: environmentName
//     contentUnderstandingLocation: contentUnderstandingLocation
//     deploymentType: deploymentType
//     gptModelName: gptModelName
//     gptModelVersion: gptModelVersion
//     gptDeploymentCapacity: gptDeploymentCapacity
//     useLocalBuild: useLocalBuild
//   }
// }

// param deployment_parameter default_deployment_param_type
// param ai_deployment_parameter ai_deployment_param_type
// param container_app_parameter container_app_deployment_info_type

// =========== Build Parameters ========== //
var deployment_param default_deployment_param_type = {
  environment_name: environmentName
  unique_id: toLower(uniqueString(subscription().id, environmentName, resourceGroup().location))
  use_local_build: useLocalBuild == 'true' ? 'localbuild' : 'usecontainer'
  solution_prefix: make_solution_prefix(toLower(uniqueString(
    subscription().id,
    environmentName,
    resourceGroup().location
  )))
  secondary_location: 'EastUs2'
  public_container_image_endpoint: 'cpscontainerreg.azurecr.io'
  resource_group_location: resourceGroup().location
  resource_name_prefix: {}
  resource_name_format_string: '{0}avm-cps'
  enable_waf: false
}

var ai_deployment ai_deployment_param_type = {
  gpt_deployment_type_name: deploymentType
  gpt_model_name: gptModelName
  gpt_model_version: gptModelVersion
  gpt_deployment_capacity: gptDeploymentCapacity
  content_understanding_available_location: contentUnderstandingLocation
}

var container_app_deployment container_app_deployment_info_type = {
  container_app: {
    maxReplicas: 1
    minReplicas: 1
  }
  container_web: {
    maxReplicas: 1
    minReplicas: 1
  }
  container_api: {
    maxReplicas: 1
    minReplicas: 1
  }
}
// ========== Load Abbreviations ========== //
var abbrs = loadJsonContent('./abbreviations.json')

// ========== Managed Identity ========== //
module avmManagedIdentity './modules/managed-identity.bicep' = {
  name: format(deployment_param.resource_name_format_string, abbrs.security.managedIdentity)
  params: {
    name: '${abbrs.security.managedIdentity}${deployment_param.solution_prefix}'
    location: deployment_param.resource_group_location
    tags: {
      app: deployment_param.solution_prefix
      location: deployment_param.resource_group_location
    }
  }
}

// Assign Owner role to the managed identity in the resource group
module avmRoleAssignment 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: format(deployment_param.resource_name_format_string, 'role-assignment-owner')
  params: {
    resourceId: avmManagedIdentity.outputs.resourceId
    principalId: avmManagedIdentity.outputs.principalId
    roleDefinitionId: '8e3af657-a8ff-443c-a75c-2fe8c4bcb635'
    principalType: 'ServicePrincipal'
  }
}

// Assign Owner role to the managed identity in the resource group
// module bicepOwnerRoleAssignment 'modules/role_assignment.bicep' = {
//   name: format(deployment_param.resource_name_format_string, 'rbac-owner')
//   params: {
//     managedIdentityResourceId: avmManagedIdentity.outputs.resourceId
//     managedIdentityPrincipalId: avmManagedIdentity.outputs.principalId
//     roleDefinitionId: subscriptionResourceId(
//       'Microsoft.Authorization/roleDefinitions',
//       '8e3af657-a8ff-443c-a75c-2fe8c4bcb635'
//     ) // Built-in role 'Owner'
//   }
// }
// module managedIdentityModule 'deploy_managed_identity.bicep' = {
//   name: 'deploy_managed_identity'
//   params: {
//     solutionName: solutionPrefix
//     miName: '${abbrs.security.managedIdentity}${solutionPrefix}'
//     solutionLocation: resourceGroupLocation
//   }
//   scope: resourceGroup(resourceGroup().name)
// }

// ========== Key Vault Module ========== //
module avmKeyVault './modules/key-vault.bicep' = {
  name: format(deployment_param.resource_name_format_string, abbrs.security.keyVault)
  params: {
    //name: format(deployment_param.resource_name_format_string, abbrs.security.keyVault)
    keyVaultParams: {
      keyvaultName: '${abbrs.security.keyVault}${deployment_param.solution_prefix}'
      location: deployment_param.resource_group_location
      tags: {
        app: deployment_param.solution_prefix
        location: deployment_param.resource_group_location
      }
      roleAssignments: [
        {
          principalId: avmManagedIdentity.outputs.principalId
          roleDefinitionIdOrName: 'Key Vault Administrator'
        }
      ]
      enablePurgeProtection: false
      enableSoftDelete: true
      publicNetworkAccess: 'Enabled'
      keyvaultsku: 'standard'
      // Add missing AVM parameters for parity with classic resource
      enableRbacAuthorization: true
      createMode: 'default'
      enableTelemetry: false
      // networkAcls, privateEndpoints, diagnosticSettings, keys, secrets, lock can be added if needed
      enableVaultForDiskEncryption: true
      enableVaultForTemplateDeployment: true
      softDeleteRetentionInDays: 7
    }
    deployment_param: deployment_param
  }
  scope: resourceGroup(resourceGroup().name)
}

// module kvault 'deploy_keyvault.bicep' = {
//   name: 'deploy_keyvault'
//   params: {
//     solutionLocation: resourceGroupLocation
//     keyvaultName: '${abbrs.security.keyVault}${solutionPrefix}'
//     managedIdentityObjectId: managedIdentityModule.outputs.managedIdentityOutput.objectId
//   }
//   scope: resourceGroup(resourceGroup().name)
// }

// ========== Application insights ========== //
module avmLogAnalyticsWorkspace 'br/public:avm/res/operational-insights/workspace:0.11.2' = {
  name: format(deployment_param.resource_name_format_string, abbrs.managementGovernance.logAnalyticsWorkspace)
  params: {
    name: '${abbrs.managementGovernance.logAnalyticsWorkspace}${deployment_param.solution_prefix}'
    location: deployment_param.resource_group_location
    diagnosticSettings: [{ useThisWorkspace: true }]
    skuName: 'PerGB2018'
    dataRetention: 30
  }
}

module avmApplicationInsights 'br/public:avm/res/insights/component:0.6.0' = {
  name: format(deployment_param.resource_name_format_string, abbrs.managementGovernance.applicationInsights)
  params: {
    name: '${abbrs.managementGovernance.applicationInsights}${deployment_param.solution_prefix}'
    location: deployment_param.resource_group_location
    workspaceResourceId: avmLogAnalyticsWorkspace.outputs.resourceId
    retentionInDays: 30
    kind: 'web'
    disableIpMasking: false
    flowType: 'Bluefield'
    diagnosticSettings: [{ workspaceResourceId: avmLogAnalyticsWorkspace.outputs.resourceId }]
  }
}

// module applicationInsights 'deploy_app_insights.bicep' = {
//   name: 'deploy_app_insights'
//   params: {
//     applicationInsightsName: '${abbrs.managementGovernance.applicationInsights}${solutionPrefix}'
//     logAnalyticsWorkspaceName: '${abbrs.managementGovernance.logAnalyticsWorkspace}${solutionPrefix}'
//   }
// }

// // ========== Container Registry ========== //
module avmContainerRegistry 'br/public:avm/res/container-registry/registry:0.9.1' = {
  name: format(deployment_param.resource_name_format_string, abbrs.containers.containerRegistry)
  params: {
    name: '${abbrs.containers.containerRegistry}${replace(deployment_param.solution_prefix, '-', '')}'
    location: deployment_param.resource_group_location
    acrSku: 'Basic'
    publicNetworkAccess: 'Enabled'
    zoneRedundancy: 'Disabled'
  }
}
// module containerRegistry 'deploy_container_registry.bicep' = {
//   name: 'deploy_container_registry'
//   params: {
//     environmentName: environmentName
//   }
// }

// // ========== Storage Account ========== //
module avmStorageAccount 'br/public:avm/res/storage/storage-account:0.20.0' = {
  name: format(deployment_param.resource_name_format_string, abbrs.storage.storageAccount)
  params: {
    name: '${abbrs.storage.storageAccount}${replace(deployment_param.solution_prefix, '-', '')}'
    location: deployment_param.resource_group_location
    skuName: 'Standard_LRS'
    kind: 'StorageV2'
    managedIdentities: { systemAssigned: true }
    minimumTlsVersion: 'TLS1_2'
    roleAssignments: [
      {
        principalId: avmManagedIdentity.outputs.principalId
        roleDefinitionIdOrName: 'Storage Blob Data Contributor'
      }
      // {
      //   principalId: avmContainerApp.outputs.?systemAssignedMIPrincipalId
      //   roleDefinitionIdOrName: 'Storage Blob Data Contributor'
      // }
      // {
      //   principalId: avmContainerApp.outputs.?systemAssignedMIPrincipalId
      //   roleDefinitionIdOrName: 'Storage Queue Data Contributor'
      // }
    ]
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
      ipRules: []
    }
    supportsHttpsTrafficOnly: true
    accessTier: 'Hot'
  }
}

module avmStorageAccount_RoleAssignment_avmContainerApp_blob 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: format(deployment_param.resource_name_format_string, 'role-assignment-storage-data-contributor-container-app')
  params: {
    resourceId: avmContainerApp.outputs.resourceId
    principalId: avmContainerApp.outputs.?systemAssignedMIPrincipalId
    roleName: 'Storage Blob Data Contributor'
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' //'Storage Blob Data Contributor'
    principalType: 'ServicePrincipal'
  }
}

module avmStorageAccount_RoleAssignment_avmContainerApp_queue 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: format(
    deployment_param.resource_name_format_string,
    'role-assignment-storage-data-contributor-container-app-queue'
  )
  params: {
    resourceId: avmContainerApp.outputs.resourceId
    principalId: avmContainerApp.outputs.?systemAssignedMIPrincipalId
    roleName: 'Storage Queue Data Contributor'
    roleDefinitionId: '974c5e8b-45b9-4653-ba55-5f855dd0fb88' //'Storage Queue Data Contributor'
    principalType: 'ServicePrincipal'
  }
}

// module storage 'deploy_storage_account.bicep' = {
//   name: 'deploy_storage_account'
//   params: {
//     solutionLocation: resourceGroupLocation
//     managedIdentityObjectId: managedIdentityModule.outputs.managedIdentityOutput.objectId
//     saName: '${abbrs.storage.storageAccount}${solutionPrefix}'
//   }
// }

// // ========== AI Foundry and related resources ========== //
// var aiModelDeployments = [
//   {
//     name: gptModelName
//     model: gptModelName
//     version: gptModelVersion
//     sku: {
//       name: deploymentType
//       capacity: gptDeploymentCapacity
//     }
//     raiPolicyName: 'Microsoft.Default'
//   }
// ]

module avmAiServices 'br/public:avm/res/cognitive-services/account:0.10.2' = {
  name: format(deployment_param.resource_name_format_string, abbrs.ai.aiServices)

  params: {
    name: '${abbrs.ai.aiServices}${deployment_param.solution_prefix}'
    location: deployment_param.resource_group_location
    sku: 'S0'
    managedIdentities: { systemAssigned: true }
    kind: 'AIServices'
    tags: {
      app: deployment_param.solution_prefix
      location: deployment_param.resource_group_location
    }
    customSubDomainName: '${abbrs.ai.aiServices}${deployment_param.solution_prefix}'
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    // roleAssignments: [
    //   {
    //     principalId: avmContainerApp.outputs.?systemAssignedMIPrincipalId
    //     roleDefinitionIdOrName: 'Cognitive Services OpenAI User'
    //   }
    // ]
    deployments: [
      {
        name: ai_deployment.gpt_model_name
        model: {
          format: 'OpenAI'
          name: ai_deployment.gpt_model_name
          version: ai_deployment.gpt_model_version
        }
        sku: {
          name: ai_deployment.gpt_deployment_type_name
          capacity: ai_deployment.gpt_deployment_capacity
        }
        raiPolicyName: 'Microsoft.Default'
      }
    ]
  }
}

// Role Assignment
module avmAiServices_roleAssignment 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: format(deployment_param.resource_name_format_string, 'role-assignment-ai-services')
  params: {
    resourceId: avmContainerApp.outputs.resourceId
    principalId: avmContainerApp.outputs.?systemAssignedMIPrincipalId
    roleName: 'Cognitive Services OpenAI User'
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' //'Cognitive Services OpenAI User'
    principalType: 'ServicePrincipal'
  }
}

module avmAiServices_cu 'br/public:avm/res/cognitive-services/account:0.10.2' = {
  name: format(deployment_param.resource_name_format_string, 'aicu-')

  params: {
    name: 'aicu-${deployment_param.solution_prefix}'
    location: contentUnderstandingLocation
    sku: 'S0'
    managedIdentities: { systemAssigned: true }
    kind: 'AIServices'
    tags: {
      app: deployment_param.solution_prefix
      location: deployment_param.resource_group_location
    }
    customSubDomainName: 'aicu-${deployment_param.solution_prefix}'
    disableLocalAuth: true
    // roleAssignments: [
    //   {
    //     principalId: avmContainerApp.outputs.?systemAssignedMIPrincipalId
    //     roleDefinitionIdOrName: 'Cognitive Services User'
    //   }
    // ]
  }
}

module avmAiServices_cu_roleAssignment 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: format(deployment_param.resource_name_format_string, 'role-assignment-ai-services-cu')
  params: {
    resourceId: avmContainerApp.outputs.resourceId
    principalId: avmContainerApp.outputs.?systemAssignedMIPrincipalId
    roleDefinitionId: 'a97b65f3-24c7-4388-baec-2e87135dc908' //'Cognitive Services User'
    principalType: 'ServicePrincipal'
  }
}

module avmAiServices_storage_hub 'br/public:avm/res/storage/storage-account:0.20.0' = {
  name: format(deployment_param.resource_name_format_string, 'aistoragehub-')
  params: {
    name: 'aisthub${replace(deployment_param.solution_prefix, '-', '')}'
    location: deployment_param.resource_group_location
    skuName: 'Standard_LRS'
    kind: 'StorageV2'
    managedIdentities: { systemAssigned: true }
    minimumTlsVersion: 'TLS1_2'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
    supportsHttpsTrafficOnly: true
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowCrossTenantReplication: false
    allowSharedKeyAccess: false
    diagnosticSettings: [
      {
        workspaceResourceId: avmLogAnalyticsWorkspace.outputs.resourceId
      }
    ]
    blobServices: {
      deleteRetentionPolicyEnabled: false
      containerDeleteRetentionPolicyDays: 7
      containerDeleteRetentionPoloicyEnabled: false
      diagnosticSettings: [
        {
          workspaceResourceId: avmLogAnalyticsWorkspace.outputs.resourceId
        }
      ]
    }
    publicNetworkAccess: 'Enabled'
    roleAssignments: [
      {
        principalId: avmManagedIdentity.outputs.principalId
        roleDefinitionIdOrName: 'Storage Blob Data Contributor'
      }
    ]
  }
}

module avmAiHub 'br/public:avm/res/machine-learning-services/workspace:0.12.1' = {
  name: format(deployment_param.resource_name_format_string, abbrs.ai.aiHub)
  params: {
    name: '${abbrs.ai.aiHub}${deployment_param.solution_prefix}'
    friendlyName: '${abbrs.ai.aiHub}${deployment_param.solution_prefix}'
    description: 'AI Hub for CPS template'
    location: deployment_param.resource_group_location
    sku: 'Basic'
    managedIdentities: { systemAssigned: true }
    tags: {
      app: deployment_param.solution_prefix
      location: deployment_param.resource_group_location
    }
    publicNetworkAccess: 'Enabled'
    // dependent resources
    associatedKeyVaultResourceId: avmKeyVault.outputs.resourceId
    associatedStorageAccountResourceId: avmAiServices_storage_hub.outputs.resourceId
    associatedContainerRegistryResourceId: avmContainerRegistry.outputs.resourceId
    associatedApplicationInsightsResourceId: avmApplicationInsights.outputs.resourceId

    kind: 'Hub'
    connections: [
      {
        name: 'AzureOpenAI-Connection'
        category: 'AIServices'
        target: avmAiServices.outputs.endpoint
        connectionProperties: {
          authType: 'AAD'
        }
        isSharedToAll: true

        metadata: {
          description: 'Connection to Azure OpenAI'
          ApiType: 'Azure'
          resourceId: avmAiServices.outputs.resourceId
        }
      }
    ]
  }
}

module avmAiProject 'br/public:avm/res/machine-learning-services/workspace:0.12.1' = {
  name: format(deployment_param.resource_name_format_string, abbrs.ai.aiHubProject)
  params: {
    name: '${abbrs.ai.aiHubProject}${deployment_param.solution_prefix}'
    location: deployment_param.resource_group_location
    managedIdentities: { systemAssigned: true }
    kind: 'Project'
    sku: 'Basic'
    friendlyName: '${abbrs.ai.aiHubProject}${deployment_param.solution_prefix}'
    hubResourceId: avmAiHub.outputs.resourceId
  }
}

// module aifoundry 'deploy_ai_foundry.bicep' = {
//   name: 'deploy_ai_foundry'
//   params: {
//     solutionName: solutionPrefix
//     solutionLocation: resourceGroupLocation
//     keyVaultName: kvault.outputs.keyvaultName
//     cuLocation: contentUnderstandingLocation
//     deploymentType: deploymentType
//     gptModelName: gptModelName
//     gptModelVersion: gptModelVersion
//     gptDeploymentCapacity: gptDeploymentCapacity
//     managedIdentityObjectId: managedIdentityModule.outputs.managedIdentityOutput.objectId
//     containerRegistryId: containerRegistry.outputs.createdAcrId
//     applicationInsightsId: applicationInsights.outputs.id
//   }
//   scope: resourceGroup(resourceGroup().name)
// }

// ========== Container App Environment ========== //
module avmContainerAppEnv 'br/public:avm/res/app/managed-environment:0.11.1' = {
  name: format(deployment_param.resource_name_format_string, abbrs.containers.containerAppsEnvironment)
  params: {
    name: '${abbrs.containers.containerAppsEnvironment}${deployment_param.solution_prefix}'
    location: deployment_param.resource_group_location
    tags: {
      app: deployment_param.solution_prefix
      location: deployment_param.resource_group_location
    }
    managedIdentities: { systemAssigned: true }
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: avmLogAnalyticsWorkspace.outputs.logAnalyticsWorkspaceId
        sharedKey: avmLogAnalyticsWorkspace.outputs.primarySharedKey
      }
    }
    zoneRedundant: false
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

//=========== Managed Identity for Container Registry ========== //
module avmContainerRegistryReader 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.1' = {
  name: format(deployment_param.resource_name_format_string, 'acr-reader-mid-')
  params: {
    name: 'acr-reader-mid${deployment_param.solution_prefix}'
    location: deployment_param.resource_group_location
  }
  scope: resourceGroup(resourceGroup().name)
}

module bicepAcrPullRoleAssignment 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: format(deployment_param.resource_name_format_string, 'rabc-acr-pull')
  params: {
    resourceId: avmContainerRegistry.outputs.resourceId
    principalId: avmContainerRegistryReader.outputs.principalId
    roleDefinitionId: '7f951dda-4ed3-4680-a7ca-43fe172d538d' // AcrPull role
    principalType: 'ServicePrincipal'
  }
}

// module bicepAcrPullRoleAssignment_ 'modules/role_assignment.bicep' = {
//   name: format(deployment_param.resource_name_format_string, 'rbac-acr-pull')
//   params: {
//     managedIdentityResourceId: avmContainerRegistryReader.outputs.resourceId
//     managedIdentityPrincipalId: avmContainerRegistryReader.outputs.principalId
//     roleDefinitionId: subscriptionResourceId(
//       'Microsoft.Authorization/roleDefinitions',
//       '7f951dda-4ed3-4680-a7ca-43fe172d538d'
//     ) // AcrPull role
//   }
// }

// module containerAppEnv './container_app/deploy_container_app_env.bicep' = {
//   name: 'deploy_container_app_env'
//   params: {
//     solutionName: solutionPrefix
//     containerEnvName: '${abbrs.containers.containerAppsEnvironment}${solutionPrefix}'
//     location: secondaryLocation
//     logAnalyticsWorkspaceName: applicationInsights.outputs.logAnalyticsWorkspaceName
//   }
// }

// ========== Container App  ========== //
module avmContainerApp 'br/public:avm/res/app/container-app:0.16.0' = {
  name: format(deployment_param.resource_name_format_string, 'caapp-')
  params: {
    name: '${abbrs.containers.containerApp}${deployment_param.solution_prefix}-app'
    location: deployment_param.resource_group_location
    environmentResourceId: avmContainerAppEnv.outputs.resourceId
    workloadProfileName: 'Consumption'
    registries: deployment_param.use_local_build == 'localbuild'
      ? [
          {
            server: deployment_param.public_container_image_endpoint
            identity: avmContainerRegistryReader.outputs.principalId
          }
        ]
      : null

    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [
        avmContainerRegistryReader.outputs.resourceId
      ]
    }

    containers: [
      {
        name: '${abbrs.containers.containerApp}${deployment_param.solution_prefix}'
        image: '${deployment_param.public_container_image_endpoint}/contentprocessor:latest'

        resources: {
          cpu: '4'
          memory: '8.0Gi'
        }
        env: [
          {
            name: 'APP_CONFIG_ENDPOINT'
            value: avmAppConfig.outputs.endpoint
          }
        ]
      }
    ]

    ingressExternal: false
    scaleSettings: {
      minReplicas: container_app_deployment.container_app.minReplicas
      maxReplicas: container_app_deployment.container_app.maxReplicas
    }
  }
}

// ========== Container App API ========== //
module avmContainerApp_API 'br/public:avm/res/app/container-app:0.16.0' = {
  name: format(deployment_param.resource_name_format_string, 'caapi-')
  params: {
    name: '${abbrs.containers.containerApp}${deployment_param.solution_prefix}-api'
    location: deployment_param.resource_group_location
    environmentResourceId: avmContainerAppEnv.outputs.resourceId
    workloadProfileName: 'Consumption'
    registries: deployment_param.use_local_build == 'localbuild'
      ? [
          {
            server: deployment_param.public_container_image_endpoint
            image: 'contentprocessorapi'
            imageTag: 'latest'
          }
        ]
      : null

    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [
        avmContainerRegistryReader.outputs.resourceId
      ]
    }

    containers: [
      {
        name: '${abbrs.containers.containerApp}${deployment_param.solution_prefix}-api'
        image: '${deployment_param.public_container_image_endpoint}/contentprocessorapi:latest'
        resources: {
          cpu: '4'
          memory: '8.0Gi'
        }
        env: [
          {
            name: 'APP_CONFIG_ENDPOINT'
            value: avmAppConfig.outputs.endpoint
          }
        ]
        probes: [
          // Liveness Probe - Checks if the app is still running
          {
            type: 'Liveness'
            httpGet: {
              path: '/startup' // Your app must expose this endpoint
              port: 80
              scheme: 'HTTP'
            }
            initialDelaySeconds: 5
            periodSeconds: 10
            failureThreshold: 3
          }
          // Readiness Probe - Checks if the app is ready to receive traffic
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
            initialDelaySeconds: 20 // Wait 10s before checking
            periodSeconds: 5 // Check every 15s
            failureThreshold: 10 // Restart if it fails 5 times
          }
        ]
      }
    ]
    scaleSettings: {
      minReplicas: container_app_deployment.container_api.minReplicas
      maxReplicas: container_app_deployment.container_api.maxReplicas
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
    ingressExternal: true
    ingressTransport: 'auto'
    ingressAllowInsecure: true
    corsPolicy: {
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
  }
}

//========== Container App Web ========== //
module avmContainerApp_Web 'br/public:avm/res/app/container-app:0.16.0' = {
  name: format(deployment_param.resource_name_format_string, 'caweb-')
  params: {
    name: '${abbrs.containers.containerApp}${deployment_param.solution_prefix}-web'
    location: deployment_param.resource_group_location
    environmentResourceId: avmContainerAppEnv.outputs.resourceId
    workloadProfileName: 'Consumption'
    registries: deployment_param.use_local_build == 'localbuild'
      ? [
          {
            server: deployment_param.public_container_image_endpoint
            image: 'contentprocessorweb'
            imageTag: 'latest'
          }
        ]
      : null

    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [
        avmContainerRegistryReader.outputs.resourceId
      ]
    }
    ingressExternal: true
    activeRevisionsMode: 'Single'
    ingressTransport: 'auto'
    ingressAllowInsecure: true
    scaleSettings: {
      minReplicas: container_app_deployment.container_web.minReplicas
      maxReplicas: container_app_deployment.container_web.maxReplicas
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
    containers: [
      {
        name: '${abbrs.containers.containerApp}${deployment_param.solution_prefix}-web'
        image: '${deployment_param.public_container_image_endpoint}/contentprocessorweb:latest'
        resources: {
          cpu: '4'
          memory: '8.0Gi'
        }
        env: [
          {
            name: 'APP_API_BASE_URL'
            value: avmContainerApp_API.outputs.fqdn
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
            name: 'APP_CONSOLE_LOG_ENABLED'
            value: 'false'
          }
        ]
      }
    ]
  }
}

// module containerApps './container_app/deploy_container_app_api_web.bicep' = {
//   name: 'deploy_container_app_api_web'
//   params: {
//     solutionName: solutionPrefix
//     location: secondaryLocation
//     appConfigEndPoint: ''
//     containerAppApiEndpoint: ''
//     containerAppWebEndpoint: ''
//     azureContainerRegistry: containerImageEndPoint
//     containerAppEnvId: containerAppEnv.outputs.containerEnvId
//     containerRegistryReaderId: containerAppEnv.outputs.containerRegistryReaderId
//     minReplicaContainerApp: minReplicaContainerApp
//     maxReplicaContainerApp: maxReplicaContainerApp
//     minReplicaContainerApi: minReplicaContainerApi
//     maxReplicaContainerApi: maxReplicaContainerApi
//     minReplicaContainerWeb: minReplicaContainerWeb
//     maxReplicaContainerWeb: maxReplicaContainerWeb
//     useLocalBuild: 'false'
//   }
// }

// ========== Cosmos Database for Mongo DB ========== //
module avmCosmosDB 'br/public:avm/res/document-db/database-account:0.15.0' = {
  name: format(deployment_param.resource_name_format_string, abbrs.databases.cosmosDBDatabase)
  params: {
    name: '${abbrs.databases.cosmosDBDatabase}${deployment_param.solution_prefix}'
    location: deployment_param.resource_group_location
    mongodbDatabases: []
    tags: {
      app: deployment_param.solution_prefix
      location: deployment_param.resource_group_location
    }
    databaseAccountOfferType: 'Standard'
    automaticFailover: false
    serverVersion: '7.0'
    capabilitiesToAdd: [
      'EnableMongo'
      'EnableServerless'
    ]
    enableAnalyticalStorage: true
    defaultConsistencyLevel: 'Session'
    maxIntervalInSeconds: 5
    maxStalenessPrefix: 100
  }
}
// module cosmosdb './deploy_cosmos_db.bicep' = {
//   name: 'deploy_cosmos_db'
//   params: {
//     cosmosAccountName: '${abbrs.databases.cosmosDBDatabase}${solutionPrefix}'
//     solutionLocation: secondaryLocation
//     kind: 'MongoDB'
//   }
// }

// ========== App Configuration ========== //
module avmAppConfig 'br/public:avm/res/app-configuration/configuration-store:0.6.3' = {
  name: format(deployment_param.resource_name_format_string, abbrs.developerTools.appConfigurationStore)
  params: {
    name: '${abbrs.developerTools.appConfigurationStore}${deployment_param.solution_prefix}'
    location: deployment_param.resource_group_location

    tags: {
      app: deployment_param.solution_prefix
      location: deployment_param.resource_group_location
    }
    managedIdentities: { systemAssigned: true }
    sku: 'Standard'
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
    keyValues: [
      {
        name: 'APP_AZURE_OPENAI_ENDPOINT'
        value: avmAiServices.outputs.endpoint //TODO: replace with actual endpoint
      }
      {
        name: 'APP_AZURE_OPENAI_MODEL'
        value: gptModelName
      }
      {
        name: 'APP_CONTENT_UNDERSTANDING_ENDPOINT'
        value: avmAiServices_cu.outputs.endpoint //TODO: replace with actual endpoint
      }
      {
        name: 'APP_COSMOS_CONTAINER_PROCESS'
        value: 'Processes'
      }
      {
        name: 'APP_COSMOS_CONTAINER_SCHEMA'
        value: 'Schemas'
      }
      {
        name: 'APP_COSMOS_DATABASE'
        value: 'ContentProcess'
      }
      {
        name: 'APP_CPS_CONFIGURATION'
        value: 'cps-configuration'
      }
      {
        name: 'APP_CPS_MAX_FILESIZE_MB'
        value: '20'
      }
      {
        name: 'APP_CPS_PROCESSES'
        value: 'cps-processes'
      }
      {
        name: 'APP_LOGGING_ENABLE'
        value: 'False'
      }
      {
        name: 'APP_LOGGING_LEVEL'
        value: 'INFO'
      }
      {
        name: 'APP_MESSAGE_QUEUE_EXTRACT'
        value: 'content-pipeline-extract-queue'
      }
      {
        name: 'APP_MESSAGE_QUEUE_INTERVAL'
        value: '5'
      }
      {
        name: 'APP_MESSAGE_QUEUE_PROCESS_TIMEOUT'
        value: '180'
      }
      {
        name: 'APP_MESSAGE_QUEUE_VISIBILITY_TIMEOUT'
        value: '10'
      }
      {
        name: 'APP_PROCESS_STEPS'
        value: 'extract,map,evaluate,save'
      }
      {
        name: 'APP_STORAGE_BLOB_URL'
        value: avmStorageAccount.outputs.serviceEndpoints.blob //TODO: replace with actual blob URL
      }
      {
        name: 'APP_STORAGE_QUEUE_URL'
        value: avmStorageAccount.outputs.serviceEndpoints.queue //TODO: replace with actual queue URL
      }
      {
        name: 'APP_AI_PROJECT_CONN_STR'
        value: '${deployment_param.resource_group_location}.api.azureml.ms;${subscription().subscriptionId};${resourceGroup().name};${avmAiProject.name}'
        //TODO: replace with actual AI project connection string
      }
    ]
    // roleAssignments: [
    //   {
    //     principalId: avmContainerApp.outputs.?systemAssignedMIPrincipalId
    //     roleDefinitionIdOrName: 'App Configuration Data Reader'
    //   }
    //   {
    //     principalId: avmContainerApp_API.outputs.?systemAssignedMIPrincipalId
    //     roleDefinitionIdOrName: 'App Configuration Data Reader'
    //   }
    // {
    //   principalId: avmContainerApp_Web.outputs.?systemAssignedMIPrincipalId
    //   roleDefinitionIdOrName: 'App Configuration Data Reader'
    // }
    // ]
  }
}

module avmRoleAssignment_container_app 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: format(deployment_param.resource_name_format_string, 'role-assignment-app-config-data-reader')
  params: {
    resourceId: avmContainerApp.outputs.resourceId
    principalId: avmContainerApp.outputs.?systemAssignedMIPrincipalId
    roleDefinitionId: '516239f1-63e1-4d78-a4de-a74fb236a071' // Built-in
    roleName: 'App Configuration Data Reader'
    principalType: 'ServicePrincipal'
  }
}

module avmRoleAssignment_container_app_api 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: format(deployment_param.resource_name_format_string, 'role-assignment-app-config-data-reader-api')
  params: {
    resourceId: avmContainerApp_API.outputs.resourceId
    principalId: avmContainerApp_API.outputs.?systemAssignedMIPrincipalId
    roleDefinitionId: '516239f1-63e1-4d78-a4de-a74fb236a071' // Built-in
    roleName: 'App Configuration Data Reader'
    principalType: 'ServicePrincipal'
  }
}
module avmRoleAssignment_container_app_web 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: format(deployment_param.resource_name_format_string, 'role-assignment-app-config-data-reader-web')
  params: {
    resourceId: avmContainerApp_Web.outputs.resourceId
    principalId: avmContainerApp_Web.outputs.?systemAssignedMIPrincipalId
    roleDefinitionId: '516239f1-63e1-4d78-a4de-a74fb236a071' // Built-in  
    roleName: 'App Configuration Data Reader'
    principalType: 'ServicePrincipal'
  }
}

// module appconfig 'deploy_app_config_service.bicep' = {
//   name: 'deploy_app_config_service'
//   scope: resourceGroup(resourceGroup().name)
//   params: {
//     appConfigName: '${abbrs.developerTools.appConfigurationStore}${solutionPrefix}'
//     storageBlobUrl: storage.outputs.storageBlobUrl
//     storageQueueUrl: storage.outputs.storageQueueUrl
//     openAIEndpoint: aifoundry.outputs.aiServicesTarget
//     contentUnderstandingEndpoint: aifoundry.outputs.aiServicesCUEndpoint
//     gptModelName: gptModelName
//     keyVaultId: kvault.outputs.keyvaultId
//     aiProjectConnectionString: aifoundry.outputs.aiProjectConnectionString
//     cosmosDbName: cosmosdb.outputs.cosmosAccountName
//   }
// }

// // ========== Role Assignments ========== //
// module roleAssignments 'deploy_role_assignments.bicep' = {
//   name: 'deploy_role_assignments'
//   params: {
//     appConfigResourceId: appconfig.outputs.appConfigId
//     conainerAppPrincipalIds: [
//       containerApps.outputs.containerAppPrincipalId
//       containerApps.outputs.containerAppApiPrincipalId
//       containerApps.outputs.containerAppWebPrincipalId
//     ]
//     storageResourceId: storage.outputs.storageId
//     storagePrincipalId: storage.outputs.storagePrincipalId
//     containerApiPrincipalId: containerApps.outputs.containerAppApiPrincipalId
//     containerAppPrincipalId: containerApps.outputs.containerAppPrincipalId
//     aiServiceCUId: aifoundry.outputs.aiServicesCuId
//     aiServiceId: aifoundry.outputs.aiServicesId
//     containerRegistryReaderPrincipalId: containerAppEnv.outputs.containerRegistryReaderPrincipalId
//   }
// }

// module updateContainerApp './container_app/deploy_container_app_api_web.bicep' = {
//   name: 'deploy_update_container_app_update'
//   params: {
//     solutionName: solutionPrefix
//     location: secondaryLocation
//     azureContainerRegistry: useLocalBuildLower == 'true' ? containerRegistry.outputs.acrEndpoint : containerImageEndPoint
//     appConfigEndPoint: appconfig.outputs.appConfigEndpoint
//     containerAppEnvId: containerAppEnv.outputs.containerEnvId
//     containerRegistryReaderId: containerAppEnv.outputs.containerRegistryReaderId
//     containerAppWebEndpoint: containerApps.outputs.containweAppWebEndPoint
//     containerAppApiEndpoint: containerApps.outputs.containweAppApiEndPoint
//     minReplicaContainerApp: minReplicaContainerApp
//     maxReplicaContainerApp: maxReplicaContainerApp
//     minReplicaContainerApi: minReplicaContainerApi
//     maxReplicaContainerApi: maxReplicaContainerApi
//     minReplicaContainerWeb: minReplicaContainerWeb
//     maxReplicaContainerWeb: maxReplicaContainerWeb
//     useLocalBuild: useLocalBuildLower
//   }
//   dependsOn: [roleAssignments]
// }

output CONTAINER_WEB_APP_NAME string = avmContainerApp_Web.outputs.name
output CONTAINER_API_APP_NAME string = avmContainerApp_API.outputs.name
output CONTAINER_WEB_APP_FQDN string = avmContainerApp_Web.outputs.fqdn
output CONTAINER_API_APP_FQDN string = avmContainerApp_API.outputs.fqdn
