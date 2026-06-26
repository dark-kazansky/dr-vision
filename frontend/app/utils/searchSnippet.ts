/**
 * Render a search snippet with XSS-safe highlighting.
 *
 * The backend `ts_headline` wraps matched terms with control-character
 * delimiters `\x01` (start) and `\x02` (stop) instead of HTML tags, so the
 * frontend can HTML-escape the text first and only then convert the
 * delimiters into `<mark>` tags. This guarantees that any HTML present in
 * the source OCR text is neutralised before being rendered via `v-html`.
 */

const HIGHLIGHT_START = '\x01'
const HIGHLIGHT_STOP = '\x02'

function escapeHtml(input: string): string {
  return input
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

/**
 * Convert a backend snippet (with `\x01`/`\x02` markers) into an HTML string
 * where matched terms are wrapped in `<mark>` and all other text is escaped.
 *
 * Returns a string safe to bind to `v-html`.
 */
export function renderSnippet(snippet: string): string {
  if (!snippet) return ''
  const parts = snippet.split(/(\x01|\x02)/)
  let html = ''
  let inMark = false
  for (const part of parts) {
    if (part === HIGHLIGHT_START) {
      html += '<mark>'
      inMark = true
    } else if (part === HIGHLIGHT_STOP) {
      html += '</mark>'
      inMark = false
    } else if (part !== '') {
      html += escapeHtml(part)
    }
  }
  // Close an unclosed <mark> to keep the HTML well-formed.
  if (inMark) html += '</mark>'
  return html
}

/**
 * Strip the highlight markers and return plain text (no HTML, no markers).
 * Useful for previews or when highlighting is not wanted.
 */
export function stripSnippetMarkers(snippet: string): string {
  if (!snippet) return ''
  return snippet.replace(/\x01/g, '').replace(/\x02/g, '')
}
