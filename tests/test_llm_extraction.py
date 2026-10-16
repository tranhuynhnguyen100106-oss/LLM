"""#1 — LLM Structured Extraction có grounding check + xác nhận của chuyên viên (mock, không gọi API thật)."""

from __future__ import annotations

import json
import unittest
from typing import Any
from unittest.mock import patch

import httpx

import creditlens_ui_v3 as v3
import llm_extraction as le
import privacy_gateway as pg
from tests.fixtures.synthetic_pdfs import FakeUpload, _lines, _pdf_bytes, case_uploads, synthetic_cases
from tests.test_fix_folder_gemini import FakeClient, FakeResponse, ok
from tests.test_ui_v3 import SECRET, FakeSt, connect, event

CASE = synthetic_cases()[0]  # EVAL-001: lương thực nhận 25.000.000 VND


def uploads_with_uncommon_salary_label() -> list[FakeUpload]:
    """Chứng từ thu nhập ghi "Lương net tháng" (regex không có alias) → regex trả None."""

    lines = _lines(CASE)
    lines["income"] = [line.replace("Lương thực nhận", "Lương net tháng") for line in lines["income"]]
    names = {u.name: u for u in case_uploads(CASE)}
    output = []
    for key, name in (("application", "01_don_de_nghi_vay.pdf"), ("income", "02_chung_tu_thu_nhap.pdf"),
                      ("statement", "03_sao_ke_ngan_hang.pdf"), ("debt", "04_nghia_vu_no.pdf")):
        output.append(FakeUpload(name, _pdf_bytes(lines[key]) if key == "income" else names[name].getvalue()))
    return output


def ready_state() -> FakeSt:
    st = FakeSt()
    connect(st, models=["gemini-3.8-flash"])
    st.session_state[pg.KEY_CONSENT] = True
    v3.xu_ly_tep_tai_len_v3(st, uploads_with_uncommon_salary_label(), st.settings)
    v3.handle_v3_event(st, event("upload_continue"), st.settings)
    pg.xac_nhan_cong(st)
    return st


def run_extract(st: FakeSt, outcome: Any) -> list[dict[str, Any]]:
    FakeClient.requests = []
    FakeClient.outcome = outcome
    with patch.object(httpx, "Client", FakeClient):
        v3.handle_v3_event(st, event("ai_extract"), st.settings)
    return list(FakeClient.requests)


def llm_items(*items: dict[str, Any]) -> FakeResponse:
    return ok([{"text": json.dumps({"items": list(items)}, ensure_ascii=False)}])


GOOD = {"field": "luong_thuc_nhan", "value": "25000000", "unit": "VND", "source_doc": "income", "page": 1,
        "quote": "Lương net tháng: 25.000.000 VND"}


def metric(st: FakeSt, code: str) -> Any:
    return next(m.gia_tri for m in st.session_state.result.chi_so if m.ma_chi_so == code)


class LlmExtractionTests(unittest.TestCase):
    def test_regex_gap_is_detected_and_only_numeric_date_fields_are_requested(self) -> None:
        st = ready_state()
        self.assertIsNone(st.session_state.result.du_lieu.luong_thuc_nhan)
        view = v3.build_v3_payload(st, st.settings)["ai_extraction"]
        self.assertEqual([m["field"] for m in view["missing"]], ["luong_thuc_nhan"])
        self.assertTrue(set(le.TRUONG_AI).isdisjoint({"ho_ten_khach_hang", "don_vi_cong_tac_ke_khai", "chuc_danh_ke_khai"}))

    def test_grounded_value_needs_human_confirmation_before_it_affects_dti_dsr(self) -> None:
        st = ready_state()
        dti_before, dsr_before = metric(st, "dti"), metric(st, "dsr")
        requests = run_extract(st, llm_items(GOOD))
        self.assertEqual(len(requests), 1)  # 1 request cho cả hồ sơ
        body = json.dumps(requests[0]["body"], ensure_ascii=False)
        self.assertNotIn(CASE.pii["ho_ten"], body)
        self.assertNotIn(CASE.pii["cccd"], body)
        self.assertNotIn(SECRET, body)
        self.assertIn("KH_01", body)
        self.assertEqual(requests[0]["body"]["generationConfig"]["responseMimeType"], "application/json")
        item = st.session_state["v3_ai_extraction"]["items"][0]
        self.assertEqual((item["status"], item["reason"]), ("pending", le.NHAN_CAN_XAC_MINH))
        self.assertIsNone(st.session_state.result.du_lieu.luong_thuc_nhan)  # chưa xác nhận → vẫn như thiếu
        self.assertEqual((metric(st, "dti"), metric(st, "dsr")), (dti_before, dsr_before))
        view = v3.build_v3_payload(st, st.settings)["ai_extraction"]
        self.assertEqual(view["items"][0]["document"], "02_chung_tu_thu_nhap.pdf")
        self.assertEqual(view["items"][0]["page"], 1)
        FakeClient.requests = []
        with patch.object(httpx, "Client", FakeClient):
            v3.handle_v3_event(st, event("ai_extract_confirm", field="luong_thuc_nhan"), st.settings)
        self.assertEqual(FakeClient.requests, [])  # xác nhận không gọi LLM
        self.assertEqual(st.session_state.result.du_lieu.luong_thuc_nhan, 25_000_000)
        field = next(f for f in st.session_state.result.truong_trich_xuat if f.ma_truong == "luong_thuc_nhan")
        self.assertEqual((field.tai_lieu_nguon, field.trang), ("02_chung_tu_thu_nhap.pdf", 1))
        self.assertIn(le.NHAN_CAN_XAC_MINH, field.bang_chung.trich_doan)
        self.assertEqual(st.session_state["v3_ai_extraction"]["items"][0]["status"], "confirmed")

    def test_fabricated_number_is_rejected(self) -> None:
        st = ready_state()
        run_extract(st, llm_items({**GOOD, "value": "35000000", "quote": "Lương net tháng: 35.000.000 VND"}))
        item = st.session_state["v3_ai_extraction"]["items"][0]
        self.assertEqual(item["status"], "rejected")
        self.assertIn(le.NHAN_KHONG_CAN_CU, item["reason"])
        v3.handle_v3_event(st, event("ai_extract_confirm", field="luong_thuc_nhan"), st.settings)
        self.assertIsNone(st.session_state.result.du_lieu.luong_thuc_nhan)

    def test_value_not_in_quote_is_rejected(self) -> None:
        st = ready_state()
        run_extract(st, llm_items({**GOOD, "value": "26000000"}))
        self.assertEqual(st.session_state["v3_ai_extraction"]["items"][0]["status"], "rejected")

    def test_wrong_page_or_wrong_document_is_rejected(self) -> None:
        st = ready_state()
        run_extract(st, llm_items({**GOOD, "page": 2}, {**GOOD, "source_doc": "application"}))
        reasons = [i["reason"] for i in st.session_state["v3_ai_extraction"]["items"]]
        self.assertTrue(all(i["status"] == "rejected" for i in st.session_state["v3_ai_extraction"]["items"]))
        self.assertIn("trang không tồn tại", reasons[0])
        self.assertIn("sai tài liệu nguồn", reasons[1])

    def test_identity_fields_from_llm_are_ignored(self) -> None:
        st = ready_state()
        run_extract(st, llm_items({**GOOD, "field": "ho_ten_khach_hang", "value": "KH_01", "quote": "Họ và tên: KH_01"}))
        self.assertEqual(st.session_state["v3_ai_extraction"]["items"][0]["status"], "rejected")
        self.assertEqual(st.session_state.result.du_lieu.ho_ten_khach_hang.strip(), CASE.pii["ho_ten"])

    def test_broken_json_shows_error_and_no_values(self) -> None:
        st = ready_state()
        requests = run_extract(st, ok([{"text": "Lương là 25 triệu"}]))
        self.assertEqual(len(requests), 1)
        state = st.session_state["v3_ai_extraction"]
        self.assertEqual(state["items"], [])
        self.assertIn("EXT-JSON", state["error"])

    def test_api_error_uses_existing_gem_codes_and_no_retry(self) -> None:
        st = ready_state()
        requests = run_extract(st, FakeResponse(429, {}))
        self.assertEqual(len(requests), 1)
        self.assertIn("GEM-429", st.session_state["v3_ai_extraction"]["error"])
        self.assertNotIn(SECRET, st.session_state["v3_ai_extraction"]["error"])

    def test_dismiss_keeps_value_unused(self) -> None:
        st = ready_state()
        run_extract(st, llm_items(GOOD))
        v3.handle_v3_event(st, event("ai_extract_reject", field="luong_thuc_nhan"), st.settings)
        self.assertEqual(st.session_state["v3_ai_extraction"]["items"][0]["status"], "dismissed")
        self.assertIsNone(st.session_state.result.du_lieu.luong_thuc_nhan)

    def test_date_field_uses_full_date_from_original_page_but_view_shows_month_year(self) -> None:
        st = ready_state()
        result = st.session_state.result
        st.session_state["result"] = result.model_copy(update={"du_lieu": result.du_lieu.model_copy(update={"ngay_bat_dau_chung_tu": None})})
        run_extract(st, llm_items({"field": "ngay_bat_dau_chung_tu", "value": "06/2022", "source_doc": "income", "page": 1,
                                   "quote": "Ngày bắt đầu làm việc: 06/2022"}))
        item = st.session_state["v3_ai_extraction"]["items"][0]
        self.assertEqual((item["status"], item["value"]), ("pending", "2022-06-01"))
        view = json.dumps(v3.build_v3_payload(st, st.settings)["ai_extraction"], ensure_ascii=False)
        self.assertIn("06/2022", view)
        self.assertNotIn("2022-06-01", view)

    def test_without_connection_no_request(self) -> None:
        st = ready_state()
        st.session_state["llm_connections"] = {}
        self.assertEqual(run_extract(st, llm_items(GOOD)), [])


if __name__ == "__main__":
    unittest.main()
