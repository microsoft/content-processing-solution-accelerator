# AVM Post Deployment Guide

> **📋 Note**: This guide is specifically for post-deployment steps after using the AVM template. For complete deployment from scratch using `azd`, see the main [Deployment Guide](./DeploymentGuide.md).

---

This document provides guidance on post-deployment steps after deploying the Content Processing Solution Accelerator from the [AVM (Azure Verified Modules) repository](https://github.com/Azure/bicep-registry-modules/tree/main/avm/ptn/sa/content-processing).

## Overview

After successfully deploying the Content Processing Solution Accelerator using the AVM template, you need to, **in this order**:

1. **Build and push container images** — the AVM deployment provisions the Azure Container Registry (ACR) and Container Apps, but does not build/push application images. Run `acr_build_push` so the container apps pick up the real images.
2. **Run the post-deployment script** — registers schemas, creates the schema set, and self-heals a handful of known AVM configuration gaps (see [Notes on AVM-specific pre-flight checks](#notes-on-avm-specific-pre-flight-checks) below).
3. **Configure authentication** — set up app registration for secure access.

> **Note:** When deploying via `azd up`, image build/push and schema registration both happen automatically through post-provisioning hooks. AVM deployments require the manual steps below because the AVM module doesn't run those hooks.

## Prerequisites

Before starting, ensure you have:

### Required Software

1. **[Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)** <small>(v2.50+)</small> — Command-line tool for managing Azure resources
2. **PowerShell** <small>(Windows PowerShell or [PowerShell 7+/pwsh](https://learn.microsoft.com/powershell/scripting/install/installing-powershell), cross-platform)</small> — Required to run `acr_build_push.ps1` and `post_deployment.ps1`
3. **[Git](https://git-scm.com/downloads/)** — Version control system for cloning the repository
4. **Deployed Infrastructure** — A successful Content Processing Solution Accelerator deployment from the [AVM repository](https://github.com/Azure/bicep-registry-modules/tree/main/avm/ptn/sa/content-processing)

## Post-Deployment Steps

### Step 1: Clone the Repository

Clone this repository to access the schema files and registration script:

```bash
git clone https://github.com/microsoft/content-processing-solution-accelerator.git
cd content-processing-solution-accelerator
```

### Step 2: Build and Push Container Images

The AVM module provisions the Azure Container Registry and Container Apps but does **not** build or push the application images. Run this from the repository root, passing the resource group you deployed into:

```powershell
.\infra\scripts\acr_build_push.ps1 "<your-resource-group-name>"
```

This builds all four container images (`web`, `api`, `app`, `wkfl`) via ACR Tasks and updates each container app to use the freshly built image. This step typically takes several minutes.

### Step 3: Get Your API Endpoint (Optional)

`post_deployment.ps1` auto-discovers the API container app's FQDN from the resource group, so this step is optional — only needed if you want to pass it explicitly or the API app can't be found automatically.

- Navigate to **Azure Portal** → **Resource Group** → **Container Apps**
- Find the container app named **ca-**`<your-environment>`**-api**
- Copy the **Application URL** (e.g. `https://ca-myenv-api.<region>.azurecontainerapps.io`)

### Step 4: Register Schemas and Create Schema Set

Run the post-deployment script, passing the resource group you deployed into:

```powershell
.\infra\scripts\post_deployment.ps1 -ResourceGroupName "<your-resource-group-name>" -ApiBaseUrl "https://<API_ENDPOINT>"
```

`-ApiBaseUrl` is optional if auto-discovery in Step 3 works; omit it to let the script find the API app itself.

The script performs three steps automatically:
1. Registers individual schema files (auto claim, damaged car image, police report, repair estimate) via `/schemavault/`
2. Creates an **"Auto Claim"** schema set via `/schemasetvault/`
3. Adds all registered schemas into the schema set

It is idempotent — it skips schemas and schema sets that already exist, so it's safe to re-run.

> **Want custom schemas?** See [Customize Schema Data](./CustomizeSchemaData.md) to create your own document schemas.

#### Notes on AVM-specific pre-flight checks

Before registering schemas, the script also runs a handful of self-healing pre-flight checks specific to AVM deployments (only active when `-ResourceGroupName` is supplied), which detect and automatically correct known AVM template gaps: storage account and Cosmos DB `publicNetworkAccess` being left `Disabled` on non-WAF deployments, the web container app's ingress port, and API authentication blocking anonymous schema registration calls. These are safe no-ops if your deployment doesn't have the issue.

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
