# 03 - Workflow Xử Lý Banking

## Tổng quan

Workflow là chuỗi các bước xử lý tuần tự, cho phép tự động hóa toàn bộ quy trình khai thác dữ liệu từ tài liệu ngân hàng. Mỗi workflow được định nghĩa dưới dạng JSON và thực thi qua API `/workflow/execute`.

## Workflow Templates

### 1. Full Bank Statement Mining

Quy trình đầy đủ: OCR → Phân loại → Trích xuất header → Trích xuất giao dịch

```json
{
  "name": "full_bank_statement_mining",
  "description": "Khai thác toàn bộ dữ liệu từ sao kê ngân hàng",
  "steps": [
    {
      "type": "parse",
      "tier": "Advance",
      "config": {
        "description": "OCR với model chất lượng cao cho tài liệu ngân hàng"
      }
    },
    {
      "type": "classify",
      "tier": "Normal",
      "config": {
        "rules": [
          {"doc_type": "bank_statement", "description": "Sao kê tài khoản ngân hàng"},
          {"doc_type": "credit_card_statement", "description": "Sao kê thẻ tín dụng"},
          {"doc_type": "transfer_confirmation", "description": "Biên lai chuyển khoản"},
          {"doc_type": "other", "description": "Tài liệu khác không thuộc các loại trên"}
        ]
      }
    },
    {
      "type": "extract",
      "tier": "Advance",
      "config": {
        "target": "document",
        "schema": {
          "fields": [
            {"name": "bank_name", "type": "string", "description": "Tên ngân hàng", "required": true},
            {"name": "account_number", "type": "string", "description": "Số tài khoản", "required": true},
            {"name": "account_holder", "type": "string", "description": "Chủ tài khoản", "required": true},
            {"name": "currency", "type": "string", "description": "Đơn vị tiền tệ", "required": true},
            {"name": "statement_period_start", "type": "date", "description": "Ngày bắt đầu kỳ", "required": true},
            {"name": "statement_period_end", "type": "date", "description": "Ngày kết thúc kỳ", "required": true},
            {"name": "opening_balance", "type": "number", "description": "Số dư đầu kỳ", "required": true},
            {"name": "closing_balance", "type": "number", "description": "Số dư cuối kỳ", "required": true},
            {"name": "total_credit", "type": "number", "description": "Tổng ghi có", "required": false},
            {"name": "total_debit", "type": "number", "description": "Tổng ghi nợ", "required": false}
          ]
        }
      }
    },
    {
      "type": "extract",
      "tier": "Advance",
      "config": {
        "target": "table_row",
        "schema": {
          "fields": [
            {"name": "transaction_date", "type": "date", "description": "Ngày giao dịch", "required": true},
            {"name": "description", "type": "string", "description": "Nội dung giao dịch", "required": true},
            {"name": "debit_amount", "type": "number", "description": "Số tiền ghi nợ", "required": false},
            {"name": "credit_amount", "type": "number", "description": "Số tiền ghi có", "required": false},
            {"name": "balance", "type": "number", "description": "Số dư", "required": false},
            {"name": "reference_number", "type": "string", "description": "Mã tham chiếu", "required": false}
          ]
        }
      }
    }
  ]
}
```

---

### 2. KYC Document Processing

Quy trình xác minh danh tính khách hàng.

```json
{
  "name": "kyc_processing",
  "description": "Trích xuất thông tin từ giấy tờ tùy thân",
  "steps": [
    {
      "type": "parse",
      "tier": "Advance",
      "config": {
        "description": "OCR chất lượng cao cho giấy tờ tùy thân"
      }
    },
    {
      "type": "classify",
      "tier": "Normal",
      "config": {
        "rules": [
          {"doc_type": "cmnd", "description": "Chứng minh nhân dân (9 số hoặc 12 số)"},
          {"doc_type": "cccd", "description": "Căn cước công dân (có chip hoặc không chip)"},
          {"doc_type": "passport", "description": "Hộ chiếu Việt Nam hoặc quốc tế"},
          {"doc_type": "driving_license", "description": "Giấy phép lái xe"},
          {"doc_type": "business_license", "description": "Giấy phép đăng ký kinh doanh"}
        ]
      }
    },
    {
      "type": "extract",
      "tier": "Advance",
      "config": {
        "target": "document",
        "schema": {
          "fields": [
            {"name": "document_type", "type": "string", "required": true},
            {"name": "document_number", "type": "string", "required": true},
            {"name": "full_name", "type": "string", "required": true},
            {"name": "date_of_birth", "type": "date", "required": true},
            {"name": "gender", "type": "string", "required": false},
            {"name": "permanent_address", "type": "string", "required": false},
            {"name": "issue_date", "type": "date", "required": true},
            {"name": "expiry_date", "type": "date", "required": false},
            {"name": "issuing_authority", "type": "string", "required": false}
          ]
        }
      }
    }
  ]
}
```

---

### 3. Loan Document Analysis

Phân tích hợp đồng vay vốn.

```json
{
  "name": "loan_analysis",
  "description": "Trích xuất thông tin từ hợp đồng tín dụng",
  "steps": [
    {
      "type": "parse",
      "tier": "Advance",
      "config": {}
    },
    {
      "type": "extract",
      "tier": "Advance",
      "config": {
        "target": "document",
        "schema": {
          "fields": [
            {"name": "contract_number", "type": "string", "required": true},
            {"name": "contract_date", "type": "date", "required": true},
            {"name": "lender_name", "type": "string", "required": true},
            {"name": "borrower_name", "type": "string", "required": true},
            {"name": "loan_amount", "type": "number", "required": true},
            {"name": "currency", "type": "string", "required": true},
            {"name": "interest_rate", "type": "number", "required": true},
            {"name": "interest_type", "type": "string", "required": false},
            {"name": "loan_term_months", "type": "number", "required": true},
            {"name": "maturity_date", "type": "date", "required": true},
            {"name": "repayment_method", "type": "string", "required": false},
            {"name": "collateral_description", "type": "string", "required": false},
            {"name": "collateral_value", "type": "number", "required": false},
            {"name": "loan_purpose", "type": "string", "required": false}
          ]
        }
      }
    }
  ]
}
```

---

### 4. Credit Card Statement Mining

Khai thác dữ liệu chi tiêu thẻ tín dụng.

```json
{
  "name": "credit_card_mining",
  "description": "Trích xuất chi tiêu từ sao kê thẻ tín dụng",
  "steps": [
    {
      "type": "parse",
      "tier": "Advance",
      "config": {}
    },
    {
      "type": "extract",
      "tier": "Advance",
      "config": {
        "target": "document",
        "schema": {
          "fields": [
            {"name": "card_number_masked", "type": "string", "required": true},
            {"name": "card_holder", "type": "string", "required": true},
            {"name": "statement_date", "type": "date", "required": true},
            {"name": "payment_due_date", "type": "date", "required": true},
            {"name": "credit_limit", "type": "number", "required": false},
            {"name": "current_balance", "type": "number", "required": true},
            {"name": "minimum_payment", "type": "number", "required": true},
            {"name": "new_charges", "type": "number", "required": true}
          ]
        }
      }
    },
    {
      "type": "extract",
      "tier": "Advance",
      "config": {
        "target": "table_row",
        "schema": {
          "fields": [
            {"name": "transaction_date", "type": "date", "required": true},
            {"name": "merchant_name", "type": "string", "required": true},
            {"name": "amount_billed", "type": "number", "required": true},
            {"name": "original_currency", "type": "string", "required": false},
            {"name": "amount_original", "type": "number", "required": false},
            {"name": "transaction_type", "type": "string", "required": false}
          ]
        }
      }
    }
  ]
}
```

---

### 5. Multi-Document Batch Processing

Xử lý hàng loạt nhiều tài liệu (sử dụng async job API).

```json
{
  "name": "batch_banking_processing",
  "description": "Xử lý hàng loạt tài liệu ngân hàng với phân loại tự động",
  "batch_config": {
    "max_concurrent": 5,
    "retry_on_failure": true,
    "max_retries": 2
  },
  "steps": [
    {
      "type": "parse",
      "tier": "Normal",
      "config": {}
    },
    {
      "type": "classify",
      "tier": "Normal",
      "config": {
        "rules": [
          {"doc_type": "bank_statement", "description": "Sao kê tài khoản"},
          {"doc_type": "credit_card_statement", "description": "Sao kê thẻ tín dụng"},
          {"doc_type": "loan_agreement", "description": "Hợp đồng vay"},
          {"doc_type": "transfer_confirmation", "description": "Biên lai chuyển khoản"},
          {"doc_type": "kyc_document", "description": "Giấy tờ tùy thân"},
          {"doc_type": "financial_report", "description": "Báo cáo tài chính"},
          {"doc_type": "other", "description": "Tài liệu khác"}
        ]
      }
    }
  ],
  "conditional_steps": {
    "bank_statement": [
      {"type": "extract", "tier": "Advance", "config": {"schema": "bank_statement_header"}},
      {"type": "extract", "tier": "Advance", "config": {"schema": "bank_statement_transactions"}}
    ],
    "credit_card_statement": [
      {"type": "extract", "tier": "Advance", "config": {"schema": "credit_card_header"}},
      {"type": "extract", "tier": "Advance", "config": {"schema": "credit_card_transactions"}}
    ],
    "loan_agreement": [
      {"type": "extract", "tier": "Advance", "config": {"schema": "loan_agreement"}}
    ]
  }
}
```

---

## Workflow Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Workflow Execution                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Upload File                                              │
│     │                                                        │
│     ▼                                                        │
│  2. Parse (OCR)                                              │
│     │  Output: raw text                                      │
│     ▼                                                        │
│  3. Classify                                                 │
│     │  Output: document_type + confidence                    │
│     ▼                                                        │
│  4. Condition Evaluate                                       │
│     │  Route to appropriate extraction schema                │
│     ├──▶ bank_statement → Schema A                          │
│     ├──▶ credit_card   → Schema B                           │
│     ├──▶ loan          → Schema C                           │
│     └──▶ other         → Generic schema                     │
│                                                              │
│  5. Extract (Header)                                         │
│     │  Output: structured header data                        │
│     ▼                                                        │
│  6. Extract (Transactions)                                   │
│     │  Output: array of transaction objects                  │
│     ▼                                                        │
│  7. Post-Processing                                          │
│     │  - Validate totals                                     │
│     │  - Categorize transactions                             │
│     │  - Flag anomalies                                      │
│     ▼                                                        │
│  8. Export / Store                                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Condition Evaluation

Sử dụng endpoint `/condition/evaluate` để routing dựa trên kết quả phân loại:

```bash
curl -X POST http://localhost:8000/api/v1/condition/evaluate \
  -F 'conditions=[
    {"operator": "equals", "value": "bank_statement"},
    {"operator": "equals", "value": "credit_card_statement"},
    {"operator": "equals", "value": "loan_agreement"}
  ]' \
  -F 'previous_result={"document_type": "bank_statement", "confidence": 0.95}' \
  -F 'field_name=document_type'
```

Response:
```json
{
  "success": true,
  "matched_index": 0,
  "is_else": false
}
```

## Error Handling

| Lỗi | Nguyên nhân | Xử lý |
|---|---|---|
| `parse_failed` | OCR không đọc được file | Thử tier cao hơn hoặc kiểm tra chất lượng file |
| `classify_failed` | Không phân loại được | Sử dụng schema generic |
| `extract_failed` | Trích xuất thất bại | Retry với prompt khác hoặc model mạnh hơn |
| `validation_error` | Dữ liệu không hợp lệ | Log warning, trả về partial result |
| `timeout` | Quá thời gian xử lý | Chuyển sang async job |

## Best Practices

1. **Luôn dùng tier Advance cho tài liệu ngân hàng** — Độ chính xác quan trọng hơn tốc độ
2. **Validate kết quả** — So sánh tổng giao dịch với opening/closing balance
3. **Xử lý multi-page** — Sao kê dài cần split trước khi extract transactions
4. **Retry logic** — Nếu extraction thất bại, thử lại với prompt cụ thể hơn
5. **Batch processing** — Dùng async job cho > 10 tài liệu
