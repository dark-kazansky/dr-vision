// Parser tier to OCR model mapping
export const parserTierToModel: Record<string, string> = {
  'Rapid': 'deepseek-ocr',
  'Normal': 'lightonocr-2-1b',
  'Advance': 'nanonets-ocr2-3b'
}

// Extractor tier to Poe model mapping
export const extractorTierToModel: Record<string, string> = {
  'Rapid': 'assistant',
  'Normal': 'qwen3-max',
  'Advance': 'gemini-3-pro'
}

// Parse tier to model mapping (for Parse view)
export const parseTierToModel: Record<string, string> = {
  'Rapid': 'deepseek-ocr',
  'Normal': 'lightonocr-2-1b',
  'Advance': 'nanonets-ocr2-3b'
}
