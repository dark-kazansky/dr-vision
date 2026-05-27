# 02 - Schema Trích Xuất Dữ Liệu

## Tổng quan

Mỗi loại tài liệu ngân hàng có schema trích xuất riêng, định nghĩa các trường dữ liệu cần khai thác. Schema sử dụng cấu trúc `ExtractionConfig` của Dr.Vision.

## Field Types

| Type | Mô tả | Ví dụ |
|---|---|---|
| `string` | Chuỗi ký tự | Tên ngân hàng, số tài khoản |
| `number` | Số (integer/float) | Số tiền, lãi suất |
| `date` | Ngày tháng | Ngày giao dịch, ngày phát hành |
| `boolean` | True/False | Có tài sản đảm bảo hay không |

## Extraction Targets

| Target | Mô tả | Use case |
|---|---|---|
| `document` | Trích xuất từ toàn bộ tài liệu | Header info, summary |
| `page` | Trích xuất theo từng trang | Multi-page statements |
| `table_row` | Trích xuất từng dòng bảng | Transaction line items |

---

## Schema 1: Sao kê tài khoản (Bank Statement)

### Header Fields (target: `document`)

```json
{
  "target": "document",
  "fields": [
    {
      "name": "bank_name",
      "type": "string",
      "description": "Tên ngân hàng phát hành sao kê",
      "required": true
    },
    {
      "name": "branch_name",
      "type": "string",
      "description": "Tên chi nhánh/phòng giao dịch",
      "required": false
    },
    {
      "name": "account_number",
      "type": "string",
      "description": "Số tài khoản (giữ nguyên format gốc)",
      "required": true
    },
    {
      "name": "account_holder",
      "type": "string",
      "description": "Tên chủ tài khoản",
      "required": true
    },
    {
      "name": "account_type",
      "type": "string",
      "description": "Loại tài khoản (thanh toán/tiết kiệm/vãng lai)",
      "required": false
    },
    {
      "name": "currency",
      "type": "string",
      "description": "Đơn vị tiền tệ (VND, USD, EUR)",
      "required": true
    },
    {
      "name": "statement_period_start",
      "type": "date",
      "description": "Ngày bắt đầu kỳ sao kê",
      "required": true
    },
    {
      "name": "statement_period_end",
      "type": "date",
      "description": "Ngày kết thúc kỳ sao kê",
      "required": true
    },
    {
      "name": "opening_balance",
      "type": "number",
      "description": "Số dư đầu kỳ",
      "required": true
    },
    {
      "name": "closing_balance",
      "type": "number",
      "description": "Số dư cuối kỳ",
      "required": true
    },
    {
      "name": "total_credit",
      "type": "number",
      "description": "Tổng tiền ghi có (tiền vào)",
      "required": false
    },
    {
      "name": "total_debit",
      "type": "number",
      "description": "Tổng tiền ghi nợ (tiền ra)",
      "required": false
    },
    {
      "name": "transaction_count",
      "type": "number",
      "description": "Tổng số giao dịch trong kỳ",
      "required": false
    }
  ]
}
```

### Transaction Line Items (target: `table_row`)

```json
{
  "target": "table_row",
  "fields": [
    {
      "name": "transaction_date",
      "type": "date",
      "description": "Ngày giao dịch",
      "required": true
    },
    {
      "name": "value_date",
      "type": "date",
      "description": "Ngày hiệu lực (ngày giá trị)",
      "required": false
    },
    {
      "name": "description",
      "type": "string",
      "description": "Nội dung/mô tả giao dịch",
      "required": true
    },
    {
      "name": "reference_number",
      "type": "string",
      "description": "Số tham chiếu/mã giao dịch",
      "required": false
    },
    {
      "name": "debit_amount",
      "type": "number",
      "description": "Số tiền ghi nợ (tiền ra), null nếu là giao dịch ghi có",
      "required": false
    },
    {
      "name": "credit_amount",
      "type": "number",
      "description": "Số tiền ghi có (tiền vào), null nếu là giao dịch ghi nợ",
      "required": false
    },
    {
      "name": "balance",
      "type": "number",
      "description": "Số dư sau giao dịch",
      "required": false
    },
    {
      "name": "transaction_type",
      "type": "string",
      "description": "Loại giao dịch (transfer/payment/withdrawal/deposit/fee/interest)",
      "required": false
    },
    {
      "name": "counterparty",
      "type": "string",
      "description": "Tên đối tác giao dịch (người gửi/nhận)",
      "required": false
    },
    {
      "name": "counterparty_account",
      "type": "string",
      "description": "Số tài khoản đối tác",
      "required": false
    },
    {
      "name": "counterparty_bank",
      "type": "string",
      "description": "Ngân hàng đối tác",
      "required": false
    }
  ]
}
```

---

## Schema 2: Sao kê thẻ tín dụng (Credit Card Statement)

### Header Fields (target: `document`)

```json
{
  "target": "document",
  "fields": [
    {
      "name": "bank_name",
      "type": "string",
      "description": "Ngân hàng phát hành thẻ",
      "required": true
    },
    {
      "name": "card_number_masked",
      "type": "string",
      "description": "Số thẻ (đã che, ví dụ: **** **** **** 1234)",
      "required": true
    },
    {
      "name": "card_holder",
      "type": "string",
      "description": "Tên chủ thẻ",
      "required": true
    },
    {
      "name": "card_type",
      "type": "string",
      "description": "Loại thẻ (Visa/Mastercard/JCB/Amex)",
      "required": false
    },
    {
      "name": "credit_limit",
      "type": "number",
      "description": "Hạn mức tín dụng",
      "required": false
    },
    {
      "name": "available_credit",
      "type": "number",
      "description": "Hạn mức khả dụng còn lại",
      "required": false
    },
    {
      "name": "statement_date",
      "type": "date",
      "description": "Ngày sao kê",
      "required": true
    },
    {
      "name": "payment_due_date",
      "type": "date",
      "description": "Ngày đến hạn thanh toán",
      "required": true
    },
    {
      "name": "previous_balance",
      "type": "number",
      "description": "Dư nợ kỳ trước",
      "required": false
    },
    {
      "name": "new_charges",
      "type": "number",
      "description": "Tổng chi tiêu phát sinh trong kỳ",
      "required": true
    },
    {
      "name": "payments_received",
      "type": "number",
      "description": "Tổng thanh toán đã nhận",
      "required": false
    },
    {
      "name": "current_balance",
      "type": "number",
      "description": "Dư nợ hiện tại",
      "required": true
    },
    {
      "name": "minimum_payment",
      "type": "number",
      "description": "Số tiền thanh toán tối thiểu",
      "required": true
    },
    {
      "name": "interest_rate",
      "type": "number",
      "description": "Lãi suất áp dụng (%/năm)",
      "required": false
    },
    {
      "name": "interest_charged",
      "type": "number",
      "description": "Tiền lãi phát sinh trong kỳ",
      "required": false
    }
  ]
}
```

### Transaction Line Items (target: `table_row`)

```json
{
  "target": "table_row",
  "fields": [
    {
      "name": "transaction_date",
      "type": "date",
      "description": "Ngày giao dịch",
      "required": true
    },
    {
      "name": "posting_date",
      "type": "date",
      "description": "Ngày hạch toán",
      "required": false
    },
    {
      "name": "merchant_name",
      "type": "string",
      "description": "Tên merchant/đơn vị chấp nhận thẻ",
      "required": true
    },
    {
      "name": "merchant_category",
      "type": "string",
      "description": "Danh mục merchant (MCC description)",
      "required": false
    },
    {
      "name": "amount_original",
      "type": "number",
      "description": "Số tiền gốc (ngoại tệ nếu có)",
      "required": true
    },
    {
      "name": "original_currency",
      "type": "string",
      "description": "Đơn vị tiền gốc (USD, EUR, VND...)",
      "required": false
    },
    {
      "name": "amount_billed",
      "type": "number",
      "description": "Số tiền quy đổi (VND)",
      "required": true
    },
    {
      "name": "transaction_type",
      "type": "string",
      "description": "Loại (purchase/refund/cash_advance/fee/interest)",
      "required": false
    }
  ]
}
```

---

## Schema 3: Hợp đồng vay (Loan Agreement)

```json
{
  "target": "document",
  "fields": [
    {
      "name": "contract_number",
      "type": "string",
      "description": "Số hợp đồng tín dụng",
      "required": true
    },
    {
      "name": "contract_date",
      "type": "date",
      "description": "Ngày ký hợp đồng",
      "required": true
    },
    {
      "name": "lender_name",
      "type": "string",
      "description": "Tên bên cho vay (ngân hàng)",
      "required": true
    },
    {
      "name": "borrower_name",
      "type": "string",
      "description": "Tên bên vay",
      "required": true
    },
    {
      "name": "borrower_id",
      "type": "string",
      "description": "Số CMND/CCCD bên vay",
      "required": false
    },
    {
      "name": "loan_amount",
      "type": "number",
      "description": "Số tiền vay",
      "required": true
    },
    {
      "name": "currency",
      "type": "string",
      "description": "Đơn vị tiền tệ",
      "required": true
    },
    {
      "name": "interest_rate",
      "type": "number",
      "description": "Lãi suất (%/năm)",
      "required": true
    },
    {
      "name": "interest_type",
      "type": "string",
      "description": "Loại lãi suất (fixed/floating/mixed)",
      "required": false
    },
    {
      "name": "loan_term_months",
      "type": "number",
      "description": "Kỳ hạn vay (tháng)",
      "required": true
    },
    {
      "name": "disbursement_date",
      "type": "date",
      "description": "Ngày giải ngân",
      "required": false
    },
    {
      "name": "maturity_date",
      "type": "date",
      "description": "Ngày đáo hạn",
      "required": true
    },
    {
      "name": "repayment_method",
      "type": "string",
      "description": "Phương thức trả nợ (equal_principal/equal_installment/bullet)",
      "required": false
    },
    {
      "name": "collateral_description",
      "type": "string",
      "description": "Mô tả tài sản đảm bảo",
      "required": false
    },
    {
      "name": "collateral_value",
      "type": "number",
      "description": "Giá trị tài sản đảm bảo",
      "required": false
    },
    {
      "name": "loan_purpose",
      "type": "string",
      "description": "Mục đích vay vốn",
      "required": false
    },
    {
      "name": "penalty_rate",
      "type": "number",
      "description": "Lãi suất phạt quá hạn (%)",
      "required": false
    }
  ]
}
```

---

## Schema 4: Xác nhận chuyển khoản (Transfer Confirmation)

```json
{
  "target": "document",
  "fields": [
    {
      "name": "transaction_id",
      "type": "string",
      "description": "Mã giao dịch / số tham chiếu",
      "required": true
    },
    {
      "name": "transaction_datetime",
      "type": "string",
      "description": "Ngày giờ giao dịch (format: YYYY-MM-DD HH:mm:ss)",
      "required": true
    },
    {
      "name": "sender_name",
      "type": "string",
      "description": "Tên người chuyển",
      "required": true
    },
    {
      "name": "sender_account",
      "type": "string",
      "description": "Số tài khoản người chuyển",
      "required": true
    },
    {
      "name": "sender_bank",
      "type": "string",
      "description": "Ngân hàng người chuyển",
      "required": false
    },
    {
      "name": "receiver_name",
      "type": "string",
      "description": "Tên người nhận",
      "required": true
    },
    {
      "name": "receiver_account",
      "type": "string",
      "description": "Số tài khoản người nhận",
      "required": true
    },
    {
      "name": "receiver_bank",
      "type": "string",
      "description": "Ngân hàng người nhận",
      "required": false
    },
    {
      "name": "amount",
      "type": "number",
      "description": "Số tiền chuyển",
      "required": true
    },
    {
      "name": "fee",
      "type": "number",
      "description": "Phí chuyển khoản",
      "required": false
    },
    {
      "name": "transfer_content",
      "type": "string",
      "description": "Nội dung chuyển khoản",
      "required": false
    },
    {
      "name": "status",
      "type": "string",
      "description": "Trạng thái giao dịch (success/pending/failed)",
      "required": false
    }
  ]
}
```

---

## Schema 5: Tài liệu KYC

```json
{
  "target": "document",
  "fields": [
    {
      "name": "document_type",
      "type": "string",
      "description": "Loại giấy tờ (cmnd/cccd/passport/driving_license)",
      "required": true
    },
    {
      "name": "document_number",
      "type": "string",
      "description": "Số giấy tờ",
      "required": true
    },
    {
      "name": "full_name",
      "type": "string",
      "description": "Họ và tên đầy đủ",
      "required": true
    },
    {
      "name": "date_of_birth",
      "type": "date",
      "description": "Ngày sinh",
      "required": true
    },
    {
      "name": "gender",
      "type": "string",
      "description": "Giới tính (male/female)",
      "required": false
    },
    {
      "name": "nationality",
      "type": "string",
      "description": "Quốc tịch",
      "required": false
    },
    {
      "name": "place_of_origin",
      "type": "string",
      "description": "Quê quán / nơi sinh",
      "required": false
    },
    {
      "name": "permanent_address",
      "type": "string",
      "description": "Địa chỉ thường trú",
      "required": false
    },
    {
      "name": "issue_date",
      "type": "date",
      "description": "Ngày cấp",
      "required": true
    },
    {
      "name": "expiry_date",
      "type": "date",
      "description": "Ngày hết hạn",
      "required": false
    },
    {
      "name": "issuing_authority",
      "type": "string",
      "description": "Nơi cấp / cơ quan cấp",
      "required": false
    }
  ]
}
```

---

## Sử dụng Schema trong API

### Ví dụ gọi API trích xuất sao kê ngân hàng

```bash
curl -X POST http://localhost:8000/api/v1/workflow/execute \
  -F "file=@bank_statement.pdf" \
  -F 'workflow={
    "steps": [
      {
        "type": "parse",
        "tier": "Advance"
      },
      {
        "type": "extract",
        "tier": "Advance",
        "config": {
          "target": "document",
          "schema": {
            "fields": [
              {"name": "bank_name", "type": "string", "required": true},
              {"name": "account_number", "type": "string", "required": true},
              {"name": "account_holder", "type": "string", "required": true},
              {"name": "opening_balance", "type": "number", "required": true},
              {"name": "closing_balance", "type": "number", "required": true},
              {"name": "statement_period_start", "type": "date", "required": true},
              {"name": "statement_period_end", "type": "date", "required": true}
            ]
          }
        }
      }
    ]
  }'
```

### Ví dụ trích xuất giao dịch (table_row)

```bash
curl -X POST http://localhost:8000/api/v1/extract \
  -F "file=@bank_statement.pdf" \
  -F "tier=Advance" \
  -F 'schema={
    "target": "table_row",
    "fields": [
      {"name": "transaction_date", "type": "date", "required": true},
      {"name": "description", "type": "string", "required": true},
      {"name": "debit_amount", "type": "number", "required": false},
      {"name": "credit_amount", "type": "number", "required": false},
      {"name": "balance", "type": "number", "required": false}
    ]
  }'
```
