metadata name = 'parameters'
metadata description = 'This file defines the parameters used in the Bicep deployment scripts for the CPS solution.'

import {
  default_deployment_param_type
  content_understanding_available_location_type
  gpt_deployment_type
  gpt_model_name_type
  ai_deployment_param_type
  container_app_deployment_info_type
  make_solution_prefix
} from 'types.bicep'

// ========== Get Parameters from bicepparam file ========== //
@minLength(3)
@maxLength(20)
@description('A unique prefix for all resources in this deployment. This should be 3-20 characters long:')
param environmentName string

@description('Set this flag to true only if you are deplpoying from Local')
param useLocalBuild string = 'false'

@metadata({
  azd: {
    type: 'location'
  }
})
param contentUnderstandingLocation content_understanding_available_location_type
@description('Deployment type for the GPT model:')
param deploymentType gpt_deployment_type = 'GlobalStandard'
@description('Name of the GPT model to deploy:')
param gptModelName gpt_model_name_type = 'gpt-4o'

@minValue(10)
@description('Capacity of the GPT deployment:')
// You can increase this, but capacity is limited per model/region, so you will get errors if you go over
// https://learn.microsoft.com/en-us/azure/ai-services/openai/quotas-limits
param gptDeploymentCapacity int = 100

@minLength(1)
@description('Version of the GPT model to deploy:')
@allowed([
  '2024-08-06'
])
param gptModelVersion string = '2024-08-06'
var containerImageEndPoint = 'cpscontainerreg.azurecr.io'
var resourceGroupLocation = resourceGroup().location
var uniqueId = toLower(uniqueString(subscription().id, environmentName, resourceGroup().location))
var solutionPrefix = make_solution_prefix(uniqueId)
var resource_format_string = '{0}avm-cps'
@description('Location used for Azure Cosmos DB, Azure Container App deployment')
param secondaryLocation string = 'EastUs2'

var deployment_param default_deployment_param_type = {
  environment_name: environmentName
  unique_id: uniqueId
  use_local_build: useLocalBuild == 'true' ? 'localbuild' : 'usecontainer'
  solution_prefix: solutionPrefix
  secondary_location: secondaryLocation
  public_container_image_endpoint: containerImageEndPoint
  resource_group_location: resourceGroupLocation
  resource_name_prefix: {}
  resource_name_format_string: resource_format_string
  enable_waf: false // Set to true if you want to enable WAF
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

output global default_deployment_param_type = deployment_param
output ai_deployment ai_deployment_param_type = ai_deployment
output container_app_deployment container_app_deployment_info_type = container_app_deployment
