# Project Structure (Cấu trúc Project chuẩn)

## Cấu trúc đầy đủ cho production project

```
YOUR-PROJECT/
│
├── AGENTS.md                    ← HARNESS: operating manual
├── init.sh                      ← HARNESS: session startup
├── verify.sh                    ← HARNESS: full verification
│
├── feature_list.json            ← STATE: task specification
├── claude-progress.md           ← STATE: session log
│
├── docs/
│   ├── architecture.md          ← INSTRUCTIONS: system design
│   ├── api-contracts.md         ← INSTRUCTIONS: API specs
│   ├── testing-guide.md         ← INSTRUCTIONS: how to test
│   ├── decisions/               ← INSTRUCTIONS: architectural decisions
│   │   ├── 001-database.md
│   │   └── 002-auth-strategy.md
│   └── troubleshooting.md       ← INSTRUCTIONS: known issues
│
├── scripts/
│   ├── check-db.ts              ← health check scripts
│   ├── seed-data.ts             ← test data setup
│   └── generate-feature-list.ts ← tooling
│
├── src/                         ← Application code
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── artifacts/
    ├── screenshots/             ← E2E verification evidence
    └── logs/                    ← Agent session logs
```

## Ý nghĩa từng thành phần

### AGENTS.md

Tài liệu duy nhất agent PHẢI đọc đầu mỗi session. **Không quá 200 dòng** (2026 best practice). Chứa essentials. Dùng symlink `ln -s AGENTS.md CLAUDE.md` nếu dùng Claude Code.

### init.sh

Script chuẩn hóa startup. Không bao giờ bắt đầu session mà không chạy cái này.

### verify.sh

Full pipeline verification. Chạy trước khi declare bất kỳ feature nào done.

### feature_list.json

Source of truth cho "cái gì cần làm" và "cái gì đã làm". JSON format để giảm risk agent edit nhầm.

### claude-progress.md

Human-readable session journal. Bridge context giữa sessions.

### docs/

Domain knowledge không cần đọc mỗi session nhưng cần khi implement specific features.

### artifacts/

Evidence của verification. Screenshots, logs. Chứng minh feature đã thực sự pass.

## Phân loại theo Subsystem

| File/Folder | Thuộc Subsystem | Đọc khi nào |
|-------------|----------------|-------------|
| AGENTS.md | Introduction | Mỗi session (bắt buộc) |
| docs/ | Introduction | Khi cần domain knowledge |
| feature_list.json | State + Scope | Mỗi session (bắt buộc) |
| claude-progress.md | State + Session | Mỗi session (bắt buộc) |
| init.sh | Session Lifecycle | Đầu mỗi session |
| verify.sh | Verification | Trước khi declare done |
| artifacts/ | Verification | Khi cần evidence |
| scripts/ | Session Lifecycle | Khi cần tooling |

## Nguyên tắc tổ chức

1. **Root-level files là Harness files** — Agent thấy ngay khi mở project
2. **docs/ là reference material** — Đọc khi cần, không load toàn bộ
3. **scripts/ là automation** — Hỗ trợ init, verify, seed data
4. **artifacts/ là evidence** — Chứng minh verification đã pass
5. **src/ và tests/ là application code** — Nơi agent thực sự làm việc
