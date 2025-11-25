# DevContainer Image for GitHub Actions

## Overview

This repository uses a custom DevContainer image for GitHub Actions workflows, providing a consistent and reproducible environment that matches local development.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  .devcontainer/Dockerfile                                   │
│  • Base: mcr.microsoft.com/vscode/devcontainers/base       │
│  • Pre-installed: Azure CLI, azd, Node.js 20+, UV, Python │
│  • Build tools: gcc, python3-dev, poppler-utils           │
└─────────────────────────────────────────────────────────────┘
                            ↓
            (Build & Publish via build-devcontainer-image.yml)
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  <your-acr>.azurecr.io/devcontainer:latest                 │
│  • Published to Azure Container Registry                    │
│  • Used by GitHub Actions workflows                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
            (Used in reusable-deployment-workflow.yml)
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  deploy job (when runner_os == 'devcontainer')             │
│  runs-on: ubuntu-latest                                     │
│  • Login to ACR using docker/login-action                   │
│  • Pull devcontainer image from ACR                         │
│  • All deployment steps run on ubuntu with tools available  │
│  • No manual tool installation needed                       │
└─────────────────────────────────────────────────────────────┘
```

## Benefits

### 1. **Consistent Environment**
- Same tools and versions in CI/CD as local development
- Eliminates "works on my machine" issues

### 2. **Faster Workflows**
- Tools pre-installed in the image
- No need for manual installation steps
- Faster job startup time

### 3. **Maintainable**
- Single source of truth (`.devcontainer/Dockerfile`)
- Update once, applies everywhere
- Easy to version and track changes

### 4. **Reproducible**
- Exact same environment every time
- Isolated from runner host
- Predictable behavior

## Image Build Process

The DevContainer image is automatically built and published when:

### 1. **On Push to Main** (when `.devcontainer/**` changes)
```yaml
on:
  push:
    branches:
      - main
    paths:
      - '.devcontainer/**'
```

### 2. **Manual Trigger**
Go to Actions → "Build DevContainer Image" → "Run workflow"

### 3. **Weekly Schedule** (security updates)
```yaml
schedule:
  - cron: '0 0 * * 0'  # Every Sunday at midnight
```

## Image Registry

**Location:** Azure Container Registry (ACR)

**Full Image Name:**
```
<your-acr>.azurecr.io/devcontainer:latest
```

**Authentication:** Uses existing ACR secrets (`ACR_TEST_LOGIN_SERVER`, `ACR_TEST_USERNAME`, `ACR_TEST_PASSWORD`)

**Tags:**
- `latest` - Latest build from main branch
- `main-<sha>` - Specific commit SHA from main branch
- `<branch>-<sha>` - Builds from other branches

## Usage in Workflows

### Automatic Usage
When you trigger `deploy-v2-devcontainer.yml`, it automatically logs into ACR and pulls the DevContainer image:

```yaml
# deploy-v2-devcontainer.yml
jobs:
  Run:
    uses: ./.github/workflows/reusable-deployment-workflow.yml
    with:
      runner_os: devcontainer  # ← Triggers DevContainer mode
      # ... other inputs
```

### How It Works
```yaml
# reusable-deployment-workflow.yml (simplified)
deploy:
  runs-on: ubuntu-latest
  
  steps:
    - name: Login to ACR
      uses: docker/login-action@v3
      with:
        registry: ${{ secrets.ACR_TEST_LOGIN_SERVER }}
        username: ${{ secrets.ACR_TEST_USERNAME }}
        password: ${{ secrets.ACR_TEST_PASSWORD }}
    
    - name: Setup DevContainer Environment
      run: docker pull ${{ env.ACR_DEVCONTAINER_IMAGE }}
    
    # All subsequent steps have access to tools from the image
    - name: Deploy using azd
      run: azd up --no-prompt
```

## Pre-installed Tools

The DevContainer image includes:

| Tool | Version | Purpose |
|------|---------|---------|
| **Azure CLI** | Latest | Azure resource management |
| **Azure Developer CLI (azd)** | Latest | Infrastructure deployment |
| **Node.js** | 20+ | Frontend build (ContentProcessorWeb) |
| **UV** | Latest | Python package management |
| **Python 3** | Latest (Debian) | Backend services |
| **Git** | Latest | Version control |
| **Docker** | via features | Container operations |
| **jq** | Latest | JSON processing |
| **TypeScript** | Global | TypeScript support |
| **Yarn** | Global | Alternative package manager |

### Additional Tools
- `poppler-utils` - PDF processing
- `python3-numpy` - Scientific computing
- `build-essential` - C/C++ compilation
- `python3-dev` - Python development headers

## Updating the DevContainer

### Step 1: Modify `.devcontainer/Dockerfile`
```dockerfile
# Example: Add a new tool
RUN apt-get update \
    && apt-get install -y my-new-tool \
    && apt-get clean
```

### Step 2: Commit and Push to Main
```bash
git add .devcontainer/Dockerfile
git commit -m "feat: add my-new-tool to devcontainer"
git push origin main
```

### Step 3: Image Builds Automatically
- GitHub Actions workflow triggers
- New image built and published
- Next workflow run uses updated image

### Step 4: (Optional) Rebuild Manually
If you need the update immediately:
1. Go to Actions tab
2. Select "Build DevContainer Image" workflow
3. Click "Run workflow"
4. Wait for completion

## Comparison: Before vs After

### Before (Manual Setup)
```yaml
steps:
  - name: Setup DevContainer Environment
    run: |
      apt-get update
      apt-get install -y curl git jq sudo
      curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
      apt-get install -y nodejs
      curl -LsSf https://astral.sh/uv/install.sh | sh
      # ... more installations
```
⏱️ ~2-3 minutes per run

### After (Pre-built Image)
```yaml
container: ghcr.io/microsoft/.../devcontainer:latest

steps:
  - name: Checkout Code
    uses: actions/checkout@v4
  # Tools already available!
```
⏱️ ~10-15 seconds to pull image (cached)

## Troubleshooting

### Image Not Found
**Error:** `Error: failed to pull image "ghcr.io/...": not found`

**Solution:**
1. Ensure the image was built at least once
2. Check Actions tab for "Build DevContainer Image" workflow status
3. Manually trigger the workflow if needed

### Outdated Image
**Problem:** Using old version of tools

**Solution:**
1. Check when image was last built (Actions → Build DevContainer Image)
2. Manually trigger rebuild to get latest
3. Or wait for next weekly scheduled build

### Permission Issues
**Error:** `Permission denied while trying to pull image`

**Solution:**
- Image is public, should not require authentication
- Verify GITHUB_TOKEN has packages:read permission

### Tools Not Available
**Problem:** Expected tool not found in container

**Solution:**
1. Check `.devcontainer/Dockerfile` - tool might not be installed
2. Add tool to Dockerfile and push update
3. Wait for new image build or trigger manually

## Local Development vs CI/CD

| Aspect | Local Development | GitHub Actions |
|--------|------------------|----------------|
| **Image Source** | Built locally from `.devcontainer/Dockerfile` | Pre-built from ghcr.io |
| **Rebuild Frequency** | On demand (VS Code rebuild) | On push to main |
| **Customization** | Edit Dockerfile locally | Push changes to repo |
| **Tool Availability** | Immediate after rebuild | After image rebuild completes |

## Best Practices

### 1. **Keep Dockerfile Minimal**
Only install essential tools needed for deployment:
```dockerfile
# ✅ Good - necessary for deployment
RUN apt-get install -y azure-cli nodejs

# ❌ Avoid - nice-to-have but not essential
RUN apt-get install -y vim htop
```

### 2. **Version Pin Critical Tools**
```dockerfile
# ✅ Good - predictable
FROM mcr.microsoft.com/vscode/devcontainers/base:bookworm

# ❌ Avoid - unpredictable
FROM mcr.microsoft.com/vscode/devcontainers/base:latest
```

### 3. **Use Multi-stage Builds**
```dockerfile
# Copy from another image instead of installing
FROM ghcr.io/astral-sh/uv:latest AS uv
COPY --from=uv /uv /uvx /bin/
```

### 4. **Clean Up After Installations**
```dockerfile
RUN apt-get update \
    && apt-get install -y tool1 tool2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*  # ← Reduces image size
```

### 5. **Test Locally First**
Before pushing Dockerfile changes:
```bash
# Build locally
docker build -f .devcontainer/Dockerfile -t test-devcontainer .

# Run a test command
docker run --rm test-devcontainer az --version
docker run --rm test-devcontainer azd version
```

## Security Considerations

### 1. **Public Image Registry**
- Image is publicly accessible (no secrets baked in)
- Anyone can pull the image
- Do NOT include secrets or credentials in Dockerfile

### 2. **Base Image Trust**
- Uses official Microsoft devcontainer images
- Regularly updated for security patches
- Weekly rebuild gets latest security updates

### 3. **Minimal Attack Surface**
- Only essential tools installed
- No unnecessary services running
- Clean up package managers after installation

## FAQ

**Q: Do I need to rebuild the image for every deployment?**
A: No, the image is pre-built and reused across deployments.

**Q: How long does image build take?**
A: ~5-7 minutes for initial build, faster with caching.

**Q: Can I use a different image registry?**
A: Yes, modify `build-devcontainer-image.yml` to use Docker Hub or another ACR instance by updating the secrets.

**Q: What if I want to test a change without pushing to main?**
A: Build locally or create a temporary workflow with a different tag, or manually trigger the build workflow from your branch.

**Q: How much space does the image use?**
A: ~1.5-2 GB (compressed), ~4-5 GB (uncompressed on runner).

**Q: Why use ACR instead of GHCR?**
A: ACR integrates better with existing Azure infrastructure and uses the same authentication secrets already configured for the project.

## Related Files

- `.devcontainer/Dockerfile` - Image definition
- `.devcontainer/devcontainer.json` - VS Code configuration
- `.github/workflows/build-devcontainer-image.yml` - Image build workflow
- `.github/workflows/reusable-deployment-workflow.yml` - Uses the image
- `.github/workflows/deploy-v2-devcontainer.yml` - Triggers DevContainer deployment

## Additional Resources

- [GitHub Actions: Running jobs in a container](https://docs.github.com/en/actions/using-jobs/running-jobs-in-a-container)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Dev Containers specification](https://containers.dev/)
