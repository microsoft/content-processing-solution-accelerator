# Golden Path Workflows Guide

This guide provides detailed step-by-step workflows for getting the most out of the Content Processing Solution Accelerator. These "golden path" workflows represent the most common and effective use cases for the solution.

## Overview

The golden path workflows are designed to:
- Demonstrate the full capabilities of the solution
- Provide a structured learning experience from document upload through AI-powered analysis
- Showcase the 3-stage claim processing pipeline: Document Processing → Summarizing → Gap Analysis
- Help users understand confidence scoring, summarization, and rule-based gap analysis

---

## Workflow 1: End-to-End Auto Claim Processing

This is the primary v2 workflow — it walks through the full claim lifecycle from uploading multiple document types through AI-powered summarization and gap analysis.

> **Architecture**: Web UI → Content Process API → Content Process Workflow (Agent Framework) → Content Processor (4-stage pipeline) → Summarizer → Gap Analyzer. For full technical details, see [Claim Processing Workflow](./ClaimProcessWorkflow.md).

### 📋 Prerequisites
- Solution deployed and validated successfully (`azd up` completed)
- Auto Claim schema set registered (registered automatically during deployment)
- Authentication configured ([App Authentication Configuration](./ConfigureAppAuthentication.md))
- Sample data downloaded from the [samples directory](../src/ContentProcessorAPI/samples) — use the `claim_date_of_loss/` or `claim_hail/` folders

### 🚀 Step-by-Step Process

#### Step 1 — Select Auto Claim Schema Set

1. Navigate to your deployed web app URL and log in
2. In the Processing Queue pane, select the **"Auto Claim"** schema set
3. This schema set groups 4 document types: Auto Insurance Claim Form, Police Report, Repair Estimate, and Damaged Vehicle Image

#### Step 2 — Upload Claim Documents

Upload all relevant documents for the claim — at minimum an auto claim form, plus supporting documents:

| Document                  | Schema to Select          | Sample Source                  |
| ------------------------- | ------------------------- | ------------------------------ |
| Auto insurance claim form | Auto Insurance Claim Form | `claim_date_of_loss/` folder            |
| Police report             | Police Report             | `claim_date_of_loss/` folder            |
| Repair estimate           | Repair Estimate           | `claim_date_of_loss/` folder            |
| Damaged vehicle photos    | Damaged Vehicle Image     | `claim_date_of_loss/` folder (PNG/JPEG) |

For each document:
1. Click **"Import Content"**
2. Select the matching schema from the dropdown
3. Upload the file (PDF, PNG, or JPEG)
4. Repeat for each document type

> **Tip**: Use the `claim_hail/` folder for a sample set with fewer documents (no police report) — useful for verifying gap analysis rules.

#### Step 3 — Validate Document Processing Results

As each document is processed through the 4-stage pipeline (Extract → Map → Evaluate → Save), review the extraction results:

1. **Monitor Processing** — Watch each file status transition: `Uploaded` → `Processing` → `Completed` (typically 1-2 minutes per document)
2. **Review Per-Document Extraction**:
   - Click on each completed file to open the review interface
   - Examine the extracted data in the **"Extracted Results"** tab
   - Compare with the source document in the **"Source Document"** pane
3. **Check Confidence Scores**:
   - **Extraction Score** — How well the AI extracted raw data from the document
   - **Schema Score** — How well the extracted data maps to the expected schema fields
   - Pay attention to low-confidence fields (below 70%) that need manual review
4. **Validate Across Document Types**:
   - Compare how the system handles structured forms (claim form) vs. free text (police report) vs. images (damaged vehicle photos)
   - Note schema-specific extraction tailored to each document type
5. **Edit & Annotate** — Correct any extraction errors and add comments

#### Step 4 — Review Summarization

After all documents complete processing, the workflow automatically generates an AI-powered consolidated summary:

1. Navigate to the **claim summary** view
2. Review the AI-generated summary that consolidates findings across all uploaded documents
3. Verify key claim details are accurately captured:
   - Policy and contact information
   - Incident description and timeline
   - Damage assessment and estimated costs
   - Parties involved
4. Note how the summary cross-references information from different document types (e.g., claim form details corroborated by police report)

#### Step 5 — Review Gap Analysis & Discrepancy Results

The final stage applies **YAML-based rules** to detect missing documents and cross-document inconsistencies:

1. Navigate to the **gap analysis** results view
2. **Missing Document Gaps** — Review flagged gaps where required documents are absent:
   - Example: Police report missing for a theft-related claim → `REQ-PR-THEFT-001` triggered
   - Each gap shows: rule ID, severity (`critical`/`high`/`medium`/`low`), and rationale
3. **Cross-Document Discrepancies** — Review flagged conflicts where field values disagree across documents:
   - Example: VIN on claim form doesn't match VIN on police report → `DISC-VEHICLE-VIN-001` triggered
   - Numeric fields use tolerance-based matching (e.g., repair estimate totals within $50)
4. **Severity Triage** — Address gaps by severity:
   - `critical` / `high` — Must be resolved before claim can proceed
   - `medium` — Review recommended
   - `low` — Informational
5. **Iterate** — Upload missing documents or correct data, then re-process if needed

> **Customizing Rules**: Gap analysis rules are defined in a reusable YAML DSL — no code changes required. See [Gap Analysis Ruleset Guide](./GapAnalysisRulesetGuide.md) for how to add, modify, or replace rules.

### 🎯 Expected Outcomes
- ✅ Multiple document types (forms, reports, estimates, images) processed accurately within a single claim
- ✅ Confidence scores above 80% for most fields across all document types
- ✅ AI-generated summary consolidates findings across all documents
- ✅ Gap analysis identifies missing documents based on conditional rules (loss type, jurisdiction, amount)
- ✅ Discrepancy checks flag conflicting data across documents (VIN, claim number, dates, amounts)
- ✅ Claim status tracked through all stages: `Pending` → `Processing` → `Summarizing` → `GapAnalysis` → `Completed`

---

## Workflow 2: Custom Document Processing Golden Path

### 📋 Prerequisites
- Workflow 1 completed successfully
- Understanding of your specific document types

### 🚀 Step-by-Step Process

1. **Create Custom Schema**
   - Follow the [Custom Schema Guide](./CustomizeSchemaData.md)
   - Define your document structure and required fields (JSON Schema)

2. **Register Your Schema**
   - Add your schema to `schema_info.json` and run `register_schema.py`
   - Or register manually via the Schema Vault API (`POST /schemavault/`)
   - Verify the schema appears in the web interface

3. **Create or Update a Schema Set**
   - **New schema set**: Create via the SchemaSet Vault API (`POST /schemasetvault/`) with a name and description
   - **Existing schema set**: Use an existing set (e.g., the "Auto Claim" set created during deployment)
   - **Add your schema to the set**: Call `POST /schemasetvault/{schemaset_id}/schemas` with the schema ID
   - A schema set is **required** in v2 — documents cannot be processed without one

   > **Tip**: You can add multiple custom schemas to the same schema set to group related document types for claim batch processing.

4. **Test with Sample Documents**
   - In the Web UI, select your schema set, then choose your custom schema
   - Upload 2-3 representative documents and review extraction results
   - Check confidence scores and verify field accuracy

5. **Refine Extraction Quality**
   - Modify schema definitions if fields are missing or incorrectly mapped
   - Customize system prompts if extraction needs tuning ([Customize Prompts](./CustomizeSystemPrompts.md))
   - Re-test with updated schema

6. **Author Gap Analysis Rules (Optional)**
   - Create domain-specific gap analysis rules in YAML for your schema set
   - Define missing document rules and cross-document discrepancy checks
   - See [Gap Analysis Ruleset Guide](./GapAnalysisRulesetGuide.md)

7. **Scale to Production**
   - Process larger document batches
   - Establish quality thresholds
   - Set up automated workflows using the API

### 🎯 Expected Outcomes
- ✅ Custom schema registered and added to a schema set
- ✅ Documents processed accurately through the schema set
- ✅ Confidence scoring helps identify manual review needs
- ✅ Gap analysis rules adapted to your domain (if authored)
- ✅ Workflow scales to handle production volumes

---

## Workflow 3: API Integration Golden Path

For programmatic and CI/CD scenarios, drive the full claim workflow via API.

### 📋 Prerequisites
- Workflow 1 completed through the Web UI
- Familiarity with the [API Documentation](./API.md)

### 🚀 Key API Steps

1. **Create a Claim** — `POST /claimprocessor/claims` with the schema set ID
2. **Upload Files** — `POST /claimprocessor/claims/{id}/files` for each document (assign schema per file)
3. **Start Processing** — `POST /claimprocessor/claims` with `claim_process_id` in request body → enqueues to `claim-process-queue`
4. **Poll Status** — `GET /claimprocessor/claims/{id}/status` → tracks `Pending` → `Processing` → `Summarizing` → `GapAnalysis` → `Completed`
5. **Retrieve Results** — `GET /claimprocessor/claims/{id}` → extraction results, summary, and gap analysis

### 🎯 Expected Outcomes
- ✅ Full claim lifecycle driven programmatically
- ✅ Same 3-stage workflow as Web UI (Document Processing → Summarizing → Gap Analysis)
- ✅ Results retrievable via API for downstream system integration

---

## Advanced Workflows

### Multi-Domain Adaptation
- Create domain-specific schema sets (logistics, legal, finance)
- Author matching gap analysis rules in YAML — no code changes needed
- Swap rules files to apply different business policies to the same documents

### Batch Automation
- Use the Claim Processor API to submit claims programmatically
- Monitor the 3-stage workflow via status polling or webhook integration
- Export results for downstream systems

## Best Practices

### Quality Assurance
- Always review low-confidence extractions manually
- Use comments to document validation decisions
- Track accuracy improvements over time

### Confidence Score Interpretation
- **90-100%**: High confidence, likely accurate
- **70-89%**: Medium confidence, review recommended
- **Below 70%**: Low confidence, manual review required

### Performance Optimization
- Use consistent document formats when possible
- Ensure good image quality for scanned documents
- Batch similar document types for better consistency

## Troubleshooting Common Issues

### Low Extraction Accuracy
- Check document quality and formatting
- Verify schema matches document structure
- Review and update system prompts if needed

### Processing Timeouts
- Reduce document file sizes
- Check Azure quota availability
- Monitor system logs for errors

### Claim Workflow Issues
- Verify ContentProcessorWorkflow container is running and healthy
- Check `claim-process-queue` for stuck messages
- Review `claim-process-dead-letter-queue` for failed messages
- Confirm Azure App Configuration has correct queue and Cosmos connection settings
- Monitor workflow logs for agent framework errors

### Authentication Issues
- Verify app registration configuration
- Check user permissions and role assignments
- Review authentication provider settings

## Next Steps

After completing these golden path workflows:

1. **Explore Advanced Features**
   - Custom gap analysis rules ([Ruleset Guide](./GapAnalysisRulesetGuide.md))
   - Custom system prompts ([Prompt Customization](./CustomizeSystemPrompts.md))
   - API-driven batch processing

2. **Adapt to Your Domain**
   - Create custom schemas for your document types
   - Author domain-specific gap rules in YAML
   - Customize summarization prompts

3. **Scale Your Solution**
   - Monitor performance metrics
   - Optimize for your specific use cases
   - Plan for production deployment

## Support and Resources

- **Technical Documentation**: [API Guide](./API.md)
- **Processing Pipeline**: [Document Extraction Pipeline](./ProcessingPipelineApproach.md)
- **Claim Workflow**: [Claim Processing Workflow](./ClaimProcessWorkflow.md)
- **Gap Analysis Rules**: [Ruleset Guide](./GapAnalysisRulesetGuide.md)
- **Troubleshooting**: [Common Issues](./TroubleShootingSteps.md)
- **Sample Data**: [Download samples](../src/ContentProcessorAPI/samples)
- **Community**: [Submit issues](https://github.com/microsoft/content-processing-solution-accelerator/issues)

---

*This guide is based on the automated test suite golden path workflows that validate the core functionality of the solution.*