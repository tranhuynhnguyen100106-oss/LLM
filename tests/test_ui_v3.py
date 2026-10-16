"""Kiểm thử UI v3 ("Đánh giá tín dụng vay" trên Streamlit)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import app
import creditlens_ui_v3 as v3
import privacy_gateway as pg
from credit_underwriting_colab import khoi_tao_trang_thai_phien
from tests.fixtures.synthetic_pdfs import case_uploads, deterministic_snapshot, synthetic_cases

ROOT = Path(__file__).resolve().parents[1]
SECRET = "TEST-ONLY-GEMINI-SENTINEL-NOT-A-KEY-0001"
BASELINE = json.loads((ROOT / "tests" / "fixtures" / "privacy_gateway_baseline.json").read_text(encoding="utf-8"))


class AttrState(dict[str, object]):
    def __getattr__(self, name: str) -> object:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: object) -> None:
        self[name] = value


class FakeSt:
    def __init__(self, secrets: dict[str, str] | None = None) -> None:
        self.session_state = AttrState()
        self.secrets = secrets or {}
        khoi_tao_trang_thai_phien(self)
        v3.khoi_tao_phien_v3(self.session_state, self.session_state.settings)

    @property
    def settings(self) -> dict[str, Any]:
        return self.session_state.settings  # type: ignore[return-value]


_counter = 0


def event(kind: str, **extra: Any) -> dict[str, Any]:
    global _counter
    _counter += 1
    return {"event_id": f"evt_test_{_counter:06d}", "type": kind, **extra}


def connect(st: FakeSt, provider: str = "gemini", models: list[str] | None = None) -> None:
    st.session_state["llm_connections"] = {
        provider: {
            "provider": provider,
            "api_key": SECRET,
            "fingerprint": "fp",
            "models": models or ["gemini-2.5-flash"],
            "model": (models or ["gemini-2.5-flash"])[0],
            "verified": True,
        }
    }
    st.session_state["active_llm_provider"] = provider


def open_demo_through_gateway(st: FakeSt, case: str = "CASE-03 — Thu nhập không nhất quán") -> None:
    v3.handle_v3_event(st, event("privacy_consent", value=True), st.settings)
    v3.handle_v3_event(st, event("demo_open", case_name=case), st.settings)
    v3.handle_v3_event(st, event("privacy_confirm"), st.settings)


def upload_case_through_gateway(st: FakeSt, index: int = 0) -> Any:
    case = synthetic_cases()[index]
    st.session_state[pg.KEY_CONSENT] = True
    v3.xu_ly_tep_tai_len_v3(st, case_uploads(case), st.settings)
    pg.xac_nhan_cong(st)
    return case


def all_pages_payloads(st: FakeSt) -> list[str]:
    output = []
    for page in v3.PAGE_KEYS:
        st.session_state["v3_active_page"] = page
        output.append(json.dumps(v3.build_v3_payload(st, st.settings), ensure_ascii=False))
    return output


class V3ViewModelSafetyTests(unittest.TestCase):
    def test_view_model_never_contains_api_key_or_vault_values(self) -> None:
        st = FakeSt()
        connect(st)
        case = upload_case_through_gateway(st)
        st.session_state["v3_chat_messages"] = [
            {"role": "user", "content": f"khách {case.pii['ho_ten']} SĐT {case.pii['sdt']}", "timestamp": 1}
        ]
        for encoded in all_pages_payloads(st):
            self.assertNotIn(SECRET, encoded)
            self.assertNotIn("api_key", encoded.casefold())
            for value in case.pii.values():
                self.assertFalse(pg._contains_value(encoded, value), value)
            self.assertNotIn("Công ty Cổ phần Minh Long", encoded)

    def test_payload_guard_rejects_leaked_key(self) -> None:
        st = FakeSt()
        connect(st)
        with self.assertRaises(v3.V3ContractError):
            v3.assert_safe_v3_payload({"note": SECRET}, st)

    def test_payload_shape_matches_ai_studio_contracts(self) -> None:
        st = FakeSt()
        open_demo_through_gateway(st)
        st.session_state["v3_active_page"] = "2_extraction"
        payload = v3.build_v3_payload(st, st.settings)
        self.assertEqual(len(payload["navigation"]), 8)
        self.assertEqual([item["page"] for item in payload["navigation"]], list(v3.PAGE_KEYS))
        core = payload["pages"]["core"]
        for key in ("page", "state", "documents", "fields", "comparisons", "metrics", "thresholds", "risks"):
            self.assertIn(key, core)
        self.assertEqual(len(payload["demo_cases"]), 10)


class V3OneSendOneRequestTests(unittest.TestCase):
    def test_send_is_one_request_and_replay_rerender_empty_navigation_are_zero(self) -> None:
        st = FakeSt()
        connect(st)
        open_demo_through_gateway(st)
        with patch("credit_underwriting_colab.tao_phan_hoi_chat_ai", return_value="KH_01 cần xem xét DSR.") as inference:
            send = event("chat_send", text="DSR của khách Nguyễn Minh Anh?", role="underwriter", model="gemini-2.5-flash")
            v3.handle_v3_event(st, send, st.settings)
            self.assertEqual(inference.call_count, 1)
            v3.handle_v3_event(st, send, st.settings)  # cùng event_id (rerun) → bỏ qua
            v3.handle_v3_event(st, event("chat_send", text="   "), st.settings)
            v3.handle_v3_event(st, event("navigate", page="6_methodology"), st.settings)
            all_pages_payloads(st)
            self.assertEqual(inference.call_count, 1)
        args, kwargs = inference.call_args
        self.assertEqual(args[0][-1], {"role": "user", "content": "DSR của khách Nguyễn Minh Anh?"})
        self.assertIs(args[4], pg.lay_vault(st.session_state))
        self.assertIn(pg.PRIVACY_PROMPT_NOTE, kwargs["system_prompt"])
        self.assertIn("Khách hàng: KH_01", kwargs["system_prompt"])
        self.assertEqual(st.session_state["v3_chat_messages"][-1]["content"], "KH_01 cần xem xét DSR.")

    def test_real_chat_function_sends_pseudonymized_system_and_history_once(self) -> None:
        st = FakeSt()
        connect(st)
        open_demo_through_gateway(st)
        captured: list[dict[str, Any]] = []
        response = Mock(status_code=200)
        response.json.return_value = {"candidates": [{"content": {"parts": [{"text": "KH_01 ổn định."}]}}]}
        client = MagicMock()
        client.__enter__.return_value = client
        client.post.side_effect = lambda _url, **kw: captured.append(kw["json"]) or response
        with patch("httpx.Client", MagicMock(return_value=client)):
            v3.handle_v3_event(
                st, event("chat_send", text="khách Nguyễn Minh Anh SĐT 0901234567", role="risk_auditor"), st.settings
            )
        self.assertEqual(len(captured), 1)
        body = json.dumps(captured[0], ensure_ascii=False)
        self.assertIn("khách KH_01 SĐT [SĐT_ĐÃ_CHE]", body)
        self.assertNotIn("Nguyễn Minh Anh", body)
        self.assertIn("Kiểm soát Rủi ro", captured[0]["system_instruction"]["parts"][0]["text"])

    def test_no_ai_connection_shows_notice_and_never_simulates(self) -> None:
        st = FakeSt()
        open_demo_through_gateway(st)
        with patch("credit_underwriting_colab.tao_phan_hoi_chat_ai") as chat, patch(
            "credit_underwriting_colab.tao_dien_giai_bang_ai"
        ) as summary:
            v3.handle_v3_event(st, event("chat_send", text="Phân tích DTI"), st.settings)
            v3.handle_v3_event(st, event("ai_generate"), st.settings)
        chat.assert_not_called()
        summary.assert_not_called()
        last = st.session_state["v3_chat_messages"][-1]
        self.assertEqual(last["content"], v3.NO_AI_MESSAGE)
        self.assertTrue(last["notice"])
        self.assertFalse(st.session_state.get("ai_summary"))

    def test_decision_recommendation_from_ai_is_blocked(self) -> None:
        st = FakeSt()
        connect(st)
        open_demo_through_gateway(st)
        with patch("credit_underwriting_colab.tao_phan_hoi_chat_ai", return_value="Kết luận: nên phê duyệt khoản vay."):
            v3.handle_v3_event(st, event("chat_send", text="Có nên cho vay?", role="advisor"), st.settings)
        self.assertIn("đã bị chặn", st.session_state["v3_chat_messages"][-1]["content"])


class V3GatewayLockTests(unittest.TestCase):
    def test_later_pages_and_chat_are_locked_until_gateway(self) -> None:
        st = FakeSt()
        connect(st)
        v3.handle_v3_event(st, event("demo_open", case_name="CASE-04 — Đơn vị công tác không khớp"), st.settings)
        for page in ("2_extraction", "3_analysis", "4_risk", "5_summary"):
            st.session_state["v3_active_page"] = "1_overview"
            v3.handle_v3_event(st, event("navigate", page=page), st.settings)
            self.assertEqual(st.session_state["v3_active_page"], "1_overview")
            st.session_state["v3_active_page"] = page  # truy cập trực tiếp
            payload = v3.build_v3_payload(st, st.settings)
            self.assertIsNone(payload["pages"]["core"])
            self.assertIsNone(payload["pages"]["summary"])
            self.assertTrue(next(i for i in payload["navigation"] if i["page"] == page)["locked"])
        with patch("credit_underwriting_colab.tao_phan_hoi_chat_ai") as inference:
            v3.handle_v3_event(st, event("chat_send", text="Hỏi"), st.settings)
        inference.assert_not_called()
        self.assertEqual(st.session_state["v3_chat_messages"][-1]["content"], pg.CHAT_LOCK_REASON)
        v3.handle_v3_event(st, event("privacy_confirm"), st.settings)  # chưa tick xác nhận
        self.assertFalse(pg.cong_hoan_tat(st.session_state))
        v3.handle_v3_event(st, event("privacy_consent", value=True), st.settings)
        v3.handle_v3_event(st, event("privacy_confirm"), st.settings)
        self.assertTrue(pg.cong_hoan_tat(st.session_state))
        v3.handle_v3_event(st, event("clear_case"), st.settings)
        self.assertIsNone(pg.lay_vault(st.session_state))

    def test_invalid_events_are_rejected(self) -> None:
        st = FakeSt()
        with self.assertRaises(v3.V3ContractError):
            v3.handle_v3_event(st, {"event_id": "bad", "type": "navigate"}, st.settings)
        with self.assertRaises(v3.V3ContractError):
            v3.handle_v3_event(st, event("eval_js", code="x"), st.settings)


class V3UploadTests(unittest.TestCase):
    def test_uploaded_synthetic_pdfs_give_baseline_numbers(self) -> None:
        for index in (0, 2, 10, 11):
            with self.subTest(index=index):
                st = FakeSt()
                case = upload_case_through_gateway(st, index)
                expected = {k: v for k, v in BASELINE["pdf_cases"][case.case_id].items() if k != "errors"}
                got = deterministic_snapshot(st.session_state.result)
                for key in ("chi_so", "canh_bao", "trang_thai", "thu_nhap_dung_de_tinh"):
                    self.assertEqual(
                        json.dumps(got[key], ensure_ascii=False, sort_keys=True),
                        json.dumps(expected[key], ensure_ascii=False, sort_keys=True),
                    )

    def test_upload_without_consent_is_not_processed(self) -> None:
        st = FakeSt()
        v3.xu_ly_tep_tai_len_v3(st, case_uploads(synthetic_cases()[0]), st.settings)
        self.assertIsNone(pg.ho_so_cho_xac_nhan(st.session_state))
        self.assertTrue(any("xác nhận" in t["title"].casefold() for t in st.session_state["v3_toasts"]))

    def test_thresholds_use_python_bounds_and_recompute_with_python(self) -> None:
        st = FakeSt()
        open_demo_through_gateway(st, "CASE-01 — Hồ sơ bình thường")
        self.assertNotIn("HIGH_DTI_DEMO", {r.loai for r in st.session_state.result.canh_bao})
        v3.handle_v3_event(st, event("threshold", key="dti_canh_bao", value=0.05), st.settings)
        self.assertIn("HIGH_DTI_DEMO", {r.loai for r in st.session_state.result.canh_bao})
        v3.handle_v3_event(st, event("threshold", key="dti_canh_bao", value=99), st.settings)  # ngoài giới hạn
        self.assertEqual(st.settings["nguong"]["dti_canh_bao"], 0.05)
        v3.handle_v3_event(st, event("threshold_reset"), st.settings)
        self.assertNotIn("HIGH_DTI_DEMO", {r.loai for r in st.session_state.result.canh_bao})


class V3ModelAndSecretsTests(unittest.TestCase):
    def test_default_model_is_not_assumed(self) -> None:
        self.assertEqual(v3.chon_model_mac_dinh("gemini", ["gemini-3.8-flash", "x"]), ("gemini-3.8-flash", None))
        model, notice = v3.chon_model_mac_dinh("gemini", ["gemini-2.5-flash", "gemini-2.5-pro"])
        self.assertEqual(model, "gemini-2.5-flash")
        self.assertIn("không khả dụng", notice or "")

    def test_secrets_key_connects_on_backend_only(self) -> None:
        st = FakeSt(secrets={"GEMINI_API_KEY": SECRET})
        with patch("credit_underwriting_colab.lay_danh_sach_model", return_value=["gemini-2.5-flash"]) as listing:
            v3.ket_noi_gemini_tu_secrets(st)
            v3.ket_noi_gemini_tu_secrets(st)
        listing.assert_called_once_with("gemini", SECRET)
        self.assertEqual(st.session_state["llm_connections"]["gemini"]["model"], "gemini-2.5-flash")
        payload = json.dumps(v3.build_v3_payload(st, st.settings), ensure_ascii=False)
        self.assertNotIn(SECRET, payload)
        self.assertIn('"source": "secrets"', payload)


class V3FallbackTests(unittest.TestCase):
    def test_flag_default_on_and_explicit_off(self) -> None:
        self.assertTrue(v3.ui_v3_enabled({}))
        for value in ("false", "0", "off", " NO "):
            self.assertFalse(v3.ui_v3_enabled({"UI_V3_ENABLED": value}))

    @patch("app.chay_ung_dung_streamlit")
    @patch("app.chay_ung_dung_streamlit_v2")
    @patch("app.chay_ung_dung_streamlit_v3")
    @patch("app.ui_v3_enabled", return_value=True)
    def test_v3_runs_alone(self, _flag: Mock, v3_run: Mock, v2_run: Mock, legacy: Mock) -> None:
        app.main()
        v3_run.assert_called_once_with()
        v2_run.assert_not_called()
        legacy.assert_not_called()

    @patch("app.ui_v2_enabled", return_value=False)
    @patch("app.chay_ung_dung_streamlit")
    @patch("app.chay_ung_dung_streamlit_v2")
    @patch("app.chay_ung_dung_streamlit_v3", side_effect=v3.V3ComponentUnavailable("missing bundle"))
    @patch("app.ui_v3_enabled", return_value=True)
    def test_v3_failure_falls_back_to_v2(self, _flag: Mock, _v3: Mock, v2_run: Mock, legacy: Mock, _v2flag: Mock) -> None:
        app.main()
        v2_run.assert_called_once_with()
        legacy.assert_not_called()

    @patch("app.show_v2_fallback_notice")
    @patch("app.chay_ung_dung_streamlit")
    @patch("app.chay_ung_dung_streamlit_v2", side_effect=RuntimeError("v2"))
    @patch("app.chay_ung_dung_streamlit_v3", side_effect=RuntimeError("v3"))
    @patch("app.ui_v3_enabled", return_value=True)
    def test_v3_and_v2_failure_fall_back_to_legacy(self, _f: Mock, _v3: Mock, _v2: Mock, legacy: Mock, notice: Mock) -> None:
        app.main()
        notice.assert_called_once_with()
        legacy.assert_called_once_with()

    def test_missing_bundle_raises_unavailable(self) -> None:
        with self.assertRaises(v3.V3ComponentUnavailable):
            v3.load_v3_assets(ROOT / "does-not-exist")


class V3BundleTests(unittest.TestCase):
    def test_committed_bundle_has_no_browser_gemini_path_or_mock_upload(self) -> None:
        bundle = (ROOT / "frontend-v3" / "dist" / "creditlens-v3.js").read_text(encoding="utf-8")
        for forbidden in ("generativelanguage.googleapis.com", "dtv_gemini_api_key", "Sample data populated", "Trần Anh Vũ"):
            self.assertNotIn(forbidden, bundle)
        self.assertIn("Bước 0 · Bảo mật hồ sơ", bundle)
        self.assertTrue((ROOT / "frontend-v3" / "dist" / "creditlens-v3.css").read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    unittest.main()
