"""Cầu nối an toàn giữa Streamlit/Python và UI v2 React production.

Python tiếp tục là nguồn sự thật duy nhất. Module này chỉ chuyển một view model
đã lọc sang lớp trình bày và xác thực sự kiện miền tối thiểu gửi về từ React.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Any, Literal, Mapping, Protocol, TypeAlias


SCHEMA_VERSION = "1.0"
COMPONENT_VERSION = "0.5.0"
# Registry identity is retained for Streamlit session compatibility.
COMPONENT_NAME = "creditlens_v2_status_card"
SHELL_COMPONENT_KIND = "app_shell"
DEMO_COMPONENT_KIND = "demo_panel"
WORKFLOW_COMPONENT_KIND = "workflow_panel"
CORE_PAGE_COMPONENT_KIND = "core_business_page"
SUMMARY_PAGE_COMPONENT_KIND = "summary_page"
METHODOLOGY_PAGE_COMPONENT_KIND = "methodology_page"
EVALUATION_PAGE_COMPONENT_KIND = "evaluation_page"
SETTINGS_PAGE_COMPONENT_KIND = "settings_page"
UI_V2_FLAG = "UI_V2_ENABLED"

_DEFAULT_ASSET_DIR = Path(__file__).resolve().parent / "frontend" / "dist"
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_THEMES = frozenset({"system", "light", "dark"})
_STATUS_TONES = frozenset({"neutral", "info", "success", "warning", "danger"})
_PROHIBITED_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "auth",
        "credential",
        "credentials",
        "password",
        "secret",
        "token",
    }
)
_EVENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,96}$")

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


class UIContractError(ValueError):
    """Dữ liệu qua cầu nối không khớp hợp đồng an toàn."""


class V2ComponentUnavailable(RuntimeError):
    """Component v2 hoặc build artifact chưa sẵn sàng."""


class ComponentRenderer(Protocol):
    def __call__(self, **kwargs: Any) -> Any: ...


_RENDERER_CACHE: dict[tuple[int, str], ComponentRenderer] = {}


@dataclass(frozen=True, slots=True)
class V2NavigationItem:
    page: str
    label: str
    group: Literal["Hồ sơ", "Kiểm chứng", "Hệ thống"]
    ordinal: int


@dataclass(frozen=True, slots=True)
class V2WorkflowStep:
    key: str
    label: str
    description: str
    state: Literal["upcoming", "current", "complete", "warning", "error"]
    status_label: str


@dataclass(frozen=True, slots=True)
class V2ProcessCard:
    key: str
    label: str
    description: str
    state: Literal["upcoming", "current", "complete", "warning", "error"]


@dataclass(frozen=True, slots=True)
class V2CaseContext:
    case_id: str | None
    source: str | None
    status_label: str
    status_tone: Literal["neutral", "info", "success", "warning", "danger"]
    summary: str


@dataclass(frozen=True, slots=True)
class V2AppShellViewModel:
    active_page: str
    navigation: tuple[V2NavigationItem, ...]
    workflow: tuple[V2WorkflowStep, ...]
    process_cards: tuple[V2ProcessCard, ...]
    case_context: V2CaseContext
    logo_data_uri: str
    theme: Literal["system", "light", "dark"] = "system"
    overview: bool = True
    page_state: Literal["empty", "ready", "processing", "success", "warning", "error", "disabled"] = "empty"
    state_message: str = "Chưa có hồ sơ đang mở."


@dataclass(frozen=True, slots=True)
class V2DemoCaseItem:
    case_name: str
    case_code: str
    title: str
    description: str


@dataclass(frozen=True, slots=True)
class V2DemoPanelViewModel:
    cases: tuple[V2DemoCaseItem, ...]
    selected_case: str
    case_context: V2CaseContext
    theme: Literal["system", "light", "dark"] = "system"
    loading: bool = False
    error: str | None = None


@dataclass(frozen=True, slots=True)
class V2WorkflowPanelViewModel:
    workflow: tuple[V2WorkflowStep, ...]
    process_cards: tuple[V2ProcessCard, ...]
    theme: Literal["system", "light", "dark"] = "system"


@dataclass(frozen=True, slots=True)
class V2EvidenceReference:
    document: str
    field: str
    value: str
    page: int | None = None
    excerpt: str | None = None


@dataclass(frozen=True, slots=True)
class V2DocumentItem:
    name: str
    expected_type: str
    detected_type: str
    pages: int
    status: str
    confidence: float
    confidence_display: str
    confidence_label: str
    confidence_tone: Literal["neutral", "info", "success", "warning", "danger"]
    type_mismatch: bool


@dataclass(frozen=True, slots=True)
class V2ExtractedFieldItem:
    key: str
    label: str
    value_display: str
    raw_value: JsonScalar
    source: str
    source_role: Literal["declared", "observed", "calculated", "other"]
    page: int | None
    confidence: float
    confidence_display: str
    confidence_label: str
    confidence_tone: Literal["neutral", "info", "success", "warning", "danger"]
    status: str
    evidence: V2EvidenceReference | None = None


@dataclass(frozen=True, slots=True)
class V2ComparisonValue:
    role: Literal["declared", "observed", "calculated"]
    label: str
    value_display: str
    source: str


@dataclass(frozen=True, slots=True)
class V2CrossDocumentComparison:
    title: str
    values: tuple[V2ComparisonValue, ...]
    difference_display: str
    status: str
    status_tone: Literal["neutral", "info", "success", "warning", "danger"]


@dataclass(frozen=True, slots=True)
class V2MetricItem:
    key: str
    label: str
    value_display: str
    raw_value: JsonScalar
    reference: str
    status: str
    status_tone: Literal["neutral", "info", "success", "warning", "danger"]
    formula: str
    note: str
    source_role: Literal["calculated"] = "calculated"


@dataclass(frozen=True, slots=True)
class V2ThresholdReference:
    key: str
    label: str
    value: float
    value_display: str
    relation: Literal["above", "below"]


@dataclass(frozen=True, slots=True)
class V2RiskItem:
    code: str
    name: str
    severity: Literal["HIGH", "MEDIUM", "LOW", "INFO"]
    severity_label: str
    severity_tone: Literal["neutral", "info", "warning", "danger"]
    description: str
    difference: str | None
    evidence: tuple[V2EvidenceReference, ...]


@dataclass(frozen=True, slots=True)
class V2CorePageViewModel:
    page: Literal["extraction", "analysis", "risk"]
    title: str
    subtitle: str
    state: Literal["empty", "loading", "success", "partial", "error"]
    state_message: str
    documents: tuple[V2DocumentItem, ...] = ()
    fields: tuple[V2ExtractedFieldItem, ...] = ()
    comparisons: tuple[V2CrossDocumentComparison, ...] = ()
    metrics: tuple[V2MetricItem, ...] = ()
    thresholds: tuple[V2ThresholdReference, ...] = ()
    risks: tuple[V2RiskItem, ...] = ()
    case_status: str | None = None
    theme: Literal["system", "light", "dark"] = "system"


@dataclass(frozen=True, slots=True)
class V2FindingItem:
    category: Literal["finding", "missing", "verification"]
    title: str
    detail: str
    tone: Literal["neutral", "info", "success", "warning", "danger"]


@dataclass(frozen=True, slots=True)
class V2SummaryPageViewModel:
    state: Literal["empty", "success", "partial", "error"]
    state_message: str
    case_id: str | None
    applicant: str
    employer: str
    loan_amount: str
    loan_term: str
    loan_purpose: str
    review_status: str
    review_status_tone: Literal["neutral", "info", "success", "warning", "danger"]
    highest_alert: str
    highest_alert_tone: Literal["neutral", "info", "warning", "danger"]
    metrics: tuple[V2MetricItem, ...] = ()
    top_risks: tuple[V2RiskItem, ...] = ()
    total_risk_count: int = 0
    findings: tuple[V2FindingItem, ...] = ()
    evidence: tuple[V2EvidenceReference, ...] = ()
    document_count: int = 0
    extracted_field_count: int = 0
    ai_explanation: str | None = None
    theme: Literal["system", "light", "dark"] = "system"


@dataclass(frozen=True, slots=True)
class V2MethodologyLayer:
    key: str
    label: str
    description: str


@dataclass(frozen=True, slots=True)
class V2FormulaCard:
    key: str
    name: str
    formula: str
    meaning: str
    limitation: str


@dataclass(frozen=True, slots=True)
class V2CapabilityRow:
    document_type: str
    support_level: str
    limitation: str


@dataclass(frozen=True, slots=True)
class V2LimitationGroup:
    title: str
    items: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class V2MethodologyPageViewModel:
    layers: tuple[V2MethodologyLayer, ...]
    formulas: tuple[V2FormulaCard, ...]
    capabilities: tuple[V2CapabilityRow, ...]
    limitations: tuple[V2LimitationGroup, ...]
    self_test_definition: str
    evaluation_definition: str
    theme: Literal["system", "light", "dark"] = "system"


@dataclass(frozen=True, slots=True)
class V2LabelValue:
    label: str
    value: str


@dataclass(frozen=True, slots=True)
class V2ScorecardItem:
    key: str
    label: str
    raw_value: JsonScalar
    value_display: str


@dataclass(frozen=True, slots=True)
class V2FieldMetricRow:
    name: str
    correct: int
    total: int
    accuracy: str
    detail: str


@dataclass(frozen=True, slots=True)
class V2ClassMetricRow:
    name: str
    tp: int
    fp: int
    fn: int
    tn: int | None
    precision: str
    recall: str
    f1: str
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class V2ConfusionRow:
    actual: str
    predicted: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class V2GroundingRow:
    variant: str
    evidence_coverage: str
    unsupported_claim_rate: str
    factual_consistency: str


@dataclass(frozen=True, slots=True)
class V2BaselineRow:
    baseline: str
    variant: str
    values: tuple[V2LabelValue, ...]


@dataclass(frozen=True, slots=True)
class V2FailureCase:
    case_id: str
    scenario: str
    expected: str
    actual: str
    failure_type: str
    probable_cause: str
    mitigation: str
    status: str


@dataclass(frozen=True, slots=True)
class V2EvaluationPageViewModel:
    state: Literal["idle", "success", "error"]
    state_message: str
    run_id: str | None = None
    metadata: tuple[V2LabelValue, ...] = ()
    dataset: tuple[V2LabelValue, ...] = ()
    scorecards: tuple[V2ScorecardItem, ...] = ()
    field_metrics: tuple[V2FieldMetricRow, ...] = ()
    risk_metrics: tuple[V2ClassMetricRow, ...] = ()
    status_metrics: tuple[V2ClassMetricRow, ...] = ()
    confusion_labels: tuple[str, ...] = ()
    confusion_rows: tuple[V2ConfusionRow, ...] = ()
    grounding: tuple[V2GroundingRow, ...] = ()
    baselines: tuple[V2BaselineRow, ...] = ()
    processing: tuple[V2LabelValue, ...] = ()
    failure_cases: tuple[V2FailureCase, ...] = ()
    limitations: tuple[str, ...] = ()
    llm_api_calls: int | None = None
    theme: Literal["system", "light", "dark"] = "system"


@dataclass(frozen=True, slots=True)
class V2ProviderStatus:
    provider: str
    label: str
    description: str
    connected: bool
    active: bool
    model: str | None
    model_count: int
    status_label: str
    status_tone: Literal["neutral", "info", "success", "warning", "danger"]


@dataclass(frozen=True, slots=True)
class V2SessionThreshold:
    key: str
    label: str
    value: float
    value_display: str


@dataclass(frozen=True, slots=True)
class V2SettingsPageViewModel:
    connection_state: Literal["connected", "not_configured", "error"]
    connection_status_label: str
    active_provider_label: str | None
    active_model: str | None
    providers: tuple[V2ProviderStatus, ...]
    thresholds: tuple[V2SessionThreshold, ...]
    chat_state: Literal["ready", "disabled", "error"]
    chat_message_count: int
    current_case: str | None
    has_result: bool
    evaluation_ready: bool
    error_message: str | None = None
    theme: Literal["system", "light", "dark"] = "system"


@dataclass(frozen=True, slots=True)
class V2NavigationEvent:
    event_id: str
    page: str
    action: Literal["select"] = "select"
    type: Literal["navigation.select"] = "navigation.select"
    component: Literal["app_shell"] = SHELL_COMPONENT_KIND
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    component_version: Literal["0.5.0"] = COMPONENT_VERSION


@dataclass(frozen=True, slots=True)
class V2DemoEvent:
    event_id: str
    case_name: str
    action: Literal["select", "open"]
    type: Literal["demo.select", "demo.open"]
    component: Literal["demo_panel"] = DEMO_COMPONENT_KIND
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    component_version: Literal["0.5.0"] = COMPONENT_VERSION


@dataclass(frozen=True, slots=True)
class V2EvaluationEvent:
    event_id: str
    action: Literal["run"] = "run"
    type: Literal["evaluation.run"] = "evaluation.run"
    component: Literal["evaluation_page"] = EVALUATION_PAGE_COMPONENT_KIND
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    component_version: Literal["0.5.0"] = COMPONENT_VERSION


V2UIEvent: TypeAlias = V2NavigationEvent | V2DemoEvent | V2EvaluationEvent


def ui_v2_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """Cờ opt-in nghiêm ngặt; mọi giá trị lạ đều được xem là tắt."""

    source = os.environ if environ is None else environ
    return str(source.get(UI_V2_FLAG, "")).strip().casefold() in _TRUE_VALUES


def _normalise_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.casefold()).strip("_")


def _assert_no_prohibited_keys(value: Any, path: str = "data") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise UIContractError(f"{path} chỉ chấp nhận khóa dạng chuỗi.")
            if _normalise_key(key) in _PROHIBITED_KEYS:
                raise UIContractError(f"{path} chứa trường bị cấm.")
            _assert_no_prohibited_keys(nested, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _assert_no_prohibited_keys(nested, f"{path}[{index}]")


def _clean_text(value: str, *, field: str, maximum: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise UIContractError(f"{field} phải là chuỗi.")
    cleaned = value.strip()
    if not allow_empty and not cleaned:
        raise UIContractError(f"{field} không được để trống.")
    if len(cleaned) > maximum:
        raise UIContractError(f"{field} vượt quá độ dài cho phép.")
    return cleaned


def _json_object(payload: dict[str, JsonValue], *, label: str) -> dict[str, JsonValue]:
    _assert_no_prohibited_keys(payload)
    try:
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        decoded = json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise UIContractError(f"{label} không thể tuần tự hóa an toàn.") from exc
    if not isinstance(decoded, dict):
        raise UIContractError(f"{label} phải là một JSON object.")
    return decoded


def _serialize_case_context(context: V2CaseContext) -> dict[str, JsonValue]:
    if context.status_tone not in _STATUS_TONES:
        raise UIContractError("Case status tone không hợp lệ.")
    return {
        "case_id": (
            _clean_text(context.case_id, field="case_id", maximum=80)
            if context.case_id is not None
            else None
        ),
        "source": (
            _clean_text(context.source, field="source", maximum=60)
            if context.source is not None
            else None
        ),
        "status_label": _clean_text(context.status_label, field="status_label", maximum=100),
        "status_tone": context.status_tone,
        "summary": _clean_text(context.summary, field="summary", maximum=180),
    }


def serialize_shell_view_model(view_model: V2AppShellViewModel) -> dict[str, JsonValue]:
    """Serialize App Shell từ allowlist; không gửi toàn bộ settings/session state."""

    if view_model.theme not in _THEMES:
        raise UIContractError("theme không hợp lệ.")
    if view_model.page_state not in {"empty", "ready", "processing", "success", "warning", "error", "disabled"}:
        raise UIContractError("page_state không hợp lệ.")
    if not view_model.navigation or len(view_model.navigation) > 8:
        raise UIContractError("Navigation phải có từ 1 đến 8 mục.")
    if len(view_model.workflow) != 4 or len(view_model.process_cards) != 4:
        raise UIContractError("Workflow và process cards phải có đúng 4 bước đã duyệt.")
    if not view_model.logo_data_uri.startswith("data:image/png;base64,") or len(view_model.logo_data_uri) > 400_000:
        raise UIContractError("Logo data URI không hợp lệ.")

    navigation: list[JsonValue] = []
    for item in view_model.navigation:
        if item.group not in {"Hồ sơ", "Kiểm chứng", "Hệ thống"} or not 1 <= item.ordinal <= 8:
            raise UIContractError("Navigation item không hợp lệ.")
        navigation.append(
            {
                "page": _clean_text(item.page, field="navigation.page", maximum=100),
                "label": _clean_text(item.label, field="navigation.label", maximum=80),
                "group": item.group,
                "ordinal": item.ordinal,
            }
        )
    pages = {str(item["page"]) for item in navigation if isinstance(item, dict)}
    if view_model.active_page not in pages:
        raise UIContractError("active_page không có trong navigation.")

    workflow: list[JsonValue] = []
    for step in view_model.workflow:
        if step.state not in {"upcoming", "current", "complete", "warning", "error"}:
            raise UIContractError("Workflow state không hợp lệ.")
        workflow.append(
            {
                "key": _clean_text(step.key, field="workflow.key", maximum=40),
                "label": _clean_text(step.label, field="workflow.label", maximum=80),
                "description": _clean_text(step.description, field="workflow.description", maximum=180),
                "state": step.state,
                "status_label": _clean_text(step.status_label, field="workflow.status_label", maximum=60),
            }
        )

    cards: list[JsonValue] = []
    for card in view_model.process_cards:
        if card.state not in {"upcoming", "current", "complete", "warning", "error"}:
            raise UIContractError("Process-card state không hợp lệ.")
        cards.append(
            {
                "key": _clean_text(card.key, field="process_card.key", maximum=40),
                "label": _clean_text(card.label, field="process_card.label", maximum=80),
                "description": _clean_text(card.description, field="process_card.description", maximum=180),
                "state": card.state,
            }
        )

    payload: dict[str, JsonValue] = {
        "schema_version": SCHEMA_VERSION,
        "component_version": COMPONENT_VERSION,
        "component": SHELL_COMPONENT_KIND,
        "theme": view_model.theme,
        "active_page": view_model.active_page,
        "navigation": navigation,
        "workflow": workflow,
        "process_cards": cards,
        "case_context": _serialize_case_context(view_model.case_context),
        "logo_data_uri": view_model.logo_data_uri,
        "overview": bool(view_model.overview),
        "page_state": view_model.page_state,
        "state_message": _clean_text(view_model.state_message, field="state_message", maximum=300),
    }
    return _json_object(payload, label="App Shell view model")


def serialize_demo_panel_view_model(view_model: V2DemoPanelViewModel) -> dict[str, JsonValue]:
    """Serialize danh sách demo an toàn; không chứa Gold Case ground truth."""

    if view_model.theme not in _THEMES:
        raise UIContractError("theme không hợp lệ.")
    if len(view_model.cases) != 10:
        raise UIContractError("Demo panel phải nhận đúng 10 case hiện hành.")
    cases: list[JsonValue] = []
    allowed_cases: set[str] = set()
    for item in view_model.cases:
        case_name = _clean_text(item.case_name, field="case_name", maximum=120)
        allowed_cases.add(case_name)
        cases.append(
            {
                "case_name": case_name,
                "case_code": _clean_text(item.case_code, field="case_code", maximum=20),
                "title": _clean_text(item.title, field="case_title", maximum=100),
                "description": _clean_text(item.description, field="case_description", maximum=180),
            }
        )
    if view_model.selected_case not in allowed_cases:
        raise UIContractError("selected_case không có trong danh sách demo.")
    payload: dict[str, JsonValue] = {
        "schema_version": SCHEMA_VERSION,
        "component_version": COMPONENT_VERSION,
        "component": DEMO_COMPONENT_KIND,
        "theme": view_model.theme,
        "cases": cases,
        "selected_case": view_model.selected_case,
        "case_context": _serialize_case_context(view_model.case_context),
        "loading": bool(view_model.loading),
        "error": (
            _clean_text(view_model.error, field="demo_error", maximum=300)
            if view_model.error is not None
            else None
        ),
    }
    return _json_object(payload, label="Demo Panel view model")


def serialize_workflow_panel_view_model(view_model: V2WorkflowPanelViewModel) -> dict[str, JsonValue]:
    """Serialize bản workflow đặt sau intake trên mobile."""

    if view_model.theme not in _THEMES:
        raise UIContractError("theme không hợp lệ.")
    if len(view_model.workflow) != 4 or len(view_model.process_cards) != 4:
        raise UIContractError("Workflow panel phải có đúng 4 bước.")
    workflow: list[JsonValue] = []
    cards: list[JsonValue] = []
    for step in view_model.workflow:
        if step.state not in {"upcoming", "current", "complete", "warning", "error"}:
            raise UIContractError("Workflow state không hợp lệ.")
        workflow.append(
            {
                "key": _clean_text(step.key, field="workflow.key", maximum=40),
                "label": _clean_text(step.label, field="workflow.label", maximum=80),
                "description": _clean_text(step.description, field="workflow.description", maximum=180),
                "state": step.state,
                "status_label": _clean_text(step.status_label, field="workflow.status_label", maximum=60),
            }
        )
    for card in view_model.process_cards:
        if card.state not in {"upcoming", "current", "complete", "warning", "error"}:
            raise UIContractError("Process-card state không hợp lệ.")
        cards.append(
            {
                "key": _clean_text(card.key, field="process_card.key", maximum=40),
                "label": _clean_text(card.label, field="process_card.label", maximum=80),
                "description": _clean_text(card.description, field="process_card.description", maximum=180),
                "state": card.state,
            }
        )
    return _json_object(
        {
            "schema_version": SCHEMA_VERSION,
            "component_version": COMPONENT_VERSION,
            "component": WORKFLOW_COMPONENT_KIND,
            "theme": view_model.theme,
            "workflow": workflow,
            "process_cards": cards,
        },
        label="Workflow Panel view model",
    )


def _serialize_evidence(evidence: V2EvidenceReference) -> dict[str, JsonValue]:
    if evidence.page is not None and (not isinstance(evidence.page, int) or evidence.page < 1):
        raise UIContractError("Trang bằng chứng không hợp lệ.")
    return {
        "document": _clean_text(evidence.document, field="evidence.document", maximum=180),
        "field": _clean_text(evidence.field, field="evidence.field", maximum=120),
        "value": _clean_text(evidence.value, field="evidence.value", maximum=300),
        "page": evidence.page,
        "excerpt": (
            _clean_text(evidence.excerpt, field="evidence.excerpt", maximum=1_000)
            if evidence.excerpt is not None
            else None
        ),
    }


def _tone(value: str, *, field: str, allowed: set[str] | None = None) -> str:
    choices = allowed or set(_STATUS_TONES)
    if value not in choices:
        raise UIContractError(f"{field} không hợp lệ.")
    return value


def serialize_core_page_view_model(view_model: V2CorePageViewModel) -> dict[str, JsonValue]:
    """Serialize ba trang Cụm 4; mọi giá trị nghiệp vụ đã do Python cung cấp."""

    if view_model.theme not in _THEMES:
        raise UIContractError("theme không hợp lệ.")
    if view_model.page not in {"extraction", "analysis", "risk"}:
        raise UIContractError("Core page không hợp lệ.")
    if view_model.state not in {"empty", "loading", "success", "partial", "error"}:
        raise UIContractError("Core page state không hợp lệ.")
    if len(view_model.documents) > 20 or len(view_model.fields) > 100:
        raise UIContractError("Dữ liệu trang trích xuất vượt giới hạn trình bày.")
    if len(view_model.comparisons) > 8 or len(view_model.metrics) > 12:
        raise UIContractError("Dữ liệu trang phân tích vượt giới hạn trình bày.")
    if len(view_model.thresholds) > 12 or len(view_model.risks) > 100:
        raise UIContractError("Dữ liệu tham chiếu hoặc cảnh báo vượt giới hạn trình bày.")

    documents: list[JsonValue] = []
    for item in view_model.documents:
        if not 0.0 <= item.confidence <= 1.0 or item.pages < 0:
            raise UIContractError("Document confidence hoặc số trang không hợp lệ.")
        documents.append(
            {
                "name": _clean_text(item.name, field="document.name", maximum=180),
                "expected_type": _clean_text(item.expected_type, field="document.expected_type", maximum=100),
                "detected_type": _clean_text(item.detected_type, field="document.detected_type", maximum=100),
                "pages": item.pages,
                "status": _clean_text(item.status, field="document.status", maximum=80),
                "confidence": item.confidence,
                "confidence_display": _clean_text(
                    item.confidence_display, field="document.confidence_display", maximum=40
                ),
                "confidence_label": _clean_text(
                    item.confidence_label, field="document.confidence_label", maximum=80
                ),
                "confidence_tone": _tone(item.confidence_tone, field="document.confidence_tone"),
                "type_mismatch": item.type_mismatch,
            }
        )

    fields: list[JsonValue] = []
    for item in view_model.fields:
        if item.source_role not in {"declared", "observed", "calculated", "other"}:
            raise UIContractError("Field source role không hợp lệ.")
        if not 0.0 <= item.confidence <= 1.0:
            raise UIContractError("Field confidence không hợp lệ.")
        if item.page is not None and (not isinstance(item.page, int) or item.page < 1):
            raise UIContractError("Field page không hợp lệ.")
        fields.append(
            {
                "key": _clean_text(item.key, field="field.key", maximum=80),
                "label": _clean_text(item.label, field="field.label", maximum=160),
                "value_display": _clean_text(item.value_display, field="field.value_display", maximum=300),
                "raw_value": item.raw_value,
                "source": _clean_text(item.source, field="field.source", maximum=180),
                "source_role": item.source_role,
                "page": item.page,
                "confidence": item.confidence,
                "confidence_display": _clean_text(
                    item.confidence_display, field="field.confidence_display", maximum=40
                ),
                "confidence_label": _clean_text(
                    item.confidence_label, field="field.confidence_label", maximum=80
                ),
                "confidence_tone": _tone(item.confidence_tone, field="field.confidence_tone"),
                "status": _clean_text(item.status, field="field.status", maximum=100),
                "evidence": _serialize_evidence(item.evidence) if item.evidence is not None else None,
            }
        )

    comparisons: list[JsonValue] = []
    for comparison in view_model.comparisons:
        if not 2 <= len(comparison.values) <= 6:
            raise UIContractError("Cross-document comparison cần từ 2 đến 6 giá trị.")
        values: list[JsonValue] = []
        for value in comparison.values:
            if value.role not in {"declared", "observed", "calculated"}:
                raise UIContractError("Comparison role không hợp lệ.")
            values.append(
                {
                    "role": value.role,
                    "label": _clean_text(value.label, field="comparison.label", maximum=120),
                    "value_display": _clean_text(
                        value.value_display, field="comparison.value_display", maximum=120
                    ),
                    "source": _clean_text(value.source, field="comparison.source", maximum=180),
                }
            )
        comparisons.append(
            {
                "title": _clean_text(comparison.title, field="comparison.title", maximum=140),
                "values": values,
                "difference_display": _clean_text(
                    comparison.difference_display, field="comparison.difference_display", maximum=100
                ),
                "status": _clean_text(comparison.status, field="comparison.status", maximum=100),
                "status_tone": _tone(comparison.status_tone, field="comparison.status_tone"),
            }
        )

    metrics: list[JsonValue] = []
    for item in view_model.metrics:
        metrics.append(
            {
                "key": _clean_text(item.key, field="metric.key", maximum=80),
                "label": _clean_text(item.label, field="metric.label", maximum=140),
                "value_display": _clean_text(item.value_display, field="metric.value_display", maximum=120),
                "raw_value": item.raw_value,
                "reference": _clean_text(item.reference, field="metric.reference", maximum=220),
                "status": _clean_text(item.status, field="metric.status", maximum=100),
                "status_tone": _tone(item.status_tone, field="metric.status_tone"),
                "formula": _clean_text(item.formula, field="metric.formula", maximum=300),
                "note": _clean_text(item.note, field="metric.note", maximum=400),
                "source_role": item.source_role,
            }
        )

    thresholds: list[JsonValue] = []
    for item in view_model.thresholds:
        if item.relation not in {"above", "below"}:
            raise UIContractError("Threshold relation không hợp lệ.")
        thresholds.append(
            {
                "key": _clean_text(item.key, field="threshold.key", maximum=80),
                "label": _clean_text(item.label, field="threshold.label", maximum=140),
                "value": item.value,
                "value_display": _clean_text(
                    item.value_display, field="threshold.value_display", maximum=80
                ),
                "relation": item.relation,
            }
        )

    risks: list[JsonValue] = []
    for risk in view_model.risks:
        if risk.severity not in {"HIGH", "MEDIUM", "LOW", "INFO"}:
            raise UIContractError("Risk severity không hợp lệ.")
        risks.append(
            {
                "code": _clean_text(risk.code, field="risk.code", maximum=40),
                "name": _clean_text(risk.name, field="risk.name", maximum=160),
                "severity": risk.severity,
                "severity_label": _clean_text(
                    risk.severity_label, field="risk.severity_label", maximum=80
                ),
                "severity_tone": _tone(
                    risk.severity_tone,
                    field="risk.severity_tone",
                    allowed={"neutral", "info", "warning", "danger"},
                ),
                "description": _clean_text(risk.description, field="risk.description", maximum=1_000),
                "difference": (
                    _clean_text(risk.difference, field="risk.difference", maximum=120)
                    if risk.difference is not None
                    else None
                ),
                "evidence": [_serialize_evidence(item) for item in risk.evidence],
            }
        )

    payload: dict[str, JsonValue] = {
        "schema_version": SCHEMA_VERSION,
        "component_version": COMPONENT_VERSION,
        "component": CORE_PAGE_COMPONENT_KIND,
        "theme": view_model.theme,
        "page": view_model.page,
        "title": _clean_text(view_model.title, field="core_page.title", maximum=160),
        "subtitle": _clean_text(view_model.subtitle, field="core_page.subtitle", maximum=300),
        "state": view_model.state,
        "state_message": _clean_text(view_model.state_message, field="core_page.state_message", maximum=300),
        "documents": documents,
        "fields": fields,
        "comparisons": comparisons,
        "metrics": metrics,
        "thresholds": thresholds,
        "risks": risks,
        "case_status": (
            _clean_text(view_model.case_status, field="core_page.case_status", maximum=120)
            if view_model.case_status is not None
            else None
        ),
    }
    return _json_object(payload, label="Core business page view model")


def _serialize_metric_for_support(item: V2MetricItem) -> dict[str, JsonValue]:
    return {
        "key": _clean_text(item.key, field="metric.key", maximum=80),
        "label": _clean_text(item.label, field="metric.label", maximum=140),
        "value_display": _clean_text(item.value_display, field="metric.value_display", maximum=120),
        "raw_value": item.raw_value,
        "reference": _clean_text(item.reference, field="metric.reference", maximum=220),
        "status": _clean_text(item.status, field="metric.status", maximum=100),
        "status_tone": _tone(item.status_tone, field="metric.status_tone"),
        "formula": _clean_text(item.formula, field="metric.formula", maximum=300),
        "note": _clean_text(item.note, field="metric.note", maximum=400),
        "source_role": "calculated",
    }


def _serialize_risk_for_support(item: V2RiskItem) -> dict[str, JsonValue]:
    if item.severity not in {"HIGH", "MEDIUM", "LOW", "INFO"}:
        raise UIContractError("Risk severity không hợp lệ.")
    return {
        "code": _clean_text(item.code, field="risk.code", maximum=40),
        "name": _clean_text(item.name, field="risk.name", maximum=160),
        "severity": item.severity,
        "severity_label": _clean_text(item.severity_label, field="risk.severity_label", maximum=80),
        "severity_tone": _tone(
            item.severity_tone,
            field="risk.severity_tone",
            allowed={"neutral", "info", "warning", "danger"},
        ),
        "description": _clean_text(item.description, field="risk.description", maximum=1_000),
        "difference": (
            _clean_text(item.difference, field="risk.difference", maximum=120)
            if item.difference is not None
            else None
        ),
        "evidence": [_serialize_evidence(evidence) for evidence in item.evidence],
    }


def serialize_summary_page_view_model(view_model: V2SummaryPageViewModel) -> dict[str, JsonValue]:
    """Serialize decision-support content; no workflow or underwriting decision is created here."""

    if view_model.theme not in _THEMES:
        raise UIContractError("theme không hợp lệ.")
    if view_model.state not in {"empty", "success", "partial", "error"}:
        raise UIContractError("Summary state không hợp lệ.")
    if view_model.total_risk_count < 0 or view_model.document_count < 0 or view_model.extracted_field_count < 0:
        raise UIContractError("Summary counts không hợp lệ.")
    if len(view_model.metrics) > 12 or len(view_model.top_risks) > 10:
        raise UIContractError("Summary business items vượt giới hạn trình bày.")
    if len(view_model.findings) > 60 or len(view_model.evidence) > 300:
        raise UIContractError("Summary findings hoặc evidence vượt giới hạn trình bày.")
    findings: list[JsonValue] = []
    for item in view_model.findings:
        if item.category not in {"finding", "missing", "verification"}:
            raise UIContractError("Finding category không hợp lệ.")
        findings.append(
            {
                "category": item.category,
                "title": _clean_text(item.title, field="finding.title", maximum=160),
                "detail": _clean_text(item.detail, field="finding.detail", maximum=1_000),
                "tone": _tone(item.tone, field="finding.tone"),
            }
        )
    payload: dict[str, JsonValue] = {
        "schema_version": SCHEMA_VERSION,
        "component_version": COMPONENT_VERSION,
        "component": SUMMARY_PAGE_COMPONENT_KIND,
        "theme": view_model.theme,
        "state": view_model.state,
        "state_message": _clean_text(view_model.state_message, field="summary.state_message", maximum=300),
        "case_id": (
            _clean_text(view_model.case_id, field="summary.case_id", maximum=80)
            if view_model.case_id is not None
            else None
        ),
        "applicant": _clean_text(view_model.applicant, field="summary.applicant", maximum=180),
        "employer": _clean_text(view_model.employer, field="summary.employer", maximum=180),
        "loan_amount": _clean_text(view_model.loan_amount, field="summary.loan_amount", maximum=120),
        "loan_term": _clean_text(view_model.loan_term, field="summary.loan_term", maximum=120),
        "loan_purpose": _clean_text(view_model.loan_purpose, field="summary.loan_purpose", maximum=300),
        "review_status": _clean_text(view_model.review_status, field="summary.review_status", maximum=120),
        "review_status_tone": _tone(view_model.review_status_tone, field="summary.review_status_tone"),
        "highest_alert": _clean_text(view_model.highest_alert, field="summary.highest_alert", maximum=100),
        "highest_alert_tone": _tone(
            view_model.highest_alert_tone,
            field="summary.highest_alert_tone",
            allowed={"neutral", "info", "warning", "danger"},
        ),
        "metrics": [_serialize_metric_for_support(item) for item in view_model.metrics],
        "top_risks": [_serialize_risk_for_support(item) for item in view_model.top_risks],
        "total_risk_count": view_model.total_risk_count,
        "findings": findings,
        "evidence": [_serialize_evidence(item) for item in view_model.evidence],
        "document_count": view_model.document_count,
        "extracted_field_count": view_model.extracted_field_count,
        "ai_explanation": (
            _clean_text(view_model.ai_explanation, field="summary.ai_explanation", maximum=20_000)
            if view_model.ai_explanation is not None
            else None
        ),
    }
    return _json_object(payload, label="Summary page view model")


def serialize_methodology_page_view_model(view_model: V2MethodologyPageViewModel) -> dict[str, JsonValue]:
    if view_model.theme not in _THEMES:
        raise UIContractError("theme không hợp lệ.")
    if len(view_model.layers) != 3 or len(view_model.formulas) != 6 or len(view_model.capabilities) != 5:
        raise UIContractError("Methodology content không đúng cấu trúc hiện hành.")
    if not 1 <= len(view_model.limitations) <= 8:
        raise UIContractError("Methodology limitations không hợp lệ.")
    layers: list[JsonValue] = [
        {
            "key": _clean_text(item.key, field="methodology.layer.key", maximum=40),
            "label": _clean_text(item.label, field="methodology.layer.label", maximum=120),
            "description": _clean_text(item.description, field="methodology.layer.description", maximum=1_000),
        }
        for item in view_model.layers
    ]
    formulas: list[JsonValue] = [
        {
            "key": _clean_text(item.key, field="formula.key", maximum=60),
            "name": _clean_text(item.name, field="formula.name", maximum=140),
            "formula": _clean_text(item.formula, field="formula.formula", maximum=400),
            "meaning": _clean_text(item.meaning, field="formula.meaning", maximum=800),
            "limitation": _clean_text(item.limitation, field="formula.limitation", maximum=800),
        }
        for item in view_model.formulas
    ]
    capabilities: list[JsonValue] = [
        {
            "document_type": _clean_text(item.document_type, field="capability.document_type", maximum=120),
            "support_level": _clean_text(item.support_level, field="capability.support_level", maximum=80),
            "limitation": _clean_text(item.limitation, field="capability.limitation", maximum=500),
        }
        for item in view_model.capabilities
    ]
    limitations: list[JsonValue] = []
    for group in view_model.limitations:
        if not 1 <= len(group.items) <= 12:
            raise UIContractError("Limitation group không hợp lệ.")
        limitations.append(
            {
                "title": _clean_text(group.title, field="limitation.title", maximum=140),
                "items": [
                    _clean_text(item, field="limitation.item", maximum=800)
                    for item in group.items
                ],
            }
        )
    return _json_object(
        {
            "schema_version": SCHEMA_VERSION,
            "component_version": COMPONENT_VERSION,
            "component": METHODOLOGY_PAGE_COMPONENT_KIND,
            "theme": view_model.theme,
            "layers": layers,
            "formulas": formulas,
            "capabilities": capabilities,
            "limitations": limitations,
            "self_test_definition": _clean_text(
                view_model.self_test_definition,
                field="methodology.self_test_definition",
                maximum=800,
            ),
            "evaluation_definition": _clean_text(
                view_model.evaluation_definition,
                field="methodology.evaluation_definition",
                maximum=800,
            ),
        },
        label="Methodology page view model",
    )


def _serialize_label_values(items: tuple[V2LabelValue, ...], *, field: str) -> list[JsonValue]:
    return [
        {
            "label": _clean_text(item.label, field=f"{field}.label", maximum=160),
            "value": _clean_text(item.value, field=f"{field}.value", maximum=500),
        }
        for item in items
    ]


def _serialize_class_metrics(items: tuple[V2ClassMetricRow, ...], *, field: str) -> list[JsonValue]:
    rows: list[JsonValue] = []
    for item in items:
        if min(item.tp, item.fp, item.fn) < 0 or (item.tn is not None and item.tn < 0):
            raise UIContractError(f"{field} counts không hợp lệ.")
        rows.append(
            {
                "name": _clean_text(item.name, field=f"{field}.name", maximum=180),
                "tp": item.tp,
                "fp": item.fp,
                "fn": item.fn,
                "tn": item.tn,
                "precision": _clean_text(item.precision, field=f"{field}.precision", maximum=40),
                "recall": _clean_text(item.recall, field=f"{field}.recall", maximum=40),
                "f1": _clean_text(item.f1, field=f"{field}.f1", maximum=40),
                "detail": (
                    _clean_text(item.detail, field=f"{field}.detail", maximum=300)
                    if item.detail is not None
                    else None
                ),
            }
        )
    return rows


def serialize_evaluation_page_view_model(view_model: V2EvaluationPageViewModel) -> dict[str, JsonValue]:
    """Serialize saved deterministic Evaluation results; this function never runs the evaluator."""

    if view_model.theme not in _THEMES:
        raise UIContractError("theme không hợp lệ.")
    if view_model.state not in {"idle", "success", "error"}:
        raise UIContractError("Evaluation state không hợp lệ.")
    if len(view_model.scorecards) > 16 or len(view_model.failure_cases) > 100:
        raise UIContractError("Evaluation presentation exceeds limits.")
    if view_model.llm_api_calls is not None and view_model.llm_api_calls < 0:
        raise UIContractError("Evaluation LLM call count không hợp lệ.")
    scorecards: list[JsonValue] = [
        {
            "key": _clean_text(item.key, field="scorecard.key", maximum=80),
            "label": _clean_text(item.label, field="scorecard.label", maximum=160),
            "raw_value": item.raw_value,
            "value_display": _clean_text(item.value_display, field="scorecard.value_display", maximum=80),
        }
        for item in view_model.scorecards
    ]
    field_metrics: list[JsonValue] = []
    for item in view_model.field_metrics:
        if item.correct < 0 or item.total < 0 or item.correct > item.total:
            raise UIContractError("Field metric counts không hợp lệ.")
        field_metrics.append(
            {
                "name": _clean_text(item.name, field="field_metric.name", maximum=180),
                "correct": item.correct,
                "total": item.total,
                "accuracy": _clean_text(item.accuracy, field="field_metric.accuracy", maximum=40),
                "detail": _clean_text(item.detail, field="field_metric.detail", maximum=200),
            }
        )
    if len(view_model.confusion_labels) not in {0, 3}:
        raise UIContractError("Confusion matrix labels không hợp lệ.")
    confusion_rows: list[JsonValue] = []
    for row in view_model.confusion_rows:
        if len(row.predicted) != len(view_model.confusion_labels) or any(value < 0 for value in row.predicted):
            raise UIContractError("Confusion matrix row không hợp lệ.")
        confusion_rows.append(
            {
                "actual": _clean_text(row.actual, field="confusion.actual", maximum=120),
                "predicted": list(row.predicted),
            }
        )
    grounding: list[JsonValue] = [
        {
            "variant": _clean_text(item.variant, field="grounding.variant", maximum=160),
            "evidence_coverage": _clean_text(item.evidence_coverage, field="grounding.coverage", maximum=40),
            "unsupported_claim_rate": _clean_text(
                item.unsupported_claim_rate,
                field="grounding.unsupported",
                maximum=40,
            ),
            "factual_consistency": _clean_text(
                item.factual_consistency,
                field="grounding.consistency",
                maximum=40,
            ),
        }
        for item in view_model.grounding
    ]
    baselines: list[JsonValue] = [
        {
            "baseline": _clean_text(item.baseline, field="baseline.name", maximum=220),
            "variant": _clean_text(item.variant, field="baseline.variant", maximum=180),
            "values": _serialize_label_values(item.values, field="baseline.values"),
        }
        for item in view_model.baselines
    ]
    failures: list[JsonValue] = [
        {
            "case_id": _clean_text(item.case_id, field="failure.case_id", maximum=80),
            "scenario": _clean_text(item.scenario, field="failure.scenario", maximum=800),
            "expected": _clean_text(item.expected, field="failure.expected", maximum=1_500),
            "actual": _clean_text(item.actual, field="failure.actual", maximum=2_000),
            "failure_type": _clean_text(item.failure_type, field="failure.type", maximum=160),
            "probable_cause": _clean_text(item.probable_cause, field="failure.cause", maximum=1_000),
            "mitigation": _clean_text(item.mitigation, field="failure.mitigation", maximum=1_000),
            "status": _clean_text(item.status, field="failure.status", maximum=100),
        }
        for item in view_model.failure_cases
    ]
    return _json_object(
        {
            "schema_version": SCHEMA_VERSION,
            "component_version": COMPONENT_VERSION,
            "component": EVALUATION_PAGE_COMPONENT_KIND,
            "theme": view_model.theme,
            "state": view_model.state,
            "state_message": _clean_text(
                view_model.state_message,
                field="evaluation.state_message",
                maximum=500,
            ),
            "run_id": (
                _clean_text(view_model.run_id, field="evaluation.run_id", maximum=120)
                if view_model.run_id is not None
                else None
            ),
            "metadata": _serialize_label_values(view_model.metadata, field="evaluation.metadata"),
            "dataset": _serialize_label_values(view_model.dataset, field="evaluation.dataset"),
            "scorecards": scorecards,
            "field_metrics": field_metrics,
            "risk_metrics": _serialize_class_metrics(view_model.risk_metrics, field="risk_metric"),
            "status_metrics": _serialize_class_metrics(view_model.status_metrics, field="status_metric"),
            "confusion_labels": [
                _clean_text(item, field="confusion.label", maximum=120)
                for item in view_model.confusion_labels
            ],
            "confusion_rows": confusion_rows,
            "grounding": grounding,
            "baselines": baselines,
            "processing": _serialize_label_values(view_model.processing, field="evaluation.processing"),
            "failure_cases": failures,
            "limitations": [
                _clean_text(item, field="evaluation.limitation", maximum=1_000)
                for item in view_model.limitations
            ],
            "llm_api_calls": view_model.llm_api_calls,
        },
        label="Evaluation page view model",
    )


def serialize_settings_page_view_model(view_model: V2SettingsPageViewModel) -> dict[str, JsonValue]:
    """Serialize only safe Settings metadata; credentials and chat content never cross the bridge."""

    if view_model.theme not in _THEMES:
        raise UIContractError("Theme của Settings không hợp lệ.")
    if view_model.connection_state not in {"connected", "not_configured", "error"}:
        raise UIContractError("Trạng thái kết nối không hợp lệ.")
    if view_model.chat_state not in {"ready", "disabled", "error"}:
        raise UIContractError("Trạng thái chat không hợp lệ.")
    if view_model.chat_message_count < 0:
        raise UIContractError("Số tin nhắn chat không hợp lệ.")
    if not 1 <= len(view_model.providers) <= 8:
        raise UIContractError("Danh sách provider không hợp lệ.")
    if not 1 <= len(view_model.thresholds) <= 12:
        raise UIContractError("Danh sách ngưỡng không hợp lệ.")

    providers: list[JsonValue] = []
    for item in view_model.providers:
        if item.model_count < 0:
            raise UIContractError("Số model không hợp lệ.")
        providers.append(
            {
                "provider": _clean_text(item.provider, field="settings.provider", maximum=40),
                "label": _clean_text(item.label, field="settings.provider.label", maximum=120),
                "description": _clean_text(
                    item.description,
                    field="settings.provider.description",
                    maximum=300,
                ),
                "connected": bool(item.connected),
                "active": bool(item.active),
                "model": (
                    _clean_text(item.model, field="settings.provider.model", maximum=160)
                    if item.model is not None
                    else None
                ),
                "model_count": item.model_count,
                "status_label": _clean_text(
                    item.status_label,
                    field="settings.provider.status_label",
                    maximum=80,
                ),
                "status_tone": _tone(item.status_tone, field="settings.provider.status_tone"),
            }
        )

    thresholds: list[JsonValue] = []
    for item in view_model.thresholds:
        if not isinstance(item.value, (int, float)) or isinstance(item.value, bool):
            raise UIContractError("Giá trị ngưỡng không hợp lệ.")
        thresholds.append(
            {
                "key": _clean_text(item.key, field="settings.threshold.key", maximum=80),
                "label": _clean_text(item.label, field="settings.threshold.label", maximum=160),
                "value": float(item.value),
                "value_display": _clean_text(
                    item.value_display,
                    field="settings.threshold.value_display",
                    maximum=80,
                ),
            }
        )

    return _json_object(
        {
            "schema_version": SCHEMA_VERSION,
            "component_version": COMPONENT_VERSION,
            "component": SETTINGS_PAGE_COMPONENT_KIND,
            "theme": view_model.theme,
            "connection_state": view_model.connection_state,
            "connection_status_label": _clean_text(
                view_model.connection_status_label,
                field="settings.connection_status_label",
                maximum=80,
            ),
            "active_provider_label": (
                _clean_text(
                    view_model.active_provider_label,
                    field="settings.active_provider_label",
                    maximum=120,
                )
                if view_model.active_provider_label is not None
                else None
            ),
            "active_model": (
                _clean_text(view_model.active_model, field="settings.active_model", maximum=160)
                if view_model.active_model is not None
                else None
            ),
            "providers": providers,
            "thresholds": thresholds,
            "chat_state": view_model.chat_state,
            "chat_message_count": view_model.chat_message_count,
            "current_case": (
                _clean_text(view_model.current_case, field="settings.current_case", maximum=80)
                if view_model.current_case is not None
                else None
            ),
            "has_result": bool(view_model.has_result),
            "evaluation_ready": bool(view_model.evaluation_ready),
            "error_message": (
                _clean_text(view_model.error_message, field="settings.error_message", maximum=300)
                if view_model.error_message is not None
                else None
            ),
        },
        label="Settings page view model",
    )


def _validate_event_base(raw_event: Mapping[str, Any], extra_keys: set[str]) -> str:
    _assert_no_prohibited_keys(raw_event, "event")
    required_keys = {
        "schema_version",
        "component_version",
        "component",
        "type",
        "action",
        "event_id",
    } | extra_keys
    if set(raw_event) != required_keys:
        raise UIContractError("Event có trường thiếu hoặc không được phép.")
    if raw_event.get("schema_version") != SCHEMA_VERSION:
        raise UIContractError("schema_version của event không tương thích.")
    if raw_event.get("component_version") != COMPONENT_VERSION:
        raise UIContractError("component_version của event không tương thích.")
    event_id = raw_event.get("event_id")
    if not isinstance(event_id, str) or not _EVENT_ID_PATTERN.fullmatch(event_id):
        raise UIContractError("event_id không hợp lệ.")
    return event_id


def parse_ui_event(raw_event: Any) -> V2UIEvent | None:
    """Xác thực nghiêm ngặt mọi event production từ trình duyệt."""

    if raw_event is None:
        return None
    if not isinstance(raw_event, Mapping):
        raise UIContractError("Event phải là một object.")
    component = raw_event.get("component")
    event_type = raw_event.get("type")
    action = raw_event.get("action")

    if component == SHELL_COMPONENT_KIND and event_type == "navigation.select" and action == "select":
        event_id = _validate_event_base(raw_event, {"page"})
        page = _clean_text(raw_event.get("page"), field="event.page", maximum=100)
        return V2NavigationEvent(event_id=event_id, page=page)
    if component == DEMO_COMPONENT_KIND and event_type in {"demo.select", "demo.open"}:
        expected_action = "select" if event_type == "demo.select" else "open"
        if action != expected_action:
            raise UIContractError("Action demo không khớp event type.")
        event_id = _validate_event_base(raw_event, {"case_name"})
        case_name = _clean_text(raw_event.get("case_name"), field="event.case_name", maximum=120)
        return V2DemoEvent(
            event_id=event_id,
            case_name=case_name,
            action=expected_action,
            type=event_type,
        )
    if (
        component == EVALUATION_PAGE_COMPONENT_KIND
        and event_type == "evaluation.run"
        and action == "run"
    ):
        event_id = _validate_event_base(raw_event, set())
        return V2EvaluationEvent(event_id=event_id)
    raise UIContractError("Loại event hoặc component không được phép.")


def load_component_assets(asset_dir: str | Path | None = None) -> tuple[str, str]:
    """Đọc build artifact đã đóng gói; không tải mã từ mạng lúc chạy."""

    directory = Path(asset_dir) if asset_dir is not None else _DEFAULT_ASSET_DIR
    js_path = directory / "creditlens-v2.js"
    css_path = directory / "creditlens-v2.css"
    try:
        javascript = js_path.read_text(encoding="utf-8")
        stylesheet = css_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise V2ComponentUnavailable("Build artifact UI v2 chưa sẵn sàng.") from exc
    if not javascript.strip() or not stylesheet.strip():
        raise V2ComponentUnavailable("Build artifact UI v2 không hợp lệ.")
    return javascript, stylesheet


def get_component_renderer(st_module: Any, asset_dir: str | Path | None = None) -> ComponentRenderer:
    """Đăng ký component v2 từ asset nội bộ với style isolation bật."""

    components = getattr(st_module, "components", None)
    v2 = getattr(components, "v2", None)
    component_factory = getattr(v2, "component", None)
    if not callable(component_factory):
        raise V2ComponentUnavailable("Streamlit Components v2 không khả dụng.")
    directory = Path(asset_dir) if asset_dir is not None else _DEFAULT_ASSET_DIR
    cache_key = (id(v2), str(directory.resolve()))
    cached = _RENDERER_CACHE.get(cache_key)
    if cached is not None:
        return cached
    javascript, stylesheet = load_component_assets(directory)
    renderer = component_factory(
        COMPONENT_NAME,
        html='<div data-creditlens-v2-root="true"></div>',
        css=stylesheet,
        js=javascript,
        isolate_styles=True,
    )
    _RENDERER_CACHE[cache_key] = renderer
    return renderer


def _event_from_result(result: Any) -> Any:
    if isinstance(result, Mapping):
        return result.get("event")
    return getattr(result, "event", None)


def _render_payload(
    st_module: Any,
    payload: dict[str, JsonValue],
    *,
    key: str,
    renderer: ComponentRenderer | None = None,
) -> V2UIEvent | None:
    component = renderer or get_component_renderer(st_module)
    result = component(key=key, data=payload, width="stretch", height="content")
    return parse_ui_event(_event_from_result(result))


def render_app_shell(
    st_module: Any,
    view_model: V2AppShellViewModel,
    *,
    renderer: ComponentRenderer | None = None,
) -> V2NavigationEvent | None:
    event = _render_payload(
        st_module,
        serialize_shell_view_model(view_model),
        key="creditlens_v2_app_shell",
        renderer=renderer,
    )
    if event is None or isinstance(event, V2NavigationEvent):
        return event
    raise UIContractError("App Shell nhận event không đúng loại.")


def render_demo_panel(
    st_module: Any,
    view_model: V2DemoPanelViewModel,
    *,
    renderer: ComponentRenderer | None = None,
) -> V2DemoEvent | None:
    event = _render_payload(
        st_module,
        serialize_demo_panel_view_model(view_model),
        key="creditlens_v2_demo_panel",
        renderer=renderer,
    )
    if event is None or isinstance(event, V2DemoEvent):
        return event
    raise UIContractError("Demo Panel nhận event không đúng loại.")


def render_workflow_panel(
    st_module: Any,
    view_model: V2WorkflowPanelViewModel,
    *,
    renderer: ComponentRenderer | None = None,
) -> None:
    event = _render_payload(
        st_module,
        serialize_workflow_panel_view_model(view_model),
        key="creditlens_v2_mobile_workflow",
        renderer=renderer,
    )
    if event is not None:
        raise UIContractError("Workflow Panel không được phát domain event.")


def render_core_page(
    st_module: Any,
    view_model: V2CorePageViewModel,
    *,
    renderer: ComponentRenderer | None = None,
) -> None:
    """Render Cụm 4 thuần trình bày; component không được phát domain event."""

    event = _render_payload(
        st_module,
        serialize_core_page_view_model(view_model),
        key=f"creditlens_v2_core_{view_model.page}",
        renderer=renderer,
    )
    if event is not None:
        raise UIContractError("Core business page không được phát domain event.")


def render_summary_page(
    st_module: Any,
    view_model: V2SummaryPageViewModel,
    *,
    renderer: ComponentRenderer | None = None,
) -> None:
    event = _render_payload(
        st_module,
        serialize_summary_page_view_model(view_model),
        key="creditlens_v2_summary_page",
        renderer=renderer,
    )
    if event is not None:
        raise UIContractError("Summary page không được phát domain event.")


def render_methodology_page(
    st_module: Any,
    view_model: V2MethodologyPageViewModel,
    *,
    renderer: ComponentRenderer | None = None,
) -> None:
    event = _render_payload(
        st_module,
        serialize_methodology_page_view_model(view_model),
        key="creditlens_v2_methodology_page",
        renderer=renderer,
    )
    if event is not None:
        raise UIContractError("Methodology page không được phát domain event.")


def render_evaluation_page(
    st_module: Any,
    view_model: V2EvaluationPageViewModel,
    *,
    renderer: ComponentRenderer | None = None,
) -> V2EvaluationEvent | None:
    event = _render_payload(
        st_module,
        serialize_evaluation_page_view_model(view_model),
        key="creditlens_v2_evaluation_page",
        renderer=renderer,
    )
    if event is None or isinstance(event, V2EvaluationEvent):
        return event
    raise UIContractError("Evaluation page nhận event không đúng loại.")


def render_settings_page(
    st_module: Any,
    view_model: V2SettingsPageViewModel,
    *,
    renderer: ComponentRenderer | None = None,
) -> None:
    """Render safe Settings metadata; all credential and chat actions stay native."""

    event = _render_payload(
        st_module,
        serialize_settings_page_view_model(view_model),
        key="creditlens_v2_settings_page",
        renderer=renderer,
    )
    if event is not None:
        raise UIContractError("Settings page không được phát domain event.")


def queue_v2_upload_action(session_state: Any) -> bool:
    """Khóa một upload action trước rerun để chặn duplicate submit."""

    if session_state.get("ui_v2_processing") or session_state.get("ui_v2_upload_requested"):
        return False
    session_state["ui_v2_upload_requested"] = True
    session_state["ui_v2_processing"] = True
    session_state["ui_v2_error"] = ""
    session_state["ui_v2_warning"] = ""
    session_state["ui_v2_notice"] = ""
    return True


def _claim_ui_event(session_state: Any, event_id: str) -> bool:
    if session_state.get("ui_v2_last_event_id") == event_id:
        return False
    session_state["ui_v2_last_event_id"] = event_id
    return True


def theme_mode_from_settings(settings: Mapping[str, Any]) -> Literal["system", "light", "dark"]:
    mode = settings.get("che_do_giao_dien", "Theo hệ thống")
    if mode == "Tối":
        return "dark"
    if mode == "Sáng":
        return "light"
    return "system"


def build_workflow_steps(
    result: Any | None,
    *,
    processing: bool = False,
    error: bool = False,
) -> tuple[V2WorkflowStep, ...]:
    """Ánh xạ trạng thái Python hiện có sang presentation states, không tính nghiệp vụ."""

    definitions = (
        ("intake", "Tiếp nhận", "Tiếp nhận và chuẩn hóa tài liệu"),
        ("compute", "Tính toán", "Tính toán xác định bằng Python"),
        ("crosscheck", "Đối chiếu", "Đối chiếu dữ kiện và bằng chứng"),
        ("human", "Con người xem xét", "Chuyên viên chịu trách nhiệm quyết định"),
    )
    if error:
        states = ("error", "upcoming", "upcoming", "upcoming")
        labels = ("Cần xử lý", "Chưa thực hiện", "Chưa thực hiện", "Chưa thực hiện")
    elif processing:
        states = ("current", "upcoming", "upcoming", "upcoming")
        labels = ("Đang xử lý", "Chưa thực hiện", "Chưa thực hiện", "Chưa thực hiện")
    elif result is None:
        states = ("current", "upcoming", "upcoming", "upcoming")
        labels = ("Hiện tại", "Chưa thực hiện", "Chưa thực hiện", "Chưa thực hiện")
    else:
        has_review_condition = bool(getattr(result, "canh_bao", ())) or getattr(result, "trang_thai", "") != "REVIEW READY"
        states = ("complete", "complete", "warning" if has_review_condition else "complete", "current")
        labels = ("Hoàn tất", "Hoàn tất", "Cần đối chiếu" if has_review_condition else "Hoàn tất", "Hiện tại")
    return tuple(
        V2WorkflowStep(
            key=key,
            label=label,
            description=description,
            state=state,  # type: ignore[arg-type]
            status_label=status_label,
        )
        for (key, label, description), state, status_label in zip(definitions, states, labels)
    )


def _build_process_cards(workflow: tuple[V2WorkflowStep, ...]) -> tuple[V2ProcessCard, ...]:
    copy = {
        "intake": "Kiểm tra PDF, phân loại tài liệu và giữ nguồn cho từng dữ kiện.",
        "compute": "Python tính chỉ số; dữ liệu thiếu không được tự suy diễn.",
        "crosscheck": "Cảnh báo được liên kết lại với tài liệu, trang và giá trị.",
        "human": "Chuyên viên xác minh và quyết định; hệ thống không tự phê duyệt.",
    }
    return tuple(
        V2ProcessCard(key=step.key, label=step.label, description=copy[step.key], state=step.state)
        for step in workflow
    )


def _has_upload_selection(session_state: Any) -> bool:
    if session_state.get("credit_upload_mode") == "Tải một thư mục":
        files = session_state.get("credit_folder_pdfs") or []
        return bool(files)
    return any(
        session_state.get(key)
        for key in ("application_pdf", "income_pdf", "statement_pdf", "debt_pdf")
    )


def _build_case_context(result: Any | None, source: str | None, status_labels: Mapping[str, str]) -> V2CaseContext:
    if result is None:
        return V2CaseContext(
            case_id=None,
            source=None,
            status_label="Chưa có hồ sơ đang mở",
            status_tone="neutral",
            summary="Tải tài liệu hoặc chọn một hồ sơ minh họa để tiếp tục.",
        )
    raw_status = str(getattr(result, "trang_thai", "INSUFFICIENT INFORMATION"))
    tone: Literal["neutral", "info", "success", "warning", "danger"] = {
        "REVIEW READY": "success",
        "HUMAN REVIEW REQUIRED": "warning",
        "INSUFFICIENT INFORMATION": "neutral",
    }.get(raw_status, "neutral")  # type: ignore[assignment]
    fields = len(getattr(result, "truong_trich_xuat", ()))
    warnings = len(getattr(result, "canh_bao", ()))
    return V2CaseContext(
        case_id=str(getattr(result, "ma_ho_so", "")) or None,
        source=source or "Phiên hiện tại",
        status_label=status_labels.get(raw_status, raw_status),
        status_tone=tone,
        summary=f"{fields} trường dữ liệu · {warnings} cảnh báo",
    )


def build_app_shell_view_model(
    *,
    active_page: str,
    pages: tuple[str, ...],
    page_labels: Mapping[str, str],
    settings: Mapping[str, Any],
    logo_data_uri: str,
    result: Any | None,
    session_state: Any,
    status_labels: Mapping[str, str],
) -> V2AppShellViewModel:
    navigation: list[V2NavigationItem] = []
    for index, page in enumerate(pages, start=1):
        if index <= 5:
            group: Literal["Hồ sơ", "Kiểm chứng", "Hệ thống"] = "Hồ sơ"
        elif index <= 7:
            group = "Kiểm chứng"
        else:
            group = "Hệ thống"
        raw_label = page_labels[page]
        label = raw_label.split(".  ", 1)[-1]
        navigation.append(V2NavigationItem(page=page, label=label, group=group, ordinal=index))

    processing = bool(session_state.get("ui_v2_processing", False))
    error = str(session_state.get("ui_v2_error") or "")[:300]
    warning = str(session_state.get("ui_v2_warning") or "")[:300]
    notice = str(session_state.get("ui_v2_notice") or "")[:300]
    has_upload = _has_upload_selection(session_state)
    raw_status = str(getattr(result, "trang_thai", "")) if result is not None else ""
    if error:
        page_state = "error"
        state_message = error
    elif processing:
        page_state = "processing"
        state_message = "Đang xử lý hồ sơ bằng pipeline Python hiện hành."
    elif result is None and has_upload:
        page_state = "ready"
        state_message = "Tài liệu đã được chọn; có thể chạy quy trình thẩm định."
    elif result is None:
        page_state = "empty"
        state_message = "Chưa có hồ sơ đang mở."
    elif warning or raw_status != "REVIEW READY":
        page_state = "warning"
        state_message = warning or "Hồ sơ cần con người xem xét hoặc bổ sung thông tin."
    else:
        page_state = "success"
        state_message = notice or "Hồ sơ đã sẵn sàng để tiếp tục xem xét."

    workflow = build_workflow_steps(result, processing=processing, error=bool(error))
    case_context = _build_case_context(
        result,
        str(session_state.get("ui_v2_case_source") or "") or None,
        status_labels,
    )
    return V2AppShellViewModel(
        active_page=active_page,
        navigation=tuple(navigation),
        workflow=workflow,
        process_cards=_build_process_cards(workflow),
        case_context=case_context,
        logo_data_uri=logo_data_uri,
        theme=theme_mode_from_settings(settings),
        overview=active_page == pages[0],
        page_state=page_state,  # type: ignore[arg-type]
        state_message=state_message,
    )


def build_demo_panel_view_model(
    *,
    case_names: tuple[str, ...],
    selected_case: str,
    case_context: V2CaseContext,
    theme: Literal["system", "light", "dark"],
    processing: bool,
    error: str | None,
) -> V2DemoPanelViewModel:
    items: list[V2DemoCaseItem] = []
    for case_name in case_names:
        code, _, title = case_name.partition(" — ")
        items.append(
            V2DemoCaseItem(
                case_name=case_name,
                case_code=code,
                title=title or case_name,
                description="Dữ liệu tổng hợp xác định; không gọi mô hình khi mở hồ sơ.",
            )
        )
    return V2DemoPanelViewModel(
        cases=tuple(items),
        selected_case=selected_case,
        case_context=case_context,
        theme=theme,
        loading=processing,
        error=error[:300] if error else None,
    )


def _confidence_tone(
    confidence: float,
    *,
    threshold: float,
    missing: bool = False,
    invalid: bool = False,
) -> Literal["neutral", "info", "success", "warning", "danger"]:
    """Ánh xạ visual từ đúng threshold hiện hành; không tạo ngưỡng nghiệp vụ mới."""

    if missing:
        return "neutral"
    if invalid or confidence < threshold:
        return "danger"
    if confidence >= 0.90:
        return "success"
    return "warning"


def _metric_tone(status: str) -> Literal["neutral", "info", "success", "warning", "danger"]:
    return {
        "Trong ngưỡng minh họa": "success",
        "Cần chú ý": "warning",
        "Chưa đủ dữ liệu": "neutral",
    }.get(status, "neutral")  # type: ignore[return-value]


def _field_source_role(field_key: str) -> Literal["declared", "observed", "calculated", "other"]:
    declared = {
        "ho_ten_khach_hang",
        "don_vi_cong_tac_ke_khai",
        "chuc_danh_ke_khai",
        "ngay_bat_dau_ke_khai",
        "thu_nhap_ke_khai",
        "so_tien_de_nghi_vay",
        "thoi_han_vay_thang",
        "khoan_tra_du_kien",
        "nghia_vu_no_ke_khai",
        "chi_phi_sinh_hoat",
        "muc_dich_vay",
    }
    observed = {
        "don_vi_cong_tac_chung_tu",
        "chuc_danh_chung_tu",
        "ngay_bat_dau_chung_tu",
        "tham_nien_lam_viec_thang",
        "luong_thuc_nhan",
        "thu_nhap_qua_sao_ke",
        "nghia_vu_no_quan_sat",
        "so_du_binh_quan",
        "bien_dong_thu_nhap",
    }
    if field_key in declared:
        return "declared"
    if field_key in observed:
        return "observed"
    return "other"


def _build_metric_items(result: Any, thresholds: Mapping[str, Any]) -> tuple[V2MetricItem, ...]:
    """Reuse one presentation mapping for Cluster 4 Analysis and Cluster 5 Summary."""

    from credit_underwriting_colab import phan_tram, so_thap_phan

    references = {
        "dti": f"Cần chú ý khi > {phan_tram(float(thresholds['dti_canh_bao']))}",
        "dsr": f"Cần chú ý khi > {phan_tram(float(thresholds['dsr_canh_bao']))}",
        "thu_nhap_kha_dung": "Trạng thái do Python trả về",
        "he_so_dem_so_du": (
            f"Cần chú ý khi < {so_thap_phan(float(thresholds['he_so_dem_so_du_thap']))}×"
        ),
        "chenh_lech_thu_nhap": (
            f"Cần chú ý khi > {phan_tram(float(thresholds['chenh_lech_thu_nhap']))}"
        ),
        "bien_dong_thu_nhap": (
            f"Cần chú ý khi > {phan_tram(float(thresholds['bien_dong_thu_nhap_cao']))}"
        ),
    }
    return tuple(
        V2MetricItem(
            key=metric.ma_chi_so,
            label=metric.ten,
            value_display=metric.hien_thi,
            raw_value=metric.gia_tri,
            reference=references.get(metric.ma_chi_so, "Trạng thái do Python trả về"),
            status=metric.trang_thai,
            status_tone=_metric_tone(metric.trang_thai),
            formula=metric.cong_thuc,
            note=metric.ghi_chu,
        )
        for metric in result.chi_so
    )


def _build_risk_items(result: Any) -> tuple[V2RiskItem, ...]:
    """Map existing backend risk order/severity without creating or reprioritising a rule."""

    from credit_underwriting_colab import NHAN_MUC_DO, NHAN_RUI_RO

    severity_tones: dict[str, Literal["neutral", "info", "warning", "danger"]] = {
        "HIGH": "danger",
        "MEDIUM": "warning",
        "LOW": "info",
        "INFO": "neutral",
    }
    items: list[V2RiskItem] = []
    for risk in result.canh_bao:
        evidence = tuple(
            V2EvidenceReference(
                document=item.tai_lieu,
                page=item.trang,
                field=item.truong_du_lieu,
                value=item.gia_tri or "Không có giá trị",
                excerpt=item.trich_doan or None,
            )
            for item in risk.bang_chung
        )
        items.append(
            V2RiskItem(
                code=risk.ma_rui_ro,
                name=NHAN_RUI_RO.get(risk.loai, risk.loai),
                severity=risk.muc_do,
                severity_label=NHAN_MUC_DO[risk.muc_do],
                severity_tone=severity_tones[risk.muc_do],
                description=risk.giai_thich,
                difference=risk.chenh_lech,
                evidence=evidence,
            )
        )
    return tuple(items)


def build_core_page_view_model(
    *,
    page: Literal["extraction", "analysis", "risk"],
    result: Any | None,
    docs: Mapping[str, Any],
    thresholds: Mapping[str, Any],
    theme: Literal["system", "light", "dark"],
    processing: bool = False,
    error: str | None = None,
) -> V2CorePageViewModel:
    """Chuyển output miền hiện hành thành dữ liệu trình bày Cụm 4, không tính lại nghiệp vụ."""

    from credit_underwriting_colab import (
        NHAN_LOAI_TAI_LIEU,
        NHAN_TRANG_THAI,
        gia_tri_truong_hien_thi,
        nhan_luu_y_tin_cay,
        phan_tram,
        so_thap_phan,
        tien,
    )

    page_copy = {
        "extraction": (
            "Trích xuất tài liệu",
            "Kiểm tra từng dữ kiện cùng nguồn, trang, confidence và bằng chứng gốc.",
        ),
        "analysis": (
            "Phân tích tín dụng bằng Python",
            "Các chỉ số được nhận nguyên trạng từ pipeline Python; giao diện không tính lại.",
        ),
        "risk": (
            "Cảnh báo rủi ro và bằng chứng",
            "Cảnh báo được nhóm theo severity hiện có và liên kết tới bằng chứng nguồn.",
        ),
    }
    title, subtitle = page_copy[page]
    if error:
        state: Literal["empty", "loading", "success", "partial", "error"] = "error"
        state_message = error[:300]
    elif processing:
        state = "loading"
        state_message = "Đang xử lý hồ sơ bằng pipeline Python hiện hành."
    elif result is None:
        state = "empty"
        state_message = "Chưa có hồ sơ để hiển thị. Hãy tải PDF hoặc mở hồ sơ minh họa."
    else:
        has_partial_data = (
            getattr(result, "trang_thai", "") != "REVIEW READY"
            or bool(getattr(result, "thong_tin_thieu", ()))
            or any(getattr(doc, "trang_thai", "") == "Không đọc được" for doc in docs.values())
        )
        state = "partial" if has_partial_data else "success"
        state_message = (
            "Một phần dữ liệu chưa đủ hoặc cần con người kiểm tra."
            if has_partial_data
            else "Dữ liệu đã sẵn sàng để chuyên viên xem xét."
        )

    if result is None:
        return V2CorePageViewModel(
            page=page,
            title=title,
            subtitle=subtitle,
            state=state,
            state_message=state_message,
            theme=theme,
        )

    low_threshold = float(thresholds["do_tin_cay_thap"])
    document_items: list[V2DocumentItem] = []
    field_items: list[V2ExtractedFieldItem] = []
    comparisons: list[V2CrossDocumentComparison] = []
    metric_items: list[V2MetricItem] = []
    threshold_items: list[V2ThresholdReference] = []
    risk_items: list[V2RiskItem] = []

    if page == "extraction":
        for doc in docs.values():
            mismatch = doc.loai_nhan_dien not in {"unknown", doc.loai_ky_vong}
            missing = doc.trang_thai == "Không đọc được"
            document_items.append(
                V2DocumentItem(
                    name=doc.ten_tep,
                    expected_type=NHAN_LOAI_TAI_LIEU[doc.loai_ky_vong],
                    detected_type=NHAN_LOAI_TAI_LIEU.get(doc.loai_nhan_dien, "Chưa xác định"),
                    pages=doc.so_trang,
                    status=doc.trang_thai,
                    confidence=float(doc.do_tin_cay),
                    confidence_display=phan_tram(float(doc.do_tin_cay)),
                    confidence_label=nhan_luu_y_tin_cay(
                        float(doc.do_tin_cay),
                        unreadable=missing,
                        type_mismatch=mismatch,
                        low_confidence_threshold=low_threshold,
                    ),
                    confidence_tone=_confidence_tone(
                        float(doc.do_tin_cay),
                        threshold=low_threshold,
                        missing=missing,
                        invalid=mismatch,
                    ),
                    type_mismatch=mismatch,
                )
            )
        for field in result.truong_trich_xuat:
            missing = field.gia_tri is None
            confidence = float(field.do_tin_cay)
            status = nhan_luu_y_tin_cay(
                confidence,
                missing=missing,
                low_confidence_threshold=low_threshold,
            )
            evidence = None
            if field.bang_chung is not None:
                evidence = V2EvidenceReference(
                    document=field.bang_chung.tai_lieu,
                    page=field.bang_chung.trang,
                    field=field.bang_chung.truong_du_lieu,
                    value=field.bang_chung.gia_tri or "Không có giá trị",
                    excerpt=field.bang_chung.trich_doan or None,
                )
            field_items.append(
                V2ExtractedFieldItem(
                    key=field.ma_truong,
                    label=field.nhan,
                    value_display=gia_tri_truong_hien_thi(field),
                    raw_value=field.gia_tri,
                    source=field.tai_lieu_nguon,
                    source_role=_field_source_role(field.ma_truong),
                    page=field.trang,
                    confidence=confidence,
                    confidence_display=phan_tram(confidence),
                    confidence_label=status,
                    confidence_tone=_confidence_tone(
                        confidence,
                        threshold=low_threshold,
                        missing=missing,
                    ),
                    status=status,
                    evidence=evidence,
                )
            )

    if page == "analysis":
        metrics_by_key = {metric.ma_chi_so: metric for metric in result.chi_so}
        income_difference = metrics_by_key.get("chenh_lech_thu_nhap")
        d = result.du_lieu
        comparisons.append(
            V2CrossDocumentComparison(
                title="Đối chiếu thu nhập giữa các nguồn",
                values=(
                    V2ComparisonValue(
                        role="declared",
                        label="Thu nhập kê khai",
                        value_display=tien(d.thu_nhap_ke_khai),
                        source="Đơn đề nghị vay vốn",
                    ),
                    V2ComparisonValue(
                        role="observed",
                        label="Lương thực nhận",
                        value_display=tien(d.luong_thuc_nhan),
                        source="Chứng từ thu nhập",
                    ),
                    V2ComparisonValue(
                        role="observed",
                        label="Thu nhập qua sao kê",
                        value_display=tien(d.thu_nhap_qua_sao_ke),
                        source="Sao kê ngân hàng",
                    ),
                    V2ComparisonValue(
                        role="calculated",
                        label="Thu nhập dùng để tính",
                        value_display=tien(result.thu_nhap_dung_de_tinh),
                        source=result.nguon_thu_nhap_dung_de_tinh,
                    ),
                ),
                difference_display=(income_difference.hien_thi if income_difference is not None else "—"),
                status=(income_difference.trang_thai if income_difference is not None else "Chưa đủ dữ liệu"),
                status_tone=(
                    _metric_tone(income_difference.trang_thai) if income_difference is not None else "neutral"
                ),
            )
        )
        metric_items.extend(_build_metric_items(result, thresholds))
        threshold_definitions = (
            ("chenh_lech_thu_nhap", "Chênh lệch thu nhập", "above", phan_tram),
            ("dti_canh_bao", "DTI", "above", phan_tram),
            ("dsr_canh_bao", "DSR", "above", phan_tram),
            ("he_so_dem_so_du_thap", "Hệ số đệm số dư", "below", None),
            ("bien_dong_thu_nhap_cao", "Biến động thu nhập", "above", phan_tram),
        )
        for key, label, relation, formatter in threshold_definitions:
            value = float(thresholds[key])
            value_display = formatter(value) if formatter else f"{so_thap_phan(value)}×"
            threshold_items.append(
                V2ThresholdReference(
                    key=key,
                    label=label,
                    value=value,
                    value_display=value_display,
                    relation=relation,  # type: ignore[arg-type]
                )
            )

    if page == "risk":
        risk_items.extend(_build_risk_items(result))

    return V2CorePageViewModel(
        page=page,
        title=title,
        subtitle=subtitle,
        state=state,
        state_message=state_message,
        documents=tuple(document_items),
        fields=tuple(field_items),
        comparisons=tuple(comparisons),
        metrics=tuple(metric_items),
        thresholds=tuple(threshold_items),
        risks=tuple(risk_items),
        case_status=NHAN_TRANG_THAI.get(result.trang_thai, result.trang_thai),
        theme=theme,
    )


def build_summary_page_view_model(
    *,
    result: Any | None,
    docs: Mapping[str, Any],
    thresholds: Mapping[str, Any],
    ai_explanation: str | None,
    theme: Literal["system", "light", "dark"],
    error: str | None = None,
) -> V2SummaryPageViewModel:
    """Build the Cluster 5 decision-support view from the existing result only."""

    from credit_underwriting_colab import NHAN_MUC_DO, NHAN_TRANG_THAI, so_thap_phan, tien

    if error:
        return V2SummaryPageViewModel(
            state="error",
            state_message=error[:300],
            case_id=None,
            applicant="Chưa có dữ liệu",
            employer="Chưa có dữ liệu",
            loan_amount="—",
            loan_term="—",
            loan_purpose="Chưa có dữ liệu",
            review_status="KHÔNG THỂ HIỂN THỊ",
            review_status_tone="danger",
            highest_alert="Chưa xác định",
            highest_alert_tone="neutral",
            theme=theme,
        )
    if result is None:
        return V2SummaryPageViewModel(
            state="empty",
            state_message="Chưa có hồ sơ để tạo tóm tắt. Hãy tải PDF hoặc mở hồ sơ minh họa.",
            case_id=None,
            applicant="Chưa có dữ liệu",
            employer="Chưa có dữ liệu",
            loan_amount="—",
            loan_term="—",
            loan_purpose="Chưa có dữ liệu",
            review_status="CHƯA CÓ HỒ SƠ",
            review_status_tone="neutral",
            highest_alert="Chưa có cảnh báo",
            highest_alert_tone="neutral",
            theme=theme,
        )

    status_tones: dict[str, Literal["neutral", "info", "success", "warning", "danger"]] = {
        "REVIEW READY": "success",
        "HUMAN REVIEW REQUIRED": "warning",
        "INSUFFICIENT INFORMATION": "neutral",
    }
    risks = _build_risk_items(result)
    severity_tones: dict[str, Literal["neutral", "info", "warning", "danger"]] = {
        "HIGH": "danger",
        "MEDIUM": "warning",
        "LOW": "info",
        "INFO": "neutral",
    }
    highest_severity = next(
        (severity for severity in ("HIGH", "MEDIUM", "LOW", "INFO") if any(r.severity == severity for r in risks)),
        None,
    )
    findings: list[V2FindingItem] = [
        V2FindingItem(
            category="finding",
            title="Thu nhập dùng để tính",
            detail=f"{tien(result.thu_nhap_dung_de_tinh)} · {result.nguon_thu_nhap_dung_de_tinh}",
            tone="info",
        ),
        V2FindingItem(
            category="finding",
            title="Trạng thái nguồn thu nhập",
            detail=(
                "Đã có nguồn đối chiếu độc lập"
                if result.thu_nhap_duoc_xac_minh_doc_lap
                else "Chỉ kê khai hoặc chưa đủ dữ liệu"
            ),
            tone="success" if result.thu_nhap_duoc_xac_minh_doc_lap else "warning",
        ),
    ]
    findings.extend(
        V2FindingItem(
            category="missing",
            title="Thông tin còn thiếu",
            detail=str(item),
            tone="warning",
        )
        for item in result.thong_tin_thieu
    )
    findings.extend(
        V2FindingItem(
            category="verification",
            title="Cần chuyên viên xác minh",
            detail=str(item),
            tone="warning",
        )
        for item in result.cau_hoi_xac_minh
    )
    if not result.thong_tin_thieu:
        findings.append(
            V2FindingItem(
                category="finding",
                title="Hạng mục bắt buộc",
                detail="Không phát hiện hạng mục bắt buộc còn thiếu.",
                tone="success",
            )
        )
    evidence = tuple(reference for risk in risks for reference in risk.evidence)
    d = result.du_lieu
    partial = result.trang_thai == "INSUFFICIENT INFORMATION" or bool(result.thong_tin_thieu)
    return V2SummaryPageViewModel(
        state="partial" if partial else "success",
        state_message=(
            "Thông tin chưa đủ; chuyên viên cần bổ sung và xác minh trước khi xem xét."
            if partial
            else "Kết quả xác định đã sẵn sàng để chuyên viên xem xét."
        ),
        case_id=result.ma_ho_so,
        applicant=d.ho_ten_khach_hang or "Thông tin chưa đủ",
        employer=d.don_vi_cong_tac_ke_khai or "Thông tin chưa đủ",
        loan_amount=tien(d.so_tien_de_nghi_vay),
        loan_term=(
            f"{so_thap_phan(d.thoi_han_vay_thang, 0)} tháng"
            if d.thoi_han_vay_thang is not None
            else "Thông tin chưa đủ"
        ),
        loan_purpose=d.muc_dich_vay or "Thông tin chưa đủ",
        review_status=NHAN_TRANG_THAI.get(result.trang_thai, result.trang_thai),
        review_status_tone=status_tones.get(result.trang_thai, "neutral"),
        highest_alert=(
            f"{highest_severity} · {NHAN_MUC_DO[highest_severity]}"
            if highest_severity is not None
            else "Không có cảnh báo"
        ),
        highest_alert_tone=(severity_tones[highest_severity] if highest_severity else "neutral"),
        metrics=_build_metric_items(result, thresholds),
        top_risks=risks[:3],
        total_risk_count=len(risks),
        findings=tuple(findings),
        evidence=evidence,
        document_count=len(docs),
        extracted_field_count=len(result.truong_trich_xuat),
        ai_explanation=ai_explanation.strip() if ai_explanation and ai_explanation.strip() else None,
        theme=theme,
    )


def build_methodology_page_view_model(
    *,
    theme: Literal["system", "light", "dark"],
) -> V2MethodologyPageViewModel:
    """Present the existing documented method and limitations without changing definitions."""

    return V2MethodologyPageViewModel(
        layers=(
            V2MethodologyLayer(
                key="facts",
                label="1. DỮ KIỆN",
                description=(
                    "Kiểm tra PDF, đọc lớp văn bản theo trang, phân loại tài liệu, tìm nhãn/bí danh "
                    "và chuẩn hóa bằng Pydantic. Không điền dữ liệu không tìm thấy."
                ),
            ),
            V2MethodologyLayer(
                key="deterministic",
                label="2. PHÂN TÍCH XÁC ĐỊNH",
                description=(
                    "Python tính DTI, DSR, thu nhập còn lại, hệ số đệm số dư, chênh lệch và biến động "
                    "thu nhập. Mẫu số bằng 0 hoặc thiếu dữ liệu trả về Chưa đủ dữ liệu."
                ),
            ),
            V2MethodologyLayer(
                key="ai",
                label="3. DIỄN GIẢI AI",
                description=(
                    "LLM chỉ nhận facts, calculations, rules và evidence khi người dùng chủ động yêu cầu. "
                    "Nếu API lỗi, báo cáo xác định vẫn hoạt động."
                ),
            ),
        ),
        formulas=(
            V2FormulaCard(
                key="dti",
                name="DTI hiện hữu",
                formula="Nghĩa vụ nợ hiện hữu ÷ Thu nhập dùng để tính",
                meaning="Tỷ trọng nghĩa vụ nợ hiện hữu trên nguồn thu nhập được chọn bởi pipeline.",
                limitation="Nợ quan sát được ưu tiên hơn nợ kê khai; dữ liệu thiếu trả về Chưa đủ dữ liệu.",
            ),
            V2FormulaCard(
                key="dsr",
                name="DSR dự kiến",
                formula="(Nợ hiện hữu + Khoản trả dự kiến) ÷ Thu nhập dùng để tính",
                meaning="Minh họa sức chịu khoản trả hiện hữu và khoản trả dự kiến của khoản vay mới.",
                limitation="Khoản trả dự kiến là đầu vào; hệ thống không đặt lãi suất hoặc chính sách tín dụng.",
            ),
            V2FormulaCard(
                key="disposable_income",
                name="Thu nhập còn lại trước khoản vay mới",
                formula="Thu nhập dùng để tính − Nợ hiện hữu − Chi phí sinh hoạt",
                meaning="Phần thu nhập còn lại trước khi trừ khoản trả dự kiến của khoản vay mới.",
                limitation="Không bao gồm khoản trả dự kiến của khoản vay mới.",
            ),
            V2FormulaCard(
                key="income_consistency",
                name="Chênh lệch thu nhập",
                formula="(Nguồn cao nhất − Nguồn thấp nhất) ÷ Nguồn cao nhất",
                meaning="So sánh thu nhập kê khai, chứng từ và sao kê hiện có.",
                limitation="Chỉ phản ánh các nguồn đã trích xuất; không suy diễn nguồn còn thiếu.",
            ),
            V2FormulaCard(
                key="income_volatility",
                name="Biến động thu nhập",
                formula="Độ lệch chuẩn dòng tiền vào tháng ÷ Dòng tiền vào bình quân",
                meaning="Chỉ báo mức dao động của dòng tiền vào theo tháng.",
                limitation="Chỉ có ý nghĩa khi sao kê có đủ dữ liệu theo tháng.",
            ),
            V2FormulaCard(
                key="balance_buffer",
                name="Hệ số đệm số dư",
                formula="Số dư bình quân ÷ Khoản trả dự kiến",
                meaning="Chỉ báo thanh khoản minh họa so với khoản trả dự kiến.",
                limitation="Không phải thước đo thanh khoản toàn diện hoặc chính sách ngân hàng.",
            ),
        ),
        capabilities=(
            V2CapabilityRow("PDF số/có lớp văn bản", "Hỗ trợ", "Tốt nhất khi nhãn và giá trị có thứ tự đọc rõ ràng"),
            V2CapabilityRow("PDF có bảng", "Một phần", "Bảng nhiều cột có thể mất liên kết theo hàng"),
            V2CapabilityRow("PDF quét ảnh", "Chưa đọc nội dung", "Cần OCR và xác nhận của con người"),
            V2CapabilityRow("PDF hỗn hợp", "Một phần", "Dữ kiện chỉ nằm trong ảnh có thể bị bỏ sót"),
            V2CapabilityRow("PDF có mật khẩu", "Không hỗ trợ", "Phải gỡ bảo vệ trước khi tải"),
        ),
        limitations=(
            V2LimitationGroup(
                title="Chất lượng tài liệu",
                items=(
                    "Chưa tích hợp OCR cho PDF chỉ có ảnh.",
                    "Bảng phức tạp và thứ tự đọc nhiều cột có thể làm sai liên kết dữ kiện.",
                    "PDF có mật khẩu phải được gỡ bảo vệ trước khi tải.",
                ),
            ),
            V2LimitationGroup(
                title="Dữ liệu và trích xuất",
                items=(
                    "Từ điển bí danh không bao phủ mọi mẫu tài liệu.",
                    "Dữ liệu không tìm thấy được giữ là thiếu; hệ thống không tự điền.",
                    "Confidence và bằng chứng nguồn phải được chuyên viên đối chiếu.",
                ),
            ),
            V2LimitationGroup(
                title="Mô hình và provider",
                items=(
                    "LLM chỉ là lớp diễn giải tùy chọn và không thay đổi kết quả Python.",
                    "Provider/model có thể lỗi, timeout hoặc hết quota; kết quả xác định vẫn được giữ nguyên.",
                    "Mọi nội dung AI-generated cần được con người kiểm chứng.",
                ),
            ),
            V2LimitationGroup(
                title="Phạm vi đánh giá và human review",
                items=(
                    "Ngưỡng hiện hành chỉ phục vụ minh họa, không phải chính sách ngân hàng.",
                    "Evaluation dùng dữ liệu synthetic/anonymized và không chứng minh hiệu năng production.",
                    "CreditLens không phê duyệt hoặc từ chối khoản vay; quyết định cuối cùng thuộc về con người.",
                ),
            ),
        ),
        self_test_definition=(
            "SELF-TEST kiểm tra phần mềm và các regression guard có tiếp tục chạy đúng hay không: "
            "threshold theo phiên, provider mocks, export và các lỗi đã sửa."
        ),
        evaluation_definition=(
            "EVALUATION đo hệ thống hoạt động tốt đến mức nào trên bộ dữ liệu synthetic độc lập: "
            "extraction, risk, status, grounding, baseline và failure cases."
        ),
        theme=theme,
    )


def _display_rate(value: Any) -> str:
    return "N/A" if value is None else f"{float(value) * 100:.1f}%"


def build_evaluation_page_view_model(
    *,
    report: Mapping[str, Any] | None,
    theme: Literal["system", "light", "dark"],
    error: str | None = None,
) -> V2EvaluationPageViewModel:
    """Map one saved Evaluation report to UI; no evaluator or provider is called."""

    if error:
        return V2EvaluationPageViewModel(
            state="error",
            state_message=error[:500],
            theme=theme,
        )
    if not isinstance(report, Mapping):
        return V2EvaluationPageViewModel(
            state="idle",
            state_message=(
                "Chưa có báo cáo. Run Evaluation chỉ chạy bộ đo xác định sau thao tác rõ ràng; "
                "render và filter không gọi LLM."
            ),
            theme=theme,
        )

    reproducibility = report["reproducibility"]
    dataset = report["dataset_summary"]
    extraction = report["extraction_metrics"]
    risk = report["risk_detection"]
    status = report["status_classification"]
    grounding_report = report["llm_grounding"]
    summary = report["overall_summary"]
    matrix = status["confusion_matrix"]
    labels = tuple(str(label) for label in matrix)

    scorecard_specs = (
        ("extraction_accuracy", "Extraction Accuracy", summary.get("extraction_accuracy")),
        ("risk_precision", "Risk Precision", risk.get("precision")),
        ("risk_recall", "Risk Recall", risk.get("recall")),
        ("risk_f1", "Risk F1", risk.get("f1")),
        ("status_accuracy", "Status Accuracy", status.get("accuracy")),
        ("status_macro_f1", "Status Macro F1", status.get("macro_f1")),
        ("evidence_coverage", "Evidence Coverage", summary.get("grounded_evidence_coverage")),
        (
            "unsupported_claim_rate",
            "Unsupported Claim Rate",
            summary.get("grounded_unsupported_claim_rate"),
        ),
        ("factual_consistency", "Factual Consistency", summary.get("grounded_factual_consistency")),
    )
    scorecards = tuple(
        V2ScorecardItem(
            key=key,
            label=label,
            raw_value=value if isinstance(value, (int, float)) else None,
            value_display=_display_rate(value),
        )
        for key, label, value in scorecard_specs
    )
    field_metrics = tuple(
        V2FieldMetricRow(
            name=str(row["field"]),
            correct=int(row["correct"]),
            total=int(row["total"]),
            accuracy=_display_rate(row.get("accuracy")),
            detail=str(row["comparison"]),
        )
        for row in extraction["by_field"]
    )
    risk_metrics = tuple(
        V2ClassMetricRow(
            name=str(row["risk"]),
            tp=int(row["tp"]),
            fp=int(row["fp"]),
            fn=int(row["fn"]),
            tn=int(row["tn"]),
            precision=_display_rate(row.get("precision")),
            recall=_display_rate(row.get("recall")),
            f1=_display_rate(row.get("f1")),
        )
        for row in risk["by_risk"]
    )
    status_metrics = tuple(
        V2ClassMetricRow(
            name=str(row["status"]),
            tp=int(row["tp"]),
            fp=int(row["fp"]),
            fn=int(row["fn"]),
            tn=None,
            precision=_display_rate(row.get("precision")),
            recall=_display_rate(row.get("recall")),
            f1=_display_rate(row.get("f1")),
        )
        for row in status["by_status"]
    )
    confusion_rows = tuple(
        V2ConfusionRow(
            actual=str(actual),
            predicted=tuple(int(predicted[label]) for label in labels),
        )
        for actual, predicted in matrix.items()
    )
    grounding = tuple(
        V2GroundingRow(
            variant=label,
            evidence_coverage=_display_rate(grounding_report[key].get("evidence_coverage")),
            unsupported_claim_rate=_display_rate(grounding_report[key].get("unsupported_claim_rate")),
            factual_consistency=_display_rate(grounding_report[key].get("factual_consistency")),
        )
        for key, label in (
            ("structured_grounded", "Structured + evidence"),
            ("generic_prompt", "Generic prompt · saved output"),
        )
    )
    baseline_a = report["baselines"]["baseline_a"]
    baseline_b = report["baselines"]["baseline_b"]
    baselines: list[V2BaselineRow] = []
    for key, label in (
        ("current", "CURRENT SYSTEM · multi-document + cross-validation"),
        ("no_cross_document", "BASELINE · no cross-document checks"),
    ):
        values = baseline_a[key]
        baselines.append(
            V2BaselineRow(
                baseline=str(baseline_a["name"]),
                variant=label,
                values=tuple(
                    V2LabelValue(metric_label, _display_rate(values[metric_key]))
                    for metric_key, metric_label in (
                        ("risk_precision", "Risk precision"),
                        ("risk_recall", "Risk recall"),
                        ("risk_f1", "Risk F1"),
                        ("status_accuracy", "Status accuracy"),
                        ("status_macro_f1", "Status macro F1"),
                    )
                ),
            )
        )
    for key, label in (
        ("structured_grounded", "CURRENT SYSTEM · structured + evidence"),
        ("generic_prompt", "BASELINE · generic prompt saved output"),
    ):
        values = baseline_b[key]
        baselines.append(
            V2BaselineRow(
                baseline=str(baseline_b["name"]),
                variant=label,
                values=(
                    V2LabelValue("Evidence coverage", _display_rate(values.get("evidence_coverage"))),
                    V2LabelValue("Unsupported claim rate", _display_rate(values.get("unsupported_claim_rate"))),
                    V2LabelValue("Factual consistency", _display_rate(values.get("factual_consistency"))),
                ),
            )
        )
    failures = tuple(
        V2FailureCase(
            case_id=str(row["case_id"]),
            scenario=str(row["input"]),
            expected=str(row["ground_truth"]),
            actual=(
                json.dumps(row["actual_output"], ensure_ascii=False, sort_keys=True)
                if isinstance(row["actual_output"], (dict, list))
                else str(row["actual_output"])
            ),
            failure_type=str(row["failure_type"]),
            probable_cause=str(row["probable_cause"]),
            mitigation=str(row["mitigation"]),
            status=str(row["status"]),
        )
        for row in report["failure_cases"]
    )
    processing = report["processing_time"]
    llm_calls = reproducibility.get("llm_api_calls")
    return V2EvaluationPageViewModel(
        state="success",
        state_message=(
            "Báo cáo Evaluation đã lưu trong phiên. Filter và rerun chỉ hiển thị lại dữ liệu đã tính."
        ),
        run_id=str(reproducibility["evaluation_run_id"]),
        metadata=(
            V2LabelValue("Run ID", str(reproducibility["evaluation_run_id"])),
            V2LabelValue("Timestamp (UTC)", str(reproducibility["timestamp"])),
            V2LabelValue("Dataset version", str(reproducibility["dataset_version"])),
            V2LabelValue("Evaluation version", str(reproducibility["evaluation_version"])),
            V2LabelValue("App version", str(reproducibility["app_version"])),
            V2LabelValue(
                "Provider / model metadata",
                f"{reproducibility['provider']} / {reproducibility['model']}",
            ),
            V2LabelValue("LLM API calls", str(llm_calls)),
        ),
        dataset=(
            V2LabelValue("Test cases", str(dataset["case_count"])),
            V2LabelValue("Scenarios", str(dataset["scenario_count"])),
            V2LabelValue("Synthetic / anonymized", str(dataset["synthetic_case_count"])),
            V2LabelValue("Variants", ", ".join(str(item) for item in dataset["variants"])),
            V2LabelValue("Scope", str(dataset["scope_note"])),
        ),
        scorecards=scorecards,
        field_metrics=field_metrics,
        risk_metrics=risk_metrics,
        status_metrics=status_metrics,
        confusion_labels=labels,
        confusion_rows=confusion_rows,
        grounding=grounding,
        baselines=tuple(baselines),
        processing=(
            V2LabelValue("Evaluation runtime", f"{processing['evaluation_runtime_ms']} ms"),
            V2LabelValue("CreditLens processing time", f"{processing['creditlens_processing_time_ms']} ms"),
            V2LabelValue("Mean case runtime", f"{processing['mean_case_runtime_ms']} ms"),
            V2LabelValue("Manual processing time", str(processing["manual_processing_time"])),
            V2LabelValue("Time saved", str(processing["time_saved_percentage"])),
        ),
        failure_cases=failures,
        limitations=tuple(str(item) for item in report["limitations"]),
        llm_api_calls=int(llm_calls) if llm_calls is not None else None,
        theme=theme,
    )


def _settings_threshold_display(key: str, value: float) -> str:
    if key == "he_so_dem_so_du_thap":
        return f"{value:.2f}×".replace(".", ",")
    return f"{value * 100:.1f}%".replace(".", ",")


def build_settings_page_view_model(
    *,
    settings: Mapping[str, Any],
    session_state: Mapping[str, Any],
    provider_catalog: Mapping[str, Mapping[str, Any]],
    thresholds: Mapping[str, Any],
    result: Any | None,
    theme: Literal["system", "light", "dark"],
) -> V2SettingsPageViewModel:
    """Build a credential-free Settings summary from the existing Python session state."""

    connections_raw = session_state.get("llm_connections", {})
    connections = connections_raw if isinstance(connections_raw, Mapping) else {}
    active_provider = str(session_state.get("active_llm_provider") or "")
    provider_rows: list[V2ProviderStatus] = []
    active_label: str | None = None
    active_model: str | None = None

    for provider, metadata in provider_catalog.items():
        raw_connection = connections.get(provider)
        connection = raw_connection if isinstance(raw_connection, Mapping) else {}
        model = str(connection.get("model") or "").strip() or None
        models = connection.get("models")
        model_count = len(models) if isinstance(models, (list, tuple)) else 0
        connected = bool(
            connection.get("verified")
            and connection.get("api_key")
            and model
        )
        active = connected and provider == active_provider
        label = str(metadata.get("nhan") or provider)
        if active:
            active_label = label
            active_model = model
        provider_rows.append(
            V2ProviderStatus(
                provider=provider,
                label=label,
                description=str(metadata.get("mo_ta") or "Nhà cung cấp hội thoại được hỗ trợ."),
                connected=connected,
                active=active,
                model=model if connected else None,
                model_count=model_count if connected else 0,
                status_label="ĐANG DÙNG" if active else ("ĐÃ KẾT NỐI" if connected else "CHƯA KẾT NỐI"),
                status_tone="success" if active else ("info" if connected else "neutral"),
            )
        )

    has_connection_error = bool(str(session_state.get("llm_connection_error") or "").strip())
    if has_connection_error:
        connection_state: Literal["connected", "not_configured", "error"] = "error"
        connection_status_label = "ERROR"
        error_message = "Không thể xác minh kết nối. Hãy kiểm tra provider, khóa, model và hạn mức."
    elif active_label and active_model:
        connection_state = "connected"
        connection_status_label = "CONNECTED"
        error_message = None
    else:
        connection_state = "not_configured"
        connection_status_label = "NOT CONFIGURED"
        error_message = None

    threshold_labels = {
        "do_tin_cay_thap": "Độ tin cậy tối thiểu",
        "chenh_lech_thu_nhap": "Chênh lệch thu nhập",
        "chenh_lech_thu_nhap_nghiem_trong": "Chênh lệch thu nhập nghiêm trọng",
        "chenh_lech_no": "Chênh lệch nợ",
        "dti_canh_bao": "Cảnh báo DTI",
        "dsr_canh_bao": "Cảnh báo DSR",
        "he_so_dem_so_du_thap": "Hệ số đệm số dư tối thiểu",
        "bien_dong_thu_nhap_cao": "Biến động thu nhập cao",
    }
    threshold_rows = tuple(
        V2SessionThreshold(
            key=key,
            label=threshold_labels[key],
            value=float(thresholds[key]),
            value_display=_settings_threshold_display(key, float(thresholds[key])),
        )
        for key in threshold_labels
    )

    messages_raw = session_state.get("llm_chat_messages", [])
    chat_message_count = 0
    if isinstance(messages_raw, list):
        chat_message_count = sum(
            1
            for item in messages_raw
            if isinstance(item, Mapping)
            and str(item.get("role") or "") in {"user", "assistant"}
            and bool(str(item.get("content") or "").strip())
        )

    return V2SettingsPageViewModel(
        connection_state=connection_state,
        connection_status_label=connection_status_label,
        active_provider_label=active_label,
        active_model=active_model,
        providers=tuple(provider_rows),
        thresholds=threshold_rows,
        chat_state="error" if session_state.get("ui_v2_chat_error") else (
            "ready" if connection_state == "connected" else "disabled"
        ),
        chat_message_count=chat_message_count,
        current_case=str(getattr(result, "ma_ho_so", "") or "") or None,
        has_result=result is not None,
        evaluation_ready=isinstance(session_state.get("evaluation_report"), Mapping),
        error_message=error_message,
        theme=theme,
    )


def v2_host_styles(theme: Literal["system", "light", "dark"]) -> str:
    """CSS host cho native Streamlit widgets, dùng đúng token Cụm 1."""

    if theme == "dark":
        canvas, surface, text, muted, border, primary, on_primary = (
            "#081226", "#101D39", "#F8FAFC", "#AEB8CB", "#33435F", "#B4C5FF", "#0B1734"
        )
        dark_media = ""
    else:
        canvas, surface, text, muted, border, primary, on_primary = (
            "#F6F8FC", "#FFFFFF", "#0F172A", "#526071", "#D8E0EC", "#203469", "#FFFFFF"
        )
        dark_media = (
            "@media (prefers-color-scheme: dark) {"
            ".stApp{--cl-canvas:#081226;--cl-surface:#101D39;--cl-text:#F8FAFC;"
            "--cl-muted:#AEB8CB;--cl-border:#33435F;--cl-primary:#B4C5FF;--cl-on-primary:#0B1734;}"
            "}"
            if theme == "system"
            else ""
        )
    return f"""
<style>
.stApp {{
  --cl-canvas:{canvas}; --cl-surface:{surface}; --cl-text:{text}; --cl-muted:{muted};
  --cl-border:{border}; --cl-primary:{primary}; --cl-on-primary:{on_primary};
  background:var(--cl-canvas); color:var(--cl-text); color-scheme:{'dark' if theme == 'dark' else 'light'};
}}
[data-testid="stHeader"], [data-testid="stSidebar"] {{ display:none !important; }}
.stMainBlockContainer {{ max-width:none !important; padding:104px 40px 48px 296px !important; }}
.stMainBlockContainer h1, .stMainBlockContainer h2, .stMainBlockContainer h3,
.stMainBlockContainer label, .stMainBlockContainer p {{ color:var(--cl-text); }}
.stMainBlockContainer [data-testid="stCaptionContainer"] p {{ color:var(--cl-muted); }}
.stMainBlockContainer [data-testid="stVerticalBlockBorderWrapper"] {{
  background:var(--cl-surface); border-color:var(--cl-border); border-radius:12px;
}}
.stMainBlockContainer [data-testid="stFileUploaderDropzone"] {{
  background:var(--cl-canvas); border-color:var(--cl-border); border-radius:8px;
}}
.stMainBlockContainer button[kind="primary"] {{
  min-height:44px; border-radius:8px; background:var(--cl-primary); color:var(--cl-on-primary);
}}
.stMainBlockContainer button[kind="secondary"] {{
  border-color:var(--cl-border) !important; background:var(--cl-surface) !important;
  color:var(--cl-text) !important;
}}
.stMainBlockContainer button[kind="secondary"] p {{ color:inherit !important; }}
.stMainBlockContainer button:focus-visible, .stMainBlockContainer input:focus-visible {{
  outline:2px solid #2563EB !important; outline-offset:2px !important;
}}
.st-key-ui_v2_settings_native {{ margin-top:24px; min-width:0; }}
.st-key-ui_v2_settings_native [data-baseweb="tab-list"] {{
  gap:8px; flex-wrap:wrap; border-bottom:1px solid var(--cl-border);
}}
.st-key-ui_v2_settings_native [data-baseweb="tab"] {{
  min-height:44px; border-radius:8px 8px 0 0; color:var(--cl-text);
}}
.st-key-ui_v2_settings_native input,
.st-key-ui_v2_settings_native textarea,
.st-key-ui_v2_settings_native [data-baseweb="select"] > div {{
  min-height:44px; border-color:var(--cl-border) !important; background:var(--cl-surface) !important;
  color:var(--cl-text) !important;
}}
.st-key-ui_v2_settings_native input[type="password"] {{
  font-family:ui-monospace, SFMono-Regular, Consolas, monospace; letter-spacing:.16em;
}}
.st-key-ui_v2_settings_native textarea:focus-visible,
.st-key-ui_v2_settings_native [data-baseweb="select"]:focus-within {{
  outline:2px solid #2563EB !important; outline-offset:2px !important;
}}
.st-key-ui_v2_settings_native [data-testid="stChatMessage"] {{
  max-width:840px; border:1px solid var(--cl-border); border-radius:12px;
  background:var(--cl-surface); padding:4px 12px; overflow-wrap:anywhere;
}}
.st-key-ui_v2_settings_native [data-testid="stChatInput"] {{
  max-width:840px; border-color:var(--cl-border); border-radius:12px;
}}
.st-key-ui_v2_settings_native [data-testid="stAlert"] {{ border-radius:10px; }}
.cl-native-section-anchor {{ scroll-margin-top:96px; }}
{dark_media}
@media (min-width:1280px) and (max-width:1439px) {{
  .stMainBlockContainer {{ padding:100px 32px 40px 280px !important; }}
}}
@media (min-width:1024px) and (max-width:1279px) {{
  .stMainBlockContainer {{ padding:96px 24px 40px 116px !important; }}
}}
@media (min-width:768px) and (max-width:1023px) {{
  .stMainBlockContainer {{ padding:88px 24px 40px !important; }}
}}
@media (max-width:767px) {{
  .stMainBlockContainer {{ padding:80px 16px max(24px, env(safe-area-inset-bottom)) !important; }}
  .stMainBlockContainer button[kind="primary"] {{ min-height:48px; width:100%; }}
  .st-key-ui_v2_settings_native [data-baseweb="tab-list"] {{ display:grid; grid-template-columns:1fr 1fr; }}
  .st-key-ui_v2_settings_native [data-baseweb="tab"] {{ min-width:0; white-space:normal; }}
}}
@media (prefers-reduced-motion:reduce) {{
  .stApp *, .stApp *::before, .stApp *::after {{ scroll-behavior:auto !important; transition-duration:0ms !important; }}
}}
</style>
"""


def _handle_navigation_event(st_module: Any, event: V2NavigationEvent, pages: tuple[str, ...]) -> None:
    if event.page not in pages:
        raise UIContractError("Trang điều hướng không hợp lệ.")
    if _claim_ui_event(st_module.session_state, event.event_id):
        st_module.session_state.ui_v2_active_page = event.page
        st_module.rerun()


def _handle_demo_event(
    st_module: Any,
    event: V2DemoEvent,
    *,
    case_names: tuple[str, ...],
    thresholds: Mapping[str, Any],
) -> None:
    if event.case_name not in case_names:
        raise UIContractError("Hồ sơ minh họa không hợp lệ.")
    if not _claim_ui_event(st_module.session_state, event.event_id):
        return
    st_module.session_state.ui_v2_selected_demo = event.case_name
    if event.action == "open":
        from credit_underwriting_colab import mo_ho_so_minh_hoa

        mo_ho_so_minh_hoa(st_module, event.case_name, thresholds)
        st_module.session_state.ui_v2_case_source = "Hồ sơ minh họa"
        st_module.session_state.ui_v2_error = ""
        st_module.session_state.ui_v2_warning = ""
        st_module.session_state.ui_v2_notice = f"Đã mở {event.case_name}."
    st_module.rerun()


def render_summary_native_actions(
    st_module: Any,
    *,
    result: Any,
    settings: Mapping[str, Any],
) -> None:
    """Keep download and credential-bearing actions in native Streamlit widgets."""

    from credit_underwriting_colab import (
        DINH_DANG_BAO_CAO,
        NHA_CUNG_CAP_LLM,
        _model_hop_le,
        _tim_font_pdf,
        bao_cao_markdown,
        ket_noi_llm_dang_dung,
        lam_sach_ma_ho_so,
        ngu_canh_tom_tat_ai,
        nguong_hieu_luc,
        tao_dien_giai_bang_ai,
        tom_tat_ai_hieu_luc,
    )

    connection = ket_noi_llm_dang_dung(st_module)
    ai_text = tom_tat_ai_hieu_luc(
        st_module,
        connection,
        result.ma_ho_so,
        str(settings["system_prompt"]),
    )
    deterministic = bao_cao_markdown(result)

    with st_module.container(border=True, key="ui_v2_export_actions"):
        st_module.subheader("Export actions")
        st_module.caption(
            "Báo cáo dùng nguyên dữ liệu, công thức, schema và filename hiện hành; tệp được tạo trong bộ nhớ."
        )
        if _tim_font_pdf():
            st_module.success("PDF Unicode tiếng Việt đã sẵn sàng (font được nhúng vào tệp).", icon="✅")
        else:
            st_module.error("Máy chủ chưa tìm thấy font Unicode. PDF chưa thể tạo; Word và Excel vẫn hoạt động.")
        selected_format = st_module.radio(
            "Định dạng báo cáo",
            list(DINH_DANG_BAO_CAO),
            horizontal=True,
            key="report_format",
        )
        extension, mime_type, generator = DINH_DANG_BAO_CAO[selected_format]
        try:
            report_bytes = generator(
                result,
                ai_text,
                float(nguong_hieu_luc(settings.get("nguong"))["do_tin_cay_thap"]),
            )
            st_module.download_button(
                f"Tải báo cáo {selected_format}",
                data=report_bytes,
                file_name=f"{lam_sach_ma_ho_so(result.ma_ho_so)}_bao_cao_tham_dinh.{extension}",
                mime=mime_type,
                on_click="ignore",
                type="primary",
                width="stretch",
                key="ui_v2_download_report",
            )
            if ai_text:
                st_module.caption(
                    "Bản tải xuống có kèm diễn giải AI đã tạo trong phiên. Các số liệu vẫn lấy từ kết quả Python."
                )
        except Exception as exc:
            st_module.error(f"Không thể tạo báo cáo {selected_format}: {type(exc).__name__}. {exc}")
        with st_module.expander("Dữ liệu kỹ thuật dành cho kiểm thử"):
            markdown_column, json_column = st_module.columns(2)
            markdown_column.download_button(
                "Tải Markdown",
                deterministic,
                file_name=f"{result.ma_ho_so}_tom_tat_tham_dinh.md",
                mime="text/markdown",
                on_click="ignore",
                width="stretch",
                key="ui_v2_download_markdown",
            )
            json_column.download_button(
                "Tải JSON có cấu trúc",
                json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
                file_name=f"{result.ma_ho_so}_ket_qua.json",
                mime="application/json",
                on_click="ignore",
                width="stretch",
                key="ui_v2_download_json",
            )

    with st_module.container(border=True, key="ui_v2_ai_explanation_actions"):
        st_module.subheader("AI-generated explanation · tùy chọn")
        st_module.caption(
            "Tách biệt với deterministic findings. LLM chỉ chạy khi người dùng bấm nút và không thay đổi phép tính."
        )
        api_key = connection.get("api_key", "") if connection else ""
        provider = connection.get("provider", "") if connection else ""
        model = connection.get("model", "") if connection else ""
        llm_ready = bool(connection and provider in NHA_CUNG_CAP_LLM and _model_hop_le(provider, model))
        if not connection:
            st_module.info("Hãy mở Cài đặt → Kết nối AI, xác thực khóa và chọn API Key sử dụng ngay.")
        elif llm_ready:
            st_module.success(f"Đang dùng **{NHA_CUNG_CAP_LLM[provider]['nhan']}** · model **{model}**.")
        else:
            st_module.warning("Kết nối chưa sẵn sàng. Hãy kiểm tra API Key và model trong Cài đặt.")
        if st_module.button(
            "Tạo diễn giải bằng AI",
            type="primary",
            disabled=not llm_ready,
            width="stretch",
            key="ui_v2_generate_ai_summary",
        ):
            try:
                with st_module.spinner("Đang tạo diễn giải có căn cứ…"):
                    generated_summary = tao_dien_giai_bang_ai(
                        result,
                        api_key,
                        provider,
                        model,
                        str(settings["system_prompt"]),
                    )
                    st_module.session_state.ai_summary = generated_summary
                    st_module.session_state.ai_summary_context = ngu_canh_tom_tat_ai(
                        connection,
                        result.ma_ho_so,
                        str(settings["system_prompt"]),
                    )
                    st_module.rerun()
            except (ValueError, RuntimeError) as exc:
                st_module.error(str(exc))


def _handle_evaluation_event(
    st_module: Any,
    event: V2EvaluationEvent,
    *,
    settings: Mapping[str, Any],
) -> None:
    """Run the existing deterministic evaluator once per explicit typed event."""

    if not _claim_ui_event(st_module.session_state, event.event_id):
        return
    from credit_underwriting_colab import ket_noi_llm_dang_dung
    from evaluation.evaluator import run_evaluation

    connection = ket_noi_llm_dang_dung(st_module)
    provider = str(connection.get("provider")) if connection else "not-used"
    model = str(connection.get("model")) if connection else "deterministic-saved-output"
    st_module.session_state.ui_v2_evaluation_error = ""
    try:
        with st_module.spinner("Đang chạy bộ đánh giá xác định…"):
            st_module.session_state.evaluation_report = run_evaluation(
                threshold_config=settings.get("nguong"),
                provider=provider,
                model=model,
            )
    except Exception as exc:
        st_module.session_state.ui_v2_evaluation_error = (
            f"Evaluation không thể hoàn tất: {type(exc).__name__}."
        )
    st_module.rerun()


def render_evaluation_native_downloads(st_module: Any, report: Mapping[str, Any]) -> None:
    """Reuse the exact existing JSON/CSV Evaluation exporters and filenames."""

    from evaluation.evaluator import report_to_csv, report_to_json

    reproducibility = report["reproducibility"]
    run_suffix = str(reproducibility["evaluation_run_id"]).split("-")[0]
    with st_module.container(border=True, key="ui_v2_evaluation_exports"):
        st_module.subheader("Evaluation export")
        download_columns = st_module.columns(2)
        download_columns[0].download_button(
            "Tải Evaluation JSON",
            report_to_json(dict(report)),
            file_name=f"creditlens_evaluation_{run_suffix}.json",
            mime="application/json",
            on_click="ignore",
            width="stretch",
            key="ui_v2_evaluation_json",
        )
        download_columns[1].download_button(
            "Tải Evaluation CSV",
            report_to_csv(dict(report)),
            file_name=f"creditlens_evaluation_{run_suffix}.csv",
            mime="text/csv",
            on_click="ignore",
            width="stretch",
            key="ui_v2_evaluation_csv",
        )


def render_settings_native_controls(st_module: Any, settings: dict[str, Any]) -> None:
    """Keep credentials, provider actions, thresholds and chat in native Streamlit."""

    from credit_underwriting_colab import trang_cai_dat

    with st_module.container(key="ui_v2_settings_native"):
        st_module.markdown(
            "<div id='secure-session-controls' class='cl-native-section-anchor'></div>",
            unsafe_allow_html=True,
        )
        trang_cai_dat(st_module, settings, v2_mode=True)


def chay_ung_dung_streamlit_v2(st_module: Any | None = None) -> None:
    """Chạy App Shell v2 và tám trang production trên source of truth Python."""

    if st_module is None:
        import streamlit as st_module

    from credit_underwriting_colab import (
        DEMO_CASES,
        LOGO_ICON_PATH,
        LOGO_PATH,
        NHA_CUNG_CAP_LLM,
        NHAN_DIEU_HUONG,
        NHAN_TRANG_THAI,
        PAGES,
        anh_data_uri,
        hien_thi_noi_dung_trang,
        hien_thi_uploader_ho_so,
        ket_noi_llm_dang_dung,
        khoi_tao_trang_thai_phien,
        nguong_hieu_luc,
        tom_tat_ai_hieu_luc,
    )

    page_icon: str = str(LOGO_ICON_PATH) if LOGO_ICON_PATH.exists() else "🏦"
    st_module.set_page_config(
        page_title="CreditLens",
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    khoi_tao_trang_thai_phien(st_module)
    pages = tuple(PAGES)
    case_names = tuple(DEMO_CASES)
    active_page = str(st_module.session_state.get("ui_v2_active_page") or pages[0])
    if active_page not in pages:
        active_page = pages[0]
        st_module.session_state.ui_v2_active_page = active_page
    selected_demo = str(st_module.session_state.get("ui_v2_selected_demo") or case_names[2])
    if selected_demo not in case_names:
        selected_demo = case_names[2]
        st_module.session_state.ui_v2_selected_demo = selected_demo

    settings = st_module.session_state.settings
    thresholds = nguong_hieu_luc(settings["nguong"])
    theme = theme_mode_from_settings(settings)
    renderer = get_component_renderer(st_module)
    shell = build_app_shell_view_model(
        active_page=active_page,
        pages=pages,
        page_labels=NHAN_DIEU_HUONG,
        settings=settings,
        logo_data_uri=anh_data_uri(LOGO_PATH),
        result=st_module.session_state.result,
        session_state=st_module.session_state,
        status_labels=NHAN_TRANG_THAI,
    )
    st_module.markdown(v2_host_styles(theme), unsafe_allow_html=True)
    navigation_event = render_app_shell(st_module, shell, renderer=renderer)
    if navigation_event is not None:
        _handle_navigation_event(st_module, navigation_event, pages)

    core_pages: dict[str, Literal["extraction", "analysis", "risk"]] = {
        pages[1]: "extraction",
        pages[2]: "analysis",
        pages[3]: "risk",
    }
    if active_page in core_pages:
        core_view_model = build_core_page_view_model(
            page=core_pages[active_page],
            result=st_module.session_state.result,
            docs=st_module.session_state.docs,
            thresholds=thresholds,
            theme=theme,
            processing=bool(st_module.session_state.get("ui_v2_processing", False)),
            error=str(st_module.session_state.get("ui_v2_error") or "") or None,
        )
        render_core_page(st_module, core_view_model, renderer=renderer)
        return
    if active_page == pages[4]:
        result = st_module.session_state.result
        ai_explanation: str | None = None
        if result is not None:
            connection = ket_noi_llm_dang_dung(st_module)
            current_ai_text = tom_tat_ai_hieu_luc(
                st_module,
                connection,
                result.ma_ho_so,
                str(settings["system_prompt"]),
            )
            ai_explanation = current_ai_text or None
        summary_view_model = build_summary_page_view_model(
            result=result,
            docs=st_module.session_state.docs,
            thresholds=thresholds,
            ai_explanation=ai_explanation,
            theme=theme,
            error=str(st_module.session_state.get("ui_v2_error") or "") or None,
        )
        render_summary_page(st_module, summary_view_model, renderer=renderer)
        if result is not None:
            render_summary_native_actions(st_module, result=result, settings=settings)
        return
    if active_page == pages[5]:
        render_methodology_page(
            st_module,
            build_methodology_page_view_model(theme=theme),
            renderer=renderer,
        )
        return
    if active_page == pages[6]:
        report = st_module.session_state.get("evaluation_report")
        evaluation_error = str(st_module.session_state.get("ui_v2_evaluation_error") or "") or None
        evaluation_event = render_evaluation_page(
            st_module,
            build_evaluation_page_view_model(
                report=report if isinstance(report, Mapping) else None,
                theme=theme,
                error=evaluation_error,
            ),
            renderer=renderer,
        )
        if evaluation_event is not None:
            _handle_evaluation_event(st_module, evaluation_event, settings=settings)
        if isinstance(report, Mapping):
            render_evaluation_native_downloads(st_module, report)
        return
    if active_page == pages[7]:
        settings_view_model = build_settings_page_view_model(
            settings=settings,
            session_state=st_module.session_state,
            provider_catalog=NHA_CUNG_CAP_LLM,
            thresholds=thresholds,
            result=st_module.session_state.result,
            theme=theme,
        )
        render_settings_page(st_module, settings_view_model, renderer=renderer)
        render_settings_native_controls(st_module, settings)
        return
    if active_page != pages[0]:
        hien_thi_noi_dung_trang(st_module, active_page, thresholds, settings)
        return

    demo_event: V2DemoEvent | None = None
    action_completed = False
    with st_module.container(key="ui_v2_intake_workspace"):
        upload_column, demo_column = st_module.columns([2, 1], gap="large", wrap=True)
        with upload_column.container(border=True, key="ui_v2_upload_surface"):
            st_module.subheader("Bộ hồ sơ tài liệu")
            st_module.caption(
                "Tải lên các tài liệu hiện có. Uploader Streamlit native tiếp tục xử lý file bytes và validation."
            )
            action_completed = hien_thi_uploader_ho_so(st_module, thresholds, v2_mode=True)
        with demo_column:
            demo_view_model = build_demo_panel_view_model(
                case_names=case_names,
                selected_case=selected_demo,
                case_context=shell.case_context,
                theme=theme,
                processing=bool(st_module.session_state.get("ui_v2_processing", False)),
                error=str(st_module.session_state.get("ui_v2_error") or "") or None,
            )
            demo_event = render_demo_panel(st_module, demo_view_model, renderer=renderer)
    if demo_event is not None:
        _handle_demo_event(
            st_module,
            demo_event,
            case_names=case_names,
            thresholds=thresholds,
        )
    if action_completed:
        st_module.rerun()
    render_workflow_panel(
        st_module,
        V2WorkflowPanelViewModel(
            workflow=shell.workflow,
            process_cards=shell.process_cards,
            theme=theme,
        ),
        renderer=renderer,
    )


def show_v2_fallback_notice(st_module: Any | None = None) -> None:
    """Thông báo chung, không rò chi tiết lỗi hoặc dữ liệu nhạy cảm."""

    if st_module is None:
        import streamlit as st_module

    if hasattr(st_module, "markdown"):
        st_module.markdown(
            "<style>"
            "[data-testid='stHeader'],[data-testid='stSidebar']{display:revert!important;}"
            ".stMainBlockContainer{max-width:100%!important;padding:6rem 1rem 10rem!important;}"
            "</style>",
            unsafe_allow_html=True,
        )
    st_module.warning(
        "UI v2 hiện không khả dụng; CreditLens đang dùng giao diện dự phòng ổn định.",
        icon="⚠️",
    )
