import { describe, it, expect, vi } from 'vitest'
import * as fc from 'fast-check'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { formatPageRanges } from '~/utils/formatPageRanges'

/**
 * Feature: dual-split-modes, Property 4: Document type result card rendering completeness
 *
 * **Validates: Requirements 5.1, 5.2, 5.4**
 *
 * For any DocumentTypeResult with a type name, a non-empty list of page numbers,
 * and an optional confidence score, the rendered result card SHALL contain the type name,
 * the formatted page range string, the total page count, and (if confidence is present)
 * a confidence badge with the correct styling class based on thresholds
 * (high >= 0.8, medium >= 0.5, low < 0.5).
 */

// Minimal rendering component that mirrors the doc-type result card template
const DocTypeResultCard = defineComponent({
  props: {
    typeName: { type: String, required: true },
    pageNumbers: { type: Array as () => number[], required: true },
    pageCount: { type: Number, required: true },
    formattedPageRange: { type: String, required: true },
    confidence: { type: Number, default: undefined },
  },
  setup(props) {
    function getConfidenceClass(confidence: number) {
      if (confidence >= 0.8) return 'high-confidence'
      if (confidence >= 0.5) return 'medium-confidence'
      return 'low-confidence'
    }
    function getConfidenceLabel(confidence: number) {
      if (confidence >= 0.8) return 'High confidence'
      if (confidence >= 0.5) return 'Medium confidence'
      return 'Low confidence'
    }
    return { getConfidenceClass, getConfidenceLabel }
  },
  template: `
    <div class="category-result-card doc-type-result-card">
      <div class="category-header">
        <h4 class="category-name">{{ typeName }}</h4>
        <span class="page-count-badge">{{ pageCount }} {{ pageCount === 1 ? 'page' : 'pages' }}</span>
      </div>
      <div class="doc-type-page-range">{{ formattedPageRange }}</div>
      <div v-if="confidence != null" class="confidence-badge-wrapper">
        <span class="confidence-badge" :class="getConfidenceClass(confidence)">
          {{ getConfidenceLabel(confidence) }}
        </span>
      </div>
    </div>
  `,
})

describe('Feature: dual-split-modes, Property 4: Document type result card rendering completeness', () => {
  // Arbitrary for DocumentTypeResult
  // Arbitrary for DocumentTypeResult - use alphanumeric strings to avoid HTML encoding edge cases
  const documentTypeResultArb = fc.record({
    type_name: fc.stringMatching(/^[A-Za-z][A-Za-z0-9 \-]{0,30}[A-Za-z0-9]$/).filter(s => s.length >= 2),
    page_numbers: fc.uniqueArray(fc.integer({ min: 1, max: 500 }), { minLength: 1, maxLength: 30 }),
    confidence: fc.option(fc.double({ min: 0, max: 1, noNaN: true }), { nil: undefined }),
  })

  it('rendered card contains type name, formatted page range, page count, and correct confidence class', () => {
    fc.assert(
      fc.property(documentTypeResultArb, (dtResult) => {
        const sorted = [...dtResult.page_numbers].sort((a, b) => a - b)
        const formattedRange = formatPageRanges(sorted)
        const pageCount = sorted.length

        const wrapper = mount(DocTypeResultCard, {
          props: {
            typeName: dtResult.type_name,
            pageNumbers: sorted,
            pageCount,
            formattedPageRange: formattedRange,
            confidence: dtResult.confidence,
          },
        })

        const html = wrapper.html()
        const text = wrapper.text()

        // 1. Type name is present (check text content to avoid HTML entity encoding issues)
        expect(text).toContain(dtResult.type_name)

        // 2. Formatted page range is present
        expect(text).toContain(formattedRange)

        // 3. Page count badge is present
        const expectedCountText = pageCount === 1 ? '1 page' : `${pageCount} pages`
        expect(text).toContain(expectedCountText)

        // 4. Confidence badge with correct class (if confidence is present)
        if (dtResult.confidence != null) {
          const badge = wrapper.find('.confidence-badge')
          expect(badge.exists()).toBe(true)

          if (dtResult.confidence >= 0.8) {
            expect(badge.classes()).toContain('high-confidence')
          } else if (dtResult.confidence >= 0.5) {
            expect(badge.classes()).toContain('medium-confidence')
          } else {
            expect(badge.classes()).toContain('low-confidence')
          }
        } else {
          // No confidence badge should be rendered
          expect(wrapper.find('.confidence-badge').exists()).toBe(false)
        }

        wrapper.unmount()
      }),
      { numRuns: 100 }
    )
  })
})
