"""Kiểm thử bắt buộc mục D — Privacy Gateway · Bước 0 · Bảo mật hồ sơ."""

from __future__ import annotations

import json
import pickle
import unittest
from functools import lru_cache
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import privacy_gateway as pg
from credit_underwriting_colab import (
    DEMO_CASES,
    PAGES,
    _noi_dung_yeu_cau_llm,
    du_lieu_demo,
    hien_thi_chat_ai,
    hien_thi_noi_dung_trang,
    khoi_tao_trang_thai_phien,
    mo_ho_so_minh_hoa,
    tao_bao_cao_word,
    tao_dien_giai_bang_ai,
    tao_phan_hoi_chat_ai,
    xu_ly_thu_muc_tai_lieu,
)
from creditlens_ui_v2 import (
    build_app_shell_view_model,
    build_privacy_gateway_view_model,
    serialize_privacy_gateway_view_model,
    serialize_shell_view_model,
)
from tests.fixtures.synthetic_pdfs import case_uploads, deterministic_snapshot, synthetic_cases


BASELINE = json.loads(
    (Path(__file__).resolve().parent / "fixtures" / "privacy_gateway_baseline.json").read_text(encoding="utf-8")
)
CONNECTION = {"provider": "deepseek", "api_key": "sk-test-0000000000000000", "model": "deepseek-chat"}


class AttrState(dict[str, object]):
    def __getattr__(self, name: str) -> object:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: object) -> None:
        self[name] = value


class NullContext:
    def __enter__(self) -> "NullContext":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class FakeSt:
    def __init__(self, **state: object) -> None:
        self.session_state = AttrState(state)
        for name in ("subheader", "info", "markdown", "error", "warning", "success", "caption", "rerun", "header"):
            setattr(self, name, Mock())
        self.prompts: list[str | None] = []

    def chat_input(self, _label: str, **_kwargs: object) -> str | None:
        return self.prompts.pop(0) if self.prompts else None

    def chat_message(self, _role: str) -> NullContext:
        return NullContext()

    def spinner(self, _label: str) -> NullContext:
        return NullContext()


@lru_cache(maxsize=None)
def processed_cases() -> tuple[tuple[Any, Any, Any], ...]:
    output = []
    for case in synthetic_cases():
        result, docs, _errors = xu_ly_thu_muc_tai_lieu(case.case_id, case_uploads(case), None)
        output.append((case, result, docs))
    return tuple(output)


def gateway(result: Any, docs: Any) -> pg.PseudonymVault:
    return pg.build_vault(pg.detect_pii(docs, result))


def fake_httpx_client(captured: list[dict[str, Any]]) -> MagicMock:
    response = Mock(status_code=200)
    response.json.return_value = {"choices": [{"message": {"content": "KH_01 cần con người xem xét."}}]}
    client = MagicMock()
    client.__enter__.return_value = client

    def post(_url: str, **kwargs: Any) -> Mock:
        captured.append(kwargs["json"])
        return response

    client.post.side_effect = post
    return MagicMock(return_value=client)


class BitForBitBaselineTests(unittest.TestCase):
    def test_twenty_pdf_cases_keep_dti_dsr_and_flags_identical_to_baseline(self) -> None:
        cases = processed_cases()
        self.assertEqual(len(cases), 20)
        for case, result, docs in cases:
            with self.subTest(case=case.case_id):
                before = deterministic_snapshot(result)
                vault = gateway(result, docs)
                pg.pseudonymize_result(result, vault)
                _noi_dung_yeu_cau_llm(result, vault)
                after = deterministic_snapshot(result)
                expected = {key: value for key, value in BASELINE["pdf_cases"][case.case_id].items() if key != "errors"}
                encode = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True)  # noqa: E731
                self.assertEqual(encode(before), encode(expected), "Kết quả khác baseline trước cổng")
                self.assertEqual(encode(after), encode(expected), "Giả danh hóa đã làm thay đổi kết quả gốc")

    def test_ten_demo_cases_are_identical_to_baseline(self) -> None:
        for name in DEMO_CASES:
            with self.subTest(case=name):
                result, docs = du_lieu_demo(name, None)
                pg.pseudonymize_result(result, gateway(result, docs))
                self.assertEqual(
                    json.dumps(deterministic_snapshot(result), ensure_ascii=False, sort_keys=True),
                    json.dumps(BASELINE["demo_cases"][name], ensure_ascii=False, sort_keys=True),
                )


class PayloadPrivacyTests(unittest.TestCase):
    def test_llm_payload_contains_no_original_vault_value(self) -> None:
        for case, result, docs in processed_cases():
            with self.subTest(case=case.case_id):
                vault = gateway(result, docs)
                payload = _noi_dung_yeu_cau_llm(result, vault)
                originals = dict(case.pii)
                for key in ("don_vi_cong_tac_ke_khai", "don_vi_cong_tac_chung_tu"):
                    if result.du_lieu.model_dump()[key]:
                        originals[key] = result.du_lieu.model_dump()[key]
                for label, value in originals.items():
                    self.assertFalse(pg._contains_value(payload, value), f"{label} còn trong payload")
                for digits in (case.pii["cccd"], case.pii["sdt"], case.pii["stk"]):
                    self.assertNotIn(digits, payload)
                pg.assert_no_pii(payload, vault)
                data = json.loads(payload[payload.index("{"):])
                self.assertEqual(data["du_lieu"]["ho_ten_khach_hang"], "KH_01")
                self.assertEqual(data["du_lieu"]["so_tien_de_nghi_vay"], result.du_lieu.so_tien_de_nghi_vay)
                self.assertEqual(
                    [item["gia_tri"] for item in data["chi_so"]],
                    [item.gia_tri for item in result.chi_so],
                    "Số liệu chỉ số phải giữ nguyên",
                )

    def test_system_prompt_gets_pseudonymization_note_and_one_request(self) -> None:
        _case, result, docs = processed_cases()[0]
        vault = gateway(result, docs)
        captured: list[dict[str, Any]] = []
        with patch("httpx.Client", fake_httpx_client(captured)):
            tao_dien_giai_bang_ai(result, CONNECTION["api_key"], "deepseek", "deepseek-chat", "Prompt gốc", vault)
        self.assertEqual(len(captured), 1)
        system, user = captured[0]["messages"]
        self.assertIn(pg.PRIVACY_PROMPT_NOTE, system["content"])
        self.assertIn("KH_01", user["content"])
        self.assertNotIn(_case.pii["ho_ten"], user["content"])
        self.assertTrue(any(entry["ket_qua"] == "PASS" for entry in vault.nhat_ky))

    def test_audit_log_records_counts_only(self) -> None:
        case, result, docs = processed_cases()[0]
        vault = gateway(result, docs)
        vault.ghi_nhat_ky("Kiểm thử", provider="deepseek", ket_qua="PASS")
        serialized = json.dumps(vault.nhat_ky, ensure_ascii=False)
        for value in case.pii.values():
            self.assertNotIn(value, serialized)
        self.assertIn("so_truong", serialized)


class TokenConsistencyTests(unittest.TestCase):
    def test_same_value_gets_same_code_across_documents_and_case_variants(self) -> None:
        for case, result, docs in processed_cases():
            with self.subTest(case=case.case_id):
                findings = pg.detect_pii(docs, result)
                names = [item for item in findings if item.loai == "HO_TEN"]
                self.assertEqual([item.ma_thay_the for item in names], ["KH_01"])
        vault = pg.build_vault(
            pg.detect_pii(None, du_lieu_demo("CASE-01 — Hồ sơ bình thường")[0])
        )
        code = vault.ma_cho("Công ty Cổ phần Công nghệ Aurora")
        self.assertEqual(vault.ma_cho("CÔNG TY CỔ PHẦN CÔNG NGHỆ AURORA"), code)
        self.assertEqual(vault.ma_cho("cong  ty co phan cong nghe aurora"), code)

    def test_employer_and_title_mismatch_flags_still_fire_with_distinct_codes(self) -> None:
        by_id = {case.case_id: (case, result, docs) for case, result, docs in processed_cases()}
        for case_id in ("EVAL-007", "EVAL-008", "EVAL-034"):
            _case, result, docs = by_id[case_id]
            payload = pg.pseudonymize_result(result, gateway(result, docs))
            self.assertIn("EMPLOYER_MISMATCH", {risk.loai for risk in result.canh_bao})
            self.assertIn("EMPLOYER_MISMATCH", {risk["loai"] for risk in payload["canh_bao"]})
            self.assertEqual(payload["du_lieu"]["don_vi_cong_tac_ke_khai"], "DN_A")
            self.assertEqual(payload["du_lieu"]["don_vi_cong_tac_chung_tu"], "DN_B")
        _case, result, docs = by_id["EVAL-001"]
        payload = pg.pseudonymize_result(result, gateway(result, docs))
        self.assertEqual(payload["du_lieu"]["don_vi_cong_tac_ke_khai"], payload["du_lieu"]["don_vi_cong_tac_chung_tu"])
        _case, result, docs = by_id["EVAL-031"]
        payload = pg.pseudonymize_result(result, gateway(result, docs))
        flags = {risk["loai"] for risk in payload["canh_bao"]}
        self.assertTrue({"JOB_TITLE_MISMATCH", "EMPLOYMENT_DATE_MISMATCH"} <= flags)
        self.assertEqual(payload["du_lieu"]["ngay_bat_dau_ke_khai"], "06/2022")
        self.assertEqual(payload["du_lieu"]["ngay_bat_dau_chung_tu"], "02/2023")


class ChatPrivacyTests(unittest.TestCase):
    def _vault(self) -> pg.PseudonymVault:
        case, result, docs = processed_cases()[0]
        self.assertEqual(case.pii["ho_ten"], "Nguyễn Minh Anh")
        return gateway(result, docs)

    def test_chat_question_is_sent_pseudonymized(self) -> None:
        vault = self._vault()
        captured: list[dict[str, Any]] = []
        messages = [{"role": "user", "content": "khách Nguyễn Minh Anh SĐT 0901234567"}]
        with patch("httpx.Client", fake_httpx_client(captured)):
            tao_phan_hoi_chat_ai(messages, CONNECTION["api_key"], "deepseek", "deepseek-chat", vault)
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["messages"][-1]["content"], "khách KH_01 SĐT [SĐT_ĐÃ_CHE]")
        self.assertEqual(messages[0]["content"], "khách Nguyễn Minh Anh SĐT 0901234567", "Không sửa lịch sử gốc")

    def test_chat_history_is_pseudonymized_and_display_can_reidentify(self) -> None:
        vault = self._vault()
        captured: list[dict[str, Any]] = []
        history = [
            {"role": "user", "content": "Email khách là khach01.demo@example.com"},
            {"role": "assistant", "content": "Đã ghi nhận cho KH_01."},
            {"role": "user", "content": "nguyen minh anh có nợ khác không?"},
        ]
        with patch("httpx.Client", fake_httpx_client(captured)):
            response = tao_phan_hoi_chat_ai(history, CONNECTION["api_key"], "deepseek", "deepseek-chat", vault)
        sent = json.dumps(captured[0]["messages"], ensure_ascii=False)
        self.assertNotIn("example.com", sent)
        self.assertIn("KH_01 có nợ khác không?", sent)
        self.assertEqual(pg.reidentify_for_display(response, vault), "Nguyễn Minh Anh cần con người xem xét.")


class FailClosedTests(unittest.TestCase):
    def test_leaked_chat_pii_blocks_request_with_zero_inference(self) -> None:
        _case, result, docs = processed_cases()[0]
        vault = gateway(result, docs)
        client = MagicMock()
        with patch("privacy_gateway.pseudonymize_text", side_effect=lambda text, _vault: text), patch(
            "httpx.Client", client
        ), patch("openai.OpenAI") as openai_client:
            with self.assertRaises(pg.PrivacyLeakError):
                tao_phan_hoi_chat_ai(
                    [{"role": "user", "content": "khách Nguyễn Minh Anh SĐT 0901234567"}],
                    CONNECTION["api_key"],
                    "deepseek",
                    "deepseek-chat",
                    vault,
                )
        client.assert_not_called()
        openai_client.assert_not_called()
        self.assertTrue(any(entry["ket_qua"].startswith("FAIL") for entry in vault.nhat_ky))

    def test_leaked_summary_payload_blocks_request_with_zero_inference(self) -> None:
        case, result, docs = processed_cases()[0]
        vault = gateway(result, docs)
        client = MagicMock()
        with patch("privacy_gateway.pseudonymize_result", side_effect=lambda res, _v: res.model_dump(mode="json")), patch(
            "httpx.Client", client
        ), patch("openai.OpenAI") as openai_client:
            for provider, model in (("deepseek", "deepseek-chat"), ("openai", "gpt-5-mini")):
                with self.assertRaises(pg.PrivacyLeakError) as raised:
                    tao_dien_giai_bang_ai(result, CONNECTION["api_key"], provider, model, "Prompt", vault)
                self.assertNotIn(case.pii["ho_ten"], str(raised.exception))
        client.assert_not_called()
        openai_client.assert_not_called()

    def test_assert_detects_raw_identifiers_even_without_vault(self) -> None:
        for leaked in ("Liên hệ 0901234567", "Gửi a.b@example.com", "Số CCCD: 079193000000", "Số tài khoản: 1903567890120"):
            with self.subTest(leaked=leaked), self.assertRaises(pg.PrivacyLeakError):
                pg.assert_no_pii(leaked, None)
        pg.assert_no_pii(json.dumps({"so_tien": 600000000.0, "ma": "CASE-20261015-01"}), None)


class GateBypassTests(unittest.TestCase):
    def _state(self, **extra: object) -> FakeSt:
        st = FakeSt(**extra)
        khoi_tao_trang_thai_phien(st)
        return st

    def test_direct_access_to_later_pages_is_locked_until_gateway_completes(self) -> None:
        st = self._state()
        result, docs = du_lieu_demo("CASE-03 — Thu nhập không nhất quán")
        st.session_state.result = result  # dữ liệu có sẵn nhưng chưa qua cổng
        for page in pg.LOCKED_PAGES:
            with self.subTest(page=page), patch("credit_underwriting_colab.trang_trich_xuat") as extraction, patch(
                "credit_underwriting_colab.trang_tom_tat"
            ) as summary:
                st.warning.reset_mock()
                hien_thi_noi_dung_trang(st, page, {}, st.session_state.settings)
                extraction.assert_not_called()
                summary.assert_not_called()
                st.warning.assert_called_once()
                self.assertIn("Bước 0", st.warning.call_args.args[0])

    def test_v2_shell_marks_locked_pages_and_chat_is_locked(self) -> None:
        st = self._state()
        shell = serialize_shell_view_model(
            build_app_shell_view_model(
                active_page=PAGES[0],
                pages=tuple(PAGES),
                page_labels={page: f"{index}.  {page}" for index, page in enumerate(PAGES, start=1)},
                settings=st.session_state.settings,
                logo_data_uri="data:image/png;base64,AA==",
                result=None,
                session_state=st.session_state,
                status_labels={},
            )
        )
        locked = {item["page"] for item in shell["navigation"] if item["locked"]}
        self.assertEqual(locked, set(pg.LOCKED_PAGES))
        self.assertEqual(shell["privacy"]["state"], "pending")
        with patch("credit_underwriting_colab.tao_phan_hoi_chat_ai") as inference:
            st.prompts = ["Câu hỏi"]
            hien_thi_chat_ai(st, CONNECTION)
        inference.assert_not_called()
        st.info.assert_called_with(pg.CHAT_LOCK_REASON)

    def test_gateway_flow_requires_consent_unlocks_pages_and_clear_removes_vault(self) -> None:
        st = self._state()
        mo_ho_so_minh_hoa(st, "CASE-04 — Đơn vị công tác không khớp", {})
        self.assertIsNone(st.session_state.result, "Hồ sơ chưa được mở trước khi xác nhận")
        self.assertTrue(pg.trang_bi_khoa(PAGES[1], st.session_state))
        with self.assertRaises(ValueError):
            pg.xac_nhan_cong(st)
        st.session_state[pg.KEY_CONSENT] = True
        vault = pg.xac_nhan_cong(st)
        self.assertIsNotNone(st.session_state.result)
        self.assertFalse(pg.trang_bi_khoa(PAGES[1], st.session_state))
        state, label, count = pg.nhan_huy_hieu(st.session_state)
        self.assertEqual((state, label), ("done", f"Đã giả danh hóa · {count} trường"))
        self.assertEqual(vault.so_truong, count)
        pg.xoa_ho_so_phien(st.session_state)
        self.assertIsNone(pg.lay_vault(st.session_state))
        self.assertTrue(pg.trang_bi_khoa(PAGES[1], st.session_state))


class VaultIsolationTests(unittest.TestCase):
    def test_vault_cannot_be_serialized_and_react_payload_has_masked_values_only(self) -> None:
        case, result, docs = processed_cases()[0]
        vault = gateway(result, docs)
        with self.assertRaises(TypeError):
            pickle.dumps(vault)
        with self.assertRaises(TypeError):
            json.dumps(vault)
        self.assertNotIn(case.pii["ho_ten"], repr(vault))
        st = FakeSt()
        khoi_tao_trang_thai_phien(st)
        pg.dua_vao_cong(st, result, docs, "Tài liệu")
        payload = json.dumps(
            serialize_privacy_gateway_view_model(build_privacy_gateway_view_model(session_state=st.session_state, theme="light")),
            ensure_ascii=False,
        )
        self.assertIn("KH_01", payload)
        for value in case.pii.values():
            self.assertNotIn(value, payload)
        self.assertNotIn("Công ty Cổ phần Minh Long", payload)

    def test_cccd_phone_email_account_are_not_stored_in_vault(self) -> None:
        case, result, docs = processed_cases()[0]
        findings = pg.detect_pii(docs, result)
        for item in findings:
            if item.loai in pg.NON_REVERSIBLE:
                self.assertIsNone(item.gia_tri)
        vault = pg.build_vault(findings)
        stored = " ".join(vault._reversible.values()) + " ".join(real for real, _code, _loai in vault._replacements.values())
        for key in ("cccd", "sdt", "email", "stk"):
            self.assertNotIn(case.pii[key], stored)

    def test_reports_default_to_pseudonymized_version(self) -> None:
        case, result, docs = processed_cases()[0]
        vault = gateway(result, docs)
        masked, ai_text = pg.ket_qua_cho_bao_cao(result, "KH_01 tại DN_A", vault, pg.REPORT_VERSIONS[0])
        self.assertEqual(masked.du_lieu.ho_ten_khach_hang, "KH_01")
        self.assertEqual(ai_text, "KH_01 tại DN_A")
        self.assertEqual(tao_bao_cao_word(masked, ai_text)[:2], b"PK")
        full, full_text = pg.ket_qua_cho_bao_cao(result, "KH_01 tại DN_A", vault, pg.REPORT_VERSIONS[1])
        self.assertIs(full, result)
        self.assertEqual(full_text, f"{case.pii['ho_ten']} tại Công ty Cổ phần Minh Long")


if __name__ == "__main__":
    unittest.main()
