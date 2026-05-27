# Subsystem 1: Introduction (Hướng dẫn & Ngữ cảnh)

## Mục đích

Introduction subsystem cung cấp **operating manual** cho agent — tất cả context cần thiết để agent hiểu project và biết cách làm việc đúng cách.

Đây là subsystem đầu tiên agent tiếp xúc khi bắt đầu mỗi session.

## Các thành phần

### AGENTS.md — Tầng trung tâm (Tool-agnostic Standard)

| Thuộc tính | Mô tả |
|-----------|-------|
| Vai trò | Sổ tay vận hành của agent (operating manual) |
| Khi nào đọc | Luôn được đọc ở đầu mỗi session |
| Nội dung | Startup procedure, invariants, definition of done, key commands |
| Giới hạn | **Không nên quá 200 dòng** (đủ ngắn để đọc toàn bộ mỗi session) |
| Tương thích | Standard mở, hoạt động với mọi tool: Claude Code, Copilot, Cursor, Kiro, Aider |

### CLAUDE.md — Tool-specific Override cho Claude Code

| Thuộc tính | Mô tả |
|-----------|-------|
| Vai trò | Thay hoặc bổ sung AGENTS.md cho Claude Code |
| Tính năng | Hierarchy imports (`@path/to/file`), local-only overrides |
| Best practice 2026 | Dùng `symlink ln -s AGENTS.md CLAUDE.md` — một file cho cả hai tools |

### docs/ — Tầng Domain Knowledge

| Thuộc tính | Mô tả |
|-----------|-------|
| Nội dung | Kiến trúc hệ thống, API contracts, Testing strategies, Architectural decisions |
| Cách dùng | Được tham chiếu từ AGENTS.md khi cần, không inline |
| Nguyên tắc | Chỉ đọc khi agent cần hiểu sâu về một domain cụ thể |

### feature_list.json — Tầng Task Specification

| Thuộc tính | Mô tả |
|-----------|-------|
| Vai trò | Mỗi feature là một instruction về *cái gì phải làm* và *cách verify* |
| Đặc điểm | Chi tiết hơn AGENTS.md nhưng granular hơn docs/ |
| Cách dùng | Đọc entry cụ thể khi implement feature X |

## Progressive Disclosure Pattern

```
Session start → đọc AGENTS.md (luôn luôn)
       ↓
Khi cần hiểu architecture → đọc docs/architecture.md
       ↓
Khi implement feature X → đọc feature_list entry cho X
       ↓
Khi gặp lỗi → đọc docs/troubleshooting.md
```

### Tại sao Progressive Disclosure?

1. **Tiết kiệm context window** — Agent không cần load toàn bộ docs vào memory
2. **Giảm nhiễu** — Chỉ thông tin relevant tại thời điểm cần
3. **Scalable** — Project lớn đến đâu cũng không làm tràn context
4. **Deterministic** — Agent luôn biết đọc gì tiếp theo dựa trên tình huống

## Ví dụ cấu trúc thư mục

```
project-root/
├── AGENTS.md                    # Operating manual (< 200 dòng)
├── CLAUDE.md -> AGENTS.md       # Symlink cho Claude Code
├── feature_list.json            # Task specifications
├── docs/
│   ├── architecture.md          # System architecture
│   ├── api-contracts.md         # API specifications
│   ├── testing-strategy.md      # How to test
│   └── troubleshooting.md       # Common issues & fixes
└── ...
```

## Nguyên tắc viết AGENTS.md

1. **Ngắn gọn** — Dưới 200 dòng, mỗi dòng có giá trị
2. **Actionable** — Mỗi instruction phải rõ ràng, không mơ hồ
3. **Tham chiếu** — Link đến docs/ thay vì inline nội dung dài
4. **Cập nhật** — Phản ánh trạng thái hiện tại của project, không phải lịch sử
5. **Invariants rõ ràng** — Những quy tắc KHÔNG BAO GIỜ được vi phạm
