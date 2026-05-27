# Subsystem 2: State (Trạng thái & Bộ nhớ)

## Mục đích

State subsystem giải quyết vấn đề cốt lõi: *AI agents là stateless, nhưng projects không là stateless.*

Cần bridge gap giữa **agent's ephemeral context** và **project's persistent reality**.

## Ba tầng State

### Tầng 1: MACHINE-READABLE STATE

| Thuộc tính | Mô tả |
|-----------|-------|
| File | `feature_list.json` |
| Câu hỏi trả lời | "Feature X đang ở trạng thái nào ngay lúc này?" |
| Dạng dữ liệu | Structured JSON, atomic updates |
| Ai update | Agent (chỉ passes/status fields) |
| Ai đọc | Agent + tooling scripts |

**Đặc điểm:**
- Cấu trúc cố định, dễ parse
- Mỗi update là atomic (thay đổi 1 field tại 1 thời điểm)
- Là nguồn sự thật cho automation và CI/CD
- Agent đọc file này đầu session để biết "đang ở đâu"

### Tầng 2: HUMAN-READABLE SESSION LOG

| Thuộc tính | Mô tả |
|-----------|-------|
| File | `claude-progress.md` (hoặc `agent-progress.md`) |
| Câu hỏi trả lời | "Trong session X, điều gì đã xảy ra và tại sao?" |
| Dạng dữ liệu | Narrative markdown |
| Ai update | Agent (cuối mỗi session) |
| Ai đọc | Agent (đầu session sau) + Developer |

**Đặc điểm:**
- Viết bằng ngôn ngữ tự nhiên
- Ghi lại decisions, blockers, và reasoning
- Giúp session tiếp theo hiểu context mà không cần hỏi lại
- Developer có thể đọc để hiểu agent đã làm gì

### Tầng 3: IMMUTABLE CODE HISTORY

| Thuộc tính | Mô tả |
|-----------|-------|
| Tool | `git log` |
| Câu hỏi trả lời | "Thay đổi code cụ thể nào đã được thực hiện?" |
| Dạng dữ liệu | Git commits với messages |
| Ai update | Agent (sau verification pass) |
| Ai đọc | Agent + Developer + CI/CD |

**Đặc điểm:**
- Immutable — không thể sửa đổi sau khi commit
- Mỗi commit gắn với một verification pass
- Commit messages mô tả *what* và *why*
- Là audit trail cuối cùng

## Mối quan hệ giữa 3 tầng

```
┌─────────────────────────────────────────────────────┐
│                   STATE FLOW                         │
│                                                     │
│  feature_list.json    agent-progress.md   git log   │
│  ┌──────────────┐    ┌───────────────┐   ┌──────┐  │
│  │ status:      │    │ Session #5:   │   │ abc12│  │
│  │  "in_progress"│───►│ Started work  │───►│ feat:│  │
│  │              │    │ on feature X  │   │ add X│  │
│  │ passes:      │    │              │   │      │  │
│  │  L0: true    │    │ Blocked by Y  │   │ def34│  │
│  │  L1: true    │    │ Resolved via Z│   │ fix: │  │
│  │  L2: false   │    │              │   │ fix Y│  │
│  └──────────────┘    └───────────────┘   └──────┘  │
│                                                     │
│  Machine-readable     Human-readable    Immutable   │
│  (current state)      (narrative)       (history)   │
└─────────────────────────────────────────────────────┘
```

## Quy tắc cập nhật State

### Khi nào update feature_list.json?
- Khi bắt đầu work trên feature → `status: "in_progress"`
- Khi một verification gate pass → `passes.L0: true`
- Khi hoàn thành tất cả gates → `status: "done"`
- Khi gặp blocker → `status: "blocked"`

### Khi nào update agent-progress.md?
- Cuối mỗi session (bắt buộc)
- Khi có decision quan trọng cần ghi lại
- Khi gặp blocker cần context cho session sau

### Khi nào commit?
- Sau khi verification gate pass (không commit code chưa verify)
- Mỗi commit là một đơn vị logic hoàn chỉnh
- Commit message theo conventional format

## Anti-patterns

| Anti-pattern | Vấn đề | Giải pháp |
|-------------|--------|-----------|
| Không update state | Session sau không biết đang ở đâu | Bắt buộc update cuối session |
| Update state trước verify | State nói "done" nhưng code broken | Chỉ update sau verification pass |
| Commit chưa verify | Main branch có code lỗi | Gate verification trước commit |
| Quá nhiều state files | Khó biết đâu là source of truth | Giữ đúng 3 tầng, không thêm |
