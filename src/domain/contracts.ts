export const SCHEMA_VERSION = "1.0" as const;
export const COMPONENT_VERSION = "0.5.0" as const;

export type ThemeMode = "system" | "light" | "dark";
export type MotionLevel = "full" | "light" | "off";
export type StatusTone = "neutral" | "info" | "success" | "warning" | "danger";
export type WorkflowState = "upcoming" | "current" | "complete" | "warning" | "error";
export type PageState = "empty" | "ready" | "processing" | "success" | "warning" | "error" | "disabled";
export type CorePageKind = "extraction" | "analysis" | "risk";
export type CorePageState = "empty" | "loading" | "success" | "partial" | "error";
export type SourceRole = "declared" | "observed" | "calculated" | "other";

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

export interface V2AppShellViewModel {
  theme: ThemeMode;
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

export interface V2DemoPanelViewModel {
  theme: ThemeMode;
  cases: DemoCaseItem[];
  selected_case: string;
  case_context: CaseContext;
  loading: boolean;
  error: string | null;
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

export interface V2CorePageViewModel {
  theme: ThemeMode;
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

export interface V2SummaryPageViewModel {
  theme: ThemeMode;
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

export interface V2MethodologyPageViewModel {
  theme: ThemeMode;
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

export interface V2EvaluationPageViewModel {
  theme: ThemeMode;
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

export interface V2SettingsPageViewModel {
  theme: ThemeMode;
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
  kind: "navigation";
  page: string;
  event_id: string;
}

export interface V2DemoEvent {
  kind: "demo";
  action: "select" | "open";
  case_name: string;
  event_id: string;
}

export interface V2EvaluationEvent {
  kind: "evaluation";
  action: "run";
  event_id: string;
}

export function createNavigationEvent(page: string): V2NavigationEvent {
  return {
    kind: "navigation",
    page,
    event_id: `nav-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
  };
}

export function createDemoEvent(action: "select" | "open", caseName: string): V2DemoEvent {
  return {
    kind: "demo",
    action,
    case_name: caseName,
    event_id: `demo-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
  };
}

export function createEvaluationEvent(): V2EvaluationEvent {
  return {
    kind: "evaluation",
    action: "run",
    event_id: `eval-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
  };
}
