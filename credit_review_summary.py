"""Credit Review Summary có cấu trúc (tác vụ LLM #2) + guardrail ngôn ngữ quyết định + hậu kiểm Python.

- ``CreditReviewSummary``: 10 mục, KHÔNG có trường quyết định cho vay (``extra="forbid"``).
- ``chua_ngon_ngu_quyet_dinh``: chặn khuyến nghị phê duyệt/từ chối (tiếng Việt + Anh), không chặn câu trung tính.
- ``hau_kiem_tom_tat``: (a) số liệu khớp JSON đầu vào, (b) risk_code/evidence_ref hợp lệ, (c) đủ 10 mục,
  (d) trạng thái trùng Python, (e) không có ngôn ngữ quyết định.
- ``render_markdown``: UI và báo cáo xuất chỉ render từ JSON đã validate.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

TRANG_THAI = ("REVIEW READY", "HUMAN REVIEW REQUIRED", "INSUFFICIENT INFORMATION")
MUC_TOM_TAT = (
    ("tong_quan", "1. Tổng quan khách hàng"),
    ("de_nghi_vay", "2. Đề nghị vay vốn"),
    ("tai_chinh_da_xac_minh", "3. Thông tin tài chính đã xác minh"),
    ("chi_so", "4. Chỉ số tín dụng"),
    ("kiem_tra_nhat_quan", "5. Kiểm tra nhất quán"),
    ("canh_bao", "6. Cảnh báo rủi ro"),
    ("thong_tin_thieu", "7. Thông tin còn thiếu"),
    ("cau_hoi_xac_minh", "8. Câu hỏi cần xác minh"),
    ("bang_chung", "9. Bằng chứng"),
    ("trang_thai_xem_xet", "10. Trạng thái xem xét của con người"),
)
HAU_KIEM_LABEL = "Output AI không vượt hậu kiểm"


class CanhBaoTomTat(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_code: str = Field(min_length=2, max_length=60)
    noi_dung: str = Field(min_length=1, max_length=1200)
    evidence_ref: str = Field(min_length=1, max_length=200)


class CreditReviewSummary(BaseModel):
    """10 mục của Credit Review Summary. Không có trường quyết định cho vay."""

    model_config = ConfigDict(extra="forbid")

    tong_quan: str = Field(min_length=1, max_length=2000)
    de_nghi_vay: str = Field(min_length=1, max_length=2000)
    tai_chinh_da_xac_minh: str = Field(min_length=1, max_length=2000)
    chi_so: list[str]
    kiem_tra_nhat_quan: str = Field(min_length=1, max_length=2000)
    canh_bao: list[CanhBaoTomTat]
    thong_tin_thieu: list[str]
    cau_hoi_xac_minh: list[str]
    bang_chung: list[str]
    trang_thai_xem_xet: Literal["REVIEW READY", "HUMAN REVIEW REQUIRED", "INSUFFICIENT INFORMATION"]

    @field_validator("tong_quan", "de_nghi_vay", "tai_chinh_da_xac_minh", "kiem_tra_nhat_quan")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Mục không được để trống.")
        return value.strip()


class LoiHauKiemAI(RuntimeError):
    """Output LLM không vượt hậu kiểm: không đưa vào báo cáo xuất; facts Python vẫn hiển thị."""

    def __init__(self, vi_pham: list[str]) -> None:
        self.vi_pham = list(vi_pham)
        super().__init__(f"{HAU_KIEM_LABEL}: " + "; ".join(self.vi_pham[:6]))


# ==========================================================
# JSON schema cho LLM
# ==========================================================

def gemini_response_schema() -> dict[str, Any]:
    """responseSchema (OpenAPI subset) cho Gemini generateContent."""

    text = {"type": "STRING"}
    texts = {"type": "ARRAY", "items": {"type": "STRING"}}
    return {
        "type": "OBJECT",
        "properties": {
            "tong_quan": text,
            "de_nghi_vay": text,
            "tai_chinh_da_xac_minh": text,
            "chi_so": texts,
            "kiem_tra_nhat_quan": text,
            "canh_bao": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {"risk_code": text, "noi_dung": text, "evidence_ref": text},
                    "required": ["risk_code", "noi_dung", "evidence_ref"],
                },
            },
            "thong_tin_thieu": texts,
            "cau_hoi_xac_minh": texts,
            "bang_chung": texts,
            "trang_thai_xem_xet": {"type": "STRING", "enum": list(TRANG_THAI)},
        },
        "required": [key for key, _ in MUC_TOM_TAT],
        "propertyOrdering": [key for key, _ in MUC_TOM_TAT],
    }


def huong_dan_json() -> str:
    """Chỉ dẫn JSON cho provider không hỗ trợ responseSchema (OpenAI/Claude/DeepSeek)."""

    return (
        "\n\nĐỊNH DẠNG ĐẦU RA: trả về DUY NHẤT một đối tượng JSON hợp lệ (không Markdown, không ```), "
        "đúng các khóa sau và không thêm khóa khác: "
        + json.dumps(CreditReviewSummary.model_json_schema(), ensure_ascii=False)
    )


YEU_CAU_TOM_TAT = (
    "Hãy soạn Credit Review Summary theo đúng 10 mục (tong_quan, de_nghi_vay, tai_chinh_da_xac_minh, chi_so, "
    "kiem_tra_nhat_quan, canh_bao, thong_tin_thieu, cau_hoi_xac_minh, bang_chung, trang_thai_xem_xet). "
    "Mỗi cảnh báo dùng đúng 'loai' trong JSON làm risk_code và 'ma_rui_ro' (VD: R-001) làm evidence_ref. "
    "Chỉ dùng con số có trong JSON (giữ nguyên cách làm tròn), không tự tính số mới. "
    "trang_thai_xem_xet phải bằng đúng 'trang_thai' trong JSON. Không đưa khuyến nghị phê duyệt/từ chối.\n\n"
)


# ==========================================================
# Guardrail ngôn ngữ quyết định (dùng chung cho Summary và chat)
# ==========================================================

_VI_ACTION = r"(phê duyệt|duyệt vay|giải ngân|cấp tín dụng|cho vay|từ chối)"
PROHIBITED_DECISION_PATTERNS: tuple[str, ...] = (
    # "khuyến nghị/đề xuất/nên … phê duyệt/giải ngân/từ chối"
    rf"\b(khuyến nghị|kiến nghị|đề xuất|đề nghị|nên)\s+(cho\s+|được\s+)?{_VI_ACTION}",
    # "đủ / không đủ / chưa đủ điều kiện (để) vay / cấp tín dụng / giải ngân"
    r"\b(đủ|không đủ|chưa đủ)\s+điều kiện\s+(để\s+)?(được\s+)?(vay|cấp tín dụng|giải ngân|phê duyệt|cho vay)",
    r"\b(quyết định|kết luận|đề xuất|khuyến nghị)\s*[:：]\s*(phê duyệt|từ chối|duyệt|cho vay|không cho vay|approve|reject)",
    r"\b(recommendation|decision|verdict)\s*[:：]\s*(approve|approved|reject|rejected|decline|declined|grant)",
    r"\brecommend(s|ed|ing)?\s+(that\s+\w+(\s+\w+){0,4}\s+)?(approv\w*|reject\w*|grant\w*|declin\w*|deny\w*)",
    r"\bshould\s+(not\s+)?(be\s+)?(approv\w*|reject\w*|grant\w*|declin\w*)",
    r"\b(not\s+)?eligible\s+for\s+(the\s+|this\s+|a\s+)?(loan|credit|financing)",
    r"\b(approve|approval|approved)\b",
    r"\b(reject|decline)\s+(the\s+|this\s+)?(loan|application)\b",
)
# Câu trung tính: quyết định thuộc con người, hoặc phủ định ("không phê duyệt", "does not approve").
_NEUTRAL_CONTEXT = re.compile(
    r"(con người|chuyên viên|hội đồng|cán bộ|human|credit officer|committee|reviewer|underwriter)",
    re.IGNORECASE,
)
_NEGATION_BEFORE = re.compile(r"(không|chưa|không được|does not|do not|doesn't|never|not)\s+(\S+\s+){0,2}$", re.IGNORECASE)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;\n])\s+|\n+")


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def chua_ngon_ngu_quyet_dinh(text: str) -> bool:
    """True nếu có câu khuyến nghị phê duyệt/từ chối/giải ngân (tiếng Việt hoặc tiếng Anh).

    - Luôn chặn: "nên/không nên …", "đủ/không đủ điều kiện …", "Kết luận/Recommendation: …",
      "should (not) be approved", "(not) eligible for the loan".
    - "khuyến nghị/đề xuất/recommend …": chặn, trừ khi bị phủ định ("Hệ thống không khuyến nghị phê duyệt…").
    - Từ đơn "approve/approval": chặn, trừ khi phủ định hoặc gắn với con người ("human approval", "credit committee").
    """

    for sentence in _SENTENCE_SPLIT.split(_nfc(text)):
        for pattern in PROHIBITED_DECISION_PATTERNS:
            for match in re.finditer(pattern, sentence, re.IGNORECASE):
                trigger = match.group(0).casefold()
                negated = bool(_NEGATION_BEFORE.search(sentence[: match.start()]))
                if re.match(r"(nên|đủ|không đủ|chưa đủ|should|not eligible|eligible)\b", trigger) or re.search(r"[:：]", trigger):
                    return True
                if re.match(r"(khuyến nghị|kiến nghị|đề xuất|đề nghị|recommend)", trigger):
                    if negated:
                        continue
                    return True
                if negated or _NEUTRAL_CONTEXT.search(sentence):
                    continue  # "requires human approval", "does not approve"
                return True
    return False


# ==========================================================
# Phân tích & hậu kiểm
# ==========================================================

def phan_tich_output(text: str) -> CreditReviewSummary:
    raw = (text or "").strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
    if fenced:
        raw = fenced.group(1)
    elif not raw.startswith("{") and "{" in raw:
        raw = raw[raw.index("{"): raw.rindex("}") + 1]
    try:
        data = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise LoiHauKiemAI(["(c) output không phải JSON hợp lệ"]) from exc
    try:
        return CreditReviewSummary.model_validate(data)
    except ValidationError as exc:
        fields = sorted({".".join(str(p) for p in err["loc"]) or "?" for err in exc.errors()})
        raise LoiHauKiemAI([f"(c) sai schema/thiếu mục: {', '.join(fields)[:200]}"]) from exc


_NUMBER = re.compile(r"(?<![\w\-/])(\d[\d.,]*\d|\d)(\s*(%|triệu|tr\b|tỷ|nghìn|ngàn|k\b|×|x\b))?", re.IGNORECASE)
_MULTIPLIER = {"triệu": 1e6, "tr": 1e6, "tỷ": 1e9, "nghìn": 1e3, "ngàn": 1e3, "k": 1e3}


def _parse_number(token: str) -> float | None:
    t = token
    if "." in t and "," in t:
        decimal = "," if t.rfind(",") > t.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        t = t.replace(thousands, "").replace(decimal, ".")
    elif "." in t:
        t = t.replace(".", "") if re.fullmatch(r"\d{1,3}(\.\d{3})+", t) else t
    elif "," in t:
        t = t.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+", t) else t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def trich_con_so(text: str) -> list[tuple[float, str]]:
    """[(giá trị, loại)] với loại ∈ {"percent", "plain"}; tiền 'x triệu/tỷ' được quy đổi."""

    output: list[tuple[float, str]] = []
    for match in _NUMBER.finditer(_nfc(text)):
        value = _parse_number(match.group(1))
        if value is None:
            continue
        unit = (match.group(3) or "").casefold()
        if unit == "%":
            output.append((value, "percent"))
        else:
            output.append((value * _MULTIPLIER.get(unit, 1.0), "plain"))
    return output


def _numbers_in_json(value: Any, sink: list[float]) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        sink.append(float(value))
    elif isinstance(value, str):
        sink.extend(number for number, _ in trich_con_so(value))
        sink.extend(number for number, kind in trich_con_so(value) if kind == "percent")
    elif isinstance(value, dict):
        for item in value.values():
            _numbers_in_json(item, sink)
    elif isinstance(value, list):
        for item in value:
            _numbers_in_json(item, sink)


def _strings(summary: CreditReviewSummary) -> Iterable[str]:
    data = summary.model_dump()
    for key, _label in MUC_TOM_TAT:
        value = data[key]
        if isinstance(value, str):
            yield value
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    yield from (str(v) for v in item.values())
                else:
                    yield str(item)


def hau_kiem_tom_tat(summary: CreditReviewSummary, payload: dict[str, Any]) -> list[str]:
    """Danh sách vi phạm (rỗng = vượt hậu kiểm). ``payload``: JSON đã giả danh hóa gửi cho LLM."""

    violations: list[str] = []
    allowed: list[float] = []
    _numbers_in_json(payload, allowed)
    percents = {round(v, 4) for v in allowed} | {round(v * 100, 4) for v in allowed if abs(v) <= 50}
    small_counts = {float(i) for i in range(0, 13)}  # đánh số mục, số lượng cảnh báo…

    # (a) số liệu khớp JSON (±0,1 điểm % cho tỷ lệ; tiền/số khác khớp tuyệt đối sau quy đổi)
    bad_numbers: list[str] = []
    for text in _strings(summary):
        for value, kind in trich_con_so(text):
            if kind == "percent":
                ok = any(abs(value - p) <= 0.1 + 1e-9 for p in percents)
            else:
                ok = value in small_counts or any(abs(value - a) <= max(1e-6, abs(a) * 1e-9) for a in allowed)
                ok = ok or any(abs(value - p) <= 0.1 + 1e-9 for p in percents if p < 1000)
            if not ok:
                bad_numbers.append(f"{value:g}{'%' if kind == 'percent' else ''}")
    if bad_numbers:
        violations.append("(a) số liệu không có trong JSON đầu vào: " + ", ".join(sorted(set(bad_numbers))[:8]))

    # (b) risk_code thuộc tập Python; evidence_ref là mã cảnh báo hoặc tài liệu nguồn
    risks = payload.get("canh_bao") or []
    risk_codes = {str(r.get("loai")) for r in risks if isinstance(r, dict)}
    refs = {str(r.get("ma_rui_ro")) for r in risks if isinstance(r, dict)}
    for risk in risks:
        for evidence in (risk.get("bang_chung") or []) if isinstance(risk, dict) else []:
            if isinstance(evidence, dict) and evidence.get("tai_lieu"):
                refs.add(str(evidence["tai_lieu"]))
    unknown = [item.risk_code for item in summary.canh_bao if item.risk_code not in risk_codes]
    if unknown:
        violations.append("(b) risk_code không do Python tạo: " + ", ".join(unknown[:6]))
    bad_refs = [item.evidence_ref for item in summary.canh_bao if not any(ref and ref in item.evidence_ref for ref in refs)]
    if bad_refs:
        violations.append("(b) evidence_ref không truy vết được: " + ", ".join(bad_refs[:6]))

    # (c) đủ 10 mục: schema đã bắt buộc mọi khóa; chuỗi không rỗng
    empty = [label for key, label in MUC_TOM_TAT if isinstance(getattr(summary, key), str) and not getattr(summary, key).strip()]
    if empty:
        violations.append("(c) mục trống: " + ", ".join(empty))

    # (d) trạng thái trùng Python
    if summary.trang_thai_xem_xet != payload.get("trang_thai"):
        violations.append(
            f"(d) trạng thái {summary.trang_thai_xem_xet} khác trạng thái Python {payload.get('trang_thai')}"
        )

    # (e) không có ngôn ngữ quyết định
    if any(chua_ngon_ngu_quyet_dinh(text) for text in _strings(summary)):
        violations.append("(e) chứa ngôn ngữ quyết định phê duyệt/từ chối")
    return violations


# ==========================================================
# Render & bản mẫu tất định
# ==========================================================

NHAN_TRANG_THAI_VI = {
    "REVIEW READY": "SẴN SÀNG ĐỂ THẨM ĐỊNH",
    "HUMAN REVIEW REQUIRED": "CẦN CON NGƯỜI XEM XÉT",
    "INSUFFICIENT INFORMATION": "THÔNG TIN CHƯA ĐỦ",
}


def render_markdown(summary: CreditReviewSummary, footer: str = "") -> str:
    def bullets(items: list[str], empty: str) -> str:
        return "\n".join(f"- {item}" for item in items) or f"- {empty}"

    warnings = "\n".join(f"- **{w.risk_code}** ({w.evidence_ref}): {w.noi_dung}" for w in summary.canh_bao) or (
        "- Không có cảnh báo theo rule Python."
    )
    sections = {
        "tong_quan": summary.tong_quan,
        "de_nghi_vay": summary.de_nghi_vay,
        "tai_chinh_da_xac_minh": summary.tai_chinh_da_xac_minh,
        "chi_so": bullets(summary.chi_so, "Không có chỉ số."),
        "kiem_tra_nhat_quan": summary.kiem_tra_nhat_quan,
        "canh_bao": warnings,
        "thong_tin_thieu": bullets(summary.thong_tin_thieu, "Không phát hiện hạng mục bắt buộc còn thiếu."),
        "cau_hoi_xac_minh": bullets(summary.cau_hoi_xac_minh, "Không có câu hỏi bổ sung."),
        "bang_chung": bullets(summary.bang_chung, "Không có bằng chứng."),
        "trang_thai_xem_xet": f"**{NHAN_TRANG_THAI_VI[summary.trang_thai_xem_xet]}** ({summary.trang_thai_xem_xet})",
    }
    body = "\n\n".join(f"### {label}\n{sections[key]}" for key, label in MUC_TOM_TAT)
    return body + (f"\n\n{footer}" if footer else "")


def ban_tom_tat_tu_ket_qua(payload: dict[str, Any]) -> CreditReviewSummary:
    """Bản Summary tất định dựng từ JSON Python (đã giả danh hóa) — dùng cho mẫu nộp bài và test, không gọi LLM."""

    d = payload.get("du_lieu") or {}
    metrics = payload.get("chi_so") or []
    risks = payload.get("canh_bao") or []

    def money(key: str) -> str:
        value = d.get(key)
        return "Thông tin chưa đủ" if value is None else f"{float(value):,.0f}".replace(",", ".") + " VND"

    evidence = []
    for risk in risks:
        for item in risk.get("bang_chung") or []:
            evidence.append(
                f"{risk['ma_rui_ro']}: {item.get('tai_lieu')}, trang {item.get('trang') or 'không xác định'}, "
                f"{item.get('truong_du_lieu')} = {item.get('gia_tri')}"
            )
    return CreditReviewSummary(
        tong_quan=f"Khách hàng {d.get('ho_ten_khach_hang') or 'Thông tin chưa đủ'}, đơn vị công tác kê khai "
        f"{d.get('don_vi_cong_tac_ke_khai') or 'Thông tin chưa đủ'}, chức danh {d.get('chuc_danh_ke_khai') or 'Thông tin chưa đủ'}.",
        de_nghi_vay=f"Số tiền đề nghị vay {money('so_tien_de_nghi_vay')}; mục đích: {d.get('muc_dich_vay') or 'Thông tin chưa đủ'}.",
        tai_chinh_da_xac_minh=f"Thu nhập dùng để tính: {payload.get('nguon_thu_nhap_dung_de_tinh') or 'Không đủ dữ liệu'}. "
        f"Thu nhập kê khai {money('thu_nhap_ke_khai')}, lương thực nhận {money('luong_thuc_nhan')}, "
        f"ghi có bình quân sao kê {money('thu_nhap_qua_sao_ke')}.",
        chi_so=[f"{m['ten']}: {m['hien_thi']} ({m['trang_thai']})" for m in metrics],
        kiem_tra_nhat_quan=(
            "Rule Python phát hiện: " + ", ".join(r["loai"] for r in risks) + "."
            if risks
            else "Rule Python không phát hiện mâu thuẫn trọng yếu."
        ),
        canh_bao=[
            CanhBaoTomTat(risk_code=r["loai"], noi_dung=r["giai_thich"], evidence_ref=r["ma_rui_ro"]) for r in risks
        ],
        thong_tin_thieu=list(payload.get("thong_tin_thieu") or []),
        cau_hoi_xac_minh=list(payload.get("cau_hoi_xac_minh") or []),
        bang_chung=evidence,
        trang_thai_xem_xet=payload.get("trang_thai") or "HUMAN REVIEW REQUIRED",
    )
