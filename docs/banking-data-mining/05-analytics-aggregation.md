# 05 - Phân Tích & Tổng Hợp Dữ Liệu

## Tổng quan

Sau khi trích xuất và phân loại giao dịch, hệ thống cung cấp các phân tích tổng hợp giúp hiểu rõ tình hình tài chính từ dữ liệu khai thác được.

## Các loại phân tích

### 1. Cash Flow Analysis (Phân tích dòng tiền)

**Mục đích:** Hiểu dòng tiền vào/ra theo thời gian.

```json
{
  "analysis_type": "cash_flow",
  "period": "monthly",
  "data": {
    "2025-01": {"inflow": 35000000, "outflow": 28000000, "net": 7000000},
    "2025-02": {"inflow": 35000000, "outflow": 31000000, "net": 4000000},
    "2025-03": {"inflow": 38000000, "outflow": 27000000, "net": 11000000},
    "2025-04": {"inflow": 35000000, "outflow": 42000000, "net": -7000000},
    "2025-05": {"inflow": 36000000, "outflow": 29000000, "net": 7000000}
  },
  "summary": {
    "avg_monthly_inflow": 35800000,
    "avg_monthly_outflow": 31400000,
    "avg_net_flow": 4400000,
    "months_negative": 1,
    "trend": "stable"
  }
}
```

**Chỉ số:**
- Tổng thu nhập / chi tiêu theo tháng
- Dòng tiền ròng (net cash flow)
- Xu hướng (tăng/giảm/ổn định)
- Tháng có dòng tiền âm

---

### 2. Spending Pattern Analysis (Phân tích chi tiêu)

**Mục đích:** Phân tích cơ cấu chi tiêu theo danh mục.

```json
{
  "analysis_type": "spending_pattern",
  "period": "2025-Q1",
  "total_spending": 86000000,
  "categories": [
    {
      "category": "rent_mortgage",
      "total": 24000000,
      "percentage": 27.9,
      "avg_per_month": 8000000,
      "trend": "stable",
      "transactions": 3
    },
    {
      "category": "food_dining",
      "total": 19500000,
      "percentage": 22.7,
      "avg_per_month": 6500000,
      "trend": "increasing",
      "transactions": 45
    },
    {
      "category": "shopping",
      "total": 12600000,
      "percentage": 14.7,
      "avg_per_month": 4200000,
      "trend": "decreasing",
      "transactions": 24
    }
  ],
  "insights": [
    "Chi tiêu ăn uống tăng 15% so với quý trước",
    "Chi tiêu mua sắm giảm 20% so với quý trước",
    "Tỷ lệ tiết kiệm: 12.3% thu nhập"
  ]
}
```

---

### 3. Income Analysis (Phân tích thu nhập)

**Mục đích:** Phân tích nguồn thu nhập và tính ổn định.

```json
{
  "analysis_type": "income",
  "period": "2025-Q1",
  "total_income": 107400000,
  "sources": [
    {
      "source": "salary",
      "total": 90000000,
      "percentage": 83.8,
      "frequency": "monthly",
      "stability": "high"
    },
    {
      "source": "interest_earned",
      "total": 4500000,
      "percentage": 4.2,
      "frequency": "monthly",
      "stability": "high"
    },
    {
      "source": "transfer_in",
      "total": 12900000,
      "percentage": 12.0,
      "frequency": "irregular",
      "stability": "low"
    }
  ],
  "metrics": {
    "income_stability_score": 0.84,
    "income_diversification": 0.32,
    "primary_income_ratio": 0.838
  }
}
```

---

### 4. Anomaly Detection (Phát hiện bất thường)

**Mục đích:** Phát hiện giao dịch bất thường cần chú ý.

#### Các loại anomaly:

| Loại | Mô tả | Ngưỡng |
|---|---|---|
| `large_transaction` | Giao dịch lớn bất thường | > 3x trung bình danh mục |
| `unusual_time` | Giao dịch ngoài giờ thường | 23:00 - 05:00 |
| `new_merchant` | Merchant chưa từng giao dịch | Lần đầu xuất hiện |
| `frequency_spike` | Tần suất giao dịch tăng đột biến | > 2x trung bình tuần |
| `round_number` | Số tiền tròn lớn (có thể chuyển khoản đáng ngờ) | > 50M VND, số tròn |
| `duplicate` | Giao dịch trùng lặp | Cùng số tiền + merchant + ngày |
| `balance_drop` | Số dư giảm mạnh | Giảm > 50% trong 1 ngày |

#### Output format:

```json
{
  "anomalies": [
    {
      "type": "large_transaction",
      "severity": "high",
      "transaction": {
        "date": "2025-05-15",
        "description": "CK CHO CONG TY ABC",
        "amount": 150000000,
        "category": "transfer_out"
      },
      "context": {
        "avg_transfer_amount": 15000000,
        "multiplier": 10.0,
        "message": "Giao dịch lớn gấp 10 lần trung bình chuyển khoản"
      }
    },
    {
      "type": "frequency_spike",
      "severity": "medium",
      "period": "2025-05-10 to 2025-05-12",
      "context": {
        "transactions_in_period": 15,
        "avg_weekly_transactions": 5,
        "message": "15 giao dịch trong 3 ngày, trung bình tuần chỉ 5"
      }
    }
  ],
  "risk_score": 0.35,
  "risk_level": "low"
}
```

---

### 5. Balance Trend Analysis (Phân tích xu hướng số dư)

```json
{
  "analysis_type": "balance_trend",
  "data_points": [
    {"date": "2025-05-01", "balance": 45000000},
    {"date": "2025-05-05", "balance": 42000000},
    {"date": "2025-05-10", "balance": 38000000},
    {"date": "2025-05-15", "balance": 35000000},
    {"date": "2025-05-20", "balance": 33000000},
    {"date": "2025-05-25", "balance": 65000000},
    {"date": "2025-05-31", "balance": 52000000}
  ],
  "metrics": {
    "min_balance": 33000000,
    "max_balance": 65000000,
    "avg_balance": 44285714,
    "volatility": 0.28,
    "salary_day_detected": 25,
    "days_below_threshold": 0,
    "threshold": 10000000
  }
}
```

---

### 6. Comparative Analysis (So sánh kỳ)

```json
{
  "analysis_type": "period_comparison",
  "current_period": "2025-05",
  "previous_period": "2025-04",
  "comparison": {
    "income": {
      "current": 36000000,
      "previous": 35000000,
      "change": 1000000,
      "change_percent": 2.86
    },
    "expense": {
      "current": 29000000,
      "previous": 42000000,
      "change": -13000000,
      "change_percent": -30.95
    },
    "savings_rate": {
      "current": 19.4,
      "previous": -20.0,
      "change": 39.4
    },
    "category_changes": [
      {"category": "shopping", "change_percent": -45.0, "direction": "decreased"},
      {"category": "food_dining", "change_percent": 12.0, "direction": "increased"},
      {"category": "utilities", "change_percent": 0.0, "direction": "stable"}
    ]
  }
}
```

---

## Data Aggregation Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                  Aggregation Pipeline                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Input: Extracted & Categorized Transactions                 │
│                                                              │
│  ┌──────────────┐                                           │
│  │  Data Store  │  ← Store all extracted transactions       │
│  │  (SQLite/    │                                           │
│  │   Postgres)  │                                           │
│  └──────┬───────┘                                           │
│         │                                                    │
│         ├──▶ Daily Aggregation                              │
│         │    - Sum by category per day                       │
│         │    - Count transactions per day                    │
│         │    - Track balance changes                         │
│         │                                                    │
│         ├──▶ Monthly Aggregation                            │
│         │    - Income vs Expense totals                      │
│         │    - Category breakdown                            │
│         │    - Savings rate calculation                      │
│         │                                                    │
│         ├──▶ Trend Calculation                              │
│         │    - Moving averages (7-day, 30-day)              │
│         │    - Month-over-month changes                      │
│         │    - Seasonality detection                         │
│         │                                                    │
│         ├──▶ Anomaly Detection                              │
│         │    - Statistical outliers (Z-score > 2)           │
│         │    - Pattern breaks                                │
│         │    - Threshold violations                          │
│         │                                                    │
│         └──▶ Report Generation                              │
│              - JSON summary                                   │
│              - CSV export                                     │
│              - Excel report with charts                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Export Formats

### CSV Export

```csv
date,description,debit,credit,balance,category,subcategory
2025-05-01,LUONG T05/2025,,35000000,45000000,salary,
2025-05-02,TIEN THUE NHA T05,8000000,,37000000,rent_mortgage,
2025-05-03,GRAB FOOD - BUN BO,85000,,36915000,food_dining,delivery
2025-05-03,PHI SMS BANKING,11000,,36904000,fee_charge,bank_fee
```

### Excel Report Structure

```
Sheet 1: Summary
  - Tổng quan thu chi
  - Biểu đồ dòng tiền

Sheet 2: Transactions
  - Danh sách giao dịch đầy đủ
  - Đã phân loại

Sheet 3: Category Breakdown
  - Chi tiết theo danh mục
  - Biểu đồ tròn

Sheet 4: Trends
  - Xu hướng theo tháng
  - So sánh kỳ

Sheet 5: Anomalies
  - Giao dịch bất thường
  - Risk assessment
```

### JSON API Response

```json
{
  "report": {
    "generated_at": "2025-05-05T10:30:00Z",
    "account": "0123456789",
    "period": "2025-05",
    "summary": { ... },
    "transactions": [ ... ],
    "categories": [ ... ],
    "anomalies": [ ... ],
    "trends": { ... }
  },
  "export_links": {
    "csv": "/api/v1/reports/export/csv?id=RPT001",
    "excel": "/api/v1/reports/export/excel?id=RPT001",
    "pdf": "/api/v1/reports/export/pdf?id=RPT001"
  }
}
```

---

## Database Schema (cho lưu trữ kết quả)

```sql
-- Bảng lưu thông tin tài khoản đã xử lý
CREATE TABLE accounts (
    id TEXT PRIMARY KEY,
    bank_name TEXT NOT NULL,
    account_number TEXT NOT NULL,
    account_holder TEXT NOT NULL,
    currency TEXT DEFAULT 'VND',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng lưu giao dịch đã trích xuất
CREATE TABLE transactions (
    id TEXT PRIMARY KEY,
    account_id TEXT REFERENCES accounts(id),
    transaction_date DATE NOT NULL,
    description TEXT NOT NULL,
    debit_amount DECIMAL(15,2),
    credit_amount DECIMAL(15,2),
    balance DECIMAL(15,2),
    category TEXT,
    category_confidence REAL,
    category_method TEXT,  -- 'rule_based' | 'llm' | 'user_corrected'
    reference_number TEXT,
    counterparty TEXT,
    source_file TEXT,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng lưu kết quả phân tích
CREATE TABLE analysis_reports (
    id TEXT PRIMARY KEY,
    account_id TEXT REFERENCES accounts(id),
    analysis_type TEXT NOT NULL,
    period_start DATE,
    period_end DATE,
    result_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng lưu anomalies
CREATE TABLE anomalies (
    id TEXT PRIMARY KEY,
    transaction_id TEXT REFERENCES transactions(id),
    anomaly_type TEXT NOT NULL,
    severity TEXT NOT NULL,  -- 'low' | 'medium' | 'high'
    context_json TEXT,
    reviewed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index cho query performance
CREATE INDEX idx_transactions_account_date ON transactions(account_id, transaction_date);
CREATE INDEX idx_transactions_category ON transactions(category);
CREATE INDEX idx_anomalies_severity ON anomalies(severity, reviewed);
```

---

## KPIs & Metrics Dashboard

| Metric | Công thức | Ý nghĩa |
|---|---|---|
| Savings Rate | (Income - Expense) / Income × 100 | Tỷ lệ tiết kiệm |
| Expense Ratio | Expense / Income × 100 | Tỷ lệ chi tiêu |
| Essential Ratio | (Rent + Utilities + Food) / Income × 100 | Chi phí thiết yếu |
| Discretionary Ratio | (Shopping + Entertainment) / Income × 100 | Chi tiêu tùy ý |
| Debt Service Ratio | Loan Payments / Income × 100 | Gánh nặng nợ |
| Emergency Fund | Balance / Avg Monthly Expense | Quỹ dự phòng (tháng) |
| Income Stability | StdDev(Monthly Income) / Avg(Monthly Income) | Độ ổn định thu nhập |
