"""Tác vụ LLM #1 — Structured extraction có grounding check (bổ sung trường SỐ/NGÀY mà regex bỏ sót).

Luồng: chuyên viên bấm "Bổ sung trích xuất bằng AI" → đoạn trích các trang liên quan (đã giả danh hóa
bằng ``pseudonymize_text``) → đúng 1 inference request (``assert_no_pii`` fail-closed) → JSON
``{field, value, unit, source_doc, page, quote}`` → Python kiểm tra value + quote có thật trong trang đó
→ đạt: "AI trích xuất — cần xác minh" (chờ chuyên viên bấm "Xác nhận"); không đạt: "Không tìm thấy căn cứ".

Giá trị AI CHỈ được dùng để tính DTI/DSR sau khi chuyên viên xác nhận từng trường.
Không dùng LLM cho trường định danh (họ tên, CCCD, đơn vị công tác…).
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationError

# field → (nhãn, loại tài liệu nguồn, kiểu dữ liệu)
TRUONG_AI: dict[str, tuple[str, tuple[str, ...], Literal["money", "months", "date"]]] = {
    "thu_nhap_ke_khai": ("Thu nhập hàng tháng kê khai", ("application",), "money"),
    "luong_thuc_nhan": ("Lương thực nhận", ("income",), "money"),
    "thu_nhap_qua_sao_ke": ("Ghi có bình quân hàng tháng (sao kê)", ("statement",), "money"),
    "so_tien_de_nghi_vay": ("Số tiền đề nghị vay", ("application",), "money"),
    "thoi_han_vay_thang": ("Thời hạn vay (tháng)", ("application",), "months"),
    "khoan_tra_du_kien": ("Khoản trả nợ dự kiến hàng tháng", ("application",), "money"),
    "nghia_vu_no_ke_khai": ("Nghĩa vụ nợ kê khai hàng tháng", ("application",), "money"),
    "nghia_vu_no_quan_sat": ("Nghĩa vụ nợ quan sát hàng tháng", ("debt", "statement"), "money"),
    "so_du_binh_quan": ("Số dư bình quân", ("statement",), "money"),
    "ngay_bat_dau_ke_khai": ("Ngày bắt đầu làm việc (đơn vay)", ("application",), "date"),
    "ngay_bat_dau_chung_tu": ("Ngày bắt đầu làm việc (chứng từ thu nhập)", ("income",), "date"),
}
NHAN_CAN_XAC_MINH = "AI trích xuất — cần xác minh"
NHAN_KHONG_CAN_CU = "Không tìm thấy căn cứ"
DO_TIN_CAY_DA_XAC_NHAN = 0.85
_MAX_PAGE_CHARS = 3000
_MAX_TOTAL_CHARS = 16000
_PAGE_SPLIT = re.compile(r"\n?--- TRANG (\d+) ---\n")

SYSTEM_PROMPT = """Bạn trích xuất dữ liệu có cấu trúc từ văn bản tài liệu tín dụng đã giả danh hóa.
- Chỉ trích các trường được yêu cầu. Chỉ dùng thông tin xuất hiện NGUYÊN VĂN trong văn bản.
- "quote" phải chép nguyên văn một đoạn ngắn (một dòng) chứa giá trị, từ đúng tài liệu và trang ghi trong "source_doc"/"page".
- "value": số tiền ghi bằng số VND (không dấu phân cách), số tháng là số nguyên, ngày giữ nguyên như trong văn bản.
- Không tìm thấy thì KHÔNG đưa trường đó vào kết quả. Không đoán, không tính toán, không suy diễn.
- Giữ nguyên các mã giả danh như KH_01, DN_A. Không đưa khuyến nghị phê duyệt/từ chối.
Trả về DUY NHẤT JSON: {"items": [{"field", "value", "unit", "source_doc", "page", "quote"}]}."""


class MucTrichXuatAI(BaseModel):
    model_config = ConfigDict(extra="ignore")

    field: str
    value: str | float | int
    unit: str = ""
    source_doc: str
    page: int = Field(ge=1)
    quote: str = Field(min_length=1, max_length=400)


class KetQuaTrichXuatAI(BaseModel):
    model_config = ConfigDict(extra="ignore")

    items: list[MucTrichXuatAI] = Field(default_factory=list)


def gemini_response_schema() -> dict[str, Any]:
    text = {"type": "STRING"}
    return {
        "type": "OBJECT",
        "properties": {
            "items": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "field": {"type": "STRING", "enum": list(TRUONG_AI)},
                        "value": text,
                        "unit": text,
                        "source_doc": {"type": "STRING", "enum": ["application", "income", "statement", "debt"]},
                        "page": {"type": "INTEGER"},
                        "quote": text,
                    },
                    "required": ["field", "value", "source_doc", "page", "quote"],
                },
            }
        },
        "required": ["items"],
    }


# ==========================================================
# Chuẩn bị đầu vào
# ==========================================================

def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def chia_trang(van_ban: str) -> dict[int, str]:
    parts = _PAGE_SPLIT.split(van_ban or "")
    pages: dict[int, str] = {}
    for index in range(1, len(parts) - 1, 2):
        try:
            pages[int(parts[index])] = parts[index + 1]
        except ValueError:
            continue
    return pages


def _doc_readable(doc: Any) -> bool:
    return doc is not None and getattr(doc, "trang_thai", "") != "Không đọc được" and bool(getattr(doc, "van_ban", ""))


def truong_can_bo_sung(result: Any, docs: Mapping[str, Any]) -> list[str]:
    """Trường SỐ/NGÀY regex trả None mà tài liệu nguồn có mặt và đọc được."""

    if result is None:
        return []
    data = result.du_lieu
    output = []
    for field, (_label, sources, _kind) in TRUONG_AI.items():
        if getattr(data, field, None) is None and any(_doc_readable(docs.get(key)) for key in sources):
            output.append(field)
    return output


def trang_da_gia_danh(docs: Mapping[str, Any], fields: list[str], vault: Any) -> dict[tuple[str, int], str]:
    """{(loại tài liệu, trang): văn bản đã giả danh hóa} của các tài liệu nguồn cần thiết."""

    from privacy_gateway import pseudonymize_text

    keys = sorted({key for field in fields for key in TRUONG_AI[field][1] if _doc_readable(docs.get(key))})
    pages: dict[tuple[str, int], str] = {}
    total = 0
    for key in keys:
        for number, text in chia_trang(docs[key].van_ban).items():
            masked = pseudonymize_text(text, vault)[:_MAX_PAGE_CHARS] if vault is not None else text[:_MAX_PAGE_CHARS]
            if total + len(masked) > _MAX_TOTAL_CHARS:
                break
            pages[(key, number)] = masked
            total += len(masked)
    return pages


def noi_dung_yeu_cau(fields: list[str], pages: Mapping[tuple[str, int], str]) -> str:
    wanted = "\n".join(f"- {field}: {TRUONG_AI[field][0]} (nguồn: {', '.join(TRUONG_AI[field][1])})" for field in fields)
    excerpts = "\n\n".join(f"[TÀI LIỆU {key} · trang {page}]\n{text.strip()}" for (key, page), text in pages.items())
    return f"Các trường cần trích xuất:\n{wanted}\n\nVăn bản (đã giả danh hóa):\n{excerpts}"


# ==========================================================
# Grounding check (Python)
# ==========================================================

def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", _nfc(text)).strip().casefold()


def _numbers(text: str) -> list[float]:
    from credit_review_summary import trich_con_so

    return [value for value, kind in trich_con_so(text) if kind == "plain"]


def _value_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    numbers = _numbers(str(value))
    return numbers[0] if len(numbers) == 1 else None


_MONTH_YEAR = re.compile(r"(?<!\d)(\d{1,2})[/\-.](\d{4})(?!\d)")
_FULL_DATE = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2}|\d{4}/\d{2}/\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})(?!\d)")


def _month_year(text: str) -> tuple[int, int] | None:
    from credit_underwriting_colab import chuan_hoa_ngay

    full = chuan_hoa_ngay(text)
    if full is not None:
        return full.month, full.year
    match = _MONTH_YEAR.search(text or "")
    return (int(match.group(1)), int(match.group(2))) if match else None


def kiem_tra_can_cu(
    item: MucTrichXuatAI,
    requested: list[str],
    masked_pages: Mapping[tuple[str, int], str],
    original_docs: Mapping[str, Any],
) -> dict[str, Any]:
    """Đạt → value chuẩn hóa (ngày: lấy ngày đầy đủ trong trang gốc). Không đạt → lý do."""

    base = {"field": item.field, "source_doc": item.source_doc, "page": item.page, "quote": item.quote[:300]}
    if item.field not in requested or item.field not in TRUONG_AI:
        return {**base, "status": "rejected", "reason": "Trường không được yêu cầu."}
    label, sources, kind = TRUONG_AI[item.field]
    base["label"] = label
    if item.source_doc not in sources:
        return {**base, "status": "rejected", "reason": f"{NHAN_KHONG_CAN_CU}: sai tài liệu nguồn."}
    page_text = masked_pages.get((item.source_doc, item.page))
    if page_text is None:
        return {**base, "status": "rejected", "reason": f"{NHAN_KHONG_CAN_CU}: trang không tồn tại hoặc không được gửi."}
    if _fold(item.quote) not in _fold(page_text):
        return {**base, "status": "rejected", "reason": f"{NHAN_KHONG_CAN_CU}: trích dẫn không có trong trang {item.page}."}

    if kind in {"money", "months"}:
        number = _value_number(item.value)
        if number is None or number < 0 or not any(abs(number - n) < 0.5 for n in _numbers(item.quote)):
            return {**base, "status": "rejected", "reason": f"{NHAN_KHONG_CAN_CU}: giá trị không xuất hiện trong trích dẫn."}
        if kind == "months" and (number != int(number) or not 1 <= number <= 600):
            return {**base, "status": "rejected", "reason": f"{NHAN_KHONG_CAN_CU}: kỳ hạn không hợp lệ."}
        return {**base, "status": "pending", "value": int(number) if kind == "months" else number, "reason": NHAN_CAN_XAC_MINH}

    # Ngày: văn bản gửi đi chỉ giữ tháng/năm → khớp với trích dẫn, rồi lấy ngày đầy đủ DUY NHẤT trong trang gốc.
    wanted = _month_year(str(item.value))
    if wanted is None or wanted != _month_year(item.quote):
        return {**base, "status": "rejected", "reason": f"{NHAN_KHONG_CAN_CU}: ngày không xuất hiện trong trích dẫn."}
    original_page = chia_trang(getattr(original_docs.get(item.source_doc), "van_ban", "")).get(item.page, "")
    from credit_underwriting_colab import chuan_hoa_ngay

    matches = {m for m in _FULL_DATE.findall(original_page) if (d := chuan_hoa_ngay(m)) and (d.month, d.year) == wanted}
    if len(matches) != 1:
        return {**base, "status": "rejected", "reason": f"{NHAN_KHONG_CAN_CU}: không xác định được ngày đầy đủ trong trang gốc."}
    return {**base, "status": "pending", "value": next(iter(matches)), "reason": NHAN_CAN_XAC_MINH}


def phan_tich_output(text: str) -> KetQuaTrichXuatAI:
    raw = (text or "").strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
    if fenced:
        raw = fenced.group(1)
    elif not raw.startswith("{") and "{" in raw:
        raw = raw[raw.index("{"): raw.rindex("}") + 1]
    try:
        return KetQuaTrichXuatAI.model_validate(json.loads(raw))
    except (ValueError, TypeError, ValidationError) as exc:
        raise RuntimeError("Output trích xuất AI không phải JSON hợp lệ theo schema (mã EXT-JSON).") from exc


# ==========================================================
# Gọi LLM (đúng 1 request) + áp dụng sau xác nhận
# ==========================================================

def trich_xuat_bo_sung_bang_ai(
    result: Any,
    docs: Mapping[str, Any],
    vault: Any,
    connection: Mapping[str, Any],
) -> dict[str, Any]:
    """1 inference request cho cả hồ sơ. Trả {"requested", "items"} — items đã qua grounding check."""

    from credit_underwriting_colab import tao_phan_hoi_chat_ai

    requested = truong_can_bo_sung(result, docs)
    if not requested:
        return {"requested": [], "items": []}
    pages = trang_da_gia_danh(docs, requested, vault)
    if not pages:
        return {"requested": requested, "items": []}
    output = tao_phan_hoi_chat_ai(
        [{"role": "user", "content": noi_dung_yeu_cau(requested, pages)}],
        str(connection.get("api_key") or ""),
        str(connection.get("provider") or ""),
        str(connection.get("model") or ""),
        vault,  # pseudonymize lại + assert_no_pii fail-closed trước khi gửi
        system_prompt=SYSTEM_PROMPT,
        response_schema=gemini_response_schema(),
    )
    parsed = phan_tich_output(output)
    seen: set[str] = set()
    items = []
    for item in parsed.items:
        checked = kiem_tra_can_cu(item, requested, pages, docs)
        if checked["status"] == "pending":
            if item.field in seen:
                checked = {**checked, "status": "rejected", "reason": "Trùng trường — chỉ giữ giá trị đầu tiên."}
            seen.add(item.field)
        items.append(checked)
    return {"requested": requested, "items": items}


def ap_dung_truong_da_xac_nhan(result: Any, docs: Mapping[str, Any], item: Mapping[str, Any], thresholds: Any) -> Any:
    """Chỉ gọi sau khi chuyên viên bấm "Xác nhận": cập nhật dữ kiện + bằng chứng rồi tính lại bằng Python."""

    import time

    from credit_underwriting_colab import BangChung, phan_tich_tu_du_kien

    field = str(item["field"])
    doc = docs.get(str(item["source_doc"]))
    doc_name = getattr(doc, "ten_tep", str(item["source_doc"]))
    evidence = BangChung(
        tai_lieu=doc_name,
        trang=int(item["page"]),
        truong_du_lieu=TRUONG_AI[field][0],
        gia_tri=str(item["value"]),
        trich_doan=f"{NHAN_CAN_XAC_MINH} · đã được chuyên viên xác nhận: {item['quote']}"[:500],
    )
    data = result.du_lieu.model_copy(update={field: item["value"]})
    fields = []
    for entry in result.truong_trich_xuat:
        if entry.ma_truong == field:
            entry = entry.model_copy(
                update={
                    "gia_tri": item["value"],
                    "tai_lieu_nguon": doc_name,
                    "trang": int(item["page"]),
                    "do_tin_cay": DO_TIN_CAY_DA_XAC_NHAN,
                    "bang_chung": evidence,
                }
            )
        fields.append(entry)
    return phan_tich_tu_du_kien(
        result.ma_ho_so, result.ten_ho_so, data, fields, dict(docs), time.perf_counter(), thresholds
    )
