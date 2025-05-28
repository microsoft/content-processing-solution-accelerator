metadata name = 'Key Vault Module'
// ========== Key Vault Module ========== //
// param name string
// param location string
// param tags object
// param roleAssignments array = []
// param enablePurgeProtection bool = false
// param enableSoftDelete bool = true
// param enableVaultForDiskEncryption  bool =   true
// param enableVaultForTemplateDeployment bool = true
// param publicNetworkAccess string = 'Enabled'
// param vaultsku string = 'standard'
// param softDeleteRetentionInDays int = 7
// param enableRbacAuthorization bool = true
// param createMode string = 'default'
// param enableTelemetry bool = true

import {
  key_vault_param_type
} from './types.bicep'

param keyVaultParams key_vault_param_type
param name string

module avmKeyVault 'br/public:avm/res/key-vault/vault:0.12.1' = {
  name: name
  params: {
    name: keyVaultParams.name
    location: keyVaultParams.location
    tags: keyVaultParams.tags
    roleAssignments: keyVaultParams.roleAssignments
    enablePurgeProtection: keyVaultParams.enablePurgeProtection
    enableSoftDelete: keyVaultParams.enableSoftDelete
    enableVaultForDiskEncryption: keyVaultParams.enableVaultForDiskEncryption
    enableVaultForTemplateDeployment: keyVaultParams.enableVaultForTemplateDeployment
    publicNetworkAccess: keyVaultParams.publicNetworkAccess
    sku: keyVaultParams.keyvaultsku
    softDeleteRetentionInDays: keyVaultParams.softDeleteRetentionInDays
    enableRbacAuthorization: keyVaultParams.enableRbacAuthorization
    createMode: keyVaultParams.createMode
    enableTelemetry: keyVaultParams.enableTelemetry
  }
}

output resourceId string = avmKeyVault.outputs.resourceId
output vaultUri string = avmKeyVault.outputs.uri
