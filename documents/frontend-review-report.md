# M.DocAI Frontend Review Report

**Date:** 2026-08-26  
**Reviewer:** Kiro  
**Scope:** Full frontend codebase (`frontend/`)  
**Framework:** Nuxt 4 + Vue 3 + Tailwind CSS  

---

## Executive Summary

The M.DocAI frontend is functional and covers all core features (parse, classify, extract, split, workflows, jobs, auth, admin settings). However, the codebase shows signs of rapid iteration — a partially-completed component refactor, mixed styling approaches, debug artifacts, and a single 1700-line page file handling all views. The recommendations below are grouped by priority.

---

## 1. Critical Issues

### 1.1 Color Inconsistency Between Pages

| Location | Orange Value | Source |
|----------|-------------|--------|
| `main.css` (CSS vars) | `#ff4f00` | Design system |
| `tailwind.config.ts` | `#ff4f00` | Tailwind theme |
| `login.vue` (scoped styles) | `#f37021` | Ported from MSB Knowledge Discovery |
| `settings.vue` | `#ff4f00` | Via CSS variable fallback |

**Impact:** Users see two different brand oranges — one on login, another in the app.  
**Fix:** Align all to one value. Recommended: `#f37021` (the MSB brand orange) since login was ported intentionally from that design.

### 1.2 Debug Artifacts in Production

- ~30 `console.log` / `console.error` calls in `index.vue` (e.g., `console.log('[index.vue] Split process triggered...')`)
- Visible debug `<p>` tags in the template:
  ```html
  <p style="font-size: 12px; color: #6b7280;">Debug: pdfSourceUrl={{ pdfSourceUrl }}, previewFileUrl={{ previewFileUrl }}</p>
  ```
- `watch` blocks that only log state changes with no side effects

**Impact:** Leaks implementation details to users; clutters browser console.  
**Fix:** Remove all debug logging. If runtime observability is needed, use a conditional logger that only fires in dev mode.

### 1.3 Non-functional UI Elements

- **"Forgot Password" button** — no `@click` handler, does nothing
- **`handleFeedbackSubmit`** — only calls `console.log('Feedback submitted:', feedback)`
- **Deploy button** — opens a dialog but the dialog has no real deployment functionality

**Impact:** Users encounter dead buttons that erode trust.  
**Fix:** Either implement the functionality or remove/disable the buttons with a "Coming soon" tooltip.

---

## 2. High Priority

### 2.1 Monolithic index.vue (1700 lines)

The main page contains:
- 4 identical upload/preview dropzone sections (one per view)
- 4 config panel sections with different tab structures
- All event handlers, state management, and computed properties for every feature
- Template code that should be in components

**Existing unused components (already extracted but not used):**
- `PreviewArea.vue`
- `FileUpload.vue`
- `UploadPreview.vue`
- `FileList.vue`
- `ResultsDisplay.vue`
- `TierSelector.vue`
- `PanelTabIcon.vue`
- `ToggleSwitch.vue`

**Impact:** Hard to maintain, slow to load, difficult to reason about.  
**Fix:** Refactor into view-specific page components or use the existing extracted components. Target: index.vue under 500 lines.

### 2.2 No Mobile Navigation

The sidebar uses `position: fixed` with a hard-coded width and is completely hidden at `<768px` (via media query). There is no alternative navigation for mobile users:
- No hamburger menu
- No bottom tab bar
- No swipe gestures

**Impact:** App is unusable on phones/tablets.  
**Fix:** Add a mobile hamburger toggle that slides the sidebar in as an overlay, or implement a bottom navigation bar for mobile viewports.

### 2.3 Missing Loading States

| Page | Issue |
|------|-------|
| Settings (admin data) | Blank sections while API calls resolve |
| Index (initial health check) | No indication that backend connectivity is being verified |
| Batch file processing | No progress indicator showing N of M files complete |

**Fix:** Add skeleton loaders or centered spinners with descriptive text.

### 2.4 Eagerly-Mounted Dialogs

Four dialog components are always in the DOM regardless of visibility:
- `FeedbackDialog`
- `HelpDialog`
- `DeployDialog`
- `FullScreenEditor`

**Impact:** Unnecessary DOM nodes and potential memory usage.  
**Fix:** Use Nuxt's `<Lazy>` prefix (e.g., `<LazyFeedbackDialog>`) or `defineAsyncComponent` so they only mount when `is-open` is true.

---

## 3. Medium Priority

### 3.1 Type Safety Gaps

| Symbol | Current Type | Should Be |
|--------|-------------|-----------|
| `selectedFile` | `ref<any>` | `ref<FileItem \| null>` |
| `results` | `any` | `ParseResult \| ClassifyResult \| ExtractResult \| null` |
| Handler `config` params | `any` | `ClassifyConfig`, `ExtractConfig`, `SplitConfig` |
| `usersList` (settings) | `ref<any[]>` | `ref<UserInfo[]>` |
| `providersForm` | `ref<any[]>` | `ref<Provider[]>` |

**Impact:** No IDE autocomplete, no compile-time error catching, easy to introduce runtime bugs.  
**Fix:** Define interfaces in `app/types/` and use them throughout.

### 3.2 Duplicate Font Import

Inter font is loaded twice:
1. `app/assets/css/main.css` line 1: `@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');`
2. `index.vue` scoped style: identical `@import url(...)` statement

**Impact:** Extra network request and render-blocking CSS.  
**Fix:** Remove the duplicate from `index.vue`. The global import in `main.css` is sufficient.

### 3.3 Unused CSS Tokens

```css
--font-display: 'Degular Display', 'Inter', Helvetica, Arial, sans-serif;
--font-editorial: 'GT Alpina', Georgia, 'Times New Roman', serif;
```

These are defined in `:root` but never referenced in any stylesheet or component.

**Fix:** Either apply them (e.g., use `font-family: var(--font-display)` on headings) or remove them to reduce confusion.

### 3.4 Memory Leak — Object URLs

`URL.createObjectURL()` is called when selecting files for preview, but:
- `handleRefresh` attempts to revoke URLs by iterating `uploadedFiles`, but the values are `File` objects, not URLs
- When files are removed via `handleRemoveFile`, only the currently-selected file's URL is revoked
- Switching between files creates new URLs without revoking the previous ones (only one revocation in `handleSelectFile`)

**Impact:** Memory grows with each file interaction; never reclaimed until page reload.  
**Fix:** Maintain a `Map<string, string>` of fileId → objectURL and revoke all on cleanup.

### 3.5 Unbounded Cache

```ts
const parsedHtmlCache = ref<Map<string, string>>(new Map())
```

Grows with every unique file result but is never cleared. For users processing many documents in a session, this accumulates.

**Fix:** Implement LRU eviction (keep last 20 entries) or clear on `clearFiles()`.

---

## 4. Low Priority (Polish)

### 4.1 Accessibility

| Issue | Location | WCAG Criterion |
|-------|----------|---------------|
| Icon buttons have no accessible label | Top bar, sidebar, file list delete | 1.1.1 Non-text Content |
| Dropzone not keyboard accessible | Upload areas | 2.1.1 Keyboard |
| No skip navigation link | Layout | 2.4.1 Bypass Blocks |
| Sidebar nav uses `<a href="#">` | Sidebar | 2.1.1 Keyboard |
| Form inputs in login use only placeholder (no `<label>`) | login.vue | 1.3.1 Info and Relationships |
| No focus indicator customization | Global | 2.4.7 Focus Visible |
| Color contrast on `--text-tertiary` (#939084) over `--bg-primary` (#fffefb) | Multiple | 1.4.3 Contrast (Minimum) — ratio ~3.5:1, fails AA for normal text |

**Note:** Full WCAG compliance requires manual testing with assistive technologies and expert accessibility review.

### 4.2 Styling Paradigm Split

- Login page: Tailwind utility classes + scoped CSS overrides
- Main app: Custom CSS with CSS variables in `main.css`
- Settings page: Mix of both
- Components (ConfigPanel, ClassifyConfigPanel, SplitConfigPanel): Scoped styles

This isn't broken but makes it harder for new developers to know which approach to use.

**Recommendation:** Pick one primary approach. Since Tailwind is already installed and the design system tokens are in `tailwind.config.ts`, gradually migrate `main.css` custom classes to Tailwind utilities.

### 4.3 Unused Declared State

| Variable | Declared In | Used? |
|----------|-------------|-------|
| `isEditMode` | index.vue | No (FullScreenEditor handles this now) |
| `editableRawResult` | index.vue | No |
| `editableParsedResult` | index.vue | No |
| `resultsPerPage` | index.vue | No (pagination is page-marker based) |

**Fix:** Remove dead code.

### 4.4 Render-Blocking Font Import

Using `@import url(...)` in CSS is render-blocking. The browser pauses rendering until the font CSS is fetched.

**Fix:** Move to `<link rel="preload" as="style">` in the Nuxt head config, or use `@font-face` with `font-display: swap` for better performance.

---

## 5. Performance Recommendations

| Area | Current | Recommended |
|------|---------|-------------|
| Dialog mounting | Always in DOM | Lazy-load via `<Lazy>` prefix |
| Font loading | CSS `@import` (blocking) | `<link preload>` in nuxt.config head |
| View rendering | All views mounted with `v-if` | Use `<KeepAlive>` for tab switching or code-split into sub-pages |
| File preview URLs | Created without consistent cleanup | Track in Map, revoke on component unmount |
| HTML cache | Unbounded Map | LRU with max 20 entries |
| Image carousel (login) | All 3 images loaded immediately | Lazy-load non-active slides |

---

## 6. Architecture Recommendation

**Current structure:**
```
pages/
  index.vue (1700 lines — all views)
  login.vue
  settings.vue
components/
  (18 components, ~8 unused)
composables/
  useAuth.ts
  useOCR.ts
  useFilePreview.ts
  useJobs.ts
  useJourney.ts
  useNotification.ts
  useTierConfig.ts
  useWorkflowApi.ts
  useWorkflowStore.ts
```

**Recommended refactor:**
```
pages/
  index.vue (shell with sidebar + router-view)
  login.vue
  settings.vue
  parse.vue (or nested: pages/app/parse.vue)
  classify.vue
  extract.vue
  split.vue
  journey.vue
  jobs.vue
components/
  shared/
    UploadPreview.vue (the reusable dropzone + preview)
    ConfigPanel.vue
    ResultsDisplay.vue
  parse/
    ParseConfigPanel.vue
  classify/
    ClassifyConfigPanel.vue
  ...
```

This would:
- Reduce index.vue from 1700 → ~200 lines
- Enable route-based code splitting
- Make each feature independently testable
- Remove the 4× duplicated upload/preview template

---

## 7. Dependency Notes

| Package | Version | Note |
|---------|---------|------|
| nuxt | ^4.3.0 | Current |
| vue | ^3.5.27 | Current |
| @nuxtjs/tailwindcss | ^6.14.0 | Current |
| marked | ^17.0.1 | Used for markdown rendering in results |
| vitest | ^4.1.4 | Test runner (dev) |
| fast-check | ^4.6.0 | Property-based testing (dev) |

No known vulnerabilities. All packages are reasonably up-to-date.

---

## Summary Action Items

| # | Priority | Item | Effort |
|---|----------|------|--------|
| 1 | Critical | Align orange color to `#f37021` everywhere | 30 min |
| 2 | Critical | Remove console.logs and debug text | 1 hour |
| 3 | Critical | Fix/remove dead buttons (Forgot Password, Feedback) | 30 min |
| 4 | High | Refactor index.vue using existing components | 4-6 hours |
| 5 | High | Add mobile navigation | 2-3 hours |
| 6 | High | Add loading states to settings page | 1 hour |
| 7 | High | Lazy-load dialogs | 30 min |
| 8 | Medium | Add TypeScript interfaces | 2 hours |
| 9 | Medium | Fix memory leak (Object URLs) | 1 hour |
| 10 | Medium | Remove duplicate font import | 5 min |
| 11 | Low | Accessibility improvements | 4-6 hours |
| 12 | Low | Remove unused state variables | 15 min |
| 13 | Low | Architecture refactor (route-per-view) | 1-2 days |

**Estimated total for Critical + High:** ~10 hours  
**Estimated total for all:** ~3-4 days
