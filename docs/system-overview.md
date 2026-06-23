# Hệ thống Automation — Doc Intelligence

## Tổng quan

Doc Intelligence là hệ thống AI Automation hỗ trợ nghiệp vụ ngân hàng, tự động hóa 2 luồng xử lý chính:

1. **Luồng Bóc tách & Đối soát chứng từ** — OCR + AI phân loại + đối soát tự động
2. **Luồng Phân bổ Nostro** — Tra cứu Nostro Code + tính toán định lượng phân bổ

Hệ thống hoạt động như một **AI Service trung gian** giữa BPM System (quản lý hồ sơ ngân hàng) và các service chuyên biệt (OCR, Web Scraper), nhận request bất đồng bộ và callback kết quả về BPM khi xử lý xong.

---

## Kiến trúc hệ thống

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────────────┐
│  BPM System  │────>│    Minio     │     │         AI Service (Core)            │
│              │<────│   Storage    │<────│                                      │
└──────────────┘     └──────────────┘     │  ┌────────────┐  ┌───────────────┐  │
       │                                   │  │ OCR Engine │  │ Nostro Scraper│  │
       │         POST /api/v1/tasks        │  └────────────┘  └───────────────┘  │
       │──────────────────────────────────>│                                      │
       │         HTTP 202 (Session ID)     │  ┌────────────┐  ┌───────────────┐  │
       │<──────────────────────────────────│  │ Classifier │  │ Matching Eng. │  │
       │                                   │  └────────────┘  └───────────────┘  │
       │         Webhook Callback #1 (OCR) │                                      │
       │<──────────────────────────────────│  ┌────────────────────────────────┐  │
       │                                   │  │      Database (PostgreSQL)     │  │
       │         Webhook Callback #2       │  └────────────────────────────────┘  │
       │         (Nostro)                  │                                      │
       │<──────────────────────────────────│                                      │
       │                                   └──────────────────────────────────────┘
       │         POST /api/v1/nostro/confirm
       │──────────────────────────────────>│
```

---

## Luồng 1: Bóc tách & Đối soát chứng từ

### Mục đích

Tự động hóa quy trình kiểm tra chứng từ giao dịch quốc tế: nhận file chứng từ (PDF, DOCX, ảnh), bóc tách nội dung, phân loại loại chứng từ, trích xuất thông tin ngữ nghĩa, và đối soát chéo với dữ liệu BPM.

### Quy trình

| Bước | Mô tả | Chi tiết |
|------|--------|----------|
| 1 | **Nhận request** | BPM gửi payload JSON chứa metadata giao dịch, dữ liệu form, dữ liệu khách hàng (từ T24/FX), và danh sách Minio paths của file chứng từ |
| 2 | **Convert file → PNG** | AI Service tải file gốc từ Minio, convert tất cả format (PDF/DOCX/IMG) sang PNG per page, upload PNG lên Minio |
| 3 | **OCR bóc tách** | Gửi Minio PNG paths sang OCR Service. OCR trả về per page: `text_blocks[]` với text + bounding box `{x, y, w, h}` + confidence, và `tables[]` với cấu trúc bảng |
| 4 | **Phân loại chứng từ** | Rule-based + LLM phân loại loại chứng từ (Hợp đồng, Invoice, Tờ khai hải quan, Bill of Lading...) |
| 5 | **Trích xuất ngữ nghĩa** | LLM bóc tách các trường phức tạp: số tiền, ngày, bên mua/bán, mã hàng, điều kiện thanh toán... |
| 6 | **Đối soát** | Matching Engine đối chiếu chéo: BPM Form vs OCR vs Dữ liệu KH. Kiểm tra quy tắc nghiệp vụ, fuzzy match, phát hiện fraud |
| 7 | **Callback** | Trả kết quả về BPM: Minio image URLs + bounding boxes + kết quả đối soát (match/mismatch/fraud) |

### Output trả về BPM

```json
{
  "session_id": "uuid",
  "pages": [
    {
      "page_number": 1,
      "image_url": "https://minio/bucket/session/page_1.png",
      "text_blocks": [
        {
          "text": "Invoice No: INV-2026-001",
          "bbox": {"x": 120, "y": 45, "w": 300, "h": 25},
          "confidence": 0.97,
          "field_type": "invoice_number"
        }
      ],
      "tables": [...]
    }
  ],
  "classification": {
    "doc_type": "INVOICE",
    "confidence": 0.95
  },
  "reconciliation": {
    "status": "MISMATCH",
    "matches": [...],
    "mismatches": [...],
    "fraud_flags": [...]
  },
  "error_snippets": [
    {
      "field": "amount",
      "snippet_url": "https://minio/bucket/session/error_amount.png",
      "expected": "50,000 USD",
      "actual": "55,000 USD"
    }
  ]
}
```

---

## Luồng 2: Phân bổ Nostro Code

### Mục đích

Tự động tra cứu Nostro Code từ hệ thống web ngân hàng đại lý, và tính toán định lượng phân bổ dựa trên:
- **File danh sách phân bổ %** do BPM cung cấp (tỷ lệ % cho từng mã Nostro)
- **Tổng số yêu cầu chuyển tiền tháng trước** (dữ liệu lịch sử)

### Quy trình

| Bước | Mô tả | Chi tiết |
|------|--------|----------|
| 1 | **Trigger** | Chạy ngầm (background) sau khi luồng OCR callback xong |
| 2 | **Nhận file phân bổ %** | BPM gửi kèm trong payload ban đầu: danh sách Nostro Code + tỷ lệ % phân bổ cho từng mã |
| 3 | **Lấy dữ liệu lịch sử** | AI Service query tổng số yêu cầu chuyển tiền tháng trước (từ DB hoặc BPM payload) |
| 4 | **Tra cứu Nostro trên web** | Web Scraper giả lập thao tác trên giao diện web ngân hàng: điền form (Currency, Bank, SWIFT), submit, scrape kết quả |
| 5 | **Tính toán định lượng** | Dựa vào tổng chuyển tiền tháng trước × tỷ lệ % → ra số tiền cụ thể cho từng mã Nostro |
| 6 | **Callback** | Trả kết quả gợi ý phân bổ về BPM |
| 7 | **GDV xác nhận** | Giao dịch viên review, có thể điều chỉnh, rồi xác nhận → AI Service lưu chính thức |

### Logic tính toán phân bổ

```
Input:
  - Tổng chuyển tiền tháng trước: 10,000,000 USD
  - File phân bổ % từ BPM:
    | Nostro Code | Ngân hàng ĐL    | SWIFT      | Tỷ lệ % |
    |-------------|------------------|------------|----------|
    | NOSTRO-001  | Citibank NY      | CITIUS33   | 40%      |
    | NOSTRO-002  | JPMorgan Chase   | CHASUS33   | 35%      |
    | NOSTRO-003  | Deutsche Bank    | DEUTDEFF   | 25%      |

Output (định lượng):
    | Nostro Code | Định lượng phân bổ  | Nostro Code tra được |
    |-------------|---------------------|----------------------|
    | NOSTRO-001  | 4,000,000 USD       | (từ web scraper)     |
    | NOSTRO-002  | 3,500,000 USD       | (từ web scraper)     |
    | NOSTRO-003  | 2,500,000 USD       | (từ web scraper)     |
```

### Output trả về BPM

```json
{
  "session_id": "uuid",
  "total_last_month": 10000000,
  "currency": "USD",
  "allocations": [
    {
      "nostro_code": "NOSTRO-001",
      "bank_name": "Citibank NY",
      "swift_code": "CITIUS33",
      "allocation_pct": 40,
      "allocated_amount": 4000000,
      "scraped_nostro_info": {
        "account_number": "...",
        "available_balance": 12000000,
        "status": "ACTIVE"
      }
    }
  ]
}
```

> **Lưu ý:** Luồng Nostro sẽ được chi tiết hóa trong tài liệu riêng khi triển khai.

---

## Đặc điểm kỹ thuật

### Async Pattern (Bất đồng bộ)

- BPM gửi request → nhận HTTP 202 + Session ID ngay lập tức
- AI Service xử lý background → callback webhook khi xong
- **2 lần callback**: Callback #1 (OCR/đối soát) trả trước, Callback #2 (Nostro) trả sau
- GDV không cần chờ Nostro xong mới xem được kết quả đối soát

### File Processing Pipeline

```
Input (bất kỳ format)     AI Service convert      Minio lưu trữ       OCR Service
─────────────────────  →  ──────────────────  →  ──────────────  →  ─────────────
PDF (multi-page)           PNG per page            /session/p1.png    Bóc text + bbox
DOCX                       PNG per page            /session/p2.png    Bóc text + bbox
JPG/PNG/TIFF               PNG (giữ nguyên)       /session/p3.png    Bóc text + bbox
```

### Bounding Box Format

Mỗi text block OCR trả về kèm toạ độ pixel trên ảnh PNG:

```json
{
  "text": "Nội dung text",
  "bbox": {
    "x": 100,    // toạ độ X góc trên trái (px)
    "y": 200,    // toạ độ Y góc trên trái (px)
    "w": 350,    // chiều rộng (px)
    "h": 30      // chiều cao (px)
  },
  "confidence": 0.95
}
```

FE sử dụng image URL + bbox để render overlay highlight lên ảnh chứng từ.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Service (Core) | FastAPI + Python 3.11 |
| OCR Service | Python (Tesseract / PaddleOCR / Cloud Vision) |
| Web Scraper (Nostro) | Python (Playwright / Selenium) |
| Object Storage | MinIO |
| Database | PostgreSQL 16 |
| AI Providers | LM Studio (local), Google Gemini, AWS Bedrock, Ollama |
| Frontend | Nuxt 4 + Vue 3 + TypeScript + TailwindCSS |
| Infrastructure | Docker Compose, Kubernetes |

---

## API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|--------|
| POST | `/api/v1/tasks` | Khởi tạo task xử lý (BPM → AI Service) |
| POST | `/api/v1/nostro/confirm` | GDV xác nhận phân bổ Nostro |
| — | Webhook Callback #1 | AI Service → BPM: kết quả đối soát |
| — | Webhook Callback #2 | AI Service → BPM: gợi ý Nostro |

---

## Lợi ích

- **Giảm thời gian xử lý**: Từ 15-30 phút/hồ sơ (thủ công) → 2-5 phút (tự động)
- **Giảm sai sót**: AI đối soát chéo nhiều nguồn dữ liệu, phát hiện mismatch & fraud
- **UX tốt hơn**: GDV xem kết quả đối soát ngay (không chờ Nostro), ảnh + bounding box trực quan
- **Audit trail**: Mọi quyết định (AI gợi ý vs GDV chọn) đều được ghi log
- **Scalable**: Async pattern cho phép xử lý nhiều hồ sơ đồng thời
