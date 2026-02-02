# Requirements Document

## Introduction

This document specifies the requirements for adding extraction configuration capabilities to the OCR application. The feature enables users to define structured data extraction schemas and specify extraction targets (document, page, or table row level) to transform unstructured OCR text into structured data according to user-defined schemas.

## Glossary
- **Configuration_Mode**: Choose the way to extraction by toggle button to show basic or advance way to config extraction
- **Extraction_Config**: Configuration object containing extraction target and schema definition
- **Extraction_Target**: The scope at which extraction is performed (Document, Page, or Table_Row)
- **Extraction_Schema**: User-defined structure specifying fields to extract, their types, and descriptions
- **Schema_Field**: Individual field definition within an extraction schema, containing name, type, description, and required flag
- **Field_Type**: Data type for extracted field values (string, number, boolean, date)
- **ConfigPanel**: Vue component for OCR configuration and extraction settings
- **Schema_Builder**: Visual interface component for defining extraction schemas
- **OCR_Processor**: Backend service that performs OCR and structured data extraction
- **Structured_Result**: Extraction output conforming to the defined schema

## Requirements

### Requirement 1: Extraction Target Selection

**User Story:** As a user, I want to select the extraction target scope, so that I can control whether data is extracted from the entire document, per page, or per table row.

#### Acceptance Criteria

1. WHEN the ConfigPanel is displayed, THE System SHALL present three extraction target options: Document, Page, and Table_Row
2. WHEN a user selects the Document target, THE System SHALL configure extraction to process the entire document and return a single result object
3. WHEN a user selects the Page target, THE System SHALL configure extraction to process each page separately and return a list of result objects
4. WHEN a user selects the Table_Row target, THE System SHALL configure extraction to process each detected table row and return a list of result objects
5. WHEN a user hovers over a help icon on an individual extraction target radio option, THE System SHALL display a custom tooltip explaining the extraction behavior for that specific target
6. WHEN the user changes the extraction target, THE System SHALL update the Extraction_Config state with the new target value

### Requirement 2: Schema Field Management

**User Story:** As a user, I want to define extraction schema fields with names, types, and descriptions, so that I can specify exactly what data to extract from documents.

#### Acceptance Criteria

1. WHEN the Schema_Builder is displayed with no fields, THE System SHALL present an empty state with "Auto Generate" and "Create Manually" buttons
2. WHEN a user clicks the "Auto Generate" button, THE System SHALL display the Auto-Generate Schema view
3. WHEN a user clicks the "Create Manually" button, THE System SHALL display the schema table interface with columns for Field_Name, Field_Type, and Field_Description
4. WHEN the schema table is displayed, WHEN a user clicks an "Add Field" button, THE System SHALL add a new empty row to the schema table
5. WHEN a user enters a field name, THE System SHALL validate that the name is non-empty and unique within the schema
6. WHEN a user selects a Field_Type dropdown, THE System SHALL present options: string, number, boolean, date, and object
7. WHEN a user clicks a remove button on a schema row, THE System SHALL remove that field from the schema
8. WHEN a user marks a field as required, THE System SHALL indicate the required status with an asterisk visual indicator
9. WHEN the schema is modified, THE System SHALL update the Extraction_Config state with the new schema definition

### Requirement 3: Schema View Modes

**User Story:** As a user, I want to toggle between visual table view and JSON code view of my schema, so that I can work in my preferred format and verify the schema structure.

#### Acceptance Criteria

1. WHEN the Schema_Builder is displayed, THE System SHALL provide a toggle control for switching between Visual and Code view modes
2. WHEN a user selects Visual view mode, THE System SHALL display the schema as an editable table interface
3. WHEN a user selects Code view mode, THE System SHALL display the schema as formatted JSON text
4. WHEN the schema is modified in Visual view, THE System SHALL synchronize the changes to the Code view representation
5. WHEN the schema is modified in Code view, THE System SHALL validate the JSON and synchronize changes to the Visual view representation
6. IF invalid JSON is entered in Code view, THEN THE System SHALL display a validation error message and prevent synchronization

### Requirement 4: Schema Bulk Operations

**User Story:** As a user, I want to apply settings to all schema fields at once, so that I can efficiently configure common properties across multiple fields.

#### Acceptance Criteria

1. WHEN the Schema_Builder contains multiple fields, THE System SHALL provide an "Apply to all fields" action control
2. WHEN a user selects "Mark all as required" from bulk actions, THE System SHALL set the required flag to true for all schema fields
3. WHEN a user selects "Mark all as optional" from bulk actions, THE System SHALL set the required flag to false for all schema fields
4. WHEN a bulk action is applied, THE System SHALL update all affected fields and reflect changes in both Visual and Code views

### Requirement 5: Extraction Configuration State Management

**User Story:** As a developer, I want extraction configuration stored in application state, so that it can be accessed by components and sent with OCR requests.

#### Acceptance Criteria

1. WHEN the application initializes, THE System SHALL create an Extraction_Config state object with default values
2. WHEN extraction target or schema is modified, THE System SHALL update the Extraction_Config state immediately
3. WHEN an OCR request is initiated, THE System SHALL include the current Extraction_Config in the request payload
4. WHEN the Extraction_Config state changes, THE System SHALL validate the configuration before allowing OCR processing
5. THE System SHALL persist the Extraction_Config state across component re-renders

### Requirement 6: Backend Extraction Processing

**User Story:** As a system, I want to process documents according to extraction configuration, so that I can return structured data matching the user-defined schema.

#### Acceptance Criteria

1. WHEN the backend receives an OCR request with Extraction_Config, THE System SHALL parse the extraction target and schema from the request
2. WHEN extraction target is Document, THE OCR_Processor SHALL extract data from the complete OCR text and return a single structured result
3. WHEN extraction target is Page, THE OCR_Processor SHALL extract data from each page's OCR text separately and return a list of structured results
4. WHEN extraction target is Table_Row, THE OCR_Processor SHALL detect table structures, extract data from each row, and return a list of structured results
5. WHEN extracting data, THE OCR_Processor SHALL attempt to populate all schema fields according to their specified types
6. WHEN a required field cannot be extracted, THE System SHALL include an error or null indicator in the result for that field
7. WHEN extraction completes, THE System SHALL return structured results in JSON format matching the schema definition

### Requirement 7: Field Type Validation and Conversion

**User Story:** As a system, I want to validate and convert extracted values to their specified field types, so that structured results have correct data types.

#### Acceptance Criteria

1. WHEN a schema field has type "string", THE OCR_Processor SHALL extract the value as a text string
2. WHEN a schema field has type "number", THE OCR_Processor SHALL attempt to parse the extracted value as a numeric type
3. WHEN a schema field has type "boolean", THE OCR_Processor SHALL attempt to interpret the extracted value as true or false
4. WHEN a schema field has type "date", THE OCR_Processor SHALL attempt to parse the extracted value as a date format
5. IF type conversion fails for a field, THEN THE System SHALL include the raw string value and a type conversion error indicator
6. WHEN all fields are successfully extracted and converted, THE System SHALL return a structured result with properly typed values

### Requirement 8: UI Integration and Validation

**User Story:** As a user, I want clear validation feedback and help text in the extraction configuration UI, so that I can correctly configure extraction settings.

#### Acceptance Criteria

1. WHEN a user enters a duplicate field name, THE System SHALL display a validation error message indicating the name must be unique
2. WHEN a user attempts to save a schema with empty field names, THE System SHALL display a validation error and prevent saving
3. WHEN a user hovers over help icons, THE System SHALL display contextual tooltips explaining the feature
4. WHEN validation errors exist, THE System SHALL disable the OCR process button until errors are resolved
5. WHEN the extraction configuration is valid, THE System SHALL enable the OCR process button
6. THE System SHALL maintain consistent styling with the existing ConfigPanel component design

### Requirement 9: Extraction Results Display

**User Story:** As a user, I want to view structured extraction results in a clear format with multiple display modes, so that I can verify the extracted data matches my expectations in my preferred format.

#### Acceptance Criteria

1. WHEN extraction processing completes successfully, THE System SHALL display the structured results in the Result tab
2. WHEN the Result tab is displayed, THE System SHALL provide a toggle control for switching between Visual and Code view modes
3. WHEN a user selects Visual view mode, THE System SHALL display extraction results in human-readable HTML format with formatted key-value pairs
4. WHEN displaying results in Visual mode, THE System SHALL color-code values by type: booleans in purple, numbers in green, strings in default color, and null values in gray italic
5. WHEN displaying results in Visual mode with nested objects, THE System SHALL show proper indentation and hierarchy
6. WHEN displaying results in Visual mode with arrays, THE System SHALL format array items with proper numbering and indentation
7. WHEN extraction target is Document in Visual mode, THE System SHALL display a single result object with all extracted fields
8. WHEN extraction target is Page or Table_Row in Visual mode, THE System SHALL display multiple result items with clear separation and item numbering
9. WHEN a user selects Code view mode, THE System SHALL display extraction results as formatted JSON with syntax highlighting
10. WHEN displaying results in Code mode, THE System SHALL use a dark background theme with proper indentation (2 spaces) and monospace font
11. WHEN extraction errors occur for specific fields, THE System SHALL highlight those fields and display error messages in both view modes
12. WHEN no extraction configuration is defined, THE System SHALL display OCR results in the original text format

### Requirement 10: Auto-Generate Schema

**User Story:** As a user, I want to automatically generate extraction schemas using AI, so that I can quickly create schemas without manually defining each field.

#### Acceptance Criteria

1. WHEN the Schema_Builder displays the empty state, THE System SHALL show an "Auto Generate" button with an orange background and brain icon
2. WHEN a user clicks the "Auto Generate" button, THE System SHALL display the Auto-Generate Schema view with title "Auto-Generate Schema" and subtitle "Provide a file, prompt, or both to generate your schema."
3. WHEN the Auto-Generate Schema view is displayed, THE System SHALL show a file upload hint with a document icon
4. WHEN the Auto-Generate Schema view is displayed, THE System SHALL show a "Schema Generation Prompt" textarea for user input
5. WHEN the Auto-Generate Schema view is displayed, THE System SHALL show a "Back" button and a "Generate" button (blue color)
6. WHEN a user clicks the "Back" button, THE System SHALL return to the empty state view and clear the prompt textarea
7. WHEN a user clicks the "Generate" button with a non-empty prompt, THE System SHALL generate a schema using the LLM based on the provided prompt and optional file
8. WHEN the "Generate" button is clicked without a prompt, THE System SHALL keep the button disabled
9. WHEN schema generation completes successfully, THE System SHALL populate the schema table with the generated fields and close the Auto-Generate view
10. IF schema generation fails, THEN THE System SHALL display an error message and allow the user to retry or go back

### Requirement 11: ConfigPanel Footer Styling

**User Story:** As a user, I want clear and consistent action buttons in the configuration panel, so that I can easily process documents or cancel operations.

#### Acceptance Criteria

1. WHEN the ConfigPanel footer is displayed, THE System SHALL show a "Process" button styled with orange background matching the run-parse-btn class
2. WHEN processing is active, THE System SHALL display a "Cancel" button with white background, red border, and red text
3. WHEN a user hovers over the "Cancel" button, THE System SHALL change the background to red and text to white
4. WHEN the "Process" button is disabled due to invalid configuration, THE System SHALL display it with gray background and reduced opacity
5. WHEN the "Process" button is enabled, THE System SHALL display it with orange background and white text
6. WHEN a user hovers over the enabled "Process" button, THE System SHALL darken the orange background color

### Requirement 12: Panel Structure and Layout

**User Story:** As a user, I want a consistent and organized panel structure across different views, so that I can easily navigate between configuration and results.

#### Acceptance Criteria

1. WHEN the Extraction view is displayed, THE System SHALL show panel tabs outside the ConfigPanel component
2. WHEN panel tabs are displayed, THE System SHALL include a Build tab with sliders icon and a Result tab with document icon
3. WHEN the ConfigPanel component is rendered, THE System SHALL accept activeTab as a prop instead of managing tab state internally
4. WHEN the config-panel class is applied, THE System SHALL not include padding on the panel container itself
5. WHEN the panel-content class is applied, THE System SHALL use 1rem padding for content areas
6. WHEN switching between tabs, THE System SHALL maintain the panel structure and styling consistency
7. WHEN the Build tab is active, THE System SHALL display Parser Tiers, Extractor Tiers, Process all PDF pages checkbox, and Extraction Configuration section
8. WHEN the Result tab is active, THE System SHALL display the Visual/Code toggle and extraction results

