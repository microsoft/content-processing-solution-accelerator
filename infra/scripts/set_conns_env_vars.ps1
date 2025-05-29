param (
    [Parameter(Mandatory = $false)]
    [string]$tenant,
    
    [Parameter(Mandatory = $false)]
    [string]$subscription,
    
    [Parameter(Mandatory = $false)]
    [string]$resourceGroup,
    
    [Parameter(Mandatory = $false)]
    [string]$workspace,

    [Parameter(Mandatory = $false)]
    [switch]$includeVerboseResponseOutputs
)

if (-not $tenant -and $env:AZURE_ORIGINAL_TENANT_ID) {
    $tenant = $env:AZURE_ORIGINAL_TENANT_ID
    if ($includeVerboseResponseOutputs) {
        Write-Output "Tenant parameter not provided. Using environment variable AZURE_ORIGINAL_TENANT_ID: $tenant"
    }
}

if (-not $subscription -and $env:AZURE_ORIGINAL_SUBSCRIPTION_ID) {
    $subscription = $env:AZURE_ORIGINAL_SUBSCRIPTION_ID
    if ($includeVerboseResponseOutputs) {
        Write-Output "Subscription parameter not provided. Using environment variable AZURE_ORIGINAL_SUBSCRIPTION_ID: $subscription"
    }
}

if (-not $resourceGroup -and $env:AZURE_ORIGINAL_RESOURCE_GROUP) {
    $resourceGroup = $env:AZURE_ORIGINAL_RESOURCE_GROUP
    if ($includeVerboseResponseOutputs) {
        Write-Output "ResourceGroup parameter not provided. Using environment variable AZURE_ORIGINAL_RESOURCE_GROUP: $resourceGroup"
    }
}

if (-not $workspace -and $env:AZURE_ORIGINAL_WORKSPACE_NAME) {
    $workspace = $env:AZURE_ORIGINAL_WORKSPACE_NAME
    if ($includeVerboseResponseOutputs) {
        Write-Output "Workspace (Project) parameter not provided. Using environment variable AZURE_ORIGINAL_WORKSPACE_NAME: $workspace"
    }
}

if (-not $tenant -or -not $subscription -or -not $resourceGroup -or -not $workspace) {
    $response = Read-Host "Start with existing Project connections? [NOTE: This action cannot be undone after executing. To revert, create a new AZD environment and run the process again.] (yes/no)"
    if ($response -eq "yes") {
        if (-not $tenant) {
            $tenant = Read-Host "Enter Tenant ID"
        }

        if (-not $subscription) {
            $subscription = Read-Host "Enter Subscription ID"
        }

        if (-not $resourceGroup) {
            $resourceGroup = Read-Host "Enter Resource Group"
        }

        if (-not $workspace) {
            $workspace = Read-Host "Enter Workspace / Project Name"
        }

    }
    elseif ($response -eq "no") {
        Write-Output "Not starting with existing Project. Exiting script."
        
        # Get User Input for Model Capacity(TPM) then save it azd env set
        $modelCapacity = Read-Host "Enter Model Capacity (TPM) for the new Project"
        if ($modelCapacity -and $modelCapacity -match '^\d+$') {
            azd env set 'MODEL_CAPACITY' $modelCapacity
            Write-Output "Environment variable MODEL_CAPACITY set to $modelCapacity"
        }
        else {
            Write-Output "Invalid Model Capacity input. Exiting script."
        }
        return
    }
    else {
        Write-Output "Invalid response. Exiting script."
        return
    }
}
else {
    Write-Output "All parameters provided. Starting with existing Project ${workspace}."
}

if (-not $tenant -or -not $subscription -or -not $resourceGroup -or -not $workspace) {
    throw "Unable to start with existing Project: One or more required parameters are missing."
}

if (-not (Get-AzContext)) {
    Write-Output "Connecting to Azure account..."
    Connect-AzAccount -Tenant $tenant -SubscriptionId $subscription
}

Set-AzContext -Subscription $subscription

$token = (Get-AzAccessToken).token
$url = "https://management.azure.com/subscriptions/$subscription/resourceGroups/$resourceGroup/providers/Microsoft.MachineLearningServices/workspaces/$workspace/connections?api-version=2024-10-01"
$headers = @{   
    'Authorization' = "Bearer $token"
    'Content-Type'  = "application/json"
    'Host'          = "management.azure.com"
}

$response = Invoke-RestMethod -Method GET -ContentType 'application/json' -Uri $url -Headers $headers
$connections = $response.value

Write-Output "Connections in workspace ${workspace}"
Write-Output "----------------------------------"   

Write-Output "Connection count: $($connections.Count)"
if ($connections.Count -eq 0) {
    Write-Output "No connections found in the workspace."
    return
}

if ($includeVerboseResponseOutputs) {
    Write-Output "Connections response:"
    Write-Output $connections
}
Write-Output "----------------------------------"   

$cogServiceAccountsUrl = "https://management.azure.com/subscriptions/$subscription/resourceGroups/$resourceGroup/providers/Microsoft.CognitiveServices/accounts/?api-version=2023-05-01"
$cogServiceAccounts = Invoke-RestMethod -Method GET -ContentType 'application/json' -Uri $cogServiceAccountsUrl -Headers $headers

Write-Output "Cognitive Service Accounts in resource group ${resourceGroup}"
Write-Output "----------------------------------"
Write-Output "Cognitive Service Account count: $($cogServiceAccounts.value.Count)"
if ($cogServiceAccounts.value.Count -eq 0) {
    Write-Output "No Cognitive Service Accounts found in the resource group."
    return
}
if ($includeVerboseResponseOutputs) {
    Write-Output "Cognitive Service Accounts response:"
    Write-Output $cogServiceAccounts.value
}
foreach ($account in $cogServiceAccounts.value) {
    $normalizedAccountName = $account.name -replace '[-_]', ''
    Write-Output "Normalized Cognitive Service Account Name: $normalizedAccountName"
}
Write-Output "----------------------------------"

Write-Output "Connections details:"
Write-Output "----------------------------------"
foreach ($connection in $connections) {
    $name = $connection.name
    $authType = $connection.properties.authType
    $category = $connection.properties.category
    $target = $connection.properties.target

    Write-Output "Name: $name"
    Write-Output "AuthType: $authType"
    Write-Output "Category: $category"
    Write-Output "Target: $target"
    
    if ($category -eq "CognitiveSearch") {
        azd env set 'AZURE_AI_SEARCH_ENABLED' 'true'
        Write-Output "Environment variable AZURE_AI_SEARCH_ENABLED set to true"
    }

    if ($category -eq "CognitiveService") {
        foreach ($account in $cogServiceAccounts.value) {
            $normalizedAccountName = $account.name -replace '[-_]', ''
            if ($normalizedAccountName -eq $name) {
                $resourceName = $account.name
                Write-Output "Matched Cognitive Service Account - Connection: '$name' Resource: $resourceName"
                
                switch ($account.kind) {
                    "ContentSafety" {
                        azd env set 'AZURE_AI_CONTENT_SAFETY_ENABLED' 'true'
                        Write-Output "Environment variable AZURE_AI_CONTENT_SAFETY_ENABLED set to true"
                    }
                    "SpeechServices" {
                        azd env set 'AZURE_AI_SPEECH_ENABLED' 'true'
                        Write-Output "Environment variable AZURE_AI_SPEECH_ENABLED set to true"
                    }
                    "FormRecognizer" {
                        azd env set 'AZURE_AI_DOC_INTELLIGENCE_ENABLED' 'true'
                        Write-Output "Environment variable AZURE_AI_DOC_INTELLIGENCE_ENABLED set to true"
                    }
                    "ComputerVision" {
                        azd env set 'AZURE_AI_VISION_ENABLED' 'true'
                        Write-Output "Environment variable AZURE_AI_VISION_ENABLED set to true"
                    }
                    "TextAnalytics" {
                        azd env set 'AZURE_AI_LANGUAGE_ENABLED' 'true'
                        Write-Output "Environment variable AZURE_AI_LANGUAGE_ENABLED set to true"
                    }
                    "TextTranslation" {
                        azd env set 'AZURE_AI_TRANSLATOR_ENABLED' 'true'
                        Write-Output "Environment variable AZURE_AI_TRANSLATOR_ENABLED set to true"
                    }
                    Default {
                        Write-Output "Unknown resource kind: $($account.kind)"
                    }
                }
            }
        }
    }

    Write-Output "-------------------------"
}
Write-Output "----------------------------------"
