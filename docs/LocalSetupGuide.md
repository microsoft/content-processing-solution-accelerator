# Local Setup and Development Guide

This guide provides instructions for setting up the Content Processing Solution Accelerator locally for development and testing. The solution consists of three main components that work together to process multi-modal documents.

## Table of Contents

- [Local Setup: Quick Start](#local-setup-quick-start)
- [Development Environment](#development-environment)
- [Deploy with Azure Developer CLI](#deploy-with-azure-developer-cli)
- [Troubleshooting](#troubleshooting)

## Local Setup: Quick Start

Follow these steps to set up and run the application locally for development:

### Prerequisites

Ensure you have the following installed:

• **Git** - [Download Git](https://git-scm.com/downloads)
• **Docker Desktop** - [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)
• **Azure CLI** - [Install Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
• **Azure Developer CLI (azd)** - [Install Azure Developer CLI](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd)
• **Python 3.11+** - [Download Python](https://www.python.org/downloads/)
• **Node.js 18+** - [Download Node.js](https://nodejs.org/)

### 1. Clone the Repository

Navigate to your development folder and clone the repository:

```bash
git clone https://github.com/microsoft/content-processing-solution-accelerator.git
cd content-processing-solution-accelerator
```

### 2. Azure Authentication

Login to Azure and set your subscription:

```bash
# Login to Azure
az login

# Set your subscription
az account set --subscription "your-subscription-id"

# Login with Azure Developer CLI
azd auth login
```

### 3. Configure Environment Variables

Copy the environment sample files and update them with your Azure resource values:

```bash
# Copy environment files
cp .env.sample .env
cp src/ContentProcessor/.env.sample src/ContentProcessor/.env
cp src/ContentProcessorAPI/.env.sample src/ContentProcessorAPI/.env
cp src/ContentProcessorWeb/.env.sample src/ContentProcessorWeb/.env
```

Update the `.env` files with your Azure resource information:

```bash
# Root .env file
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-openai-api-key
AZURE_OPENAI_MODEL=gpt-4o
AZURE_CONTENT_UNDERSTANDING_ENDPOINT=https://your-content-understanding-endpoint
AZURE_STORAGE_CONNECTION_STRING=your-storage-connection-string
AZURE_COSMOS_CONNECTION_STRING=your-cosmos-connection-string
```

### 4. Start the Application

Run the startup script to install dependencies and start all components:

**Windows:**
```cmd
start.cmd
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

Alternatively, you can start each component manually:

**Backend API:**
```bash
cd src/ContentProcessorAPI
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Content Processor:**
```bash
cd src/ContentProcessor
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python src/main.py
```

**Web Frontend:**
```bash
cd src/ContentProcessorWeb
npm install
npm start
```

### 5. Access the Application

Once all components are running, open your browser and navigate to:

• **Web Interface:** [http://localhost:3000](http://localhost:3000)
• **API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
• **API Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

## Development Environment

For advanced development and customization, you can set up each component individually:

### Content Processor API (Backend)

The REST API provides endpoints for file upload, processing management, and schema operations.

```bash
cd src/ContentProcessorAPI

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the API server with hot reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Content Processor (Background Service)

The background processing engine handles document extraction and transformation.

```bash
cd src/ContentProcessor

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the processor
python src/main.py
```

### Content Processor Web (Frontend)

The React/TypeScript frontend provides the user interface.

```bash
cd src/ContentProcessorWeb

# Install dependencies
npm install

# Start development server
npm start
```

### Using Docker for Development

For containerized development, create a `docker-compose.dev.yml` file:

```yaml
version: '3.8'
services:
  content-processor-api:
    build:
      context: ./src/ContentProcessorAPI
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - APP_ENV=development
    volumes:
      - ./src/ContentProcessorAPI:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  content-processor-web:
    build:
      context: ./src/ContentProcessorWeb
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_BASE_URL=http://localhost:8000
    volumes:
      - ./src/ContentProcessorWeb:/app
    command: npm start

  content-processor:
    build:
      context: ./src/ContentProcessor
      dockerfile: Dockerfile
    environment:
      - APP_ENV=development
    volumes:
      - ./src/ContentProcessor:/app
```

Run with Docker Compose:
```bash
docker-compose -f docker-compose.dev.yml up --build
```

## Deploy with Azure Developer CLI

Follow these steps to deploy the application to Azure using Azure Developer CLI:

### Prerequisites

• Ensure you have the [Azure Developer CLI](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd) installed.
• Ensure you have an Azure subscription with appropriate permissions.
• Check [Azure OpenAI quota availability](./quota_check.md) before deployment.

### 1. Initialize the Project

Initialize the project for Azure deployment:

```bash
# Initialize azd project
azd init

# Select the content-processing template when prompted
```

### 2. Configure Environment

Set up your environment variables:

```bash
# Set environment name
azd env set AZURE_ENV_NAME "your-environment-name"

# Set Azure location
azd env set AZURE_LOCATION "eastus"

# Set OpenAI deployment parameters
azd env set AZURE_OPENAI_GPT_DEPLOYMENT_CAPACITY "10"
azd env set AZURE_OPENAI_GPT_MODEL_NAME "gpt-4o"
```

### 3. Deploy Infrastructure and Applications

Deploy both infrastructure and applications:

```bash
# Provision Azure resources and deploy applications
azd up
```

This command will:
• Create all required Azure resources
• Build and deploy the container applications
• Configure networking and security settings

### 4. Verify Deployment

Once deployment is complete, verify the application is running:

```bash
# Get deployment information
azd show

# Open the deployed web application
azd browse
```

### 5. Redeploy Application Code

To deploy code changes without reprovisioning infrastructure:

```bash
# Deploy only application code changes
azd deploy
```

### 6. Clean Up Resources

To remove all deployed resources:

```bash
# Delete all Azure resources
azd down
```

## Troubleshooting

### Common Issues

**Python Module Not Found:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Node.js Dependencies Issues:**
```bash
# Clear npm cache and reinstall
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

**Port Conflicts:**
```bash
# Check what's using the port
netstat -tulpn | grep :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Kill the process or change the port
```

**Azure Authentication Issues:**
```bash
# Re-authenticate
az logout
az login
azd auth login
```

**CORS Issues:**
• Ensure API CORS settings include the web app URL
• Check browser network tab for CORS errors  
• Verify API is running on the expected port

**Environment Variables Not Loading:**
• Verify `.env` file is in the correct directory
• Check file permissions (especially on Linux/macOS)
• Ensure no extra spaces in variable assignments

### Debug Mode

Enable detailed logging by setting these environment variables:

```bash
APP_LOGGING_LEVEL=DEBUG
APP_LOGGING_ENABLE=True
```

### Getting Help

• Check the [Technical Architecture](./TechnicalArchitecture.md) documentation
• Review the [API Documentation](./API.md) for endpoint details
• Submit issues to the [GitHub repository](https://github.com/microsoft/content-processing-solution-accelerator/issues)
• Check existing issues for similar problems

---

For additional support, please refer to the [main README](../README.md) or the [Deployment Guide](./DeploymentGuide.md) for production deployment instructions.
