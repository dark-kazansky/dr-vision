# 01 - Các Loại Tài Liệu Ngân Hàng

## Tổng quan

Hệ thống hỗ trợ phân loại và xử lý các loại tài liệu ngân hàng phổ biến tại Việt Nam và quốc tế.

## Danh sách loại tài liệu

### 1. Sao kê tài khoản (Bank Statement)

| Thuộc tính | Giá trị |
|---|---|
| Mã loại | `bank_statement` |
| Mô tả | Sao kê giao dịch tài khoản thanh toán/tiết kiệm hàng tháng |
| Đặc điểm nhận dạng | Logo ngân hàng, số tài khoản, bảng giao dịch, số dư đầu/cuối kỳ |
| Độ ưu tiên | Cao |

**Dữ liệu khai thác:**
- Thông tin tài khoản (số TK, chủ TK, chi nhánh)
- Số dư đầu kỳ / cuối kỳ
- Danh sách giao dịch (ngày, mô tả, số tiền, loại)
- Tổng thu / tổng chi

---

### 2. Sao kê thẻ tín dụng (Credit Card Statement)

| Thuộc tính | Giá trị |
|---|---|
| Mã loại | `credit_card_statement` |
| Mô tả | Bảng kê chi tiêu thẻ tín dụng hàng tháng |
| Đặc điểm nhận dạng | Số thẻ (masked), hạn mức, dư nợ, ngày thanh toán tối thiểu |
| Độ ưu tiên | Cao |

**Dữ liệu khai thác:**
- Thông tin thẻ (số thẻ masked, loại thẻ, hạn mức)
- Dư nợ kỳ trước / kỳ này
- Thanh toán tối thiểu
- Chi tiết giao dịch (ngày, merchant, số tiền, ngoại tệ)
- Lãi suất áp dụng

---

### 3. Hợp đồng vay (Loan Agreement)

| Thuộc tính | Giá trị |
|---|---|
| Mã loại | `loan_agreement` |
| Mô tả | Hợp đồng tín dụng / vay vốn |
| Đặc điểm nhận dạng | Số hợp đồng, bên vay/cho vay, số tiền vay, lãi suất, kỳ hạn |
| Độ ưu tiên | Trung bình |

**Dữ liệu khai thác:**
- Thông tin bên vay / bên cho vay
- Số tiền vay, lãi suất, kỳ hạn
- Lịch trả nợ (amortization schedule)
- Tài sản đảm bảo
- Điều kiện giải ngân

---

### 4. Tài liệu KYC (Know Your Customer)

| Thuộc tính | Giá trị |
|---|---|
| Mã loại | `kyc_document` |
| Mô tả | Giấy tờ xác minh danh tính khách hàng |
| Đặc điểm nhận dạng | CMND/CCCD, hộ chiếu, giấy phép kinh doanh |
| Độ ưu tiên | Cao |

**Dữ liệu khai thác:**
- Họ tên, ngày sinh, giới tính
- Số CMND/CCCD, ngày cấp, nơi cấp
- Địa chỉ thường trú
- Ảnh chân dung (nếu có)

---

### 5. Séc & Phiếu nộp tiền (Check / Deposit Slip)

| Thuộc tính | Giá trị |
|---|---|
| Mã loại | `check_deposit` |
| Mô tả | Séc ngân hàng hoặc phiếu nộp/rút tiền |
| Đặc điểm nhận dạng | Số séc, người thụ hưởng, số tiền bằng số và chữ |
| Độ ưu tiên | Trung bình |

**Dữ liệu khai thác:**
- Số séc, ngày phát hành
- Người phát hành / thụ hưởng
- Số tiền (bằng số và bằng chữ)
- Ngân hàng phát hành

---

### 6. Xác nhận chuyển khoản (Transfer Confirmation)

| Thuộc tính | Giá trị |
|---|---|
| Mã loại | `transfer_confirmation` |
| Mô tả | Biên lai xác nhận chuyển khoản / chuyển tiền |
| Đặc điểm nhận dạng | Mã giao dịch, TK nguồn/đích, số tiền, thời gian |
| Độ ưu tiên | Trung bình |

**Dữ liệu khai thác:**
- Mã giao dịch
- Tài khoản nguồn / đích
- Tên người gửi / nhận
- Số tiền, phí chuyển
- Nội dung chuyển khoản
- Thời gian giao dịch

---

### 7. Báo cáo tài chính (Financial Report)

| Thuộc tính | Giá trị |
|---|---|
| Mã loại | `financial_report` |
| Mô tả | Báo cáo tài chính doanh nghiệp (P&L, Balance Sheet) |
| Đặc điểm nhận dạng | Tiêu đề báo cáo, kỳ báo cáo, bảng số liệu tài chính |
| Độ ưu tiên | Trung bình |

**Dữ liệu khai thác:**
- Doanh thu, chi phí, lợi nhuận
- Tổng tài sản, nợ phải trả, vốn chủ sở hữu
- Dòng tiền hoạt động / đầu tư / tài chính
- Các chỉ số tài chính (ROE, ROA, D/E ratio)

---

### 8. Hợp đồng bảo hiểm (Insurance Document)

| Thuộc tính | Giá trị |
|---|---|
| Mã loại | `insurance_document` |
| Mô tả | Hợp đồng bảo hiểm nhân thọ / phi nhân thọ |
| Đặc điểm nhận dạng | Số hợp đồng BH, người được BH, quyền lợi, phí BH |
| Độ ưu tiên | Thấp |

**Dữ liệu khai thác:**
- Loại bảo hiểm, số hợp đồng
- Người mua / người được bảo hiểm
- Số tiền bảo hiểm, phí bảo hiểm
- Thời hạn hợp đồng
- Quyền lợi bảo hiểm

---

### 9. Tài liệu thế chấp (Mortgage Document)

| Thuộc tính | Giá trị |
|---|---|
| Mã loại | `mortgage_document` |
| Mô tả | Hợp đồng thế chấp bất động sản / tài sản |
| Đặc điểm nhận dạng | Thông tin tài sản, giá trị định giá, điều khoản thế chấp |
| Độ ưu tiên | Thấp |

**Dữ liệu khai thác:**
- Thông tin tài sản thế chấp
- Giá trị định giá
- Tỷ lệ cho vay / giá trị tài sản (LTV)
- Điều kiện giải chấp

---

### 10. Tài liệu thuế (Tax Document)

| Thuộc tính | Giá trị |
|---|---|
| Mã loại | `tax_document` |
| Mô tả | Tờ khai thuế, biên lai nộp thuế |
| Đặc điểm nhận dạng | Mã số thuế, kỳ kê khai, số thuế phải nộp |
| Độ ưu tiên | Thấp |

**Dữ liệu khai thác:**
- Mã số thuế, tên đơn vị
- Kỳ kê khai
- Doanh thu chịu thuế
- Số thuế phải nộp / đã nộp
- Loại thuế (GTGT, TNDN, TNCN)

---

## Classification Rules Configuration

```json
{
  "rules": [
    {
      "doc_type": "bank_statement",
      "description": "Sao kê tài khoản ngân hàng hàng tháng với danh sách giao dịch, số dư đầu/cuối kỳ"
    },
    {
      "doc_type": "credit_card_statement",
      "description": "Bảng kê chi tiêu thẻ tín dụng với thông tin merchant, dư nợ, hạn thanh toán"
    },
    {
      "doc_type": "loan_agreement",
      "description": "Hợp đồng tín dụng/vay vốn với lãi suất, kỳ hạn, lịch trả nợ"
    },
    {
      "doc_type": "kyc_document",
      "description": "Giấy tờ tùy thân (CMND, CCCD, hộ chiếu) hoặc giấy tờ xác minh danh tính"
    },
    {
      "doc_type": "check_deposit",
      "description": "Séc ngân hàng hoặc phiếu nộp/rút tiền mặt"
    },
    {
      "doc_type": "transfer_confirmation",
      "description": "Biên lai xác nhận chuyển khoản với mã giao dịch, TK nguồn/đích"
    },
    {
      "doc_type": "financial_report",
      "description": "Báo cáo tài chính doanh nghiệp (bảng cân đối, kết quả kinh doanh, lưu chuyển tiền tệ)"
    },
    {
      "doc_type": "insurance_document",
      "description": "Hợp đồng bảo hiểm với quyền lợi, phí bảo hiểm, thời hạn"
    },
    {
      "doc_type": "mortgage_document",
      "description": "Hợp đồng thế chấp tài sản với thông tin định giá, điều kiện giải chấp"
    },
    {
      "doc_type": "tax_document",
      "description": "Tờ khai thuế hoặc biên lai nộp thuế với mã số thuế, kỳ kê khai"
    }
  ]
}
```

## Ngân hàng Việt Nam được hỗ trợ

| STT | Ngân hàng | Mã | Ghi chú |
|---|---|---|---|
| 1 | Vietcombank | VCB | Sao kê PDF chuẩn |
| 2 | BIDV | BIDV | Sao kê PDF/Excel |
| 3 | VietinBank | CTG | Sao kê PDF |
| 4 | Techcombank | TCB | Sao kê PDF/ảnh |
| 5 | MB Bank | MBB | Sao kê PDF |
| 6 | ACB | ACB | Sao kê PDF |
| 7 | VPBank | VPB | Sao kê PDF |
| 8 | TPBank | TPB | Sao kê PDF/ảnh |
| 9 | Sacombank | STB | Sao kê PDF |
| 10 | HDBank | HDB | Sao kê PDF |
