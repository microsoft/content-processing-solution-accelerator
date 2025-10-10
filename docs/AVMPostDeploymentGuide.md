# AVM Post Deployment Guide

> **📋 Note**: This guide is specifically for post-deployment steps after using the AVM template. For complete deployment from scratch, see the main [Deployment Guide](./DeploymentGuide.md).

---

This document provides guidance on post-deployment steps after deploying the Content processing solution accelerator from the [AVM (Azure Verified Modules) repository](https://github.com/Azure/bicep-registry-modules/tree/main/avm/ptn/sa/content-processing).

## Overview

After successfully deploying the Content Processing Solution Accelerator using the AVM template, you'll need to complete some configuration steps to make the solution fully operational.

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

### Step 2: Complete Post-Deployment Configuration

Follow the **[Post Deployment Steps](./DeploymentGuide.md#post-deployment-steps)** section in the main Deployment Guide, which includes:

1. **[Optional: Publishing Local Build Container to Azure Container Registry](./DeploymentGuide.md#post-deployment-steps)**
2. **[Register Schema Files](./DeploymentGuide.md#post-deployment-steps)**
3. **[Import Sample Data](./DeploymentGuide.md#post-deployment-steps)**
4. **[Add Authentication Provider](./DeploymentGuide.md#post-deployment-steps)**

## Next Steps

Once configuration is complete, see the **[Next Steps](./DeploymentGuide.md#next-steps)** section in the main Deployment Guide to start using the solution.
