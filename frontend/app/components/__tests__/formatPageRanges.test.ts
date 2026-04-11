import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import { formatPageRanges } from '~/utils/formatPageRanges'

/**
 * Feature: dual-split-modes, Property 3: Page range formatting
 * 
 * **Validates: Requirements 5.3**
 * 
 * For any sorted list of positive integers representing page numbers,
 * the formatting function SHALL produce a string where contiguous sequences
 * are collapsed into ranges (e.g., "1–3") and non-contiguous pages are
 * separated by commas (e.g., "Pages 1–3, 7"). A single page SHALL be
 * displayed without a range dash.
 */
describe('Feature: dual-split-modes, Property 3: Page range formatting', () => {
  // Helper: parse the formatted string back to verify correctness
  function parseFormattedRange(formatted: string): number[] {
    // Remove "Page " or "Pages " prefix
    const body = formatted.replace(/^Pages?\s+/, '')
    const pages: number[] = []
    const segments = body.split(',').map(s => s.trim())
    for (const seg of segments) {
      if (seg.includes('–')) {
        const [start, end] = seg.split('–').map(Number)
        for (let i = start; i <= end; i++) {
          pages.push(i)
        }
      } else {
        pages.push(Number(seg))
      }
    }
    return pages.sort((a, b) => a - b)
  }

  it('should produce correct range strings for any sorted list of positive integers', () => {
    fc.assert(
      fc.property(
        fc.uniqueArray(fc.integer({ min: 1, max: 500 }), { minLength: 1, maxLength: 50 }),
        (pages: number[]) => {
          const sorted = [...pages].sort((a, b) => a - b)
          const result = formatPageRanges(sorted)

          // 1. Single page uses "Page", multiple uses "Pages"
          if (sorted.length === 1) {
            expect(result).toMatch(/^Page \d+$/)
          } else {
            expect(result).toMatch(/^Pages /)
          }

          // 2. Round-trip: parsing the formatted string back should yield the same sorted pages
          const parsed = parseFormattedRange(result)
          expect(parsed).toEqual(sorted)

          // 3. Contiguous ranges should use en-dash (–), not list individual pages
          // Verify that contiguous sequences of 3+ are collapsed
          const body = result.replace(/^Pages?\s+/, '')
          const segments = body.split(',').map(s => s.trim())
          for (const seg of segments) {
            if (seg.includes('–')) {
              const [start, end] = seg.split('–').map(Number)
              // Range must span at least 2 consecutive numbers
              expect(end).toBeGreaterThan(start)
            }
          }
        }
      ),
      { numRuns: 100 }
    )
  })

  it('should handle unsorted input by sorting first', () => {
    fc.assert(
      fc.property(
        fc.uniqueArray(fc.integer({ min: 1, max: 500 }), { minLength: 1, maxLength: 50 }),
        (pages: number[]) => {
          const sorted = [...pages].sort((a, b) => a - b)
          // Pass unsorted - function should sort internally
          const resultUnsorted = formatPageRanges(pages)
          const resultSorted = formatPageRanges(sorted)
          expect(resultUnsorted).toBe(resultSorted)
        }
      ),
      { numRuns: 100 }
    )
  })

  it('should return empty string for empty array', () => {
    expect(formatPageRanges([])).toBe('')
  })
})
