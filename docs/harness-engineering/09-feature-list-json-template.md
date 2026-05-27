# feature_list.json: Bản thiết kế đầy đủ

Đây là schema đầy đủ với giải thích từng field:

## Template

```json
{
  "project": "Knowledge Base Desktop App",
  "version": "1.0.0",

  "schema_version": "2",
  "last_updated": "2025-04-06T10:30:00Z",
  "updated_by_session": 5,

  "summary": {
    "total": 12,
    "done": 4,
    "pending": 8
  },

  "features": [
    {
      "id": "feat-001",

      "category": "core",
      // Loại feature: core | functional | polish | infrastructure

      "priority": 1,
      // 1 = highest priority, lower numbers done first

      "description": "User có thể import tài liệu local (.md và .txt)",
      // Một câu mô tả rõ ràng, testable

      "acceptance_criteria": [
        "File dialog mở khi click nút 'Import Document'",
        "Chỉ file .md và .txt xuất hiện trong dialog",
        "Sau import, tài liệu xuất hiện trong document list với tên đúng",
        "Nội dung tài liệu có thể đọc được khi click vào"
      ],
      // Những tiêu chí cụ thể, đo lường được

      "test_steps": [
        "Launch app",
        "Click nút 'Import Document' ở sidebar",
        "Verify file dialog mở",
        "Chọn file test: tests/fixtures/sample.md",
        "Verify file xuất hiện trong document list",
        "Click vào file trong list",
        "Verify nội dung sample.md hiển thị đúng trong main pane",
        "Lặp lại với tests/fixtures/sample.txt",
        "Thử import file .pdf → verify bị từ chối hoặc handled gracefully"
      ],
      // Đây là script test thủ công. Agent phải thực hiện từng bước.

      "dependencies": [],
      // Features phải done trước khi feature này có thể làm

      "estimated_complexity": "low",
      // low | medium | high | very-high

      "passes": true,
      // false = chưa xong | true = đã verify pass

      "last_attempted": "2025-04-01T09:15:00Z",
      // Timestamp của lần verify gần nhất

      "evidence": {
        "test_run": "npm test → 8 passed, 0 failed",
        "e2e": "All 9 test steps passed manually in Session #2",
        "screenshot": "artifacts/screenshots/feat-001-done.png",
        "verified_by_session": 2
      },
      // Bằng chứng verification, ai đó có thể kiểm tra lại

      "notes": "File dialog filter không hoạt động trên Linux, tracked separately"
      // Ghi chú thêm không fit vào fields khác
    },

    {
      "id": "feat-002",
      "category": "core",
      "priority": 2,
      "description": "User có thể quản lý document library (xem, xóa, rename)",
      "acceptance_criteria": [
        "Document list hiển thị tất cả imported documents",
        "Mỗi document hiển thị: tên, size, ngày import",
        "Right-click menu có options: Rename, Delete",
        "Delete yêu cầu confirmation",
        "Rename updates tên hiển thị ngay lập tức"
      ],
      "test_steps": [
        "Import 3 tài liệu test",
        "Verify tất cả 3 xuất hiện trong list với metadata đúng",
        "Right-click document đầu tiên → verify context menu xuất hiện",
        "Click Rename → verify có thể type tên mới → press Enter",
        "Verify tên update trong list",
        "Right-click document thứ 2 → Delete → verify confirmation dialog",
        "Confirm delete → verify document biến mất khỏi list",
        "Cancel delete → verify document vẫn còn"
      ],
      "dependencies": ["feat-001"],
      "estimated_complexity": "medium",
      "passes": false,
      "last_attempted": null,
      "evidence": null,
      "notes": "Cần careful UI testing cho rename flow"
    }
  ]
}
```

## Giải thích Schema

### Metadata (top-level)

| Field | Mô tả | Ai update |
|-------|--------|-----------|
| `project` | Tên project | Developer (1 lần) |
| `version` | Version hiện tại | Developer |
| `schema_version` | Version của schema format | Developer |
| `last_updated` | Timestamp lần update cuối | Agent (tự động) |
| `updated_by_session` | Session nào update cuối | Agent (tự động) |
| `summary` | Tổng hợp nhanh | Agent (tính lại mỗi update) |

### Feature fields

| Field | Mô tả | Bắt buộc | Ai update |
|-------|--------|----------|-----------|
| `id` | ID duy nhất (feat-XXX) | ✓ | Developer |
| `category` | core / functional / polish / infrastructure | ✓ | Developer |
| `priority` | 1 = cao nhất | ✓ | Developer |
| `description` | Mô tả ngắn, testable | ✓ | Developer |
| `acceptance_criteria` | Tiêu chí đo lường được | ✓ | Developer |
| `test_steps` | Script test thủ công | ✓ | Developer |
| `dependencies` | Features phải done trước | ✓ | Developer |
| `estimated_complexity` | low/medium/high/very-high | ✓ | Developer |
| `passes` | false/true | ✓ | Agent (chỉ sau verify) |
| `last_attempted` | Timestamp verify gần nhất | ✓ | Agent |
| `evidence` | Bằng chứng verification | ✓ | Agent |
| `notes` | Ghi chú bổ sung | Optional | Cả hai |

### Quy tắc quan trọng

1. **Agent chỉ được update**: `passes`, `last_attempted`, `evidence`, `notes`
2. **Agent KHÔNG được**: xóa features, thay đổi `test_steps`, sửa `acceptance_criteria`
3. **`passes: true`** chỉ khi TẤT CẢ test_steps đã thực hiện và pass
4. **`evidence`** phải đủ chi tiết để người khác có thể verify lại
5. **`dependencies`** phải tất cả passes: true trước khi bắt đầu feature này
