import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import { renderSnippet, stripSnippetMarkers } from '~/utils/searchSnippet'

/**
 * feat-070: Full-text search snippet rendering.
 *
 * The backend wraps matched terms with control-character delimiters
 * (\x01 / \x02). renderSnippet must HTML-escape all non-marker text so the
 * result is safe to bind to v-html, then convert markers to <mark> tags.
 */
describe('feat-070: searchSnippet', () => {
  describe('renderSnippet', () => {
    it('returns empty string for empty input', () => {
      expect(renderSnippet('')).toBe('')
      expect(renderSnippet(null as unknown as string)).toBe('')
    })

    it('converts highlight markers to <mark> tags', () => {
      const snippet = '\x01invoice\x02 total: 1,000,000 VND'
      const html = renderSnippet(snippet)
      expect(html).toBe('<mark>invoice</mark> total: 1,000,000 VND')
    })

    it('handles multiple highlighted terms', () => {
      const snippet = 'the \x01quick\x02 brown \x01fox\x02 jumps'
      const html = renderSnippet(snippet)
      expect(html).toBe('the <mark>quick</mark> brown <mark>fox</mark> jumps')
    })

    it('preserves text outside markers', () => {
      const html = renderSnippet('hello \x01world\x02 end')
      expect(html).toBe('hello <mark>world</mark> end')
    })

    it('escapes HTML in plain text to prevent XSS', () => {
      const snippet = '<script>alert(1)</script>\x01hit\x02'
      const html = renderSnippet(snippet)
      expect(html).not.toContain('<script>')
      expect(html).toContain('&lt;script&gt;')
      expect(html).toBe('&lt;script&gt;alert(1)&lt;/script&gt;<mark>hit</mark>')
    })

    it('escapes HTML inside highlighted terms too', () => {
      const snippet = '\x01<b>bold</b>\x02'
      const html = renderSnippet(snippet)
      expect(html).toBe('<mark>&lt;b&gt;bold&lt;/b&gt;</mark>')
    })

    it('closes an unclosed <mark> tag', () => {
      const html = renderSnippet('text \x01unclosed')
      expect(html).toBe('text <mark>unclosed</mark>')
    })

    it('handles a lone stop marker gracefully', () => {
      const html = renderSnippet('text \x02 more')
      expect(html).toBe('text </mark> more')
    })

    it('preserves Vietnamese diacritics in highlighted text', () => {
      const snippet = 'kết quả \x01hóa đơn\x02 điện tử'
      const html = renderSnippet(snippet)
      expect(html).toBe('kết quả <mark>hóa đơn</mark> điện tử')
    })
  })

  describe('renderSnippet — property-based', () => {
    it('never emits raw <script> or unescaped < > & in non-mark output', () => {
      fc.assert(
        fc.property(
          fc.string({ maxLength: 50 }).map((s) =>
            s.replace(/\x01/g, 'A').replace(/\x02/g, 'B')
          ),
          (text) => {
            // Inject some markers randomly.
            const withMarkers = `${text}\x01${text}\x02${text}`
            const html = renderSnippet(withMarkers)
            // After stripping the trusted <mark>/</mark> tags, the remainder
            // must not contain raw angle brackets; ampersands must only appear
            // as part of HTML entities.
            const stripped = html
              .replace(/<mark>/g, '')
              .replace(/<\/mark>/g, '')
            expect(stripped).not.toMatch(/[<>]/)
            expect(stripped).not.toMatch(/&(?!amp;|lt;|gt;|quot;|#39;)/)
          }
        ),
        { numRuns: 200 }
      )
    })

    it('output is round-trippable: marker positions correspond to <mark> tags', () => {
      fc.assert(
        fc.property(
          fc.array(fc.string({ maxLength: 20 }).map((s) => s.replace(/[\x01\x02]/g, '')), { minLength: 1, maxLength: 5 }),
          (segments) => {
            // Build a snippet with markers between segments.
            const snippet = segments
              .map((s, i) => (i % 2 === 1 ? `\x01${s}\x02` : s))
              .join('')
            const html = renderSnippet(snippet)
            // Count mark tags — should equal number of \x01 markers.
            const openCount = (snippet.match(/\x01/g) || []).length
            const htmlOpenCount = (html.match(/<mark>/g) || []).length
            const htmlCloseCount = (html.match(/<\/mark>/g) || []).length
            expect(htmlOpenCount).toBe(openCount)
            expect(htmlCloseCount).toBe(openCount)
          }
        ),
        { numRuns: 100 }
      )
    })
  })

  describe('stripSnippetMarkers', () => {
    it('removes all markers and returns plain text', () => {
      expect(stripSnippetMarkers('hello \x01world\x02 end')).toBe('hello world end')
      expect(stripSnippetMarkers('\x01a\x02\x01b\x02')).toBe('ab')
    })

    it('returns empty for empty input', () => {
      expect(stripSnippetMarkers('')).toBe('')
    })

    it('leaves text without markers unchanged', () => {
      expect(stripSnippetMarkers('plain text')).toBe('plain text')
    })
  })
})
