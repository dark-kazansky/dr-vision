# Subsystem 4: Scope (Phạm vi & Ràng buộc)

## Mục đích

Scope subsystem ngăn hai failure modes đối lập:

- **Overreach:** Agent làm quá nhiều (scope creep)
- **Under-finish:** Agent làm chưa đủ (surface-level implementation)

## One Feature at a Time Principle

Đây là nguyên tắc đơn giản nhất nhưng bị vi phạm nhiều nhất.

### Tại sao "one feature at a time" quan trọng đến vậy?

**Khi agent cố làm nhiều features song song:**

1. Context window split giữa nhiều concerns
2. State trở nên inconsistent, một feature "half-done" ảnh hưởng đến tests của feature khác
3. Verification không thể isolate, nếu tests fail, không biết feature nào gây ra
4. Rất khó để rollback nếu có sự cố

**Khi agent chỉ làm một feature:**

1. Toàn bộ context tập trung vào một vấn đề
2. State rõ ràng, trước và sau implementation
3. Verification isolate, nếu fail, biết ngay là feature này
4. Rollback dễ dàng, chỉ ảnh hưởng một feature

## Definition of Done (DoD)

DoD là phần quan trọng nhất của Scope subsystem. Nó trả lời: *"Chính xác khi nào một feature được coi là hoàn thành?"*

Một DoD tốt phải:
- **Cụ thể, không mơ hồ**: có thể trả lời Yes/No cho từng criterion
- **Không phụ thuộc vào cảm giác**: không "trông có vẻ đúng"
- **Testable**: có thể verify tự động hoặc bằng steps rõ ràng

### Definition of Done Checklist

Một feature được coi là DONE khi VÀ CHỈ KHI:

**Technical:**
- Unit tests pass (`npm test`, 0 failures)
- TypeScript type check pass (0 errors)
- Linting pass (0 warnings nếu strict, 0 errors always)
- Build success (`npm run build`)

**Functional:**
- TẤT CẢ test_steps trong feature_list.json thực hiện thủ công pass
- Edge cases được handle (empty state, error state, loading state)
- Feature hoạt động offline (nếu app cần offline support)

**Documentation:**
- feature_list.json: passes → true, evidence ghi lại
- agent-progress.md: session entry với summary
- Git commit với descriptive message

**Clean State:**
- Không có debug code (`console.log`, `debugger`)
- Không có commented-out code blocks lớn
- Không có TODO comments về feature này (chuyển thành separate issue)

## Stop-and-Note Pattern

Pattern quan trọng để prevent scope creep khi agent tình cờ phát hiện vấn đề khác:

### Kịch bản

```
Agent đang implement feat-007 (search)
Agent phát hiện bug trong feat-003 (import)
```

### KHÔNG ĐÚNG: Fix feat-003 luôn

→ Dẫn đến scope creep, untested changes, có thể regression

### ĐÚNG: Stop-and-Note

→ Ghi vào progress log:

```
"[NOTED - Session 7] Bug phát hiện trong import:
  File >10MB gây UI freeze. Không liên quan đến feat-007.
  Cần investigate sau feat-007 hoàn thành.
  Tracked as: ISSUE-import-freeze-large-files"
```

→ Tiếp tục với feat-007

### Sau khi feat-007 xong

Agent hoặc developer quyết định có giải quyết noted bug hay không, theo priority.

## Scope Boundaries

### Được phép (In-scope)

- Thay đổi files liên quan trực tiếp đến feature
- Thêm tests cho code mới
- Update documentation cho thay đổi
- Fix lỗi phát sinh từ thay đổi của mình

### Không được phép (Out-of-scope)

- Refactor code không liên quan
- Thêm features không được yêu cầu
- Thay đổi coding style của code hiện có
- Upgrade dependencies không liên quan
- "Cải thiện" performance khi không được yêu cầu
- Fix bug ở feature khác (dùng Stop-and-Note)

## Scope Enforcement

### Trước khi thực hiện thay đổi

Agent phải tự hỏi:
1. File này có nằm trong scope của feature hiện tại không?
2. Thay đổi này có phục vụ trực tiếp cho feature không?
3. Có vi phạm invariant nào không?
4. Nếu bỏ thay đổi này, feature có còn hoạt động không?

Nếu câu 4 trả lời "Có" → thay đổi đó là out-of-scope.

## Anti-patterns

| Anti-pattern | Mô tả | Giải pháp |
|-------------|--------|-----------|
| Scope Creep | Agent tự mở rộng phạm vi | Stop-and-Note pattern |
| Under-finish | Agent declare done khi chưa đủ DoD | DoD checklist enforcement |
| Yak Shaving | Fix A → cần fix B → cần fix C... | Dừng lại, ghi noted issue |
| Gold Plating | Thêm tính năng "nice to have" | Chỉ làm đúng requirement |
| Multi-feature | Làm nhiều features cùng lúc | One Feature at a Time |
| Premature Optimization | Optimize code chưa cần | Chỉ optimize khi có evidence |
