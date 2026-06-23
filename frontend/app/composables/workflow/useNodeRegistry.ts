/**
 * Node Registry Composable
 * 
 * Extensible registry for workflow node types.
 * Provides node type definitions, categories, and factory methods.
 */

import type { NodeTypeDefinition, NodeCategory } from '~/types/workflow'

const NODE_DEFINITIONS: NodeTypeDefinition[] = [
  // ─── Input Nodes ─────────────────────────────────────────────────────────
  {
    type: 'file-input',
    label: 'File Input',
    description: 'Upload files (images, PDFs) for processing',
    category: 'input',
    icon: '📁',
    color: '#3b82f6',
    inputs: [],
    outputs: [{ id: 'file', label: 'File', type: 'file' }],
    defaultConfig: { acceptedTypes: ['image/*', 'application/pdf'], maxFiles: 10 },
    configSchema: [
      { key: 'maxFiles', label: 'Max Files', type: 'number', default: 10 },
    ],
    executable: true,
  },
  {
    type: 'text-input',
    label: 'Text Input',
    description: 'Provide text content directly',
    category: 'input',
    icon: '📝',
    color: '#3b82f6',
    inputs: [],
    outputs: [{ id: 'text', label: 'Text', type: 'text' }],
    defaultConfig: { content: '' },
    configSchema: [
      { key: 'content', label: 'Content', type: 'textarea', placeholder: 'Enter text...' },
    ],
    executable: true,
  },
  {
    type: 'api-input',
    label: 'API Input',
    description: 'Receive data from external API webhook',
    category: 'input',
    icon: '🔌',
    color: '#3b82f6',
    inputs: [],
    outputs: [{ id: 'data', label: 'Data', type: 'json' }],
    defaultConfig: { endpoint: '', method: 'POST' },
    configSchema: [
      { key: 'endpoint', label: 'Endpoint Path', type: 'text', placeholder: '/webhook/...' },
      { key: 'method', label: 'Method', type: 'select', options: [
        { label: 'POST', value: 'POST' },
        { label: 'GET', value: 'GET' },
      ]},
    ],
    executable: true,
  },

  // ─── Processing Nodes ────────────────────────────────────────────────────
  {
    type: 'ocr',
    label: 'OCR',
    description: 'Extract text from images/PDFs using AI vision models',
    category: 'processing',
    icon: '👁️',
    color: '#8b5cf6',
    inputs: [{ id: 'file', label: 'File', type: 'file' }],
    outputs: [{ id: 'text', label: 'Text', type: 'text' }],
    defaultConfig: { tier: 'Normal', processAllPages: true },
    configSchema: [
      { key: 'tier', label: 'Processing Tier', type: 'select', options: [
        { label: 'Rapid', value: 'Rapid' },
        { label: 'Normal', value: 'Normal' },
        { label: 'Advance', value: 'Advance' },
      ]},
      { key: 'processAllPages', label: 'Process All Pages', type: 'boolean', default: true },
    ],
    executable: true,
  },
  {
    type: 'parser',
    label: 'Document Parser',
    description: 'Parse documents with formatting preservation',
    category: 'processing',
    icon: '📄',
    color: '#8b5cf6',
    inputs: [{ id: 'file', label: 'File', type: 'file' }],
    outputs: [
      { id: 'text', label: 'Parsed Text', type: 'text' },
      { id: 'metadata', label: 'Metadata', type: 'json' },
    ],
    defaultConfig: { tier: 'Normal', parseFormatting: true },
    configSchema: [
      { key: 'tier', label: 'Processing Tier', type: 'select', options: [
        { label: 'Rapid', value: 'Rapid' },
        { label: 'Normal', value: 'Normal' },
        { label: 'Advance', value: 'Advance' },
      ]},
      { key: 'parseFormatting', label: 'Preserve Formatting', type: 'boolean', default: true },
    ],
    executable: true,
  },
  {
    type: 'text-splitter',
    label: 'Text Splitter',
    description: 'Split text into chunks by size or semantic boundaries',
    category: 'processing',
    icon: '✂️',
    color: '#8b5cf6',
    inputs: [{ id: 'text', label: 'Text', type: 'text' }],
    outputs: [{ id: 'chunks', label: 'Chunks', type: 'json' }],
    defaultConfig: { method: 'semantic', chunkSize: 1000, overlap: 200 },
    configSchema: [
      { key: 'method', label: 'Split Method', type: 'select', options: [
        { label: 'Semantic', value: 'semantic' },
        { label: 'Fixed Size', value: 'fixed' },
        { label: 'By Page', value: 'page' },
      ]},
      { key: 'chunkSize', label: 'Chunk Size', type: 'number', default: 1000 },
      { key: 'overlap', label: 'Overlap', type: 'number', default: 200 },
    ],
    executable: true,
  },
  {
    type: 'layout-recognize',
    label: 'Layout Recognize',
    description: 'Detect document layout structure (text, tables, figures, titles, equations)',
    category: 'processing',
    icon: '🔲',
    color: '#8b5cf6',
    inputs: [{ id: 'file', label: 'File', type: 'file' }],
    outputs: [
      { id: 'regions', label: 'Layout Regions', type: 'json' },
      { id: 'file', label: 'File (pass-through)', type: 'file' },
    ],
    defaultConfig: { threshold: 0.2, scaleFactor: 3 },
    configSchema: [
      { key: 'threshold', label: 'Confidence Threshold', type: 'number', default: 0.2 },
      { key: 'scaleFactor', label: 'Scale Factor', type: 'select', options: [
        { label: '1x (Fast)', value: '1' },
        { label: '2x (Balanced)', value: '2' },
        { label: '3x (Quality)', value: '3' },
        { label: '4x (High Quality)', value: '4' },
      ]},
    ],
    executable: true,
  },
  {
    type: 'table-recognize',
    label: 'Table Recognizer',
    description: 'Detect table structure (rows, columns, cells) and extract to CSV/JSON/Markdown',
    category: 'processing',
    icon: '📊',
    color: '#8b5cf6',
    inputs: [{ id: 'file', label: 'File', type: 'file' }],
    outputs: [
      { id: 'tables', label: 'Tables', type: 'json' },
      { id: 'csv', label: 'CSV', type: 'text' },
      { id: 'file', label: 'File (pass-through)', type: 'file' },
    ],
    defaultConfig: { method: 'auto', tier: 'Normal', threshold: 0.3, scaleFactor: 3, outputFormat: 'all', useLayoutDetection: true },
    configSchema: [
      { key: 'method', label: 'Processing Method', type: 'select', options: [
        { label: 'Auto (detect best method)', value: 'auto' },
        { label: 'DeepDoc TSR (scanned/image)', value: 'deepdoc' },
        { label: 'MarkItDown (native XLSX/DOCX/CSV)', value: 'markitdown' },
        { label: 'LLM Extract (AI-powered)', value: 'llm' },
      ]},
      { key: 'tier', label: 'Processing Tier', type: 'select', options: [
        { label: 'Rapid', value: 'Rapid' },
        { label: 'Normal', value: 'Normal' },
        { label: 'Advance', value: 'Advance' },
      ]},
      { key: 'threshold', label: 'Confidence Threshold', type: 'number', default: 0.3 },
      { key: 'scaleFactor', label: 'Scale Factor', type: 'select', options: [
        { label: '1x (Fast)', value: '1' },
        { label: '2x (Balanced)', value: '2' },
        { label: '3x (Quality)', value: '3' },
        { label: '4x (High Quality)', value: '4' },
      ]},
      { key: 'outputFormat', label: 'Output Format', type: 'select', options: [
        { label: 'JSON (Cells)', value: 'json' },
        { label: 'CSV', value: 'csv' },
        { label: 'Markdown', value: 'markdown' },
        { label: 'HTML', value: 'html' },
        { label: 'All Formats', value: 'all' },
      ]},
      { key: 'useLayoutDetection', label: 'Auto-detect Table Regions', type: 'checkbox', default: true },
    ],
    executable: true,
  },
  {
    type: 'document-to-markdown',
    label: 'Document to Markdown',
    description: 'Convert documents (XLSX, DOCX, PDF, HTML, CSV) to structured Markdown preserving tables',
    category: 'processing',
    icon: '📝',
    color: '#8b5cf6',
    inputs: [{ id: 'file', label: 'File', type: 'file' }],
    outputs: [
      { id: 'markdown', label: 'Markdown Text', type: 'text' },
      { id: 'tables', label: 'Extracted Tables', type: 'json' },
    ],
    defaultConfig: {},
    configSchema: [],
    executable: true,
  },
  {
    type: 'ocr-postprocess',
    label: 'OCR Post-Process',
    description: 'Auto-correct OCR errors, normalize text, score word confidence',
    category: 'processing',
    icon: '✏️',
    color: '#8b5cf6',
    inputs: [{ id: 'text', label: 'Text', type: 'text' }],
    outputs: [
      { id: 'text', label: 'Corrected Text', type: 'text' },
      { id: 'confidences', label: 'Word Confidences', type: 'json' },
    ],
    defaultConfig: { language: 'vi', confidenceThreshold: 0.7 },
    configSchema: [
      { key: 'language', label: 'Language', type: 'select', options: [
        { label: 'Vietnamese', value: 'vi' },
        { label: 'English', value: 'en' },
      ]},
      { key: 'confidenceThreshold', label: 'Confidence Threshold', type: 'number', default: 0.7 },
    ],
    executable: true,
  },
  {
    type: 'template-extract',
    label: 'Template Extract',
    description: 'Auto-detect document type and extract fields using matching template',
    category: 'processing',
    icon: '🎯',
    color: '#8b5cf6',
    inputs: [{ id: 'file', label: 'File', type: 'file' }],
    outputs: [
      { id: 'fields', label: 'Extracted Fields', type: 'json' },
      { id: 'template', label: 'Matched Template', type: 'json' },
    ],
    defaultConfig: { templateId: '', autoMatch: true },
    configSchema: [
      { key: 'templateId', label: 'Template ID (leave empty for auto-match)', type: 'text', default: '' },
      { key: 'autoMatch', label: 'Auto-detect Document Type', type: 'checkbox', default: true },
    ],
    executable: true,
  },
  {
    type: 'document-compare',
    label: 'Document Compare',
    description: 'Compare two documents: text diff, similarity score, structural changes',
    category: 'processing',
    icon: '🔀',
    color: '#8b5cf6',
    inputs: [
      { id: 'file_a', label: 'Document A', type: 'file' },
      { id: 'file_b', label: 'Document B', type: 'file' },
    ],
    outputs: [
      { id: 'diff', label: 'Diff Analysis', type: 'json' },
      { id: 'score', label: 'Similarity Score', type: 'json' },
    ],
    defaultConfig: { mode: 'line', ignoreWhitespace: false, ignoreCase: false },
    configSchema: [
      { key: 'mode', label: 'Comparison Mode', type: 'select', options: [
        { label: 'Line-by-line', value: 'line' },
        { label: 'Word-by-word', value: 'word' },
        { label: 'Paragraph', value: 'paragraph' },
      ]},
      { key: 'ignoreWhitespace', label: 'Ignore Whitespace', type: 'checkbox', default: false },
      { key: 'ignoreCase', label: 'Ignore Case', type: 'checkbox', default: false },
    ],
    executable: true,
  },

  // ─── AI Nodes ────────────────────────────────────────────────────────────
  {
    type: 'classifier',
    label: 'Document Classifier',
    description: 'Classify documents into categories using AI',
    category: 'ai',
    icon: '🏷️',
    color: '#f59e0b',
    inputs: [{ id: 'text', label: 'Text', type: 'text' }],
    outputs: [
      { id: 'classification', label: 'Classification', type: 'json' },
      { id: 'confidence', label: 'Confidence', type: 'json' },
    ],
    defaultConfig: { tier: 'Normal', rules: [] },
    configSchema: [
      { key: 'tier', label: 'Processing Tier', type: 'select', options: [
        { label: 'Rapid', value: 'Rapid' },
        { label: 'Normal', value: 'Normal' },
        { label: 'Advance', value: 'Advance' },
      ]},
      { key: 'rules', label: 'Classification Rules', type: 'json', default: [] },
    ],
    executable: true,
  },
  {
    type: 'extractor',
    label: 'Data Extractor',
    description: 'Extract structured data from text using schema',
    category: 'ai',
    icon: '🔍',
    color: '#f59e0b',
    inputs: [{ id: 'text', label: 'Text', type: 'text' }],
    outputs: [{ id: 'data', label: 'Structured Data', type: 'json' }],
    defaultConfig: { tier: 'Normal', target: 'document', schema: { fields: [] } },
    configSchema: [
      { key: 'tier', label: 'Processing Tier', type: 'select', options: [
        { label: 'Rapid', value: 'Rapid' },
        { label: 'Normal', value: 'Normal' },
        { label: 'Advance', value: 'Advance' },
      ]},
      { key: 'target', label: 'Extraction Target', type: 'select', options: [
        { label: 'Document', value: 'document' },
        { label: 'Page', value: 'page' },
        { label: 'Table Row', value: 'table_row' },
      ]},
      { key: 'schema', label: 'Extraction Schema', type: 'json', default: { fields: [] } },
    ],
    executable: true,
  },
  {
    type: 'llm',
    label: 'LLM Prompt',
    description: 'Process text with a custom LLM prompt',
    category: 'ai',
    icon: '🤖',
    color: '#f59e0b',
    inputs: [{ id: 'text', label: 'Input Text', type: 'text' }],
    outputs: [{ id: 'response', label: 'Response', type: 'text' }],
    defaultConfig: { model: 'gemini-3-flash', prompt: '', temperature: 0.7, maxTokens: 2048 },
    configSchema: [
      { key: 'model', label: 'Model', type: 'select', options: [
        { label: 'Gemini 3 Flash', value: 'gemini-3-flash' },
        { label: 'Claude Haiku', value: 'claude-haiku' },
        { label: 'Claude Sonnet', value: 'claude-sonnet' },
        { label: 'Qwen3 Max', value: 'qwen3-max' },
      ]},
      { key: 'prompt', label: 'System Prompt', type: 'textarea', placeholder: 'Instructions for the LLM...' },
      { key: 'temperature', label: 'Temperature', type: 'number', default: 0.7 },
      { key: 'maxTokens', label: 'Max Tokens', type: 'number', default: 2048 },
    ],
    executable: true,
  },
  {
    type: 'summarizer',
    label: 'Summarizer',
    description: 'Generate summaries of text content',
    category: 'ai',
    icon: '📋',
    color: '#f59e0b',
    inputs: [{ id: 'text', label: 'Text', type: 'text' }],
    outputs: [{ id: 'summary', label: 'Summary', type: 'text' }],
    defaultConfig: { style: 'concise', maxLength: 500 },
    configSchema: [
      { key: 'style', label: 'Summary Style', type: 'select', options: [
        { label: 'Concise', value: 'concise' },
        { label: 'Detailed', value: 'detailed' },
        { label: 'Bullet Points', value: 'bullets' },
      ]},
      { key: 'maxLength', label: 'Max Length (words)', type: 'number', default: 500 },
    ],
    executable: true,
  },

  // ─── Logic Nodes ─────────────────────────────────────────────────────────
  {
    type: 'condition',
    label: 'Condition',
    description: 'Branch workflow based on conditions',
    category: 'logic',
    icon: '🔀',
    color: '#10b981',
    inputs: [{ id: 'input', label: 'Input', type: 'any' }],
    outputs: [
      { id: 'true', label: 'True', type: 'any' },
      { id: 'false', label: 'False', type: 'any' },
    ],
    defaultConfig: { field: '', operator: 'equals', value: '' },
    configSchema: [
      { key: 'field', label: 'Field Path', type: 'text', placeholder: 'e.g. classification.type' },
      { key: 'operator', label: 'Operator', type: 'select', options: [
        { label: 'Equals', value: 'equals' },
        { label: 'Not Equals', value: 'not_equals' },
        { label: 'Contains', value: 'contains' },
        { label: 'Greater Than', value: 'gt' },
        { label: 'Less Than', value: 'lt' },
      ]},
      { key: 'value', label: 'Value', type: 'text' },
    ],
    executable: true,
  },
  {
    type: 'merge',
    label: 'Merge',
    description: 'Merge multiple inputs into one output',
    category: 'logic',
    icon: '🔗',
    color: '#10b981',
    inputs: [
      { id: 'input-1', label: 'Input 1', type: 'any' },
      { id: 'input-2', label: 'Input 2', type: 'any' },
    ],
    outputs: [{ id: 'merged', label: 'Merged', type: 'json' }],
    defaultConfig: { strategy: 'combine' },
    configSchema: [
      { key: 'strategy', label: 'Merge Strategy', type: 'select', options: [
        { label: 'Combine All', value: 'combine' },
        { label: 'Wait for All', value: 'wait_all' },
        { label: 'First Available', value: 'first' },
      ]},
    ],
    executable: true,
  },
  {
    type: 'loop',
    label: 'Loop',
    description: 'Iterate over array items',
    category: 'logic',
    icon: '🔄',
    color: '#10b981',
    inputs: [{ id: 'items', label: 'Items', type: 'json' }],
    outputs: [
      { id: 'item', label: 'Current Item', type: 'any' },
      { id: 'done', label: 'All Done', type: 'json' },
    ],
    defaultConfig: { maxIterations: 100 },
    configSchema: [
      { key: 'maxIterations', label: 'Max Iterations', type: 'number', default: 100 },
    ],
    executable: true,
  },

  // ─── Output Nodes ────────────────────────────────────────────────────────
  {
    type: 'json-output',
    label: 'JSON Output',
    description: 'Export results as JSON',
    category: 'output',
    icon: '📤',
    color: '#ef4444',
    inputs: [{ id: 'data', label: 'Data', type: 'any' }],
    outputs: [],
    defaultConfig: { format: 'pretty' },
    configSchema: [
      { key: 'format', label: 'Format', type: 'select', options: [
        { label: 'Pretty', value: 'pretty' },
        { label: 'Compact', value: 'compact' },
      ]},
    ],
    executable: true,
  },
  {
    type: 'webhook-output',
    label: 'Webhook Output',
    description: 'Send results to an external webhook',
    category: 'output',
    icon: '🌐',
    color: '#ef4444',
    inputs: [{ id: 'data', label: 'Data', type: 'any' }],
    outputs: [],
    defaultConfig: { url: '', method: 'POST', headers: {} },
    configSchema: [
      { key: 'url', label: 'Webhook URL', type: 'text', placeholder: 'https://...' },
      { key: 'method', label: 'Method', type: 'select', options: [
        { label: 'POST', value: 'POST' },
        { label: 'PUT', value: 'PUT' },
      ]},
    ],
    executable: true,
  },
  {
    type: 'file-output',
    label: 'File Output',
    description: 'Save results to a file (CSV, JSON, DOCX)',
    category: 'output',
    icon: '💾',
    color: '#ef4444',
    inputs: [{ id: 'data', label: 'Data', type: 'any' }],
    outputs: [],
    defaultConfig: { filename: 'output', format: 'json' },
    configSchema: [
      { key: 'filename', label: 'Filename', type: 'text', default: 'output' },
      { key: 'format', label: 'Format', type: 'select', options: [
        { label: 'JSON', value: 'json' },
        { label: 'CSV', value: 'csv' },
        { label: 'Markdown', value: 'md' },
      ]},
    ],
    executable: true,
  },
]

const CATEGORY_META: Record<NodeCategory, { label: string; icon: string; color: string }> = {
  input: { label: 'Input', icon: '📥', color: '#3b82f6' },
  processing: { label: 'Processing', icon: '⚙️', color: '#8b5cf6' },
  ai: { label: 'AI / ML', icon: '🧠', color: '#f59e0b' },
  logic: { label: 'Logic', icon: '🔀', color: '#10b981' },
  output: { label: 'Output', icon: '📤', color: '#ef4444' },
}

export function useNodeRegistry() {
  const registry = ref<NodeTypeDefinition[]>([...NODE_DEFINITIONS])

  /** Get all registered node types */
  const getNodeTypes = () => registry.value

  /** Get node types by category */
  const getNodesByCategory = (category: NodeCategory) =>
    registry.value.filter(n => n.category === category)

  /** Get all categories with their metadata */
  const getCategories = () => CATEGORY_META

  /** Get a specific node type definition */
  const getNodeType = (type: string): NodeTypeDefinition | undefined =>
    registry.value.find(n => n.type === type)

  /** Register a new node type (extensibility) */
  const registerNodeType = (definition: NodeTypeDefinition) => {
    const existing = registry.value.findIndex(n => n.type === definition.type)
    if (existing >= 0) {
      registry.value[existing] = definition
    } else {
      registry.value.push(definition)
    }
  }

  /** Unregister a node type */
  const unregisterNodeType = (type: string) => {
    registry.value = registry.value.filter(n => n.type !== type)
  }

  /** Search node types by query */
  const searchNodes = (query: string): NodeTypeDefinition[] => {
    const q = query.toLowerCase()
    return registry.value.filter(
      n => n.label.toLowerCase().includes(q) ||
           n.description.toLowerCase().includes(q) ||
           n.type.toLowerCase().includes(q)
    )
  }

  return {
    registry: readonly(registry),
    getNodeTypes,
    getNodesByCategory,
    getCategories,
    getNodeType,
    registerNodeType,
    unregisterNodeType,
    searchNodes,
  }
}
