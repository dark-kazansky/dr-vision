// Chunk categories for document splitting

export interface ChunkCategory {
  name: string
  description: string
}

export interface ChunkCategoryGroup {
  name: string
  categories: ChunkCategory[]
}

// All chunk categories for document splitting
export const chunkCategories: ChunkCategory[] = [
  // Top 5 - Most common document sections
  { name: 'executive summary', description: 'High-level overview summarizing key findings, conclusions, and recommendations' },
  { name: 'introduction', description: 'Opening section providing background, context, and purpose of the document' },
  { name: 'conclusion', description: 'Final section summarizing outcomes, implications, and key takeaways' },
  { name: 'appendix', description: 'Supplementary materials including data tables, charts, and supporting documents' },
  { name: 'table of contents', description: 'Document structure and page navigation' },
  
  // Reports & Analysis sections
  { name: 'abstract', description: 'Brief summary of the entire document' },
  { name: 'methodology', description: 'Detailed explanation of research methods and analytical approaches' },
  { name: 'findings', description: 'Presentation of key discoveries and results' },
  { name: 'recommendations', description: 'Suggested actions and next steps' },
  { name: 'literature review', description: 'Review of existing research and publications' },
  
  // Legal & Business sections
  { name: 'definitions', description: 'Legal terms and their meanings' },
  { name: 'terms and conditions', description: 'Agreement terms and conditions' },
  { name: 'signatures', description: 'Signature pages and authorization sections' },
  { name: 'exhibits', description: 'Supporting documents and attachments' },
  { name: 'cover page', description: 'Title, author, and document identification' },
  
  // Financial & Technical sections
  { name: 'financial statements', description: 'Financial data and accounting information' },
  { name: 'specifications', description: 'Technical specifications and requirements' },
  { name: 'diagrams', description: 'Technical diagrams and illustrations' },
  { name: 'instructions', description: 'Step-by-step instructions and procedures' },
  { name: 'references', description: 'Citations and bibliography of sources' },
  
  // Additional common sections
  { name: 'acknowledgments', description: 'Recognition of contributors and supporters' },
  { name: 'glossary', description: 'Definitions of specialized terms' },
  { name: 'index', description: 'Alphabetical listing of topics and page numbers' },
  { name: 'bibliography', description: 'List of sources and references' },
  { name: 'notes', description: 'Additional explanatory information' },
  { name: 'summary', description: 'Brief overview of main points' },
  { name: 'discussion', description: 'Analysis and interpretation of results' },
  { name: 'background', description: 'Historical context and relevant information' },
  { name: 'objectives', description: 'Goals and intended outcomes' },
  { name: 'scope', description: 'Boundaries and limitations of the document' }
]

// Grouped categories for dropdown organization
export const chunkCategoryGroups: ChunkCategoryGroup[] = [
  {
    name: 'Reports & Analysis',
    categories: [
      { name: 'abstract', description: 'Brief summary of the entire document' },
      { name: 'methodology', description: 'Detailed explanation of research methods and analytical approaches' },
      { name: 'findings', description: 'Presentation of key discoveries and results' },
      { name: 'recommendations', description: 'Suggested actions and next steps' },
      { name: 'literature review', description: 'Review of existing research and publications' },
      { name: 'discussion', description: 'Analysis and interpretation of results' },
      { name: 'summary', description: 'Brief overview of main points' }
    ]
  },
  {
    name: 'Legal Documents',
    categories: [
      { name: 'definitions', description: 'Legal terms and their meanings' },
      { name: 'terms and conditions', description: 'Agreement terms and conditions' },
      { name: 'signatures', description: 'Signature pages and authorization sections' },
      { name: 'exhibits', description: 'Supporting documents and attachments' }
    ]
  },
  {
    name: 'Business Documents',
    categories: [
      { name: 'cover page', description: 'Title, author, and document identification' },
      { name: 'financial statements', description: 'Financial data and accounting information' },
      { name: 'background', description: 'Historical context and relevant information' },
      { name: 'objectives', description: 'Goals and intended outcomes' },
      { name: 'scope', description: 'Boundaries and limitations of the document' }
    ]
  },
  {
    name: 'Academic & Research',
    categories: [
      { name: 'references', description: 'Citations and bibliography of sources' },
      { name: 'acknowledgments', description: 'Recognition of contributors and supporters' },
      { name: 'glossary', description: 'Definitions of specialized terms' },
      { name: 'index', description: 'Alphabetical listing of topics and page numbers' },
      { name: 'bibliography', description: 'List of sources and references' },
      { name: 'notes', description: 'Additional explanatory information' }
    ]
  },
  {
    name: 'Technical Documents',
    categories: [
      { name: 'specifications', description: 'Technical specifications and requirements' },
      { name: 'diagrams', description: 'Technical diagrams and illustrations' },
      { name: 'instructions', description: 'Step-by-step instructions and procedures' }
    ]
  }
]

// Get top N categories for quick-add buttons
export function getTopChunkCategories(count: number = 5): ChunkCategory[] {
  return chunkCategories.slice(0, count)
}

// Get remaining categories grouped for dropdown (excluding top N)
export function getRemainingChunkCategoryGroups(topCount: number = 5): ChunkCategoryGroup[] {
  const topCategories = chunkCategories.slice(0, topCount)
  const topCategoryNames = new Set(topCategories.map(cat => cat.name.toLowerCase()))
  
  return chunkCategoryGroups.map(group => ({
    name: group.name,
    categories: group.categories.filter(cat => !topCategoryNames.has(cat.name.toLowerCase()))
  })).filter(group => group.categories.length > 0)
}
