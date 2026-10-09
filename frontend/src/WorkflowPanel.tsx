import type { V2WorkflowPanelViewModel, WorkflowState } from "./contracts";

const STEP_ICONS: Record<WorkflowState, string> = {
  upcoming: "·",
  current: "→",
  complete: "✓",
  warning: "!",
  error: "×"
};

export function WorkflowPanel({ viewModel }: { viewModel: V2WorkflowPanelViewModel }) {
  return (
    <section className="cl-mobile-workflow" data-theme={viewModel.theme} aria-labelledby="cl-mobile-workflow-title">
      <p className="cl-page-header__eyebrow">Luồng xử lý</p>
      <h2 id="cl-mobile-workflow-title">Quy trình thẩm định</h2>
      <ol>
        {viewModel.workflow.map((step, index) => (
          <li className={`cl-workflow__step cl-workflow__step--${step.state}`} key={step.key}>
            <span className="cl-workflow__marker" aria-hidden="true">
              {step.state === "upcoming" ? index + 1 : STEP_ICONS[step.state]}
            </span>
            <div>
              <strong>{step.label}</strong>
              <p>{step.description}</p>
              <span className="cl-workflow__status" aria-current={step.state === "current" ? "step" : undefined}>
                {step.status_label}
              </span>
            </div>
          </li>
        ))}
      </ol>
      <div className="cl-mobile-workflow__cards">
        {viewModel.process_cards.map((card, index) => (
          <article className={`cl-process-card cl-process-card--${card.state}`} key={card.key}>
            <div className="cl-process-card__topline">
              <span>{String(index + 1).padStart(2, "0")}</span>
              <span>{card.state === "complete" ? "Hoàn tất" : card.state === "current" ? "Hiện tại" : card.state === "warning" ? "Cần xem xét" : card.state === "error" ? "Có lỗi" : "Sắp tới"}</span>
            </div>
            <h3>{card.label}</h3>
            <p>{card.description}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
