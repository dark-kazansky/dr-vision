# Banking Data Mining - Tổng Quan

## Giới thiệu

Tài liệu này mô tả kế hoạch triển khai tính năng Data Mining cho lĩnh vực ngân hàng trên nền tảng Dr.Vision. Hệ thống tận dụng pipeline xử lý tài liệu hiện có (OCR → Classification → Extraction → Splitting) để khai thác dữ liệu từ các tài liệu ngân hàng.

## Mục tiêu

- Tự động hóa việc trích xuất dữ liệu từ tài liệu ngân hàng
- Phân loại tài liệu ngân hàng theo loại (sao kê, hợp đồng vay, KYC, ...)
- Trích xuất giao dịch chi tiết từ bảng sao kê
- Phân tích xu hướng chi tiêu và dòng tiền
- Phát hiện bất thường trong giao dịch
- Đảm bảo tuân thủ quy định bảo mật dữ liệu ngân hàng

## Cấu trúc tài liệu

```
docs/banking-data-mining/
├── README.md                          # Tổng quan (file này)
├── 01-document-types.md               # Các loại tài liệu ngân hàng
├── 02-extraction-schemas.md           # Schema trích xuất dữ liệu
├── 03-workflows.md                    # Workflow xử lý banking
├── 04-transaction-categorization.md   # Phân loại giao dịch
├── 05-analytics-aggregation.md        # Phân tích & tổng hợp dữ liệu
├── 06-compliance-security.md          # Bảo mật & tuân thủ
└── 07-implementation-roadmap.md       # Lộ trình triển khai
```

## Kiến trúc tổng quan

```
┌─────────────────────────────────────────────────────────┐
│                    Banking Data Mining                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐            │
│  │  Upload  │──▶│   OCR    │──▶│ Classify │            │
│  │  (PDF/   │   │ (Parse)  │   │ Doc Type │            │
│  │  Image)  │   └──────────┘   └────┬─────┘            │
│  └──────────┘                        │                   │
│                                      ▼                   │
│  ┌──────────────────────────────────────────────┐       │
│  │              Extraction Layer                  │       │
│  │  ┌────────────┐  ┌────────────┐  ┌────────┐ │       │
│  │  │  Header    │  │Transaction │  │Summary │ │       │
│  │  │  Fields    │  │  Line Items│  │ Fields │ │       │
│  │  └────────────┘  └────────────┘  └────────┘ │       │
│  └──────────────────────────────────────────────┘       │
│                          │                               │
│                          ▼                               │
│  ┌──────────────────────────────────────────────┐       │
│  │            Analytics Layer                     │       │
│  │  ┌──────────┐  ┌──────────┐  ┌───────────┐  │       │
│  │  │Categorize│  │ Anomaly  │  │ Aggregate │  │       │
│  │  │  Txns    │  │ Detect   │  │ & Report  │  │       │
│  │  └──────────┘  └──────────┘  └───────────┘  │       │
│  └──────────────────────────────────────────────┘       │
│                          │                               │
│                          ▼                               │
│  ┌──────────────────────────────────────────────┐       │
│  │              Export Layer                      │       │
│  │  CSV / Excel / JSON / Database Integration    │       │
│  └──────────────────────────────────────────────┘       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Công nghệ sử dụng

| Thành phần | Công nghệ | Mục đích |
|---|---|---|
| OCR Engine | Google Gemini 2.5 Flash | Trích xuất text từ PDF/ảnh |
| Classification | Claude Sonnet (Bedrock) | Phân loại tài liệu |
| Extraction | Claude Sonnet / Gemini Pro | Trích xuất dữ liệu có cấu trúc |
| Analytics | Python (pandas, numpy) | Phân tích & tổng hợp |
| Export | openpyxl, csv | Xuất báo cáo |
| Storage | SQLite / PostgreSQL | Lưu trữ kết quả |

## Bắt đầu nhanh

1. Upload tài liệu ngân hàng (PDF/ảnh)
2. Hệ thống tự động phân loại loại tài liệu
3. Trích xuất dữ liệu theo schema tương ứng
4. Xem kết quả phân tích và xuất báo cáo

Xem chi tiết từng phần trong các tài liệu con.
