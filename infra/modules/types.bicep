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
