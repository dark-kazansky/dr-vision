/**
 * useTranslation Composable
 * 
 * Provides translated strings based on current locale.
 * Usage: const { t } = useTranslation()
 *        {{ t('sidebar.parse') }}
 */
import { useLocale } from './useLocale'

const translations: Record<string, Record<string, string>> = {
  // Sidebar navigation
  'sidebar.parse': { vi: 'Phân tích', en: 'Parse' },
  'sidebar.classify': { vi: 'Phân loại', en: 'Classify' },
  'sidebar.extract': { vi: 'Trích xuất', en: 'Extract' },
  'sidebar.split': { vi: 'Tách trang', en: 'Split' },
  'sidebar.journey': { vi: 'Doc Journey', en: 'Doc Journey' },

  // Top bar
  'topbar.feedback': { vi: 'Góp ý', en: 'Feedback' },
  'topbar.help': { vi: 'Trợ giúp', en: 'Help' },

  // Journey Dashboard
  'journey.title': { vi: 'Doc Journey', en: 'Doc Journey' },
  'journey.subtitle': { vi: 'Quản lý workflow xử lý tài liệu', en: 'Manage document processing workflows' },
  'journey.create': { vi: 'Tạo Journey mới', en: 'New Journey' },
  'journey.workflows': { vi: 'Workflows', en: 'Workflows' },
  'journey.jobHistory': { vi: 'Lịch sử Jobs', en: 'Job History' },
  'journey.noWorkflows': { vi: 'Chưa có workflow nào', en: 'No workflows yet' },
  'journey.noWorkflowsDesc': { vi: 'Tạo workflow đầu tiên để bắt đầu xử lý tài liệu tự động', en: 'Create your first workflow to start automated document processing' },
  'journey.noJobs': { vi: 'Chưa có job nào', en: 'No jobs yet' },
  'journey.noJobsDesc': { vi: 'Chạy workflow để xem lịch sử jobs tại đây', en: 'Run a workflow to see job history here' },
  'journey.allStatuses': { vi: 'Tất cả trạng thái', en: 'All statuses' },
  'journey.refresh': { vi: 'Làm mới', en: 'Refresh' },
  'journey.loading': { vi: 'Đang tải...', en: 'Loading...' },
  'journey.steps': { vi: 'bước', en: 'steps' },

  // Journey Builder toolbar
  'builder.newWorkflow': { vi: 'Workflow mới', en: 'New Workflow' },
  'builder.editingWorkflow': { vi: 'Đang chỉnh sửa', en: 'Editing Workflow' },
  'builder.save': { vi: 'Lưu', en: 'Save' },
  'builder.saving': { vi: 'Đang lưu...', en: 'Saving...' },
  'builder.execute': { vi: 'Thực thi', en: 'Execute' },
  'builder.processing': { vi: 'Đang xử lý...', en: 'Processing...' },
  'builder.deploy': { vi: 'Triển khai', en: 'Deploy' },
  'builder.results': { vi: 'Kết quả', en: 'Results' },
  'builder.dashboard': { vi: 'Dashboard', en: 'Dashboard' },

  // Builder panel
  'panel.addNodes': { vi: 'Thêm Node', en: 'Add Nodes' },
  'panel.upload': { vi: 'Tải lên', en: 'Upload' },
  'panel.parse': { vi: 'Phân tích', en: 'Parse' },
  'panel.ocr': { vi: 'OCR', en: 'OCR' },
  'panel.classify': { vi: 'Phân loại', en: 'Classify' },
  'panel.extract': { vi: 'Trích xuất', en: 'Extract' },
  'panel.split': { vi: 'Tách', en: 'Split' },
  'panel.condition': { vi: 'Điều kiện', en: 'Condition' },
  'panel.validate': { vi: 'Xác thực', en: 'Validate' },
  'panel.script': { vi: 'Script', en: 'User Script' },

  // Page content - Parse
  'page.dropzone': { vi: 'Kéo thả file vào đây hoặc nhấn để tải lên', en: 'Drop files here or click to upload' },
  'page.dropzoneFormats': { vi: 'Hỗ trợ: PNG, JPG, JPEG, PDF (tối đa 10MB)', en: 'Supported: PNG, JPG, JPEG, PDF (max 10MB)' },
  'page.parserTiers': { vi: 'Cấp độ xử lý', en: 'Parser Tiers' },
  'page.processAllPages': { vi: 'Xử lý tất cả trang PDF', en: 'Process all PDF pages' },
  'page.processAllFiles': { vi: 'Xử lý tất cả file', en: 'Process all files' },
  'page.noResults': { vi: 'Chưa có kết quả', en: 'No results yet' },
  'page.process': { vi: 'Xử lý', en: 'Process' },
  'page.processing': { vi: 'Đang xử lý...', en: 'Processing...' },
  'page.cancel': { vi: 'Hủy', en: 'Cancel' },
  'page.edit': { vi: 'Chỉnh sửa', en: 'Edit' },
  'page.uploadedFiles': { vi: 'File đã tải', en: 'Uploaded Files' },
  'page.previewError.pdf': { vi: 'Không thể tải xem trước PDF', en: 'Unable to load PDF preview' },
  'page.previewError.image': { vi: 'Không thể tải xem trước ảnh', en: 'Unable to load image preview' },

  // Tabs
  'tab.build': { vi: 'Cấu hình', en: 'Build' },
  'tab.raw': { vi: 'Kết quả thô', en: 'Raw Result' },
  'tab.parsed': { vi: 'Kết quả phân tích', en: 'Parsed Result' },
  'tab.result': { vi: 'Kết quả', en: 'Result' },

  // Common
  'common.cancel': { vi: 'Hủy', en: 'Cancel' },
  'common.ok': { vi: 'Đồng ý', en: 'OK' },
  'common.delete': { vi: 'Xóa', en: 'Delete' },
  'common.edit': { vi: 'Sửa', en: 'Edit' },
  'common.close': { vi: 'Đóng', en: 'Close' },
  'common.confirm': { vi: 'Xác nhận', en: 'Confirm' },

  // Notifications
  'notify.saveSuccess': { vi: 'Lưu workflow thành công!', en: 'Workflow saved successfully!' },
  'notify.saveFailed': { vi: 'Lưu workflow thất bại', en: 'Failed to save workflow' },
  'notify.deleteFailed': { vi: 'Xóa workflow thất bại', en: 'Failed to delete workflow' },
  'notify.uploadFirst': { vi: 'Vui lòng tải file lên trước', en: 'Please upload a file first' },
  'notify.enterPrompt': { vi: 'Vui lòng nhập mô tả dữ liệu cần trích xuất', en: 'Please enter a prompt describing what data to extract' },
  'notify.noExtractNodes': { vi: 'Không tìm thấy node trích xuất nào', en: 'No extract nodes with prompts found' },

  // Confirm dialogs
  'confirm.clearNodes': { vi: 'Xóa tất cả nodes?', en: 'Clear all nodes?' },
  'confirm.clearSchema': { vi: 'Xóa tất cả schema fields?', en: 'Clear all generated schema fields?' },
  'confirm.deleteWorkflow': { vi: 'Xóa workflow này? Không thể hoàn tác.', en: 'Delete this workflow? This cannot be undone.' },
}

export function useTranslation() {
  const { locale } = useLocale()

  const t = (key: string, fallback?: string): string => {
    const entry = translations[key]
    if (!entry) return fallback || key
    return entry[locale.value] || entry['vi'] || fallback || key
  }

  return { t }
}
