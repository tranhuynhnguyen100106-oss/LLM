# Đánh giá tín dụng vay

Hệ thống hỗ trợ thẩm định khoản vay: tính DTI/DSR xác định, đối chiếu chéo chứng từ, cảnh báo rủi ro minh bạch và **trợ lý Google Gemini 3.8 Flash** (`gemini-3.8-flash`) trả lời dựa trên hồ sơ đang mở.

## Chạy nhanh

| Cách chạy | Lệnh | Gemini lấy khóa từ |
|---|---|---|
| Dev (React + Node) | `npm install && npm run dev` | biến `GEMINI_API_KEY` |
| Production trên Render | dùng `render.yaml` (service `danh-gia-tin-dung-vay`) | biến môi trường `GEMINI_API_KEY` |
| **Bản độc lập 1 tệp** (chạy trên mọi tên miền / hosting tĩnh: GitHub Pages, Netlify, Vercel…) | `npm run build:standalone` → `dist-standalone/index.html` | người dùng dán khóa vào nút 🔑 trong khung chat (lưu ở trình duyệt) |

Lấy khóa Gemini miễn phí tại https://aistudio.google.com/apikey.

### Chạy trên tên miền độc lập (GitHub Pages)

1. Repo → **Settings → Pages → Source: GitHub Actions**.
2. Chạy workflow *Deploy … to GitHub Pages* thủ công (Actions → Run workflow) → web có tại `https://<tài-khoản>.github.io/LLM/`. Workflow **không** tự chạy khi push lên `main`, vì bản độc lập gọi Gemini từ trình duyệt.
3. Tên miền riêng: tạo biến repo `CUSTOM_DOMAIN` (Settings → Secrets and variables → Actions → Variables), trỏ bản ghi CNAME của tên miền về `<tài-khoản>.github.io`.

> Khuyến nghị: với hệ thống thật, dùng chế độ có máy chủ để khóa API không lộ ra trình duyệt.

---

## Chạy trên Streamlit (bản chính thức · UI v3)

Bản công khai tại **https://creditlens-underwriting.streamlit.app** chạy giao diện "Đánh giá tín dụng vay" trên Streamlit:

- **Python là server và source of truth**: trích xuất PDF thật (pypdf), Privacy Gateway (Bước 0), công thức DTI/DSR, rules, ngưỡng, Evaluation, gọi LLM, xuất Word/Excel/PDF/Markdown/JSON (`app.py` → `creditlens_ui_v3.py`, `credit_underwriting_colab.py`, `privacy_gateway.py`, `evaluation/`).
- **React (`src/components`) là presentation layer**, đóng gói thành một Streamlit Component v2 ở `frontend-v3/`. Bundle `frontend-v3/dist/` **được commit** vì Streamlit Cloud không build Node. Khi build cho Streamlit, `src/lib/gemini.ts` được thay bằng `frontend-v3/src/geminiStub.ts`: không gọi Gemini từ trình duyệt và không lưu khóa vào localStorage. `src/domain/engine.ts` chỉ giữ lại để đối chiếu trong test.
- Luồng dữ liệu: Python → view model JSON (allowlist, đã giả danh hóa, không có API key) → React. React → event có kiểu (`event_id` duy nhất) → Python kiểm tra và chống xử lý trùng → thực thi. Mỗi lần Send tối đa 1 inference request.
- Thứ tự giao diện: **v3 → v2 → legacy**. Cờ `UI_V3_ENABLED` mặc định bật; đặt `UI_V3_ENABLED = "false"` để quay về v2. Nếu v3 lỗi, app tự chuyển sang v2.

**Cấu hình Gemini (chủ app tự làm):** Streamlit Cloud → app → ⋮ → Settings → **Secrets**, thêm `GEMINI_API_KEY = "…"`. Nếu không có khóa này, người dùng nhập khóa ở **Cài đặt → Kết nối AI** (ô mật khẩu gốc của Streamlit, chỉ lưu trong session Python). Model được chọn từ danh sách API trả về; nếu `gemini-3.8-flash` không có, app chọn model khả dụng đầu tiên và báo lại.

Rebuild giao diện v3 sau khi sửa `src/` hoặc `frontend-v3/src`:

```bash
cd frontend-v3 && pnpm install && pnpm test && pnpm build   # commit frontend-v3/dist
```

Các tệp Node (`server.ts`, `package.json`, `scripts/build-standalone.mjs`, `.github/workflows/pages.yml`, service Node trong `render.yaml`) được giữ nguyên để chạy bản React/Node. Streamlit không phụ thuộc vào các tệp này.

---

> **Nguyên tắc an toàn:** Ứng dụng hỗ trợ thẩm định và phân tích xác định; không tự phê duyệt hoặc từ chối khoản vay. Mọi quyết định cuối cùng bắt buộc do chuyên viên và Hội đồng Tín dụng xem xét.

---

## Kiến trúc và Công nghệ

Bản chính thức chạy trên **Streamlit**; Python là server và nguồn sự thật, React chỉ là lớp hiển thị:

- **Python** (`app.py` → `creditlens_ui_v3.py`): trích xuất PDF bằng pypdf + regex/alias, Privacy Gateway (`privacy_gateway.py`), công thức DTI/DSR và rule engine (`credit_underwriting_colab.py`), Evaluation (`evaluation/`), gọi LLM, xuất Word/Excel/PDF/Markdown/JSON.
- **React 19 + TypeScript** (`src/components`) được đóng gói thành **Streamlit Component v2** ở `frontend-v3/` (bundle `frontend-v3/dist/` được commit). Python gửi view model JSON đã giả danh hóa; React gửi event có kiểu về Python.
- Fallback giao diện: **v3 → v2 → legacy**.
- Sơ đồ pipeline đầy đủ (bước nào AI làm, bước nào con người duyệt): [`docs/workflow.md`](docs/workflow.md). Mẫu nộp bài (thư mục 4 PDF tổng hợp + Credit Review Summary mẫu): [`samples/`](samples/README.md).
- **Giới hạn PDF:** chỉ đọc PDF có lớp văn bản. **Chưa hỗ trợ OCR cho PDF scan** (failure case FAIL-01) — hồ sơ như vậy được báo “Không đọc được” và chuyển con người xem xét.

---

## 3 tác vụ LLM

Mọi phép tính do Python thực hiện; LLM chỉ làm 3 việc dưới đây. Mỗi tác vụ chạy khi chuyên viên bấm, **tối đa 1 inference request mỗi lần bấm**, dữ liệu gửi đi luôn qua Privacy Gateway (giả danh hóa + `assert_no_pii` fail-closed).

| # | Tác vụ | Loại | Kiểm soát | Con người |
|---|---|---|---|---|
| 1 | **Structured extraction** — bổ sung các trường số/ngày mà regex bỏ sót (`trich_xuat_bo_sung_bang_ai`) | Extraction | JSON `{field, value, unit, source_doc, page, quote}`; Python kiểm tra value + quote có thật trong trang PDF, không khớp → “Không tìm thấy căn cứ” | Từng trường phải bấm **Xác nhận** mới được dùng tính DTI/DSR |
| 2 | **Credit Review Summary** — báo cáo 10 mục (`tao_dien_giai_bang_ai`) | Report generation | JSON schema `CreditReviewSummary`; hậu kiểm số liệu, risk_code, đủ 10 mục, trạng thái, ngôn ngữ quyết định | Output không qua hậu kiểm không vào báo cáo xuất |
| 3 | **Hỏi đáp theo vai trò** — Thẩm định viên / Kiểm soát rủi ro / Cố vấn (`tao_phan_hoi_chat_ai`) | Q&A | Ngữ cảnh hồ sơ đã giả danh hóa; chặn khuyến nghị phê duyệt/từ chối | Quyết định cuối thuộc chuyên viên |

Ba vai trò chat là ba system prompt của **cùng một** tác vụ (3), không tính thành ba tác vụ.

---

## Cách chạy đánh giá

```bash
pip install -r requirements.txt
pytest tests/ evaluation/                       # toàn bộ test (không gọi LLM)
CREDITLENS_SELF_TEST=1 python credit_underwriting_colab.py
python -c "from evaluation.evaluator import run_evaluation, report_to_json; print(report_to_json(run_evaluation()))" > evaluation_report.json
```

`run_evaluation()` chấm 36 ca gold (12 kịch bản × 3 biến thể) **và** benchmark 20 bộ PDF tổng hợp chạy qua pipeline pypdf thật. Không gọi LLM (`llm_api_calls = 0`).

Đánh giá **output LLM thật** (Summary + Extraction) chạy riêng bằng khóa của người chạy, đọc từ biến môi trường:

```bash
export GEMINI_API_KEY=...        # không ghi vào repo
python scripts/run_llm_eval.py --model gemini-3.8-flash --cases 12
```

Kết quả lưu ở `evaluation/llm_outputs/<model>/` (đã giả danh hóa, không chứa khóa) và hiển thị ở trang Evaluation, tách riêng khỏi số liệu mô phỏng.

---

## 8 Phân hệ Chức năng Chính

1. **Tổng quan và Hồ sơ (`1_overview`):**
   - Vùng tiếp nhận tài liệu (Intake Area) hỗ trợ kéo thả hoặc chọn nhiều tệp PDF (Đơn vay, Chứng từ thu nhập, Sao kê ngân hàng, Nghĩa vụ nợ).
   - Bộ chọn 10 tình huống thử nghiệm (Demo Cases) tổng hợp xác định.
   - Stepper quy trình 4 chặng: Tiếp nhận → Tính toán xác định → Đối chiếu đa chứng từ → Con người xem xét.

2. **Trích xuất tài liệu (`2_extraction`):**
   - Danh mục tài liệu với trạng thái, số trang, loại nhận diện và điểm tin cậy (Confidence score).
   - 20 trường dữ kiện chuẩn hóa theo vai trò nguồn (Kê khai / Quan sát từ chứng từ / Tính toán).
   - Chi tiết bằng chứng nguồn (Evidence Disclosure) trích xuất từ tài liệu và số trang cụ thể.

3. **Phân tích tín dụng (`3_analysis`):**
   - Thẻ nguồn thu nhập cơ sở dùng để tính toán và trạng thái xác minh độc lập.
   - Lưới 6 chỉ số tài chính trọng yếu: DTI hiện hữu, DSR dự kiến, Thu nhập còn lại, Hệ số đệm số dư, Chênh lệch thu nhập, Biến động thu nhập.
   - Bảng đối chiếu chéo dữ liệu đa chứng từ (Thu nhập 3 nguồn, Đơn vị công tác, Nghĩa vụ nợ).

4. **Cảnh báo rủi ro (`4_risk`):**
   - Động cơ quy tắc xác định phát hiện mâu thuẫn: `INCOME_MISMATCH`, `EMPLOYER_MISMATCH`, `POSSIBLE_UNDECLARED_DEBT`, `HIGH_DTI_DEMO`, `HIGH_DSR_DEMO`, `LOW_BALANCE_BUFFER`, `HIGH_INCOME_VOLATILITY`, `LOW_EXTRACTION_CONFIDENCE`.
   - Phân loại mức độ nghiêm trọng: CAO (HIGH), TRUNG BÌNH (MEDIUM), THẤP (LOW), THÔNG TIN (INFO).
   - Trích dẫn bằng chứng đính kèm từng cảnh báo.

5. **Tóm tắt thẩm định (`5_summary`):**
   - Bảng tổng hợp quyết định cấp tín dụng (Decision-Support Hero) với thông tin khách hàng, khoản vay đề nghị.
   - Phân tách rõ ràng giữa *Deterministic findings* (kết quả tính toán xác định) và *Human review checklist* (câu hỏi và thông tin cần bổ sung).
   - Tùy chọn tạo diễn giải ngôn ngữ tự nhiên bằng AI hỗ trợ.
   - Nút xuất báo cáo: Tải Markdown (`.md`), Tải JSON có cấu trúc (`.json`), In / Lưu PDF.

6. **Phương pháp và Giới hạn (`6_methodology`):**
   - Kiến trúc 3 tầng: Dữ kiện → Phân tích xác định → Diễn giải AI.
   - 6 thẻ công thức tài chính kèm ý nghĩa và giới hạn đo lường.
   - Bảng ma trận năng lực xử lý các loại định dạng PDF.
   - Nhóm các giới hạn hệ thống và trách nhiệm con người.

7. **Evaluation Benchmark (`7_evaluation`):**
   - Bộ kiểm thử chất lượng: 36 ca gold (12 kịch bản × 3 biến thể) và benchmark 20 bộ PDF tổng hợp.
   - Scorecards độ chính xác trích xuất và phân loại.
   - Ma trận nhầm lẫn (Confusion Matrix) 3x3 cho trạng thái thẩm định.
   - So sánh baseline: không đối chiếu chéo (rule) và prompt chung chung không có JSON ngữ cảnh (LLM); số liệu output LLM thật tách riêng số liệu mô phỏng.
   - Danh mục 10 trường hợp ngoại lệ (Failure Cases) kèm nguyên nhân và giải pháp khắc phục.
   - Xuất kết quả đánh giá ra định dạng CSV và JSON.

8. **Cài đặt & Trợ lý AI (`8_settings`):**
   - Quản lý trạng thái kết nối các nhà cung cấp mô hình (Gemini, OpenAI, Claude, DeepSeek).
   - Thanh trượt tinh chỉnh 8 ngưỡng rủi ro minh họa trong phiên với tính năng **tính toán lại tức thì** trên toàn bộ ứng dụng.
   - Khung chat tương tác với trợ lý CreditLens trả lời câu hỏi nghiệp vụ dựa trên dữ kiện hồ sơ.

---

## Quyền riêng tư

CreditLens dùng **Privacy Gateway — Bước 0 · Bảo mật hồ sơ** (`privacy_gateway.py`) làm cửa duy nhất để đưa tài liệu vào hệ thống. Kỹ thuật là **giả danh hóa (pseudonymization/tokenization)**: thay thông tin định danh bằng mã. Hệ thống không mã hóa toàn bộ hồ sơ, vì LLM cần đọc được số liệu để diễn giải.

**Luồng xử lý**

1. Chuyên viên tick xác nhận bảo mật, rồi tải thư mục 3–4 PDF, tải từng tệp hoặc mở hồ sơ minh họa. Trang Bước 0 luôn hiển thị cảnh báo: *"Bản công khai chỉ dành cho dữ liệu tổng hợp hoặc đã ẩn danh. Không tải hồ sơ khách hàng thật."*
2. Hệ thống quét PII theo hai cách: lấy giá trị đã trích xuất vào `DuLieuHoSo`, và dùng regex Việt Nam để tìm CCCD 12 số, CMND 9 số, số điện thoại `0[35789]…`/`+84`, email, số tài khoản 8–19 số, cùng các dòng có nhãn như "Họ và tên:", "Địa chỉ:", "Ngày sinh:".
3. Bảng xem trước hiển thị loại PII, giá trị đã che, mã thay thế và tài liệu/trang. Chuyên viên có thể che thêm giá trị thủ công (mã `TC_xx`), nhưng không thể bỏ che các trường bắt buộc.
4. Khi bấm **"Giả danh hóa và tiếp tục"**, hệ thống tạo vault cho phiên và mở khóa các trang Trích xuất, Phân tích, Rủi ro, Tóm tắt và Chat. App Shell hiện huy hiệu "Đã giả danh hóa · N trường".

**Quy tắc thay thế**

| Loại | Xử lý | Ví dụ |
|---|---|---|
| Họ tên khách hàng / người liên quan | Thay bằng mã | `KH_01`, `NLQ_01` |
| CCCD/CMND/hộ chiếu | Che hoàn toàn, không lưu | `[CCCD_ĐÃ_CHE]` |
| Số tài khoản, số thẻ | Chỉ giữ 4 số cuối | `TK_****1234` |
| Số điện thoại, email | Che hoàn toàn | `[SĐT_ĐÃ_CHE]` |
| Địa chỉ | Chỉ giữ tỉnh/thành | `ĐC_01 (TP.HCM)` |
| Đơn vị công tác | Thay bằng mã, nhất quán giữa các tài liệu | `DN_A` |
| Ngày sinh | Chuyển thành nhóm tuổi | `30–35 tuổi` |
| Ngày bắt đầu làm việc | Chỉ giữ tháng/năm | `03/2021` |
| Số tiền, tỷ lệ, kỳ hạn | Giữ nguyên | — |

Trước khi gán mã, giá trị được chuẩn hóa (bỏ dấu, viết thường, gộp khoảng trắng). Nhờ vậy cùng một giá trị luôn nhận cùng một mã trên mọi tài liệu, và cảnh báo "đơn vị kê khai ≠ chứng từ" vẫn hoạt động (`DN_A ≠ DN_B`).

**Bảo đảm kỹ thuật**

- Mọi phép tính DTI/DSR, rule engine và nhãn rủi ro đều chạy trên kết quả gốc. Bản giả danh hóa chỉ là bản sao dùng để gửi LLM, xuất báo cáo và hiển thị.
- `du_lieu_gui_llm()` và khung chat chỉ gửi bản đã giả danh hóa. Ngay trước **mọi** request, hệ thống gọi `assert_no_pii()` theo cơ chế fail-closed: nếu payload còn giá trị thật, request bị chặn (0 inference) và chuyên viên nhận thông báo. System prompt được bổ sung câu: *"Dữ liệu đã được giả danh hóa. Giữ nguyên các mã như KH_01, DN_A; không suy đoán danh tính thật."*
- Vault chỉ nằm trong `st.session_state`: không ghi file, không ghi log, không tuần tự hóa, không gửi sang React. Với CCCD, số điện thoại, email và số tài khoản, vault chỉ giữ dấu vân tay HMAC theo phiên, không giữ giá trị thật.
- Kết quả AI mặc định hiển thị dạng mã. Nút "Hiện thông tin thật" chỉ có tác dụng trong phiên. Báo cáo Word/Excel/PDF mặc định là **Bản giả danh hóa**; có thể chọn **Bản đầy đủ**.
- Nút "Xóa hồ sơ khỏi phiên" xóa luôn vault. Nhật ký kiểm soát chỉ ghi số liệu (số trường theo loại, thời điểm, provider, kết quả assert), không ghi giá trị.
- Mỗi PDF giới hạn 10 MB (`GIOI_HAN_TEP` và `server.maxUploadSize = 10`). `.streamlit/secrets.toml` nằm trong `.gitignore`. API Key chỉ nằm trong phiên.

**Giới hạn:** máy chủ vẫn đọc file gốc trong bộ nhớ để trích xuất. Regex có thể bỏ sót PII viết tự do hoặc nằm trong PDF scan (không có OCR). Số liệu kết hợp với ngữ cảnh vẫn có thể giúp tái nhận dạng. Bản công khai chỉ dùng cho dữ liệu tổng hợp.
