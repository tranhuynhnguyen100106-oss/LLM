import { useCreditLens } from "./context/CreditLensContext";
import { AppShell } from "./components/AppShell";
import { OverviewPage } from "./components/OverviewPage";
import { CoreBusinessPage } from "./components/CoreBusinessPage";
import { SummaryPage, MethodologyPage, EvaluationPage } from "./components/Cluster5Pages";
import { SettingsPage } from "./components/Cluster6SettingsPage";
import {
  buildCorePageViewModel,
  buildSummaryPageViewModel,
  buildMethodologyViewModel
} from "./domain/engine";

export function App() {
  const {
    activePage,
    theme,
    result,
    thresholds,
    aiExplanation,
    evaluationReport
  } = useCreditLens();

  const renderCurrentPage = () => {
    switch (activePage) {
      case "1_overview":
        return <OverviewPage />;
      case "2_extraction":
        return (
          <CoreBusinessPage
            viewModel={buildCorePageViewModel("extraction", result, thresholds, theme)}
          />
        );
      case "3_analysis":
        return (
          <CoreBusinessPage
            viewModel={buildCorePageViewModel("analysis", result, thresholds, theme)}
          />
        );
      case "4_risk":
        return (
          <CoreBusinessPage
            viewModel={buildCorePageViewModel("risk", result, thresholds, theme)}
          />
        );
      case "5_summary":
        return (
          <SummaryPage
            viewModel={buildSummaryPageViewModel(result, aiExplanation, theme)}
          />
        );
      case "6_methodology":
        return <MethodologyPage viewModel={buildMethodologyViewModel(theme)} />;
      case "7_evaluation":
        return <EvaluationPage viewModel={evaluationReport} />;
      case "8_settings":
        return <SettingsPage />;
      default:
        return <OverviewPage />;
    }
  };

  return (
    <AppShell>
      <div key={activePage} className="cl-page-transition-wrapper">
        {renderCurrentPage()}
      </div>
    </AppShell>
  );
}

export default App;
