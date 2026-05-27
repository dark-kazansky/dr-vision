# 04 - Phân Loại Giao Dịch (Transaction Categorization)

## Tổng quan

Sau khi trích xuất giao dịch từ sao kê, hệ thống tự động phân loại từng giao dịch vào các danh mục chi tiêu. Đây là bước quan trọng cho phân tích tài chính cá nhân và doanh nghiệp.

## Danh mục giao dịch

### Cá nhân (Personal)

| Mã | Danh mục | Mô tả | Ví dụ |
|---|---|---|---|
| `salary` | Lương & Thu nhập | Lương, thưởng, thu nhập phụ | "LUONG T05/2025", "BONUS Q1" |
| `transfer_in` | Chuyển khoản đến | Nhận tiền từ người khác | "CT TU NGUYEN VAN A" |
| `transfer_out` | Chuyển khoản đi | Chuyển tiền cho người khác | "CK CHO TRAN THI B" |
| `food_dining` | Ăn uống | Nhà hàng, quán ăn, delivery | "GRAB FOOD", "THE COFFEE HOUSE" |
| `groceries` | Siêu thị & Tạp hóa | Mua sắm thực phẩm, đồ gia dụng | "VINMART", "BACH HOA XANH" |
| `transportation` | Di chuyển | Xăng, taxi, xe buýt, grab | "GRAB", "BE", "PETROLIMEX" |
| `utilities` | Tiện ích | Điện, nước, internet, điện thoại | "EVN", "VNPT", "VIETTEL" |
| `rent_mortgage` | Nhà ở | Tiền thuê nhà, trả góp nhà | "TIEN THUE NHA T05" |
| `healthcare` | Y tế | Bệnh viện, thuốc, bảo hiểm y tế | "BV BACH MAI", "NHA THUOC" |
| `education` | Giáo dục | Học phí, sách vở, khóa học | "HOC PHI", "UDEMY" |
| `entertainment` | Giải trí | Phim, game, streaming | "NETFLIX", "SPOTIFY", "CGV" |
| `shopping` | Mua sắm | Quần áo, điện tử, online shopping | "SHOPEE", "LAZADA", "TIKI" |
| `insurance` | Bảo hiểm | Phí bảo hiểm các loại | "PRUDENTIAL", "MANULIFE" |
| `investment` | Đầu tư | Chứng khoán, tiết kiệm, crypto | "VNDS", "SSI", "TIET KIEM" |
| `loan_payment` | Trả nợ vay | Trả góp, trả lãi | "TRA GOP", "TRA LAI VAY" |
| `fee_charge` | Phí ngân hàng | Phí dịch vụ, phí SMS, phí thẻ | "PHI SMS", "PHI THUONG NIEN" |
| `interest_earned` | Lãi tiết kiệm | Lãi tiền gửi | "LAI TIET KIEM", "LAI TG" |
| `other` | Khác | Không xác định được danh mục | |

### Doanh nghiệp (Business)

| Mã | Danh mục | Mô tả |
|---|---|---|
| `revenue` | Doanh thu | Thu từ bán hàng, dịch vụ |
| `cogs` | Giá vốn | Chi phí nguyên vật liệu, hàng hóa |
| `payroll` | Lương nhân viên | Chi lương, BHXH, thuế TNCN |
| `rent_office` | Thuê văn phòng | Tiền thuê mặt bằng |
| `marketing` | Marketing | Quảng cáo, PR, sự kiện |
| `software` | Phần mềm & IT | License, hosting, SaaS |
| `travel` | Công tác | Vé máy bay, khách sạn, ăn uống công tác |
| `tax_payment` | Nộp thuế | Thuế GTGT, TNDN, TNCN |
| `loan_disbursement` | Giải ngân vay | Nhận tiền vay từ ngân hàng |
| `loan_repayment` | Trả nợ vay | Trả gốc + lãi vay |
| `equipment` | Thiết bị | Mua sắm tài sản cố định |
| `professional_services` | Dịch vụ chuyên nghiệp | Kế toán, luật sư, tư vấn |

---

## Phương pháp phân loại

### 1. Rule-based (Ưu tiên cao)

Dựa trên keyword matching trong nội dung giao dịch:

```python
CATEGORY_RULES = {
    "salary": {
        "keywords": ["luong", "salary", "bonus", "thuong", "phu cap"],
        "patterns": [r"LUONG\s+T\d{2}", r"SALARY\s+\d{4}"],
        "direction": "credit"  # Chỉ áp dụng cho tiền vào
    },
    "utilities": {
        "keywords": ["evn", "vnpt", "viettel", "fpt", "nuoc", "dien"],
        "patterns": [r"TIEN\s+DIEN", r"CUOC\s+DIEN\s+THOAI"],
        "direction": "debit"
    },
    "food_dining": {
        "keywords": ["grab food", "shopee food", "baemin", "coffee", "ca phe"],
        "merchants": ["THE COFFEE HOUSE", "HIGHLANDS", "STARBUCKS", "JOLLIBEE"],
        "direction": "debit"
    },
    "transportation": {
        "keywords": ["grab", "be", "gojek", "xang", "petrol"],
        "merchants": ["GRAB", "BE GROUP", "PETROLIMEX", "PVOIL"],
        "direction": "debit"
    },
    "shopping": {
        "keywords": ["shopee", "lazada", "tiki", "sendo"],
        "merchants": ["SHOPEE", "LAZADA", "TIKI", "AMAZON"],
        "direction": "debit"
    },
    "fee_charge": {
        "keywords": ["phi", "fee", "charge", "thuong nien"],
        "patterns": [r"PHI\s+(SMS|DV|THE|CK|QTHT)"],
        "direction": "debit"
    },
    "interest_earned": {
        "keywords": ["lai", "interest", "tiet kiem"],
        "patterns": [r"LAI\s+(TK|TG|TIET\s+KIEM)"],
        "direction": "credit"
    }
}
```

### 2. LLM-based (Fallback)

Khi rule-based không match, sử dụng LLM để phân loại:

```python
CATEGORIZATION_PROMPT = """
Phân loại giao dịch ngân hàng sau vào một trong các danh mục:
{categories_list}

Giao dịch:
- Ngày: {date}
- Nội dung: {description}
- Số tiền: {amount}
- Loại: {debit_or_credit}

Trả lời JSON:
{
    "category": "mã_danh_mục",
    "confidence": 0.85,
    "reasoning": "giải thích ngắn"
}
"""
```

### 3. Hybrid Approach (Khuyến nghị)

```
┌─────────────────────────────────────────┐
│         Transaction Input                │
│  "CK CHO NGUYEN VAN A NOI DUNG:        │
│   TIEN THUE NHA THANG 5"               │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│      Step 1: Rule-based Matching         │
│  Check keywords, patterns, merchants     │
│  Match found? → confidence > 0.9         │
└────────────────┬────────────────────────┘
                 │
          No match / Low confidence
                 │
                 ▼
┌─────────────────────────────────────────┐
│      Step 2: LLM Classification          │
│  Send to LLM with context               │
│  Get category + confidence               │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│      Step 3: Confidence Check            │
│  confidence > 0.7 → Accept              │
│  confidence < 0.7 → Mark as "other"     │
└─────────────────────────────────────────┘
```

---

## Output Format

### Single Transaction

```json
{
  "transaction_date": "2025-05-01",
  "description": "CK CHO NGUYEN VAN A - TIEN THUE NHA T05",
  "debit_amount": 8000000,
  "credit_amount": null,
  "balance": 25000000,
  "category": "rent_mortgage",
  "category_confidence": 0.92,
  "category_method": "rule_based"
}
```

### Aggregated Summary

```json
{
  "period": "2025-05",
  "account": "0123456789",
  "summary": {
    "total_income": 35000000,
    "total_expense": 28500000,
    "net_flow": 6500000,
    "transaction_count": 47
  },
  "by_category": [
    {"category": "salary", "amount": 30000000, "count": 1, "percentage": 85.7},
    {"category": "transfer_in", "amount": 5000000, "count": 3, "percentage": 14.3}
  ],
  "expense_breakdown": [
    {"category": "rent_mortgage", "amount": 8000000, "count": 1, "percentage": 28.1},
    {"category": "food_dining", "amount": 6500000, "count": 15, "percentage": 22.8},
    {"category": "shopping", "amount": 4200000, "count": 8, "percentage": 14.7},
    {"category": "utilities", "amount": 3500000, "count": 4, "percentage": 12.3},
    {"category": "transportation", "amount": 2800000, "count": 12, "percentage": 9.8},
    {"category": "other", "amount": 3500000, "count": 7, "percentage": 12.3}
  ]
}
```

---

## Merchant Database

Xây dựng database merchant phổ biến tại Việt Nam:

```python
MERCHANT_MAPPING = {
    # Food & Dining
    "THE COFFEE HOUSE": {"category": "food_dining", "subcategory": "cafe"},
    "HIGHLANDS COFFEE": {"category": "food_dining", "subcategory": "cafe"},
    "STARBUCKS": {"category": "food_dining", "subcategory": "cafe"},
    "JOLLIBEE": {"category": "food_dining", "subcategory": "fast_food"},
    "LOTTERIA": {"category": "food_dining", "subcategory": "fast_food"},
    "GRAB FOOD": {"category": "food_dining", "subcategory": "delivery"},
    "SHOPEE FOOD": {"category": "food_dining", "subcategory": "delivery"},
    
    # Shopping
    "SHOPEE": {"category": "shopping", "subcategory": "ecommerce"},
    "LAZADA": {"category": "shopping", "subcategory": "ecommerce"},
    "TIKI": {"category": "shopping", "subcategory": "ecommerce"},
    "VINCOM": {"category": "shopping", "subcategory": "mall"},
    "AEON MALL": {"category": "shopping", "subcategory": "mall"},
    
    # Groceries
    "VINMART": {"category": "groceries", "subcategory": "supermarket"},
    "BACH HOA XANH": {"category": "groceries", "subcategory": "convenience"},
    "CO.OP MART": {"category": "groceries", "subcategory": "supermarket"},
    "BIG C": {"category": "groceries", "subcategory": "hypermarket"},
    "LOTTE MART": {"category": "groceries", "subcategory": "hypermarket"},
    
    # Transportation
    "GRAB": {"category": "transportation", "subcategory": "ride_hailing"},
    "BE": {"category": "transportation", "subcategory": "ride_hailing"},
    "PETROLIMEX": {"category": "transportation", "subcategory": "fuel"},
    "PVOIL": {"category": "transportation", "subcategory": "fuel"},
    
    # Utilities
    "EVN": {"category": "utilities", "subcategory": "electricity"},
    "VNPT": {"category": "utilities", "subcategory": "telecom"},
    "VIETTEL": {"category": "utilities", "subcategory": "telecom"},
    "FPT TELECOM": {"category": "utilities", "subcategory": "internet"},
    
    # Entertainment
    "NETFLIX": {"category": "entertainment", "subcategory": "streaming"},
    "SPOTIFY": {"category": "entertainment", "subcategory": "streaming"},
    "CGV": {"category": "entertainment", "subcategory": "cinema"},
    "GALAXY": {"category": "entertainment", "subcategory": "cinema"},
}
```

---

## Cải thiện độ chính xác

### 1. Learning từ user feedback

```json
{
  "transaction_id": "TXN001",
  "original_category": "other",
  "corrected_category": "food_dining",
  "description": "THANH TOAN QR - QUAN PHO 24",
  "feedback_date": "2025-05-01"
}
```

### 2. Context-aware categorization

Sử dụng thông tin ngữ cảnh để cải thiện:
- **Thời gian**: Giao dịch 11h-13h → khả năng cao là ăn trưa
- **Số tiền**: 50k-200k vào giờ ăn → food_dining
- **Tần suất**: Giao dịch lặp lại hàng tháng cùng số tiền → utilities/rent
- **Lịch sử**: Merchant đã được phân loại trước đó → reuse

### 3. Metrics theo dõi

| Metric | Mục tiêu | Đo lường |
|---|---|---|
| Auto-categorization rate | > 85% | % giao dịch được phân loại tự động |
| Accuracy | > 90% | % phân loại đúng (sau user feedback) |
| "Other" rate | < 15% | % giao dịch không phân loại được |
| Avg confidence | > 0.8 | Trung bình confidence score |
