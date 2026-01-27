# Implementation Plan: OCR Web UI

## Overview

This implementation plan breaks down the OCR Web UI feature into discrete coding tasks. The approach follows a bottom-up strategy: first setting up the backend infrastructure and integrating with existing OCR code, then building the frontend interface, and finally connecting them together. Each task builds incrementally on previous work.

## Tasks

- [x] 1. Set up Flask backend structure and integrate existing OCR code
  - Create Flask application with basic configuration
  - Set up file upload handling with size limits
  - Create wrapper functions around existing LM Studio OCR code
  - Configure CORS for local development
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 2. Implement backend OCR endpoint
  - [x] 2.1 Create POST /ocr endpoint with file upload handling
    - Accept multipart/form-data requests
    - Validate file types (png, jpg, jpeg, pdf)
    - Return JSON responses with success/error structure
    - _Requirements: 1.1, 1.2, 1.3, 3.2, 3.3, 6.5_
  
  - [ ]* 2.2 Write property test for file type validation
    - **Property 1: Valid File Type Acceptance**
    - **Property 2: Invalid File Type Rejection**
    - **Validates: Requirements 1.1, 1.2, 1.3**
  
  - [x] 2.3 Implement base64 encoding and LM Studio API communication
    - Encode uploaded files to base64
    - Send requests to http://localhost:1234 with model ID "lightonocr-2-1b"
    - Parse API responses and extract text
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  
  - [ ]* 2.4 Write property test for base64 encoding
    - **Property 6: Base64 Encoding Validity**
    - **Validates: Requirements 3.1**
  
  - [ ]* 2.5 Write unit tests for API endpoint
    - Test correct endpoint URL (http://localhost:1234)
    - Test correct model ID ("lightonocr-2-1b")
    - Test LM Studio unavailable scenario
    - _Requirements: 3.2, 3.3, 3.5_

- [ ] 3. Implement backend error handling
  - [x] 3.1 Add error handling for connection failures
    - Catch connection errors to LM Studio
    - Return appropriate error responses with error_type
    - _Requirements: 3.5_
  
  - [x] 3.2 Add error handling for processing failures
    - Catch OCR processing exceptions
    - Return descriptive error messages
    - _Requirements: 3.6_
  
  - [ ]* 3.3 Write property test for error handling
    - **Property 8: Error Message Display**
    - **Validates: Requirements 3.6, 5.3**

- [x] 4. Create frontend HTML structure
  - Create single-page HTML layout
  - Add file upload input with accept attribute
  - Add preview area for images/PDFs
  - Add process button
  - Add results display area with copy button
  - Add status/error message area
  - _Requirements: 1.5, 7.1, 7.2_

- [ ] 5. Implement frontend file upload and validation
  - [x] 5.1 Create JavaScript file upload handler
    - Handle file selection events
    - Validate file types client-side
    - Update file state on valid selection
    - Display error for invalid files
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  
  - [ ]* 5.2 Write property test for file state management
    - **Property 3: File State Persistence**
    - **Validates: Requirements 1.4**

- [ ] 6. Implement frontend preview functionality
  - [x] 6.1 Create preview display logic for images
    - Generate data URLs for image files
    - Display images in preview area
    - _Requirements: 2.1_
  
  - [x] 6.2 Create preview display logic for PDFs
    - Integrate PDF.js library
    - Render first page of PDF files
    - _Requirements: 2.2_
  
  - [x] 6.3 Implement preview state management
    - Show placeholder when no file uploaded
    - Replace preview when new file uploaded
    - _Requirements: 2.3, 2.4_
  
  - [ ]* 6.4 Write property tests for preview functionality
    - **Property 4: Preview Display for Uploaded Files**
    - **Property 5: Preview State Transitions**
    - **Validates: Requirements 2.1, 2.2, 2.4**
  
  - [ ]* 6.5 Write unit test for empty state
    - Test placeholder display when no file uploaded
    - _Requirements: 2.3_

- [x] 7. Checkpoint - Ensure backend and frontend basics work
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement OCR processing and API communication
  - [x] 8.1 Create fetch API call to POST /ocr endpoint
    - Send file as multipart/form-data
    - Handle response parsing
    - Update UI state based on response
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  
  - [x] 8.2 Implement loading state management
    - Show loading indicator when processing starts
    - Hide loading indicator when processing completes
    - _Requirements: 5.1, 5.2_
  
  - [ ]* 8.3 Write property test for loading state lifecycle
    - **Property 12: Loading State Lifecycle**
    - **Validates: Requirements 5.1, 5.2**

- [ ] 9. Implement results display
  - [x] 9.1 Create results display component
    - Display extracted text with preserved formatting
    - Show empty state when no results
    - Replace results when new processing completes
    - _Requirements: 4.1, 4.2, 4.3, 4.5_
  
  - [x] 9.2 Implement copy to clipboard functionality
    - Add copy button click handler
    - Use Clipboard API to copy text
    - Provide visual feedback on copy
    - _Requirements: 4.4_
  
  - [ ]* 9.3 Write property tests for results display
    - **Property 9: Results Display State Management**
    - **Property 10: Text Formatting Preservation**
    - **Property 11: Copy Functionality**
    - **Validates: Requirements 4.1, 4.2, 4.4, 4.5**
  
  - [ ]* 9.4 Write unit test for empty results state
    - Test placeholder display when no processing occurred
    - _Requirements: 4.3_

- [ ] 10. Implement error and success feedback
  - [x] 10.1 Create error message display logic
    - Show error messages for all error types
    - Clear errors on new operations
    - _Requirements: 3.5, 3.6, 5.3_
  
  - [x] 10.2 Create success feedback logic
    - Show success state on completion
    - Provide visual confirmation
    - _Requirements: 5.4_
  
  - [ ]* 10.3 Write property tests for feedback
    - **Property 13: Success Feedback**
    - **Validates: Requirements 5.4**

- [ ] 11. Add CSS styling and UI polish
  - [x] 11.1 Create CSS for layout and visual hierarchy
    - Style all components with clear visual hierarchy
    - Ensure responsive design
    - Add loading spinner animation
    - _Requirements: 7.3_
  
  - [x] 11.2 Optimize UI responsiveness
    - Ensure UI updates happen within 200ms
    - Optimize event handlers
    - _Requirements: 7.4_
  
  - [ ]* 11.3 Write property test for UI response time
    - **Property 14: UI Response Time**
    - **Validates: Requirements 7.4**

- [ ] 12. Integration and final testing
  - [x] 12.1 Wire all components together
    - Ensure file upload → preview → process → results flow works
    - Test error scenarios end-to-end
    - Verify all state transitions
    - _Requirements: All_
  
  - [ ]* 12.2 Write integration tests
    - Test complete user workflows
    - Test error recovery scenarios
    - _Requirements: All_

- [x] 13. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties with minimum 100 iterations
- Unit tests validate specific examples and edge cases
- The implementation follows an incremental approach: backend first, then frontend, then integration
- PDF.js library will be used for PDF preview functionality
- Hypothesis (Python) and fast-check (JavaScript) are recommended for property-based testing
