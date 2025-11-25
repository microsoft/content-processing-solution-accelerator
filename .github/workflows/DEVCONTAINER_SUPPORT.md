# DevContainer Deployment Support

## Overview

The reusable deployment workflow now supports running deployments in a DevContainer environment alongside Ubuntu and Windows runners. This provides a containerized, consistent deployment environment that mirrors local development setups.

## What Changed

### 1. Updated `reusable-deployment-workflow.yml`

**Added DevContainer as Runner Option:**
- `runner_os` input now accepts: `ubuntu-latest`, `windows-latest`, or `devcontainer`
- When `devcontainer` is specified, the job runs on `ubuntu-latest` with a Debian-based container

**Container Configuration:**
```yaml
runs-on: ${{ inputs.runner_os == 'devcontainer' && 'ubuntu-latest' || inputs.runner_os }}
container: ${{ inputs.runner_os == 'devcontainer' && 'mcr.microsoft.com/devcontainers/base:debian' || null }}
```

**DevContainer Environment Setup:**
- Automatic installation of required tools (curl, git, jq, Node.js, UV)
- Runs only when `runner_os == 'devcontainer'`
- Ensures all dependencies are available in the containerized environment

### 2. Created `deploy-v2-devcontainer.yml`

New workflow file that calls the reusable workflow with `runner_os: devcontainer`:
- Manual trigger via workflow_dispatch
- All deployment parameters supported (WAF, EXP, Docker build, E2E tests, cleanup)
- Same feature parity as Linux and Windows workflows

## How It Works

### Execution Flow

1. **Workflow Trigger**: User triggers `deploy-v2-devcontainer.yml` manually
2. **Runner Selection**: Job runs on `ubuntu-latest` runner
3. **Container Launch**: DevContainer (Debian-based) is started
4. **Environment Setup**: Tools are installed (Node.js, UV, etc.)
5. **Deployment**: Standard deployment steps execute inside container
6. **Cleanup**: Resources cleaned up (if configured)

### Key Features

✅ **Isolated Environment**: Runs in a containerized Debian environment  
✅ **Consistent Tooling**: Same tools as local DevContainer development  
✅ **Full Feature Parity**: All deployment options available  
✅ **No Code Duplication**: Uses same reusable workflow  
✅ **Docker-in-Docker**: Supports Docker builds within container  

## Usage

### Via GitHub Actions UI

1. Navigate to **Actions** → **Deploy-Test-Cleanup (v2) DevContainer**
2. Click **Run workflow**
3. Configure parameters:
   - Azure Location
   - WAF/EXP settings
   - Docker build options
   - E2E test selection
   - Resource cleanup
4. Click **Run workflow**

### Example: Basic DevContainer Deployment

```yaml
# Minimal configuration
azure_location: australiaeast
waf_enabled: false
EXP: false
build_docker_image: false
cleanup_resources: true
run_e2e_tests: GoldenPath-Testing
```

### Example: WAF + EXP Deployment

```yaml
# Advanced configuration
azure_location: australiaeast
waf_enabled: true
EXP: true
AZURE_ENV_LOG_ANALYTICS_WORKSPACE_ID: <workspace-id>
AZURE_EXISTING_AI_PROJECT_RESOURCE_ID: <project-id>
build_docker_image: false
cleanup_resources: true
run_e2e_tests: GoldenPath-Testing
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│          GitHub Actions Workflow Triggers               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────┐ │
│  │ deploy-v2  │  │ deploy-v2  │  │ deploy-v2-       │ │
│  │   .yml     │  │ -windows   │  │ devcontainer.yml │ │
│  │            │  │   .yml     │  │                  │ │
│  │ runner_os: │  │ runner_os: │  │ runner_os:       │ │
│  │ ubuntu-    │  │ windows-   │  │ devcontainer     │ │
│  │ latest     │  │ latest     │  │                  │ │
│  └──────┬─────┘  └──────┬─────┘  └────────┬─────────┘ │
│         │                │                  │           │
│         └────────────────┼──────────────────┘           │
│                          │                              │
│            ┌─────────────▼──────────────┐              │
│            │ reusable-deployment-       │              │
│            │    workflow.yml            │              │
│            │                            │              │
│            │ Handles all runner types:  │              │
│            │ • ubuntu-latest (native)   │              │
│            │ • windows-latest (native)  │              │
│            │ • devcontainer (in container)│            │
│            └────────────────────────────┘              │
│                                                          │
└─────────────────────────────────────────────────────────┘

DevContainer Execution:
┌──────────────────────────────────────────────────┐
│ ubuntu-latest runner                             │
│  ┌────────────────────────────────────────────┐ │
│  │ DevContainer (Debian)                      │ │
│  │  • Azure CLI installed                     │ │
│  │  • Azure Developer CLI installed           │ │
│  │  • Node.js 20+ installed                   │ │
│  │  • UV package manager installed            │ │
│  │  • Docker-in-Docker available              │ │
│  │                                            │ │
│  │  Deployment Steps Execute Here            │ │
│  └────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

## Comparison Matrix

| Feature | Linux | Windows | DevContainer |
|---------|-------|---------|--------------|
| **Runner** | ubuntu-latest | windows-latest | ubuntu-latest + container |
| **Environment** | Native Ubuntu | Native Windows | Debian container |
| **Container Support** | Native Docker | Native Docker | Docker-in-Docker |
| **Tool Installation** | Pre-installed | Pre-installed | Auto-installed in container |
| **Use Case** | Production CI/CD | Windows testing | Dev environment simulation |
| **Trigger** | Auto + Manual | Manual only | Manual only |
| **Scheduled** | ✅ Twice daily | ❌ | ❌ |

## Benefits

### 1. Development-Production Parity
DevContainer deployments use the same containerized environment as local development, reducing "works on my machine" issues.

### 2. Isolated Testing
Test deployment changes in an isolated container without affecting the host runner or other jobs.

### 3. Consistent Tooling
Ensures exact versions of tools (Node.js, Python, etc.) match local development.

### 4. Flexibility
Choose the best environment for each deployment:
- **Linux**: Fast, production-ready
- **Windows**: Windows-specific testing
- **DevContainer**: Development environment validation

## Technical Details

### Container Image
- **Base**: `mcr.microsoft.com/devcontainers/base:debian`
- **Distro**: Debian (bookworm)
- **User**: root (for tool installation)

### Installed Tools
- Azure CLI (via apt)
- Azure Developer CLI (via install script)
- Node.js 20+ (via NodeSource)
- UV (via install script)
- Git, jq, curl, sudo

### Environment Variables
Same as Linux runner:
- `AZURE_DEV_COLLECT_TELEMETRY`
- `WAF_ENABLED`
- `EXP`
- `CLEANUP_RESOURCES`

## Troubleshooting

### Container Fails to Start
**Issue**: DevContainer image pull fails  
**Solution**: GitHub Actions will retry automatically. Check GitHub status page.

### Tool Installation Fails
**Issue**: apt-get or curl commands fail  
**Solution**: Check network connectivity. Container has internet access by default.

### Permission Errors
**Issue**: Cannot write files or execute commands  
**Solution**: Container runs as root by default. Check file paths are correct.

### Docker-in-Docker Issues
**Issue**: Docker commands fail inside container  
**Solution**: Verify Docker service is available. May need to add `services: docker` to job.

## Limitations

1. **No Windows Support**: DevContainer option only works with Linux-based containers
2. **Manual Trigger Only**: No scheduled runs (by design)
3. **Startup Time**: Container initialization adds ~30-60 seconds vs native runner
4. **Resource Overhead**: Container adds memory/CPU overhead

## Best Practices

### When to Use DevContainer
- ✅ Testing deployment changes before production
- ✅ Validating tool version compatibility
- ✅ Reproducing local development issues in CI
- ✅ Isolating experimental deployments

### When to Use Linux/Windows
- ✅ Production deployments (Linux)
- ✅ Scheduled/automatic deployments (Linux)
- ✅ Windows-specific testing (Windows)
- ✅ Maximum performance (both)

## Future Enhancements

Possible improvements:
- [ ] Custom DevContainer image with pre-installed tools
- [ ] Cache container layers for faster startup
- [ ] Support for different base images
- [ ] Integration with GitHub Codespaces

## Related Files

```
.github/workflows/
├── reusable-deployment-workflow.yml  # ✨ Updated: Added devcontainer support
├── deploy-v2.yml                     # Linux workflow
├── deploy-v2-windows.yml             # Windows workflow
└── deploy-v2-devcontainer.yml        # 🆕 New: DevContainer workflow

.devcontainer/
├── devcontainer.json                 # Local DevContainer config
├── Dockerfile                        # Local DevContainer image
└── setupEnv.sh                       # Local environment setup
```

## Summary

The reusable deployment workflow now supports three runner environments:
1. **ubuntu-latest** - Native Linux (production)
2. **windows-latest** - Native Windows (testing)
3. **devcontainer** - Containerized Debian (development)

This provides maximum flexibility while maintaining a single source of truth for deployment logic. DevContainer support enables better development-production parity and isolated testing capabilities.

---

**Questions?** See the [main README](../README.md) or [Troubleshooting Guide](../docs/TroubleShootingSteps.md).
