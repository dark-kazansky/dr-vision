# 06 - Bảo Mật & Tuân Thủ (Compliance & Security)

## Tổng quan

Xử lý dữ liệu ngân hàng đòi hỏi tuân thủ nghiêm ngặt các quy định về bảo mật thông tin và quyền riêng tư. Tài liệu này mô tả các biện pháp bảo mật cần triển khai.

## Quy định áp dụng

### Việt Nam

| Quy định | Phạm vi | Yêu cầu chính |
|---|---|---|
| Luật An toàn thông tin mạng (2015) | Bảo vệ thông tin cá nhân | Đồng ý, mục đích rõ ràng, bảo mật |
| Nghị định 13/2023/NĐ-CP | Bảo vệ dữ liệu cá nhân | Thông báo, đồng ý, quyền chủ thể |
| Thông tư 09/2020/TT-NHNN | An toàn thông tin ngân hàng | Mã hóa, kiểm soát truy cập |
| Luật Giao dịch điện tử (2023) | Chữ ký số, giao dịch điện tử | Xác thực, toàn vẹn dữ liệu |

### Quốc tế (nếu áp dụng)

| Quy định | Phạm vi |
|---|---|
| GDPR | Dữ liệu công dân EU |
| PCI DSS | Dữ liệu thẻ thanh toán |
| SOC 2 | Kiểm soát bảo mật dịch vụ |

---

## Phân loại dữ liệu nhạy cảm

### Mức độ nhạy cảm

| Mức | Loại dữ liệu | Ví dụ | Xử lý |
|---|---|---|---|
| **Critical** | Thông tin xác thực | Mật khẩu, PIN, OTP | Không lưu trữ |
| **High** | PII + Tài chính | Số TK, số dư, giao dịch | Mã hóa + Access control |
| **Medium** | PII cơ bản | Họ tên, ngày sinh, địa chỉ | Mã hóa |
| **Low** | Metadata | Loại tài liệu, timestamp | Logging bình thường |

### Dữ liệu cần bảo vệ đặc biệt

```python
SENSITIVE_FIELDS = {
    # Critical - Không bao giờ lưu/log
    "pin": "NEVER_STORE",
    "password": "NEVER_STORE",
    "otp": "NEVER_STORE",
    "cvv": "NEVER_STORE",
    
    # High - Mã hóa + Masking trong log
    "account_number": "ENCRYPT_AND_MASK",
    "card_number": "ENCRYPT_AND_MASK",
    "document_number": "ENCRYPT_AND_MASK",  # CMND/CCCD
    "balance": "ENCRYPT",
    "transaction_amount": "ENCRYPT",
    
    # Medium - Mã hóa
    "full_name": "ENCRYPT",
    "date_of_birth": "ENCRYPT",
    "address": "ENCRYPT",
    "phone_number": "ENCRYPT",
}
```

---

## PII Masking (Che giấu thông tin nhạy cảm)

### Quy tắc masking

```python
MASKING_RULES = {
    "account_number": {
        # 0123456789 → ******6789
        "method": "show_last_4",
        "mask_char": "*"
    },
    "card_number": {
        # 4111 1111 1111 1234 → **** **** **** 1234
        "method": "show_last_4",
        "mask_char": "*"
    },
    "document_number": {
        # 012345678901 → 0123****8901
        "method": "show_first_last_4",
        "mask_char": "*"
    },
    "phone_number": {
        # 0901234567 → 090***4567
        "method": "show_first_3_last_4",
        "mask_char": "*"
    },
    "full_name": {
        # Nguyễn Văn An → N***n V*n A*
        "method": "partial_mask",
        "mask_char": "*"
    }
}
```

### Implementation

```python
class PIIMasker:
    """Mask sensitive information in logs and responses."""
    
    @staticmethod
    def mask_account_number(value: str) -> str:
        """Mask account number, showing only last 4 digits."""
        if len(value) <= 4:
            return value
        return "*" * (len(value) - 4) + value[-4:]
    
    @staticmethod
    def mask_card_number(value: str) -> str:
        """Mask card number in standard format."""
        digits = value.replace(" ", "").replace("-", "")
        if len(digits) < 13:
            return value
        masked = "*" * (len(digits) - 4) + digits[-4:]
        # Format as groups of 4
        return " ".join([masked[i:i+4] for i in range(0, len(masked), 4)])
    
    @staticmethod
    def mask_for_logging(data: dict, fields_to_mask: list) -> dict:
        """Create a masked copy of data for safe logging."""
        masked = data.copy()
        for field in fields_to_mask:
            if field in masked and masked[field]:
                masked[field] = PIIMasker.mask_account_number(str(masked[field]))
        return masked
```

---

## Mã hóa dữ liệu (Encryption)

### At Rest (Dữ liệu lưu trữ)

```python
# Sử dụng AES-256-GCM cho mã hóa dữ liệu nhạy cảm
ENCRYPTION_CONFIG = {
    "algorithm": "AES-256-GCM",
    "key_derivation": "PBKDF2-SHA256",
    "iterations": 100000,
    "key_rotation_days": 90,
}
```

### In Transit (Dữ liệu truyền tải)

- HTTPS/TLS 1.3 cho tất cả API endpoints
- Certificate pinning cho mobile clients
- Không truyền dữ liệu nhạy cảm qua query parameters

### File Processing

```python
FILE_SECURITY = {
    # Upload
    "max_file_size_mb": 20,
    "allowed_types": ["pdf", "png", "jpg", "jpeg", "tiff"],
    "virus_scan": True,
    
    # Storage
    "temp_file_encryption": True,
    "auto_delete_after_processing": True,
    "max_retention_hours": 24,
    
    # Processing
    "memory_only_processing": True,  # Không ghi file tạm ra disk nếu có thể
    "secure_delete": True,  # Overwrite trước khi xóa
}
```

---

## Kiểm soát truy cập (Access Control)

### Role-Based Access Control (RBAC)

| Role | Quyền | Mô tả |
|---|---|---|
| `admin` | Full access | Quản trị hệ thống |
| `analyst` | Read + Process | Xử lý tài liệu, xem kết quả |
| `viewer` | Read only | Chỉ xem báo cáo (masked) |
| `api_client` | API access | Truy cập qua API key |

### API Authentication

```python
AUTH_CONFIG = {
    "method": "Bearer Token (JWT)",
    "token_expiry_minutes": 60,
    "refresh_token_expiry_days": 7,
    "max_active_sessions": 3,
    "require_2fa_for": ["admin", "analyst"],
}
```

### Rate Limiting (theo role)

| Role | Requests/minute | Burst | Daily limit |
|---|---|---|---|
| `admin` | 100 | 200 | Unlimited |
| `analyst` | 30 | 60 | 1000 |
| `viewer` | 10 | 20 | 200 |
| `api_client` | 60 | 120 | 5000 |

---

## Audit Trail (Nhật ký kiểm toán)

### Sự kiện cần ghi log

```python
AUDIT_EVENTS = [
    # Document processing
    "document.uploaded",
    "document.processed",
    "document.deleted",
    "document.exported",
    
    # Data access
    "data.viewed",
    "data.extracted",
    "data.exported",
    "data.searched",
    
    # User actions
    "user.login",
    "user.logout",
    "user.permission_changed",
    "user.api_key_created",
    
    # System events
    "system.config_changed",
    "system.model_changed",
    "system.error",
]
```

### Audit Log Format

```json
{
  "timestamp": "2025-05-05T10:30:00.000Z",
  "event_type": "document.processed",
  "user_id": "user_001",
  "user_role": "analyst",
  "ip_address": "192.168.1.100",
  "resource": {
    "type": "bank_statement",
    "file_hash": "sha256:abc123...",
    "file_size_bytes": 245000
  },
  "action_details": {
    "workflow": "full_bank_statement_mining",
    "steps_completed": 4,
    "processing_time_ms": 12500,
    "model_used": "gemini-2.5-flash"
  },
  "result": "success",
  "data_accessed": ["account_number", "transactions", "balance"]
}
```

### Log Retention

| Loại log | Thời gian lưu | Lý do |
|---|---|---|
| Audit logs | 7 năm | Yêu cầu pháp lý ngân hàng |
| Access logs | 1 năm | Phân tích bảo mật |
| Error logs | 90 ngày | Troubleshooting |
| Processing logs | 30 ngày | Performance monitoring |

---

## Data Retention & Deletion

### Chính sách lưu trữ

```python
RETENTION_POLICY = {
    # File gốc (uploaded)
    "uploaded_files": {
        "retention": "delete_after_processing",
        "max_hours": 24,
        "secure_delete": True
    },
    
    # Kết quả trích xuất
    "extraction_results": {
        "retention": "configurable",
        "default_days": 90,
        "max_days": 365,
        "encrypted": True
    },
    
    # Báo cáo phân tích
    "analysis_reports": {
        "retention": "configurable",
        "default_days": 365,
        "encrypted": True
    },
    
    # Audit logs
    "audit_logs": {
        "retention": "fixed",
        "years": 7,
        "immutable": True  # Không thể sửa/xóa
    }
}
```

### Right to Deletion (Quyền xóa dữ liệu)

Theo NĐ 13/2023, chủ thể dữ liệu có quyền yêu cầu xóa:

```python
async def handle_deletion_request(user_id: str, request_id: str):
    """Process data deletion request."""
    # 1. Verify identity
    # 2. Identify all data belonging to user
    # 3. Delete extraction results
    # 4. Delete analysis reports
    # 5. Retain audit logs (legal requirement)
    # 6. Generate deletion certificate
    # 7. Notify user of completion
    pass
```

---

## Incident Response

### Quy trình xử lý sự cố bảo mật

```
1. DETECT    → Phát hiện sự cố (monitoring, alert)
2. CONTAIN   → Ngăn chặn lan rộng (isolate, block)
3. ASSESS    → Đánh giá mức độ ảnh hưởng
4. NOTIFY    → Thông báo các bên liên quan
5. REMEDIATE → Khắc phục sự cố
6. REVIEW    → Rút kinh nghiệm, cập nhật quy trình
```

### Phân loại sự cố

| Mức | Mô tả | Thời gian phản hồi |
|---|---|---|
| P1 - Critical | Data breach, unauthorized access | < 1 giờ |
| P2 - High | Service disruption, data corruption | < 4 giờ |
| P3 - Medium | Performance degradation, minor leak | < 24 giờ |
| P4 - Low | Configuration issue, false positive | < 72 giờ |

---

## Security Checklist

### Trước khi deploy

- [ ] Tất cả API endpoints yêu cầu authentication
- [ ] PII masking hoạt động trong logs
- [ ] Encryption at rest cho dữ liệu nhạy cảm
- [ ] HTTPS enforced cho tất cả connections
- [ ] Rate limiting configured
- [ ] File upload validation (type, size, virus scan)
- [ ] Temp files auto-deleted sau processing
- [ ] Audit logging enabled
- [ ] Error messages không leak thông tin nhạy cảm
- [ ] CORS configured đúng (không wildcard)
- [ ] API keys rotated định kỳ
- [ ] Dependency vulnerabilities scanned
- [ ] Penetration testing completed

### Monitoring liên tục

- [ ] Failed login attempts monitoring
- [ ] Unusual data access patterns
- [ ] API rate limit violations
- [ ] File processing errors
- [ ] Encryption key expiry alerts
- [ ] Certificate expiry alerts
- [ ] Disk space for audit logs
