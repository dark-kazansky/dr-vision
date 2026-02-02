# Design Document: Extraction Configuration Feature

## Overview

The extraction configuration feature extends the OCR application to transform unstructured OCR text into structured data according to user-defined schemas. Users can specify extraction targets (document, page, or table row level) and define schemas with typed fields. The system uses LLM-based extraction to intelligently parse OCR text and populate structured results.

This design enhances the existing ConfigPanel component with a Schema Builder interface and extends the backend OCR processor to handle structured extraction using the configured LLM models.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Nuxt/Vue)                   │
├─────────────────────────────────────────────────────────────┤
│  ConfigPanel.vue                                             │
│  ├─ Extraction Target Selector (Radio buttons)              │
│  ├─ Schema Builder Component                                │
│  │  ├─ Visual Table View                                    │
│  │  └─ JSON Code View                                       │
│  └─ Validation & Help UI                                    │
├─────────────────────────────────────────────────────────────┤
│  useOCR.ts Composable                                        │
│  └─ Extraction Config State Management                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP POST /ocr
                            │ (with extraction_config)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI/Python)                  │
├─────────────────────────────────────────────────────────────┤
│  routes.py                                                   │
│  └─ /ocr endpoint (enhanced with extraction params)         │
├─────────────────────────────────────────────────────────────┤
│  OCRProcessor                                                │
│  ├─ Standard OCR Processing                                 │
│  └─ Structured Extraction (new)                             │
│     ├─ Document-level extraction                            │
│     ├─ Page-level extraction                                │
│     └─ Table row extraction                                 │
├─────────────────────────────────────────────────────────────┤
│  ExtractionEngine (new)                                      │
│  ├─ Schema validation                                        │
│  ├─ LLM-based extraction                                     │
│  ├─ Type conversion & validation                            │
│  └─ Result formatting                                        │
└─────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

1. **Configuration Phase:**
   - User selects extraction target in ConfigPanel
   - User defines schema fields in Schema Builder
   - Frontend validates configuration and updates state

2. **Processing Phase:**
   - User uploads document and clicks "Process OCR"
   - Frontend sends file + OCR config + extraction config to backend
   - Backend performs OCR to get text
   - Backend applies extraction based on target and schema
   - Backend returns structured results

3. **Display Phase:**
   - Frontend receives structured results
   - Results displayed according to extraction target (single object or list)

## Components and Interfaces

### Frontend Components

#### 1. Enhanced ConfigPanel.vue

**Purpose:** Main configuration interface including extraction settings

**New Props:**
```typescript
interface Props {
  availableModels: string[]
  isProcessing: boolean
  canProcess: boolean
  activeTab: string  // NEW: Tab state managed by parent
}
```

**New State:**
```typescript
interface ExtractionConfig {
  enabled: boolean
  target: 'document' | 'page' | 'table_row'
  schema: SchemaField[]
}

interface SchemaField {
  name: string
  type: 'string' | 'number' | 'boolean' | 'date'
  description: string
  required: boolean
}

// Result display state
const resultViewMode = ref<'visual' | 'code'>('visual')
const extractionResult = ref<any>(null)
```

**New Emits:**
```typescript
interface Emits {
  (e: 'process', config: { 
    modelId: string
    tier: string
    processAllPages: boolean
    extractionConfig?: ExtractionConfig
  }): void
  (e: 'update:activeTab', value: string): void  // NEW: Emit tab changes to parent
}
```

**Key Changes:**
- Panel tabs are now managed by parent component (Extraction view)
- ConfigPanel accepts `activeTab` as a prop instead of managing it internally
- Removed padding from config-panel class
- Reduced panel-content padding to 1rem
- Added Result tab content with Visual/Code toggle
- Added result display logic for both visual and code modes

#### 2. SchemaBuilder Component (New)

**Purpose:** Visual interface for defining extraction schemas with auto-generation capability

**Props:**
```typescript
interface Props {
  modelValue: SchemaField[]
  disabled?: boolean
}
```

**Emits:**
```typescript
interface Emits {
  (e: 'update:modelValue', schema: SchemaField[]): void
  (e: 'validation-change', isValid: boolean): void
}
```

**Features:**
- Empty state with "Auto Generate" (orange button with brain icon) and "Create Manually" (white button with border) buttons
- Auto-Generate Schema view with:
  - Title: "Auto-Generate Schema"
  - Subtitle: "Provide a file, prompt, or both to generate your schema."
  - File upload hint with document icon
  - Schema Generation Prompt textarea
  - Back button and Generate button (blue)
- Table view with add/remove rows
- Field name, type, description editing
- Required field toggle
- Validation (unique names, non-empty)
- Bulk operations (mark all required/optional)
- View mode toggle (Visual/Code)
- JSON view with syntax highlighting
- Support for nested object fields (object type)

#### 3. ExtractionTargetSelector Component (New)

**Purpose:** Radio button group for selecting extraction target with individual tooltips

**Props:**
```typescript
interface Props {
  modelValue: 'document' | 'page' | 'table_row'
  disabled?: boolean
}
```

**Emits:**
```typescript
interface Emits {
  (e: 'update:modelValue', target: string): void
}
```

**Features:**
- Three radio options with labels (Document, Page, Table Row)
- Help icons on each individual radio option with custom tooltips:
  - Document: "Extract from the entire document at once (single result)"
  - Page: "Extract from each page separately (list of results)"
  - Table Row: "Extract from each row of a table structure (list of results)"
- Disabled state support
- No help icon on the main "Extraction Target" label

#### 4. Result Display Component (Integrated in ConfigPanel)

**Purpose:** Display extraction results in Visual or Code mode

**Features:**

**Visual Mode:**
- Human-readable HTML format with formatted key-value pairs
- Color-coded values:
  - Booleans: Purple (#7c3aed)
  - Numbers: Green (#059669)
  - Strings: Default color (#111827)
  - Null values: Gray italic (#9ca3af)
- Nested object support with proper indentation (1.5rem per level)
- Array items with numbering and formatting
- Multiple result items for page/table row extraction with clear separation
- Item numbering (Item 1, Item 2, etc.)

**Code Mode:**
- Raw JSON format with syntax highlighting
- Dark background theme (#1f2937)
- Light text color (#e5e7eb)
- Proper indentation (2 spaces)
- Monospace font (Courier New)
- Scrollable for long results

**Toggle Control:**
- Two-button toggle (Visual/Code)
- Light gray background (#f3f4f6)
- Active state: white background with shadow
- Rounded corners (0.5rem)
- Smooth transitions (0.15s)

**Implementation:**
```typescript
// Format extraction result for visual display
const formattedVisualResult = computed(() => {
  if (!extractionResult.value) return ''
  
  const result = extractionResult.value
  let html = '<div class="extraction-visual">'
  
  // Handle different result structures
  if (Array.isArray(result)) {
    // List of results (for page or table row extraction)
    result.forEach((item, index) => {
      html += `<div class="result-item">`
      html += `<h4>Item ${index + 1}</h4>`
      html += formatObject(item)
      html += `</div>`
    })
  } else if (typeof result === 'object') {
    // Single result (for document extraction)
    html += formatObject(result)
  }
  
  html += '</div>'
  return html
})

// Helper function to format object as HTML
function formatObject(obj: any, level = 0): string {
  let html = '<div class="object-content">'
  
  for (const [key, value] of Object.entries(obj)) {
    html += `<div class="field-row" style="margin-left: ${level * 1.5}rem;">`
    html += `<span class="field-key">${key}:</span> `
    
    if (value === null || value === undefined) {
      html += `<span class="field-value null">null</span>`
    } else if (Array.isArray(value)) {
      html += `<span class="field-value array">[${value.length} items]</span>`
      // Format array items recursively
    } else if (typeof value === 'object') {
      html += '<span class="field-value object">{object}</span>'
      html += formatObject(value, level + 1)
    } else if (typeof value === 'boolean') {
      html += `<span class="field-value boolean">${value}</span>`
    } else if (typeof value === 'number') {
      html += `<span class="field-value number">${value}</span>`
    } else {
      html += `<span class="field-value string">${value}</span>`
    }
    
    html += `</div>`
  }
  
  html += '</div>'
  return html
}

// Format extraction result as JSON
const formattedJsonResult = computed(() => {
  if (!extractionResult.value) return ''
  return JSON.stringify(extractionResult.value, null, 2)
})
```

### Frontend Composable Enhancement

#### Enhanced useOCR.ts

**New State:**
```typescript
const extractionConfig = useState<ExtractionConfig | null>('extraction-config', () => null)
```

**Enhanced processFile Method:**
```typescript
const processFile = async (
  fileId: string,
  file: File,
  config: OCRConfig,
  extractionConfig?: ExtractionConfig
) => {
  // ... existing code ...
  
  // Add extraction config to form data if provided
  if (extractionConfig && extractionConfig.enabled) {
    formData.append('extraction_enabled', 'true')
    formData.append('extraction_target', extractionConfig.target)
    formData.append('extraction_schema', JSON.stringify(extractionConfig.schema))
  }
  
  // ... rest of processing ...
}
```

### Backend Components

#### 1. Enhanced routes.py

**New Request Parameters:**
```python
@router.post("/ocr", response_model=OCRResponse)
async def process_ocr(
    file: UploadFile = File(...),
    model_id: str = Form(...),
    process_all_pages: bool = Form(False),
    tier: TierEnum = Form(TierEnum.NORMAL),
    extraction_enabled: bool = Form(False),
    extraction_target: Optional[str] = Form(None),
    extraction_schema: Optional[str] = Form(None),
    config: Config = Depends(get_config)
) -> OCRResponse:
    # Parse extraction config if enabled
    extraction_config = None
    if extraction_enabled and extraction_schema:
        extraction_config = ExtractionConfig.parse_raw(extraction_schema)
    
    # ... existing OCR processing ...
    
    # Apply extraction if configured
    if extraction_config:
        result = apply_extraction(ocr_text, extraction_config, processor)
    
    # ... return results ...
```

#### 2. ExtractionEngine (New Module)

**Purpose:** Core extraction logic using LLM

**Class Structure:**
```python
class ExtractionEngine:
    def __init__(self, llm_client, model_config):
        self.llm_client = llm_client
        self.model_config = model_config
    
    def extract_document(self, text: str, schema: List[SchemaField]) -> Dict[str, Any]:
        """Extract structured data from entire document text"""
        pass
    
    def extract_pages(self, pages: List[str], schema: List[SchemaField]) -> List[Dict[str, Any]]:
        """Extract structured data from each page separately"""
        pass
    
    def extract_table_rows(self, text: str, schema: List[SchemaField]) -> List[Dict[str, Any]]:
        """Detect tables and extract structured data from each row"""
        pass
    
    def _build_extraction_prompt(self, text: str, schema: List[SchemaField]) -> str:
        """Build LLM prompt for extraction"""
        pass
    
    def _parse_llm_response(self, response: str, schema: List[SchemaField]) -> Dict[str, Any]:
        """Parse and validate LLM response against schema"""
        pass
    
    def _convert_field_type(self, value: str, field_type: str) -> Any:
        """Convert extracted string value to specified type"""
        pass
```

**Extraction Prompt Strategy:**

The extraction engine will use structured prompts to guide the LLM:

```
You are a data extraction assistant. Extract structured information from the following text according to the schema provided.

Schema:
- field_name (type): description [required/optional]
- field_name (type): description [required/optional]
...

Text:
{ocr_text}

Instructions:
1. Extract values for each field from the text
2. Return results as valid JSON matching the schema
3. Use null for missing optional fields
4. Ensure types match the schema (string, number, boolean, date)

Response format:
{
  "field_name": value,
  "field_name": value,
  ...
}
```

#### 3. Enhanced OCRProcessor

**New Method:**
```python
def process_with_extraction(
    self,
    file_path: str,
    extraction_config: ExtractionConfig,
    render_dpi: int = 200
) -> ExtractionResult:
    """
    Process document with OCR and apply structured extraction.
    
    Args:
        file_path: Path to document file
        extraction_config: Extraction configuration with target and schema
        render_dpi: DPI for PDF rendering
    
    Returns:
        ExtractionResult with structured data
    """
    # Perform OCR based on file type
    ocr_result = self._perform_ocr(file_path, render_dpi)
    
    # Create extraction engine
    engine = ExtractionEngine(self.llm_client, self.model_config)
    
    # Apply extraction based on target
    if extraction_config.target == 'document':
        structured_data = engine.extract_document(
            ocr_result.text,
            extraction_config.schema
        )
    elif extraction_config.target == 'page':
        structured_data = engine.extract_pages(
            ocr_result.pages,
            extraction_config.schema
        )
    elif extraction_config.target == 'table_row':
        structured_data = engine.extract_table_rows(
            ocr_result.text,
            extraction_config.schema
        )
    
    return ExtractionResult(
        success=True,
        structured_data=structured_data,
        extraction_config=extraction_config
    )
```

#### 4. SchemaGenerationEngine (New Module)

**Purpose:** Generate extraction schemas automatically using LLM based on user prompts and optional file samples

**Class Structure:**
```python
class SchemaGenerationEngine:
    def __init__(self, llm_client, model_config):
        self.llm_client = llm_client
        self.model_config = model_config
    
    def generate_schema(
        self, 
        prompt: str, 
        sample_file: Optional[str] = None
    ) -> List[SchemaField]:
        """
        Generate extraction schema from user prompt and optional sample file.
        
        Args:
            prompt: User's description of what to extract
            sample_file: Optional sample document to analyze
        
        Returns:
            List of generated schema fields
        """
        pass
    
    def _build_generation_prompt(
        self, 
        user_prompt: str, 
        sample_text: Optional[str] = None
    ) -> str:
        """Build LLM prompt for schema generation"""
        pass
    
    def _parse_schema_response(self, response: str) -> List[SchemaField]:
        """Parse LLM response into schema field list"""
        pass
```

**Schema Generation Prompt Strategy:**

```
You are a schema generation assistant. Based on the user's description, generate a structured extraction schema.

User Request:
{user_prompt}

{if sample_text provided:}
Sample Document Text:
{sample_text}
{end if}

Instructions:
1. Analyze the user's request to understand what data they want to extract
2. If a sample document is provided, analyze its structure
3. Generate a list of fields that should be extracted
4. For each field, specify:
   - name: A clear, descriptive field name (use snake_case)
   - type: One of: string, number, boolean, date, object
   - description: What this field represents
   - required: Whether this field is essential (true/false)
5. Return the schema as valid JSON array

Response format:
[
  {
    "name": "field_name",
    "type": "string",
    "description": "Field description",
    "required": true
  },
  ...
]
```

## Data Models

### Frontend Models

```typescript
// Extraction configuration
interface ExtractionConfig {
  enabled: boolean
  target: 'document' | 'page' | 'table_row'
  schema: SchemaField[]
}

// Schema field definition
interface SchemaField {
  name: string
  type: 'string' | 'number' | 'boolean' | 'date' | 'object'
  description: string
  required: boolean
  level?: number  // Hierarchy level for nested objects
  hasChildren?: boolean  // Whether this field has child fields
  expanded?: boolean  // UI state for nested objects
  properties?: SchemaField[]  // Child fields for object type
}

// Enhanced OCR result with extraction
interface OCRResult {
  success: boolean
  text?: string
  structured_data?: any | any[]  // Single object or array based on target
  extraction_config?: ExtractionConfig
  error?: string
  error_type?: string
  pages?: number
  filename?: string
  model?: string
}
```

### Backend Models

```python
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Literal
from enum import Enum

class FieldType(str, Enum):
    """Field type enumeration"""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
    OBJECT = "object"

class SchemaField(BaseModel):
    """Schema field definition"""
    name: str = Field(..., min_length=1, description="Field name")
    type: FieldType = Field(..., description="Field data type")
    description: str = Field(default="", description="Field description")
    required: bool = Field(default=False, description="Whether field is required")
    level: Optional[int] = Field(default=0, description="Hierarchy level for nested objects")
    hasChildren: Optional[bool] = Field(default=False, description="Whether field has children")
    properties: Optional[List['SchemaField']] = Field(default=None, description="Child fields for object type")
    
    @validator('name')
    def validate_name(cls, v):
        """Validate field name is not empty and contains valid characters"""
        if not v or not v.strip():
            raise ValueError("Field name cannot be empty")
        # Allow alphanumeric, underscore, hyphen
        if not all(c.isalnum() or c in ('_', '-', ' ') for c in v):
            raise ValueError("Field name contains invalid characters")
        return v.strip()

class ExtractionTarget(str, Enum):
    """Extraction target enumeration"""
    DOCUMENT = "document"
    PAGE = "page"
    TABLE_ROW = "table_row"

class ExtractionConfig(BaseModel):
    """Extraction configuration"""
    enabled: bool = Field(default=False, description="Whether extraction is enabled")
    target: ExtractionTarget = Field(..., description="Extraction target scope")
    schema: List[SchemaField] = Field(..., min_items=1, description="Extraction schema")
    
    @validator('schema')
    def validate_unique_names(cls, v):
        """Validate all field names are unique"""
        names = [field.name for field in v]
        if len(names) != len(set(names)):
            raise ValueError("Schema field names must be unique")
        return v

class ExtractionResult(BaseModel):
    """Extraction result"""
    success: bool
    structured_data: Optional[Any] = None  # Dict or List[Dict]
    extraction_config: Optional[ExtractionConfig] = None
    error: Optional[str] = None
    error_type: Optional[str] = None

class OCRResponse(BaseModel):
    """Enhanced OCR response with extraction support"""
    success: bool
    text: Optional[str] = None
    structured_data: Optional[Any] = None  # Single object or list
    extraction_config: Optional[Dict[str, Any]] = None
    filename: Optional[str] = None
    model: Optional[str] = None
    pages: Optional[int] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property 1: Extraction target determines result structure

*For any* document, schema, and extraction target selection, when extraction is performed, the result structure should match the target: document target returns a single object, page target returns an array with one object per page, and table_row target returns an array with one object per detected row.

**Validates: Requirements 1.2, 1.3, 1.4, 6.2, 6.3, 6.4**

### Property 2: Extraction config state synchronization

*For any* modification to extraction target or schema fields, the Extraction_Config state should update immediately and synchronously to reflect the changes.

**Validates: Requirements 1.6, 2.7, 5.2**

### Property 3: Schema field name uniqueness validation

*For any* schema, attempting to add or modify a field with a name that already exists in the schema should be rejected with a validation error, and attempting to add a field with an empty name should also be rejected.

**Validates: Requirements 2.3, 8.1, 8.2**

### Property 4: Schema field list operations preserve integrity

*For any* schema, adding a field should increase the schema length by exactly one, and removing a field should decrease the schema length by exactly one and remove only the specified field.

**Validates: Requirements 2.2, 2.5**

### Property 5: Visual and code view round-trip consistency

*For any* valid schema, modifying the schema in visual view then switching to code view should display equivalent JSON, and modifying valid JSON in code view then switching to visual view should display an equivalent table representation.

**Validates: Requirements 3.4, 3.5, 4.4**

### Property 6: Invalid JSON in code view prevents synchronization

*For any* invalid JSON string entered in code view, the system should display a validation error and prevent synchronization to visual view, leaving the visual view unchanged.

**Validates: Requirements 3.6**

### Property 7: Bulk operations apply to all fields

*For any* schema with multiple fields, applying "mark all as required" should set required=true for every field, and applying "mark all as optional" should set required=false for every field.

**Validates: Requirements 4.2, 4.3**

### Property 8: Extraction config included in OCR requests

*For any* OCR request initiated with extraction enabled, the request payload should include the complete current Extraction_Config with target and schema.

**Validates: Requirements 5.3**

### Property 9: Config validation gates processing

*For any* Extraction_Config state, if validation errors exist (duplicate names, empty names, invalid schema), the OCR process button should be disabled, and if the config is valid, the button should be enabled.

**Validates: Requirements 5.4, 8.4, 8.5**

### Property 10: State persistence across re-renders

*For any* Extraction_Config state, triggering a component re-render should not modify the config state - the config should remain identical before and after re-render.

**Validates: Requirements 5.5**

### Property 11: Backend parses extraction config correctly

*For any* valid Extraction_Config sent in an OCR request, the backend should successfully parse the extraction target and schema without errors.

**Validates: Requirements 6.1**

### Property 12: All schema fields present in extraction result

*For any* extraction operation with a defined schema, the structured result should contain keys for all schema fields (even if values are null or contain errors).

**Validates: Requirements 6.5**

### Property 13: Required field extraction errors are indicated

*For any* extraction where a required field cannot be extracted from the document, the result should include an error indicator or null value for that field.

**Validates: Requirements 6.6**

### Property 14: Extraction result matches schema structure

*For any* schema and extraction result, the result should be valid JSON where each field key matches a schema field name, and the structure conforms to the schema definition.

**Validates: Requirements 6.7**

### Property 15: Field type conversion correctness

*For any* schema field with a specified type (string, number, boolean, date), the extracted value should either be successfully converted to that type, or include a type conversion error indicator with the raw string value.

**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6**

### Property 16: Result display format matches extraction target

*For any* extraction result, if the target was document, the UI should display a single object structure, and if the target was page or table_row, the UI should display a list structure with clear item separation.

**Validates: Requirements 9.2, 9.3**

### Property 17: Result display includes all required information

*For any* displayed extraction result, the UI should show field names, extracted values, and data types for all fields in the result.

**Validates: Requirements 9.4**

### Property 18: Extraction errors are visually highlighted

*For any* extraction result containing field-level errors, the UI should highlight those specific fields and display error messages.

**Validates: Requirements 9.5**

### Property 19: Auto-generate button displays in empty state

*For any* schema builder state where the schema is empty, the empty state view should display both "Auto Generate" and "Create Manually" buttons.

**Validates: Requirements 10.1**

### Property 20: Auto-generate view displays on button click

*For any* empty schema state, clicking the "Auto Generate" button should transition to the Auto-Generate Schema view with title, subtitle, file upload hint, prompt textarea, and action buttons.

**Validates: Requirements 10.2, 10.3, 10.4, 10.5**

### Property 21: Back button returns to empty state

*For any* Auto-Generate Schema view state, clicking the "Back" button should return to the empty state view and clear the prompt textarea.

**Validates: Requirements 10.6**

### Property 22: Generate button requires non-empty prompt

*For any* Auto-Generate Schema view state, the "Generate" button should be disabled when the prompt textarea is empty and enabled when it contains text.

**Validates: Requirements 10.8**

### Property 23: Schema generation produces valid schema

*For any* valid generation prompt, the schema generation should produce a list of SchemaField objects that pass all validation rules (unique names, valid types, non-empty names).

**Validates: Requirements 10.7, 10.9**

### Property 24: ConfigPanel footer button styling

*For any* ConfigPanel state, the "Process" button should have orange background when enabled and gray background when disabled, and the "Cancel" button should have white background with red border when displayed.

**Validates: Requirements 11.1, 11.2, 11.4, 11.5**

### Property 25: Individual extraction target tooltips

*For any* extraction target radio option, hovering over its help icon should display a custom tooltip specific to that target option explaining its extraction behavior.

**Validates: Requirements 1.5**

### Property 26: Visual mode displays formatted HTML

*For any* extraction result, when Visual mode is selected, the display should contain HTML-formatted key-value pairs with proper structure.

**Validates: Requirements 9.3**

### Property 27: Visual mode color-codes values by type

*For any* extraction result value, when displayed in Visual mode, the value should have the correct color coding based on its type: booleans in purple, numbers in green, strings in default color, and null values in gray italic.

**Validates: Requirements 9.4**

### Property 28: Visual mode shows nested object hierarchy

*For any* extraction result containing nested objects, when displayed in Visual mode, each nesting level should increase indentation by 1.5rem.

**Validates: Requirements 9.5**

### Property 29: Visual mode formats arrays with numbering

*For any* extraction result containing arrays, when displayed in Visual mode, array items should be numbered and properly indented.

**Validates: Requirements 9.6**

### Property 30: Document target displays single result in Visual mode

*For any* document-level extraction result, when displayed in Visual mode, the output should show a single result object without item numbering.

**Validates: Requirements 9.7**

### Property 31: Page/Row targets display multiple items in Visual mode

*For any* page or table row extraction result, when displayed in Visual mode, the output should show multiple result items with clear separation and item numbering (Item 1, Item 2, etc.).

**Validates: Requirements 9.8**

### Property 32: Code mode displays valid JSON

*For any* extraction result, when Code mode is selected, the display should contain valid JSON with 2-space indentation.

**Validates: Requirements 9.9**

## Error Handling

### Frontend Error Handling

1. **Schema Validation Errors:**
   - Duplicate field names: Display inline error message
   - Empty field names: Display inline error message
   - Invalid JSON in code view: Display error banner with details
   - Action: Disable process button until resolved

2. **State Management Errors:**
   - Failed state updates: Log error, show user notification
   - Invalid config structure: Reset to default config
   - Action: Prevent processing with invalid state

3. **API Request Errors:**
   - Network failures: Display retry option
   - Backend validation errors: Display error details
   - Timeout: Display timeout message with retry
   - Action: Keep config intact for retry

### Backend Error Handling

1. **Config Parsing Errors:**
   - Invalid JSON: Return 400 with parsing error details
   - Missing required fields: Return 400 with validation error
   - Invalid field types: Return 400 with type error details
   - Action: Reject request before processing

2. **Extraction Errors:**
   - LLM API failures: Return 500 with error details
   - Timeout during extraction: Return 504 with timeout message
   - Invalid LLM response: Return 500 with parsing error
   - Action: Include partial results if available

3. **Type Conversion Errors:**
   - Failed number conversion: Include raw value + error flag
   - Failed date parsing: Include raw value + error flag
   - Failed boolean interpretation: Include raw value + error flag
   - Action: Continue processing other fields

4. **Table Detection Errors:**
   - No tables found: Return empty array with warning
   - Malformed table structure: Return partial results with warning
   - Action: Provide best-effort extraction

### Error Response Format

```python
{
  "success": false,
  "error": "Human-readable error message",
  "error_type": "validation_error | processing_error | extraction_error | timeout",
  "details": {
    "field": "field_name",  # For field-specific errors
    "raw_value": "...",     # For type conversion errors
    "expected_type": "number"  # For type conversion errors
  }
}
```

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests for comprehensive coverage:

- **Unit tests**: Verify specific examples, edge cases, UI interactions, and error conditions
- **Property tests**: Verify universal properties across all inputs using randomized test data

### Property-Based Testing

**Library:** We will use **fast-check** for frontend TypeScript property tests and **Hypothesis** for backend Python property tests.

**Configuration:**
- Minimum 100 iterations per property test
- Each property test references its design document property number
- Tag format: `Feature: extraction-configuration, Property {number}: {property_text}`

**Property Test Coverage:**

Each correctness property (1-18) must be implemented as a property-based test:

1. Property 1: Generate random documents, schemas, and targets; verify result structure
2. Property 2: Generate random config modifications; verify state updates
3. Property 3: Generate schemas with duplicate/empty names; verify rejection
4. Property 4: Generate random schemas; verify add/remove operations
5. Property 5: Generate random schemas; verify visual↔code round-trip
6. Property 6: Generate invalid JSON; verify error handling
7. Property 7: Generate random schemas; verify bulk operations
8. Property 8: Generate random configs; verify request payload inclusion
9. Property 9: Generate valid/invalid configs; verify button state
10. Property 10: Generate random configs; verify persistence across re-renders
11. Property 11: Generate random configs; verify backend parsing
12. Property 12: Generate random schemas; verify all fields present in results
13. Property 13: Generate documents missing required fields; verify error indicators
14. Property 14: Generate random schemas; verify result structure matches schema
15. Property 15: Generate random field types and values; verify conversion or errors
16. Property 16: Generate random targets; verify UI display format
17. Property 17: Generate random results; verify all info displayed
18. Property 18: Generate results with errors; verify error highlighting

### Unit Testing

**Frontend Unit Tests:**
- Component rendering (ConfigPanel, SchemaBuilder, ExtractionTargetSelector)
- User interactions (button clicks, input changes, dropdown selections)
- Tooltip display on hover
- View mode switching
- Specific validation scenarios
- Error message display

**Backend Unit Tests:**
- Endpoint request/response handling
- Specific extraction scenarios (invoice, receipt, form examples)
- Type conversion edge cases (empty strings, special characters)
- Table detection with known table structures
- Error response formatting

### Integration Testing

**End-to-End Scenarios:**
1. Complete workflow: Configure schema → Upload document → Process → View results
2. Multi-page PDF with page-level extraction
3. Table document with row-level extraction
4. Error recovery: Invalid config → Fix → Retry
5. View switching: Modify in visual → Verify in code → Modify in code → Verify in visual

### Test Data

**Generators for Property Tests:**

Frontend:
```typescript
// Generate random schema fields
const arbSchemaField = fc.record({
  name: fc.string({ minLength: 1, maxLength: 20 }),
  type: fc.constantFrom('string', 'number', 'boolean', 'date'),
  description: fc.string({ maxLength: 100 }),
  required: fc.boolean()
})

// Generate random extraction configs
const arbExtractionConfig = fc.record({
  enabled: fc.boolean(),
  target: fc.constantFrom('document', 'page', 'table_row'),
  schema: fc.array(arbSchemaField, { minLength: 1, maxLength: 10 })
})
```

Backend:
```python
from hypothesis import strategies as st

# Generate random schema fields
schema_field_strategy = st.builds(
    SchemaField,
    name=st.text(min_size=1, max_size=20),
    type=st.sampled_from(['string', 'number', 'boolean', 'date']),
    description=st.text(max_size=100),
    required=st.booleans()
)

# Generate random extraction configs
extraction_config_strategy = st.builds(
    ExtractionConfig,
    enabled=st.booleans(),
    target=st.sampled_from(['document', 'page', 'table_row']),
    schema=st.lists(schema_field_strategy, min_size=1, max_size=10)
)
```

## Implementation Notes

### LLM Extraction Approach

The extraction engine uses the existing LLM models configured in the application (via LM Studio or similar). The prompt engineering approach:

1. **Structured Prompts:** Clear instructions with schema definition
2. **JSON Output:** Request JSON format for easy parsing
3. **Type Hints:** Include type information in prompts
4. **Examples:** Optionally include few-shot examples for complex schemas

### Table Detection Strategy

For table row extraction, we use a two-phase approach:

1. **Detection Phase:** Use LLM to identify table boundaries and structure
2. **Extraction Phase:** Extract schema fields from each detected row

Alternative: Use regex/heuristics for simple table detection before LLM extraction.

### Performance Considerations

1. **Caching:** Cache LLM responses for identical text+schema combinations
2. **Batching:** For page-level extraction, consider batching pages in single LLM call
3. **Streaming:** For large documents, consider streaming results
4. **Timeouts:** Set reasonable timeouts for LLM calls (30-60 seconds)

### UI/UX Considerations

1. **Progressive Disclosure:** Hide schema builder until extraction is enabled
2. **Inline Help:** Tooltips on all complex features
3. **Visual Feedback:** Loading states during extraction
4. **Error Recovery:** Clear error messages with actionable fixes
5. **Responsive Design:** Schema builder works on various screen sizes

### Backward Compatibility

The feature is fully backward compatible:
- Extraction is opt-in (disabled by default)
- Existing OCR functionality unchanged when extraction disabled
- API accepts optional extraction parameters
- Frontend gracefully handles missing extraction config

## Future Enhancements

1. **Schema Templates:** Pre-built schemas for common document types (invoices, receipts, forms)
2. **Field Validation Rules:** Min/max values, regex patterns, custom validators
3. **Conditional Fields:** Fields that appear based on other field values
4. **Multi-language Support:** Extraction from documents in various languages
5. **Confidence Scores:** LLM confidence for each extracted field
6. **Manual Correction:** UI for correcting extraction errors
7. **Export Formats:** Export structured data as CSV, Excel, or database inserts
8. **Batch Processing:** Process multiple documents with same schema
