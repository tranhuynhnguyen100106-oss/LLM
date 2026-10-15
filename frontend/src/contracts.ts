export const SCHEMA_VERSION = "1.0" as const;
export const COMPONENT_VERSION = "0.5.0" as const;
export const SHELL_COMPONENT = "app_shell" as const;
export const DEMO_COMPONENT = "demo_panel" as const;
export const WORKFLOW_COMPONENT = "workflow_panel" as const;
export const CORE_PAGE_COMPONENT = "core_business_page" as const;
export const SUMMARY_PAGE_COMPONENT = "summary_page" as const;
export const METHODOLOGY_PAGE_COMPONENT = "methodology_page" as const;
export const EVALUATION_PAGE_COMPONENT = "evaluation_page" as const;
export const SETTINGS_PAGE_COMPONENT = "settings_page" as const;

export type ThemeMode = "system" | "light" | "dark";
export type StatusTone = "neutral" | "info" | "success" | "warning" | "danger";
export type WorkflowState = "upcoming" | "current" | "complete" | "warning" | "error";
export type PageState = "empty" | "ready" | "processing" | "success" | "warning" | "error" | "disabled";
export type CorePageKind = "extraction" | "analysis" | "risk";
export type CorePageState = "empty" | "loading" | "success" | "partial" | "error";
export type SourceRole = "declared" | "observed" | "calculated" | "other";

interface ContractBase {
  schema_version: typeof SCHEMA_VERSION;
  component_version: typeof COMPONENT_VERSION;
  theme: ThemeMode;
}

export interface NavigationItem {
  page: string;
  label: string;
  group: "Hồ sơ" | "Kiểm chứng" | "Hệ thống";
  ordinal: number;
}

export interface WorkflowStep {
  key: string;
  label: string;
  description: string;
  state: WorkflowState;
  status_label: string;
}

export interface ProcessCard {
  key: string;
  label: string;
  description: string;
  state: WorkflowState;
}

export interface CaseContext {
  case_id: string | null;
  source: string | null;
  status_label: string;
  status_tone: StatusTone;
  summary: string;
}

export interface V2AppShellViewModel extends ContractBase {
  component: typeof SHELL_COMPONENT;
  active_page: string;
  navigation: NavigationItem[];
  workflow: WorkflowStep[];
  process_cards: ProcessCard[];
  case_context: CaseContext;
  logo_data_uri: string;
  overview: boolean;
  page_state: PageState;
  state_message: string;
}

export interface DemoCaseItem {
  case_name: string;
  case_code: string;
  title: string;
  description: string;
}

export interface V2DemoPanelViewModel extends ContractBase {
  component: typeof DEMO_COMPONENT;
  cases: DemoCaseItem[];
  selected_case: string;
  case_context: CaseContext;
  loading: boolean;
  error: string | null;
}

export interface V2WorkflowPanelViewModel extends ContractBase {
  component: typeof WORKFLOW_COMPONENT;
  workflow: WorkflowStep[];
  process_cards: ProcessCard[];
}

export interface EvidenceReference {
  document: string;
  field: string;
  value: string;
  page: number | null;
  excerpt: string | null;
}

export interface DocumentItem {
  name: string;
  expected_type: string;
  detected_type: string;
  pages: number;
  status: string;
  confidence: number;
  confidence_display: string;
  confidence_label: string;
  confidence_tone: StatusTone;
  type_mismatch: boolean;
}

export interface ExtractedFieldItem {
  key: string;
  label: string;
  value_display: string;
  raw_value: string | number | boolean | null;
  source: string;
  source_role: SourceRole;
  page: number | null;
  confidence: number;
  confidence_display: string;
  confidence_label: string;
  confidence_tone: StatusTone;
  status: string;
  evidence: EvidenceReference | null;
}

export interface ComparisonValue {
  role: Exclude<SourceRole, "other">;
  label: string;
  value_display: string;
  source: string;
}

export interface CrossDocumentComparison {
  title: string;
  values: ComparisonValue[];
  difference_display: string;
  status: string;
  status_tone: StatusTone;
}

export interface MetricItem {
  key: string;
  label: string;
  value_display: string;
  raw_value: string | number | boolean | null;
  reference: string;
  status: string;
  status_tone: StatusTone;
  formula: string;
  note: string;
  source_role: "calculated";
}

export interface ThresholdReference {
  key: string;
  label: string;
  value: number;
  value_display: string;
  relation: "above" | "below";
}

export interface RiskItem {
  code: string;
  name: string;
  severity: "HIGH" | "MEDIUM" | "LOW" | "INFO";
  severity_label: string;
  severity_tone: Exclude<StatusTone, "success">;
  description: string;
  difference: string | null;
  evidence: EvidenceReference[];
}

export interface V2CorePageViewModel extends ContractBase {
  component: typeof CORE_PAGE_COMPONENT;
  page: CorePageKind;
  title: string;
  subtitle: string;
  state: CorePageState;
  state_message: string;
  documents: DocumentItem[];
  fields: ExtractedFieldItem[];
  comparisons: CrossDocumentComparison[];
  metrics: MetricItem[];
  thresholds: ThresholdReference[];
  risks: RiskItem[];
  case_status: string | null;
}

export interface FindingItem {
  category: "finding" | "missing" | "verification";
  title: string;
  detail: string;
  tone: StatusTone;
}

export interface V2SummaryPageViewModel extends ContractBase {
  component: typeof SUMMARY_PAGE_COMPONENT;
  state: "empty" | "success" | "partial" | "error";
  state_message: string;
  case_id: string | null;
  applicant: string;
  employer: string;
  loan_amount: string;
  loan_term: string;
  loan_purpose: string;
  review_status: string;
  review_status_tone: StatusTone;
  highest_alert: string;
  highest_alert_tone: Exclude<StatusTone, "success">;
  metrics: MetricItem[];
  top_risks: RiskItem[];
  total_risk_count: number;
  findings: FindingItem[];
  evidence: EvidenceReference[];
  document_count: number;
  extracted_field_count: number;
  ai_explanation: string | null;
}

export interface MethodologyLayer {
  key: string;
  label: string;
  description: string;
}

export interface FormulaCard {
  key: string;
  name: string;
  formula: string;
  meaning: string;
  limitation: string;
}

export interface CapabilityRow {
  document_type: string;
  support_level: string;
  limitation: string;
}

export interface LimitationGroup {
  title: string;
  items: string[];
}

export interface V2MethodologyPageViewModel extends ContractBase {
  component: typeof METHODOLOGY_PAGE_COMPONENT;
  layers: MethodologyLayer[];
  formulas: FormulaCard[];
  capabilities: CapabilityRow[];
  limitations: LimitationGroup[];
  self_test_definition: string;
  evaluation_definition: string;
}

export interface LabelValue {
  label: string;
  value: string;
}

export interface ScorecardItem {
  key: string;
  label: string;
  raw_value: string | number | boolean | null;
  value_display: string;
}

export interface FieldMetricRow {
  name: string;
  correct: number;
  total: number;
  accuracy: string;
  detail: string;
}

export interface ClassMetricRow {
  name: string;
  tp: number;
  fp: number;
  fn: number;
  tn: number | null;
  precision: string;
  recall: string;
  f1: string;
  detail: string | null;
}

export interface ConfusionRow {
  actual: string;
  predicted: number[];
}

export interface GroundingRow {
  variant: string;
  evidence_coverage: string;
  unsupported_claim_rate: string;
  factual_consistency: string;
}

export interface BaselineRow {
  baseline: string;
  variant: string;
  values: LabelValue[];
}

export interface FailureCase {
  case_id: string;
  scenario: string;
  expected: string;
  actual: string;
  failure_type: string;
  probable_cause: string;
  mitigation: string;
  status: string;
}

export interface V2EvaluationPageViewModel extends ContractBase {
  component: typeof EVALUATION_PAGE_COMPONENT;
  state: "idle" | "success" | "error";
  state_message: string;
  run_id: string | null;
  metadata: LabelValue[];
  dataset: LabelValue[];
  scorecards: ScorecardItem[];
  field_metrics: FieldMetricRow[];
  risk_metrics: ClassMetricRow[];
  status_metrics: ClassMetricRow[];
  confusion_labels: string[];
  confusion_rows: ConfusionRow[];
  grounding: GroundingRow[];
  baselines: BaselineRow[];
  processing: LabelValue[];
  failure_cases: FailureCase[];
  limitations: string[];
  llm_api_calls: number | null;
}

export interface ProviderStatus {
  provider: string;
  label: string;
  description: string;
  connected: boolean;
  active: boolean;
  model: string | null;
  model_count: number;
  status_label: string;
  status_tone: StatusTone;
}

export interface SessionThreshold {
  key: string;
  label: string;
  value: number;
  value_display: string;
}

export interface V2SettingsPageViewModel extends ContractBase {
  component: typeof SETTINGS_PAGE_COMPONENT;
  connection_state: "connected" | "not_configured" | "error";
  connection_status_label: string;
  active_provider_label: string | null;
  active_model: string | null;
  providers: ProviderStatus[];
  thresholds: SessionThreshold[];
  chat_state: "ready" | "disabled" | "error";
  chat_message_count: number;
  current_case: string | null;
  has_result: boolean;
  evaluation_ready: boolean;
  error_message: string | null;
}

export interface V2NavigationEvent {
  schema_version: typeof SCHEMA_VERSION;
  component_version: typeof COMPONENT_VERSION;
  component: typeof SHELL_COMPONENT;
  type: "navigation.select";
  action: "select";
  event_id: string;
  page: string;
}

export interface V2DemoEvent {
  schema_version: typeof SCHEMA_VERSION;
  component_version: typeof COMPONENT_VERSION;
  component: typeof DEMO_COMPONENT;
  type: "demo.select" | "demo.open";
  action: "select" | "open";
  event_id: string;
  case_name: string;
}

export interface V2EvaluationEvent {
  schema_version: typeof SCHEMA_VERSION;
  component_version: typeof COMPONENT_VERSION;
  component: typeof EVALUATION_PAGE_COMPONENT;
  type: "evaluation.run";
  action: "run";
  event_id: string;
}

export type V2UIEvent = V2NavigationEvent | V2DemoEvent | V2EvaluationEvent;
export type V2ViewModel =
  | V2AppShellViewModel
  | V2DemoPanelViewModel
  | V2WorkflowPanelViewModel
  | V2CorePageViewModel
  | V2SummaryPageViewModel
  | V2MethodologyPageViewModel
  | V2EvaluationPageViewModel
  | V2SettingsPageViewModel;

const THEMES = new Set<ThemeMode>(["system", "light", "dark"]);
const STATUS_TONES = new Set<StatusTone>(["neutral", "info", "success", "warning", "danger"]);
const WORKFLOW_STATES = new Set<WorkflowState>(["upcoming", "current", "complete", "warning", "error"]);
const PAGE_STATES = new Set<PageState>(["empty", "ready", "processing", "success", "warning", "error", "disabled"]);
const CORE_PAGE_STATES = new Set<CorePageState>(["empty", "loading", "success", "partial", "error"]);
const SOURCE_ROLES = new Set<SourceRole>(["declared", "observed", "calculated", "other"]);
const PROHIBITED_KEYS = new Set([
  "api_key",
  "apikey",
  "authorization",
  "auth",
  "credential",
  "credentials",
  "password",
  "secret",
  "token"
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normaliseKey(key: string): string {
  return key.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

function assertNoProhibitedKeys(value: unknown): void {
  if (Array.isArray(value)) {
    value.forEach(assertNoProhibitedKeys);
    return;
  }
  if (!isRecord(value)) return;
  for (const [key, nested] of Object.entries(value)) {
    if (PROHIBITED_KEYS.has(normaliseKey(key))) throw new Error("Payload contains a prohibited field.");
    assertNoProhibitedKeys(nested);
  }
}

function parseText(value: unknown, field: string, maximum: number, nullable = false): string | null {
  if (nullable && value === null) return null;
  if (typeof value !== "string") throw new Error(`${field} must be a string.`);
  const cleaned = value.trim();
  if (!cleaned || cleaned.length > maximum) throw new Error(`${field} is invalid.`);
  return cleaned;
}

function parseBase(value: Record<string, unknown>): { theme: ThemeMode } {
  if (value.schema_version !== SCHEMA_VERSION) throw new Error("Unsupported schema version.");
  if (value.component_version !== COMPONENT_VERSION) throw new Error("Unsupported component version.");
  if (typeof value.theme !== "string" || !THEMES.has(value.theme as ThemeMode)) throw new Error("Invalid theme.");
  return { theme: value.theme as ThemeMode };
}

function parseCaseContext(value: unknown): CaseContext {
  if (!isRecord(value)) throw new Error("Invalid case context.");
  if (typeof value.status_tone !== "string" || !STATUS_TONES.has(value.status_tone as StatusTone)) {
    throw new Error("Invalid case status tone.");
  }
  return {
    case_id: parseText(value.case_id, "case_id", 80, true),
    source: parseText(value.source, "source", 60, true),
    status_label: parseText(value.status_label, "status_label", 100) as string,
    status_tone: value.status_tone as StatusTone,
    summary: parseText(value.summary, "summary", 180) as string
  };
}

export function parseAppShellViewModel(value: unknown): V2AppShellViewModel {
  assertNoProhibitedKeys(value);
  if (!isRecord(value)) throw new Error("App Shell view model must be an object.");
  const base = parseBase(value);
  if (value.component !== SHELL_COMPONENT) throw new Error("Unexpected component kind.");
  if (!Array.isArray(value.navigation) || value.navigation.length !== 8) throw new Error("Invalid navigation.");
  if (!Array.isArray(value.workflow) || value.workflow.length !== 4) throw new Error("Invalid workflow.");
  if (!Array.isArray(value.process_cards) || value.process_cards.length !== 4) throw new Error("Invalid process cards.");
  if (typeof value.page_state !== "string" || !PAGE_STATES.has(value.page_state as PageState)) throw new Error("Invalid page state.");
  if (typeof value.overview !== "boolean") throw new Error("Invalid overview flag.");
  if (typeof value.logo_data_uri !== "string" || !value.logo_data_uri.startsWith("data:image/png;base64,")) {
    throw new Error("Invalid logo.");
  }

  const navigation = value.navigation.map((raw): NavigationItem => {
    if (!isRecord(raw)) throw new Error("Invalid navigation item.");
    const group = parseText(raw.group, "navigation.group", 20) as NavigationItem["group"];
    if (!["Hồ sơ", "Kiểm chứng", "Hệ thống"].includes(group)) throw new Error("Invalid navigation group.");
    if (!Number.isInteger(raw.ordinal) || Number(raw.ordinal) < 1 || Number(raw.ordinal) > 8) {
      throw new Error("Invalid navigation ordinal.");
    }
    return {
      page: parseText(raw.page, "navigation.page", 100) as string,
      label: parseText(raw.label, "navigation.label", 80) as string,
      group,
      ordinal: Number(raw.ordinal)
    };
  });
  const activePage = parseText(value.active_page, "active_page", 100) as string;
  if (!navigation.some((item) => item.page === activePage)) throw new Error("Active page is not in navigation.");

  const workflow = value.workflow.map((raw): WorkflowStep => {
    if (!isRecord(raw)) throw new Error("Invalid workflow step.");
    if (typeof raw.state !== "string" || !WORKFLOW_STATES.has(raw.state as WorkflowState)) {
      throw new Error("Invalid workflow state.");
    }
    return {
      key: parseText(raw.key, "workflow.key", 40) as string,
      label: parseText(raw.label, "workflow.label", 80) as string,
      description: parseText(raw.description, "workflow.description", 180) as string,
      state: raw.state as WorkflowState,
      status_label: parseText(raw.status_label, "workflow.status_label", 60) as string
    };
  });
  const processCards = value.process_cards.map((raw): ProcessCard => {
    if (!isRecord(raw)) throw new Error("Invalid process card.");
    if (typeof raw.state !== "string" || !WORKFLOW_STATES.has(raw.state as WorkflowState)) {
      throw new Error("Invalid process-card state.");
    }
    return {
      key: parseText(raw.key, "process_card.key", 40) as string,
      label: parseText(raw.label, "process_card.label", 80) as string,
      description: parseText(raw.description, "process_card.description", 180) as string,
      state: raw.state as WorkflowState
    };
  });

  return {
    schema_version: SCHEMA_VERSION,
    component_version: COMPONENT_VERSION,
    component: SHELL_COMPONENT,
    theme: base.theme,
    active_page: activePage,
    navigation,
    workflow,
    process_cards: processCards,
    case_context: parseCaseContext(value.case_context),
    logo_data_uri: value.logo_data_uri,
    overview: value.overview,
    page_state: value.page_state as PageState,
    state_message: parseText(value.state_message, "state_message", 300) as string
  };
}

export function parseDemoPanelViewModel(value: unknown): V2DemoPanelViewModel {
  assertNoProhibitedKeys(value);
  if (!isRecord(value)) throw new Error("Demo Panel view model must be an object.");
  const base = parseBase(value);
  if (value.component !== DEMO_COMPONENT) throw new Error("Unexpected component kind.");
  if (!Array.isArray(value.cases) || value.cases.length !== 10) throw new Error("Invalid demo cases.");
  if (typeof value.loading !== "boolean") throw new Error("Invalid loading state.");
  const cases = value.cases.map((raw): DemoCaseItem => {
    if (!isRecord(raw)) throw new Error("Invalid demo case.");
    return {
      case_name: parseText(raw.case_name, "case_name", 120) as string,
      case_code: parseText(raw.case_code, "case_code", 20) as string,
      title: parseText(raw.title, "case_title", 100) as string,
      description: parseText(raw.description, "case_description", 180) as string
    };
  });
  const selectedCase = parseText(value.selected_case, "selected_case", 120) as string;
  if (!cases.some((item) => item.case_name === selectedCase)) throw new Error("Selected case is invalid.");
  return {
    schema_version: SCHEMA_VERSION,
    component_version: COMPONENT_VERSION,
    component: DEMO_COMPONENT,
    theme: base.theme,
    cases,
    selected_case: selectedCase,
    case_context: parseCaseContext(value.case_context),
    loading: value.loading,
    error: parseText(value.error, "demo_error", 300, true)
  };
}

function parseWorkflowSteps(value: unknown): WorkflowStep[] {
  if (!Array.isArray(value) || value.length !== 4) throw new Error("Invalid workflow.");
  return value.map((raw): WorkflowStep => {
    if (!isRecord(raw)) throw new Error("Invalid workflow step.");
    if (typeof raw.state !== "string" || !WORKFLOW_STATES.has(raw.state as WorkflowState)) {
      throw new Error("Invalid workflow state.");
    }
    return {
      key: parseText(raw.key, "workflow.key", 40) as string,
      label: parseText(raw.label, "workflow.label", 80) as string,
      description: parseText(raw.description, "workflow.description", 180) as string,
      state: raw.state as WorkflowState,
      status_label: parseText(raw.status_label, "workflow.status_label", 60) as string
    };
  });
}

function parseProcessCards(value: unknown): ProcessCard[] {
  if (!Array.isArray(value) || value.length !== 4) throw new Error("Invalid process cards.");
  return value.map((raw): ProcessCard => {
    if (!isRecord(raw)) throw new Error("Invalid process card.");
    if (typeof raw.state !== "string" || !WORKFLOW_STATES.has(raw.state as WorkflowState)) {
      throw new Error("Invalid process-card state.");
    }
    return {
      key: parseText(raw.key, "process_card.key", 40) as string,
      label: parseText(raw.label, "process_card.label", 80) as string,
      description: parseText(raw.description, "process_card.description", 180) as string,
      state: raw.state as WorkflowState
    };
  });
}

export function parseWorkflowPanelViewModel(value: unknown): V2WorkflowPanelViewModel {
  assertNoProhibitedKeys(value);
  if (!isRecord(value)) throw new Error("Workflow Panel view model must be an object.");
  const base = parseBase(value);
  if (value.component !== WORKFLOW_COMPONENT) throw new Error("Unexpected component kind.");
  return {
    schema_version: SCHEMA_VERSION,
    component_version: COMPONENT_VERSION,
    component: WORKFLOW_COMPONENT,
    theme: base.theme,
    workflow: parseWorkflowSteps(value.workflow),
    process_cards: parseProcessCards(value.process_cards)
  };
}

function parseStatusTone(value: unknown, field: string): StatusTone {
  if (typeof value !== "string" || !STATUS_TONES.has(value as StatusTone)) {
    throw new Error(`${field} is invalid.`);
  }
  return value as StatusTone;
}

function parseJsonScalar(value: unknown, field: string): string | number | boolean | null {
  if (value === null || typeof value === "string" || typeof value === "boolean") return value;
  if (typeof value === "number" && Number.isFinite(value)) return value;
  throw new Error(`${field} must be a finite JSON scalar.`);
}

function parsePage(value: unknown, field: string): number | null {
  if (value === null) return null;
  if (!Number.isInteger(value) || Number(value) < 1) throw new Error(`${field} is invalid.`);
  return Number(value);
}

function parseEvidence(value: unknown): EvidenceReference {
  if (!isRecord(value)) throw new Error("Invalid evidence reference.");
  return {
    document: parseText(value.document, "evidence.document", 180) as string,
    field: parseText(value.field, "evidence.field", 120) as string,
    value: parseText(value.value, "evidence.value", 300) as string,
    page: parsePage(value.page, "evidence.page"),
    excerpt: parseText(value.excerpt, "evidence.excerpt", 1000, true)
  };
}

function parseMetricItem(raw: unknown): MetricItem {
  if (!isRecord(raw) || raw.source_role !== "calculated") throw new Error("Invalid metric.");
  return {
    key: parseText(raw.key, "metric.key", 80) as string,
    label: parseText(raw.label, "metric.label", 140) as string,
    value_display: parseText(raw.value_display, "metric.value_display", 120) as string,
    raw_value: parseJsonScalar(raw.raw_value, "metric.raw_value"),
    reference: parseText(raw.reference, "metric.reference", 220) as string,
    status: parseText(raw.status, "metric.status", 100) as string,
    status_tone: parseStatusTone(raw.status_tone, "metric.status_tone"),
    formula: parseText(raw.formula, "metric.formula", 300) as string,
    note: parseText(raw.note, "metric.note", 400) as string,
    source_role: "calculated"
  };
}

function parseRiskItem(raw: unknown): RiskItem {
  if (!isRecord(raw) || !["HIGH", "MEDIUM", "LOW", "INFO"].includes(String(raw.severity))) {
    throw new Error("Invalid risk item.");
  }
  const severityTone = parseStatusTone(raw.severity_tone, "risk.severity_tone");
  if (severityTone === "success") throw new Error("Invalid risk severity tone.");
  if (!Array.isArray(raw.evidence)) throw new Error("Invalid risk evidence.");
  return {
    code: parseText(raw.code, "risk.code", 40) as string,
    name: parseText(raw.name, "risk.name", 160) as string,
    severity: raw.severity as RiskItem["severity"],
    severity_label: parseText(raw.severity_label, "risk.severity_label", 80) as string,
    severity_tone: severityTone,
    description: parseText(raw.description, "risk.description", 1000) as string,
    difference: parseText(raw.difference, "risk.difference", 120, true),
    evidence: raw.evidence.map(parseEvidence)
  };
}

function parseLabelValues(value: unknown, field: string): LabelValue[] {
  if (!Array.isArray(value)) throw new Error(`${field} must be an array.`);
  return value.map((raw): LabelValue => {
    if (!isRecord(raw)) throw new Error(`Invalid ${field} item.`);
    return {
      label: parseText(raw.label, `${field}.label`, 160) as string,
      value: parseText(raw.value, `${field}.value`, 500) as string
    };
  });
}

function parseNonNegativeInteger(value: unknown, field: string): number {
  if (!Number.isInteger(value) || Number(value) < 0) throw new Error(`${field} is invalid.`);
  return Number(value);
}

function parseClassMetric(raw: unknown, field: string): ClassMetricRow {
  if (!isRecord(raw)) throw new Error(`Invalid ${field}.`);
  return {
    name: parseText(raw.name, `${field}.name`, 180) as string,
    tp: parseNonNegativeInteger(raw.tp, `${field}.tp`),
    fp: parseNonNegativeInteger(raw.fp, `${field}.fp`),
    fn: parseNonNegativeInteger(raw.fn, `${field}.fn`),
    tn: raw.tn === null ? null : parseNonNegativeInteger(raw.tn, `${field}.tn`),
    precision: parseText(raw.precision, `${field}.precision`, 40) as string,
    recall: parseText(raw.recall, `${field}.recall`, 40) as string,
    f1: parseText(raw.f1, `${field}.f1`, 40) as string,
    detail: parseText(raw.detail, `${field}.detail`, 300, true)
  };
}

export function parseCorePageViewModel(value: unknown): V2CorePageViewModel {
  assertNoProhibitedKeys(value);
  if (!isRecord(value)) throw new Error("Core page view model must be an object.");
  const base = parseBase(value);
  if (value.component !== CORE_PAGE_COMPONENT) throw new Error("Unexpected component kind.");
  if (!["extraction", "analysis", "risk"].includes(String(value.page))) throw new Error("Invalid core page.");
  if (typeof value.state !== "string" || !CORE_PAGE_STATES.has(value.state as CorePageState)) {
    throw new Error("Invalid core page state.");
  }
  if (!Array.isArray(value.documents) || value.documents.length > 20) throw new Error("Invalid documents.");
  if (!Array.isArray(value.fields) || value.fields.length > 100) throw new Error("Invalid fields.");
  if (!Array.isArray(value.comparisons) || value.comparisons.length > 8) throw new Error("Invalid comparisons.");
  if (!Array.isArray(value.metrics) || value.metrics.length > 12) throw new Error("Invalid metrics.");
  if (!Array.isArray(value.thresholds) || value.thresholds.length > 12) throw new Error("Invalid thresholds.");
  if (!Array.isArray(value.risks) || value.risks.length > 100) throw new Error("Invalid risks.");

  const documents = value.documents.map((raw): DocumentItem => {
    if (!isRecord(raw)) throw new Error("Invalid document item.");
    if (!Number.isInteger(raw.pages) || Number(raw.pages) < 0) throw new Error("Invalid document pages.");
    if (typeof raw.confidence !== "number" || !Number.isFinite(raw.confidence) || raw.confidence < 0 || raw.confidence > 1) {
      throw new Error("Invalid document confidence.");
    }
    if (typeof raw.type_mismatch !== "boolean") throw new Error("Invalid type mismatch flag.");
    return {
      name: parseText(raw.name, "document.name", 180) as string,
      expected_type: parseText(raw.expected_type, "document.expected_type", 100) as string,
      detected_type: parseText(raw.detected_type, "document.detected_type", 100) as string,
      pages: Number(raw.pages),
      status: parseText(raw.status, "document.status", 80) as string,
      confidence: raw.confidence,
      confidence_display: parseText(raw.confidence_display, "document.confidence_display", 40) as string,
      confidence_label: parseText(raw.confidence_label, "document.confidence_label", 80) as string,
      confidence_tone: parseStatusTone(raw.confidence_tone, "document.confidence_tone"),
      type_mismatch: raw.type_mismatch
    };
  });

  const fields = value.fields.map((raw): ExtractedFieldItem => {
    if (!isRecord(raw)) throw new Error("Invalid extracted field.");
    if (typeof raw.source_role !== "string" || !SOURCE_ROLES.has(raw.source_role as SourceRole)) {
      throw new Error("Invalid source role.");
    }
    if (typeof raw.confidence !== "number" || !Number.isFinite(raw.confidence) || raw.confidence < 0 || raw.confidence > 1) {
      throw new Error("Invalid field confidence.");
    }
    return {
      key: parseText(raw.key, "field.key", 80) as string,
      label: parseText(raw.label, "field.label", 160) as string,
      value_display: parseText(raw.value_display, "field.value_display", 300) as string,
      raw_value: parseJsonScalar(raw.raw_value, "field.raw_value"),
      source: parseText(raw.source, "field.source", 180) as string,
      source_role: raw.source_role as SourceRole,
      page: parsePage(raw.page, "field.page"),
      confidence: raw.confidence,
      confidence_display: parseText(raw.confidence_display, "field.confidence_display", 40) as string,
      confidence_label: parseText(raw.confidence_label, "field.confidence_label", 80) as string,
      confidence_tone: parseStatusTone(raw.confidence_tone, "field.confidence_tone"),
      status: parseText(raw.status, "field.status", 100) as string,
      evidence: raw.evidence === null ? null : parseEvidence(raw.evidence)
    };
  });

  const comparisons = value.comparisons.map((raw): CrossDocumentComparison => {
    if (!isRecord(raw) || !Array.isArray(raw.values) || raw.values.length < 2 || raw.values.length > 6) {
      throw new Error("Invalid comparison.");
    }
    const values = raw.values.map((entry): ComparisonValue => {
      if (!isRecord(entry) || !["declared", "observed", "calculated"].includes(String(entry.role))) {
        throw new Error("Invalid comparison value.");
      }
      return {
        role: entry.role as ComparisonValue["role"],
        label: parseText(entry.label, "comparison.label", 120) as string,
        value_display: parseText(entry.value_display, "comparison.value_display", 120) as string,
        source: parseText(entry.source, "comparison.source", 180) as string
      };
    });
    return {
      title: parseText(raw.title, "comparison.title", 140) as string,
      values,
      difference_display: parseText(raw.difference_display, "comparison.difference_display", 100) as string,
      status: parseText(raw.status, "comparison.status", 100) as string,
      status_tone: parseStatusTone(raw.status_tone, "comparison.status_tone")
    };
  });

  const metrics = value.metrics.map(parseMetricItem);

  const thresholds = value.thresholds.map((raw): ThresholdReference => {
    if (!isRecord(raw) || !["above", "below"].includes(String(raw.relation))) throw new Error("Invalid threshold.");
    if (typeof raw.value !== "number" || !Number.isFinite(raw.value)) throw new Error("Invalid threshold value.");
    return {
      key: parseText(raw.key, "threshold.key", 80) as string,
      label: parseText(raw.label, "threshold.label", 140) as string,
      value: raw.value,
      value_display: parseText(raw.value_display, "threshold.value_display", 80) as string,
      relation: raw.relation as ThresholdReference["relation"]
    };
  });

  const risks = value.risks.map(parseRiskItem);

  return {
    schema_version: SCHEMA_VERSION,
    component_version: COMPONENT_VERSION,
    component: CORE_PAGE_COMPONENT,
    theme: base.theme,
    page: value.page as CorePageKind,
    title: parseText(value.title, "core_page.title", 160) as string,
    subtitle: parseText(value.subtitle, "core_page.subtitle", 300) as string,
    state: value.state as CorePageState,
    state_message: parseText(value.state_message, "core_page.state_message", 300) as string,
    documents,
    fields,
    comparisons,
    metrics,
    thresholds,
    risks,
    case_status: parseText(value.case_status, "core_page.case_status", 120, true)
  };
}

export function parseSummaryPageViewModel(value: unknown): V2SummaryPageViewModel {
  assertNoProhibitedKeys(value);
  if (!isRecord(value)) throw new Error("Summary page view model must be an object.");
  const base = parseBase(value);
  if (value.component !== SUMMARY_PAGE_COMPONENT) throw new Error("Unexpected component kind.");
  if (!["empty", "success", "partial", "error"].includes(String(value.state))) {
    throw new Error("Invalid summary state.");
  }
  if (!Array.isArray(value.metrics) || value.metrics.length > 12) throw new Error("Invalid summary metrics.");
  if (!Array.isArray(value.top_risks) || value.top_risks.length > 10) throw new Error("Invalid top risks.");
  if (!Array.isArray(value.findings) || value.findings.length > 60) throw new Error("Invalid findings.");
  if (!Array.isArray(value.evidence) || value.evidence.length > 300) throw new Error("Invalid summary evidence.");
  const highestAlertTone = parseStatusTone(value.highest_alert_tone, "summary.highest_alert_tone");
  if (highestAlertTone === "success") throw new Error("Invalid highest alert tone.");
  const findings = value.findings.map((raw): FindingItem => {
    if (!isRecord(raw) || !["finding", "missing", "verification"].includes(String(raw.category))) {
      throw new Error("Invalid finding.");
    }
    return {
      category: raw.category as FindingItem["category"],
      title: parseText(raw.title, "finding.title", 160) as string,
      detail: parseText(raw.detail, "finding.detail", 1000) as string,
      tone: parseStatusTone(raw.tone, "finding.tone")
    };
  });
  return {
    schema_version: SCHEMA_VERSION,
    component_version: COMPONENT_VERSION,
    component: SUMMARY_PAGE_COMPONENT,
    theme: base.theme,
    state: value.state as V2SummaryPageViewModel["state"],
    state_message: parseText(value.state_message, "summary.state_message", 300) as string,
    case_id: parseText(value.case_id, "summary.case_id", 80, true),
    applicant: parseText(value.applicant, "summary.applicant", 180) as string,
    employer: parseText(value.employer, "summary.employer", 180) as string,
    loan_amount: parseText(value.loan_amount, "summary.loan_amount", 120) as string,
    loan_term: parseText(value.loan_term, "summary.loan_term", 120) as string,
    loan_purpose: parseText(value.loan_purpose, "summary.loan_purpose", 300) as string,
    review_status: parseText(value.review_status, "summary.review_status", 120) as string,
    review_status_tone: parseStatusTone(value.review_status_tone, "summary.review_status_tone"),
    highest_alert: parseText(value.highest_alert, "summary.highest_alert", 100) as string,
    highest_alert_tone: highestAlertTone,
    metrics: value.metrics.map(parseMetricItem),
    top_risks: value.top_risks.map(parseRiskItem),
    total_risk_count: parseNonNegativeInteger(value.total_risk_count, "summary.total_risk_count"),
    findings,
    evidence: value.evidence.map(parseEvidence),
    document_count: parseNonNegativeInteger(value.document_count, "summary.document_count"),
    extracted_field_count: parseNonNegativeInteger(value.extracted_field_count, "summary.extracted_field_count"),
    ai_explanation: parseText(value.ai_explanation, "summary.ai_explanation", 20000, true)
  };
}

export function parseMethodologyPageViewModel(value: unknown): V2MethodologyPageViewModel {
  assertNoProhibitedKeys(value);
  if (!isRecord(value)) throw new Error("Methodology view model must be an object.");
  const base = parseBase(value);
  if (value.component !== METHODOLOGY_PAGE_COMPONENT) throw new Error("Unexpected component kind.");
  if (!Array.isArray(value.layers) || value.layers.length !== 3) throw new Error("Invalid methodology layers.");
  if (!Array.isArray(value.formulas) || value.formulas.length !== 6) throw new Error("Invalid formula cards.");
  if (!Array.isArray(value.capabilities) || value.capabilities.length !== 5) throw new Error("Invalid capability rows.");
  if (!Array.isArray(value.limitations) || value.limitations.length < 1 || value.limitations.length > 8) {
    throw new Error("Invalid limitation groups.");
  }
  const layers = value.layers.map((raw): MethodologyLayer => {
    if (!isRecord(raw)) throw new Error("Invalid methodology layer.");
    return {
      key: parseText(raw.key, "methodology.layer.key", 40) as string,
      label: parseText(raw.label, "methodology.layer.label", 120) as string,
      description: parseText(raw.description, "methodology.layer.description", 1000) as string
    };
  });
  const formulas = value.formulas.map((raw): FormulaCard => {
    if (!isRecord(raw)) throw new Error("Invalid formula card.");
    return {
      key: parseText(raw.key, "formula.key", 60) as string,
      name: parseText(raw.name, "formula.name", 140) as string,
      formula: parseText(raw.formula, "formula.formula", 400) as string,
      meaning: parseText(raw.meaning, "formula.meaning", 800) as string,
      limitation: parseText(raw.limitation, "formula.limitation", 800) as string
    };
  });
  const capabilities = value.capabilities.map((raw): CapabilityRow => {
    if (!isRecord(raw)) throw new Error("Invalid capability row.");
    return {
      document_type: parseText(raw.document_type, "capability.document_type", 120) as string,
      support_level: parseText(raw.support_level, "capability.support_level", 80) as string,
      limitation: parseText(raw.limitation, "capability.limitation", 500) as string
    };
  });
  const limitations = value.limitations.map((raw): LimitationGroup => {
    if (!isRecord(raw) || !Array.isArray(raw.items) || raw.items.length < 1 || raw.items.length > 12) {
      throw new Error("Invalid limitation group.");
    }
    return {
      title: parseText(raw.title, "limitation.title", 140) as string,
      items: raw.items.map((item) => parseText(item, "limitation.item", 800) as string)
    };
  });
  return {
    schema_version: SCHEMA_VERSION,
    component_version: COMPONENT_VERSION,
    component: METHODOLOGY_PAGE_COMPONENT,
    theme: base.theme,
    layers,
    formulas,
    capabilities,
    limitations,
    self_test_definition: parseText(value.self_test_definition, "self_test_definition", 800) as string,
    evaluation_definition: parseText(value.evaluation_definition, "evaluation_definition", 800) as string
  };
}

export function parseEvaluationPageViewModel(value: unknown): V2EvaluationPageViewModel {
  assertNoProhibitedKeys(value);
  if (!isRecord(value)) throw new Error("Evaluation view model must be an object.");
  const base = parseBase(value);
  if (value.component !== EVALUATION_PAGE_COMPONENT) throw new Error("Unexpected component kind.");
  if (!["idle", "success", "error"].includes(String(value.state))) throw new Error("Invalid Evaluation state.");
  if (!Array.isArray(value.scorecards) || value.scorecards.length > 16) throw new Error("Invalid scorecards.");
  if (!Array.isArray(value.field_metrics) || !Array.isArray(value.risk_metrics) || !Array.isArray(value.status_metrics)) {
    throw new Error("Invalid Evaluation metrics.");
  }
  if (!Array.isArray(value.confusion_labels) || ![0, 3].includes(value.confusion_labels.length)) {
    throw new Error("Invalid confusion labels.");
  }
  const confusionLabels = value.confusion_labels.map((item) => parseText(item, "confusion.label", 120) as string);
  if (!Array.isArray(value.confusion_rows)) throw new Error("Invalid confusion rows.");
  const confusionRows = value.confusion_rows.map((raw): ConfusionRow => {
    if (!isRecord(raw) || !Array.isArray(raw.predicted) || raw.predicted.length !== confusionLabels.length) {
      throw new Error("Invalid confusion row.");
    }
    return {
      actual: parseText(raw.actual, "confusion.actual", 120) as string,
      predicted: raw.predicted.map((item) => parseNonNegativeInteger(item, "confusion.value"))
    };
  });
  const scorecards = value.scorecards.map((raw): ScorecardItem => {
    if (!isRecord(raw)) throw new Error("Invalid scorecard.");
    return {
      key: parseText(raw.key, "scorecard.key", 80) as string,
      label: parseText(raw.label, "scorecard.label", 160) as string,
      raw_value: parseJsonScalar(raw.raw_value, "scorecard.raw_value"),
      value_display: parseText(raw.value_display, "scorecard.value_display", 80) as string
    };
  });
  const fieldMetrics = value.field_metrics.map((raw): FieldMetricRow => {
    if (!isRecord(raw)) throw new Error("Invalid field metric.");
    const correct = parseNonNegativeInteger(raw.correct, "field_metric.correct");
    const total = parseNonNegativeInteger(raw.total, "field_metric.total");
    if (correct > total) throw new Error("Invalid field metric counts.");
    return {
      name: parseText(raw.name, "field_metric.name", 180) as string,
      correct,
      total,
      accuracy: parseText(raw.accuracy, "field_metric.accuracy", 40) as string,
      detail: parseText(raw.detail, "field_metric.detail", 200) as string
    };
  });
  if (!Array.isArray(value.grounding) || !Array.isArray(value.baselines)) throw new Error("Invalid evaluation comparisons.");
  const grounding = value.grounding.map((raw): GroundingRow => {
    if (!isRecord(raw)) throw new Error("Invalid grounding row.");
    return {
      variant: parseText(raw.variant, "grounding.variant", 160) as string,
      evidence_coverage: parseText(raw.evidence_coverage, "grounding.coverage", 40) as string,
      unsupported_claim_rate: parseText(raw.unsupported_claim_rate, "grounding.unsupported", 40) as string,
      factual_consistency: parseText(raw.factual_consistency, "grounding.consistency", 40) as string
    };
  });
  const baselines = value.baselines.map((raw): BaselineRow => {
    if (!isRecord(raw)) throw new Error("Invalid baseline row.");
    return {
      baseline: parseText(raw.baseline, "baseline.name", 220) as string,
      variant: parseText(raw.variant, "baseline.variant", 180) as string,
      values: parseLabelValues(raw.values, "baseline.values")
    };
  });
  if (!Array.isArray(value.failure_cases) || value.failure_cases.length > 100) throw new Error("Invalid failure cases.");
  const failureCases = value.failure_cases.map((raw): FailureCase => {
    if (!isRecord(raw)) throw new Error("Invalid failure case.");
    return {
      case_id: parseText(raw.case_id, "failure.case_id", 80) as string,
      scenario: parseText(raw.scenario, "failure.scenario", 800) as string,
      expected: parseText(raw.expected, "failure.expected", 1500) as string,
      actual: parseText(raw.actual, "failure.actual", 2000) as string,
      failure_type: parseText(raw.failure_type, "failure.type", 160) as string,
      probable_cause: parseText(raw.probable_cause, "failure.cause", 1000) as string,
      mitigation: parseText(raw.mitigation, "failure.mitigation", 1000) as string,
      status: parseText(raw.status, "failure.status", 100) as string
    };
  });
  if (!Array.isArray(value.limitations)) throw new Error("Invalid Evaluation limitations.");
  if (value.llm_api_calls !== null && (!Number.isInteger(value.llm_api_calls) || Number(value.llm_api_calls) < 0)) {
    throw new Error("Invalid Evaluation LLM call count.");
  }
  return {
    schema_version: SCHEMA_VERSION,
    component_version: COMPONENT_VERSION,
    component: EVALUATION_PAGE_COMPONENT,
    theme: base.theme,
    state: value.state as V2EvaluationPageViewModel["state"],
    state_message: parseText(value.state_message, "evaluation.state_message", 500) as string,
    run_id: parseText(value.run_id, "evaluation.run_id", 120, true),
    metadata: parseLabelValues(value.metadata, "evaluation.metadata"),
    dataset: parseLabelValues(value.dataset, "evaluation.dataset"),
    scorecards,
    field_metrics: fieldMetrics,
    risk_metrics: value.risk_metrics.map((raw) => parseClassMetric(raw, "risk_metric")),
    status_metrics: value.status_metrics.map((raw) => parseClassMetric(raw, "status_metric")),
    confusion_labels: confusionLabels,
    confusion_rows: confusionRows,
    grounding,
    baselines,
    processing: parseLabelValues(value.processing, "evaluation.processing"),
    failure_cases: failureCases,
    limitations: value.limitations.map((item) => parseText(item, "evaluation.limitation", 1000) as string),
    llm_api_calls: value.llm_api_calls === null ? null : Number(value.llm_api_calls)
  };
}

export function parseSettingsPageViewModel(value: unknown): V2SettingsPageViewModel {
  assertNoProhibitedKeys(value);
  if (!isRecord(value)) throw new Error("Settings view model must be an object.");
  const base = parseBase(value);
  if (value.component !== SETTINGS_PAGE_COMPONENT) throw new Error("Unexpected component kind.");
  if (!["connected", "not_configured", "error"].includes(String(value.connection_state))) {
    throw new Error("Invalid connection state.");
  }
  if (!Array.isArray(value.providers) || value.providers.length < 1 || value.providers.length > 8) {
    throw new Error("Invalid provider list.");
  }
  if (!Array.isArray(value.thresholds) || value.thresholds.length < 1 || value.thresholds.length > 12) {
    throw new Error("Invalid threshold list.");
  }
  if (!["ready", "disabled", "error"].includes(String(value.chat_state))) {
    throw new Error("Invalid chat state.");
  }
  if (typeof value.has_result !== "boolean" || typeof value.evaluation_ready !== "boolean") {
    throw new Error("Invalid session state.");
  }

  const providers = value.providers.map((raw): ProviderStatus => {
    if (!isRecord(raw)) throw new Error("Invalid provider status.");
    if (typeof raw.connected !== "boolean" || typeof raw.active !== "boolean") {
      throw new Error("Invalid provider flags.");
    }
    return {
      provider: parseText(raw.provider, "settings.provider", 40) as string,
      label: parseText(raw.label, "settings.provider.label", 120) as string,
      description: parseText(raw.description, "settings.provider.description", 300) as string,
      connected: raw.connected,
      active: raw.active,
      model: parseText(raw.model, "settings.provider.model", 160, true),
      model_count: parseNonNegativeInteger(raw.model_count, "settings.provider.model_count"),
      status_label: parseText(raw.status_label, "settings.provider.status_label", 80) as string,
      status_tone: parseStatusTone(raw.status_tone, "settings.provider.status_tone")
    };
  });
  const activeProviders = providers.filter((item) => item.active);
  if (activeProviders.length > 1 || activeProviders.some((item) => !item.connected)) {
    throw new Error("Invalid active provider state.");
  }

  const thresholds = value.thresholds.map((raw): SessionThreshold => {
    if (!isRecord(raw) || typeof raw.value !== "number" || !Number.isFinite(raw.value)) {
      throw new Error("Invalid session threshold.");
    }
    return {
      key: parseText(raw.key, "settings.threshold.key", 80) as string,
      label: parseText(raw.label, "settings.threshold.label", 160) as string,
      value: raw.value,
      value_display: parseText(raw.value_display, "settings.threshold.value_display", 80) as string
    };
  });

  return {
    schema_version: SCHEMA_VERSION,
    component_version: COMPONENT_VERSION,
    component: SETTINGS_PAGE_COMPONENT,
    theme: base.theme,
    connection_state: value.connection_state as V2SettingsPageViewModel["connection_state"],
    connection_status_label: parseText(value.connection_status_label, "settings.connection_status_label", 80) as string,
    active_provider_label: parseText(value.active_provider_label, "settings.active_provider_label", 120, true),
    active_model: parseText(value.active_model, "settings.active_model", 160, true),
    providers,
    thresholds,
    chat_state: value.chat_state as V2SettingsPageViewModel["chat_state"],
    chat_message_count: parseNonNegativeInteger(value.chat_message_count, "settings.chat_message_count"),
    current_case: parseText(value.current_case, "settings.current_case", 80, true),
    has_result: value.has_result,
    evaluation_ready: value.evaluation_ready,
    error_message: parseText(value.error_message, "settings.error_message", 300, true)
  };
}

export function parseViewModel(value: unknown): V2ViewModel {
  if (!isRecord(value)) throw new Error("View model must be an object.");
  if (value.component === SHELL_COMPONENT) return parseAppShellViewModel(value);
  if (value.component === DEMO_COMPONENT) return parseDemoPanelViewModel(value);
  if (value.component === WORKFLOW_COMPONENT) return parseWorkflowPanelViewModel(value);
  if (value.component === CORE_PAGE_COMPONENT) return parseCorePageViewModel(value);
  if (value.component === SUMMARY_PAGE_COMPONENT) return parseSummaryPageViewModel(value);
  if (value.component === METHODOLOGY_PAGE_COMPONENT) return parseMethodologyPageViewModel(value);
  if (value.component === EVALUATION_PAGE_COMPONENT) return parseEvaluationPageViewModel(value);
  if (value.component === SETTINGS_PAGE_COMPONENT) return parseSettingsPageViewModel(value);
  throw new Error("Unknown component kind.");
}

function defaultEventId(): string {
  if (typeof globalThis.crypto?.randomUUID === "function") return globalThis.crypto.randomUUID();
  return `evt_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 12)}`;
}

function eventId(eventIdFactory: () => string): string {
  const value = eventIdFactory();
  if (!/^[A-Za-z0-9_-]{8,96}$/.test(value)) throw new Error("Invalid event id.");
  return value;
}

export function createNavigationEvent(page: string, eventIdFactory: () => string = defaultEventId): V2NavigationEvent {
  return {
    schema_version: SCHEMA_VERSION,
    component_version: COMPONENT_VERSION,
    component: SHELL_COMPONENT,
    type: "navigation.select",
    action: "select",
    event_id: eventId(eventIdFactory),
    page
  };
}

export function createDemoEvent(
  action: "select" | "open",
  caseName: string,
  eventIdFactory: () => string = defaultEventId
): V2DemoEvent {
  return {
    schema_version: SCHEMA_VERSION,
    component_version: COMPONENT_VERSION,
    component: DEMO_COMPONENT,
    type: action === "select" ? "demo.select" : "demo.open",
    action,
    event_id: eventId(eventIdFactory),
    case_name: caseName
  };
}

export function createEvaluationEvent(
  eventIdFactory: () => string = defaultEventId
): V2EvaluationEvent {
  return {
    schema_version: SCHEMA_VERSION,
    component_version: COMPONENT_VERSION,
    component: EVALUATION_PAGE_COMPONENT,
    type: "evaluation.run",
    action: "run",
    event_id: eventId(eventIdFactory)
  };
}
