/**
 * Mock Data for Journey Dashboard development.
 *
 * Provides sample workflows (25) and jobs (15+) with various statuses
 * for UI development when backend/DB is not available.
 *
 * - Each workflow can have multiple executions (jobs)
 * - Jobs reference workflow_id to show relationship
 * - Pagination support: page size = 10
 */

import type { Job } from '~/composables/workflow/useJobManager'

export interface MockWorkflow {
  workflow_id: string
  name: string
  description: string
  step_count: number
  status: string
  created_at: string
  updated_at: string
}

export const MOCK_WORKFLOWS: MockWorkflow[] = [
  { workflow_id: 'wf-001', name: 'Invoice Processing', description: 'OCR → Classify → Extract invoice fields (amount, date, vendor)', step_count: 3, status: 'published', created_at: '2026-05-01T09:00:00Z', updated_at: '2026-05-21T14:30:00Z' },
  { workflow_id: 'wf-002', name: 'Contract Analysis', description: 'Parse PDF → Classify type → Extract key clauses and dates', step_count: 4, status: 'published', created_at: '2026-05-02T10:00:00Z', updated_at: '2026-05-20T16:00:00Z' },
  { workflow_id: 'wf-003', name: 'Bank Statement Mining', description: 'Split pages → OCR → Extract transactions → Categorize spending', step_count: 5, status: 'published', created_at: '2026-05-03T08:00:00Z', updated_at: '2026-05-21T10:00:00Z' },
  { workflow_id: 'wf-004', name: 'Receipt Scanner', description: 'Quick OCR → Extract total, date, store name', step_count: 2, status: 'published', created_at: '2026-05-04T11:00:00Z', updated_at: '2026-05-19T11:00:00Z' },
  { workflow_id: 'wf-005', name: 'ID Document Verification', description: 'Parse ID card/passport → Extract personal info → Validate format', step_count: 3, status: 'published', created_at: '2026-05-05T08:00:00Z', updated_at: '2026-05-18T08:00:00Z' },
  { workflow_id: 'wf-006', name: 'Medical Report Parser', description: 'OCR medical documents → Extract diagnosis, medications, lab results', step_count: 4, status: 'published', created_at: '2026-05-06T09:30:00Z', updated_at: '2026-05-17T09:30:00Z' },
  { workflow_id: 'wf-007', name: 'Tax Form Extractor', description: 'Parse tax forms → Extract income, deductions, tax amounts', step_count: 3, status: 'published', created_at: '2026-05-07T10:00:00Z', updated_at: '2026-05-16T10:00:00Z' },
  { workflow_id: 'wf-008', name: 'Shipping Label Reader', description: 'OCR shipping labels → Extract sender, receiver, tracking number', step_count: 2, status: 'published', created_at: '2026-05-08T07:00:00Z', updated_at: '2026-05-15T07:00:00Z' },
  { workflow_id: 'wf-009', name: 'Resume/CV Parser', description: 'Parse resume → Extract skills, experience, education, contact info', step_count: 3, status: 'published', created_at: '2026-05-09T14:00:00Z', updated_at: '2026-05-14T14:00:00Z' },
  { workflow_id: 'wf-010', name: 'Insurance Claim Processor', description: 'Classify claim type → Extract policy number, damage details, amounts', step_count: 4, status: 'published', created_at: '2026-05-10T08:30:00Z', updated_at: '2026-05-13T08:30:00Z' },
  { workflow_id: 'wf-011', name: 'Utility Bill Analyzer', description: 'OCR utility bills → Extract usage, charges, account number', step_count: 3, status: 'published', created_at: '2026-05-11T09:00:00Z', updated_at: '2026-05-21T09:00:00Z' },
  { workflow_id: 'wf-012', name: 'Purchase Order Validator', description: 'Parse PO → Extract items, quantities, prices → Validate totals', step_count: 4, status: 'published', created_at: '2026-05-12T10:00:00Z', updated_at: '2026-05-20T10:00:00Z' },
  { workflow_id: 'wf-013', name: 'Passport Data Extraction', description: 'OCR passport MRZ → Extract name, nationality, expiry date', step_count: 2, status: 'published', created_at: '2026-05-13T11:00:00Z', updated_at: '2026-05-19T11:00:00Z' },
  { workflow_id: 'wf-014', name: 'Loan Application Review', description: 'Parse application → Extract income, assets, liabilities → Score', step_count: 5, status: 'draft', created_at: '2026-05-14T08:00:00Z', updated_at: '2026-05-18T08:00:00Z' },
  { workflow_id: 'wf-015', name: 'Delivery Note Processor', description: 'OCR delivery notes → Extract items delivered, signatures, dates', step_count: 3, status: 'published', created_at: '2026-05-15T09:00:00Z', updated_at: '2026-05-17T09:00:00Z' },
  { workflow_id: 'wf-016', name: 'Academic Transcript Parser', description: 'Parse transcripts → Extract courses, grades, GPA calculation', step_count: 3, status: 'draft', created_at: '2026-05-16T10:00:00Z', updated_at: '2026-05-16T10:00:00Z' },
  { workflow_id: 'wf-017', name: 'Business Card Scanner', description: 'Quick OCR → Extract name, company, phone, email, address', step_count: 2, status: 'published', created_at: '2026-05-17T07:30:00Z', updated_at: '2026-05-21T07:30:00Z' },
  { workflow_id: 'wf-018', name: 'Warranty Card Extractor', description: 'Parse warranty docs → Extract product, serial number, expiry', step_count: 3, status: 'draft', created_at: '2026-05-18T08:00:00Z', updated_at: '2026-05-18T08:00:00Z' },
  { workflow_id: 'wf-019', name: 'Customs Declaration Form', description: 'OCR customs forms → Extract goods, values, origin country', step_count: 4, status: 'published', created_at: '2026-05-19T09:00:00Z', updated_at: '2026-05-21T09:00:00Z' },
  { workflow_id: 'wf-020', name: 'Rental Agreement Analyzer', description: 'Parse lease → Extract rent, duration, terms, parties involved', step_count: 4, status: 'published', created_at: '2026-05-20T10:00:00Z', updated_at: '2026-05-21T10:00:00Z' },
  { workflow_id: 'wf-021', name: 'Prescription Reader', description: 'OCR prescription → Extract medication names, dosage, frequency', step_count: 2, status: 'draft', created_at: '2026-05-20T11:00:00Z', updated_at: '2026-05-20T11:00:00Z' },
  { workflow_id: 'wf-022', name: 'Vehicle Registration Parser', description: 'Parse registration docs → Extract plate, VIN, owner, expiry', step_count: 3, status: 'published', created_at: '2026-05-20T14:00:00Z', updated_at: '2026-05-21T14:00:00Z' },
  { workflow_id: 'wf-023', name: 'Meeting Minutes Summarizer', description: 'OCR handwritten notes → Parse → Summarize action items', step_count: 3, status: 'draft', created_at: '2026-05-21T08:00:00Z', updated_at: '2026-05-21T08:00:00Z' },
  { workflow_id: 'wf-024', name: 'Payslip Data Extractor', description: 'Parse payslips → Extract gross, net, deductions, employer info', step_count: 3, status: 'published', created_at: '2026-05-21T09:00:00Z', updated_at: '2026-05-21T12:00:00Z' },
  { workflow_id: 'wf-025', name: 'Multi-Language Invoice', description: 'Detect language → OCR with appropriate model → Extract fields', step_count: 4, status: 'draft', created_at: '2026-05-21T10:00:00Z', updated_at: '2026-05-21T10:00:00Z' },
]

// Helper to generate jobs — multiple executions per workflow
function generateMockJobs(): Job[] {
  const jobs: Job[] = []
  let jobCounter = 1

  const makeJob = (
    wfId: string, wfName: string, status: Job['status'], progress: number,
    filename: string, nodes: Job['nodes'], error: string | null,
    createdOffset: number, durationSec: number
  ): Job => {
    const id = `job-${String(jobCounter++).padStart(3, '0')}`
    const created = new Date(Date.now() - createdOffset * 60000).toISOString()
    const started = new Date(Date.now() - (createdOffset - 0.1) * 60000).toISOString()
    const completed = ['completed', 'failed'].includes(status)
      ? new Date(Date.now() - (createdOffset - durationSec / 60) * 60000).toISOString() : null

    return {
      job_id: id, workflow_id: wfId, workflow_name: wfName, status, progress,
      nodes, filename, file_count: 1, max_retries: 3,
      created_at: created, started_at: started, completed_at: completed,
      cancelled_at: null, error, results: null,
    }
  }

  // wf-001 Invoice Processing — 5 executions
  jobs.push(makeJob('wf-001', 'Invoice Processing', 'completed', 1.0, 'invoice_001.pdf', [
    { node_id: 'n1', node_type: 'parse', node_label: 'OCR', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n2', node_type: 'classify', node_label: 'Classify', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n3', node_type: 'extract', node_label: 'Extract', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
  ], null, 5, 8))

  jobs.push(makeJob('wf-001', 'Invoice Processing', 'completed', 1.0, 'invoice_002.pdf', [
    { node_id: 'n1', node_type: 'parse', node_label: 'OCR', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n2', node_type: 'classify', node_label: 'Classify', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n3', node_type: 'extract', node_label: 'Extract', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
  ], null, 30, 6))

  jobs.push(makeJob('wf-001', 'Invoice Processing', 'failed', 0.33, 'invoice_corrupt.pdf', [
    { node_id: 'n1', node_type: 'parse', node_label: 'OCR', status: 'failed', retry_count: 3, started_at: null, completed_at: null, error: 'PDF is corrupted or password-protected' },
    { node_id: 'n2', node_type: 'classify', node_label: 'Classify', status: 'skipped', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n3', node_type: 'extract', node_label: 'Extract', status: 'skipped', retry_count: 0, started_at: null, completed_at: null, error: null },
  ], 'OCR failed: PDF is corrupted', 60, 12))

  jobs.push(makeJob('wf-001', 'Invoice Processing', 'running', 0.66, 'invoice_batch.pdf', [
    { node_id: 'n1', node_type: 'parse', node_label: 'OCR', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n2', node_type: 'classify', node_label: 'Classify', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n3', node_type: 'extract', node_label: 'Extract', status: 'running', retry_count: 0, started_at: null, completed_at: null, error: null },
  ], null, 1, 0))

  jobs.push(makeJob('wf-001', 'Invoice Processing', 'running', 0.1, 'invoice_new.pdf', [
    { node_id: 'n1', node_type: 'parse', node_label: 'OCR', status: 'running', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n2', node_type: 'classify', node_label: 'Classify', status: 'pending', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n3', node_type: 'extract', node_label: 'Extract', status: 'pending', retry_count: 0, started_at: null, completed_at: null, error: null },
  ], null, 0.5, 0))

  // wf-002 Contract Analysis — 3 executions
  jobs.push(makeJob('wf-002', 'Contract Analysis', 'completed', 1.0, 'contract_lease.pdf', [
    { node_id: 'n1', node_type: 'parse', node_label: 'Parse PDF', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n2', node_type: 'classify', node_label: 'Classify', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n3', node_type: 'extract', node_label: 'Extract Clauses', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n4', node_type: 'extract', node_label: 'Extract Dates', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
  ], null, 120, 15))

  jobs.push(makeJob('wf-002', 'Contract Analysis', 'failed', 0.5, 'contract_complex.pdf', [
    { node_id: 'n1', node_type: 'parse', node_label: 'Parse PDF', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n2', node_type: 'classify', node_label: 'Classify', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n3', node_type: 'extract', node_label: 'Extract Clauses', status: 'failed', retry_count: 3, started_at: null, completed_at: null, error: 'LLM timeout after 30s' },
    { node_id: 'n4', node_type: 'extract', node_label: 'Extract Dates', status: 'skipped', retry_count: 0, started_at: null, completed_at: null, error: null },
  ], 'Extract Clauses failed: LLM timeout', 90, 20))

  jobs.push(makeJob('wf-002', 'Contract Analysis', 'failed', 0.25, 'contract_nda.pdf', [
    { node_id: 'n1', node_type: 'parse', node_label: 'Parse PDF', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n2', node_type: 'classify', node_label: 'Classify', status: 'skipped', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n3', node_type: 'extract', node_label: 'Extract Clauses', status: 'skipped', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n4', node_type: 'extract', node_label: 'Extract Dates', status: 'skipped', retry_count: 0, started_at: null, completed_at: null, error: null },
  ], 'User cancelled during processing', 180, 0))

  // wf-003 Bank Statement — 3 executions
  jobs.push(makeJob('wf-003', 'Bank Statement Mining', 'completed', 1.0, 'vietcombank_04_2026.pdf', [
    { node_id: 'n1', node_type: 'split', node_label: 'Split Pages', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n2', node_type: 'parse', node_label: 'OCR Pages', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n3', node_type: 'extract', node_label: 'Transactions', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n4', node_type: 'classify', node_label: 'Categorize', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n5', node_type: 'extract', node_label: 'Summary', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
  ], null, 45, 25))

  jobs.push(makeJob('wf-003', 'Bank Statement Mining', 'completed', 1.0, 'techcombank_05_2026.pdf', [
    { node_id: 'n1', node_type: 'split', node_label: 'Split Pages', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n2', node_type: 'parse', node_label: 'OCR Pages', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n3', node_type: 'extract', node_label: 'Transactions', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n4', node_type: 'classify', node_label: 'Categorize', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n5', node_type: 'extract', node_label: 'Summary', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
  ], null, 200, 30))

  jobs.push(makeJob('wf-003', 'Bank Statement Mining', 'running', 0.4, 'mbbank_05_2026.pdf', [
    { node_id: 'n1', node_type: 'split', node_label: 'Split Pages', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n2', node_type: 'parse', node_label: 'OCR Pages', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n3', node_type: 'extract', node_label: 'Transactions', status: 'running', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n4', node_type: 'classify', node_label: 'Categorize', status: 'pending', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n5', node_type: 'extract', node_label: 'Summary', status: 'pending', retry_count: 0, started_at: null, completed_at: null, error: null },
  ], null, 2, 0))

  // wf-004 Receipt — 2 executions
  jobs.push(makeJob('wf-004', 'Receipt Scanner', 'completed', 1.0, 'receipt_highland.jpg', [
    { node_id: 'n1', node_type: 'parse', node_label: 'Quick OCR', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n2', node_type: 'extract', node_label: 'Extract Info', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
  ], null, 15, 3))

  jobs.push(makeJob('wf-004', 'Receipt Scanner', 'completed', 1.0, 'receipt_grab.png', [
    { node_id: 'n1', node_type: 'parse', node_label: 'Quick OCR', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n2', node_type: 'extract', node_label: 'Extract Info', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
  ], null, 300, 2))

  // wf-006 Medical — 1 execution
  jobs.push(makeJob('wf-006', 'Medical Report Parser', 'completed', 1.0, 'blood_test_results.pdf', [
    { node_id: 'n1', node_type: 'parse', node_label: 'OCR', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n2', node_type: 'classify', node_label: 'Report Type', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n3', node_type: 'extract', node_label: 'Lab Values', status: 'completed', retry_count: 1, started_at: null, completed_at: null, error: null },
    { node_id: 'n4', node_type: 'extract', node_label: 'Diagnosis', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
  ], null, 500, 12))

  // wf-009 Resume — 1 execution
  jobs.push(makeJob('wf-009', 'Resume/CV Parser', 'completed', 1.0, 'cv_nguyen_van_a.pdf', [
    { node_id: 'n1', node_type: 'parse', node_label: 'Parse', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n2', node_type: 'extract', node_label: 'Skills & Exp', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n3', node_type: 'extract', node_label: 'Contact', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
  ], null, 400, 7))

  // wf-017 Business Card — 2 executions
  jobs.push(makeJob('wf-017', 'Business Card Scanner', 'completed', 1.0, 'card_ceo_abc.jpg', [
    { node_id: 'n1', node_type: 'parse', node_label: 'OCR', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n2', node_type: 'extract', node_label: 'Extract', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
  ], null, 10, 2))

  jobs.push(makeJob('wf-017', 'Business Card Scanner', 'failed', 0.5, 'card_blurry.jpg', [
    { node_id: 'n1', node_type: 'parse', node_label: 'OCR', status: 'completed', retry_count: 0, started_at: null, completed_at: null, error: null },
    { node_id: 'n2', node_type: 'extract', node_label: 'Extract', status: 'failed', retry_count: 3, started_at: null, completed_at: null, error: 'Low confidence: image too blurry' },
  ], 'Extract failed: image too blurry', 8, 5))

  return jobs
}

export const MOCK_JOBS: Job[] = generateMockJobs()

/**
 * Use mock data as fallback when API returns empty.
 */
export function useMockData() {
  const useMocks = useState<boolean>('use-mock-data', () => false)

  const enableMocks = () => { useMocks.value = true }
  const disableMocks = () => { useMocks.value = false }

  return {
    useMocks: readonly(useMocks),
    mockWorkflows: MOCK_WORKFLOWS,
    mockJobs: MOCK_JOBS,
    enableMocks,
    disableMocks,
  }
}
