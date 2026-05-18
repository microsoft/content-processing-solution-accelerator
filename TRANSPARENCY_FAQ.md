## Content Processing Solution Accelerator: Responsible AI FAQ 

- ### What is the Content Processing Solution Accelerator? 

  This solution accelerator is an open-source GitHub Repository to extract data from unstructured documents and transform the data into defined schemas with validation to enhance the speed of downstream data ingestion and improve quality. It enables the ability to efficiently automate extraction, validation, and structuring of information for event driven system-to-system workflows. The solution is built using Azure OpenAI Service, Azure AI Services, Azure AI Content Understanding Service, Azure Cosmos DB, and Azure Container Apps.  

 

- ### What can the Content Processing Solution Accelerator do?  

    The sample solution is tailored for a Claims Specialist at an auto insurance company, who reviews large amounts of claim-related data including forms, reports, repair estimates, and damage photos. The sample data is synthetically generated utilizing Azure OpenAI Service and saved into related templates and files, which are unstructured documents that can be used to show the processing pipeline. Any names and other personally identifiable information in the sample data is fictitious.  

    The sample solution processes the uploaded documents by exposing an API endpoint that utilizes Azure OpenAI Service and Azure AI Content Understanding Service for extraction. The extracted data is then transformed into a specific schema output based on the content type (ex: repair estimate), and validates the extraction and schema mapping through accuracy scoring. The scoring enables thresholds to dictate a human-in-the-loop review of the output if needed, allowing a user to review, update, and add comments.  The solution also summarizes and identifies gaps across the collection of uploaded documents.

- ### What is/are the Content Processing Solution Accelerator’s intended use(s)? 

    This repository is to be used only as a solution accelerator following the open-source license terms listed in the GitHub repository. The example scenario’s intended purpose is to demonstrate how users can extract data from unstructured content to enhance the speed of data ingestion, transformation to pre-defined schemas, and improve data quality for downstream processing. The output is for informational purposes only and should be reviewed by a human. 


- ### How was the Content Processing Solution Accelerator evaluated? What metrics are used to measure performance? 

  The sample solution was evaluated using Azure AI Foundry Prompt Flow to test for harmful content, groundedness, and potential security risks.  

- ### What are the limitations of the Content Processing Solution Accelerator? How can users minimize the Content Processing Solution Accelerator’s limitations when using the system?   

  This solution accelerator can only be used as a sample to accelerate the creation of content processing solutions. The repository showcases a sample scenario of a Claims Specialist at an auto insurance company, analyzing large amounts of claim-related data, but a human must still be responsible to validate the accuracy and correctness of data extracted for their documents, schema definitions related to business specific documents to be extracted, quality and validation scoring logic and thresholds for human-in-the-loop review, ingesting transformed data into subsequent systems, and their relevancy for using with customers. Users of the accelerator should review the system prompts provided and update as per their organizational guidance. 
  
  AI generated content in the solution may be inaccurate and the outputs and integrated solutions derived from the output data are not robustly trustworthy and should be manually reviewed by the user. You can find more information on AI generated content accuracy at https://aka.ms/overreliance-framework.
  
  Currently, the sample repository is available in English only and is only tested to support PDF, PNG, and JPEG files up to 20MB in size.

- ### What operational factors and settings allow for effective and responsible use of the Content Processing Solution Accelerator? 

    Users can try different values for some parameters, including but not limited to system prompt, temperature, and max tokens shared as configurable environment variables while running run evaluations during content processing. Schema definitions can and should be customized by the user to match specific business data definitions. Please note that these parameters are only provided as guidance to start the configuration but not as a complete available list to adjust the system behavior. Users should adjust the system to meet their needs. Please always refer to the latest product documentation for these details or reach out to your Microsoft account team if you need assistance.