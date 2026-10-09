import { useId, useState } from "react";

import { createStatusCardEvent, type V2DomainEvent, type V2StatusCardViewModel } from "./contracts";

interface V2StatusCardProps {
  viewModel: V2StatusCardViewModel;
  onDomainEvent: (event: V2DomainEvent) => void;
}

const STATUS_LABELS: Record<V2StatusCardViewModel["status"], string> = {
  neutral: "Thông tin",
  info: "Thử nghiệm",
  success: "Đã xác nhận",
  warning: "Cần lưu ý",
  danger: "Có lỗi"
};

export function V2StatusCard({ viewModel, onDomainEvent }: V2StatusCardProps) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const headingId = useId();
  const detailsId = useId();

  return (
    <section
      className={`cl-status-card cl-status-card--${viewModel.status}`}
      data-theme={viewModel.theme}
      aria-labelledby={headingId}
    >
      <div className="cl-status-card__main">
        <span className="cl-status-card__badge">
          <span aria-hidden="true" className="cl-status-card__dot" />
          {STATUS_LABELS[viewModel.status]}
        </span>
        <h2 id={headingId}>{viewModel.title}</h2>
        <p>{viewModel.message}</p>

        {viewModel.loading ? (
          <p className="cl-status-card__feedback" role="status" aria-live="polite">
            <span className="cl-status-card__spinner" aria-hidden="true" />
            Đang chuẩn bị component…
          </p>
        ) : null}

        {viewModel.error ? (
          <p className="cl-status-card__feedback cl-status-card__feedback--error" role="alert">
            {viewModel.error}
          </p>
        ) : null}

        {viewModel.details.length > 0 ? (
          <div className="cl-status-card__disclosure">
            <button
              type="button"
              className="cl-status-card__link"
              aria-expanded={detailsOpen}
              aria-controls={detailsId}
              onClick={() => setDetailsOpen((current) => !current)}
            >
              {detailsOpen ? "Ẩn chi tiết kỹ thuật" : "Xem chi tiết kỹ thuật"}
            </button>
            {detailsOpen ? (
              <ul id={detailsId}>
                {viewModel.details.map((detail) => (
                  <li key={detail}>{detail}</li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
      </div>

      {viewModel.action_label ? (
        <div className="cl-status-card__actions">
          <button
            type="button"
            className="cl-status-card__button"
            disabled={viewModel.loading || Boolean(viewModel.error)}
            onClick={() => onDomainEvent(createStatusCardEvent())}
          >
            {viewModel.action_label}
          </button>
        </div>
      ) : null}
    </section>
  );
}
