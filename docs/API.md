# Ingesting the API for Event-Driven Processing

The Content Processing solution accelerator consists of a number of APIs to handle processing. The web UI utilizes these same APIs to demonstrate uploading a file to be processed, processing it, and showing the current processing queue. This also includes adding and modifying schema definitions, managing schema sets (collections), and managing claim batch lifecycles that files are being mapped and transformed to.

> **Note:** Once the solution has been deployed, you'll be able to access the API definition here:
>
> - Swagger: `https://<content-processing-api-container-url>/docs`
> - OpenAPI: `https://<content-processing-api-container-url>/redoc`

## APIs

Outlined below are the various APIs that are available as both Swagger and OpenAPI specifications within the solution.

### Content Processor

Responsible for processing-level actions to capture a file, processes, and queue management.

- **[POST]** `/contentprocessor/processed` — List processed contents (paginated).
- **[POST]** `/contentprocessor/submit` — Submit a file to be processed with its selected schema and any custom metadata to pass along with it for external reference.
- **[GET]** `/contentprocessor/status/{process_id}` — Get the status of a file being processed. It shows the status of the file being processed in the pipeline.
- **[GET]** `/contentprocessor/processed/{process_id}` — Get the processed content result for a given process ID.
- **[PUT]** `/contentprocessor/processed/{process_id}` — Update the processed content result or attach a comment.
- **[GET]** `/contentprocessor/processed/{process_id}/steps` — Get the per-step processing outputs for a given process ID.
- **[GET]** `/contentprocessor/processed/files/{process_id}` — Stream the original uploaded file for inline viewing.
- **[DELETE]** `/contentprocessor/processed/{process_id}` — Delete a processed content record and its associated blob storage data.

### Claim Processor

Responsible for claim batch lifecycle management, including creating claim containers, adding files, starting batch processing workflows, and reviewing results.

- **[PUT]** `/claimprocessor/claims` — Create a new claim container with a schema collection assignment. Returns the claim manifest with a unique claim ID.
- **[GET]** `/claimprocessor/claims/{claim_id}/manifest` — Get the claim manifest for a specific claim, including its files and schema configuration.
- **[POST]** `/claimprocessor/claims/{claim_id}/files` — Add a file to an existing claim container with its schema assignment and metadata.
- **[POST]** `/claimprocessor/claims` — Submit a claim for batch processing. Enqueues the claim request to the workflow queue for processing (Document Processing → RAI Analysis → Summarizing → Gap Analysis).
- **[POST]** `/claimprocessor/claims/processed` — Get a paginated list of all claim batch processing results.
- **[GET]** `/claimprocessor/claims/{claim_id}/status` — Get the current processing status of a claim batch (Pending → Processing → RAI Analysis → Summarizing → Gap Analysis → Completed/Failed).
- **[GET]** `/claimprocessor/claims/{claim_id}` — Retrieve the full claim processing details including processed documents, summarization, and gap analysis results.
- **[POST]** `/claimprocessor/claims/{claim_id}/comment` — Add a comment/annotation to a claim process record.
- **[DELETE]** `/claimprocessor/claims/{claim_id}` — Delete a claim container and its processing record.

### Schema Vault

System-level configuration for adding and managing individual schemas in the system related to processing.

- **[GET]** `/schemavault/` — Get the list of schemas registered in the system.
- **[PUT]** `/schemavault/` — Update the schema with new information passed.
- **[POST]** `/schemavault/` — Create and register a new schema in the system.
- **[DELETE]** `/schemavault/` — Unregister a schema from the system.
- **[GET]** `/schemavault/schemas/{schema_id}` — Download the registered schema file by schema ID.

### Schema Set Vault

System-level configuration for managing schema sets (collections). Schema sets group multiple individual schemas together for claim batch processing workflows.

- **[GET]** `/schemasetvault/` — Get the list of all schema sets registered in the system.
- **[POST]** `/schemasetvault/` — Create a new schema set with a name and description.
- **[GET]** `/schemasetvault/{schemaset_id}` — Get a specific schema set by its ID.
- **[DELETE]** `/schemasetvault/{schemaset_id}` — Delete a schema set by its ID.
- **[GET]** `/schemasetvault/{schemaset_id}/schemas` — Get all individual schemas within a schema set.
- **[POST]** `/schemasetvault/{schemaset_id}/schemas` — Add an existing schema to a schema set.
- **[DELETE]** `/schemasetvault/{schemaset_id}/schemas/{schema_id}` — Remove a schema from a schema set.

### Health & Probes

- **[GET]** `/` — Get API root info and uptime.
- **[GET]** `/health` — Determine the alive state of the solution for processing.
- **[GET]** `/startup` — Determine the startup state of the solution.

> **Note:** You can find a sample REST Client call with endpoints and payload examples in the repository at:
>
> `/src/ContentProcessorAPI/test_http/invoke_APIs.http`

## Note on Custom Meta Data

Custom metadata can optionally be passed along when submitting a file to be processed on the Content Processor API. This allows for external source system reference information to be captured and passed through the processing steps. This information stays as reference only for down-stream reference and is not used in processing or modifying any data extraction, mapping, or transformation.

## Security

Security is applied to the API by utilizing a vnet for traffic and network control. A service principal with permission can programmatically call the endpoints and is registered as an application registration in Azure.
