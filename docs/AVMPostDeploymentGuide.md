# AVM Post Deployment Guide

> **📋 Note**: This guide is specifically for post-deployment steps after using the AVM template. For complete deployment from scratch using `azd`, see the main [Deployment Guide](./DeploymentGuide.md).

---

This document provides guidance on post-deployment steps after deploying the Content Processing Solution Accelerator from the [AVM (Azure Verified Modules) repository](https://github.com/Azure/bicep-registry-modules/tree/main/avm/ptn/sa/content-processing).

## Overview

After successfully deploying the Content Processing Solution Accelerator using the AVM template, you need to:

1. **Register schemas** — upload schema files, create a schema set, and link them together
2. **Process sample files** — upload and process sample claim bundles for verification
3. **Configure authentication** — set up app registration for secure access

> **Note:** Post-deployment data setup and authentication are manual steps for both `azd` and AVM deployments. Run the scripts in this guide after infrastructure provisioning.

## Prerequisites

Before starting, ensure you have:

### Required Software

1. **[Python](https://www.python.org/downloads/)** <small>(v3.10+)</small> — Required to run the schema registration script
2. **[Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)** <small>(v2.50+)</small> — Command-line tool for managing Azure resources
3. **[Git](https://git-scm.com/downloads/)** — Version control system for cloning the repository
4. **Deployed Infrastructure** — A successful Content Processing Solution Accelerator deployment from the [AVM repository](https://github.com/Azure/bicep-registry-modules/tree/main/avm/ptn/sa/content-processing)

### Python Dependencies

The registration script requires the `requests` library:

```bash
pip install requests
```

## Post-Deployment Steps

### Step 1: Clone the Repository

Clone this repository to access the schema files and registration script:

```bash
git clone https://github.com/microsoft/content-processing-solution-accelerator.git
cd content-processing-solution-accelerator
```

### Step 2: Get Your API Endpoint

Locate the API container app's FQDN from your deployment output or the Azure Portal:

- Navigate to **Azure Portal** → **Resource Group** → **Container Apps**
- Find the container app named **ca-**`<your-environment>`**-api**
- Copy the **Application URL** (e.g. `https://ca-myenv-api.<region>.azurecontainerapps.io`)

### Step 3: Register Schemas and Create Schema Set

The registration script performs three steps automatically:
1. Registers individual schema files (auto claim, damaged car image, police report, repair estimate) via `/schemavault/`
2. Creates an **"Auto Claim"** schema set via `/schemasetvault/`
3. Adds all registered schemas into the schema set

Run the script:

```bash
cd src/ContentProcessorAPI/samples/schemas
python register_schema.py https://<API_ENDPOINT> schema_info.json
```

Replace `<API_ENDPOINT>` with the URL from Step 2 (without a trailing slash).

The script is idempotent — it skips schemas and schema sets that already exist, so it's safe to re-run.

> **Want custom schemas?** See [Customize Schema Data](./CustomizeSchemaData.md) to create your own document schemas.

### Step 4: Process Sample File Bundles (Optional)

After schema registration, you can upload and process the included sample claim bundles to verify the deployment is working end to end. Each sample folder (`claim_date_of_loss/`, `claim_hail/`) contains a `bundle_info.json` manifest that maps files to their schema classes.

The workflow for each bundle:
1. **Create a claim batch** with the schema set ID via `PUT /claimprocessor/claims`
2. **Upload each file** with its mapped schema ID via `POST /claimprocessor/claims/{claim_id}/files`
3. **Submit the batch** for processing via `POST /claimprocessor/claims`

You can perform these steps via the web UI or the API directly. See the [API documentation](./API.md) and [Golden Path Workflows](./GoldenPathWorkflows.md) for details.

> **Note:** In `azd` and AVM flows, sample file processing runs when you execute the post-deployment script manually.

### Step 5: Configure Authentication (Required)

**This step is mandatory for application access:**

1. Follow [App Authentication Configuration](./ConfigureAppAuthentication.md).
2. Wait up to 10 minutes for authentication changes to take effect.

### Step 6: Verify Deployment

1. Access your application using the Web App URL from your deployment output.
2. Confirm the application loads successfully.
3. Verify you can sign in with your authenticated account.

## Next Steps

Once configuration is complete:

- [Technical Architecture](./TechnicalArchitecture.md) — Understand the system design and components
- [Create Custom Schemas](./CustomizeSchemaData.md) — Add your own document schemas
- [API Integration](API.md) — Explore programmatic document processing
- [Golden Path Workflows](./GoldenPathWorkflows.md) — Step-by-step testing procedures

## Need Help?

- 🐛 **Issues:** Check [Troubleshooting Guide](./TroubleShootingSteps.md)
- 💬 **Support:** Review [Support Guidelines](../SUPPORT.md)
