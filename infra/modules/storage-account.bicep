metadata name = 'AVM Storage Account Module'

import {
  default_deployment_param_type as default_deployment_param_type
} from './types.bicep'

param deployment_param default_deployment_param_type

import { roleAssignmentType } from 'br/public:avm/utl/types/avm-common-types:0.5.1'
@description('Optional. Array of role assignments to create.')
param roleAssignments roleAssignmentType[]?

module avmStorageAccount 'br/public:avm/res/storage/storage-account:0.20.0' = {
  name: format(deployment_param.resource_name_format_string, deployment_param.naming_abbrs.storage.storageAccount)
  params: {
    name: '${deployment_param.naming_abbrs.storage.storageAccount}${replace(deployment_param.solution_prefix, '-', '')}'
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
