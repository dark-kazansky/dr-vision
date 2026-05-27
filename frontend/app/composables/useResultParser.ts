/**
 * Composable for parsing OCR results — markdown, HTML, plain text formatting.
 */
import { marked } from 'marked'

export function useResultParser() {
  const parsedHtmlCache = ref<Map<string, string>>(new Map())

  const clearCache = () => {
    parsedHtmlCache.value.clear()
  }

  /**
   * Parse result pages from raw text (split by "--- Page X ---" markers).
   */
  const parseResultPages = (text: string | undefined): string[] => {
    if (!text) return []
    if (text.includes('--- Page')) {
      return text.split(/--- Page \d+ ---\n/).filter(p => p.trim())
    }
    return [text]
  }

  /**
   * Parse a single page result into formatted HTML.
   */
  const parseToHtml = (text: string, pageIndex: number): string => {
    if (!text) return ''

    const cacheKey = `${pageIndex}-${text.substring(0, 100)}`
    if (parsedHtmlCache.value.has(cacheKey)) {
      return parsedHtmlCache.value.get(cacheKey)!
    }

    let html = ''

    const hasHtmlTable = /<table[\s\S]*?<\/table>/i.test(text)
    const hasHtmlTags = /<(?!table|\/table|tr|\/tr|td|\/td|th|\/th|tbody|\/tbody|thead|\/thead)[a-z][\s\S]*?>/i.test(text)
    const hasMarkdownSyntax = /(\*\*|__|\#|\[.*?\]\(.*?\)|```|^\s*[-*]|\n\d+\.)/.test(text)

    // Strategy 1: Mixed HTML and Markdown
    if (hasHtmlTable && hasMarkdownSyntax) {
      try {
        const tables: string[] = []
        const markers: string[] = []

        let processedText = text.replace(/<table[\s\S]*?<\/table>/gi, (match) => {
          const index = tables.length
          tables.push(match)
          const marker = `|||TABLE_MARKER_${index}|||`
          markers.push(marker)
          return marker
        })

        html = marked.parse(processedText, { breaks: true, gfm: true, pedantic: false }) as string

        tables.forEach((table, index) => {
          const patterns = [
            new RegExp(`<p>\\|\\|\\|TABLE_MARKER_${index}\\|\\|\\|</p>`, 'g'),
            new RegExp(`\\|\\|\\|TABLE_MARKER_${index}\\|\\|\\|`, 'g')
          ]
          patterns.forEach(pattern => { html = html.replace(pattern, table) })
        })

        html = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
        parsedHtmlCache.value.set(cacheKey, html)
        return html
      } catch (error) {
        console.error('Mixed content parsing error:', error)
      }
    }

    // Strategy 2: Pure HTML content
    if (hasHtmlTable || (hasHtmlTags && !hasMarkdownSyntax)) {
      html = text
      html = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
      html = html.replace(/<\/(p|div|table|h[1-6])>/gi, '</$1>\n')
      parsedHtmlCache.value.set(cacheKey, html)
      return html
    }

    // Strategy 3: Markdown content
    if (hasMarkdownSyntax) {
      try {
        html = marked.parse(text, {
          breaks: true, gfm: true, pedantic: false,
        }) as string
        parsedHtmlCache.value.set(cacheKey, html)
        return html
      } catch (error) {
        console.error('Markdown parsing error:', error)
      }
    }

    // Strategy 4: Plain text formatting
    html = text

    // Detect pipe-separated tables
    if (text.includes('|')) {
      const lines = text.split('\n')
      let inTable = false
      let tableHtml = ''
      let nonTableHtml = ''

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]!.trim()
        if (line.includes('|')) {
          if (!inTable) { inTable = true; tableHtml = '<table><tbody>' }
          if (/^\|[\s\-:]+\|$/.test(line)) continue
          const cells = line.split('|').filter(cell => cell.trim())
          const prevLine = i > 0 ? lines[i - 1] ?? '' : ''
          const isHeader = i === 0 || (i === 1 && /^\|[\s\-:]+\|$/.test(prevLine))
          if (isHeader && tableHtml === '<table><tbody>') {
            tableHtml = '<table><thead><tr>'
            cells.forEach(cell => { tableHtml += `<th>${cell.trim()}</th>` })
            tableHtml += '</tr></thead><tbody>'
          } else {
            tableHtml += '<tr>'
            cells.forEach(cell => { tableHtml += `<td>${cell.trim()}</td>` })
            tableHtml += '</tr>'
          }
        } else {
          if (inTable) { tableHtml += '</tbody></table>'; nonTableHtml += tableHtml; tableHtml = ''; inTable = false }
          nonTableHtml += line + '\n'
        }
      }
      if (inTable) { tableHtml += '</tbody></table>'; nonTableHtml += tableHtml }
      html = nonTableHtml
    }

    // Convert paragraphs and formatting
    html = html.replace(/\n\n+/g, '</p><p>')
    html = '<p>' + html + '</p>'
    html = html.replace(/\n/g, '<br>')
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    html = html.replace(/__(.+?)__/g, '<strong>$1</strong>')
    html = html.replace(/(?<!\*)\*([^\*]+?)\*(?!\*)/g, '<em>$1</em>')
    html = html.replace(/(?<!_)_([^_]+?)_(?!_)/g, '<em>$1</em>')
    html = html.replace(/<p>(.+?):<\/p>/g, '<h3>$1:</h3>')
    html = html.replace(/<br>[\-\*]\s+(.+?)(?=<br>|<\/p>)/g, '<li>$1</li>')
    html = html.replace(/(<li>.*?<\/li>)+/g, '<ul>$&</ul>')
    html = html.replace(/<br>\d+\.\s+(.+?)(?=<br>|<\/p>)/g, '<li>$1</li>')
    html = html.replace(/(<li>.*?<\/li>)+/g, (match) => {
      if (!match.includes('<ul>')) return '<ol>' + match + '</ol>'
      return match
    })

    parsedHtmlCache.value.set(cacheKey, html)
    return html
  }

  return {
    parseResultPages,
    parseToHtml,
    clearCache,
  }
}
