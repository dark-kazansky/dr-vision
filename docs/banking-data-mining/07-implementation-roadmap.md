# 07 - Lộ Trình Triển Khai (Implementation Roadmap)

## Tổng quan

Lộ trình triển khai chia thành 4 phase, mỗi phase kéo dài 2-4 tuần. Ưu tiên delivery giá trị sớm nhất có thể (MVP) rồi mở rộng dần.

---

## Phase 1: Foundation (Tuần 1-2)

**Mục tiêu:** Có thể xử lý sao kê ngân hàng cơ bản end-to-end.

### Tasks

| # | Task | Effort | Priority |
|---|---|---|---|
| 1.1 | Tạo banking classification rules config | 2h | P0 |
| 1.2 | Tạo extraction schema cho bank statement (header + transactions) | 4h | P0 |
| 1.3 | Tạo workflow template "bank_statement_mining" | 2h | P0 |
| 1.4 | Test với sao kê thực tế (VCB, BIDV, TCB) | 4h | P0 |
| 1.5 | Tạo extraction schema cho credit card statement | 3h | P1 |
| 1.6 | Tạo extraction schema cho transfer confirmation | 2h | P1 |
| 1.7 | Tối ưu prompt cho tiếng Việt | 4h | P1 |

### Deliverables

- [ ] API có thể nhận sao kê PDF → trả về JSON giao dịch
- [ ] Hỗ trợ ít nhất 3 ngân hàng VN (VCB, BIDV, TCB)
- [ ] Accuracy > 85% cho header fields
- [ ] Accuracy > 75% cho transaction line items

### Technical Details

```python
# backend/config/banking_schemas.py (new file)

BANKING_CLASSIFICATION_RULES = [
    {"doc_type": "bank_statement", "description": "..."},
    {"doc_type": "credit_card_statement", "description": "..."},
    # ...
]

BANK_STATEMENT_HEADER_SCHEMA = {
    "target": "document",
    "fields": [...]
}

BANK_STATEMENT_TRANSACTION_SCHEMA = {
    "target": "table_row", 
    "fields": [...]
}
```

---

## Phase 2: Categorization & Analytics (Tuần 3-4)

**Mục tiêu:** Tự động phân loại giao dịch và cung cấp phân tích cơ bản.

### Tasks

| # | Task | Effort | Priority |
|---|---|---|---|
| 2.1 | Xây dựng Transaction Categorizer component | 8h | P0 |
| 2.2 | Tạo merchant database (VN) | 4h | P0 |
| 2.3 | Implement rule-based categorization | 6h | P0 |
| 2.4 | Implement LLM fallback categorization | 4h | P1 |
| 2.5 | Xây dựng basic analytics (cash flow, spending breakdown) | 8h | P1 |
| 2.6 | CSV/JSON export endpoint | 4h | P1 |
| 2.7 | Unit tests cho categorizer | 4h | P1 |

### Deliverables

- [ ] Giao dịch được tự động phân loại (> 80% auto-categorized)
- [ ] API trả về spending summary theo category
- [ ] Export CSV với giao dịch đã phân loại
- [ ] Merchant database với 100+ merchants VN

### New Components

```
backend/
├── components/
│   └── transaction_categorizer.py    # NEW
├── services/
│   └── banking_analytics_service.py  # NEW
├── config/
│   ├── banking_schemas.py            # NEW (from Phase 1)
│   └── merchant_database.py          # NEW
└── api/v1/
    └── banking.py                    # NEW - Banking-specific endpoints
```

---

## Phase 3: Advanced Analytics & Storage (Tuần 5-7)

**Mục tiêu:** Phân tích nâng cao, lưu trữ kết quả, xử lý batch.

### Tasks

| # | Task | Effort | Priority |
|---|---|---|---|
| 3.1 | Database schema cho transactions & reports | 6h | P0 |
| 3.2 | Anomaly detection component | 8h | P1 |
| 3.3 | Period comparison analysis | 6h | P1 |
| 3.4 | Balance trend analysis | 4h | P1 |
| 3.5 | Batch processing (multiple files) | 8h | P1 |
| 3.6 | Excel export với charts | 6h | P2 |
| 3.7 | Cross-document aggregation | 8h | P2 |
| 3.8 | KYC document processing workflow | 4h | P2 |
| 3.9 | Loan document analysis workflow | 4h | P2 |

### Deliverables

- [ ] SQLite storage cho extracted transactions
- [ ] Anomaly detection với severity levels
- [ ] Month-over-month comparison reports
- [ ] Batch upload & processing (up to 20 files)
- [ ] Excel report generation

### Database Integration

```python
# backend/storage/banking_db.py (new)

class BankingDatabase:
    """SQLite storage for banking data mining results."""
    
    async def store_transactions(self, account_id, transactions): ...
    async def get_transactions(self, account_id, date_range): ...
    async def get_analytics(self, account_id, analysis_type): ...
    async def store_anomalies(self, anomalies): ...
```

---

## Phase 4: Security & Production (Tuần 8-10)

**Mục tiêu:** Production-ready với bảo mật đầy đủ.

### Tasks

| # | Task | Effort | Priority |
|---|---|---|---|
| 4.1 | PII masking trong logs | 4h | P0 |
| 4.2 | Data encryption at rest | 6h | P0 |
| 4.3 | Audit trail logging | 6h | P0 |
| 4.4 | Auto-delete temp files | 2h | P0 |
| 4.5 | RBAC implementation | 8h | P1 |
| 4.6 | Data retention policies | 4h | P1 |
| 4.7 | API rate limiting per role | 4h | P1 |
| 4.8 | Security testing & hardening | 8h | P1 |
| 4.9 | Performance optimization | 6h | P2 |
| 4.10 | Documentation & API docs | 4h | P2 |

### Deliverables

- [ ] Tất cả PII được mask trong logs
- [ ] Dữ liệu nhạy cảm encrypted at rest
- [ ] Audit log cho mọi data access
- [ ] File tạm tự động xóa sau processing
- [ ] Security checklist passed

---

## Timeline Overview

```
Week 1-2:  ████████████████████████  Phase 1: Foundation
                                      → MVP: Process bank statements

Week 3-4:  ████████████████████████  Phase 2: Categorization
                                      → Auto-categorize transactions

Week 5-7:  ████████████████████████████████████  Phase 3: Analytics
                                      → Advanced analysis & storage

Week 8-10: ████████████████████████████████████  Phase 4: Security
                                      → Production-ready
```

---

## Milestones

| Milestone | Target Date | Criteria |
|---|---|---|
| **M1: MVP** | End of Week 2 | Process 1 bank statement → JSON output |
| **M2: Smart** | End of Week 4 | Auto-categorize + basic analytics |
| **M3: Complete** | End of Week 7 | Full analytics + batch + storage |
| **M4: Production** | End of Week 10 | Security + compliance ready |

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|---|---|---|---|
| OCR accuracy thấp cho PDF scan | High | Medium | Dùng tier Advance, test nhiều ngân hàng |
| Format sao kê khác nhau giữa các NH | Medium | High | Tạo prompt flexible, test coverage rộng |
| Transaction extraction miss rows | High | Medium | Validate tổng vs opening/closing balance |
| LLM hallucination số liệu | High | Low | Cross-validate, confidence threshold |
| Performance chậm cho file lớn | Medium | Medium | Async processing, pagination |
| Data breach | Critical | Low | Encryption, access control, audit |

---

## Success Metrics

### Phase 1

| Metric | Target |
|---|---|
| Header extraction accuracy | > 90% |
| Transaction extraction accuracy | > 80% |
| Supported banks (VN) | ≥ 3 |
| Processing time (single page) | < 30s |

### Phase 2

| Metric | Target |
|---|---|
| Auto-categorization rate | > 80% |
| Categorization accuracy | > 85% |
| Merchant database size | > 100 |
| Export formats supported | CSV, JSON |

### Phase 3

| Metric | Target |
|---|---|
| Anomaly detection precision | > 70% |
| Batch processing throughput | 20 files/batch |
| Analytics response time | < 5s |
| Data storage reliability | 99.9% |

### Phase 4

| Metric | Target |
|---|---|
| PII masking coverage | 100% |
| Audit log completeness | 100% |
| Security test pass rate | 100% |
| API uptime | > 99.5% |

---

## Tech Stack Additions

| Component | Technology | Reason |
|---|---|---|
| Database | SQLite (dev) → PostgreSQL (prod) | Structured storage |
| Encryption | `cryptography` library (Fernet) | AES-256 encryption |
| Excel export | `openpyxl` | Excel generation with charts |
| Analytics | `pandas` (optional) | Data aggregation |
| Testing | `pytest` + `hypothesis` | Property-based testing |
| Monitoring | Structured logging (JSON) | Audit trail |

### Dependencies to add

```txt
# requirements.txt additions
openpyxl>=3.1.0        # Excel export
cryptography>=42.0.0   # Data encryption
```

---

## Getting Started (cho developers)

### 1. Bắt đầu với Phase 1, Task 1.1

```bash
# Tạo file config schemas
touch backend/config/banking_schemas.py
```

### 2. Test với sample data

```bash
# Chạy workflow với sao kê mẫu
curl -X POST http://localhost:8000/api/v1/workflow/execute \
  -F "file=@samples/vcb_statement.pdf" \
  -F "workflow=@docs/banking-data-mining/samples/bank_statement_workflow.json"
```

### 3. Validate kết quả

```python
# Kiểm tra extraction result
assert result["bank_name"] is not None
assert result["opening_balance"] + sum(credits) - sum(debits) == result["closing_balance"]
```

---

## Folder Structure (sau khi hoàn thành)

```
backend/
├── agents/                          # Existing - AI model agents
├── api/v1/
│   ├── banking.py                   # NEW - Banking API endpoints
│   └── ...
├── components/
│   ├── transaction_categorizer.py   # NEW - Transaction categorization
│   └── ...
├── config/
│   ├── banking_schemas.py           # NEW - Banking extraction schemas
│   ├── merchant_database.py         # NEW - Merchant mapping
│   └── ...
├── services/
│   ├── banking_analytics_service.py # NEW - Analytics logic
│   ├── banking_export_service.py    # NEW - Export (CSV/Excel)
│   └── ...
├── storage/
│   ├── banking_db.py                # NEW - Database operations
│   └── migrations/                  # NEW - DB migrations
├── security/
│   ├── pii_masker.py                # NEW - PII masking
│   ├── encryption.py                # NEW - Data encryption
│   └── audit_logger.py             # NEW - Audit trail
└── tests/
    └── banking/                     # NEW - Banking-specific tests
        ├── test_categorizer.py
        ├── test_extraction.py
        └── test_analytics.py
```
