# Implementation Plan: Extraction Configuration Feature

## Overview

This implementation plan reflects the current state of the extraction configuration feature implementation. Many core components have been built, including frontend components (ExtractionTargetSelector, SchemaBuilder), backend models, extraction processor, and schema generation engine. The remaining work focuses on completing integration, fixing bugs, adding comprehensive testing, and polishing the user experience.

## Current Implementation Status

**Completed:**
- Frontend data models and types
- ExtractionTargetSelector component
- SchemaBuilder component (Visual and Code views, bulk operations, Auto-Generate UI)
- Backend data models (SchemaField, ExtractionConfig, etc.)
- ExtractionProcessor for structured data extraction via Poe API
- SchemaGenerationEngine for auto-generating schemas
- Backend /ocr endpoint enhanced with extraction parameters
- Backend /generate-schema endpoint
- ConfigPanel integration with extraction components
- Result display with Visual/Code toggle

**In Progress:**
- Full end-to-end integration testing
- Property-based testing
- Bug fixes and edge case handling
- UI/UX polish

## Tasks

- [x] 1. Complete frontend-backend integration for schema generation
  - [x] 1.1 Fix handleGenerateSchema in SchemaBuilder
    - Verify /generate-schema endpoint is being called correctly
    - Handle file upload with prompt (if file is provided)
    - Properly handle loading states during generation
    - Display clear error messages on failure
    - Populate schema table with generated fields on success
    - Close auto-generate view and transition to table view on success
    - _Requirements: 10.7, 10.9, 10.10_
  
  - [ ]* 1.2 Write integration tests for auto-generate flow
    - Test complete flow: click button → enter prompt → generate → populate schema
    - Test error handling and retry
    - Test file upload with prompt
    - Test empty prompt validation
    - _Requirements: 10.7, 10.9, 10.10_

- [x] 2. Fix and test extraction processing workflow
  - [x] 2.1 Verify extraction processor integration in routes.py
    - Ensure ExtractionProcessor is properly instantiated
    - Verify extraction is called when extraction_enabled=true
    - Test document-level extraction returns single object
    - Test page-level extraction returns array of objects
    - Handle extraction errors gracefully
    - _Requirements: 6.2, 6.3, 6.4, 6.7_
  
  - [x] 2.2 Add table row extraction support
    - Implement table detection logic in ExtractionProcessor
    - Extract data from each detected table row
    - Return array of structured results
    - Handle documents with no tables gracefully
    - _Requirements: 6.4_
  
  - [ ]* 2.3 Write property test for extraction target result structure
    - **Property 1: Extraction target determines result structure**
    - **Validates: Requirements 1.2, 1.3, 1.4, 6.2, 6.3, 6.4**
  
  - [ ]* 2.4 Write integration tests for extraction workflow
    - Test document extraction with sample invoice
    - Test page extraction with multi-page PDF
    - Test table row extraction with table document
    - Test extraction with missing required fields
    - Test extraction with type conversion errors
    - _Requirements: 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

- [x] 3. Enhance result display and formatting
  - [x] 3.1 Improve visual mode formatting
    - Verify color-coding for different value types (boolean: purple, number: green, null: gray)
    - Test nested object indentation (1.5rem per level)
    - Test array item numbering and formatting
    - Ensure proper separation between multiple result items
    - Add item numbering for page/table row results (Item 1, Item 2, etc.)
    - _Requirements: 9.4, 9.5, 9.6, 9.7, 9.8_
  
  - [x] 3.2 Improve code mode formatting
    - Verify JSON syntax highlighting
    - Ensure dark theme styling (#1f2937 background, #e5e7eb text)
    - Test proper indentation (2 spaces)
    - Add scrolling for long results
    - _Requirements: 9.9, 9.10_
  
  - [x] 3.3 Add error highlighting in results
    - Highlight fields with extraction errors in visual mode
    - Display error messages for failed fields
    - Show type conversion errors clearly
    - _Requirements: 9.11_
  
  - [ ]* 3.4 Write property tests for result display
    - **Property 26: Visual mode displays formatted HTML**
    - **Property 27: Visual mode color-codes values by type**
    - **Property 28: Visual mode shows nested object hierarchy**
    - **Property 29: Visual mode formats arrays with numbering**
    - **Property 30: Document target displays single result in Visual mode**
    - **Property 31: Page/Row targets display multiple items in Visual mode**
    - **Property 32: Code mode displays valid JSON**
    - **Validates: Requirements 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9**
  
  - [ ]* 3.5 Write unit tests for result display
    - Test toggle switches between Visual and Code modes
    - Test Visual mode displays HTML with correct structure
    - Test Code mode displays JSON with correct formatting
    - Test color-coding for each value type
    - Test nested object indentation levels
    - Test array item numbering
    - Test single vs multiple result display
    - Test error highlighting
    - _Requirements: 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10, 9.11_

- [x] 4. Add comprehensive validation and error handling
  - [x] 4.1 Enhance frontend validation
    - Validate schema field names are unique (show inline errors)
    - Validate field names are non-empty (show inline errors)
    - Validate JSON in code view (show error banner)
    - Disable process button when validation errors exist
    - Show clear validation messages
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_
  
  - [x] 4.2 Enhance backend error handling
    - Return 400 for invalid extraction config with details
    - Return 500 for extraction processing errors with details
    - Return 504 for LLM timeout errors
    - Include partial results when possible
    - Handle type conversion errors gracefully
    - _Requirements: 6.6, 7.5_
  
  - [ ]* 4.3 Write property tests for validation
    - **Property 3: Schema field name uniqueness validation**
    - **Property 6: Invalid JSON in code view prevents synchronization**
    - **Property 9: Config validation gates processing**
    - **Validates: Requirements 2.3, 3.6, 5.4, 8.1, 8.2, 8.4, 8.5**
  
  - [ ]* 4.4 Write unit tests for error handling
    - Test duplicate field name validation
    - Test empty field name validation
    - Test invalid JSON validation
    - Test process button disabled with errors
    - Test backend error responses
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 5. Implement property-based tests for core properties
  - [ ]* 5.1 Write property test for state synchronization
    - **Property 2: Extraction config state synchronization**
    - **Validates: Requirements 1.6, 2.7, 5.2**
  
  - [ ]* 5.2 Write property test for schema operations
    - **Property 4: Schema field list operations preserve integrity**
    - **Validates: Requirements 2.2, 2.5**
  
  - [ ]* 5.3 Write property test for view round-trip
    - **Property 5: Visual and code view round-trip consistency**
    - **Validates: Requirements 3.4, 3.5**
  
  - [ ]* 5.4 Write property test for bulk operations
    - **Property 7: Bulk operations apply to all fields**
    - **Validates: Requirements 4.2, 4.3**
  
  - [ ]* 5.5 Write property test for extraction config in requests
    - **Property 8: Extraction config included in OCR requests**
    - **Validates: Requirements 5.3**
  
  - [ ]* 5.6 Write property test for state persistence
    - **Property 10: State persistence across re-renders**
    - **Validates: Requirements 5.5**
  
  - [ ]* 5.7 Write property test for backend config parsing
    - **Property 11: Backend parses extraction config correctly**
    - **Validates: Requirements 6.1**
  
  - [ ]* 5.8 Write property test for schema fields in results
    - **Property 12: All schema fields present in extraction result**
    - **Validates: Requirements 6.5**
  
  - [ ]* 5.9 Write property test for required field errors
    - **Property 13: Required field extraction errors are indicated**
    - **Validates: Requirements 6.6**
  
  - [ ]* 5.10 Write property test for result schema conformance
    - **Property 14: Extraction result matches schema structure**
    - **Validates: Requirements 6.7**
  
  - [ ]* 5.11 Write property test for field type conversion
    - **Property 15: Field type conversion correctness**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6**
  
  - [ ]* 5.12 Write property test for result display format
    - **Property 16: Result display format matches extraction target**
    - **Validates: Requirements 9.2, 9.3**
  
  - [ ]* 5.13 Write property test for result information completeness
    - **Property 17: Result display includes all required information**
    - **Validates: Requirements 9.4**
  
  - [ ]* 5.14 Write property test for error highlighting
    - **Property 18: Extraction errors are visually highlighted**
    - **Validates: Requirements 9.11**
  
  - [ ]* 5.15 Write property test for auto-generate button display
    - **Property 19: Auto-generate button displays in empty state**
    - **Validates: Requirements 10.1**
  
  - [ ]* 5.16 Write property test for auto-generate view display
    - **Property 20: Auto-generate view displays on button click**
    - **Validates: Requirements 10.2, 10.3, 10.4, 10.5**
  
  - [ ]* 5.17 Write property test for back button behavior
    - **Property 21: Back button returns to empty state**
    - **Validates: Requirements 10.6**
  
  - [ ]* 5.18 Write property test for generate button state
    - **Property 22: Generate button requires non-empty prompt**
    - **Validates: Requirements 10.8**
  
  - [ ]* 5.19 Write property test for schema generation validity
    - **Property 23: Schema generation produces valid schema**
    - **Validates: Requirements 10.7, 10.9**
  
  - [ ]* 5.20 Write property test for footer button styling
    - **Property 24: ConfigPanel footer button styling**
    - **Validates: Requirements 11.1, 11.2, 11.4, 11.5**
  
  - [ ]* 5.21 Write property test for individual tooltips
    - **Property 25: Individual extraction target tooltips**
    - **Validates: Requirements 1.5**

- [ ] 6. Add comprehensive unit tests for components
  - [ ]* 6.1 Write unit tests for ExtractionTargetSelector
    - Test all three radio options render
    - Test tooltip display on hover for each option
    - Test v-model updates on selection
    - Test no help icon on main label
    - Test disabled state
    - _Requirements: 1.1, 1.5, 1.6_
  
  - [ ]* 6.2 Write unit tests for SchemaBuilder visual view
    - Test empty state shows Auto Generate and Create Manually buttons
    - Test table renders with correct columns
    - Test add field increases row count
    - Test remove field decreases row count
    - Test field type dropdown has all options (string, number, boolean, date)
    - Test required checkbox toggles asterisk
    - Test validation error messages display
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 10.1_
  
  - [ ]* 6.3 Write unit tests for SchemaBuilder code view
    - Test toggle switches between views
    - Test JSON displays correctly in code view
    - Test visual table displays in visual view
    - Test invalid JSON shows error
    - Test view synchronization
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_
  
  - [ ]* 6.4 Write unit tests for SchemaBuilder bulk operations
    - Test bulk actions menu appears with multiple fields
    - Test mark all required sets all fields to required
    - Test mark all optional sets all fields to optional
    - Test both views reflect bulk changes
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  
  - [ ]* 6.5 Write unit tests for Auto-Generate UI
    - Test empty state shows both buttons
    - Test clicking Auto Generate shows the view
    - Test Back button returns to empty state
    - Test Generate button disabled with empty prompt
    - Test Generate button enabled with non-empty prompt
    - Test file upload hint displays
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.8_
  
  - [ ]* 6.6 Write unit tests for enhanced ConfigPanel
    - Test extraction UI shows when enabled
    - Test extraction UI hides when disabled
    - Test process button disabled with invalid config
    - Test process button enabled with valid config
    - Test emit includes extraction config
    - Test cancel button displays during processing
    - Test footer button styling (orange for process, red border for cancel)
    - _Requirements: 5.3, 5.4, 8.4, 8.5, 11.1, 11.2, 11.4, 11.5_
  
  - [ ]* 6.7 Write unit tests for panel structure
    - Test panel tabs render outside ConfigPanel
    - Test Build and Result tabs have correct icons
    - Test activeTab prop is accepted by ConfigPanel
    - Test config-panel has no padding
    - Test panel-content has 1rem padding
    - Test Build tab displays correct sections
    - Test Result tab displays toggle and results
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.7, 12.8_

- [ ] 7. Backend unit tests and integration tests
  - [ ]* 7.1 Write unit tests for ExtractionProcessor
    - Test prompt building with various schemas
    - Test Poe API response parsing
    - Test JSON extraction from markdown code blocks
    - Test error handling for API failures
    - Test error handling for invalid responses
    - _Requirements: 6.5, 6.6, 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [ ]* 7.2 Write unit tests for SchemaGenerationEngine
    - Test prompt building with various inputs
    - Test schema parsing from LLM response
    - Test error handling for invalid responses
    - Test field validation during parsing
    - _Requirements: 10.7, 10.9_
  
  - [ ]* 7.3 Write unit tests for extraction models
    - Test SchemaField validation (non-empty name, valid characters)
    - Test ExtractionConfig validation (unique field names)
    - Test model serialization/deserialization
    - _Requirements: 6.1_
  
  - [ ]* 7.4 Write integration tests for /ocr endpoint with extraction
    - Test endpoint accepts extraction parameters
    - Test endpoint returns structured data
    - Test endpoint handles invalid extraction config
    - Test endpoint handles extraction errors
    - Test document-level extraction
    - Test page-level extraction
    - _Requirements: 6.1, 6.2, 6.3, 6.7_
  
  - [ ]* 7.5 Write integration tests for /generate-schema endpoint
    - Test endpoint with valid prompts
    - Test endpoint with file uploads
    - Test endpoint with prompt + file
    - Test error handling for invalid requests
    - Test error handling for API failures
    - _Requirements: 10.7, 10.9_

- [x] 8. End-to-end integration and polish
  - [x] 8.1 Test complete extraction workflow
    - Test: Configure schema → Upload document → Process → View results in Visual mode
    - Test: Configure schema → Upload document → Process → View results in Code mode
    - Test: Switch between Visual and Code modes
    - Test: Document-level extraction with sample invoice
    - Test: Page-level extraction with multi-page PDF
    - Test: Auto-generate schema → Process document
    - _Requirements: All requirements_
  
  - [x] 8.2 Fix any bugs discovered during testing
    - Address edge cases
    - Fix UI/UX issues
    - Improve error messages
    - Optimize performance
  
  - [x] 8.3 Polish UI/UX
    - Ensure consistent styling across all components
    - Verify tooltips are helpful and accurate
    - Test responsive design on different screen sizes
    - Ensure loading states are clear
    - Verify error messages are actionable
    - _Requirements: 8.6, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_
  
  - [ ]* 8.4 Write end-to-end integration tests
    - Test complete workflow: configure → upload → process → display
    - Test error recovery workflow
    - Test view switching workflow
    - Test auto-generate workflow
    - _Requirements: All requirements_

- [x] 9. Final checkpoint - Ensure all tests pass
  - Run full test suite (unit + property + integration)
  - Verify all 32 correctness properties are tested
  - Ensure minimum 100 iterations for property tests
  - Fix any failing tests
  - Verify all requirements are covered
  - Ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties with randomized inputs (minimum 100 iterations)
- Unit tests validate specific examples, edge cases, and UI interactions
- Integration tests validate end-to-end workflows
- Frontend uses TypeScript/Vue 3/Nuxt 3 with Tailwind CSS
- Backend uses Python/FastAPI with Pydantic models
- Property testing uses fast-check (frontend) and Hypothesis (backend)
- Each property test must include tags: `Feature: extraction-configuration, Property {N}: {description}`
- The spec includes 32 correctness properties covering all requirements
- Current implementation uses Poe API (assistant, qwen3-max, gemini-3-pro) for extraction and schema generation
- POE_API_KEY environment variable must be set for extraction features to work

## Implementation Status Summary

**Core Components (Completed):**
- ✅ Frontend data models and types
- ✅ ExtractionTargetSelector component
- ✅ SchemaBuilder component (Visual/Code views, bulk operations, Auto-Generate UI)
- ✅ Backend data models (SchemaField, ExtractionConfig, ExtractionResult, etc.)
- ✅ ExtractionProcessor for structured data extraction
- ✅ SchemaGenerationEngine for auto-generating schemas
- ✅ Backend /ocr endpoint enhanced with extraction parameters
- ✅ Backend /generate-schema endpoint
- ✅ ConfigPanel integration with extraction components
- ✅ Result display with Visual/Code toggle

**Remaining Work:**
- ⚠️ Complete frontend-backend integration for schema generation
- ⚠️ Fix and test extraction processing workflow (especially table row extraction)
- ⚠️ Enhance result display formatting and error highlighting
- ⚠️ Add comprehensive validation and error handling
- ⚠️ Implement property-based tests (32 properties)
- ⚠️ Add comprehensive unit tests for all components
- ⚠️ Add backend unit and integration tests
- ⚠️ End-to-end integration testing and polish
