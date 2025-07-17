# Customizing Schema and Data

## How to Use Your Own Data
Files that are to be processed can be passed to the API to queue them for processing. Each file passed will include a parameter for what schema it will be mapped and transformed into (EX: an invoice). 

The schema file should represent what fields are in the document and should be thought of as a "standardized output" for any type of document this schema is applied to. For example, the Content Processing solution accelerator includes an "invoice" schema that includes a number of fields like "invoice date" or "line items". 

Using AI, the processing pipeline will extract what is preceived as is the "invoice date" and use that extraction to output into the "invoice date" field.

With this concept in mind, schemas need to be created specific to your business and domain requirements. A lot of times schemas may be generally common across industries, but this allows for variations specific to your use case.

A schema should be created that includes all fields you expect to extract and transform to. Once a schema is added specific to your intended files, you can then programmatically call the API endpoints to submit and process the file for that schema or utilize the web UI to manually process and review.

## Steps to add a Custom Schema
1. **Create .py class to define schema**<br/>
    A new class needs to be created that defines the schema as a strongly typed python class. This class inherits from _pydantic_.
    
    > **Schema Folder:** [/src/ContentProcessorAPI/samples/schemas/](/src/ContentProcessorAPI/samples/schemas/)<br/> All schema classes should be placed into this folder

    
    > **Sample Schema - Invoice:** [/src/ContentProcessorAPI/samples/schemas/invoice.py](/src/ContentProcessorAPI/samples/schemas/invoice.py)
    

    Duplicate this class file and update with a class definition that represents the new schema you'd like to create. This should have **fields** and **subclasses** and **methods** that represent the makeup of the schema. 
    
    > **Optional:** You can also use GitHub Copilot to create a schema definition if desired. We used this sample prompt and used the invoice.py schema file to create additional sample schemas:

       Generate a Schema Class based on the following Invoice.py schema definition, which has been built and derived from Pydantic BaseModel class. The generated Schema Class should be called "Used Car Sales Agreement Contract" schema file. Please define the entities based on normal Used Car Sales Agreement Contract documents in the industry.
     

    #### Class and Subclass Definitions
    Each schema is represented as a .py file with one or more class definitions. The file should include:
    - Base import statements.
    - Class and subclass definitions that inherit from pydantic BaseModel.
    - Each class has fields, methods, and meta data.
    - Classes include a class name, a string describing the class, its attributes, and the attributes descriptions. These are used during mapping and data transformation in the processing pipeline.
    - Classes also include fields and methods.


    #### Fields

    - Fields are defined in the class to represent what data this class holds. This is a 1-to-1 relationship with what gets extracted from a file being processed is mapped to this specific field. If your file has a field you'd like to extract called "invoice date", you'd have a field defined in your class to represent that.
    - Each field has annotations to designate if it is optional or required.
    - Fields also have a string describing what it is and it is used as a prompt to help with data evaluation/validation, mapping and transformation in the processing pipeline. Include an example in the description to help with specificity or experiment with simple logic to help the LLM process the content correctly.


    #### Methods
    - There are three required static methods that need to be included in a schema definition:
        1. example() - returns an object of this schema
        2. from_json() - creates an object from a JSON string
        3. to_dict() - converts object to a dictionary

2. **Use API to register a new schema**<br/>
    After the Schema class file has been created, you will next need to register the schema in the system. This adds the schema to the Cosmos DB and stores your class file in blob storage for use in the processing pipeline. 
    
    To do this, you can reference the sample REST Client file with an API call setup with the **[POST] schemavault** request labeled "Register Schema file with information" located here:
    > [/src/ContentProcessorAPI/test_http/invoke_APIs.http](/src/ContentProcessorAPI/samples/test_http/invoke_APIs.http)

    Below is the sample call with areas you would modify:

    > **Note:** To create and execute requests in `.http` files, you must install the [REST Client VSCode extension](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) in your Visual Studio Code. Ensure this extension is installed before proceeding to the next step.

    1. The file name for created Schema file(**<< your file >>**.py)
    2. The file location of the schema class will be registered.
    3. The name of the main schema class that will get instantiated.
    4. Friendly, readable description of the schema. this value will be show up in UI.

    > ![Schema Registartion REST API call with payload](./images/schema-register-api.png)

    After running the request, you will see a response with an ID confirming the schema has been added. It will now show up in the web UI in the schema dropdown as well.

