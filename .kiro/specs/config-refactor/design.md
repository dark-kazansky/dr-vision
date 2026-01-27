# Design Document: OCR Web UI Configuration Refactoring

## Overview

This design describes the refactoring of the OCR Web UI Flask application from a monolithic structure to a modular, configuration-driven architecture. The refactoring will separate concerns into distinct modules while maintaining all existing functionality and API compatibility.

The key architectural changes include:
- Extracting configuration into external YAML files
- Separating business logic from Flask route handlers
- Creating dedicated modules for OCR processing, utilities, and configuration management
- Implementing configuration validation and environment variable support

## Architecture

### Current Architecture

```
app.py (monolithic, ~500 lines)
├── Configuration (hardcoded at top)
├── Utility Functions
├── OCR Processing Functions
└── Flask Routes
```

### Target Architecture

```
config/
├── config.yaml              # Main configuration file
└── config_schema.py         # Configuration validation

src/
├── __init__.py
├── config.py                # Configuration loader and validator
├── ocr_processor.py         # OCR processing logic
├── utils.py                 # Utility functions
└── routes.py                # Flask route handlers

app.py                       # Main application entry point (minimal)
```

### Module Responsibilities

**config.yaml**: Contains all configurable settings including API providers, model configurations, Flask settings, and file upload constraints.

**config.py**: Loads configuration from YAML, validates against schema, applies environment variable overrides, and provides a singleton configuration object.

**ocr_processor.py**: Contains all OCR processing logic including image OCR, PDF OCR (single and multi-page), and API communication. Independent of Flask.

**utils.py**: Contains utility functions for file validation, type detection, and server status checks.

**routes.py**: Contains Flask route handlers that delegate to business logic modules.

**app.py**: Minimal entry point that initializes Flask app, loads configuration, registers routes, and starts the server.

## Components and Interfaces

### Configuration Module (config.py)

**Purpose**: Load, validate, and provide access to application configuration.

**Interface**:
```python
class Config:
    """Singleton configuration object."""
    
    @classmethod
    def load(cls, config_path: str = 'config/config.yaml') -> 'Config':
        """Load configuration from file with environment variable overrides."""
        pass
    
    @property
    def models(self) -> dict:
        """Get model configurations."""
        pass
    
    @property
    def flask_config(self) -> dict:
        """Get Flask-specific configuration."""
        pass
    
    @property
    def upload_config(self) -> dict:
        """Get file upload configuration."""
        pass
    
    def get_model_config(self, model_id: str) -> Optional[dict]:
        """Get configuration for a specific model."""
        pass
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        pass
```

**Environment Variable Overrides**:
- `LM_STUDIO_BASE_URL`: Override base URL for LM Studio
- `DEFAULT_MODEL_ID`: Override default model
- `UPLOAD_FOLDER`: Override upload directory
- `MAX_FILE_SIZE_MB`: Override maximum file size

### OCR Processor Module (ocr_processor.py)

**Purpose**: Handle all OCR processing logic independent of Flask.

**Interface**:
```python
class OCRProcessor:
    """Handles OCR processing for images and PDFs."""
    
    def __init__(self, model_config: dict):
        """Initialize with model configuration."""
        pass
    
    def process_image(self, image_path: str) -> str:
        """Process OCR on an image file."""
        pass
    
    def process_pdf_page(self, pdf_path: str, page_number: int) -> str:
        """Process OCR on a single PDF page."""
        pass
    
    def process_pdf_all_pages(self, pdf_path: str) -> dict:
        """Process OCR on all PDF pages."""
        pass

class OCRResult:
    """Result of OCR processing."""
    success: bool
    text: Optional[str]
    error: Optional[str]
    error_type: Optional[str]
    pages: Optional[int]
```

**Error Types**:
- `invalid_model`: Model ID not found in configuration
- `invalid_file`: File type not supported or file invalid
- `connection_error`: Cannot connect to API provider
- `processing_error`: Error during OCR processing
- `file_too_large`: File exceeds size limit

### Utilities Module (utils.py)

**Purpose**: Provide reusable utility functions.

**Interface**:
```python
def allowed_file(filename: str, allowed_extensions: set) -> bool:
    """Check if file extension is allowed."""
    pass

def get_file_type(filename: str) -> Optional[str]:
    """Determine file type from extension."""
    pass

def check_server_status(base_url: str) -> dict:
    """Check if API server is running."""
    pass

def secure_save_file(file, upload_folder: str) -> str:
    """Securely save uploaded file and return path."""
    pass
```

### Routes Module (routes.py)

**Purpose**: Define Flask route handlers that delegate to business logic.

**Interface**:
```python
def register_routes(app: Flask, config: Config) -> None:
    """Register all routes with the Flask app."""
    pass

# Routes to register:
# GET  /              - Serve main HTML page
# GET  /<path>        - Serve static files
# GET  /health        - Health check endpoint
# POST /ocr           - OCR processing endpoint
```

## Data Models

### Configuration Schema (config.yaml)

```yaml
# API Provider Configuration
api_providers:
  lm_studio:
    base_url: "http://localhost:1234"
    timeout: 30

# Model Configurations
models:
  lightonocr-2-1b:
    model_id: "lightonocr-2-1b"
    provider: "lm_studio"
    name: "LightOnOCR-2-1B"
    max_tokens: 4096
    temperature: 0.2
    top_p: 0.9
  
  deepseek-ocr:
    model_id: "deepseek-ocr"
    provider: "lm_studio"
    name: "DeepSeek OCR"
    max_tokens: 4096
    temperature: 0.2
    top_p: 0.9
  
  nanonets-ocr2-3b:
    model_id: "nanonets-ocr2-3b"
    provider: "lm_studio"
    name: "Nanonets OCR2-3B"
    max_tokens: 4096
    temperature: 0.2
    top_p: 0.9

# Default model selection
default_model: "lightonocr-2-1b"

# Flask Configuration
flask:
  debug: true
  host: "0.0.0.0"
  port: 5001
  static_folder: "static"
  static_url_path: "/static"

# File Upload Configuration
upload:
  folder: "uploads"
  max_size_mb: 10
  allowed_extensions:
    - png
    - jpg
    - jpeg
    - pdf

# PDF Processing Configuration
pdf:
  render_dpi: 200
  default_process_all_pages: false
```

### Model Configuration Object

```python
@dataclass
class ModelConfig:
    model_id: str
    provider: str
    name: str
    base_url: str  # Resolved from provider
    max_tokens: int = 4096
    temperature: float = 0.2
    top_p: float = 0.9
```

### OCR Request

```python
@dataclass
class OCRRequest:
    file_path: str
    file_type: str  # 'image' or 'pdf'
    model_id: str
    process_all_pages: bool = False
```

### OCR Response

```python
@dataclass
class OCRResponse:
    success: bool
    text: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    pages: Optional[int] = None
    filename: Optional[str] = None
    model: Optional[str] = None
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Configuration Loading Completeness

*For any* valid configuration file, loading the configuration should result in a Config object that contains all required sections (api_providers, models, flask, upload) with all required fields populated.

**Validates: Requirements 1.1, 1.3**

### Property 2: Configuration Reload Consistency

*For any* two different valid configuration files, loading the first, then loading the second should result in the Config object reflecting the second file's values, not the first.

**Validates: Requirements 1.2**

### Property 3: Configuration Validation Rejection

*For any* configuration file missing required fields or containing invalid values, the validation function should return a non-empty list of specific error messages describing each problem.

**Validates: Requirements 1.4, 7.1, 7.2, 7.3, 7.4**

### Property 4: Dynamic Model Registration

*For any* valid model configuration added to the config file, after loading the configuration, the model should be accessible via get_model_config() and should contain all required fields (model_id, provider, name, base_url).

**Validates: Requirements 2.1, 2.2**

### Property 5: Multi-Provider Routing

*For any* two models configured with different provider base URLs, OCR requests to each model should send API calls to their respective base URLs.

**Validates: Requirements 2.3**

### Property 6: Invalid Model Error Response

*For any* model ID not present in the configuration, requesting OCR with that model ID should return an error response containing the list of available model IDs.

**Validates: Requirements 2.4**

### Property 7: Configuration Nested Access

*For any* nested configuration value (e.g., models.lightonocr-2-1b.temperature), the Config object should provide access to that value through the appropriate accessor method.

**Validates: Requirements 4.3**

### Property 8: API Endpoint Behavioral Equivalence

*For any* valid OCR request (file, model, parameters), the refactored application should return a response with the same structure and success/error status as the original implementation.

**Validates: Requirements 5.1, 5.4**

### Property 9: File Type Support Preservation

*For any* file with an extension in the set {png, jpg, jpeg, pdf}, the refactored application should accept and process the file, and for any file with an extension not in that set, the application should reject it with an appropriate error.

**Validates: Requirements 5.2**

### Property 10: Error Response Equivalence

*For any* invalid input (missing file, invalid file type, file too large, invalid model), the refactored application should return an error response with the same error_type and similar error message as the original implementation.

**Validates: Requirements 5.3**

### Property 11: Environment Variable Override Precedence

*For any* configuration value that supports environment variable override, when the environment variable is set to a valid value, the Config object should use the environment variable value instead of the file value.

**Validates: Requirements 6.1, 6.2**

### Property 12: Environment Variable Fallback

*For any* environment variable set to an invalid value, the application should log a warning and use the default value from the configuration file.

**Validates: Requirements 6.4**

## Error Handling

### Configuration Errors

**Missing Configuration File**:
- Error: `ConfigurationError: Configuration file not found: {path}`
- Action: Application fails to start
- User Guidance: Provide path to valid configuration file or create default

**Invalid YAML Syntax**:
- Error: `ConfigurationError: Invalid YAML syntax in {path}: {details}`
- Action: Application fails to start
- User Guidance: Fix YAML syntax errors

**Missing Required Fields**:
- Error: `ConfigurationError: Missing required configuration: {field_path}`
- Action: Application fails to start
- User Guidance: Add missing fields to configuration

**Invalid Field Values**:
- Error: `ConfigurationError: Invalid value for {field}: {value}. Expected {expected_type}`
- Action: Application fails to start
- User Guidance: Correct the invalid value

### Runtime Errors

**Model Not Found**:
- Error: `Invalid model: {model_id}. Available models: {model_list}`
- HTTP Status: 400
- Error Type: `invalid_model`

**API Connection Errors**:
- Error: `LM Studio server is not running. Please start the server at {base_url}`
- HTTP Status: 500
- Error Type: `connection_error`

**File Processing Errors**:
- Error: `Failed to process file: {details}`
- HTTP Status: 500
- Error Type: `processing_error`

### Error Recovery

**Graceful Degradation**:
- If API server is unavailable at startup, log warning but allow application to start
- Health check endpoint reports server status
- OCR requests fail with clear error messages

**Configuration Validation**:
- Validate all configuration on startup before accepting requests
- Fail fast with clear error messages
- Provide guidance for fixing configuration issues

## Testing Strategy

### Unit Testing

Unit tests will verify specific examples, edge cases, and error conditions:

**Configuration Loading**:
- Test loading valid configuration file
- Test loading configuration with missing required fields
- Test loading configuration with invalid YAML syntax
- Test environment variable overrides for specific variables
- Test invalid environment variable handling

**Model Configuration**:
- Test retrieving existing model configuration
- Test retrieving non-existent model configuration
- Test model configuration with all required fields
- Test model configuration with missing fields

**File Validation**:
- Test allowed file extensions (png, jpg, jpeg, pdf)
- Test disallowed file extensions
- Test file type detection for each supported type
- Test file size validation

**OCR Processing**:
- Test image OCR with valid image
- Test PDF single page OCR
- Test PDF multi-page OCR
- Test OCR with invalid file
- Test OCR with unavailable API server

**Route Handlers**:
- Test /health endpoint returns correct status
- Test /ocr endpoint with valid request
- Test /ocr endpoint with missing file
- Test /ocr endpoint with invalid model
- Test error handler for file too large

### Property-Based Testing

Property tests will verify universal properties across all inputs using a property-based testing library (pytest with Hypothesis for Python):

**Configuration Properties**:
- Property 1: Configuration Loading Completeness (100+ iterations with generated valid configs)
- Property 3: Configuration Validation Rejection (100+ iterations with generated invalid configs)
- Property 7: Configuration Nested Access (100+ iterations with generated nested structures)
- Property 11: Environment Variable Override Precedence (100+ iterations with generated env vars)
- Property 12: Environment Variable Fallback (100+ iterations with generated invalid env vars)

**Model Configuration Properties**:
- Property 4: Dynamic Model Registration (100+ iterations with generated model configs)
- Property 5: Multi-Provider Routing (100+ iterations with generated provider configs)
- Property 6: Invalid Model Error Response (100+ iterations with generated invalid model IDs)

**Backward Compatibility Properties**:
- Property 8: API Endpoint Behavioral Equivalence (100+ iterations with generated OCR requests)
- Property 9: File Type Support Preservation (100+ iterations with generated filenames)
- Property 10: Error Response Equivalence (100+ iterations with generated invalid inputs)

Each property test must:
- Run minimum 100 iterations with randomized inputs
- Include a comment tag: `# Feature: config-refactor, Property N: {property_text}`
- Reference the design document property number
- Use appropriate generators for test data (valid/invalid configs, filenames, requests)

### Integration Testing

Integration tests will verify end-to-end workflows:
- Start application with valid configuration
- Process OCR request through full stack
- Verify configuration changes take effect on restart
- Test multiple models with different providers
- Test environment variable overrides in full application context

### Test Coverage Goals

- Unit test coverage: >90% for all modules
- Property test coverage: All 12 correctness properties implemented
- Integration test coverage: All major workflows (startup, OCR processing, configuration reload)
- Error path coverage: All error types and error handlers tested
