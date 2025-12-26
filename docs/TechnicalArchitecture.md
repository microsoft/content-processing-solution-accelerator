## Technical Architecture

Additional details about the technical architecture of the Content Processing solution accelerator. This describes the purpose and additional context of each component in the solution.

![image](./images/readme/solution-architecture.png)


### Ingress Controller
Using Azure's Application Gateway Ingress Controller for the different container apps. Allowing for load balancing and dynamic traffic management across the application layer.

### Container Registry
Using Azure Container Registry, container images are built, stored, and managed in a private registry. These container images include the Content Processor, Content process API, and Content Process Monitor Web.

### Service - Content Processor
Internal container app for document processing pods.

### Content Process API
Using Azure Container App, this includes API end points exposed to facilitate ingestion of files to be processed, schema management, and processing queue datasets. Swagger and Open API specifications are available for the APIs.

### Content Process Monitor Web
Using Azure Container App, this app acts as the UI for the process monitoring queue. The app is built with React and TypeScript. It acts as an API client to create an experience for uploading new documents, monitoring current and historical processes, and reviewing output results.

### App Configuration
Using Azure App Configuration, app settings and configurations are centralized and used with the Content Processor, Content process API, and Content Process Monitor Web.

### Storage Queue
Using Azure Storage Queue, pipeline work steps and processing jobs are added to the storage queue to be picked up and run for their respective jobs. Files uploaded are queued while being saved the blob storage and removed after successful completion. 

### Azure AI Content Understanding Service
Used to detect and extract text from images and PDFs. This service also retrieves the coordinates of each piece of text, along with confidence scores, by leveraging built-in (pretrained) models. This utilizes the prebuild-layout 2024-12-01-preview for extraction.

### Azure OpenAI Service
Using Azure OpenAI Service, a deployment of the GPT-4o 2024-10-01-preview model is used during the content processing pipeline to extract content. GPT Vision is used for extraction and validation functions during processing. This model can be changed to a different Azure OpenAI Service model if desired, but this has not been thoroughly tested and may be affected by the output token limits.

### Blob Storage
Using Azure Blob Storage, schema .py files, source files for processing, and final output JSON files are stored in blob storage.

### Azure Cosmos DB for MongoDB
Using Azure Cosmos DB for MongoDB, files that have been submitted for processing are added to the DB and their processing step history is saved. The processing queue stores individual processes information and history for status and processing step review, along with final extraction and transformation into JSON for its selected schema.
