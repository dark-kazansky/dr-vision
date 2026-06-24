# Phase 1: Foundation — Tài Liệu Triển Khai Chi Tiết

## 1. Tổng Quan

### Mục tiêu Phase 1

Xây dựng **configuration layer** để hệ thống Doc Intelligence có thể xử lý sao kê ngân hàng end-to-end. Vì core pipeline (OCR → Classification → Extraction) đã hoàn chỉnh ở mức 80%, Phase 1 chủ yếu là **định nghĩa schemas, rules và workflow templates** — không cần viết logic xử lý mới.

### Deliverables

| # | Deliverable | Trạng thái |
|---|---|---|
| D1 | File `backend/config/banking_schemas.py` chứa tất cả config banking | ✅ Done |
| D2 | Classification rules cho 10 loại tài liệu ngân hàng | ✅ Done |
| D3 | Extraction schemas cho 5 loại tài liệu chính (7 schemas) | ✅ Done |
| D4 | Schema Registry với auto-routing theo document type | ✅ Done |
| D5 | 5 Workflow templates sẵn dùng | ✅ Done |
| D6 | Vietnamese-optimized extraction prompts | ✅ Done |
| D7 | Export module qua `config/__init__.py` | ✅ Done |
| D8 | Test accuracy với sao kê thực tế (VCB, BIDV, TCB) | ⏳ Pending |

---

## 2. Kiến Trúc Triển Khai

### Vị trí trong hệ thống

```
┌───────────────────────────────────────────────────────────────┐
│                     Doc Intelligence Backend                          │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│  api/v1/                                                       │
│  ├── parse.py          POST /parse        ── OCR từ file ──┐  │
│  ├── classify.py       POST /classify     ── Phân loại   ──┤  │
│  ├── extract.py        POST /extract      ── Trích xuất  ──┤  │
│  └── workflow.py       POST /workflow/execute ── Pipeline ──┘  │
│         │                                                      │
│         │ Sử dụng schemas từ                                   │
│         ▼                                                      │
│  config/                                                       │
│  ├── banking_schemas.py    ◄── [NEW] Tất cả config banking    │
│  ├── tier_config.py            Model mappings (existing)       │
│  ├── manager.py                Settings loader (existing)      │
│  └── __init__.py           ◄── [UPDATED] Export banking utils  │
│                                                                │
│  components/               Existing - không thay đổi           │
│  ├── classifier.py         Dùng BANKING_CLASSIFICATION_RULES   │
│  ├── extractor.py          Dùng BANK_STATEMENT_*_SCHEMA        │
│  └── parser.py             OCR engine                          │
│                                                                │
└───────────────────────────────────────────────────────────────┘
```

### Files đã tạo / sửa đổi

| File | Hành động | Dòng code | Mô tả |
|---|---|---|---|
| `backend/config/banking_schemas.py` | **NEW** | 449 | Config trung tâm cho banking domain |
| `backend/config/__init__.py` | **MODIFIED** | 25 | Thêm export cho banking utilities |

---

## 3. Chi Tiết `banking_schemas.py`

### 3.1 Classification Rules

Định nghĩa **10 loại tài liệu ngân hàng** để sử dụng với `POST /classify`:

```python
from config.banking_schemas import BANKING_CLASSIFICATION_RULES

# Danh sách 10 doc_types:
# bank_statement, credit_card_statement, loan_agreement, kyc_document,
# check_deposit, transfer_confirmation, financial_report,
# insurance_document, mortgage_document, tax_document
```

Mỗi rule có `doc_type` (mã) và `description` (mô tả tiếng Việt để AI phân loại chính xác hơn).

### 3.2 Extraction Schemas

Tổng cộng **7 schemas** cho 5 loại tài liệu chính:

| Schema Constant | Doc Type | Target | Fields | Mô tả |
|---|---|---|---|---|
| `BANK_STATEMENT_HEADER_SCHEMA` | bank_statement | `document` | 13 | Thông tin chung: bank, TK, số dư, kỳ sao kê |
| `BANK_STATEMENT_TRANSACTION_SCHEMA` | bank_statement | `table_row` | 11 | Từng dòng giao dịch: date, amount, balance |
| `CREDIT_CARD_HEADER_SCHEMA` | credit_card_statement | `document` | 15 | Thẻ tín dụng: card, limit, due date |
| `CREDIT_CARD_TRANSACTION_SCHEMA` | credit_card_statement | `table_row` | 8 | Chi tiêu thẻ: merchant, amount, currency |
| `LOAN_AGREEMENT_SCHEMA` | loan_agreement | `document` | 16 | Hợp đồng vay: amount, rate, term, collateral |
| `TRANSFER_CONFIRMATION_SCHEMA` | transfer_confirmation | `document` | 12 | Chuyển khoản: sender, receiver, amount |
| `KYC_DOCUMENT_SCHEMA` | kyc_document | `document` | 11 | CMND/CCCD: name, DOB, ID number |

#### Chi tiết fields — Bank Statement Header (13 fields)

| Field | Type | Required | Mô tả |
|---|---|---|---|
| `bank_name` | string | ✅ | Tên ngân hàng |
| `branch_name` | string | | Chi nhánh |
| `account_number` | string | ✅ | Số tài khoản (giữ format gốc) |
| `account_holder` | string | ✅ | Tên chủ TK |
| `account_type` | string | | thanh toán/tiết kiệm/vãng lai |
| `currency` | string | ✅ | VND, USD, EUR |
| `statement_period_start` | date | ✅ | Ngày bắt đầu kỳ |
| `statement_period_end` | date | ✅ | Ngày kết thúc kỳ |
| `opening_balance` | number | ✅ | Số dư đầu kỳ |
| `closing_balance` | number | ✅ | Số dư cuối kỳ |
| `total_credit` | number | | Tổng ghi có |
| `total_debit` | number | | Tổng ghi nợ |
| `transaction_count` | number | | Số lượng giao dịch |

#### Chi tiết fields — Bank Statement Transactions (11 fields)

| Field | Type | Required | Mô tả |
|---|---|---|---|
| `transaction_date` | date | ✅ | Ngày giao dịch |
| `value_date` | date | | Ngày hiệu lực |
| `description` | string | ✅ | Nội dung giao dịch |
| `reference_number` | string | | Mã tham chiếu |
| `debit_amount` | number | | Tiền ra (null nếu credit) |
| `credit_amount` | number | | Tiền vào (null nếu debit) |
| `balance` | number | | Số dư sau GD |
| `transaction_type` | string | | transfer/payment/withdrawal/... |
| `counterparty` | string | | Tên đối tác |
| `counterparty_account` | string | | TK đối tác |
| `counterparty_bank` | string | | NH đối tác |

### 3.3 Schema Registry

Auto-routing từ kết quả classification sang extraction schema phù hợp:

```python
from config.banking_schemas import get_schema_for_doc_type

# Sau khi classify → "bank_statement":
schemas = get_schema_for_doc_type("bank_statement")
# → {"header": {target: "document", fields: [...]},
#    "transactions": {target: "table_row", fields: [...]}}

# Sau khi classify → "loan_agreement":
schemas = get_schema_for_doc_type("loan_agreement")
# → {"document": {target: "document", fields: [...]}}

# Doc type không hỗ trợ:
schemas = get_schema_for_doc_type("unknown_type")
# → None
```

### 3.4 Workflow Templates

5 pipeline workflows sẵn dùng:

| Template | Steps | Mô tả |
|---|---|---|
| `full_bank_statement_mining` | parse → classify → extract header → extract transactions | Khai thác toàn bộ sao kê |
| `credit_card_mining` | parse → extract header → extract transactions | Khai thác thẻ tín dụng |
| `kyc_processing` | parse → classify (5 subtypes) → extract | Xác minh danh tính |
| `loan_analysis` | parse → extract | Phân tích hợp đồng vay |
| `transfer_confirmation` | parse → extract | Trích xuất biên lai CK |

```python
from config.banking_schemas import get_workflow_template, list_workflow_templates

# Liệt kê:
for t in list_workflow_templates():
    print(f"{t['name']}: {t['description']}")

# Lấy workflow để gửi qua API:
workflow = get_workflow_template("full_bank_statement_mining")
# → Dùng trực tiếp với POST /workflow/execute
```

### 3.5 Vietnamese Extraction Prompts

Prompts đặc biệt cho tài liệu tiếng Việt:

| Key | Quy tắc |
|---|---|
| `bank_statement_header` | Số tiền không dấu chấm phân cách; mặc định VND |
| `bank_statement_transactions` | Debit = tiền ra, Credit = tiền vào; null ≠ 0 |
| `credit_card` | Số thẻ giữ masked; phân biệt ngoại tệ vs VND |
| `kyc` | Họ tên viết HOA; CMND/CCCD giữ format gốc |

### 3.6 Supported Banks

10 ngân hàng Việt Nam:

| Code | Ngân hàng | Formats |
|---|---|---|
| VCB | Vietcombank | PDF |
| BIDV | BIDV | PDF, Excel |
| CTG | VietinBank | PDF |
| TCB | Techcombank | PDF, Image |
| MBB | MB Bank | PDF |
| ACB | ACB | PDF |
| VPB | VPBank | PDF |
| TPB | TPBank | PDF, Image |
| STB | Sacombank | PDF |
| HDB | HDBank | PDF |

---

## 4. Hướng Dẫn Sử Dụng API

### 4.1 Trích xuất header sao kê ngân hàng

```bash
curl -X POST http://localhost:8000/api/v1/extract \
  -F "file=@vcb_statement.pdf" \
  -F "tier=Advance" \
  -F "target=document" \
  -F 'schema=[
    {"name":"bank_name","type":"string","required":true},
    {"name":"account_number","type":"string","required":true},
    {"name":"account_holder","type":"string","required":true},
    {"name":"currency","type":"string","required":true},
    {"name":"statement_period_start","type":"date","required":true},
    {"name":"statement_period_end","type":"date","required":true},
    {"name":"opening_balance","type":"number","required":true},
    {"name":"closing_balance","type":"number","required":true}
  ]'
```

**Response mẫu:**

```json
{
  "success": true,
  "structured_data": {
    "bank_name": "Ngân hàng TMCP Ngoại thương Việt Nam",
    "account_number": "0011004567890",
    "account_holder": "NGUYEN VAN A",
    "currency": "VND",
    "statement_period_start": "2025-04-01",
    "statement_period_end": "2025-04-30",
    "opening_balance": 45000000,
    "closing_balance": 52300000
  },
  "field_errors": null,
  "filename": "vcb_statement.pdf"
}
```

### 4.2 Trích xuất danh sách giao dịch

```bash
curl -X POST http://localhost:8000/api/v1/extract \
  -F "file=@vcb_statement.pdf" \
  -F "tier=Advance" \
  -F "target=table_row" \
  -F 'schema=[
    {"name":"transaction_date","type":"date","required":true},
    {"name":"description","type":"string","required":true},
    {"name":"debit_amount","type":"number","required":false},
    {"name":"credit_amount","type":"number","required":false},
    {"name":"balance","type":"number","required":false}
  ]'
```

**Response mẫu:**

```json
{
  "success": true,
  "structured_data": [
    {
      "transaction_date": "2025-04-01",
      "description": "LUONG T04/2025 - CONG TY ABC",
      "debit_amount": null,
      "credit_amount": 35000000,
      "balance": 80000000
    },
    {
      "transaction_date": "2025-04-02",
      "description": "CK CHO NGUYEN THI B - TIEN THUE NHA",
      "debit_amount": 8000000,
      "credit_amount": null,
      "balance": 72000000
    },
    {
      "transaction_date": "2025-04-03",
      "description": "THANH TOAN THE - GRAB",
      "debit_amount": 85000,
      "credit_amount": null,
      "balance": 71915000
    }
  ],
  "field_errors": null
}
```

### 4.3 Phân loại tài liệu ngân hàng

```bash
curl -X POST http://localhost:8000/api/v1/classify \
  -F "file=@unknown_doc.pdf" \
  -F "tier=Normal" \
  -F 'rules=[
    {"doc_type":"bank_statement","description":"Sao kê tài khoản ngân hàng hàng tháng với danh sách giao dịch, số dư đầu/cuối kỳ"},
    {"doc_type":"credit_card_statement","description":"Bảng kê chi tiêu thẻ tín dụng với thông tin merchant, dư nợ, hạn mức"},
    {"doc_type":"loan_agreement","description":"Hợp đồng tín dụng/vay vốn với lãi suất, kỳ hạn, lịch trả nợ"},
    {"doc_type":"transfer_confirmation","description":"Biên lai xác nhận chuyển khoản với mã giao dịch, TK nguồn/đích"},
    {"doc_type":"kyc_document","description":"Giấy tờ tùy thân (CMND, CCCD, hộ chiếu)"}
  ]'
```

**Response mẫu:**

```json
{
  "success": true,
  "results": [{
    "documentType": "bank_statement",
    "confidence": 0.95,
    "reasoning": "Tài liệu chứa logo ngân hàng, bảng giao dịch với cột Nợ/Có, số dư đầu kỳ và cuối kỳ"
  }]
}
```

### 4.4 Full workflow pipeline

```bash
curl -X POST http://localhost:8000/api/v1/workflow/execute \
  -F "file=@vcb_statement.pdf" \
  -F 'workflow={
    "steps": [
      {"type":"parse","tier":"Advance","config":{}},
      {"type":"classify","tier":"Normal","config":{
        "rules":[
          {"doc_type":"bank_statement","description":"Sao kê tài khoản ngân hàng"},
          {"doc_type":"credit_card_statement","description":"Sao kê thẻ tín dụng"},
          {"doc_type":"other","description":"Tài liệu khác"}
        ]
      }},
      {"type":"extract","tier":"Advance","config":{
        "target":"document",
        "schema":{"fields":[
          {"name":"bank_name","type":"string","required":true},
          {"name":"account_number","type":"string","required":true},
          {"name":"opening_balance","type":"number","required":true},
          {"name":"closing_balance","type":"number","required":true}
        ]}
      }},
      {"type":"extract","tier":"Advance","config":{
        "target":"table_row",
        "schema":{"fields":[
          {"name":"transaction_date","type":"date","required":true},
          {"name":"description","type":"string","required":true},
          {"name":"debit_amount","type":"number","required":false},
          {"name":"credit_amount","type":"number","required":false},
          {"name":"balance","type":"number","required":false}
        ]}
      }}
    ]
  }'
```

### 4.5 Sử dụng programmatic (Python)

```python
from config.banking_schemas import (
    BANKING_CLASSIFICATION_RULES,
    get_schema_for_doc_type,
    get_workflow_template,
    list_workflow_templates,
)

# 1. Xem danh sách workflow templates
for t in list_workflow_templates():
    print(f"  {t['name']}: {t['description']}")

# 2. Lấy workflow cho sao kê ngân hàng
workflow = get_workflow_template("full_bank_statement_mining")
print(f"Steps: {len(workflow['steps'])}")
for step in workflow["steps"]:
    print(f"  → {step['type']} (tier: {step['tier']})")

# 3. Auto-routing: classify rồi lấy schema phù hợp
doc_type = "bank_statement"  # Từ kết quả classify
schemas = get_schema_for_doc_type(doc_type)
if schemas:
    for schema_name, schema_def in schemas.items():
        print(f"  {schema_name}: target={schema_def['target']}, "
              f"fields={len(schema_def['fields'])}")
```

---

## 5. Quy Tắc Xử Lý Dữ Liệu Tiếng Việt

### Số tiền

- Không dùng dấu chấm/phẩy phân cách: `15000000` ✅, `15.000.000` ❌
- Đơn vị mặc định là `VND` nếu không ghi rõ
- `debit_amount = null` khi giao dịch là credit (không phải `0`)

### Ngày tháng

- Format chuẩn: `YYYY-MM-DD`
- Hệ thống hỗ trợ parse 8+ date formats (dd/mm/yyyy, mm/dd/yyyy, ...)

### Text

- Giữ nguyên tiếng Việt trong `description`
- Họ tên viết HOA đúng theo tài liệu gốc
- Số tài khoản, số CMND/CCCD giữ nguyên format

---

## 6. Validation & Testing

### Tiêu chí đánh giá

| Metric | Mục tiêu | Công thức |
|---|---|---|
| Header accuracy | > 90% | Số fields đúng / tổng required fields |
| Transaction accuracy | > 80% | Số dòng GD trích xuất đúng / tổng dòng thực |
| Balance validation | 100% | `opening + Σcredit - Σdebit == closing` |
| Date parsing rate | > 95% | Số dates parse thành công / tổng date fields |
| Processing time | < 30s | Thời gian xử lý 1 trang sao kê |

### Test matrix

| Ngân hàng | Format | Header | Transactions | Ghi chú |
|---|---|---|---|---|
| Vietcombank (VCB) | PDF | ☐ | ☐ | Ưu tiên test đầu tiên |
| BIDV | PDF | ☐ | ☐ | |
| Techcombank (TCB) | PDF | ☐ | ☐ | |
| VietinBank (CTG) | PDF | ☐ | ☐ | |
| MB Bank (MBB) | PDF | ☐ | ☐ | |

### Script validate kết quả

```python
def validate_statement_result(header, transactions):
    """Kiểm tra tính nhất quán của dữ liệu trích xuất."""
    errors = []

    # 1. Required fields phải có giá trị
    required = ["bank_name", "account_number", "account_holder",
                "opening_balance", "closing_balance"]
    for field in required:
        if not header.get(field):
            errors.append(f"Missing required field: {field}")

    # 2. Balance validation
    if transactions and header.get("opening_balance") is not None:
        total_credit = sum(t.get("credit_amount", 0) or 0 for t in transactions)
        total_debit = sum(t.get("debit_amount", 0) or 0 for t in transactions)
        expected_closing = header["opening_balance"] + total_credit - total_debit

        if abs(expected_closing - header.get("closing_balance", 0)) > 1:
            errors.append(
                f"Balance mismatch: "
                f"opening({header['opening_balance']}) + "
                f"credit({total_credit}) - debit({total_debit}) = "
                f"{expected_closing} != closing({header['closing_balance']})"
            )

    # 3. Mỗi transaction phải có date và description
    for i, txn in enumerate(transactions):
        if not txn.get("transaction_date"):
            errors.append(f"Transaction #{i+1}: missing date")
        if not txn.get("description"):
            errors.append(f"Transaction #{i+1}: missing description")
        if not txn.get("debit_amount") and not txn.get("credit_amount"):
            errors.append(f"Transaction #{i+1}: no amount (both debit and credit are null)")

    return {"valid": len(errors) == 0, "errors": errors}
```

---

## 7. Sơ Đồ Luồng Xử Lý

```
                        Upload PDF/Image
                              │
                              ▼
                    ┌───────────────────┐
                    │   POST /parse     │  OCR (tier: Advance)
                    │   Parser component│  → Raw text
                    └────────┬──────────┘
                             │
                             ▼
                    ┌───────────────────┐
                    │  POST /classify   │  Phân loại tài liệu
                    │  Classifier comp. │  → doc_type + confidence
                    │  Dùng: BANKING_   │
                    │  CLASSIFICATION_  │
                    │  RULES            │
                    └────────┬──────────┘
                             │
                    ┌────────┴────────────────────┐
                    │                              │
            bank_statement              credit_card_statement
                    │                              │
                    ▼                              ▼
        ┌───────────────────┐          ┌───────────────────┐
        │ Extract Header    │          │ Extract CC Header │
        │ target: document  │          │ target: document  │
        │ 13 fields         │          │ 15 fields         │
        └────────┬──────────┘          └────────┬──────────┘
                 │                              │
                 ▼                              ▼
        ┌───────────────────┐          ┌───────────────────┐
        │ Extract Txns      │          │ Extract CC Txns   │
        │ target: table_row │          │ target: table_row │
        │ 11 fields/row     │          │ 8 fields/row      │
        └────────┬──────────┘          └────────┬──────────┘
                 │                              │
                 └──────────┬───────────────────┘
                            ▼
                    ┌───────────────────┐
                    │  Structured JSON  │
                    │  {header, txns[]} │
                    └───────────────────┘
```

---

## 8. Lưu Ý Kỹ Thuật

### Tương thích với hệ thống hiện có

- **Không thay đổi** bất kỳ component nào (Parser, Classifier, Extractor)
- **Không thay đổi** API endpoints — dùng đúng API hiện có
- **Không thêm** dependencies mới
- Chỉ thêm **configuration data** dưới dạng Python dict/list

### Tier khuyến nghị cho banking

| Bước | Tier | Lý do |
|---|---|---|
| Parse (OCR) | **Advance** | Sao kê ngân hàng có bảng phức tạp, cần OCR chất lượng cao |
| Classify | **Normal** | Phân loại tài liệu không cần model mạnh nhất |
| Extract | **Advance** | Trích xuất số liệu tài chính cần độ chính xác cao |

### Model mapping hiện tại (tier_config.py)

| Tier | Provider | Model |
|---|---|---|
| Rapid | LM Studio | `lightonocr-2-1b` |
| Normal | AWS Bedrock | `claude-haiku` |
| Advance | AWS Bedrock | `claude-sonnet` |

---

## 9. Bước Tiếp Theo — Chuẩn Bị Phase 2

Sau khi hoàn thành testing Phase 1:

1. **Transaction Categorizer** — Phân loại giao dịch theo danh mục chi tiêu (rule-based + LLM hybrid)
2. **Merchant Database** — 100+ merchants Việt Nam (Grab, Shopee, VinMart, ...)
3. **Banking Analytics Service** — Phân tích dòng tiền, cơ cấu chi tiêu
4. **Banking API endpoints** — `POST /banking/process`, `GET /banking/analytics`
5. **CSV Export** — Xuất giao dịch đã phân loại
