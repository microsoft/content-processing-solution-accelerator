# AVM Post Deployment Guide

This document provides guidance on post-deployment steps after deploying the Content processing solution accelerator from the [AVM (Azure Verified Modules) repository](https://github.com/Azure/bicep-registry-modules/tree/main/avm/ptn/sa/content-processing).

## Overview

After successfully deploying the Content Processing Solution Accelerator using the AVM template, you'll need to complete some configuration steps to make the solution fully operational. This guide walks you through:

- Setting up schema definitions for document processing
- Importing sample data to test the solution
- Configuring authentication for secure access
- Verifying your deployment is working correctly

## Prerequisites

Before starting the post-deployment process, ensure you have the following:

### Required Software

1. **[PowerShell](https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell?view=powershell-7.4)** <small>(v7.0+ recommended)</small> - Available for Windows, macOS, and Linux

2. **[Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)** <small>(v2.50+)</small> - Command-line tool for managing Azure resources

3. **[Git](https://git-scm.com/downloads/)** - Version control system for cloning the repository

4. **Deployed Infrastructure** - A successful Content processing solution accelerator deployment from the [AVM repository](https://github.com/Azure/bicep-registry-modules/tree/main/avm/ptn/sa/content-processing)

#### Important Note for PowerShell Users

If you encounter issues running PowerShell scripts due to execution policy restrictions, you can temporarily adjust the `ExecutionPolicy` by running the following command in an elevated PowerShell session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

This will allow the scripts to run for the current session without permanently changing your system's policy.

## Post-Deployment Steps

### Step 1: Clone the Repository

First, clone this repository to access the post-deployment scripts:

```powershell
git clone https://github.com/microsoft/content-processing-solution-accelerator.git
cd content-processing-solution-accelerator
```

### Step 2: Verify Your Deployment

Before proceeding, verify that your AVM deployment completed successfully:

1. **Check Resource Group**: Confirm all expected resources are present in your Azure resource group
2. **Verify Container Apps**: Ensure both API and Web container apps are running
3. **Test Connectivity**: Verify you can access the container app URLs

### Step 3: Optional - Rebuild and Push Container Images

If you need to rebuild the source code and push updated containers to the deployed Azure Container Registry:

**Linux/macOS**:
```bash
cd ./infra/scripts/
./docker-build.sh
```

**Windows (PowerShell)**:
```powershell
cd .\infra\scripts\
.\docker-build.ps1
```

> **Note**: This step is only necessary if you've modified the source code or need to update the container images.

### Step 4: Register Schema Files

Configure the solution with sample schemas for document processing:

> 💡 **Want to customize schemas?** [Learn more about adding your own schemas here](./CustomizeSchemaData.md)

#### 4.1 Get API Service Endpoint

1. Navigate to your Azure portal and find your resource group
2. Locate the API container app (named **ca-**_\<environmentName\>_**-api**)
3. Copy the Application URL from the Overview page
   
   ![Check API Service Url](./images/CheckAPIService.png)

#### 4.2 Register Sample Schemas

Navigate to the schemas directory and run the registration script:

```powershell
cd src/ContentProcessorAPI/samples/schemas
```

**Linux/macOS**:
```bash
./register_schema.sh https://<YOUR_API_ENDPOINT>/schemavault/ schema_info_sh.json
```

**Windows**:
```powershell
./register_schema.ps1 https://<YOUR_API_ENDPOINT>/schemavault/ .\schema_info_ps1.json
```

#### 4.3 Verify Schema Registration

Check that schemas were registered successfully:
![Schema file registration](./images/SchemaFileRegistration.png)

### Step 5: Import Sample Data

Upload sample documents to test the solution:

#### 5.1 Get Schema IDs

Note down the Schema IDs for "Invoice" and "Property Loss Damage Claim Form" from the previous step.

#### 5.2 Upload Sample Documents

Navigate to the samples directory:

```powershell
cd src/ContentProcessorAPI/samples/
```

**Upload Invoice samples (Linux/macOS)**:
```bash
./upload_files.sh https://<YOUR_API_ENDPOINT>/contentprocessor/submit ./invoices <INVOICE_SCHEMA_ID>
```

**Upload Property Claims samples (Linux/macOS)**:
```bash
./upload_files.sh https://<YOUR_API_ENDPOINT>/contentprocessor/submit ./propertyclaims <PROPERTY_CLAIM_SCHEMA_ID>
```

**Upload Invoice samples (Windows)**:
```powershell
./upload_files.ps1 https://<YOUR_API_ENDPOINT>/contentprocessor/submit .\invoices <INVOICE_SCHEMA_ID>
```

**Upload Property Claims samples (Windows)**:
```powershell
./upload_files.ps1 https://<YOUR_API_ENDPOINT>/contentprocessor/submit .\propertyclaims <PROPERTY_CLAIM_SCHEMA_ID>
```

### Step 6: Configure Authentication

Set up secure access to your application:

1. Follow the detailed steps in [Configure App Authentication](./ConfigureAppAuthentication.md)
2. **Important**: Authentication changes can take up to 10 minutes to take effect

## Next Steps

Now that you've completed your deployment, you can start using the solution. Try out these things to start getting familiar with the capabilities:
* Open the web container app URL in your browser and explore the web user interface and upload your own invoices.
* [Create your own schema definition](./CustomizeSchemaData.md), so you can upload and process your own types of documents.
* [Ingest the API](API.md) for processing documents programmatically.

---

> **📋 Note**: This guide is specifically for post-deployment steps after using the AVM template. For complete deployment from scratch, see the main [Deployment Guide](./DeploymentGuide.md).