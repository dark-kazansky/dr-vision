/**
 * Extraction Configuration Types
 * 
 * Type definitions for the extraction configuration feature that enables
 * structured data extraction from OCR text according to user-defined schemas.
 */

/**
 * Field type enumeration for schema fields
 */
export type FieldType = 'string' | 'number' | 'boolean' | 'date' | 'object'

/**
 * Extraction target enumeration
 * Defines the scope at which extraction is performed
 */
export type ExtractionTarget = 'document' | 'page' | 'table_row'

/**
 * Schema field definition
 * Represents a single field in the extraction schema with support for nested objects
 */
export interface SchemaField {
  /** Field name (must be unique within schema) */
  name: string
  /** Field data type */
  type: FieldType
  /** Optional field description */
  description: string
  /** Whether the field is required */
  required: boolean
  /** Hierarchy level (0 = root, 1+ = nested) */
  level?: number
  /** Whether this field has child fields */
  hasChildren?: boolean
  /** Whether children are expanded (for UI) */
  expanded?: boolean
  /** Child fields (for nested objects) */
  properties?: SchemaField[]
}

/**
 * Extraction configuration
 * Contains the extraction target and schema definition
 */
export interface ExtractionConfig {
  /** Whether extraction is enabled */
  enabled: boolean
  /** Extraction target scope */
  target: ExtractionTarget
  /** Extraction schema (list of fields) */
  schema: SchemaField[]
}

/**
 * Enhanced OCR result with extraction support
 * Extends the base OCR result to include structured data
 */
export interface OCRResult {
  /** Whether the OCR operation was successful */
  success: boolean
  /** Raw OCR text (when extraction is disabled) */
  text?: string
  /** Structured data (single object or array based on target) */
  structured_data?: any | any[]
  /** Extraction configuration used (if any) */
  extraction_config?: ExtractionConfig
  /** Field-level extraction errors (field name -> error message) */
  field_errors?: Record<string, string>
  /** Error message (if operation failed) */
  error?: string
  /** Error type classification */
  error_type?: string
  /** Number of pages processed */
  pages?: number
  /** Original filename */
  filename?: string
  /** Model used for OCR */
  model?: string
}
