from __future__ import annotations

import inspect
from pathlib import Path
import re
import unittest

from creditlens_ui_v2 import (
    render_evaluation_native_downloads,
    render_summary_native_actions,
    v2_host_styles,
)
from credit_underwriting_colab import PAGES, lam_sach_ma_ho_so


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "frontend" / "dist"


class Cluster7ProductionGates(unittest.TestCase):
    def test_all_eight_routes_remain_available_in_the_expected_order(self) -> None:
        self.assertEqual(
            PAGES,
            [
                "Trang chủ & hồ sơ",
                "Trích xuất tài liệu",
                "Phân tích tín dụng",
                "Cảnh báo rủi ro",
                "Tóm tắt thẩm định",
                "Đánh giá & phương pháp",
                "Evaluation",
                "Cài đặt",
            ],
        )

    def test_untrusted_case_ids_are_sanitized_before_html_or_filenames(self) -> None:
        hostile = '<img src=x onerror="alert(1)">../../CASE 01'
        cleaned = lam_sach_ma_ho_so(hostile)
        self.assertNotIn("<", cleaned)
        self.assertNotIn(">", cleaned)
        self.assertNotIn("/", cleaned)
        self.assertRegex(cleaned, r"^[A-Za-z0-9_-]+$")
        self.assertLessEqual(len(cleaned), 80)

    def test_v2_downloads_do_not_rerun_and_invalidate_their_media_source(self) -> None:
        summary_source = inspect.getsource(render_summary_native_actions)
        evaluation_source = inspect.getsource(render_evaluation_native_downloads)
        self.assertGreaterEqual(summary_source.count('on_click="ignore"'), 3)
        self.assertGreaterEqual(evaluation_source.count('on_click="ignore"'), 2)

    def test_native_host_css_has_mobile_focus_and_reduced_motion_guards(self) -> None:
        css = v2_host_styles("system")
        self.assertIn("@media (max-width:767px)", css)
        self.assertIn("focus-visible", css)
        self.assertIn("@media (prefers-reduced-motion:reduce)", css)
        self.assertIn("transition-duration:0ms", css)

    def test_production_bundle_is_bounded_without_sourcemaps_or_key_material(self) -> None:
        javascript_path = DIST / "creditlens-v2.js"
        stylesheet_path = DIST / "creditlens-v2.css"
        self.assertTrue(javascript_path.is_file())
        self.assertTrue(stylesheet_path.is_file())
        self.assertLess(javascript_path.stat().st_size, 500_000)
        self.assertLess(stylesheet_path.stat().st_size, 60_000)
        self.assertEqual(list(DIST.glob("*.map")), [])

        bundle = javascript_path.read_text(encoding="utf-8")
        self.assertNotIn("sourceMappingURL", bundle)
        self.assertNotRegex(bundle, re.compile(r"sk-(?:proj|ant|live|test)-[A-Za-z0-9_-]{12,}"))
        self.assertNotRegex(bundle, re.compile(r"AIza[0-9A-Za-z_-]{20,}"))


if __name__ == "__main__":
    unittest.main()
