# Harness Engineering

## Công thức cốt lõi

```
Product/Agent = Core Engine (Model) + Harness
```

- **Core Engine (Model)** — Trí thông minh thô (LLM, thuật toán ML). Cung cấp khả năng suy luận, sinh nội dung, phân tích.
- **Harness (Bộ khung bọc ngoài)** — Biến trí thông minh thô thành sản phẩm chạy ổn định, an toàn và đáng tin cậy trong môi trường Production.

## Kiến trúc 5 Hệ thống con

```
┌─────────────────────────────────────────────────────────┐
│                        HARNESS                          │
│               Agent = Model + Harness                   │
│                                                         │
│   ┌───────────┐                    ┌───────────────┐    │
│   │  HƯỚNG DẪN │◄──────────────────►│  TRẠNG THÁI  │    │
│   │ Introduction│                    │    State      │    │
│   └─────┬─────┘                    └──────┬────────┘    │
│         │                                  │            │
│         ▼                                  ▼            │
│   ┌───────────┐        ┌─────┐     ┌───────────────┐    │
│   │ VÒNG ĐỜI  │◄──────►│CORE │◄───►│  XÁC MINH    │    │
│   │  PHIÊN    │        │     │     │ Verification  │    │
│   │  Session  │        └─────┘     └───────────────┘    │
│   └─────┬─────┘                          ▲            │
│         │                                  │            │
│         ▼                                  │            │
│   ┌───────────────┐                       │            │
│   │   PHẠM VI     │───────────────────────┘            │
│   │    Scope      │                                     │
│   └───────────────┘                                     │
└─────────────────────────────────────────────────────────┘
```

Mỗi hệ thống con hoạt động **độc lập** nhưng kết nối qua **Repository**.

| # | Subsystem | Tên tiếng Việt | Vai trò |
|---|-----------|---------------|---------|
| 1 | Introduction | Hướng dẫn & Ngữ cảnh | Cung cấp context và operating manual cho agent |
| 2 | State | Trạng thái & Bộ nhớ | Bridge gap giữa ephemeral context và persistent reality |
| 3 | Verification | Xác minh & Kiểm tra | Đảm bảo agent chỉ declare "done" khi có bằng chứng |
| 4 | Scope | Phạm vi & Ràng buộc | Giới hạn và kiểm soát phạm vi hoạt động |
| 5 | Session Lifecycle | Vòng đời phiên | Quản lý lifecycle của mỗi phiên làm việc |

## Nguyên tắc thiết kế

1. **Repository là nguồn sự thật duy nhất** — Mọi state, instruction, evidence đều sống trong repo
2. **Progressive Disclosure** — Agent chỉ load thông tin cần thiết tại thời điểm cần
3. **Gate-based Verification** — Không được skip level, mỗi gate phải PASS trước khi lên tiếp
4. **Immutable Evidence** — Mọi thay đổi đều được ghi lại qua git commits
5. **Tool-agnostic** — Hoạt động với mọi AI coding tool (Claude Code, Copilot, Cursor, Kiro, Aider)

## Tài liệu chi tiết

- [Subsystem 1: Introduction](./01-subsystem-introduction.md)
- [Subsystem 2: State](./02-subsystem-state.md)
- [Subsystem 3: Verification](./03-subsystem-verification.md)
- [Subsystem 4: Scope](./04-subsystem-scope.md)
- [Subsystem 5: Session Lifecycle](./05-subsystem-session-lifecycle.md)
- [Project Structure](./06-project-structure.md)
- [AGENTS.md Template](./07-agents-md-template.md)
- [init.sh Template](./08-init-sh-template.md)
- [feature_list.json Template](./09-feature-list-json-template.md)
- [claude-progress.md Template](./10-progress-template.md)
- [verify.sh Template](./11-verify-sh-template.md)
