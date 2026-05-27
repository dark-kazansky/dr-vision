# Subsystem 3: Verification (Xác minh & Kiểm tra)

## Mục đích

Verification subsystem đảm bảo: *agent chỉ declare "done" khi có bằng chứng thực sự rằng feature hoạt động.*

Đây là subsystem **quan trọng nhất** để ngăn **Premature Victory pattern** — hiện tượng agent tuyên bố hoàn thành khi code chưa thực sự work.

## Nguyên tắc cốt lõi

> **Agent KHÔNG ĐƯỢC declare là DONE cho đến khi TẤT CẢ các cấp độ verification báo PASS.**

## Verification Pyramid (Kim tự tháp Xác minh)

```
                    ▲ Độ tin cậy
                   ╱ ╲
                  ╱ L5 ╲         Kiểm thử E2E
                 ╱───────╲       Playwright, luồng người dùng đầy đủ
                ╱   L4    ╲      Kiểm thử Smoke
               ╱───────────╲     Kiểm tra sức khỏe cơ bản
              ╱     L3      ╲    Build
             ╱───────────────╲   Biên dịch, đóng gói, không lỗi
            ╱      L2        ╲   Kiểm thử đơn vị
           ╱─────────────────╲   Jest / Vitest / Pytest
          ╱       L1          ╲  Phân tích tĩnh
         ╱─────────────────────╲ Lint, kiểm tra kiểu dữ liệu
        ╱         L0            ╲ Sức khỏe môi trường
       ╱─────────────────────────╲ Dependencies, servers đang chạy
       ────────────────────────────
                Tốc độ ►
```

| Level | Tên | Công cụ | Thời gian | Mô tả |
|-------|-----|---------|-----------|-------|
| L0 | Environment Health | `./init.sh`, health check | ~2s | Dependencies installed, servers running |
| L1 | Static Analysis | `npm run lint`, `npm run type-check` | ~5s | Lint pass, type check pass, 0 errors |
| L2 | Unit Tests | `npm test`, `pytest` | ~30s | Tất cả unit tests pass |
| L3 | Build | `npm run build`, `docker build` | ~60s | Biên dịch thành công, không lỗi |
| L4 | Smoke Tests | App start, basic navigation | ~120s | Ứng dụng khởi động, routes cơ bản hoạt động |
| L5 | E2E Tests | Playwright, Cypress | ~300s | Luồng người dùng đầy đủ pass |

## Quy tắc Gate

### Quy tắc #1: Chạy từ dưới lên

```
L0 → L1 → L2 → L3 → L4 → L5
```

Luôn bắt đầu từ L0. Không được skip level.

### Quy tắc #2: Fail = DỪNG LẠI

Nếu bất kỳ gate nào fail → **DỪNG LẠI**, fix trước khi tiếp tục lên level tiếp theo.

```
L0: PASS ✓
L1: PASS ✓
L2: FAIL ✗ ← DỪNG TẠI ĐÂY
L3: (không chạy)
L4: (không chạy)
L5: (không chạy)
```

### Quy tắc #3: Mỗi level phải PASS trước khi lên level tiếp theo

Không được chạy L3 nếu L2 chưa pass. Không có ngoại lệ.

### Quy tắc #4: Chỉ declare DONE khi tất cả gates PASS

```
status: "done" CHỈ KHI:
  L0: PASS ✓
  L1: PASS ✓
  L2: PASS ✓
  L3: PASS ✓
  L4: PASS ✓
  L5: PASS ✓
```

## Verification Gate Protocol

```bash
# Verification gates theo thứ tự bắt buộc:

# Gate 0: Environment health (~2s)
./init.sh  # hoặc health check script

# Gate 1: Static Analysis (~5s)
npm run lint        # 0 errors
npm run type-check  # 0 errors

# Gate 2: Unit Tests (~30s)
npm test  # tất cả pass

# Gate 3: Build (~60s)
npm run build  # success, no errors

# Gate 4: Smoke Tests (~120s)
# → App starts successfully
# → Basic navigation works
# → Key endpoints respond

# Gate 5: Feature E2E (~300s)
# → Mỗi test_step trong feature_list.json pass
# → Evidence được ghi lại
```

## Cập nhật State sau Verification

Chỉ khi GATE 0-5 đều pass:

```json
{
  "feature": "feature-x",
  "status": "done",
  "passes": {
    "L0": true,
    "L1": true,
    "L2": true,
    "L3": true,
    "L4": true,
    "L5": true
  },
  "verified_at": "2026-05-19T10:30:00Z"
}
```

## Premature Victory Pattern (Anti-pattern)

### Triệu chứng
- Agent nói "Done! Feature X is complete" sau khi viết code
- Không có evidence nào cho thấy code thực sự chạy
- Không chạy tests, không verify build

### Nguyên nhân
- Agent optimize cho "task completion" thay vì "correctness"
- Thiếu verification gates trong workflow
- Không có enforcement mechanism

### Giải pháp
- Verification subsystem bắt buộc chạy tất cả gates
- State chỉ update sau verification pass
- Definition of Done rõ ràng trong AGENTS.md

## Áp dụng cho các ngôn ngữ/framework khác

### Python (FastAPI/Django)

```bash
# L0: Environment
python -c "import fastapi; print('OK')"

# L1: Static Analysis
ruff check .
mypy .

# L2: Unit Tests
pytest tests/unit/

# L3: Build
pip install -e .  # hoặc docker build

# L4: Smoke
uvicorn main:app &
curl http://localhost:8000/health

# L5: E2E
pytest tests/e2e/
```

### Frontend (Nuxt/Vue)

```bash
# L0: Environment
node -v && npm list nuxt

# L1: Static Analysis
npm run lint
npx vue-tsc --noEmit

# L2: Unit Tests
npx vitest --run

# L3: Build
npm run build

# L4: Smoke
npm run preview &
curl http://localhost:3000

# L5: E2E
npx playwright test
```
