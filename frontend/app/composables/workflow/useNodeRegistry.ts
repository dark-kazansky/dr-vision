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
