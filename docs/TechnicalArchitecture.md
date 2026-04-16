## Technical Architecture

Additional details about the technical architecture of the Content Processing solution accelerator. This describes the purpose and additional context of each component in the solution.

![image](./images/readme/solution-architecture.png)

### End-to-End Processing Flow

The solution supports two processing paths, both routed through the **Content Process API**:

#### Path 1 — Claim Batch Processing (multi-document)

```mermaid
flowchart LR
    WEB["🖥️ Web UI"] -->|HTTP| API["🔗 Content Process API<br/>/claimprocessor/*"]
    API -->|enqueue| Q1["📨 claim-process-queue"]
    Q1 -->|dequeue| WF["⚙️ Content Process Workflow<br/>(Agent Framework)"]

    subgraph Workflow["Claim Workflow — 4 Stages"]
        direction LR
        S1["Stage 1<br/>Document Processing"] --> S1b["Stage 2<br/>RAI Analysis<br/>(Safety Gate)"] --> S2["Stage 3<br/>Summarizing<br/>(GPT-5.1)"] --> S3["Stage 4<br/>Gap & Discrepancy<br/>Analysis (GPT-5.1)"]
    end

    WF --> S1
    S1 -->|"HTTP per doc"| API2["🔗 Content Process API<br/>/contentprocessor/*"]
    API2 -->|enqueue| Q2["📨 extract-queue"]
    Q2 -->|dequeue| CP["📄 Content Processor"]

    subgraph Pipeline["4-Stage Extraction Pipeline"]
        direction LR
        E["Extract<br/>(AI Content Understanding)"] --> M["Map<br/>(GPT-5.1 Vision)"] --> V["Evaluate<br/>(Merge & Score)"] --> SV["Save<br/>(Blob + Cosmos)"]
    end

    CP --> E
```

#### Path 2 — Single Document Processing

```mermaid
flowchart LR
    WEB["🖥️ Web UI"] -->|HTTP| API["🔗 Content Process API<br/>/contentprocessor/*"]
    API -->|enqueue| Q["📨 extract-queue"]
    Q -->|dequeue| CP["📄 Content Processor"]

    subgraph Pipeline["4-Stage Extraction Pipeline"]
        direction LR
        E["Extract<br/>(AI Content Understanding)"] --> M["Map<br/>(GPT-5.1 Vision)"] --> V["Evaluate<br/>(Merge & Score)"] --> SV["Save<br/>(Blob + Cosmos)"]
    end

    CP --> E
```

For detailed workflow documentation, see [Claim Processing Workflow](./ClaimProcessWorkflow.md). For the 4-stage document extraction pipeline, see [Processing Pipeline Approach](./ProcessingPipelineApproach.md).

### Claim Processing — Detailed Process Flow

The diagram below shows the complete end-to-end claim processing flow, including all queues, services, and data stores.

```mermaid
flowchart TB
    %% ── Trigger ──────────────────────────────────
    USER(["👤 User"]) -->|"Enqueue with\nClaim Process ID\n(Batch ID)"| INGESTION_Q["📨 Ingestion Queue\n(claim-process-queue)"]
    INGESTION_Q --> LAUNCH["Launch Workflow"]
    LAUNCH --> CLAIM_WF["Claim Process\nWorkflow"]

    %% ── Agentic Workflow ─────────────────────────
    subgraph AGENTIC ["Agentic Workflow"]
        direction TB
        DOC_PROC["Document Process\n(Content Processing\nTask Management)"]

        DOC_PROC -->|"Share\nProcessed Outputs"| RAI["🛡️ RAI Analysis\n(Safety Gate)"]
        RAI -->|"Safe content"| SUMMARIZE["Summarizing"]
        RAI -->|"Unsafe → Halt"| FAIL_RAI(["❌ Failed"])
        DOC_PROC -->|"Share\nProcessed Outputs"| GAP["GAP Finding"]

        SUMMARIZE -->|"Summary"| GPT_WF["🤖 GPT"]
        GAP -->|"GAPs"| GPT_WF

        GPT_WF -->|"Summarize with\nall processed Contents"| SUMMARIZE
        GPT_WF -->|"Finding GAP\nin processed Contents\nwith Rulesets"| GAP
    end

    CLAIM_WF --> DOC_PROC

    %% ── Document Processing submits to Content Processor ──
    DOC_PROC -->|"Enqueue Document Processing"| EXTRACT_Q

    %% ── Content Processing Pipeline ──────────────
    subgraph PIPELINE ["Content Processing Pipeline"]
        direction LR

        subgraph SERVICES ["Azure Services"]
            direction TB
            CU["Content Understanding\n+\nAI Document Intelligence"]
            BLOB["Storage Blob"]
            GPT_CP["🤖 GPT"]
        end

        EXTRACT_Q["📨 Extracting Queue\n(content-pipeline-extract-queue)"] -->|"Enqueue With\nProcess Payload"| EXTRACT_H["Extract Handler"]
        EXTRACT_H -->|"Send Request"| CU
        CU -->|"Parsed Text\n(Markdown)"| EXTRACT_H

        EXTRACT_H -->|"Enqueue With\nProcess Payload"| PROCESS_Q["📨 Processing Queue\n(content-pipeline-map-queue)"]

        PROCESS_Q --> MAP_H["Map Handler"]
        MAP_H -->|"Convert Image per Pages"| BLOB
        BLOB -->|"File Stream"| MAP_H
        MAP_H -->|"Send Request"| GPT_CP
        GPT_CP -->|"Mapped Result"| MAP_H

        MAP_H -->|"Enqueue With\nProcess Payload"| EVAL_Q["📨 Evaluating Queue\n(content-pipeline-evaluate-queue)"]
        EVAL_Q --> EVAL_H["Evaluate Handler"]

        EVAL_H -->|"Enqueue With\nProcess Payload"| SAVE_Q["📨 Save Queue\n(content-pipeline-save-queue)"]
        SAVE_Q --> SAVE_H["Save Handler"]
    end

    %% ── Status Updates to Cosmos DB ──────────────
    COSMOS[("🗄️ Cosmos DB")]

    EXTRACT_H -->|"Update Status"| COSMOS
    MAP_H -->|"Update Status"| COSMOS
    EVAL_H -->|"Update Status"| COSMOS
    SAVE_H -->|"Update Status"| COSMOS

    DOC_PROC -.->|"Monitor and Update\nProcess Status"| COSMOS
    SUMMARIZE -->|"Update Process Status"| COSMOS
    GAP -->|"Update Process Status"| COSMOS
    CLAIM_WF -->|"Update Process Status"| COSMOS
```

**Key flow**:

1. A user enqueues a claim (batch ID) to the **Ingestion Queue**
2. The **Claim Process Workflow** launches and registers the **Agentic Workflow** (4 stages)
3. **Stage 1 — Document Process**: For each document, enqueues to the **Content Processing Pipeline** (Extract → Map → Evaluate → Save), each step using its own queue
4. **Stage 2 — RAI Analysis**: Screens extracted content through the LLM safety classifier; halts on unsafe content
5. **Stage 3 — Summarizing**: Sends all processed content to GPT for consolidated summarization
6. **Stage 4 — GAP Finding**: Sends processed content + YAML rulesets to GPT for gap/discrepancy analysis
7. Every stage updates **Cosmos DB** with processing status

### Container Registry
Using Azure Container Registry, container images are built, stored, and managed in a private registry. These container images include the Content Processor, Content Process API, Claim Process Monitor Web, and Content Process Workflow (Claim Processor).

### Naming Conventions

The solution uses slightly different names across source code directories, Docker images, and Azure Container Apps. The table below maps each service to its canonical names:

| Service | Source Directory | Docker Image | Container App | Notes |
|---|---|---|---|---|
| Content Processor | `src/ContentProcessor` | `contentprocessor` | `ca-<suffix>-app` | 4-stage document extraction pipeline |
| Content Process API | `src/ContentProcessorAPI` | `contentprocessorapi` | `ca-<suffix>-api` | Central API gateway |
| Content Process Workflow | `src/ContentProcessorWorkflow` | `contentprocessworkflow` | `ca-<suffix>-wkfl` | Agent Framework claim orchestration |
| Claim Process Monitor Web | `src/ContentProcessorWeb` | `contentprocessorweb` | `ca-<suffix>-web` | React/TypeScript frontend |

> **Note:** `<suffix>` is a unique string generated during deployment (the `solutionSuffix` Bicep parameter).

### Service - Content Processor
Internal container app for document processing pods. This service runs a multi-step pipeline (Extract → Map → Evaluate → Save) that consumes jobs from Azure Storage Queue, processing individual documents through Azure AI Content Understanding and Azure OpenAI Service.

### Service - Content Process Workflow (Claim Processor)
Internal queue-driven container app that orchestrates claim-level batch processing workflows. This service is built on the **Agent Framework's Workflow Engine** — a DAG-based event-streaming execution model using `WorkflowBuilder` and `Executor` patterns. The workflow runs a four-stage linear pipeline:
1. **Document Processing** – For each document in the claim, invokes the Content Process API's content processor endpoints, which in turn triggers the Content Processor's 4-stage extraction pipeline. Polls for completion and collects extraction results with confidence scores.
2. **RAI Analysis** – Responsible AI safety gate that screens all extracted content through an LLM-based classifier. Blocks the pipeline if content is flagged as unsafe.
3. **Summarizing** – Uses Azure OpenAI Service GPT-5.1 to generate consolidated summaries of the processed claim documents.
4. **Gap Analysis** – Uses Azure OpenAI Service GPT-5.1 to perform gap analysis across the claim documents, identifying missing or inconsistent information.

The workflow reads claim processing requests from Azure Storage Queue (`claim-process-queue`) with support for concurrent workers, retry logic with exponential backoff, dead-letter queues, and graceful shutdown. For full details, see [Claim Processing Workflow](./ClaimProcessWorkflow.md).

### Content Process API (Claim Process API)
Using Azure Container App, this is the central API gateway for the solution. It exposes two sets of endpoints:
- **Workflow endpoints** (`/claimprocessor/*`) – Used by the Web UI for claim lifecycle management (create claim, add files, start processing, get status/results).
- **Content processor endpoints** (`/contentprocessor/*`) – Used by the Content Process Workflow to submit individual documents for extraction processing.

The API also provides schema management, schema set (collection) management, and processing queue datasets. Swagger and Open API specifications are available for the APIs.

### Claim Process Monitor Web
Using Azure Container App, this app acts as the UI for the process monitoring queue. The app is built with React and TypeScript. It acts as an API client to create an experience for uploading new documents, creating and managing claim batches, monitoring current and historical processes, and reviewing output results including summarization and gap analysis.

### App Configuration
Using Azure App Configuration, app settings and configurations are centralized and used with the Content Processor, Content Process API, Content Process Workflow, and Claim Process Monitor Web.

### Storage Queue
Using Azure Storage Queue, pipeline work steps and processing jobs are added to storage queues to be picked up and run by their respective services. The solution uses a **dynamic naming convention** for pipeline queues and dedicated queues for claim workflow orchestration:

**Content Processor pipeline queues** — generated from the pattern `content-pipeline-{step}-queue` based on the configured pipeline steps (`extract`, `map`, `evaluate`, `save`):

| Queue | Dead-Letter Queue | Purpose |
|---|---|---|
| `content-pipeline-extract-queue` | `content-pipeline-extract-queue-dead-letter-queue` | Document extraction (AI Content Understanding) |
| `content-pipeline-map-queue` | `content-pipeline-map-queue-dead-letter-queue` | Schema mapping (GPT-5.1 Vision) |
| `content-pipeline-evaluate-queue` | `content-pipeline-evaluate-queue-dead-letter-queue` | Merge & confidence scoring |
| `content-pipeline-save-queue` | `content-pipeline-save-queue-dead-letter-queue` | Persist results to Blob + Cosmos DB |

**Claim Workflow queues** — used by the Content Process Workflow (Agent Framework):

| Queue | Purpose |
|---|---|
| `claim-process-queue` | Claim batch processing workflow requests |
| `claim-process-dead-letter-queue` | Failed claim messages after retry exhaustion |

### Azure AI Content Understanding Service
Used to detect and extract text from images and PDFs. This service also retrieves the coordinates of each piece of text, along with confidence scores, by leveraging built-in (pretrained) models. This utilizes the prebuilt-layout for extraction.

### Azure OpenAI Service
Using Azure OpenAI Service, a deployment of the GPT-5.1 model is used during the content processing pipeline to extract content. GPT Vision is used for extraction and validation functions during processing. The model is also used for summarization and gap analysis in the claim processing workflow. This model can be changed to a different Azure OpenAI Service model if desired, but this has not been thoroughly tested and may be affected by the output token limits.

### Blob Storage
Using Azure Blob Storage, the solution uses multiple containers:
- **process-batch** – Claim batch manifests and batch-level artifacts.
- **cps-processes** – Source files for processing, intermediate results, and final output JSON files.
- **cps-configuration** – Schema `.py` files and configuration data.

### Azure Cosmos DB for MongoDB
Using Azure Cosmos DB for MongoDB, the solution uses multiple collections:
- **Processes** – Individual document processing records with status, step history, extraction results, and confidence scores.
- **Schemas** – Registered schema definitions.
- **Schemasets** – Schema set (collection) configurations that group schemas for claim processing.
- **claimprocesses** – Claim batch processing records with workflow status, processed documents, summarization, and gap analysis results.
- **batches** – Batch processing metadata.
- **checkpoints** – Agent Framework workflow execution checkpoints for fault tolerance.

The processing queue stores individual processes information and history for status and processing step review, along with final extraction and transformation into JSON for its selected schema.
