# Tài Liệu Tính Năng Hiện Có (Existing Features)

Dự án **Doc Intelligence** (OCR Web UI) được phát triển dưới dạng một hệ thống nhận dạng ký tự quang học (OCR) hoàn chỉnh, phân chia thành hai thành phần chính: **Backend (FastAPI)** và **Frontend (Nuxt.js)**. Dưới đây là danh sách chi tiết các tính năng đã được triển khai.

## 1. Backend (FastAPI)

Backend được xây dựng theo cấu trúc modular, hỗ trợ xử lý hình ảnh và tài liệu PDF, quản lý các kết nối đến nhiều mô hình AI khác nhau.

- **Hỗ trợ Đa Mô Hình (Multi-Model Support):**
  - Tích hợp linh hoạt nhiều mô hình AI: `lightonocr-2-1b` (chạy qua vLLM ở production), `deepseek-ocr` và `nanonets-ocr2-3b` (chạy cục bộ qua LM Studio).
- **Xử lý Đa Định Dạng & PDF:**
  - Hỗ trợ trích xuất văn bản từ hình ảnh (PNG, JPG, JPEG).
  - Hỗ trợ xử lý tệp PDF từ đơn trang đến đa trang (lựa chọn xử lý một trang cụ thể hoặc tất cả các trang).
- **Kiến trúc dựa trên Cấu hình (Configuration-Driven):**
  - Sử dụng định dạng YAML (`config.yaml`) để quản lý toàn bộ thiết lập (base_url của LM Studio, cổng API, giới hạn tải lên, v.v.).
  - Hỗ trợ ghi đè cấu hình thông qua biến môi trường để dễ dàng chuyển đổi giữa development và production.
- **Bảo vệ kiểu dữ liệu & Xử lý lỗi:**
  - Sử dụng Pydantic models để đảm bảo tính hợp lệ (validation) của request/response.
  - Cơ chế thông báo lỗi chi tiết, rành mạch thành từng loại lỗi (`invalid_model`, `invalid_file`, `connection_error`, v.v.).
- **Tài liệu API Tự Động:**
  - Giao diện Swagger UI tương tác (`/docs`) và ReDoc (`/redoc`) được tạo ra tự động nhờ sức mạnh của FastAPI.

## 2. Frontend (Nuxt.js)

Giao diện người dùng được xây dựng nguyên bản bằng Nuxt 3, Vue 3 Composition API và TailwindCSS mang đến trải nghiệm mượt mà, phản hồi tốt trên đa thiết bị.

- **Quản Lý Tải Lên Tệp (File Upload Management):**
  - Khu vực Upload hỗ trợ chức năng Kéo thả tệp (Drag-and-Drop) linh hoạt.
  - Quản lý danh sách các tệp chờ và tệp đã xử lý (File List queue) cùng hiển thị trạng thái xử lý trực tiếp.
- **Trình Xem Trước (Preview Area):**
  - Hỗ trợ xem trước hình ảnh và file PDF trực tiếp trên trình duyệt.
  - Các chức năng kiểm soát điều hướng: Phóng to (Zoom In), Thu nhỏ (Zoom Out), Điều hướng trang cho file PDF.
- **Bảng Điều Khiển Cấu Hình (Config Panel):**
  - Giao diện chọn các model AI (`lightonocr-2-1b`, v.v.) hiện có từ Backend (được gọi qua `/health` endpoint).
- **Giao Diện Hiển Thị Kết Quả Đa Dạng (Results Display):**
  - **Thẻ "Build":** Hiển thị metadata và văn bản dựng sẵn.
  - **Thẻ "Raw Text":** Trả về kết quả đầu ra thô từ mô hình AI.
  - **Thẻ "Parsed Result":** Cung cấp cấu trúc văn bản hoặc biểu mẫu đã được định dạng.
  - Tích hợp nút "Copy to Clipboard" cho phép sao chép dữ liệu trích xuất chỉ với 1 cú click chuột.
- **Real-time Status:**
  - Góc nhìn thời gian thực giúp người dùng theo dõi được việc tiến hóa xử lý OCR diễn ra như thế nào.

## Tổng Kết

Dự án có sự phân chia **Separation of Concerns** rõ rệt:

1. Giao diện (Frontend) quản lý UI/UX tĩnh và đồng bộ trạng thái.
2. Dịch vụ Lõi (Backend) tập trung lo phần luồng xử lý Data, Routing theo Controller, và kết nối với Provider/LLM Services.
   Hệ thống cũng đang cung cấp các bản script cho CI/CD và Docker nhằm dễ dàng triển khai (deploy).
