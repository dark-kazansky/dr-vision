# OCR Web UI - Nuxt.js Frontend

A modern, responsive frontend for OCR processing built with Nuxt 3, Vue 3, and TypeScript.

## Features

- **Modern Stack**: Nuxt 3 with Vue 3 Composition API and TypeScript
- **Responsive Design**: TailwindCSS for beautiful, mobile-friendly UI
- **Drag-and-Drop**: Intuitive file upload with drag-and-drop support
- **Real-time Status**: Live processing status updates
- **Multi-file Support**: Process multiple files with queue management
- **PDF Support**: Preview and process PDF documents with page navigation
- **Results Display**: Three-tab results view (Build, Raw Text, Parsed)
- **Copy to Clipboard**: Easy result copying
- **Zoom Controls**: Image and PDF preview with zoom functionality

## Project Structure

```
frontend/
├── pages/
│   └── index.vue                # Main OCR page
├── components/
│   ├── FileUpload.vue           # File upload with drag-and-drop
│   ├── FileList.vue             # File list sidebar
│   ├── PreviewArea.vue          # PDF/Image preview
│   ├── ConfigPanel.vue          # OCR configuration
│   └── ResultsDisplay.vue       # Three-tab results view
├── composables/
│   ├── useOCR.ts                # OCR state and API calls
│   └── useFilePreview.ts        # Preview state management
├── assets/
│   └── css/
│       └── main.css             # Global styles
├── nuxt.config.ts               # Nuxt configuration
├── tsconfig.json                # TypeScript configuration
└── package.json                 # Dependencies and scripts
```

## Installation

### Prerequisites

- Node.js 18+ or higher
- npm or yarn
- Backend API running (see backend/README.md)

### Setup

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Configure API endpoint:**
   
   Create a `.env` file in the frontend directory:
   ```env
   API_BASE_URL=http://localhost:8000
   ```
   
   Or use the default (http://localhost:8000)

3. **Start development server:**
   ```bash
   npm run dev
   ```
   
   The app will be available at `http://localhost:3000`

## Development

### Running the Development Server

```bash
npm run dev
```

The development server includes:
- Hot module replacement (HMR)
- TypeScript type checking
- Auto-import of components and composables
- TailwindCSS with JIT compilation

### Building for Production

```bash
npm run build
```

This creates an optimized production build in `.output/`

### Preview Production Build

```bash
npm run preview
```

Preview the production build locally before deployment.

### Generate Static Site

```bash
npm run generate
```

Generate a static site for deployment to static hosting (Netlify, Vercel, etc.)

## Configuration

### API Integration

Configure the backend API URL in `nuxt.config.ts`:

```typescript
runtimeConfig: {
  public: {
    apiBaseUrl: process.env.API_BASE_URL || 'http://localhost:8000'
  }
}
```

Or set the `API_BASE_URL` environment variable.

### TailwindCSS

TailwindCSS is configured via the `@nuxtjs/tailwindcss` module. Customize in `tailwind.config.js` (auto-generated).

### TypeScript

TypeScript configuration is in `tsconfig.json`. The project uses strict mode for better type safety.

## Components

### FileUpload

Drag-and-drop file upload component with validation.

**Props:**
- `maxFiles`: Maximum number of files (default: 10)
- `maxSizeMB`: Maximum file size in MB (default: 10)
- `acceptedTypes`: Allowed file extensions (default: ['png', 'jpg', 'jpeg', 'pdf'])

**Events:**
- `upload`: Emitted when files are uploaded

### FileList

Displays uploaded files with status indicators.

**Props:**
- `files`: Array of FileItem objects
- `selectedId`: ID of currently selected file

**Events:**
- `select`: Emitted when a file is selected
- `remove`: Emitted when a file is removed
- `clear`: Emitted when clear all is clicked

### PreviewArea

Preview component for images and PDFs with zoom and navigation controls.

**Props:**
- `file`: FileItem to preview
- `zoom`: Current zoom level (50-200)
- `currentPage`: Current page number (for PDFs)
- `totalPages`: Total pages (for PDFs)
- `canZoomIn`, `canZoomOut`, `canGoNext`, `canGoPrev`: Control states

**Events:**
- `zoom-in`, `zoom-out`: Zoom controls
- `next-page`, `prev-page`: Page navigation

### ConfigPanel

OCR configuration panel with model selection and options.

**Props:**
- `availableModels`: Array of available model IDs
- `isProcessing`: Whether OCR is currently processing
- `canProcess`: Whether processing can be started

**Events:**
- `process`: Emitted when process button is clicked

### ResultsDisplay

Three-tab results display with copy-to-clipboard functionality.

**Props:**
- `results`: OCRResult object or null

**Tabs:**
- Build: Shows metadata and text
- Raw Text: Shows raw OCR output
- Parsed Result: Shows formatted/parsed text

## Composables

### useOCR

Manages OCR state and API calls.

**State:**
- `files`: Array of uploaded files
- `isProcessing`: Processing status
- `results`: Current OCR results
- `availableModels`: Available model IDs

**Methods:**
- `uploadFiles(files)`: Add files to the list
- `processFile(fileId, file, config)`: Process a file with OCR
- `removeFile(fileId)`: Remove a file from the list
- `checkHealth()`: Check backend health and get available models
- `clearFiles()`: Clear all files

### useFilePreview

Manages file preview state.

**State:**
- `previewFile`: Currently previewed file
- `zoom`: Zoom level (50-200)
- `currentPage`: Current page number
- `totalPages`: Total pages
- `previewUrl`: Preview URL

**Methods:**
- `setPreviewFile(file)`: Set file to preview
- `zoomIn()`, `zoomOut()`, `resetZoom()`: Zoom controls
- `nextPage()`, `prevPage()`, `goToPage(n)`: Page navigation

**Computed:**
- `canGoNext`, `canGoPrev`: Navigation availability
- `canZoomIn`, `canZoomOut`: Zoom availability

## Styling

### TailwindCSS

The project uses TailwindCSS for utility-first styling. Custom styles are in `assets/css/main.css`.

### CSS Variables

Global CSS variables are defined in `main.css`:
- Color palette (primary, secondary, success, warning, error)
- Neutral colors (gray scale)
- Spacing scale
- Border radius
- Shadows

### Component Styles

Components use scoped styles with a mix of:
- TailwindCSS utility classes
- Custom CSS for complex layouts
- CSS variables for theming

## API Integration

### Endpoints Used

**POST /ocr**
- Upload and process files
- Parameters: file, model_id, process_all_pages, tier

**GET /health**
- Check backend status
- Get available models

### Error Handling

The frontend handles various error types:
- `invalid_model`: Model not found
- `invalid_file`: File type not supported
- `connection_error`: Cannot connect to backend
- `processing_error`: OCR processing failed
- `file_too_large`: File exceeds size limit

Errors are displayed in:
- File status indicators
- Results display
- Toast notifications (if implemented)

## Deployment

### Static Hosting (Netlify, Vercel)

1. **Build the static site:**
   ```bash
   npm run generate
   ```

2. **Deploy the `.output/public` directory**

3. **Set environment variables:**
   - `API_BASE_URL`: Your backend API URL

### Node.js Server

1. **Build the application:**
   ```bash
   npm run build
   ```

2. **Start the server:**
   ```bash
   node .output/server/index.mjs
   ```

3. **Set environment variables:**
   - `API_BASE_URL`: Your backend API URL
   - `PORT`: Server port (default: 3000)

### Docker

Create a `Dockerfile`:

```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

ENV PORT=3000
ENV API_BASE_URL=http://localhost:8000

EXPOSE 3000

CMD ["node", ".output/server/index.mjs"]
```

Build and run:
```bash
docker build -t ocr-frontend .
docker run -p 3000:3000 -e API_BASE_URL=http://backend:8000 ocr-frontend
```

## Troubleshooting

### API Connection Errors

If you see "Cannot connect to backend":

1. Verify backend is running at the configured URL
2. Check CORS settings in backend configuration
3. Verify `API_BASE_URL` is correct
4. Check browser console for detailed errors

### File Upload Errors

If file uploads fail:

1. Check file size is under the limit (default: 10MB)
2. Verify file type is supported (png, jpg, jpeg, pdf)
3. Check backend upload configuration
4. Verify backend is accessible

### Build Errors

If build fails:

1. Clear `.nuxt` and `node_modules`:
   ```bash
   rm -rf .nuxt node_modules
   npm install
   ```

2. Check TypeScript errors:
   ```bash
   npm run build
   ```

3. Verify all dependencies are installed

### Development Server Issues

If dev server won't start:

1. Check port 3000 is not in use
2. Clear Nuxt cache:
   ```bash
   rm -rf .nuxt
   ```

3. Reinstall dependencies:
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```

## Development Tips

### Auto-imports

Nuxt 3 auto-imports:
- Components from `components/`
- Composables from `composables/`
- Vue APIs (ref, computed, watch, etc.)
- Nuxt APIs (useState, useFetch, etc.)

No need to manually import these!

### Type Safety

The project uses TypeScript strict mode. Define types for:
- Component props and emits
- Composable return values
- API responses
- State objects

### State Management

Use `useState` for global state:
```typescript
const files = useState<FileItem[]>('ocr-files', () => [])
```

The key ('ocr-files') ensures state is shared across components.

### API Calls

Use `$fetch` for API calls:
```typescript
const result = await $fetch<OCRResult>(`${apiBaseUrl}/ocr`, {
  method: 'POST',
  body: formData
})
```

It's auto-imported and handles errors automatically.

## Contributing

When adding new features:

1. Create components in `components/`
2. Create composables for shared logic in `composables/`
3. Use TypeScript for type safety
4. Follow the existing code style
5. Test with the backend API

## License

[Your License Here]

## Support

For issues or questions:
- Check the troubleshooting section
- Review component documentation
- Test with backend API
- Check browser console for errors

---

**Version:** 2.0.0  
**Last Updated:** January 27, 2026  
**Framework:** Nuxt 3.x with Vue 3 Composition API
