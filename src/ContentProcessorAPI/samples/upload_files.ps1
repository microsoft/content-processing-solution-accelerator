param (
    [Parameter(Mandatory = $true)]
    [string]$ApiEndpointUrl,

    [Parameter(Mandatory = $true)]
    [string]$FolderPath,

    [Parameter(Mandatory = $true)]
    [string]$SchemaId
)

# Validate if the folder exists
if (-not (Test-Path -Path $FolderPath)) {
    Write-Error "Error: Folder '$FolderPath' does not exist."
    exit 1
}

# Load System.Net.Http namespace
Add-Type -AssemblyName System.Net.Http

# Create an HttpClient instance
$httpClient = New-Object System.Net.Http.HttpClient

# Function to determine the MIME type based on file extension
function Get-MimeType {
    param ([string]$FileName)
    switch ([System.IO.Path]::GetExtension($FileName).ToLower()) {
        ".jpg" { return "image/jpeg" }
        ".jpeg" { return "image/jpeg" }
        ".png" { return "image/png" }
        ".pdf" { return "application/pdf" }
        default { return "application/octet-stream" }
    }
}

# Iterate over all files in the folder
Get-ChildItem -Path $FolderPath -File | ForEach-Object {
    $file = $_.FullName
    $filename = $_.Name

    # Determine the MIME type for the file
    $mimeType = Get-MimeType -FileName $filename

    # Create the JSON payload for the data field
    $dataJson = @{
        Metadata_Id = "Meta 001"
        Schema_Id   = $SchemaId
    } | ConvertTo-Json -Depth 10

    # Create a MultipartFormDataContent object
    $multipartContent = New-Object System.Net.Http.MultipartFormDataContent

    # Add the file content
    try {
        $fileBytes = [System.IO.File]::ReadAllBytes($file)
        $fileContent = [System.Net.Http.ByteArrayContent]::new($fileBytes)
        $fileContent.Headers.ContentDisposition = [System.Net.Http.Headers.ContentDispositionHeaderValue]::Parse("form-data; name=`"file`"; filename=`"$filename`"")
        $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse($mimeType)
        $multipartContent.Add($fileContent, "file", $filename)
    }
    catch {
        Write-Error "Failed to read file '$filename'. Error: $_"
        return
    }

    # Add the JSON payload
    try {
        $jsonContent = [System.Net.Http.StringContent]::new($dataJson, [System.Text.Encoding]::UTF8, "application/json")
        $jsonContent.Headers.ContentDisposition = [System.Net.Http.Headers.ContentDispositionHeaderValue]::Parse("form-data; name=`"data`"")
        $multipartContent.Add($jsonContent, "data")
    }
    catch {
        Write-Error "Failed to create JSON content for '$filename'. Error: $_"
        return
    }

    # Invoke the API
    try {
        $response = $httpClient.PostAsync($ApiEndpointUrl, $multipartContent).Result
        $responseBody = $response.Content.ReadAsStringAsync().Result

        if ($response.IsSuccessStatusCode) {
            # Extract and display the response
            $responseJson = $responseBody | ConvertFrom-Json
            $message = $responseJson.message
            Write-Output "Uploaded '$filename' successfully. Message: $message"
        }
        else {
            Write-Error "Failed to upload '$filename'. HTTP Status: $($response.StatusCode)"
            Write-Error "Error Response: $responseBody"
        }
    }
    catch {
        # Handle errors
        Write-Error "Failed to upload '$filename'. Error: $_"
    }
}
