# CreditLens UI v2 — Cluster 6 Handoff

## Phạm vi đã hoàn thành

Cụm 6 bổ sung trang **Cài đặt và trợ lý AI** cho UI v2, đồng thời giữ nguyên toàn bộ luồng bảo mật và inference hiện hữu ở Python/Streamlit. Phạm vi gồm trạng thái kết nối, provider/model, ngưỡng phiên, trạng thái chat/lịch sử, session state, loading/error an toàn, responsive và accessibility.

Không thay đổi extraction, công thức tín dụng, Rule Engine, schema, validation chéo tài liệu, risk classification, Evaluation/Gold Cases, provider adapters, hành vi tính phí hoặc deployment.

## Runtime và rollback

- `CREDITLENS_UI_V2=0`: legacy UI giữ nguyên.
- `CREDITLENS_UI_V2=1`: các trang 1–8 dùng v2; trang 8 render lớp tổng quan React an toàn và controls Streamlit native bên dưới.
- Nếu component v2 không khả dụng hoặc payload không hợp lệ, shell hiện tại tiếp tục dùng fallback Python đã có.
- Không xóa legacy path và không deploy production trong Cụm 6.

## Kiến trúc nguồn dữ liệu

```text
Python session state / provider catalog / thresholds
              |
              | strict allowlist, no credential/chat content
              v
      Settings view-model an toàn
              |
              v
 React summary (presentation-only)

Native Streamlit controls ──> Python provider adapter ──> provider API
```

React không sở hữu API key, không gửi browser event ở trang Settings, không gọi provider API và không giữ nội dung chat. Python vẫn là source of truth cho provider/model, thresholds, chat history và mọi inference request.

## Security boundary

- API key nhập qua `st.text_input(..., type="password")` và chỉ tồn tại trong session memory hiện hữu.
- Settings view-model chỉ cho phép metadata an toàn: provider label, model đang chọn, số model khả dụng, trạng thái kết nối, ngưỡng và session flags.
- Không serialize raw API key, fingerprint, danh sách key, raw provider error hoặc nội dung chat.
- Contract guard từ chối cả secret-shaped field lồng sâu.
- UI chỉ nhận thông báo lỗi đã chuẩn hóa; logger an toàn vẫn redaction secret.
- Không dùng `localStorage`, telemetry hay browser-side provider request.

## Provider và model

UI đọc catalog backend hiện hữu và thể hiện bốn provider hiện hành:

- OpenAI / GPT
- Google / Gemini
- Anthropic / Claude
- DeepSeek

Không hard-code một provider mặc định cho inference. Việc nhận diện, xác thực, tải model và chọn model vẫn do Python xử lý. Đổi provider/model không phát sinh inference request.

## Ngưỡng phiên

Trang Settings hiển thị đúng tám giá trị từ `nguong_hieu_luc(...)`:

1. Độ tin cậy tối thiểu
2. Chênh lệch thu nhập
3. Chênh lệch thu nhập nghiêm trọng
4. Chênh lệch nợ
5. Cảnh báo DTI
6. Cảnh báo DSR
7. Hệ số đệm số dư tối thiểu
8. Biến động thu nhập cao

Controls chỉnh sửa vẫn là Streamlit native và chỉ cập nhật session state theo luồng cũ; không thay đổi threshold defaults hoặc logic sử dụng ngưỡng.

## Chat và request semantics

| Tương tác | Số inference request |
|---|---:|
| Send prompt hợp lệ #1 | 1 |
| Send prompt hợp lệ #2 | 1 |
| Rerun | 0 |
| Render history | 0 |
| Prompt rỗng/whitespace | 0 |
| Đổi provider/model | 0 |

Lịch sử hội thoại và context vẫn được Python giữ trong session; React chỉ nhận số lượt tin nhắn hợp lệ và cờ có/không context hồ sơ.

## Error và loading

- Kết nối có ba trạng thái văn bản: `CONNECTED`, `NOT CONFIGURED`, `ERROR`; không dựa riêng vào màu.
- Raw provider exception không được đưa vào React props.
- Nút gửi chat bị disable khi chưa có provider/model hợp lệ hoặc trong lúc gửi theo hành vi cũ.
- Lỗi provider được trình bày bằng thông điệp an toàn đã chuẩn hóa.

## Responsive và accessibility

- Desktop, compact desktop, tablet và mobile dùng cùng source of truth.
- Settings grids thu gọn theo các breakpoint 1280/1024/768; mobile dùng một cột và controls native không tràn viewport.
- Tabs native hỗ trợ bàn phím; focus state rõ; password input có label; trạng thái kết nối/chat có nhãn văn bản.
- `prefers-reduced-motion` tắt transition không thiết yếu.

## Xác minh

- Python UI tests: 36/36 pass.
- Python UI + evaluation regression: 46/46 pass.
- Frontend tests: 24/24 pass.
- TypeScript typecheck: pass.
- Production build: pass; `frontend/dist` đã rebuild.
- Browser QA: Settings page, native tabs, 8 thresholds, password masking/clearing, keyboard navigation, mobile 390 px, tablet 800 px, compact desktop 1100 px và desktop 1440 px.
- Console browser: không có warning/error.
- UI-only additional inference calls: 0.

## Deferred

- **Deferred to Cluster 7:** hardening/release validation hoặc các yêu cầu Cụm 7 chưa được kích hoạt.
- **Deferred to Cluster 8:** deployment/production rollout hoặc các yêu cầu Cụm 8 chưa được kích hoạt.

