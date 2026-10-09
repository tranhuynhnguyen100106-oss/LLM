import { useMemo, useState } from "react";
import type { ReactNode } from "react";

import type {
  EvidenceReference,
  ExtractedFieldItem,
  RiskItem,
  SourceRole,
  StatusTone,
  V2CorePageViewModel
} from "./contracts";

const ROLE_LABELS: Record<SourceRole, string> = {
  declared: "Kê khai",
  observed: "Quan sát từ chứng từ",
  calculated: "Python tính toán",
  other: "Nguồn khác"
};

const STATE_LABELS = {
  empty: "Chưa có dữ liệu",
  loading: "Đang xử lý",
  success: "Sẵn sàng xem xét",
  partial: "Dữ liệu chưa đầy đủ",
  error: "Không thể hiển thị"
} as const;

export function ToneBadge({ tone, children }: { tone: StatusTone; children: ReactNode }) {
  return <span className={`cl-core-badge cl-tone--${tone}`}>{children}</span>;
}

export function RoleBadge({ role }: { role: SourceRole }) {
  return <span className={`cl-source-role cl-source-role--${role}`}>{ROLE_LABELS[role]}</span>;
}

export function Evidence({ item }: { item: EvidenceReference }) {
  return (
    <div className="cl-evidence-card">
      <div className="cl-evidence-card__path">
        <strong>{item.document}</strong>
        <span>{item.page === null ? "Trang không xác định" : `Trang ${item.page}`}</span>
      </div>
      <dl>
        <div>
          <dt>Trường</dt>
          <dd>{item.field}</dd>
        </div>
        <div>
          <dt>Giá trị</dt>
          <dd>{item.value}</dd>
        </div>
      </dl>
      {item.excerpt ? <blockquote>{item.excerpt}</blockquote> : <p>Không có trích đoạn nguồn.</p>}
    </div>
  );
}

function ExtractionField({ field }: { field: ExtractedFieldItem }) {
  return (
    <article className="cl-field-card">
      <div className="cl-field-card__identity">
        <div>
          <span className="cl-field-card__key">{field.key}</span>
          <h3>{field.label}</h3>
        </div>
        <RoleBadge role={field.source_role} />
      </div>
      <p className="cl-field-card__value">{field.value_display}</p>
      <dl className="cl-field-card__meta">
        <div>
          <dt>Confidence</dt>
          <dd>
            <ToneBadge tone={field.confidence_tone}>
              {field.confidence_display} · {field.confidence_label}
            </ToneBadge>
          </dd>
        </div>
        <div>
          <dt>Tài liệu</dt>
          <dd>{field.source}</dd>
        </div>
        <div>
          <dt>Trang / nguồn</dt>
          <dd>{field.page === null ? "Không xác định" : `Trang ${field.page}`}</dd>
        </div>
        <div>
          <dt>Trạng thái</dt>
          <dd>{field.status}</dd>
        </div>
      </dl>
      {field.evidence ? (
        <details className="cl-local-disclosure">
          <summary>Xem bằng chứng nguồn</summary>
          <Evidence item={field.evidence} />
        </details>
      ) : (
        <p className="cl-field-card__no-evidence">Chưa có bằng chứng tham chiếu.</p>
      )}
    </article>
  );
}

function ExtractionPage({ viewModel }: { viewModel: V2CorePageViewModel }) {
  const [sourceRole, setSourceRole] = useState<"all" | SourceRole>("all");
  const [confidenceTone, setConfidenceTone] = useState<"all" | StatusTone>("all");
  const filteredFields = useMemo(
    () =>
      viewModel.fields.filter(
        (field) =>
          (sourceRole === "all" || field.source_role === sourceRole) &&
          (confidenceTone === "all" || field.confidence_tone === confidenceTone)
      ),
    [confidenceTone, sourceRole, viewModel.fields]
  );

  return (
    <>
      <section className="cl-core-section" aria-labelledby="cl-documents-title">
        <div className="cl-core-section__heading">
          <div>
            <p className="cl-core-eyebrow">Document status</p>
            <h2 id="cl-documents-title">Danh mục tài liệu</h2>
          </div>
          <span>{viewModel.documents.length} tài liệu</span>
        </div>
        {viewModel.documents.length ? (
          <div className="cl-document-grid">
            {viewModel.documents.map((document) => (
              <article className="cl-document-card" key={`${document.name}-${document.expected_type}`}>
                <div className="cl-document-card__topline">
                  <h3>{document.name}</h3>
                  <ToneBadge tone={document.confidence_tone}>{document.status}</ToneBadge>
                </div>
                <dl>
                  <div><dt>Loại dự kiến</dt><dd>{document.expected_type}</dd></div>
                  <div><dt>Loại nhận diện</dt><dd>{document.detected_type}</dd></div>
                  <div><dt>Số trang</dt><dd>{document.pages}</dd></div>
                  <div>
                    <dt>Confidence</dt>
                    <dd>{document.confidence_display} · {document.confidence_label}</dd>
                  </div>
                </dl>
                {document.type_mismatch ? <p className="cl-document-card__warning">Sai lệch loại — cần xác minh</p> : null}
              </article>
            ))}
          </div>
        ) : (
          <p className="cl-inline-empty">Phiên hiện tại không có metadata tài liệu.</p>
        )}
      </section>

      <section className="cl-core-section" aria-labelledby="cl-fields-title">
        <div className="cl-core-section__heading cl-core-section__heading--filters">
          <div>
            <p className="cl-core-eyebrow">Extracted fields</p>
            <h2 id="cl-fields-title">Dữ kiện đã chuẩn hóa</h2>
          </div>
          <span aria-live="polite">{filteredFields.length}/{viewModel.fields.length} trường</span>
        </div>
        <div className="cl-core-filters" aria-label="Bộ lọc dữ kiện cục bộ">
          <label>
            Nguồn dữ liệu
            <select value={sourceRole} onChange={(event) => setSourceRole(event.target.value as typeof sourceRole)}>
              <option value="all">Tất cả nguồn</option>
              <option value="declared">Kê khai</option>
              <option value="observed">Quan sát từ chứng từ</option>
              <option value="calculated">Python tính toán</option>
              <option value="other">Nguồn khác</option>
            </select>
          </label>
          <label>
            Trạng thái confidence
            <select
              value={confidenceTone}
              onChange={(event) => setConfidenceTone(event.target.value as typeof confidenceTone)}
            >
              <option value="all">Tất cả trạng thái</option>
              <option value="success">Tin cậy cao</option>
              <option value="warning">Cần đối chiếu</option>
              <option value="danger">Cần xác minh</option>
              <option value="neutral">Thiếu dữ liệu</option>
            </select>
          </label>
        </div>
        {filteredFields.length ? (
          <div className="cl-field-grid">{filteredFields.map((field) => <ExtractionField field={field} key={field.key} />)}</div>
        ) : (
          <p className="cl-inline-empty">Không có trường phù hợp bộ lọc hiện tại.</p>
        )}
      </section>
    </>
  );
}

function AnalysisPage({ viewModel }: { viewModel: V2CorePageViewModel }) {
  return (
    <>
      <section className="cl-core-section" aria-labelledby="cl-comparison-title">
        <div className="cl-core-section__heading">
          <div>
            <p className="cl-core-eyebrow">Cross-document comparison</p>
            <h2 id="cl-comparison-title">Đối chiếu dữ liệu</h2>
          </div>
        </div>
        <div className="cl-comparison-grid">
          {viewModel.comparisons.map((comparison) => (
            <article className="cl-comparison-card" key={comparison.title}>
              <div className="cl-comparison-card__topline">
                <h3>{comparison.title}</h3>
                <ToneBadge tone={comparison.status_tone}>{comparison.status}</ToneBadge>
              </div>
              <div className="cl-comparison-values">
                {comparison.values.map((value, index) => (
                  <div className="cl-comparison-value" key={`${value.role}-${value.label}-${index}`}>
                    <RoleBadge role={value.role} />
                    <span>{value.label}</span>
                    <strong>{value.value_display}</strong>
                    <small>{value.source}</small>
                  </div>
                ))}
              </div>
              <div className="cl-comparison-card__difference">
                <span>Chênh lệch từ Python</span>
                <strong>{comparison.difference_display}</strong>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="cl-core-section" aria-labelledby="cl-metrics-title">
        <div className="cl-core-section__heading">
          <div>
            <p className="cl-core-eyebrow">Financial metrics</p>
            <h2 id="cl-metrics-title">Chỉ số tín dụng</h2>
          </div>
          <span>{viewModel.metrics.length} chỉ số do Python trả về</span>
        </div>
        <MetricGrid metrics={viewModel.metrics} />
      </section>

      <section className="cl-core-section" aria-labelledby="cl-thresholds-title">
        <div className="cl-core-section__heading">
          <div>
            <p className="cl-core-eyebrow">Current configuration</p>
            <h2 id="cl-thresholds-title">Ngưỡng minh họa hiện hành</h2>
          </div>
        </div>
        <p className="cl-core-disclaimer">Các ngưỡng này chỉ phục vụ minh họa, không phải chính sách cấp tín dụng của ngân hàng.</p>
        <div className="cl-threshold-list">
          {viewModel.thresholds.map((threshold) => (
            <div key={threshold.key}>
              <span>{threshold.label}</span>
              <strong>{threshold.relation === "above" ? ">" : "<"} {threshold.value_display}</strong>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

const SEVERITY_ORDER: RiskItem["severity"][] = ["HIGH", "MEDIUM", "LOW", "INFO"];

export function MetricGrid({ metrics }: { metrics: V2CorePageViewModel["metrics"] }) {
  return (
    <div className="cl-metric-grid">
      {metrics.map((metric) => (
        <article className={`cl-metric-card cl-metric-card--${metric.status_tone}`} key={metric.key}>
          <div className="cl-metric-card__topline">
            <RoleBadge role={metric.source_role} />
            <ToneBadge tone={metric.status_tone}>{metric.status}</ToneBadge>
          </div>
          <h3>{metric.label}</h3>
          <p className="cl-metric-card__value">{metric.value_display}</p>
          <p className="cl-metric-card__reference">{metric.reference}</p>
          <details className="cl-local-disclosure">
            <summary>Xem công thức và diễn giải</summary>
            <dl className="cl-metric-card__details">
              <div><dt>Công thức</dt><dd>{metric.formula}</dd></div>
              <div><dt>Diễn giải</dt><dd>{metric.note}</dd></div>
            </dl>
          </details>
        </article>
      ))}
    </div>
  );
}

export function RiskCard({ risk }: { risk: RiskItem }) {
  return (
    <article className={`cl-risk-card cl-risk-card--${risk.severity_tone}`}>
      <div className="cl-risk-card__topline">
        <span className="cl-risk-card__code">{risk.code}</span>
        <ToneBadge tone={risk.severity_tone}>{risk.severity} · {risk.severity_label}</ToneBadge>
      </div>
      <h3>{risk.name}</h3>
      <p>{risk.description}</p>
      {risk.difference ? (
        <div className="cl-risk-card__difference"><span>Chênh lệch liên quan</span><strong>{risk.difference}</strong></div>
      ) : null}
      <details className="cl-local-disclosure">
        <summary>Bằng chứng ({risk.evidence.length})</summary>
        {risk.evidence.length ? (
          <div className="cl-evidence-stack">{risk.evidence.map((item, index) => <Evidence item={item} key={`${item.document}-${item.page}-${index}`} />)}</div>
        ) : (
          <p className="cl-inline-empty">Thông tin chưa đủ — không có bằng chứng hỗ trợ.</p>
        )}
      </details>
    </article>
  );
}

function RiskPage({ viewModel }: { viewModel: V2CorePageViewModel }) {
  if (!viewModel.risks.length) {
    return <div className="cl-core-no-risks" role="status">Không phát hiện mâu thuẫn trọng yếu theo các quy tắc minh họa hiện tại.</div>;
  }
  return (
    <div className="cl-risk-groups">
      {SEVERITY_ORDER.map((severity) => {
        const risks = viewModel.risks.filter((risk) => risk.severity === severity);
        if (!risks.length) return null;
        return (
          <details className="cl-risk-group" key={severity} open>
            <summary>
              <span>Mức độ {risks[0]?.severity_label}</span>
              <strong>{risks.length}</strong>
            </summary>
            <div className="cl-risk-grid">{risks.map((risk) => <RiskCard risk={risk} key={risk.code} />)}</div>
          </details>
        );
      })}
    </div>
  );
}

export function CoreBusinessPage({ viewModel }: { viewModel: V2CorePageViewModel }) {
  const isTerminalState = viewModel.state === "empty" || viewModel.state === "loading" || viewModel.state === "error";
  return (
    <main className="cl-core-page" data-theme={viewModel.theme} data-page={viewModel.page} id="creditlens-core-content">
      <header className="cl-core-header">
        <div>
          <p className="cl-core-eyebrow">CreditLens · Core business page</p>
          <h1>{viewModel.title}</h1>
          <p>{viewModel.subtitle}</p>
        </div>
        {viewModel.case_status ? <ToneBadge tone={viewModel.state === "partial" ? "warning" : "info"}>{viewModel.case_status}</ToneBadge> : null}
      </header>
      <div
        className={`cl-core-state cl-core-state--${viewModel.state}`}
        role={viewModel.state === "error" ? "alert" : "status"}
        aria-live="polite"
      >
        {viewModel.state === "loading" ? <span className="cl-core-spinner" aria-hidden="true" /> : null}
        <strong>{STATE_LABELS[viewModel.state]}</strong>
        <span>{viewModel.state_message}</span>
      </div>
      {viewModel.state === "loading" ? (
        <div className="cl-core-skeleton" aria-hidden="true"><span /><span /><span /></div>
      ) : null}
      {!isTerminalState && viewModel.page === "extraction" ? <ExtractionPage viewModel={viewModel} /> : null}
      {!isTerminalState && viewModel.page === "analysis" ? <AnalysisPage viewModel={viewModel} /> : null}
      {!isTerminalState && viewModel.page === "risk" ? <RiskPage viewModel={viewModel} /> : null}
    </main>
  );
}
