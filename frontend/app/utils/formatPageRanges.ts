/**
 * Format page numbers into collapsed ranges.
 * e.g., [1,2,3,7] → "Pages 1–3, 7", [5] → "Page 5"
 */
export function formatPageRanges(pages: number[]): string {
  if (pages.length === 0) return ''

  const sorted = [...pages].sort((a, b) => a - b)
  const ranges: string[] = []
  let start = sorted[0]
  let end = sorted[0]

  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i] === end + 1) {
      end = sorted[i]
    } else {
      ranges.push(start === end ? `${start}` : `${start}–${end}`)
      start = sorted[i]
      end = sorted[i]
    }
  }
  ranges.push(start === end ? `${start}` : `${start}–${end}`)

  const label = sorted.length === 1 ? 'Page' : 'Pages'
  return `${label} ${ranges.join(', ')}`
}
