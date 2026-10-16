/**
 * StreamlitApp — cùng bố cục với src/App.tsx của bản AI Studio, nhưng view model của từng trang
 * do Python gửi xuống (không gọi buildCorePageViewModel/buildSummaryPageViewModel của engine.ts).
 */
import { AppShell } from "../../src/components/AppShell";
import { OverviewPage } from "../../src/components/OverviewPage";
import { CoreBusinessPage } from "../../src/components/CoreBusinessPage";
import { SummaryPage, MethodologyPage, EvaluationPage } from "../../src/components/Cluster5Pages";
import { SettingsPage } from "../../src/components/Cluster6SettingsPage";
import { LockedPageNotice, PrivacyGatewayPanel } from "../../src/components/PrivacyGatewayPanel";
import { AiExtractionPanel } from "../../src/components/AiExtractionPanel";
import { useCreditLens } from "./StreamlitContext";
import type { V3AppPayload } from "./StreamlitContext";

function PagePending({ label }: { label: string }) {
  return (
    <section className="cl-core-state cl-core-state--empty" role="status">
      <strong>{label}</strong>
      <span>Đang chờ dữ liệu từ máy chủ Python…</span>
    </section>
  );
}

export function StreamlitApp({ payload }: { payload: V3AppPayload }) {
  const { activePage, navigationItems, privacy, setActivePage } = useCreditLens();
  const item = navigationItems.find((n) => n.page === activePage);
  const goToGateway = () => setActivePage(navigationItems[0]?.page ?? "1_overview");

  const render = () => {
    if (item?.locked) {
      return (
        <LockedPageNotice
          reason={item.lock_reason || privacy?.lock_reason || "Hoàn tất Bước 0 để mở trang này."}
          onGoToGateway={goToGateway}
        />
      );
    }
    const { core, summary, methodology, evaluation } = payload.pages;
    switch (activePage) {
      case "1_overview":
        return (
          <>
            <PrivacyGatewayPanel />
            <OverviewPage />
          </>
        );
      case "2_extraction":
        return core ? (
          <>
            <AiExtractionPanel />
            <CoreBusinessPage viewModel={core} />
          </>
        ) : (
          <PagePending label="Trang phân tích" />
        );
      case "3_analysis":
      case "4_risk":
        return core ? <CoreBusinessPage viewModel={core} /> : <PagePending label="Trang phân tích" />;
      case "5_summary":
        return summary ? <SummaryPage viewModel={summary} /> : <PagePending label="Tóm tắt thẩm định" />;
      case "6_methodology":
        return methodology ? <MethodologyPage viewModel={methodology} /> : <PagePending label="Phương pháp" />;
      case "7_evaluation":
        return evaluation ? <EvaluationPage viewModel={evaluation} /> : <PagePending label="Evaluation" />;
      case "8_settings":
        return <SettingsPage />;
      default:
        return <OverviewPage />;
    }
  };

  return (
    <AppShell>
      <div key={activePage} className="cl-page-transition-wrapper">
        {render()}
      </div>
    </AppShell>
  );
}
