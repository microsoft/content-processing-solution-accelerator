# Golden Path Workflows Guide

This guide provides detailed step-by-step workflows for getting the most out of the Content Processing Solution Accelerator. These "golden path" workflows represent the most common and effective use cases for the solution.

## Overview

The golden path workflows are designed to:
- Demonstrate the full capabilities of the solution
- Provide a structured learning experience
- Showcase best practices for document processing
- Help users understand the confidence scoring and validation features

## Workflow 1: Invoice Processing Golden Path

### 📋 Prerequisites
- Solution deployed and validated successfully
- Sample schemas registered (Invoice schema)
- Authentication configured

### 🚀 Step-by-Step Process

1. **Access the Web Interface**
   - Navigate to your deployed web app URL
   - Log in using your configured authentication

2. **Select Invoice Schema**
   - In the Processing Queue pane, select "Invoice" from the schema dropdown
   - Verify the schema shows as available

3. **Upload Sample Invoice**
   - Click "Import Content" button
   - Select an invoice file from the sample data (PDF, PNG, or JPEG)
   - Click "Upload" to submit

4. **Monitor Processing**
   - Watch the file status change from "Uploaded" → "Processing" → "Completed"
   - This typically takes 1-2 minutes

5. **Review Extracted Data**
   - Click on the completed file to open the review interface
   - Examine the extracted data in the "Extracted Results" tab
   - Compare with the source document in the "Source Document" pane

6. **Validate and Modify Results**
   - Edit any incorrect data in the JSON output
   - Add notes in the "Comments" section
   - Pay attention to confidence scores for each field

7. **Save and Approve**
   - Click "Save" to store your modifications
   - Review the process steps in the "Process Steps" tab

### 🎯 Expected Outcomes
- ✅ Invoice data accurately extracted (vendor, amounts, dates, line items)
- ✅ Confidence scores above 80% for most fields
- ✅ Any low-confidence fields flagged for manual review
- ✅ Process steps show successful extraction, mapping, and evaluation

## Workflow 2: Property Claims Golden Path

### 📋 Prerequisites
- Invoice workflow completed successfully
- Property Loss Damage Claim Form schema registered

### 🚀 Step-by-Step Process

1. **Switch to Property Claims Schema**
   - Select "Property Loss Damage Claim Form" from the schema dropdown

2. **Upload Property Damage Document**
   - Import a property claim form from the sample data
   - Monitor the processing workflow

3. **Validate Complex Extraction**
   - Review extracted claim details, damages, and policy information
   - Note how the system handles form fields vs. free text

4. **Test Validation Features**
   - Modify extracted data to test validation rules
   - Add detailed comments about damage assessments

5. **Process Multiple Documents**
   - Upload additional property claim documents
   - Compare extraction accuracy across different document formats

### 🎯 Expected Outcomes
- ✅ Complex form data accurately extracted
- ✅ Multi-modal content (text, images, tables) processed correctly
- ✅ Validation rules applied appropriately

## Workflow 3: Custom Document Processing Golden Path

### 📋 Prerequisites
- Basic workflows completed
- Understanding of your specific document types

### 🚀 Step-by-Step Process

1. **Create Custom Schema**
   - Follow the [Custom Schema Guide](./CustomizeSchemaData.md)
   - Define your document structure and required fields

2. **Register Your Schema**
   - Use the schema registration scripts
   - Validate schema is available in the web interface

3. **Test with Sample Documents**
   - Start with 2-3 representative documents
   - Process and review initial results

4. **Refine Extraction Quality**
   - Analyze confidence scores and accuracy
   - Modify schema definitions if needed
   - Re-test with updated schema

5. **Scale to Production**
   - Process larger document batches
   - Establish quality thresholds
   - Set up automated workflows using the API

### 🎯 Expected Outcomes
- ✅ Custom schema accurately processes your document types
- ✅ Confidence scoring helps identify manual review needs
- ✅ Workflow scales to handle production volumes

## Advanced Workflows

### Multi-Schema Processing
- Process different document types in the same session
- Compare extraction approaches across schemas
- Understand when to use different processing strategies

### API Integration Golden Path
- Use programmatic APIs for document submission
- Implement webhook callbacks for processing notifications
- Build custom validation and approval workflows

### Batch Processing Workflow
- Upload multiple documents simultaneously
- Monitor batch processing status
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

### Authentication Issues
- Verify app registration configuration
- Check user permissions and role assignments
- Review authentication provider settings

## Next Steps

After completing these golden path workflows:

1. **Explore Advanced Features**
   - Custom validation rules
   - Webhook integrations
   - Batch processing APIs

2. **Integrate with Your Systems**
   - Connect to downstream databases
   - Set up automated workflows
   - Implement custom business logic

3. **Scale Your Solution**
   - Monitor performance metrics
   - Optimize for your specific use cases
   - Plan for production deployment

## Support and Resources

- **Technical Documentation**: [API Guide](./API.md)
- **Troubleshooting**: [Common Issues](./TroubleShootingSteps.md)
- **Sample Data**: [Download samples](../src/ContentProcessorAPI/samples)
- **Community**: [Submit issues](https://github.com/microsoft/content-processing-solution-accelerator/issues)

---

*This guide is based on the automated test suite golden path workflows that validate the core functionality of the solution.*