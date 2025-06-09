using './main.bicep'

param environmentName = readEnvironmentVariable('AZURE_ENV_NAME', 'cps')
param secondaryLocation = readEnvironmentVariable('AZURE_ENV_SECONDARY_LOCATION', 'EastUs2')
param contentUnderstandingLocation = readEnvironmentVariable('AZURE_ENV_CU_LOCATION', 'WestUS')
param deploymentType = readEnvironmentVariable('AZURE_ENV_MODEL_DEPLOYMENT_TYPE', 'GlobalStandard')
param gptModelName = readEnvironmentVariable('AZURE_ENV_MODEL_NAME', 'gpt-4.1')
param gptModelVersion = readEnvironmentVariable('AZURE_ENV_MODEL_VERSION', '2025-04-14')
param gptDeploymentCapacity = int(readEnvironmentVariable('AZURE_ENV_MODEL_CAPACITY', '30'))
param useLocalBuild = readEnvironmentVariable('USE_LOCAL_BUILD', 'false')
param imageTag = readEnvironmentVariable('AZURE_ENV_IMAGETAG', 'latest')
param existingLogAnalyticsWorkspaceId = readEnvironmentVariable('AZURE_ENV_LOG_ANALYTICS_WORKSPACE_ID', '')
