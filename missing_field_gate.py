"""Cổng xác nhận thiếu thông tin — hỏi chuyên viên ngay sau Bước 0, trước khi xem kết quả và trước mọi lệnh gọi LLM.

- Danh sách thiếu lấy từ ``kiem_tra_truong_thieu`` (cùng rule với ``phan_tich_tu_du_kien``), không viết lại rule.
- Mỗi hồ sơ chỉ hỏi lại khi danh sách mã trường thiếu THAY ĐỔI (chữ ký = mã hồ sơ + mã trường).
- "Tiếp tục" không đổi trạng thái hay số liệu do Python tính; chỉ ghi quyết định vào nhật ký kiểm soát.
- Nhật ký chỉ ghi thời điểm, mã hồ sơ, MÃ trường thiếu và lựa chọn — không ghi giá trị cá nhân.
- Hộp thoại chỉ chứa nhãn trường, không có giá trị.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

KEY_GATE = "missing_gate"
KEY_AUDIT = "missing_gate_audit"
KEY_FILES = "missing_gate_files"
KEY_MERGE = "v3_upload_merge"

CHOICES = ("continue", "supplement", "ai", "cancel")
NHAN_LUA_CHON = {
    "continue": "Tiếp tục đánh giá",
    "supplement": "Bổ sung tài liệu",
    "ai": "Bổ sung bằng AI",
    "cancel": "Hủy hồ sơ",
}
TIEU_DE = "Hồ sơ còn thiếu thông tin"
GIAI_THICH = (
    "Nếu tiếp tục, hồ sơ sẽ được đánh giá ở trạng thái INSUFFICIENT INFORMATION / HUMAN REVIEW REQUIRED. "
    "Các chỉ số phụ thuộc trường thiếu sẽ hiển thị 'Chưa đủ dữ liệu'."
)
LY_DO_CHAN = "Hãy xử lý hộp thoại “Hồ sơ còn thiếu thông tin” trước. Không gọi AI khi hộp thoại đang mở."
NHAN_TAI_LIEU_KHAC = "Thông tin chung"


def _state_get(state: Any, key: str, default: Any = None) -> Any:
    try:
        return state.get(key, default)
    except AttributeError:
        return getattr(state, key, default)


def danh_sach_thieu(state: Any) -> list[dict[str, str]]:
    """Mục thiếu của hồ sơ đang mở (đã qua Bước 0). Chưa qua Bước 0 → rỗng."""

    from credit_underwriting_colab import kiem_tra_truong_thieu
    from privacy_gateway import cong_hoan_tat

    if not cong_hoan_tat(state):
        return []
    result = _state_get(state, "result")
    return kiem_tra_truong_thieu(result.du_lieu, dict(_state_get(state, "docs") or {}))


def chu_ky(ma_ho_so: str, items: list[Mapping[str, str]]) -> str:
    return ma_ho_so + "|" + ",".join(sorted(str(item["field"]) for item in items))


def _ai_con_cho_xac_nhan(state: Any, ma_ho_so: str) -> bool:
    current = _state_get(state, "v3_ai_extraction")
    if not isinstance(current, Mapping) or current.get("ma_ho_so") != ma_ho_so:
        return False
    return any(item.get("status") == "pending" for item in current.get("items") or [])


def cong_dang_mo(state: Any) -> bool:
    """Mở khi có mục thiếu và danh sách này chưa được chuyên viên quyết định.

    Sau "Bổ sung bằng AI": đóng trong lúc còn trường AI chờ xác nhận; xác nhận xong mà danh sách
    không đổi (ví dụ chuyên viên bỏ qua) thì hỏi lại.
    """

    from credit_underwriting_colab import MUC_DO_BAT_BUOC

    items = danh_sach_thieu(state)
    if not any(item["muc_do"] == MUC_DO_BAT_BUOC for item in items):
        return False  # chỉ thiếu mục "Nên có" → không chặn; các mục này hiện kèm khi hộp thoại mở
    ma_ho_so = str(_state_get(state, "result").ma_ho_so)
    record = _state_get(state, KEY_GATE)
    if not isinstance(record, Mapping) or record.get("signature") != chu_ky(ma_ho_so, items):
        return True
    if record.get("choice") == "ai":
        return not _ai_con_cho_xac_nhan(state, ma_ho_so)
    return False


def ghi_quyet_dinh(state: Any, choice: str) -> dict[str, Any]:
    """Ghi lựa chọn của chuyên viên cho danh sách thiếu hiện tại (chỉ mã trường, không giá trị)."""

    from privacy_gateway import lay_vault

    if choice not in CHOICES:
        raise ValueError("Lựa chọn không hợp lệ.")
    items = danh_sach_thieu(state)
    ma_ho_so = str(getattr(_state_get(state, "result"), "ma_ho_so", ""))
    entry = {
        "thoi_diem": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ma_ho_so": ma_ho_so,
        "ma_truong_thieu": [str(item["field"]) for item in items],
        "lua_chon": choice,
    }
    audit = list(_state_get(state, KEY_AUDIT) or [])
    audit.append(entry)
    state[KEY_AUDIT] = audit[-100:]
    state[KEY_GATE] = {
        "ma_ho_so": ma_ho_so,
        "signature": chu_ky(ma_ho_so, items),
        "choice": choice,
        "labels": [str(item["label"]) for item in items],
    }
    vault = lay_vault(state)
    if vault is not None:
        vault.ghi_nhat_ky("Cổng thiếu thông tin", ket_qua=f"{NHAN_LUA_CHON[choice]} · {len(items)} mục")
    if choice in {"continue", "cancel"}:
        state[KEY_FILES] = None
    return entry


def ghi_chu_tiep_tuc(state: Any) -> str | None:
    """Dòng ghi chú cho trang Tóm tắt và báo cáo xuất khi chuyên viên đã chọn tiếp tục."""

    record = _state_get(state, KEY_GATE)
    result = _state_get(state, "result")
    if not isinstance(record, Mapping) or result is None or record.get("ma_ho_so") != result.ma_ho_so:
        return None
    if record.get("choice") != "continue" or not record.get("labels"):
        return None
    return "Chuyên viên đã chọn tiếp tục đánh giá khi thiếu: " + ", ".join(record["labels"]) + "."


def co_the_bo_sung_ai(state: Any) -> bool:
    """Chỉ khi còn trường SỐ/NGÀY thiếu mà tài liệu nguồn đọc được (đúng phạm vi llm_extraction)."""

    from llm_extraction import truong_can_bo_sung

    result = _state_get(state, "result")
    return result is not None and bool(truong_can_bo_sung(result, dict(_state_get(state, "docs") or {})))


def view_model(state: Any) -> dict[str, Any] | None:
    """View model hộp thoại (chỉ nhãn trường). Không mở → None."""

    from credit_underwriting_colab import MUC_DO_BAT_BUOC, NHAN_LOAI_TAI_LIEU

    if not cong_dang_mo(state):
        return None
    items = danh_sach_thieu(state)
    groups: dict[str, list[dict[str, str]]] = {}
    for item in items:
        groups.setdefault(item["doc"], []).append(
            {"field": item["field"], "label": item["label"], "level": item["muc_do"]}
        )
    order = ("application", "income", "statement", "debt")
    return {
        "open": True,
        "title": TIEU_DE,
        "explanation": GIAI_THICH,
        "groups": [
            {
                "doc": doc,
                "doc_label": NHAN_LOAI_TAI_LIEU.get(doc, NHAN_TAI_LIEU_KHAC),
                "items": sorted(entries, key=lambda e: e["level"] != MUC_DO_BAT_BUOC),
            }
            for doc, entries in sorted(groups.items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else 9)
        ],
        "required_count": sum(1 for item in items if item["muc_do"] == MUC_DO_BAT_BUOC),
        "can_ai": co_the_bo_sung_ai(state),
        "can_restore_files": bool(_state_get(state, KEY_FILES)),
    }


def luu_tep_cho_bo_sung(state: Any, plan: Mapping[str, Any], kept: Mapping[str, Any]) -> None:
    """Giữ bảng phân loại + tệp đã tải đến khi chuyên viên quyết định ở hộp thoại (chỉ trong phiên)."""

    state[KEY_FILES] = {"plan": dict(plan), "kept": dict(kept)}


def khoi_phuc_tep_bo_sung(state: Any) -> bool:
    """"Bổ sung tài liệu": đưa bảng phân loại cũ về Bước 0; tệp tải thêm sẽ được gộp vào bảng này."""

    saved = _state_get(state, KEY_FILES)
    state[KEY_FILES] = None
    if not isinstance(saved, Mapping) or not saved.get("plan"):
        return False
    state["v3_upload_plan"] = dict(saved["plan"])
    state["v3_upload_plan_files"] = dict(saved["kept"])
    state[KEY_MERGE] = True
    return True


def gop_ke_hoach(
    base: Mapping[str, Any], base_kept: Mapping[str, Any], new: Mapping[str, Any], new_kept: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Gộp tệp tải thêm vào bảng phân loại cũ; trùng đường dẫn → giữ tệp mới."""

    new_paths = {item["path"] for item in new.get("items") or []}
    items: list[dict[str, Any]] = []
    kept: dict[str, Any] = {}
    for item, source in [
        *((i, base_kept) for i in base.get("items") or [] if i["path"] not in new_paths),
        *((i, new_kept) for i in new.get("items") or []),
    ]:
        file_id = f"f{len(items) + 1}"
        if item["id"] in source:
            kept[file_id] = source[item["id"]]
        items.append({**item, "id": file_id})
    skipped = [*(base.get("skipped") or []), *(new.get("skipped") or [])]
    return {**dict(new), "items": items, "skipped": skipped}, kept


def hien_thi_hop_thoai_legacy(st: Any) -> bool:
    """Giao diện v2/legacy: cùng hộp thoại bằng ``st.dialog``. Trả True khi hộp thoại đang mở.

    Bản legacy không có bảng xác nhận trường AI nên không có nút "Bổ sung bằng AI" (chỉ có ở v3).
    Đóng bằng Esc/nút × = "Bổ sung tài liệu".
    """

    from privacy_gateway import xoa_ho_so_phien

    state = st.session_state
    vm = view_model(state)
    if vm is None or not hasattr(st, "dialog"):
        return vm is not None

    def chon(choice: str) -> None:
        if not cong_dang_mo(state):
            return
        ghi_quyet_dinh(state, choice)
        if choice in {"supplement", "cancel"}:
            xoa_ho_so_phien(state)
            xoa_trang_thai_cong(state)

    @st.dialog(vm["title"], width="medium", on_dismiss=lambda: chon("supplement"))
    def _hop_thoai() -> None:
        for group in vm["groups"]:
            st.markdown(f"**{group['doc_label']}**")
            st.markdown("\n".join(f"- {item['label']} — *{item['level']}*" for item in group["items"]))
        st.warning(vm["explanation"])
        left, middle, right = st.columns(3)
        if left.button("Bổ sung tài liệu", key="missing_gate_supplement", type="primary", width="stretch"):
            chon("supplement")
            st.rerun()
        if middle.button("Tiếp tục đánh giá", key="missing_gate_continue", width="stretch"):
            chon("continue")
            st.rerun()
        if right.button("Hủy hồ sơ", key="missing_gate_cancel", width="stretch"):
            chon("cancel")
            st.rerun()

    _hop_thoai()
    return True


def xoa_trang_thai_cong(state: Any) -> None:
    """Đóng/hủy hồ sơ: bỏ tệp giữ tạm và cờ gộp (nhật ký kiểm soát vẫn giữ — chỉ có mã trường)."""

    state[KEY_FILES] = None
    state[KEY_GATE] = None
    state[KEY_MERGE] = False
