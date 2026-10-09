import { useMemo, useState } from "react";

import { Evidence, MetricGrid, RiskCard, ToneBadge } from "./CoreBusinessPage";
import {
  createEvaluationEvent,
  type V2EvaluationEvent,
  type V2EvaluationPageViewModel,
  type V2MethodologyPageViewModel,
  type V2SummaryPageViewModel
} from "./contracts";

const SUMMARY_STATE_LABELS = {
  empty: "Chưa có dữ liệu",
  success: "Sẵn sàng để xem xét",
  partial: "Thông tin chưa đầy đủ",
  error: "Không thể hiển thị"
} as const;

export function SummaryPage({ viewModel }: { viewModel: V2SummaryPageViewModel }) {
  const deterministicFindings = viewModel.findings.filter((item) => item.category === "finding");
  const reviewFindings = viewModel.findings.filter((item) => item.category !== "finding");
  const terminal = viewModel.state === "empty" || viewModel.state === "error";

  return (
    <main className="cl-support-page cl-summary-page" data-theme={viewModel.theme} id="creditlens-summary-content">
      <header className="cl-support-header">
        <div>
          <p className="cl-core-eyebrow">Decision support view</p>
          <h1>Tóm tắt thẩm định tín dụng</h1>
          <p>Deterministic findings được ưu tiên; quyết định cuối cùng thuộc về chuyên viên.</p>
        </div>
        <ToneBadge tone={viewModel.review_status_tone}>{viewModel.review_status}</ToneBadge>
      </header>
      <div
        className={`cl-core-state cl-core-state--${viewModel.state}`}
        role={viewModel.state === "error" ? "alert" : "status"}
        aria-live="polite"
      >
        <strong>{SUMMARY_STATE_LABELS[viewModel.state]}</strong>
        <span>{viewModel.state_message}</span>
      </div>

      {!terminal ? (
        <>
          <section className="cl-summary-hero" aria-labelledby="cl-case-summary-title">
            <div className="cl-summary-applicant">
              <p className="cl-core-eyebrow">Applicant / Case</p>
              <h2 id="cl-case-summary-title">{viewModel.applicant}</h2>
              <p>{viewModel.employer}</p>
              <code>{viewModel.case_id}</code>
            </div>
            <dl className="cl-summary-status-grid">
              <div>
                <dt>Review status</dt>
                <dd><ToneBadge tone={viewModel.review_status_tone}>{viewModel.review_status}</ToneBadge></dd>
              </div>
              <div>
                <dt>Mức cảnh báo cao nhất</dt>
                <dd><ToneBadge tone={viewModel.highest_alert_tone}>{viewModel.highest_alert}</ToneBadge></dd>
              </div>
              <div><dt>Số tiền đề nghị</dt><dd>{viewModel.loan_amount}</dd></div>
              <div><dt>Thời hạn</dt><dd>{viewModel.loan_term}</dd></div>
              <div className="cl-summary-status-grid__wide"><dt>Mục đích vay</dt><dd>{viewModel.loan_purpose}</dd></div>
            </dl>
          </section>

          <section className="cl-core-section" aria-labelledby="cl-summary-metrics-title">
            <div className="cl-core-section__heading">
              <div><p className="cl-core-eyebrow">Key metrics</p><h2 id="cl-summary-metrics-title">Chỉ số chính</h2></div>
              <span>{viewModel.metrics.length} giá trị từ Python</span>
            </div>
            <MetricGrid metrics={viewModel.metrics} />
          </section>

          <section className="cl-core-section" aria-labelledby="cl-top-risks-title">
            <div className="cl-core-section__heading">
              <div><p className="cl-core-eyebrow">Top risks</p><h2 id="cl-top-risks-title">Cảnh báo cần ưu tiên đọc</h2></div>
              <span>{viewModel.top_risks.length}/{viewModel.total_risk_count} cảnh báo theo thứ tự backend</span>
            </div>
            {viewModel.top_risks.length ? (
              <div className="cl-risk-grid">{viewModel.top_risks.map((risk) => <RiskCard risk={risk} key={risk.code} />)}</div>
            ) : (
              <div className="cl-core-no-risks" role="status">Không phát hiện cảnh báo trọng yếu theo các quy tắc minh họa hiện tại.</div>
            )}
          </section>

          <section className="cl-core-section" aria-labelledby="cl-findings-title">
            <div className="cl-core-section__heading">
              <div><p className="cl-core-eyebrow">Deterministic findings</p><h2 id="cl-findings-title">Kết quả xác định</h2></div>
            </div>
            <div className="cl-finding-grid">
              {deterministicFindings.map((item, index) => (
                <article className="cl-finding-card" key={`${item.title}-${index}`}>
                  <ToneBadge tone={item.tone}>{item.title}</ToneBadge>
                  <p>{item.detail}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="cl-core-section" aria-labelledby="cl-evidence-summary-title">
            <div className="cl-core-section__heading">
              <div><p className="cl-core-eyebrow">Evidence summary</p><h2 id="cl-evidence-summary-title">Phạm vi bằng chứng</h2></div>
            </div>
            <dl className="cl-summary-counts">
              <div><dt>Tài liệu</dt><dd>{viewModel.document_count}</dd></div>
              <div><dt>Trường trích xuất</dt><dd>{viewModel.extracted_field_count}</dd></div>
              <div><dt>Tham chiếu cảnh báo</dt><dd>{viewModel.evidence.length}</dd></div>
            </dl>
            <details className="cl-local-disclosure">
              <summary>Xem bằng chứng cảnh báo ({viewModel.evidence.length})</summary>
              {viewModel.evidence.length ? (
                <div className="cl-evidence-stack">
                  {viewModel.evidence.map((item, index) => <Evidence item={item} key={`${item.document}-${item.page}-${index}`} />)}
                </div>
              ) : <p className="cl-inline-empty">Không có bằng chứng rủi ro được tạo.</p>}
            </details>
          </section>

          <section className="cl-human-review-panel" aria-labelledby="cl-human-review-title">
            <div className="cl-core-section__heading">
              <div><p className="cl-core-eyebrow">Human-in-the-loop</p><h2 id="cl-human-review-title">System assessment và Human Review</h2></div>
            </div>
            <div className="cl-human-review-grid">
              <article>
                <h3>System assessment</h3>
                <p><strong>{viewModel.review_status}</strong></p>
                <p>Python cung cấp trạng thái, chỉ số, cảnh báo và bằng chứng. Hệ thống không ra quyết định khoản vay.</p>
              </article>
              <article>
                <h3>Human Review</h3>
                {reviewFindings.length ? (
                  <ul>{reviewFindings.map((item, index) => <li key={`${item.category}-${index}`}><strong>{item.title}:</strong> {item.detail}</li>)}</ul>
                ) : <p>Không có câu hỏi hoặc hạng mục bắt buộc còn thiếu trong kết quả hiện tại.</p>}
                <p className="cl-human-review-final">Chuyên viên xác minh dữ kiện, xử lý mâu thuẫn và chịu trách nhiệm về quyết định cuối cùng.</p>
              </article>
            </div>
          </section>

          {viewModel.ai_explanation ? (
            <section className="cl-ai-explanation" aria-labelledby="cl-ai-explanation-title">
              <div><span>AI-generated explanation</span><h2 id="cl-ai-explanation-title">Diễn giải bổ sung bằng AI</h2></div>
              <p>{viewModel.ai_explanation}</p>
              <small>Nội dung này không thay đổi deterministic findings, công thức hoặc review status.</small>
            </section>
          ) : null}

          <section className="cl-export-anchor" aria-labelledby="cl-export-title">
            <p className="cl-core-eyebrow">Export actions</p>
            <h2 id="cl-export-title">Xuất báo cáo</h2>
            <p>Word, Excel, PDF, Markdown và JSON tiếp tục dùng generator, schema và filename hiện hành trong khu vực tải xuống ngay bên dưới.</p>
          </section>
        </>
      ) : null}
    </main>
  );
}

export function MethodologyPage({ viewModel }: { viewModel: V2MethodologyPageViewModel }) {
  return (
    <main className="cl-support-page cl-methodology-page" data-theme={viewModel.theme} id="creditlens-methodology-content">
      <header className="cl-support-header">
        <div><p className="cl-core-eyebrow">Methodology & limitations</p><h1>Phương pháp và giới hạn</h1><p>Business definitions được giữ nguyên; giao diện chỉ tổ chức lại để dễ kiểm tra.</p></div>
      </header>
      <section className="cl-core-section" aria-labelledby="cl-method-layers-title">
        <div className="cl-core-section__heading"><div><p className="cl-core-eyebrow">Three-layer method</p><h2 id="cl-method-layers-title">Ba lớp của thuật toán</h2></div></div>
        <div className="cl-method-layer-grid">{viewModel.layers.map((layer) => <article key={layer.key}><h3>{layer.label}</h3><p>{layer.description}</p></article>)}</div>
      </section>
      <section className="cl-core-section" aria-labelledby="cl-formulas-title">
        <div className="cl-core-section__heading"><div><p className="cl-core-eyebrow">Formula cards</p><h2 id="cl-formulas-title">Công thức hiện hành</h2></div><span>6 chỉ số · Không tính trong React</span></div>
        <div className="cl-formula-grid">{viewModel.formulas.map((card) => (
          <article className="cl-formula-card" key={card.key}>
            <h3>{card.name}</h3><code>{card.formula}</code><p>{card.meaning}</p>
            <details className="cl-local-disclosure"><summary>Giới hạn</summary><p>{card.limitation}</p></details>
          </article>
        ))}</div>
      </section>
      <section className="cl-core-section" aria-labelledby="cl-pdf-capability-title">
        <div className="cl-core-section__heading"><div><p className="cl-core-eyebrow">Document capability</p><h2 id="cl-pdf-capability-title">Khả năng đọc PDF</h2></div></div>
        <div className="cl-table-scroll" tabIndex={0} aria-label="Bảng khả năng đọc PDF">
          <table className="cl-data-table" aria-label="Bảng khả năng đọc PDF"><thead><tr><th scope="col">Loại PDF</th><th scope="col">Mức hỗ trợ</th><th scope="col">Giới hạn</th></tr></thead>
            <tbody>{viewModel.capabilities.map((row) => <tr key={row.document_type}><th scope="row">{row.document_type}</th><td>{row.support_level}</td><td>{row.limitation}</td></tr>)}</tbody>
          </table>
        </div>
      </section>
      <section className="cl-self-eval-section" aria-labelledby="cl-self-eval-title">
        <div className="cl-core-section__heading"><div><p className="cl-core-eyebrow">Different questions</p><h2 id="cl-self-eval-title">SELF-TEST ≠ EVALUATION</h2></div></div>
        <div className="cl-self-eval-grid"><article><h3>SELF-TEST</h3><p>{viewModel.self_test_definition}</p></article><article><h3>EVALUATION</h3><p>{viewModel.evaluation_definition}</p></article></div>
      </section>
      <section className="cl-limitations-section" aria-labelledby="cl-limitations-title">
        <div className="cl-core-section__heading"><div><p className="cl-core-eyebrow">Limitations & Human Review</p><h2 id="cl-limitations-title">Giới hạn và trách nhiệm xem xét</h2></div></div>
        <div className="cl-limitation-grid">{viewModel.limitations.map((group) => <article key={group.title}><h3>{group.title}</h3><ul>{group.items.map((item) => <li key={item}>{item}</li>)}</ul></article>)}</div>
      </section>
    </main>
  );
}

function EvaluationTable({ title, rows }: { title: string; rows: V2EvaluationPageViewModel["risk_metrics"] }) {
  return (
    <section className="cl-core-section" aria-labelledby={`cl-${title.toLowerCase().replace(/[^a-z]+/g, "-")}`}>
      <div className="cl-core-section__heading"><h2 id={`cl-${title.toLowerCase().replace(/[^a-z]+/g, "-")}`}>{title}</h2></div>
      <div className="cl-table-scroll" tabIndex={0} aria-label={`Bảng ${title}`}>
        <table className="cl-data-table cl-metric-table" aria-label={`Bảng ${title}`}><thead><tr><th scope="col">Class</th><th scope="col">TP</th><th scope="col">FP</th><th scope="col">FN</th><th scope="col">TN</th><th scope="col">Precision</th><th scope="col">Recall</th><th scope="col">F1</th></tr></thead>
          <tbody>{rows.map((row) => <tr key={row.name}><th scope="row">{row.name}</th><td>{row.tp}</td><td>{row.fp}</td><td>{row.fn}</td><td>{row.tn ?? "N/A"}</td><td>{row.precision}</td><td>{row.recall}</td><td>{row.f1}</td></tr>)}</tbody>
        </table>
      </div>
    </section>
  );
}

interface EvaluationPageProps {
  viewModel: V2EvaluationPageViewModel;
  onDomainEvent: (event: V2EvaluationEvent) => void;
}

export function EvaluationPage({ viewModel, onDomainEvent }: EvaluationPageProps) {
  const [runLocked, setRunLocked] = useState(false);
  const [failureType, setFailureType] = useState("all");
  const types = useMemo(() => Array.from(new Set(viewModel.failure_cases.map((item) => item.failure_type))), [viewModel.failure_cases]);
  const failures = useMemo(() => viewModel.failure_cases.filter((item) => failureType === "all" || item.failure_type === failureType), [failureType, viewModel.failure_cases]);
  const runEvaluation = () => {
    if (runLocked) return;
    setRunLocked(true);
    onDomainEvent(createEvaluationEvent());
  };
  return (
    <main className="cl-support-page cl-evaluation-page" data-theme={viewModel.theme} id="creditlens-evaluation-content">
      <header className="cl-support-header cl-evaluation-header">
        <div><p className="cl-core-eyebrow">Deterministic benchmark</p><h1>Model / Pipeline Evaluation</h1><p>Evaluation đo chất lượng hệ thống; không phải self-test và không gọi LLM.</p></div>
        <button className="cl-evaluation-run" type="button" onClick={runEvaluation} disabled={runLocked}>
          {runLocked ? "Đang chạy…" : viewModel.state === "success" ? "Run Evaluation lại" : "Run Evaluation"}
        </button>
      </header>
      <div className={`cl-core-state cl-core-state--${viewModel.state === "error" ? "error" : viewModel.state === "success" ? "success" : "empty"}`} role={viewModel.state === "error" ? "alert" : "status"} aria-live="polite">
        <strong>{viewModel.state === "success" ? "Evaluation đã sẵn sàng" : viewModel.state === "error" ? "Evaluation lỗi" : "Chưa có báo cáo"}</strong><span>{viewModel.state_message}</span>
      </div>
      {viewModel.state === "success" ? <>
        <section className="cl-eval-meta" aria-labelledby="cl-eval-meta-title"><div><p className="cl-core-eyebrow">Reproducibility</p><h2 id="cl-eval-meta-title">Dataset và lần chạy</h2></div><div className="cl-label-value-grid">{[...viewModel.metadata, ...viewModel.dataset].map((item, index) => <div key={`${item.label}-${index}`}><span>{item.label}</span><strong>{item.value}</strong></div>)}</div></section>
        <section className="cl-core-section" aria-labelledby="cl-scorecards-title"><div className="cl-core-section__heading"><div><p className="cl-core-eyebrow">Evaluation scorecards</p><h2 id="cl-scorecards-title">Kết quả chính</h2></div><span>LLM API calls: {viewModel.llm_api_calls ?? "N/A"}</span></div><div className="cl-scorecard-grid">{viewModel.scorecards.map((item) => <article key={item.key}><span>{item.label}</span><strong>{item.value_display}</strong></article>)}</div></section>
        <section className="cl-core-section" aria-labelledby="cl-field-metrics-title"><div className="cl-core-section__heading"><h2 id="cl-field-metrics-title">Extraction Accuracy · field-level</h2></div><div className="cl-table-scroll" tabIndex={0} aria-label="Bảng field-level extraction metrics"><table className="cl-data-table"><thead><tr><th scope="col">Field</th><th scope="col">Correct</th><th scope="col">Total</th><th scope="col">Accuracy</th><th scope="col">Comparison</th></tr></thead><tbody>{viewModel.field_metrics.map((row) => <tr key={row.name}><th scope="row">{row.name}</th><td>{row.correct}</td><td>{row.total}</td><td>{row.accuracy}</td><td>{row.detail}</td></tr>)}</tbody></table></div></section>
        <EvaluationTable title="Risk Precision / Recall / F1" rows={viewModel.risk_metrics} />
        <section className="cl-core-section" aria-labelledby="cl-confusion-title"><div className="cl-core-section__heading"><div><p className="cl-core-eyebrow">Status accuracy</p><h2 id="cl-confusion-title">Confusion Matrix</h2></div></div><div className="cl-table-scroll" tabIndex={0} aria-label="Confusion matrix trạng thái"><table className="cl-data-table cl-confusion-table" aria-label="Confusion matrix trạng thái"><caption>Hàng là Actual; cột là Predicted. Giá trị số là text equivalent của heatmap.</caption><thead><tr><th scope="col">Actual \ Predicted</th>{viewModel.confusion_labels.map((label) => <th scope="col" key={label}>{label}</th>)}</tr></thead><tbody>{viewModel.confusion_rows.map((row) => <tr key={row.actual}><th scope="row">{row.actual}</th>{row.predicted.map((count, index) => <td className={`${count > 0 ? "is-nonzero" : ""} ${row.actual === viewModel.confusion_labels[index] ? "is-diagonal" : ""}`} key={`${row.actual}-${viewModel.confusion_labels[index]}`}>{count}</td>)}</tr>)}</tbody></table></div></section>
        <EvaluationTable title="Status metrics by class" rows={viewModel.status_metrics} />
        <section className="cl-core-section" aria-labelledby="cl-grounding-title"><div className="cl-core-section__heading"><div><p className="cl-core-eyebrow">Saved outputs · no API</p><h2 id="cl-grounding-title">Grounding metrics</h2></div></div><div className="cl-table-scroll" tabIndex={0} aria-label="Bảng grounding metrics"><table className="cl-data-table"><thead><tr><th scope="col">Variant</th><th scope="col">Evidence coverage</th><th scope="col">Unsupported claim rate</th><th scope="col">Factual consistency</th></tr></thead><tbody>{viewModel.grounding.map((row) => <tr key={row.variant}><th scope="row">{row.variant}</th><td>{row.evidence_coverage}</td><td>{row.unsupported_claim_rate}</td><td>{row.factual_consistency}</td></tr>)}</tbody></table></div></section>
        <section className="cl-core-section" aria-labelledby="cl-baselines-title"><div className="cl-core-section__heading"><div><p className="cl-core-eyebrow">Current system vs baseline</p><h2 id="cl-baselines-title">Baseline comparison</h2></div></div><div className="cl-baseline-grid">{viewModel.baselines.map((row) => <article key={`${row.baseline}-${row.variant}`}><span>{row.baseline}</span><h3>{row.variant}</h3><dl>{row.values.map((item) => <div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>)}</dl></article>)}</div></section>
        <section className="cl-core-section" aria-labelledby="cl-processing-title"><div className="cl-core-section__heading"><h2 id="cl-processing-title">Processing time</h2></div><dl className="cl-label-value-grid">{viewModel.processing.map((item) => <div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>)}</dl></section>
        <section className="cl-core-section" aria-labelledby="cl-failures-title"><div className="cl-core-section__heading cl-core-section__heading--filters"><div><p className="cl-core-eyebrow">Failure-case report</p><h2 id="cl-failures-title">Failure cases</h2></div><span aria-live="polite">{failures.length}/{viewModel.failure_cases.length} cases</span></div><div className="cl-core-filters"><label>Failure type<select value={failureType} onChange={(event) => setFailureType(event.target.value)}><option value="all">Tất cả failure types</option>{types.map((item) => <option value={item} key={item}>{item}</option>)}</select></label></div><div className="cl-failure-grid">{failures.map((item) => <article key={item.case_id}><div><code>{item.case_id}</code><ToneBadge tone={item.status.includes("MITIGATED") || item.status.includes("EVALUATED") ? "success" : "warning"}>{item.status}</ToneBadge></div><h3>{item.failure_type}</h3><dl><div><dt>Input / Scenario</dt><dd>{item.scenario}</dd></div><div><dt>Expected</dt><dd>{item.expected}</dd></div><div><dt>Actual</dt><dd>{item.actual}</dd></div><div><dt>Probable Cause</dt><dd>{item.probable_cause}</dd></div><div><dt>Mitigation</dt><dd>{item.mitigation}</dd></div></dl></article>)}</div></section>
        <section className="cl-limitations-section" aria-labelledby="cl-eval-limitations-title"><div className="cl-core-section__heading"><h2 id="cl-eval-limitations-title">Evaluation limitations</h2></div><ul>{viewModel.limitations.map((item) => <li key={item}>{item}</li>)}</ul></section>
      </> : null}
    </main>
  );
}
