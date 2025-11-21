param (
    [Parameter(Mandatory = $true)]
    [string]$ApiEndpointUrl,

    [Parameter(Mandatory = $true)]
    [string]$SchemaInfoJson
)

# Validate if the JSON file exists
if (-not (Test-Path -Path $SchemaInfoJson)) {
    Write-Error "Error: JSON file '$SchemaInfoJson' does not exist."
    exit 1
}

# Parse the JSON file and process each schema entry
$schemaEntries = Get-Content -Path $SchemaInfoJson | ConvertFrom-Json

# Get the directory of the SchemaInfoJson file
$schemaInfoDirectory = [System.IO.Path]::GetDirectoryName((Get-Item -Path $SchemaInfoJson).FullName)

foreach ($entry in $schemaEntries) {
    # Extract file, class name, and description from the JSON entry
    $schemaFile = $entry.File
    $className = $entry.ClassName
    $description = $entry.Description

    # Resolve the full path of the schema file
    if (-not [System.IO.Path]::IsPathRooted($schemaFile)) {
        $schemaFile = Join-Path -Path $schemaInfoDirectory -ChildPath $schemaFile
    }

    # Validate if the schema file exists
    if (-not (Test-Path -Path $schemaFile)) {
        Write-Warning "Error: Schema file '$schemaFile' does not exist. Skipping..."
        continue
    }

    # Extract the filename from the file path
    $filename = [System.IO.Path]::GetFileName($schemaFile)

    # Create a temporary JSON file for the class name and description
    $tempJson = New-TemporaryFile
    $tempJsonContent = @{
        ClassName   = $className
        Description = $description
    } | ConvertTo-Json -Depth 10
    Set-Content -Path $tempJson -Value $tempJsonContent

    # Create a multipart form-data content
    $multipartContent = New-Object System.Net.Http.MultipartFormDataContent

    try {
        # Add the schema file to the multipart content
        $fileStream = [System.IO.File]::OpenRead($schemaFile)
        $fileContent = New-Object System.Net.Http.StreamContent($fileStream)
        $fileContent.Headers.ContentDisposition = [System.Net.Http.Headers.ContentDispositionHeaderValue]::new("form-data")
        $fileContent.Headers.ContentDisposition.Name = '"file"'
        $fileContent.Headers.ContentDisposition.FileName = '"' + $filename + '"'
        $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::new("text/x-python") # Explicitly set Content-Type
        $multipartContent.Add($fileContent)

        # Add the class name and description JSON to the multipart content
        $dataContent = New-Object System.Net.Http.StringContent((Get-Content -Path $tempJson -Raw))
        $dataContent.Headers.ContentDisposition = [System.Net.Http.Headers.ContentDispositionHeaderValue]::new("form-data")
        $dataContent.Headers.ContentDisposition.Name = '"data"'
        $dataContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::new("application/json") # Explicitly set Content-Type
        $multipartContent.Add($dataContent)

        # Log request details for debugging
        # Write-Output "Uploading schema file: $schemaFile"
        # Write-Output "ClassName: $className, Description: $description"
        # Write-Output "API Endpoint: $ApiEndpointUrl"

        # Invoke the API with the multipart content
        $httpClient = New-Object System.Net.Http.HttpClient
        $responseMessage = $httpClient.PostAsync($ApiEndpointUrl, $multipartContent).Result

        # Extract HTTP status code and response content
        $httpStatusCode = $responseMessage.StatusCode
        $responseContent = $responseMessage.Content.ReadAsStringAsync().Result

        # Print the API response
        if ($responseMessage.IsSuccessStatusCode) {
            # Extract Id and Description from the response JSON
            $responseJson = $responseContent | ConvertFrom-Json
            $id = $responseJson.Id
            $desc = $responseJson.Description
            Write-Output "$desc's Schema Id - $id"
            
            # Set GitHub Actions output if GITHUB_OUTPUT environment variable exists
            if ($env:GITHUB_OUTPUT) {
                # Create a safe variable name from the class name (lowercase, alphanumeric and underscores only)
                $safeName = $className.ToLower() -replace '[^a-z0-9_]', ''
                "${safeName}_schema_id=$id" | Out-File -FilePath $env:GITHUB_OUTPUT -Encoding utf8 -Append
            }
        }
        else {
            Write-Error "Failed to upload '$schemaFile'. HTTP Status: $httpStatusCode"
            Write-Error "Error Response: $responseContent"
        }
    }
    catch {
        Write-Error "An error occurred while processing '$schemaFile': $_"
    }
    finally {
        # Ensure the file stream is closed
        if ($fileStream) {
            $fileStream.Close()
        }
    }

    # Clean up the temporary JSON file
    Remove-Item -Path $tempJson -Force
}
