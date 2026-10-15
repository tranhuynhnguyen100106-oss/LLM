from __future__ import annotations

import json
import inspect
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import app
from creditlens_ui_v2 import (
    V2AppShellViewModel,
    V2CaseContext,
    UIContractError,
    V2ComponentUnavailable,
    V2DemoCaseItem,
    V2DemoPanelViewModel,
    V2EvaluationEvent,
    V2NavigationItem,
    V2ProcessCard,
    V2SettingsPageViewModel,
    _claim_ui_event,
    build_core_page_view_model,
    build_evaluation_page_view_model,
    build_methodology_page_view_model,
    build_summary_page_view_model,
    build_settings_page_view_model,
    V2WorkflowStep,
    build_workflow_steps,
    get_component_renderer,
    load_component_assets,
    parse_ui_event,
    queue_v2_upload_action,
    render_core_page,
    render_evaluation_page,
    render_settings_page,
    serialize_demo_panel_view_model,
    serialize_core_page_view_model,
    serialize_evaluation_page_view_model,
    serialize_methodology_page_view_model,
    serialize_shell_view_model,
    serialize_summary_page_view_model,
    serialize_settings_page_view_model,
    show_v2_fallback_notice,
    ui_v2_enabled,
)
from credit_underwriting_colab import (
    DEMO_CASES,
    NHA_CUNG_CAP_LLM,
    _ghi_log_loi_chat_an_toan,
    bao_cao_markdown,
    cau_hinh_mac_dinh,
    du_lieu_demo,
    gia_tri_truong_hien_thi,
    hien_thi_chat_ai,
    ket_noi_llm_dang_dung,
    nguong_hieu_luc,
    tao_bao_cao_excel,
    tao_bao_cao_pdf,
    tao_bao_cao_word,
    trang_cai_dat,
)
from evaluation.evaluator import run_evaluation


VALID_NAVIGATION_EVENT = {
    "schema_version": "1.0",
    "component_version": "0.5.0",
    "component": "app_shell",
    "type": "navigation.select",
    "action": "select",
    "event_id": "evt_12345678",
    "page": "Tổng quan",
}


class FakeV2Factory:
    def __init__(self) -> None:
        self.registration: dict[str, object] = {}

    def component(self, name: str, **kwargs: object):
        self.registration = {"name": name, **kwargs}
        return lambda **_render_kwargs: {"event": None}


class FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, object] = {}
        self.rerun = Mock()
        self.warning = Mock()
        factory = FakeV2Factory()
        self.components = type("Components", (), {"v2": factory})()


class AttrState(dict[str, object]):
    def __getattr__(self, name: str) -> object:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: object) -> None:
        self[name] = value


class NullContext:
    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class FakeChatStreamlit:
    def __init__(self, prompts: list[str | None], messages: list[dict[str, str]] | None = None) -> None:
        self.prompts = list(prompts)
        self.session_state = AttrState(llm_chat_messages=list(messages or []))
        self.subheader = Mock()
        self.info = Mock()
        self.markdown = Mock()
        self.error = Mock()
        self.chat_input_calls: list[dict[str, object]] = []

    def chat_input(self, label: str, **kwargs: object) -> str | None:
        self.chat_input_calls.append({"label": label, **kwargs})
        return self.prompts.pop(0) if self.prompts else None

    def chat_message(self, _role: str) -> NullContext:
        return NullContext()

    def spinner(self, _label: str) -> NullContext:
        return NullContext()


class UIContractsTests(unittest.TestCase):
    def test_feature_flag_is_opt_in_and_strict(self) -> None:
        self.assertFalse(ui_v2_enabled({}))
        self.assertFalse(ui_v2_enabled({"UI_V2_ENABLED": "unexpected"}))
        for value in ("1", "true", "TRUE", " yes ", "on"):
            self.assertTrue(ui_v2_enabled({"UI_V2_ENABLED": value}))

    def test_invalid_or_secret_shaped_event_is_rejected(self) -> None:
        valid_event = {
            "schema_version": "1.0",
            "component_version": "0.5.0",
            "component": "app_shell",
            "type": "navigation.select",
            "action": "select",
            "event_id": "evt_12345678",
            "page": "Tổng quan",
        }
        with self.assertRaises(UIContractError):
            parse_ui_event({**valid_event, "token": "never-accept"})
        with self.assertRaises(UIContractError):
            parse_ui_event({**valid_event, "action": "recompute_credit"})
        with self.assertRaises(UIContractError):
            parse_ui_event(
                {
                    "schema_version": "1.0",
                    "component_version": "0.5.0",
                    "component": "v2_status_card",
                    "type": "status_card.action",
                    "action": "acknowledge",
                    "event_id": "evt_12345678",
                }
            )

    def test_domain_event_handler_is_idempotent(self) -> None:
        state: dict[str, object] = {}
        self.assertTrue(_claim_ui_event(state, "evt_12345678"))
        self.assertFalse(_claim_ui_event(state, "evt_12345678"))
        self.assertEqual(state["ui_v2_last_event_id"], "evt_12345678")

    def test_cluster_3_events_are_typed_and_strict(self) -> None:
        navigation = parse_ui_event(
            {
                "schema_version": "1.0",
                "component_version": "0.5.0",
                "component": "app_shell",
                "type": "navigation.select",
                "action": "select",
                "event_id": "evt_nav_1234",
                "page": "2_extraction",
            }
        )
        self.assertEqual(navigation.page, "2_extraction")  # type: ignore[union-attr]
        with self.assertRaises(UIContractError):
            parse_ui_event(
                {
                    "schema_version": "1.0",
                    "component_version": "0.5.0",
                    "component": "demo_panel",
                    "type": "demo.open",
                    "action": "select",
                    "event_id": "evt_demo_1234",
                    "case_name": "CASE-03 — Hồ sơ tiêu chuẩn",
                }
            )

    def test_upload_action_lock_is_idempotent(self) -> None:
        state: dict[str, object] = {}
        self.assertTrue(queue_v2_upload_action(state))
        self.assertFalse(queue_v2_upload_action(state))
        self.assertTrue(state["ui_v2_processing"])
        self.assertTrue(state["ui_v2_upload_requested"])

    def test_workflow_is_four_step_python_derived_presentation(self) -> None:
        empty = build_workflow_steps(None)
        self.assertEqual([step.key for step in empty], ["intake", "compute", "crosscheck", "human"])
        self.assertEqual([step.state for step in empty], ["current", "upcoming", "upcoming", "upcoming"])
        processing = build_workflow_steps(None, processing=True)
        self.assertEqual(processing[0].status_label, "Đang xử lý")

    def test_shell_and_demo_payloads_are_allowlisted(self) -> None:
        workflow = tuple(
            V2WorkflowStep(key=key, label=label, description="Mô tả", state=state, status_label="Trạng thái")
            for key, label, state in (
                ("intake", "Tiếp nhận", "current"),
                ("compute", "Tính toán", "upcoming"),
                ("crosscheck", "Đối chiếu", "upcoming"),
                ("human", "Con người xem xét", "upcoming"),
            )
        )
        cards = tuple(
            V2ProcessCard(key=step.key, label=step.label, description="Mô tả", state=step.state)
            for step in workflow
        )
        navigation = tuple(
            V2NavigationItem(page=f"page-{index}", label=f"Trang {index}", group="Hồ sơ", ordinal=index)
            for index in range(1, 9)
        )
        context = V2CaseContext(
            case_id=None,
            source=None,
            status_label="Chưa có hồ sơ",
            status_tone="neutral",
            summary="Tải tài liệu để tiếp tục.",
        )
        shell = serialize_shell_view_model(
            V2AppShellViewModel(
                active_page="page-1",
                navigation=navigation,
                workflow=workflow,
                process_cards=cards,
                case_context=context,
                logo_data_uri="data:image/png;base64,AA==",
            )
        )
        self.assertEqual(shell["component"], "app_shell")
        self.assertNotIn("settings", shell)

        demo_cases = tuple(
            V2DemoCaseItem(
                case_name=f"CASE-{index:02d} — Tình huống {index}",
                case_code=f"CASE-{index:02d}",
                title=f"Tình huống {index}",
                description="Dữ liệu tổng hợp xác định.",
            )
            for index in range(1, 11)
        )
        demo = serialize_demo_panel_view_model(
            V2DemoPanelViewModel(cases=demo_cases, selected_case=demo_cases[2].case_name, case_context=context)
        )
        self.assertEqual(len(demo["cases"]), 10)
        self.assertNotIn("ground_truth", json.dumps(demo, ensure_ascii=False))

    def test_component_registration_uses_local_assets_and_style_isolation(self) -> None:
        with patch.object(
            Path,
            "read_text",
            side_effect=["export default () => {};", ":host { display: block; }"],
        ):
            st = FakeStreamlit()
            renderer = get_component_renderer(st, Path("synthetic-assets"))
            self.assertTrue(callable(renderer))
            registration = st.components.v2.registration
            self.assertEqual(registration["name"], "creditlens_v2_status_card")
            self.assertTrue(registration["isolate_styles"])
            self.assertNotIn("http", registration["js"])

    def test_component_registration_is_reused_across_reruns(self) -> None:
        st = FakeStreamlit()
        with patch("creditlens_ui_v2.load_component_assets", return_value=("export default () => {};", ":host{}")):
            first = get_component_renderer(st, Path("cache-assets-a"))
            second = get_component_renderer(st, Path("cache-assets-a"))
        self.assertIs(first, second)

    def test_missing_build_artifact_raises_safe_unavailable_error(self) -> None:
        with patch.object(Path, "read_text", side_effect=FileNotFoundError):
            with self.assertRaisesRegex(V2ComponentUnavailable, "chưa sẵn sàng"):
                load_component_assets(Path("missing-assets"))

    def test_fallback_notice_never_exposes_exception_details(self) -> None:
        st = FakeStreamlit()
        show_v2_fallback_notice(st)
        message = st.warning.call_args.args[0]
        self.assertIn("giao diện dự phòng ổn định", message)
        self.assertNotIn("Exception", message)


class Cluster4CorePagesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.thresholds = nguong_hieu_luc()

    def test_extraction_view_model_preserves_values_confidence_and_evidence(self) -> None:
        result, docs = du_lieu_demo("CASE-09 — Độ tin cậy thấp", self.thresholds)
        view_model = build_core_page_view_model(
            page="extraction",
            result=result,
            docs=docs,
            thresholds=self.thresholds,
            theme="light",
        )
        payload = serialize_core_page_view_model(view_model)
        fields = {item["key"]: item for item in payload["fields"]}

        self.assertEqual(
            {key: item["value_display"] for key, item in fields.items()},
            {field.ma_truong: gia_tri_truong_hien_thi(field) for field in result.truong_trich_xuat},
        )
        self.assertEqual(
            {key: item["confidence"] for key, item in fields.items()},
            {field.ma_truong: field.do_tin_cay for field in result.truong_trich_xuat},
        )
        low = fields["luong_thuc_nhan"]
        self.assertEqual(low["confidence_display"], "58,0%")
        self.assertEqual(low["confidence_label"], "Cần xác minh")
        self.assertEqual(low["confidence_tone"], "danger")
        self.assertEqual(low["evidence"]["document"], "chung_tu_thu_nhap.pdf")
        self.assertEqual(len(payload["documents"]), len(docs))

    def test_analysis_view_model_preserves_all_metrics_and_thresholds(self) -> None:
        result, docs = du_lieu_demo("CASE-10 — Nhiều cảnh báo đồng thời", self.thresholds)
        payload = serialize_core_page_view_model(
            build_core_page_view_model(
                page="analysis",
                result=result,
                docs=docs,
                thresholds=self.thresholds,
                theme="dark",
            )
        )
        metrics = {item["key"]: item for item in payload["metrics"]}
        self.assertEqual(set(metrics), {item.ma_chi_so for item in result.chi_so})
        for metric in result.chi_so:
            rendered = metrics[metric.ma_chi_so]
            self.assertEqual(rendered["raw_value"], metric.gia_tri)
            self.assertEqual(rendered["value_display"], metric.hien_thi)
            self.assertEqual(rendered["status"], metric.trang_thai)
            self.assertEqual(rendered["formula"], metric.cong_thuc)

        thresholds = {item["key"]: item["value"] for item in payload["thresholds"]}
        for key in (
            "chenh_lech_thu_nhap",
            "dti_canh_bao",
            "dsr_canh_bao",
            "he_so_dem_so_du_thap",
            "bien_dong_thu_nhap_cao",
        ):
            self.assertEqual(thresholds[key], self.thresholds[key])
        comparison = payload["comparisons"][0]
        income_metric = next(item for item in result.chi_so if item.ma_chi_so == "chenh_lech_thu_nhap")
        self.assertEqual(comparison["difference_display"], income_metric.hien_thi)
        self.assertEqual(comparison["status"], income_metric.trang_thai)

    def test_risk_view_model_preserves_flags_severity_status_and_evidence(self) -> None:
        result, docs = du_lieu_demo("CASE-10 — Nhiều cảnh báo đồng thời", self.thresholds)
        payload = serialize_core_page_view_model(
            build_core_page_view_model(
                page="risk",
                result=result,
                docs=docs,
                thresholds=self.thresholds,
                theme="system",
            )
        )
        risks = {item["code"]: item for item in payload["risks"]}
        self.assertEqual(set(risks), {item.ma_rui_ro for item in result.canh_bao})
        for risk in result.canh_bao:
            rendered = risks[risk.ma_rui_ro]
            self.assertEqual(rendered["severity"], risk.muc_do)
            self.assertEqual(rendered["description"], risk.giai_thich)
            self.assertEqual(rendered["difference"], risk.chenh_lech)
            self.assertEqual(len(rendered["evidence"]), len(risk.bang_chung))
        self.assertEqual(payload["case_status"], "CẦN CON NGƯỜI XEM XÉT")

    def test_empty_loading_partial_and_error_states_are_deterministic(self) -> None:
        empty = build_core_page_view_model(
            page="extraction",
            result=None,
            docs={},
            thresholds=self.thresholds,
            theme="light",
        )
        loading = build_core_page_view_model(
            page="analysis",
            result=None,
            docs={},
            thresholds=self.thresholds,
            theme="light",
            processing=True,
        )
        error = build_core_page_view_model(
            page="risk",
            result=None,
            docs={},
            thresholds=self.thresholds,
            theme="light",
            error="Lỗi trình bày an toàn",
        )
        partial_result, partial_docs = du_lieu_demo("CASE-07 — Sao kê không đọc được", self.thresholds)
        partial = build_core_page_view_model(
            page="extraction",
            result=partial_result,
            docs=partial_docs,
            thresholds=self.thresholds,
            theme="light",
        )
        self.assertEqual((empty.state, loading.state, partial.state, error.state), ("empty", "loading", "partial", "error"))

    def test_core_page_is_presentation_only_and_rejects_browser_events(self) -> None:
        result, docs = du_lieu_demo(next(iter(DEMO_CASES)), self.thresholds)
        view_model = build_core_page_view_model(
            page="analysis",
            result=result,
            docs=docs,
            thresholds=self.thresholds,
            theme="light",
        )

        def renderer(**_kwargs: object) -> dict[str, object]:
            return {"event": VALID_NAVIGATION_EVENT}

        with self.assertRaisesRegex(UIContractError, "không được phát domain event"):
            render_core_page(FakeStreamlit(), view_model, renderer=renderer)

    def test_all_ten_demo_cases_have_exact_business_output_parity(self) -> None:
        for case_name in DEMO_CASES:
            with self.subTest(case=case_name):
                result, docs = du_lieu_demo(case_name, self.thresholds)
                extraction = serialize_core_page_view_model(
                    build_core_page_view_model(
                        page="extraction",
                        result=result,
                        docs=docs,
                        thresholds=self.thresholds,
                        theme="light",
                    )
                )
                analysis = serialize_core_page_view_model(
                    build_core_page_view_model(
                        page="analysis",
                        result=result,
                        docs=docs,
                        thresholds=self.thresholds,
                        theme="light",
                    )
                )
                risk = serialize_core_page_view_model(
                    build_core_page_view_model(
                        page="risk",
                        result=result,
                        docs=docs,
                        thresholds=self.thresholds,
                        theme="light",
                    )
                )

                extracted_by_key = {item["key"]: item for item in extraction["fields"]}
                for field in result.truong_trich_xuat:
                    rendered = extracted_by_key[field.ma_truong]
                    self.assertEqual(rendered["raw_value"], field.gia_tri)
                    self.assertEqual(rendered["value_display"], gia_tri_truong_hien_thi(field))
                    self.assertEqual(rendered["source"], field.tai_lieu_nguon)
                    self.assertEqual(rendered["page"], field.trang)
                    self.assertEqual(rendered["confidence"], field.do_tin_cay)

                metrics_by_key = {item["key"]: item for item in analysis["metrics"]}
                for metric in result.chi_so:
                    rendered = metrics_by_key[metric.ma_chi_so]
                    self.assertEqual(
                        (rendered["raw_value"], rendered["value_display"], rendered["status"]),
                        (metric.gia_tri, metric.hien_thi, metric.trang_thai),
                    )

                risks_by_code = {item["code"]: item for item in risk["risks"]}
                for warning in result.canh_bao:
                    rendered = risks_by_code[warning.ma_rui_ro]
                    self.assertEqual(rendered["severity"], warning.muc_do)
                    self.assertEqual(rendered["difference"], warning.chenh_lech)
                    self.assertEqual(rendered["description"], warning.giai_thich)
                    self.assertEqual(len(rendered["evidence"]), len(warning.bang_chung))


class Cluster5SupportPagesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.thresholds = nguong_hieu_luc()

    def test_summary_has_exact_status_metrics_risks_findings_and_evidence_parity(self) -> None:
        for case_name in DEMO_CASES:
            with self.subTest(case=case_name):
                result, docs = du_lieu_demo(case_name, self.thresholds)
                payload = serialize_summary_page_view_model(
                    build_summary_page_view_model(
                        result=result,
                        docs=docs,
                        thresholds=self.thresholds,
                        ai_explanation="Diễn giải đã có trong phiên",
                        theme="light",
                    )
                )
                self.assertEqual(payload["case_id"], result.ma_ho_so)
                self.assertEqual(payload["total_risk_count"], len(result.canh_bao))
                self.assertEqual(payload["document_count"], len(docs))
                self.assertEqual(payload["extracted_field_count"], len(result.truong_trich_xuat))
                metrics = {item["key"]: item for item in payload["metrics"]}
                for metric in result.chi_so:
                    self.assertEqual(metrics[metric.ma_chi_so]["raw_value"], metric.gia_tri)
                    self.assertEqual(metrics[metric.ma_chi_so]["value_display"], metric.hien_thi)
                    self.assertEqual(metrics[metric.ma_chi_so]["status"], metric.trang_thai)
                self.assertEqual(
                    [item["code"] for item in payload["top_risks"]],
                    [item.ma_rui_ro for item in result.canh_bao[:3]],
                )
                self.assertEqual(
                    len(payload["evidence"]),
                    sum(len(item.bang_chung) for item in result.canh_bao),
                )
                self.assertEqual(payload["ai_explanation"], "Diễn giải đã có trong phiên")

    def test_summary_human_review_is_presentation_only_and_preserves_backend_status(self) -> None:
        result, docs = du_lieu_demo("CASE-08 — Đơn vay chưa đầy đủ", self.thresholds)
        view_model = build_summary_page_view_model(
            result=result,
            docs=docs,
            thresholds=self.thresholds,
            ai_explanation=None,
            theme="dark",
        )
        payload = serialize_summary_page_view_model(view_model)
        self.assertEqual(view_model.state, "partial")
        self.assertEqual(payload["review_status"], "THÔNG TIN CHƯA ĐỦ")
        self.assertTrue(any(item["category"] == "missing" for item in payload["findings"]))
        self.assertIsNone(payload["ai_explanation"])

    def test_methodology_preserves_current_layers_formulas_capabilities_and_limitations(self) -> None:
        payload = serialize_methodology_page_view_model(
            build_methodology_page_view_model(theme="system")
        )
        self.assertEqual([item["key"] for item in payload["layers"]], ["facts", "deterministic", "ai"])
        formulas = {item["key"]: item["formula"] for item in payload["formulas"]}
        self.assertEqual(formulas["dti"], "Nghĩa vụ nợ hiện hữu ÷ Thu nhập dùng để tính")
        self.assertEqual(
            formulas["dsr"],
            "(Nợ hiện hữu + Khoản trả dự kiến) ÷ Thu nhập dùng để tính",
        )
        self.assertEqual(len(payload["capabilities"]), 5)
        self.assertIn("SELF-TEST", payload["self_test_definition"])
        self.assertIn("EVALUATION", payload["evaluation_definition"])

    def test_evaluation_view_model_is_exact_saved_report_presentation(self) -> None:
        report = run_evaluation(app_version="cluster-5-test")
        payload = serialize_evaluation_page_view_model(
            build_evaluation_page_view_model(report=report, theme="light")
        )
        scorecards = {item["key"]: item for item in payload["scorecards"]}
        self.assertEqual(
            scorecards["extraction_accuracy"]["raw_value"],
            report["overall_summary"]["extraction_accuracy"],
        )
        self.assertEqual(scorecards["risk_precision"]["raw_value"], report["risk_detection"]["precision"])
        self.assertEqual(scorecards["risk_recall"]["raw_value"], report["risk_detection"]["recall"])
        self.assertEqual(scorecards["risk_f1"]["raw_value"], report["risk_detection"]["f1"])
        self.assertEqual(payload["llm_api_calls"], 0)
        self.assertEqual(len(payload["field_metrics"]), len(report["extraction_metrics"]["by_field"]))
        self.assertEqual(len(payload["risk_metrics"]), len(report["risk_detection"]["by_risk"]))
        self.assertEqual(len(payload["confusion_rows"]), 3)
        self.assertEqual(len(payload["baselines"]), 4)
        self.assertEqual(len(payload["failure_cases"]), len(report["failure_cases"]))
        self.assertEqual(
            payload["confusion_rows"][0]["predicted"],
            list(list(report["status_classification"]["confusion_matrix"].values())[0].values()),
        )

    @patch("credit_underwriting_colab.tao_phan_hoi_chat_ai")
    @patch("credit_underwriting_colab.tao_dien_giai_bang_ai")
    def test_deterministic_evaluation_and_rendering_make_no_llm_calls(
        self,
        ai_summary: Mock,
        ai_chat: Mock,
    ) -> None:
        report = run_evaluation()
        serialize_evaluation_page_view_model(
            build_evaluation_page_view_model(report=report, theme="light")
        )
        ai_summary.assert_not_called()
        ai_chat.assert_not_called()
        self.assertEqual(report["reproducibility"]["llm_api_calls"], 0)

    def test_evaluation_event_is_strict_and_render_accepts_only_run_event(self) -> None:
        raw_event = {
            "schema_version": "1.0",
            "component_version": "0.5.0",
            "component": "evaluation_page",
            "type": "evaluation.run",
            "action": "run",
            "event_id": "eval_12345678",
        }
        self.assertEqual(parse_ui_event(raw_event), V2EvaluationEvent(event_id="eval_12345678"))
        idle = build_evaluation_page_view_model(report=None, theme="light")

        def renderer(**_kwargs: object) -> dict[str, object]:
            return {"event": raw_event}

        event = render_evaluation_page(FakeStreamlit(), idle, renderer=renderer)
        self.assertEqual(event, V2EvaluationEvent(event_id="eval_12345678"))
        with self.assertRaises(UIContractError):
            parse_ui_event({**raw_event, "action": "filter"})

    def test_word_excel_pdf_markdown_and_json_export_outputs_remain_valid(self) -> None:
        result, _docs = du_lieu_demo("CASE-03 — Thu nhập không nhất quán", self.thresholds)
        docx_data = tao_bao_cao_word(result, "", self.thresholds["do_tin_cay_thap"])
        xlsx_data = tao_bao_cao_excel(result, "", self.thresholds["do_tin_cay_thap"])
        pdf_data = tao_bao_cao_pdf(result, "", self.thresholds["do_tin_cay_thap"])
        markdown_data = bao_cao_markdown(result)
        json_data = json.dumps(result.model_dump(mode="json"), ensure_ascii=False)
        self.assertEqual(docx_data[:2], b"PK")
        self.assertEqual(xlsx_data[:2], b"PK")
        self.assertEqual(pdf_data[:5], b"%PDF-")
        self.assertIn(result.ma_ho_so, markdown_data)
        self.assertEqual(json.loads(json_data)["ma_ho_so"], result.ma_ho_so)


class Cluster6SettingsAndChatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = cau_hinh_mac_dinh()
        self.thresholds = nguong_hieu_luc(self.settings["nguong"])
        self.secret = "sk-proj-CLUSTER6-SENTINEL-123456"
        self.connection = {
            "provider": "openai",
            "api_key": self.secret,
            "fingerprint": "sentinel-fingerprint-must-stay-backend",
            "models": ["gpt-test", "gpt-second"],
            "model": "gpt-test",
            "verified": True,
        }

    def _state(self) -> AttrState:
        return AttrState(
            llm_connections={"openai": dict(self.connection)},
            active_llm_provider="openai",
            llm_chat_messages=[
                {"role": "user", "content": "Câu hỏi trước"},
                {"role": "assistant", "content": "Phản hồi trước"},
            ],
            evaluation_report={"ready": True},
            llm_connection_error="",
        )

    def test_settings_payload_is_allowlisted_and_never_contains_credentials_or_chat_content(self) -> None:
        result, _docs = du_lieu_demo("CASE-03 — Thu nhập không nhất quán", self.thresholds)
        payload = serialize_settings_page_view_model(
            build_settings_page_view_model(
                settings=self.settings,
                session_state=self._state(),
                provider_catalog=NHA_CUNG_CAP_LLM,
                thresholds=self.thresholds,
                result=result,
                theme="dark",
            )
        )
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertEqual(payload["component"], "settings_page")
        self.assertEqual(payload["connection_status_label"], "CONNECTED")
        self.assertEqual(payload["active_provider_label"], "OpenAI · GPT")
        self.assertEqual(payload["active_model"], "gpt-test")
        self.assertEqual(payload["chat_message_count"], 2)
        self.assertNotIn(self.secret, serialized)
        self.assertNotIn("sentinel-fingerprint", serialized)
        self.assertNotIn("Câu hỏi trước", serialized)
        self.assertNotIn("Phản hồi trước", serialized)
        self.assertNotIn("api_key", serialized.casefold())
        self.assertNotIn("fingerprint", serialized.casefold())

    def test_provider_model_and_thresholds_preserve_existing_session_values(self) -> None:
        state = self._state()
        fake_st = type("FakeConnectionState", (), {"session_state": state})()
        active = ket_noi_llm_dang_dung(fake_st)
        self.assertIsNotNone(active)
        self.assertEqual(active["model"], "gpt-test")  # type: ignore[index]

        payload = serialize_settings_page_view_model(
            build_settings_page_view_model(
                settings=self.settings,
                session_state=state,
                provider_catalog=NHA_CUNG_CAP_LLM,
                thresholds=self.thresholds,
                result=None,
                theme="light",
            )
        )
        rendered_thresholds = {item["key"]: item["value"] for item in payload["thresholds"]}
        self.assertEqual(rendered_thresholds, self.thresholds)
        self.assertEqual([item["provider"] for item in payload["providers"]], list(NHA_CUNG_CAP_LLM))
        active_provider = next(item for item in payload["providers"] if item["active"])
        self.assertEqual(active_provider["model"], "gpt-test")
        self.assertEqual(active_provider["model_count"], 2)

    def test_api_key_input_remains_native_masked_and_settings_render_is_presentation_only(self) -> None:
        self.assertIn('type="password"', inspect.getsource(trang_cai_dat))
        view_model = build_settings_page_view_model(
            settings=self.settings,
            session_state=self._state(),
            provider_catalog=NHA_CUNG_CAP_LLM,
            thresholds=self.thresholds,
            result=None,
            theme="system",
        )
        captured: dict[str, object] = {}

        def renderer(**kwargs: object) -> dict[str, object]:
            captured.update(kwargs)
            return {"event": None}

        with patch("credit_underwriting_colab.tao_phan_hoi_chat_ai") as inference:
            render_settings_page(FakeStreamlit(), view_model, renderer=renderer)
        inference.assert_not_called()
        serialized = json.dumps(captured["data"], ensure_ascii=False)
        self.assertNotIn(self.secret, serialized)
        self.assertNotIn("api_key", serialized.casefold())

        def invalid_renderer(**_kwargs: object) -> dict[str, object]:
            return {"event": VALID_NAVIGATION_EVENT}

        with self.assertRaisesRegex(UIContractError, "không được phát domain event"):
            render_settings_page(FakeStreamlit(), view_model, renderer=invalid_renderer)

    def test_one_send_one_request_rerun_zero_and_second_message_retains_context(self) -> None:
        st = FakeChatStreamlit(["Tin nhắn thứ nhất"])
        captured_requests: list[list[dict[str, str]]] = []

        def respond(messages: list[dict[str, str]], *_args: object) -> str:
            captured_requests.append([dict(message) for message in messages])
            return "Phản hồi thứ nhất" if len(captured_requests) == 1 else "Phản hồi thứ hai"

        with patch(
            "credit_underwriting_colab.tao_phan_hoi_chat_ai",
            side_effect=respond,
        ) as inference:
            hien_thi_chat_ai(st, self.connection)
            self.assertEqual(inference.call_count, 1)
            hien_thi_chat_ai(st, self.connection)
            self.assertEqual(inference.call_count, 1, "Rerun không được gửi lại prompt")
            st.prompts.append("Tin nhắn thứ hai")
            hien_thi_chat_ai(st, self.connection)
            self.assertEqual(inference.call_count, 2)

        first_history, second_history = captured_requests
        self.assertEqual(first_history, [{"role": "user", "content": "Tin nhắn thứ nhất"}])
        self.assertEqual(
            second_history,
            [
                {"role": "user", "content": "Tin nhắn thứ nhất"},
                {"role": "assistant", "content": "Phản hồi thứ nhất"},
                {"role": "user", "content": "Tin nhắn thứ hai"},
            ],
        )
        self.assertEqual(
            st.session_state["llm_chat_messages"][-1],
            {"role": "assistant", "content": "Phản hồi thứ hai"},
        )

    def test_render_history_empty_prompt_and_model_change_make_zero_requests(self) -> None:
        history = [
            {"role": "user", "content": "Lịch sử"},
            {"role": "assistant", "content": "Đã trả lời"},
        ]
        with patch("credit_underwriting_colab.tao_phan_hoi_chat_ai") as inference:
            history_st = FakeChatStreamlit([None], messages=history)
            hien_thi_chat_ai(history_st, self.connection)
            empty_st = FakeChatStreamlit(["   "])
            hien_thi_chat_ai(empty_st, self.connection)

            state = self._state()
            state["llm_connections"]["openai"]["model"] = "gpt-second"  # type: ignore[index]
            model_view = build_settings_page_view_model(
                settings=self.settings,
                session_state=state,
                provider_catalog=NHA_CUNG_CAP_LLM,
                thresholds=self.thresholds,
                result=None,
                theme="light",
            )
            serialize_settings_page_view_model(model_view)

        inference.assert_not_called()
        self.assertEqual(model_view.active_model, "gpt-second")
        self.assertEqual(history_st.session_state["llm_chat_messages"], history)

    def test_connection_and_chat_errors_are_generic_and_logs_redact_the_key(self) -> None:
        state = self._state()
        state["llm_connection_error"] = f"Provider rejected {self.secret}"
        payload = serialize_settings_page_view_model(
            build_settings_page_view_model(
                settings=self.settings,
                session_state=state,
                provider_catalog=NHA_CUNG_CAP_LLM,
                thresholds=self.thresholds,
                result=None,
                theme="light",
            )
        )
        self.assertEqual(payload["connection_state"], "error")
        self.assertNotIn(self.secret, json.dumps(payload, ensure_ascii=False))

        st = FakeChatStreamlit(["Câu hỏi lỗi"])
        with patch(
            "credit_underwriting_colab.tao_phan_hoi_chat_ai",
            side_effect=RuntimeError(f"Bearer {self.secret}"),
        ):
            hien_thi_chat_ai(st, self.connection)
        shown_error = st.error.call_args.args[0]
        self.assertEqual(shown_error, "Không thể nhận phản hồi từ model. Vui lòng kiểm tra kết nối hoặc API Key.")
        self.assertNotIn(self.secret, shown_error)

        with self.assertLogs("creditlens.chat", level="ERROR") as captured:
            _ghi_log_loi_chat_an_toan(
                RuntimeError(f"Bearer {self.secret} failed"),
                "openai",
                "gpt-test",
                self.secret,
            )
        self.assertNotIn(self.secret, "\n".join(captured.output))
        self.assertIn("[REDACTED]", "\n".join(captured.output))


class AppEntryPointTests(unittest.TestCase):
    @patch("app.chay_ung_dung_streamlit")
    @patch("app.chay_ung_dung_streamlit_v2")
    @patch("app.ui_v2_enabled", return_value=False)
    def test_flag_off_runs_legacy_exactly(self, _flag: Mock, v2: Mock, legacy: Mock) -> None:
        app.main()
        v2.assert_not_called()
        legacy.assert_called_once_with()

    @patch("app.chay_ung_dung_streamlit")
    @patch("app.chay_ung_dung_streamlit_v2")
    @patch("app.ui_v2_enabled", return_value=True)
    def test_flag_on_runs_v2_shell_only(self, _flag: Mock, v2: Mock, legacy: Mock) -> None:
        app.main()
        v2.assert_called_once_with()
        legacy.assert_not_called()

    @patch("app.show_v2_fallback_notice")
    @patch("app.chay_ung_dung_streamlit")
    @patch("app.chay_ung_dung_streamlit_v2", side_effect=RuntimeError("synthetic-build-failure"))
    @patch("app.ui_v2_enabled", return_value=True)
    def test_component_failure_falls_back_to_legacy(
        self,
        _flag: Mock,
        _v2: Mock,
        legacy: Mock,
        notice: Mock,
    ) -> None:
        app.main()
        notice.assert_called_once_with()
        legacy.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
