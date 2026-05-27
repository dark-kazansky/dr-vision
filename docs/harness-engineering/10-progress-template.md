# claude-progress.md: Template và Best Practices

## Template

```markdown
# Claude Progress Log: Knowledge Base Desktop App

**Quy ước:** Mỗi session thêm entry mới ở đầu file (newest first).
Đọc 3-5 entries gần nhất để hiểu context.

## Session #5: 2025-04-06 · Thực hiện bởi: Claude Opus 4.5

### Mục tiêu ban đầu:
Implement feat-003: Document indexing với ChromaDB

### Đã làm:
- Init ChromaDB trong Electron main process
- Implement IndexService: `src/main/services/IndexService.ts`
- Background indexing khi import tài liệu
- Progress indicator trong status bar
- Unit tests cho IndexService: 12 tests, tất cả pass
- Smoke test sau indexing: OK

### Verification results:
- `npm run lint`: 0 errors ✓
- `npm run type-check`: 0 errors ✓
- `npm test`: 20/20 passed ✓
- Tất cả 8 test_steps feat-003: PASSED ✓

### feat-003 status: DONE ✅

### Ghi chú quan trọng:
- ChromaDB client cần `chromadb` npm package (đã thêm vào package.json)
- Indexing có thể chậm với documents >5MB, ghi chú trong feat-008
- [NOTED] Phát hiện memory leak tiềm năng trong document list renderer
  → Cần investigate nhưng không trong scope của feat-003
  → Tracked: ISSUE-memory-leak-doc-list

### Commit trong session này:

a1b2c3d feat(index): initialize ChromaDB in main process
d4e5f6g feat(index): implement IndexService with background indexing
g7h8i9j feat(ui): add indexing progress to status bar
j0k1l2m test(index): add IndexService unit tests
m3n4o5p feat(index): complete feat-003, all verifications pass

### Session tiếp theo NÊN:
1. Chạy `./init.sh` như thường lệ
2. Verify feat-003 still passes (smoke test)
3. Bắt đầu feat-004: "Search với semantic query"
4. feat-004 phụ thuộc vào ChromaDB đã setup ở feat-003 → OK

### Session tiếp theo KHÔNG NÊN:
- Không investigate memory leak trước khi feat-004 done
- Không optimize ChromaDB config trước khi basic search work
- Không touch IndexService nếu không cần cho search

---

## Session #4: 2025-04-05 · Thực hiện bởi: Claude Opus 4.5

### Mục tiêu ban đầu:
Implement feat-002: Document library management

... [entry ngắn hơn cho sessions cũ hơn]

---

## Session #3: 2025-04-04

... [tiếp tục]
```

## Cấu trúc mỗi Session Entry

Mỗi entry PHẢI có các section sau:

| Section | Bắt buộc | Mô tả |
|---------|----------|-------|
| Mục tiêu ban đầu | ✓ | Feature nào đang làm |
| Đã làm | ✓ | Liệt kê cụ thể những gì đã implement |
| Verification results | ✓ | Kết quả từng gate |
| Status | ✓ | DONE ✅ hoặc IN PROGRESS 🔄 hoặc BLOCKED 🚫 |
| Ghi chú quan trọng | Nếu có | Dependencies mới, noted issues, warnings |
| Commits | ✓ | Danh sách commits trong session |
| Session tiếp theo NÊN | ✓ | Hướng dẫn rõ ràng cho session sau |
| Session tiếp theo KHÔNG NÊN | ✓ | Cảnh báo scope creep |

## Best Practices

### 1. Newest first

Entry mới nhất luôn ở đầu file. Agent đọc từ trên xuống, chỉ cần 3-5 entries gần nhất.

### 2. Cụ thể, không chung chung

```markdown
# ❌ Không tốt:
- Đã làm nhiều thứ cho search feature
- Tests pass

# ✓ Tốt:
- Implement SearchService: `src/main/services/SearchService.ts`
- Thêm semantic search endpoint qua IPC: `search:query`
- Unit tests: 8/8 pass, coverage 92%
```

### 3. Session tiếp theo NÊN/KHÔNG NÊN

Đây là phần quan trọng nhất cho continuity. Phải cụ thể:

```markdown
# ❌ Không tốt:
### Session tiếp theo:
- Tiếp tục làm

# ✓ Tốt:
### Session tiếp theo NÊN:
1. Chạy ./init.sh
2. Verify feat-003 still passes
3. Bắt đầu feat-004

### Session tiếp theo KHÔNG NÊN:
- Không refactor IndexService
- Không optimize trước khi basic flow work
```

### 4. NOTED issues rõ ràng

```markdown
- [NOTED] Phát hiện memory leak tiềm năng trong document list renderer
  → Cần investigate nhưng không trong scope của feat-003
  → Tracked: ISSUE-memory-leak-doc-list
```

### 5. Giữ file manageable

- Khi file quá dài (>50 sessions), archive sessions cũ vào `artifacts/logs/`
- Giữ 10-15 sessions gần nhất trong file chính
