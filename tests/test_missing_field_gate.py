"""Cổng xác nhận thiếu thông tin (UI v3) + sửa rule trạng thái khi thiếu trường (mock, không gọi API thật)."""

from __future__ import annotations

import json
import time
import unittest
from typing import Any
from unittest.mock import patch

import httpx

import credit_underwriting_colab as cu
import creditlens_ui_v3 as v3
import missing_field_gate as mg
import privacy_gateway as pg
from tests.fixtures.synthetic_pdfs import FakeUpload, _lines, _pdf_bytes, synthetic_cases
from tests.test_fix_folder_gemini import FakeClient, ok
from tests.test_ui_v3 import FakeSt, connect, event

CASE = synthetic_cases()[0]  # EVAL-001: hồ sơ nhất quán và đầy đủ
NAMES = {"application": "01_don_de_nghi_vay.pdf", "income": "02_chung_tu_thu_nhap.pdf",
         "statement": "03_sao_ke_ngan_hang.pdf", "debt": "04_nghia_vu_no.pdf"}


def uploads(drop: dict[str, tuple[str, ...]] | None = None, rename: dict[str, tuple[str, str]] | None = None,
            only: tuple[str, ...] = tuple(NAMES)) -> list[FakeUpload]:
    """PDF tổng hợp của EVAL-001, bỏ dòng có tiền tố trong ``drop`` hoặc đổi nhãn theo ``rename``."""

    lines = _lines(CASE)
    output = []
    for key in only:
        doc_lines = [line for line in lines[key] if not any(line.startswith(p) for p in (drop or {}).get(key, ()))]
        if rename and key in rename:
            old, new = rename[key]
            doc_lines = [line.replace(old, new) for line in doc_lines]
        output.append(FakeUpload(NAMES[key], _pdf_bytes(doc_lines)))
    return output


def through_gateway(files: list[FakeUpload], *, connected: bool = False) -> FakeSt:
    st = FakeSt()
    if connected:
        connect(st, models=["gemini-3.8-flash"])
    st.session_state[pg.KEY_CONSENT] = True
    v3.xu_ly_tep_tai_len_v3(st, files, st.settings)
    v3.handle_v3_event(st, event("upload_continue"), st.settings)
    v3.handle_v3_event(st, event("privacy_confirm"), st.settings)
    return st


def gate(st: FakeSt) -> dict[str, Any] | None:
    return v3.build_v3_payload(st, st.settings)["missing_gate"]


def gate_fields(view: dict[str, Any]) -> dict[str, str]:
    return {item["field"]: item["level"] for group in view["groups"] for item in group["items"]}


def snapshot(result: Any) -> dict[str, Any]:
    return {
        "trang_thai": result.trang_thai,
        "chi_so": [(m.ma_chi_so, m.gia_tri, m.trang_thai) for m in result.chi_so],
        "canh_bao": [r.loai for r in result.canh_bao],
        "thong_tin_thieu": list(result.thong_tin_thieu),
        "du_lieu": result.du_lieu.model_dump(),
    }


def count_requests(st: FakeSt, kind: str, **extra: Any) -> int:
    FakeClient.requests = []
    FakeClient.outcome = ok([{"text": json.dumps({"items": []})}])
    with patch.object(httpx, "Client", FakeClient):
        v3.handle_v3_event(st, event(kind, **extra), st.settings)
    return len(FakeClient.requests)


class StatusRuleTests(unittest.TestCase):
    """② Thiếu họ tên / thời hạn hoặc không tính được DTI/DSR → không bao giờ REVIEW READY."""

    docs = {k: cu.TaiLieu(loai_ky_vong=k, ten_tep=f"{k}.pdf", van_ban="x", so_trang=1, trang_thai="Đã trích xuất",
                          loai_nhan_dien=k, do_tin_cay=1.0) for k in NAMES}

    def run_case(self, **changes: Any) -> Any:
        data = cu.BASE_DATA.model_copy(update=changes)
        return cu.phan_tich_tu_du_kien("T", "T", data, [], self.docs, time.perf_counter())

    def test_complete_case_stays_review_ready(self) -> None:
        self.assertEqual(self.run_case().trang_thai, "REVIEW READY")

    def test_missing_fields_never_review_ready(self) -> None:
        for changes in ({"ho_ten_khach_hang": None}, {"thoi_han_vay_thang": None}, {"khoan_tra_du_kien": None},
                        {"nghia_vu_no_ke_khai": None, "nghia_vu_no_quan_sat": None}):
            with self.subTest(changes=changes):
                self.assertEqual(self.run_case(**changes).trang_thai, "HUMAN REVIEW REQUIRED")

    def test_critical_missing_still_insufficient(self) -> None:
        result = self.run_case(so_tien_de_nghi_vay=None, ho_ten_khach_hang=None)
        self.assertEqual(result.trang_thai, "INSUFFICIENT INFORMATION")

    def test_pure_check_matches_thong_tin_thieu(self) -> None:
        data = cu.BASE_DATA.model_copy(update={"ho_ten_khach_hang": None, "thoi_han_vay_thang": None,
                                               "chi_phi_sinh_hoat": None})
        items = cu.kiem_tra_truong_thieu(data, self.docs)
        result = cu.phan_tich_tu_du_kien("T", "T", data, [], self.docs, time.perf_counter())
        self.assertEqual([i["label"] for i in items if i["muc_do"] == cu.MUC_DO_BAT_BUOC], result.thong_tin_thieu)
        self.assertEqual({i["field"]: i["muc_do"] for i in items}, {
            "ho_ten_khach_hang": "Bắt buộc", "thoi_han_vay_thang": "Bắt buộc", "chi_phi_sinh_hoat": "Nên có"})


class MissingFieldGateTests(unittest.TestCase):
    def test_complete_case_has_no_dialog(self) -> None:
        st = through_gateway(uploads())
        self.assertIsNone(gate(st))
        self.assertEqual(st.session_state.result.trang_thai, "REVIEW READY")
        self.assertIsNone(st.session_state.get(mg.KEY_FILES))  # đủ thông tin → không giữ tệp tạm

    def test_missing_name_lists_name(self) -> None:
        st = through_gateway(uploads(drop={k: ("Họ và tên", "Chủ tài khoản", "Khách hàng") for k in NAMES}))
        view = gate(st)
        self.assertEqual(view["title"], "Hồ sơ còn thiếu thông tin")
        self.assertEqual(gate_fields(view), {"ho_ten_khach_hang": "Bắt buộc"})
        self.assertNotEqual(st.session_state.result.trang_thai, "REVIEW READY")

    def test_missing_income_lists_core_fields(self) -> None:
        st = through_gateway(uploads(rename={"income": ("Lương thực nhận", "Lương net tháng"),
                                             "statement": ("Bình quân ghi có", "Tiền về TB")}))
        fields = gate_fields(gate(st))
        self.assertEqual(fields["luong_thuc_nhan"], "Bắt buộc")
        self.assertEqual(fields["thu_nhap_qua_sao_ke"], "Bắt buộc")
        self.assertTrue(gate(st)["can_ai"])  # có trường SỐ thiếu → hiện nút "Bổ sung bằng AI"

    def test_many_missing_grouped_by_document(self) -> None:
        st = through_gateway(uploads(drop={"application": ("Số tiền đề nghị vay", "Thời hạn vay", "Chi phí sinh hoạt")},
                                     only=("application", "income", "debt")))
        view = gate(st)
        fields = gate_fields(view)
        self.assertEqual(fields["tai_lieu_statement"], "Bắt buộc")
        self.assertEqual(fields["so_tien_de_nghi_vay"], "Bắt buộc")
        self.assertEqual(fields["thoi_han_vay_thang"], "Bắt buộc")
        self.assertEqual(fields["chi_phi_sinh_hoat"], "Nên có")
        docs = [g["doc"] for g in view["groups"]]
        self.assertEqual(docs, sorted(docs, key=["application", "income", "statement", "debt"].index))
        application = next(g for g in view["groups"] if g["doc"] == "application")
        self.assertEqual(application["items"][-1]["level"], "Nên có")  # "Bắt buộc" lên trước

    def test_dialog_has_no_personal_values(self) -> None:
        st = through_gateway(uploads(drop={"application": ("Số tiền đề nghị vay",)}))
        encoded = json.dumps(gate(st), ensure_ascii=False)
        for value in (CASE.pii["ho_ten"], CASE.pii["cccd"], "25.000.000", "25000000"):
            self.assertNotIn(value, encoded)

    def test_pages_locked_and_no_llm_request_while_open(self) -> None:
        st = through_gateway(uploads(drop={"application": ("Số tiền đề nghị vay",)}), connected=True)
        payload = v3.build_v3_payload(st, st.settings)
        locked = {item["page"]: item["locked"] for item in payload["navigation"]}
        self.assertTrue(all(locked[p] for p in ("2_extraction", "3_analysis", "4_risk", "5_summary")))
        self.assertFalse(locked["6_methodology"])
        for kind, extra in (("ai_generate", {}), ("chat_send", {"text": "Tóm tắt hồ sơ"}), ("ai_extract", {})):
            with self.subTest(kind=kind):
                self.assertEqual(count_requests(st, kind, **extra), 0)
        self.assertIsNotNone(gate(st))

    def test_continue_keeps_status_and_numbers_and_writes_audit(self) -> None:
        st = through_gateway(uploads(drop={"application": ("Thời hạn vay",)}))
        before = snapshot(st.session_state.result)
        v3.handle_v3_event(st, event("missing_gate_continue"), st.settings)
        self.assertIsNone(gate(st))
        self.assertEqual(snapshot(st.session_state.result), before)
        self.assertEqual(before["trang_thai"], "HUMAN REVIEW REQUIRED")
        audit = st.session_state[mg.KEY_AUDIT]
        self.assertEqual(audit[-1]["lua_chon"], "continue")
        self.assertEqual(audit[-1]["ma_truong_thieu"], ["thoi_han_vay_thang"])
        self.assertEqual(set(audit[-1]), {"thoi_diem", "ma_ho_so", "ma_truong_thieu", "lua_chon"})
        vault_log = pg.lay_vault(st.session_state).nhat_ky
        self.assertEqual(vault_log[-1]["su_kien"], "Cổng thiếu thông tin")
        encoded = json.dumps([audit, vault_log], ensure_ascii=False)
        self.assertNotIn(CASE.pii["ho_ten"], encoded)
        # Rerender/điều hướng không bật lại hộp thoại.
        for page in ("5_summary", "1_overview", "3_analysis"):
            v3.handle_v3_event(st, event("navigate", page=page), st.settings)
            self.assertIsNone(gate(st))

    def test_continue_note_on_summary_page_and_exports(self) -> None:
        st = through_gateway(uploads(drop={"application": ("Thời hạn vay",)}))
        v3.handle_v3_event(st, event("missing_gate_continue"), st.settings)
        v3.handle_v3_event(st, event("navigate", page="5_summary"), st.settings)
        summary = v3.build_v3_payload(st, st.settings)["pages"]["summary"]
        note = "Chuyên viên đã chọn tiếp tục đánh giá khi thiếu: Thời hạn vay."
        self.assertEqual(summary["findings"][0]["detail"], note)
        result = st.session_state.result
        self.assertIn(note, cu.bao_cao_markdown(result, ghi_chu_kiem_soat=mg.ghi_chu_tiep_tuc(st.session_state)))
        for generator in (cu.tao_bao_cao_word, cu.tao_bao_cao_excel):
            self.assertTrue(generator(result, "", 0.75, ghi_chu_kiem_soat=note).startswith(b"PK"))

    def test_supplement_returns_to_step0_keeping_files_and_merges_new_upload(self) -> None:
        st = through_gateway(uploads(only=("application", "income")))
        self.assertIn("tai_lieu_statement", gate_fields(gate(st)))
        v3.handle_v3_event(st, event("missing_gate_supplement"), st.settings)
        state = st.session_state
        self.assertIsNone(state.result)
        self.assertIsNone(pg.lay_vault(state))
        self.assertEqual(state.v3_active_page, "1_overview")
        self.assertEqual({row["path"] for row in v3.upload_plan_view(state)["rows"]}, {NAMES["application"], NAMES["income"]})
        v3.xu_ly_tep_tai_len_v3(st, uploads(only=("statement",)), st.settings)
        rows = v3.upload_plan_view(state)["rows"]
        self.assertEqual({row["path"] for row in rows}, {NAMES["application"], NAMES["income"], NAMES["statement"]})
        v3.handle_v3_event(st, event("upload_continue"), st.settings)
        v3.handle_v3_event(st, event("privacy_confirm"), st.settings)
        self.assertIsNone(gate(st))  # đã đủ → không hiện lại
        self.assertEqual(state.result.trang_thai, "REVIEW READY")

    def test_escape_equivalent_supplement_on_demo_case(self) -> None:
        st = FakeSt()
        v3.handle_v3_event(st, event("privacy_consent", value=True), st.settings)
        v3.handle_v3_event(st, event("demo_open", case_name="CASE-08 — Đơn vay chưa đầy đủ"), st.settings)
        v3.handle_v3_event(st, event("privacy_confirm"), st.settings)
        self.assertEqual(set(gate_fields(gate(st))), {"so_tien_de_nghi_vay", "thoi_han_vay_thang"})
        v3.handle_v3_event(st, event("missing_gate_supplement"), st.settings)
        self.assertIsNone(st.session_state.result)
        self.assertIsNone(st.session_state.get("v3_upload_plan"))

    def test_ai_button_sends_exactly_one_request_and_dialog_follows_confirmation(self) -> None:
        st = through_gateway(uploads(rename={"income": ("Lương thực nhận", "Lương net tháng")}), connected=True)
        self.assertEqual(set(gate_fields(gate(st))), {"luong_thuc_nhan"})
        good = {"field": "luong_thuc_nhan", "value": "25000000", "unit": "VND", "source_doc": "income", "page": 1,
                "quote": "Lương net tháng: 25.000.000 VND"}
        FakeClient.requests = []
        FakeClient.outcome = ok([{"text": json.dumps({"items": [good]}, ensure_ascii=False)}])
        with patch.object(httpx, "Client", FakeClient):
            v3.handle_v3_event(st, event("missing_gate_ai"), st.settings)
        self.assertEqual(len(FakeClient.requests), 1)
        self.assertEqual(st.session_state.v3_active_page, "2_extraction")
        self.assertIsNone(gate(st))  # chờ chuyên viên xác nhận trường AI
        self.assertIsNone(st.session_state.result.du_lieu.luong_thuc_nhan)  # chưa xác nhận → chưa dùng
        v3.handle_v3_event(st, event("ai_extract_confirm", field="luong_thuc_nhan"), st.settings)
        self.assertEqual(st.session_state.result.du_lieu.luong_thuc_nhan, 25_000_000)
        self.assertIsNone(gate(st))  # đã đủ → hộp thoại biến mất

    def test_ai_dismissed_reopens_dialog(self) -> None:
        st = through_gateway(uploads(rename={"income": ("Lương thực nhận", "Lương net tháng")}), connected=True)
        good = {"field": "luong_thuc_nhan", "value": "25000000", "unit": "VND", "source_doc": "income", "page": 1,
                "quote": "Lương net tháng: 25.000.000 VND"}
        FakeClient.outcome = ok([{"text": json.dumps({"items": [good]}, ensure_ascii=False)}])
        with patch.object(httpx, "Client", FakeClient):
            v3.handle_v3_event(st, event("missing_gate_ai"), st.settings)
        v3.handle_v3_event(st, event("ai_extract_reject", field="luong_thuc_nhan"), st.settings)
        self.assertEqual(set(gate_fields(gate(st))), {"luong_thuc_nhan"})  # vẫn thiếu → hỏi lại

    def test_changed_missing_list_reopens_dialog(self) -> None:
        st = through_gateway(uploads(drop={"application": ("Thời hạn vay",)}))
        v3.handle_v3_event(st, event("missing_gate_continue"), st.settings)
        self.assertIsNone(gate(st))
        state = st.session_state
        state["result"] = cu.phan_tich_tu_du_kien(
            state.result.ma_ho_so, state.result.ten_ho_so,
            state.result.du_lieu.model_copy(update={"so_tien_de_nghi_vay": None}),
            list(state.result.truong_trich_xuat), dict(state.docs), time.perf_counter())
        self.assertEqual(set(gate_fields(gate(st))), {"thoi_han_vay_thang", "so_tien_de_nghi_vay"})

    def test_ai_button_hidden_without_numeric_gap(self) -> None:
        st = through_gateway(uploads(drop={k: ("Họ và tên", "Chủ tài khoản", "Khách hàng") for k in NAMES}), connected=True)
        self.assertFalse(gate(st)["can_ai"])
        self.assertEqual(count_requests(st, "missing_gate_ai"), 0)
        self.assertIsNotNone(gate(st))

    def test_cancel_clears_case_and_vault(self) -> None:
        st = through_gateway(uploads(drop={"application": ("Số tiền đề nghị vay",)}))
        v3.handle_v3_event(st, event("missing_gate_cancel"), st.settings)
        state = st.session_state
        self.assertIsNone(state.result)
        self.assertIsNone(pg.lay_vault(state))
        self.assertIsNone(state.get(mg.KEY_FILES))
        self.assertEqual(state[mg.KEY_AUDIT][-1]["lua_chon"], "cancel")
        self.assertIsNone(v3.build_v3_payload(st, st.settings)["missing_gate"])

    def test_gate_events_ignored_when_dialog_closed(self) -> None:
        st = through_gateway(uploads())
        v3.handle_v3_event(st, event("missing_gate_cancel"), st.settings)
        self.assertIsNotNone(st.session_state.result)
        self.assertFalse(st.session_state.get(mg.KEY_AUDIT))

    def test_legacy_dialog_reports_open_state(self) -> None:
        st = through_gateway(uploads(drop={"application": ("Số tiền đề nghị vay",)}))
        self.assertTrue(mg.hien_thi_hop_thoai_legacy(st))  # FakeSt không có st.dialog → chỉ báo đang mở
        v3.handle_v3_event(st, event("missing_gate_continue"), st.settings)
        self.assertFalse(mg.hien_thi_hop_thoai_legacy(st))


if __name__ == "__main__":
    unittest.main()
