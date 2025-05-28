// ========== Managed Identity ========== //
param name string
param location string
param tags object

module avmManagedIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.1' = {
  name: name
  params: {
    name: name
    location: location
    tags: tags
  }
}

output resourceId string = avmManagedIdentity.outputs.resourceId
output principalId string = avmManagedIdentity.outputs.principalId
