import type { FrontendRenderer } from "@streamlit/component-v2-lib";
import { createRoot } from "react-dom/client";

import { AppShell } from "./AppShell";
import {
  CORE_PAGE_COMPONENT,
  DEMO_COMPONENT,
  EVALUATION_PAGE_COMPONENT,
  METHODOLOGY_PAGE_COMPONENT,
  parseViewModel,
  SETTINGS_PAGE_COMPONENT,
  SHELL_COMPONENT,
  STATUS_COMPONENT,
  SUMMARY_PAGE_COMPONENT,
  WORKFLOW_COMPONENT,
  type V2UIEvent
} from "./contracts";
import { EvaluationPage, MethodologyPage, SummaryPage } from "./Cluster5Pages";
import { SettingsPage } from "./Cluster6SettingsPage";
import { CoreBusinessPage } from "./CoreBusinessPage";
import { DemoCasePanel } from "./DemoCasePanel";
import { V2StatusCard } from "./V2StatusCard";
import { WorkflowPanel } from "./WorkflowPanel";
import "./styles.css";

const render: FrontendRenderer = ({ data, parentElement, setTriggerValue }) => {
  const mountPoint = parentElement.querySelector<HTMLElement>("[data-creditlens-v2-root]");
  if (!mountPoint) return;

  const root = createRoot(mountPoint);
  try {
    const viewModel = parseViewModel(data);
    const emitDomainEvent = (event: V2UIEvent) => setTriggerValue("event", event);
    if (viewModel.component === SHELL_COMPONENT) {
      root.render(<AppShell viewModel={viewModel} onDomainEvent={emitDomainEvent} />);
    } else if (viewModel.component === DEMO_COMPONENT) {
      root.render(<DemoCasePanel viewModel={viewModel} onDomainEvent={emitDomainEvent} />);
    } else if (viewModel.component === STATUS_COMPONENT) {
      root.render(<V2StatusCard viewModel={viewModel} onDomainEvent={emitDomainEvent} />);
    } else if (viewModel.component === WORKFLOW_COMPONENT) {
      root.render(<WorkflowPanel viewModel={viewModel} />);
    } else if (viewModel.component === CORE_PAGE_COMPONENT) {
      root.render(<CoreBusinessPage viewModel={viewModel} />);
    } else if (viewModel.component === SUMMARY_PAGE_COMPONENT) {
      root.render(<SummaryPage viewModel={viewModel} />);
    } else if (viewModel.component === METHODOLOGY_PAGE_COMPONENT) {
      root.render(<MethodologyPage viewModel={viewModel} />);
    } else if (viewModel.component === EVALUATION_PAGE_COMPONENT) {
      root.render(<EvaluationPage viewModel={viewModel} onDomainEvent={emitDomainEvent} />);
    } else if (viewModel.component === SETTINGS_PAGE_COMPONENT) {
      root.render(<SettingsPage viewModel={viewModel} />);
    }
  } catch {
    root.render(
      <section className="cl-status-card cl-status-card--danger" role="alert">
        <div className="cl-status-card__main">
          <h2>Không thể hiển thị UI v2</h2>
          <p>Dữ liệu component không hợp lệ. Giao diện hiện tại vẫn an toàn để sử dụng.</p>
        </div>
      </section>
    );
  }

  return () => root.unmount();
};

export default render;
