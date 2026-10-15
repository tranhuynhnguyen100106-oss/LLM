"""Bộ 20 hồ sơ PDF tổng hợp dùng cho kiểm thử Privacy Gateway.

Các PDF được sinh lúc chạy test vào thư mục tạm, KHÔNG commit vào repo. Toàn bộ
tên người, CCCD, số điện thoại, email, địa chỉ và số tài khoản là dữ liệu giả.
Số liệu tài chính lấy từ ``evaluation/dataset`` (12 kịch bản ``exact`` + 8 kịch
bản ``normalized-equivalent``) để bao phủ đủ các nhóm cảnh báo.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evaluation.dataset import load_gold_cases


SYNTHETIC_NAMES = (
    "Nguyễn Minh Anh", "Trần Thu Hà", "Lê Quốc Bảo", "Phạm Ngọc Lan", "Hoàng Gia Huy",
    "Võ Thanh Tâm", "Đặng Mai Phương", "Bùi Đức Long", "Đỗ Khánh Linh", "Ngô Hải Đăng",
    "Dương Bảo Ngọc", "Lý Tuấn Kiệt", "Phan Thị Hồng", "Vũ Minh Khoa", "Hồ Thanh Vân",
    "Mai Quang Vinh", "Tô Ngọc Trâm", "Châu Anh Tuấn", "La Thùy Dung", "Kiều Văn Nam",
)
RELATED_NAMES = (
    "Trần Văn Bình", "Nguyễn Thị Hoa", "Lê Văn Phúc", "Phạm Thị Yến", "Hoàng Văn Sơn",
)
PROVINCES = ("TP. Hồ Chí Minh", "Hà Nội", "Đà Nẵng", "Cần Thơ", "Khánh Hòa")


@dataclass(frozen=True)
class SyntheticCase:
    case_id: str
    scenario: str
    inputs: dict[str, Any]
    pii: dict[str, str]


def _money(value: Any) -> str:
    return f"{float(value):,.0f}".replace(",", ".") + " VND"


def _select_cases() -> list[dict[str, Any]]:
    gold = load_gold_cases()
    exact = [case for case in gold if case["variant"] == "exact"]
    normalized = [case for case in gold if case["variant"] == "normalized-equivalent"][:8]
    selected = exact + normalized
    assert len(selected) == 20
    return selected


def synthetic_cases() -> list[SyntheticCase]:
    cases: list[SyntheticCase] = []
    for index, gold in enumerate(_select_cases()):
        inputs = dict(gold["extracted_input"])
        name = SYNTHETIC_NAMES[index]
        if gold["variant"] == "normalized-equivalent":
            name = f"  {name.upper()}  "
        inputs["ho_ten_khach_hang"] = name
        pii = {
            "ho_ten": name.strip(),
            "nguoi_lien_quan": RELATED_NAMES[index % len(RELATED_NAMES)],
            "cccd": f"0{79 + index % 9:02d}{193000000 + index * 7919:09d}",
            "sdt": f"09{index % 10}{1234560 + index:07d}",
            "email": f"khach{index + 1:02d}.demo@example.com",
            "dia_chi": f"{12 + index} Đường Số {index + 3}, Phường {index + 1}, {PROVINCES[index % len(PROVINCES)]}",
            "ngay_sinh": f"{(index % 27) + 1:02d}/{(index % 12) + 1:02d}/{1985 + index % 12}",
            "stk": f"{1903 + index:04d}{567890120 + index:09d}",
        }
        cases.append(SyntheticCase(gold["case_id"], gold["scenario"], inputs, pii))
    return cases


def _lines(case: SyntheticCase) -> dict[str, list[str]]:
    d = case.inputs
    p = case.pii

    def add(rows: list[str], label: str, value: Any, *, money: bool = False, percent: bool = False) -> None:
        if value is None:
            return
        if money:
            rows.append(f"{label}: {_money(value)}")
        elif percent:
            rows.append(f"{label}: {float(value) * 100:.2f}%".replace(".", ","))
        elif isinstance(value, float) and value.is_integer():
            rows.append(f"{label}: {int(value)}")
        else:
            rows.append(f"{label}: {value}")

    application = ["ĐƠN ĐỀ NGHỊ VAY VỐN", "Hồ sơ tổng hợp minh họa - không phải dữ liệu thật"]
    add(application, "Họ và tên", d["ho_ten_khach_hang"])
    application += [
        f"Ngày sinh: {p['ngay_sinh']}",
        f"Số CCCD: {p['cccd']}",
        f"Điện thoại: {p['sdt']}",
        f"Email: {p['email']}",
        f"Địa chỉ: {p['dia_chi']}",
        f"Người liên quan: {p['nguoi_lien_quan']}",
    ]
    add(application, "Đơn vị công tác", d["don_vi_cong_tac_ke_khai"])
    add(application, "Chức danh", d["chuc_danh_ke_khai"])
    add(application, "Ngày bắt đầu làm việc", d["ngay_bat_dau_ke_khai"])
    add(application, "Thâm niên tháng", d["tham_nien_lam_viec_thang"])
    add(application, "Thu nhập kê khai", d["thu_nhap_ke_khai"], money=True)
    add(application, "Số tiền đề nghị vay", d["so_tien_de_nghi_vay"], money=True)
    add(application, "Thời hạn vay tháng", d["thoi_han_vay_thang"])
    add(application, "Trả nợ khoản vay mới hàng tháng", d["khoan_tra_du_kien"], money=True)
    add(application, "Nghĩa vụ nợ kê khai", d["nghia_vu_no_ke_khai"], money=True)
    add(application, "Chi phí sinh hoạt", d["chi_phi_sinh_hoat"], money=True)
    add(application, "Mục đích vay", d["muc_dich_vay"])

    income = ["XÁC NHẬN THU NHẬP - PHIẾU LƯƠNG", f"Họ và tên: {d['ho_ten_khach_hang']}"]
    add(income, "Đơn vị công tác", d["don_vi_cong_tac_chung_tu"])
    add(income, "Chức danh", d["chuc_danh_chung_tu"])
    add(income, "Ngày bắt đầu làm việc", d["ngay_bat_dau_chung_tu"])
    add(income, "Lương thực nhận", d["luong_thuc_nhan"], money=True)

    statement = [
        "SAO KÊ NGÂN HÀNG 6 THÁNG",
        f"Chủ tài khoản: {d['ho_ten_khach_hang']}",
        f"Số tài khoản: {p['stk']}",
    ]
    add(statement, "Bình quân ghi có", d["thu_nhap_qua_sao_ke"], money=True)
    add(statement, "Số dư bình quân", d["so_du_binh_quan"], money=True)
    add(statement, "Biến động thu nhập", d["bien_dong_thu_nhap"], percent=True)

    debt = ["THÔNG TIN NGHĨA VỤ NỢ", f"Khách hàng: {d['ho_ten_khach_hang']}"]
    add(debt, "Nghĩa vụ nợ hàng tháng", d["nghia_vu_no_quan_sat"], money=True)
    return {"application": application, "income": income, "statement": statement, "debt": debt}


FILE_NAMES = {
    "application": "01_don_de_nghi_vay.pdf",
    "income": "02_chung_tu_thu_nhap.pdf",
    "statement": "03_sao_ke_ngan_hang.pdf",
    "debt": "04_nghia_vu_no.pdf",
}


def _pdf_bytes(lines: list[str]) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    from credit_underwriting_colab import _tim_font_pdf

    fonts = _tim_font_pdf()
    if fonts is None:
        raise RuntimeError("Cần font Unicode (Noto/DejaVu) để sinh PDF tiếng Việt.")
    if "CLFixture" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("CLFixture", fonts[0]))
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4, invariant=1)
    pdf.setFont("CLFixture", 10)
    y = 800
    for line in lines:
        pdf.drawString(50, y, line)
        y -= 18
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


class FakeUpload:
    """Giả lập UploadedFile của Streamlit (chỉ cần ``name`` và ``getvalue``)."""

    def __init__(self, name: str, data: bytes) -> None:
        self.name = name
        self._data = data
        self.size = len(data)

    def getvalue(self) -> bytes:
        return self._data


def case_uploads(case: SyntheticCase) -> list[FakeUpload]:
    return [FakeUpload(FILE_NAMES[key], _pdf_bytes(lines)) for key, lines in _lines(case).items()]


def write_case_folder(case: SyntheticCase, root: Path) -> Path:
    folder = root / case.case_id
    folder.mkdir(parents=True, exist_ok=True)
    for upload in case_uploads(case):
        (folder / upload.name).write_bytes(upload.getvalue())
    return folder


def deterministic_snapshot(result: Any) -> dict[str, Any]:
    """Phần kết quả phải giữ nguyên bit-for-bit (bỏ thời điểm/thời gian xử lý)."""

    dumped = result.model_dump(mode="json")
    return {
        "du_lieu": dumped["du_lieu"],
        "chi_so": dumped["chi_so"],
        "canh_bao": dumped["canh_bao"],
        "thong_tin_thieu": dumped["thong_tin_thieu"],
        "cau_hoi_xac_minh": dumped["cau_hoi_xac_minh"],
        "trang_thai": dumped["trang_thai"],
        "thu_nhap_dung_de_tinh": dumped["thu_nhap_dung_de_tinh"],
        "nguon_thu_nhap_dung_de_tinh": dumped["nguon_thu_nhap_dung_de_tinh"],
        "truong_trich_xuat": dumped["truong_trich_xuat"],
    }
