# Requirements Document: OCR Web UI

## Introduction

This document specifies the requirements for a web-based user interface that enables users to perform Optical Character Recognition (OCR) on images and PDF files using a locally hosted LightOnOCR-2-1B model via LM Studio. The system will provide a simple interface for file upload, preview, and text extraction display.

## Glossary

- **OCR_System**: The complete web application including UI and backend integration
- **LM_Studio_API**: The local API endpoint (http://localhost:1234) hosting the LightOnOCR-2-1B model
- **User**: A person interacting with the web interface to perform OCR operations
- **Upload_Component**: The UI element that handles file selection and upload
- **Preview_Component**: The UI element that displays the uploaded file before processing
- **Results_Display**: The UI element that shows extracted text from OCR processing
- **Backend_Service**: The existing Python code that interfaces with LM Studio API

## Requirements

### Requirement 1: File Upload

**User Story:** As a user, I want to upload images or PDF files, so that I can extract text from them using OCR.

#### Acceptance Criteria

1. WHEN a user selects a file, THE Upload_Component SHALL accept image files (PNG, JPG, JPEG)
2. WHEN a user selects a file, THE Upload_Component SHALL accept PDF files
3. WHEN a user selects an unsupported file type, THE Upload_Component SHALL reject the file and display an error message
4. WHEN a file is successfully selected, THE OCR_System SHALL store the file for processing
5. THE Upload_Component SHALL provide a clear button or interface element for file selection

### Requirement 2: File Preview

**User Story:** As a user, I want to see a preview of my uploaded file, so that I can verify I selected the correct file before processing.

#### Acceptance Criteria

1. WHEN an image file is uploaded, THE Preview_Component SHALL display the image
2. WHEN a PDF file is uploaded, THE Preview_Component SHALL display the first page of the PDF
3. WHEN no file is uploaded, THE Preview_Component SHALL display a placeholder or empty state
4. WHEN a new file is uploaded, THE Preview_Component SHALL replace the previous preview with the new file preview

### Requirement 3: OCR Processing

**User Story:** As a user, I want to process my uploaded file with OCR, so that I can extract text from it.

#### Acceptance Criteria

1. WHEN a user initiates OCR processing, THE Backend_Service SHALL encode the file in base64 format
2. WHEN the file is encoded, THE Backend_Service SHALL send the encoded data to the LM_Studio_API at http://localhost:1234
3. WHEN sending to the API, THE Backend_Service SHALL use the model ID "lightonocr-2-1b"
4. WHEN the LM_Studio_API returns a response, THE Backend_Service SHALL extract the text content
5. IF the LM_Studio_API is unavailable, THEN THE OCR_System SHALL display an error message indicating the service is not reachable
6. IF the OCR processing fails, THEN THE OCR_System SHALL display an error message with failure details

### Requirement 4: Results Display

**User Story:** As a user, I want to see the extracted text results, so that I can use the OCR output.

#### Acceptance Criteria

1. WHEN OCR processing completes successfully, THE Results_Display SHALL show the extracted text
2. WHEN displaying results, THE Results_Display SHALL preserve the text formatting and line breaks
3. WHEN no OCR processing has occurred, THE Results_Display SHALL show an empty state or placeholder
4. THE Results_Display SHALL provide a way to copy the extracted text to clipboard
5. WHEN a new file is processed, THE Results_Display SHALL replace previous results with new results

### Requirement 5: User Feedback

**User Story:** As a user, I want to know the status of my OCR request, so that I understand what the system is doing.

#### Acceptance Criteria

1. WHEN OCR processing starts, THE OCR_System SHALL display a loading indicator
2. WHEN OCR processing completes, THE OCR_System SHALL hide the loading indicator
3. WHEN an error occurs, THE OCR_System SHALL display a clear error message describing the issue
4. WHEN processing is successful, THE OCR_System SHALL provide visual confirmation of completion

### Requirement 6: Integration with Existing Backend

**User Story:** As a developer, I want the UI to integrate with existing Python backend code, so that I can reuse the current LM Studio API implementation.

#### Acceptance Criteria

1. THE OCR_System SHALL use the existing Python functions for OCR processing
2. THE Backend_Service SHALL maintain the current base64 encoding implementation
3. THE Backend_Service SHALL maintain the current API endpoint configuration (http://localhost:1234)
4. THE Backend_Service SHALL maintain the current model ID ("lightonocr-2-1b")
5. THE OCR_System SHALL provide an HTTP API endpoint that the UI can call to trigger OCR processing

### Requirement 7: Simple and Intuitive Interface

**User Story:** As a user, I want a simple and easy-to-use interface, so that I can perform OCR without confusion.

#### Acceptance Criteria

1. THE OCR_System SHALL present all core functions (upload, preview, process, results) on a single page
2. THE OCR_System SHALL use clear labels and instructions for each UI element
3. THE OCR_System SHALL provide visual hierarchy to guide users through the workflow
4. THE OCR_System SHALL respond to user interactions within 200 milliseconds for UI updates (excluding OCR processing time)
