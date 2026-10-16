"""#3 — Credit Review Summary có cấu trúc, hậu kiểm Python (a)–(e) và guardrail ngôn ngữ quyết định."""

from __future__ import annotations

import json
import unittest
from typing import Any
from unittest.mock import patch

import httpx

import credit_review_summary as crs
import credit_underwriting_colab as cu
import creditlens_ui_v3 as v3
import privacy_gateway as pg
from tests.test_fix_folder_gemini import FakeClient, FakeResponse, chat_ready, ok
from tests.test_ui_v3 import SECRET, event

D1_LEAKED = [
    "Tôi đề xuất phê duyệt hồ sơ này",
    "Hồ sơ đủ điều kiện để giải ngân",
    "I recommend approving this loan",
    "Recommendation: APPROVE",
    "Khuyến nghị phê duyệt khoản vay",
    "Nên từ chối",
]
VARIANTS = [
    "Đề xuất giải ngân 300 triệu",
    "Khách hàng đủ điều kiện vay",
    "Hồ sơ đủ điều kiện cấp tín dụng",
    "Khách hàng không đủ điều kiện vay",
    "We approve this application",
    "Loan approval is granted",
    "I recommend rejecting the application",
    "The customer is eligible for the loan",
    "The bank should approve the loan",
    "This loan should be rejected",
    "Kết luận: phê duyệt",
    "Không nên phê duyệt hồ sơ này",
    "Khuyến nghị phê duyệt, chờ Hội đồng xác nhận",
    "We reject the loan",
]
NEUTRAL = [
    "Hồ sơ cần con người phê duyệt.",
    "Quyết định phê duyệt hoặc từ chối thuộc Hội đồng Tín dụng.",
    "Hệ thống không phê duyệt hoặc từ chối khoản vay.",
    "Hệ thống không khuyến nghị phê duyệt hay từ chối.",
    "Final approval rests with the credit committee.",
    "This summary requires human approval.",
    "Số tiền đề nghị vay: 300.000.000 VND",
    "The system does not approve or reject loans.",
    "Thông tin chưa đủ để kết luận.",
    "Chuyên viên cần xác minh thu nhập trước khi trình phê duyệt.",
]


def payload_and_summary() -> tuple[dict[str, Any], crs.CreditReviewSummary, Any, Any]:
    result, docs = cu.du_lieu_demo("CASE-03 — Thu nhập không nhất quán", None)
    vault = pg.build_vault(pg.detect_pii(docs, result))
    payload = json.loads(cu.du_lieu_gui_llm(result, vault))
    return payload, crs.ban_tom_tat_tu_ket_qua(payload), result, vault


class GuardrailTests(unittest.TestCase):
    def test_d1_leaked_sentences_and_variants_are_blocked(self) -> None:
        for text in D1_LEAKED + VARIANTS:
            with self.subTest(text=text):
                self.assertTrue(crs.chua_ngon_ngu_quyet_dinh(text))

    def test_neutral_sentences_are_not_blocked(self) -> None:
        for text in NEUTRAL:
            with self.subTest(text=text):
                self.assertFalse(crs.chua_ngon_ngu_quyet_dinh(text))

    def test_chat_uses_expanded_guardrail(self) -> None:
        st = chat_ready()
        for text in ("Tôi đề xuất phê duyệt hồ sơ này.", "I recommend approving this loan."):
            FakeClient.requests = []
            FakeClient.outcome = ok([{"text": text}])
            with patch.object(httpx, "Client", FakeClient):
                v3.handle_v3_event(st, event("chat_send", text="Kết luận?"), st.settings)
            self.assertIn("đã bị chặn", st.session_state["v3_chat_messages"][-1]["content"])


class SchemaAndPostCheckTests(unittest.TestCase):
    def test_schema_has_ten_sections_and_no_decision_field(self) -> None:
        self.assertEqual(list(crs.CreditReviewSummary.model_fields), [key for key, _ in crs.MUC_TOM_TAT])
        self.assertEqual(len(crs.MUC_TOM_TAT), 10)
        self.assertFalse(any("quyet_dinh" in k or "decision" in k for k in crs.CreditReviewSummary.model_fields))
        _payload, summary, _r, _v = payload_and_summary()
        with self.assertRaises(crs.LoiHauKiemAI):
            crs.phan_tich_output(json.dumps({**summary.model_dump(), "quyet_dinh": "APPROVE"}))
        self.assertEqual(crs.gemini_response_schema()["properties"]["trang_thai_xem_xet"]["enum"], list(crs.TRANG_THAI))

    def test_faithful_summary_passes(self) -> None:
        payload, summary, _r, _v = payload_and_summary()
        self.assertEqual(crs.hau_kiem_tom_tat(summary, payload), [])

    def _violations(self, mutate: Any) -> list[str]:
        payload, summary, _r, _v = payload_and_summary()
        data = summary.model_dump()
        mutate(data)
        return crs.hau_kiem_tom_tat(crs.CreditReviewSummary.model_validate(data), payload)

    def test_a_numbers_must_match_input_with_rounding_tolerance(self) -> None:
        dsr = "67,9%"
        self.assertEqual(self._violations(lambda d: d["chi_so"].append(f"DSR {dsr}")), [])
        self.assertEqual(self._violations(lambda d: d["chi_so"].append("DSR 67,95%")), [])  # ±0,1 điểm %
        self.assertTrue(self._violations(lambda d: d["chi_so"].append("DSR 68,5%"))[0].startswith("(a)"))
        self.assertTrue(self._violations(lambda d: d.update(de_nghi_vay="Vay 999 triệu VND"))[0].startswith("(a)"))

    def test_b_risk_code_and_evidence_must_come_from_python(self) -> None:
        bad_code = self._violations(lambda d: d["canh_bao"].append({"risk_code": "FRAUD", "noi_dung": "x", "evidence_ref": "R-001"}))
        self.assertTrue(any(v.startswith("(b) risk_code") for v in bad_code))
        bad_ref = self._violations(lambda d: d["canh_bao"][0].update(evidence_ref="tài liệu không tồn tại"))
        self.assertTrue(any(v.startswith("(b) evidence_ref") for v in bad_ref))

    def test_c_missing_section_or_invalid_json_fails(self) -> None:
        _payload, summary, _r, _v = payload_and_summary()
        data = summary.model_dump()
        del data["bang_chung"]
        with self.assertRaises(crs.LoiHauKiemAI) as raised:
            crs.phan_tich_output(json.dumps(data))
        self.assertIn("(c)", str(raised.exception))
        with self.assertRaises(crs.LoiHauKiemAI):
            crs.phan_tich_output("Đây là bản tóm tắt dạng văn bản tự do.")
        self.assertEqual(crs.phan_tich_output("```json\n" + summary.model_dump_json() + "\n```"), summary)

    def test_d_status_must_equal_python(self) -> None:
        violations = self._violations(lambda d: d.update(trang_thai_xem_xet="REVIEW READY"))
        self.assertTrue(any(v.startswith("(d)") for v in violations))

    def test_e_decision_language_fails(self) -> None:
        violations = self._violations(lambda d: d.update(kiem_tra_nhat_quan="Tôi đề xuất phê duyệt hồ sơ này."))
        self.assertTrue(any(v.startswith("(e)") for v in violations))


class GeminiSummaryFlowTests(unittest.TestCase):
    def _generate(self, st: Any, output_text: str) -> None:
        FakeClient.requests = []
        FakeClient.outcome = ok([{"text": output_text}])
        with patch.object(httpx, "Client", FakeClient):
            v3.handle_v3_event(st, event("ai_generate"), st.settings)

    def test_valid_json_is_rendered_from_validated_schema_one_request(self) -> None:
        st = chat_ready()
        result = st.session_state.result
        payload = json.loads(cu.du_lieu_gui_llm(result, pg.lay_vault(st.session_state)))
        self._generate(st, crs.ban_tom_tat_tu_ket_qua(payload).model_dump_json())
        self.assertEqual(len(FakeClient.requests), 1)
        config = FakeClient.requests[0]["body"]["generationConfig"]
        self.assertEqual(config["responseMimeType"], "application/json")
        self.assertEqual(config["responseSchema"]["required"], [k for k, _ in crs.MUC_TOM_TAT])
        summary = st.session_state["ai_summary"]
        for _key, label in crs.MUC_TOM_TAT:
            self.assertIn(f"### {label}", summary)
        self.assertIn("đã vượt hậu kiểm", summary)
        self.assertNotIn(SECRET, json.dumps(FakeClient.requests[0]["body"], ensure_ascii=False))

    def test_failed_post_check_is_not_exported_and_facts_remain(self) -> None:
        st = chat_ready()
        payload = json.loads(cu.du_lieu_gui_llm(st.session_state.result, pg.lay_vault(st.session_state)))
        bad = crs.ban_tom_tat_tu_ket_qua(payload).model_dump()
        bad["chi_so"].append("DSR 12,3%")
        self._generate(st, json.dumps(bad, ensure_ascii=False))
        self.assertEqual(len(FakeClient.requests), 1)  # không retry
        self.assertFalse(st.session_state.get("ai_summary"))
        toast = st.session_state["v3_toasts"][-1]
        self.assertEqual(toast["title"], crs.HAU_KIEM_LABEL)
        self.assertIn("(a)", toast["description"])
        st.session_state["v3_active_page"] = "5_summary"
        view = v3.build_v3_payload(st, st.settings)
        self.assertIsNone(view["ai"]["explanation"])
        self.assertTrue(view["pages"]["summary"])  # facts Python vẫn hiển thị


if __name__ == "__main__":
    unittest.main()
