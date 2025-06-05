@export()
type content_understanding_available_location_type = 'WestUS' | 'SwedenCentral' | 'AustraliaEast'
@export()
type gpt_deployment_type = 'Standard' | 'GlobalStandard'
@export()
type gpt_model_name_type = 'gpt-4o-mini' | 'gpt-4o' | 'gpt-4'
@export()
type gpt_model_version_type = '2024-08-06'
@export()
type container_app_deployment_type = 'localbuild' | 'usecontainer' // This file defines the types used in the Bicep deployment scripts for the CPS solution.

@export()
type ai_deployment_param_type = {
  @description('GPT model deployment type:')
  gpt_deployment_type_name: gpt_deployment_type

  @description('Name of the GPT model to deploy:')
  gpt_model_name: gpt_model_name_type

  @description('Version of the GPT model to deploy:')
  gpt_model_version: gpt_model_version_type

  @description('Capacity of the GPT deployment:')
  @minValue(10)
  gpt_deployment_capacity: int

  @description('Location used for Content Understanding deployment:')
  content_understanding_available_location: content_understanding_available_location_type
}

@export()
type default_deployment_param_type = {
  @minLength(3)
  @maxLength(20)
  @description('A unique prefix for all resources in this deployment. This should be 3-20 characters long:')
  environment_name: string
  unique_id: string
  solution_prefix: string
  @description('Location used for Azure Cosmos DB, Azure Container App deployment')
  secondary_location: string
  use_local_build: container_app_deployment_type
  public_container_image_endpoint: string
  resource_group_location: string
  resource_name_prefix: object
  resource_name_format_string: string
  @description('Azure Resource Naming Abbreviations')
  naming_abbrs: object
  @description('Optional. Enable or disable telemetry for the deployment.')
  enable_telemetry: bool
  enable_waf: bool
  tags: object
}

@export()
type container_app_deployment_info_type = {
  container_app: {
    maxReplicas: int
    minReplicas: int
  }
  container_web: {
    maxReplicas: int
    minReplicas: int
  }
  container_api: {
    maxReplicas: int
    minReplicas: int
  }
}

@export()
func make_solution_prefix(unique_id string) string => 'cps-${padLeft(take(unique_id, 12), 12, '0')}'

type keyvault_sku_type = 'standard' | 'premium'

type keyvault_public_network_access_type = 'Disabled' | 'Enabled'

import {
  privateEndpointSingleServiceType
  privateEndpointMultiServiceType
} from 'br/public:avm/utl/types/avm-common-types:0.5.1'

@export()
type key_vault_param_type = {
  @description('Name of the Key Vault')
  keyvaultName: string
  @description('Location of the Key Vault')
  location: string
  @description('Tags for the Key Vault')
  tags: object
  @description('Role assignments for the Key Vault')
  roleAssignments: array
  @description('Enable purge protection for the Key Vault')
  enablePurgeProtection: bool
  @description('Enable soft delete for the Key Vault')
  enableSoftDelete: bool
  @description('Enable vault for disk encryption')
  enableVaultForDiskEncryption: bool
  @description('Enable vault for template deployment')
  enableVaultForTemplateDeployment: bool
  @description('Public network access setting for the Key Vault')
  publicNetworkAccess: keyvault_public_network_access_type
  @description('SKU of the Key Vault')
  keyvaultsku: keyvault_sku_type
  @description('Soft delete retention period in days')
  softDeleteRetentionInDays: int
  @description('Enable RBAC authorization for the Key Vault')
  enableRbacAuthorization: bool
  @description('Create mode for the Key Vault')
  createMode: string
  @description('Enable telemetry for the Key Vault')
  enableTelemetry: bool
  @description('Optional. Configuration details for private endpoints. For security reasons, it is recommended to use private endpoints whenever possible.')
  privateEndpoints: privateEndpointSingleServiceType[]?
}

type app_insights_retention_in_days = 30 | 60 | 90 | 120 | 180 | 270 | 365
type app_insights_kind = 'web' | 'other'
type app_insights_applicationType = 'web' | 'other'
type app_insights_flow_type = 'Bluefield' | 'Basic'
type app_insights_sku_name =
  | 'PerGB2018'
  | 'CapacityReservation'
  | 'Premium'
  | 'Standard'
  | 'Free'
  | 'PerNode'
  | 'LACluster'
  | 'Standalone'

@export()
type app_insights_param_type = {
  @description('Name of the Application Insights resource')
  appInsightsName: string
  @description('Location for the Application Insights and Log Analytics Workspace resources')
  location: string
  // @description('Workspace resource ID for the Application Insights resource')
  // workspaceResourceId: string
  @description('Retention period in days for the Application Insights resource')
  retentionInDays: app_insights_retention_in_days
  @description('Kind of the Application Insights resource')
  kind: app_insights_kind
  @description('Disable IP masking for the Application Insights resource')
  disableIpMasking: bool
  @description('Flow type for the Application Insights resource')
  flowType: app_insights_flow_type
  @description('Application Type for the Application Insights resource')
  applicationType: app_insights_applicationType
  @description('Disable local authentication for the Application Insights resource')
  disableLocalAuth: bool
  // @description('Force customer storage for profiler in Application Insights resource')
  // forceCustomerStorageForProfiler: bool
  // @description('Public network access for ingestion in Application Insights resource')
  // publicNetworkAccessForIngestion: 'Enabled' | 'Disabled'
  @description('Public network access for query in Application Insights resource')
  publicNetworkAccessForQuery: 'Enabled' | 'Disabled'
  @description('Request source for the Application Insights resource')
  requestSource: 'rest' | 'other'

  @description('Name of the Log Analytics Workspace resource')
  logAnalyticsWorkspaceName: string
  @description('SKU name for the Log Analytics Workspace resource')
  skuName: app_insights_sku_name
  // @description('This is the features properties for Log Analytics Workspace resource') --DEFAULT to 1
  // features: {
  //   @description('Search version for the Log Analytics Workspace resource')
  //   searchVersion: 1
  // }
  // diagnosticSettings: {
  //   @description('Enable diagnostic settings for the Application Insights resource')
  //   enableDiagnosticSettings: bool
  // }
}

type container_registry_sku_type = 'Basic' | 'Standard' | 'Premium'
type public_network_access_type = 'Enabled' | 'Disabled'
type zone_redundancy_type = 'Enabled' | 'Disabled'

@export()
type container_registry_param_type = {
  @description('Name of the Azure Container Registry')
  acrName: string
  @description('Location for the Azure Container Registry')
  location: string
  @description('SKU for the Azure Container Registry')
  acrSku: container_registry_sku_type
  @description('Public network access setting for the Azure Container Registry')
  publicNetworkAccess: public_network_access_type
  @description('Zone redundancy setting for the Azure Container Registry')
  zoneRedundancy: zone_redundancy_type
  @description('Optional. Configuration details for private endpoints. For security reasons, it is recommended to use private endpoints whenever possible.')
  privateEndpoints: privateEndpointSingleServiceType[]?
}
