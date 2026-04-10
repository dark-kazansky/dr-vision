/**
 * Document types and their descriptions for classification
 */

export interface DocumentType {
  type: string
  description: string
}

export interface DocumentTypeGroup {
  name: string
  categories: DocumentType[]
}

export const documentTypes: DocumentType[] = [
  {
    type: 'invoice',
    description: 'Business invoice containing itemized charges, tax information, payment terms, and vendor details'
  },
  {
    type: 'receipt',
    description: 'Proof of payment document showing transaction details, amount paid, and purchase confirmation'
  },
  {
    type: 'contract',
    description: 'Legal agreement between parties outlining terms, conditions, obligations, and binding commitments'
  },
  {
    type: 'resume',
    description: 'Professional document summarizing work experience, education, skills, and qualifications'
  },
  {
    type: 'medical record',
    description: 'Patient healthcare document containing diagnosis, treatment plans, medications, and medical history'
  },
  {
    type: 'bank statement',
    description: 'Financial document showing account transactions, balances, deposits, and withdrawals over a period'
  },
  {
    type: 'tax form',
    description: 'Government document for reporting income, deductions, and tax obligations'
  },
  {
    type: 'purchase order',
    description: 'Commercial document issued by buyer to seller indicating types, quantities, and agreed prices'
  },
  {
    type: 'shipping label',
    description: 'Document containing sender and recipient information, tracking number, and delivery instructions'
  },
  {
    type: 'insurance policy',
    description: 'Contract document outlining coverage terms, premiums, deductibles, and claim procedures'
  },
  {
    type: 'passport',
    description: 'Government-issued identity document for international travel with personal information and photo'
  },
  {
    type: 'driver license',
    description: 'Official permit to operate motor vehicles with holder identification and restrictions'
  },
  {
    type: 'utility bill',
    description: 'Statement for electricity, water, gas, or internet services showing usage and charges'
  },
  {
    type: 'pay stub',
    description: 'Document showing employee earnings, deductions, taxes, and net pay for a pay period'
  },
  {
    type: 'certificate',
    description: 'Official document verifying completion, achievement, qualification, or authenticity'
  },
  {
    type: 'letter',
    description: 'Written communication between parties for business, personal, or official correspondence'
  },
  {
    type: 'form',
    description: 'Structured document with fields for collecting specific information or data'
  },
  {
    type: 'report',
    description: 'Formal document presenting information, analysis, findings, or recommendations'
  },
  {
    type: 'presentation',
    description: 'Visual document with slides containing information, data, and graphics for communication'
  },
  {
    type: 'spreadsheet',
    description: 'Tabular document with rows and columns for organizing, calculating, and analyzing data'
  }
]

// Grouped document types for organized dropdown
export const documentTypeGroups: DocumentTypeGroup[] = [
  {
    name: 'Financial Documents',
    categories: [
      { type: 'invoice', description: 'Business invoice containing itemized charges, tax information, payment terms, and vendor details' },
      { type: 'receipt', description: 'Proof of payment document showing transaction details, amount paid, and purchase confirmation' },
      { type: 'bank statement', description: 'Financial document showing account transactions, balances, deposits, and withdrawals over a period' },
      { type: 'tax form', description: 'Government document for reporting income, deductions, and tax obligations' },
      { type: 'pay stub', description: 'Document showing employee earnings, deductions, taxes, and net pay for a pay period' }
    ]
  },
  {
    name: 'Legal Documents',
    categories: [
      { type: 'contract', description: 'Legal agreement between parties outlining terms, conditions, obligations, and binding commitments' },
      { type: 'insurance policy', description: 'Contract document outlining coverage terms, premiums, deductibles, and claim procedures' }
    ]
  },
  {
    name: 'Identity Documents',
    categories: [
      { type: 'passport', description: 'Government-issued identity document for international travel with personal information and photo' },
      { type: 'driver license', description: 'Official permit to operate motor vehicles with holder identification and restrictions' }
    ]
  },
  {
    name: 'Business Documents',
    categories: [
      { type: 'purchase order', description: 'Commercial document issued by buyer to seller indicating types, quantities, and agreed prices' },
      { type: 'shipping label', description: 'Document containing sender and recipient information, tracking number, and delivery instructions' },
      { type: 'report', description: 'Formal document presenting information, analysis, findings, or recommendations' },
      { type: 'presentation', description: 'Visual document with slides containing information, data, and graphics for communication' }
    ]
  },
  {
    name: 'Personal Documents',
    categories: [
      { type: 'resume', description: 'Professional document summarizing work experience, education, skills, and qualifications' },
      { type: 'medical record', description: 'Patient healthcare document containing diagnosis, treatment plans, medications, and medical history' },
      { type: 'utility bill', description: 'Statement for electricity, water, gas, or internet services showing usage and charges' },
      { type: 'certificate', description: 'Official document verifying completion, achievement, qualification, or authenticity' },
      { type: 'letter', description: 'Written communication between parties for business, personal, or official correspondence' }
    ]
  },
  {
    name: 'Data Documents',
    categories: [
      { type: 'form', description: 'Structured document with fields for collecting specific information or data' },
      { type: 'spreadsheet', description: 'Tabular document with rows and columns for organizing, calculating, and analyzing data' }
    ]
  }
]

// Get top N document types for quick add buttons
export const getTopDocumentTypes = (count: number = 5): DocumentType[] => {
  return documentTypes.slice(0, count)
}

// Get remaining document types for dropdown
export const getRemainingDocumentTypes = (skipCount: number = 5): DocumentType[] => {
  return documentTypes.slice(skipCount)
}

// Get remaining document type groups for dropdown (excluding top N)
export const getRemainingDocumentTypeGroups = (skipCount: number = 5): DocumentTypeGroup[] => {
  const topTypes = documentTypes.slice(0, skipCount).map(dt => dt.type)
  
  return documentTypeGroups.map(group => ({
    name: group.name,
    categories: group.categories.filter(cat => !topTypes.includes(cat.type))
  })).filter(group => group.categories.length > 0)
}
