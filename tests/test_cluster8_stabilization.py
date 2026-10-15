from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Cluster8StabilizationGates(unittest.TestCase):
    def test_retired_status_card_scaffold_is_absent(self) -> None:
        python_bridge = (ROOT / "creditlens_ui_v2.py").read_text(encoding="utf-8")
        contracts = (ROOT / "frontend" / "src" / "contracts.ts").read_text(encoding="utf-8")
        index = (ROOT / "frontend" / "src" / "index.tsx").read_text(encoding="utf-8")
        styles = (ROOT / "frontend" / "src" / "styles.css").read_text(encoding="utf-8")

        self.assertNotIn("class V2StatusCardViewModel", python_bridge)
        self.assertNotIn("render_experimental_v2", python_bridge)
        self.assertNotIn("STATUS_COMPONENT", contracts)
        self.assertNotIn("V2StatusCard", index)
        self.assertNotIn(".cl-status-card", styles)

    def test_native_secondary_buttons_keep_theme_safe_contrast(self) -> None:
        bridge = (ROOT / "creditlens_ui_v2.py").read_text(encoding="utf-8")
        self.assertIn('button[kind="secondary"]', bridge)
        self.assertIn("background:var(--cl-surface) !important", bridge)
        self.assertIn("color:var(--cl-text) !important", bridge)
        self.assertIn('button[kind="secondary"] p {{ color:inherit !important; }}', bridge)

    def test_production_rollback_path_remains_available(self) -> None:
        entrypoint = (ROOT / "app.py").read_text(encoding="utf-8")
        bridge = (ROOT / "creditlens_ui_v2.py").read_text(encoding="utf-8")
        self.assertIn("if ui_v2_enabled():", entrypoint)
        self.assertIn("show_v2_fallback_notice()", entrypoint)
        self.assertIn("chay_ung_dung_streamlit()", entrypoint)
        self.assertIn('UI_V2_FLAG = "UI_V2_ENABLED"', bridge)


if __name__ == "__main__":
    unittest.main()
