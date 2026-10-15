import { useId, useState } from "react";

import { createDemoEvent, type V2DemoEvent, type V2DemoPanelViewModel } from "./contracts";

interface DemoCasePanelProps {
  viewModel: V2DemoPanelViewModel;
  onDomainEvent: (event: V2DemoEvent) => void;
}

export function DemoCasePanel({ viewModel, onDomainEvent }: DemoCasePanelProps) {
  const selectId = useId();
  const descriptionId = useId();
  const [openPending, setOpenPending] = useState(false);
  const selected = viewModel.cases.find((item) => item.case_name === viewModel.selected_case) ?? viewModel.cases[0];
  const busy = viewModel.loading || openPending;

  const openSelectedCase = () => {
    if (!selected || busy || viewModel.error) return;
    setOpenPending(true);
    onDomainEvent(createDemoEvent("open", selected.case_name));
  };

  return (
    <section className="cl-demo-panel" data-theme={viewModel.theme} aria-labelledby="cl-demo-title">
      <p className="cl-page-header__eyebrow">Luồng xác định</p>
      <h2 id="cl-demo-title">Hồ sơ minh họa</h2>
      <p className="cl-demo-panel__intro">Xem luồng sản phẩm bằng dữ liệu tổng hợp mà không gọi mô hình.</p>

      <label htmlFor={selectId}>Chọn hồ sơ</label>
      <select
        id={selectId}
        value={viewModel.selected_case}
        aria-describedby={descriptionId}
        disabled={busy}
        onChange={(event) => onDomainEvent(createDemoEvent("select", event.target.value))}
      >
        {viewModel.cases.map((item) => (
          <option value={item.case_name} key={item.case_name}>
            {item.case_name}
          </option>
        ))}
      </select>

      {selected ? (
        <article className="cl-demo-card" id={descriptionId}>
          <span>{selected.case_code}</span>
          <h3>{selected.title}</h3>
          <p>{selected.description}</p>
        </article>
      ) : null}

      {busy ? <p role="status">Đang xử lý domain action…</p> : null}
      {viewModel.error ? <p role="alert" className="cl-demo-panel__error">{viewModel.error}</p> : null}

      <button
        type="button"
        className="cl-demo-panel__action"
        disabled={busy || Boolean(viewModel.error) || !selected}
        onClick={openSelectedCase}
      >
        Mở hồ sơ minh họa
      </button>

      <div className={`cl-demo-status cl-tone--${viewModel.case_context.status_tone}`}>
        <strong>{viewModel.case_context.status_label}</strong>
        <p>{viewModel.case_context.summary}</p>
        {viewModel.case_context.case_id ? <code>{viewModel.case_context.case_id}</code> : null}
      </div>
    </section>
  );
}
