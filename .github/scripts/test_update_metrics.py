"""Check metric date boundaries, incomplete responses, and repeatable output."""

import copy
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from unittest.mock import patch

from update_metrics import month_windows, render_svg, search_count, write_outputs


def snapshot():
    return {"as_of": "2026-09-16", "totals": {"merged_prs": 100, "reviewed_prs": 20, "issues": 30, "stars": 40},
            "months": [{"start": str(start), "end": str(end), "merged_prs": 0}
                       for start, end in month_windows(date(2026, 9, 16))]}


class MetricsTest(unittest.TestCase):
    def test_month_windows_cross_year_and_include_partial_current_month(self):
        windows = month_windows(date(2024, 3, 10))
        self.assertEqual(len(windows), 12)
        self.assertEqual(windows[0], (date(2023, 4, 1), date(2023, 4, 30)))
        self.assertEqual(windows[-2], (date(2024, 2, 1), date(2024, 2, 29)))
        self.assertEqual(windows[-1], (date(2024, 3, 1), date(2024, 3, 10)))

    def test_incomplete_search_does_not_become_a_metric(self):
        with patch('update_metrics.fetch_json', return_value={"incomplete_results": True, "total_count": 5}):
            with self.assertRaises(RuntimeError):
                search_count('is:public is:pr')

    def test_zero_months_render_valid_svg_in_each_layout(self):
        for theme in ['light', 'dark']:
            for mobile in [False, True]:
                svg = render_svg(snapshot(), theme, mobile)
                root = ET.fromstring(svg)
                self.assertEqual(root.attrib['width'], '480' if mobile else '960')
                self.assertIn('current month partial', svg)
                self.assertNotIn('nan', svg)

    def test_repeatable_generation_preserves_curated_content_and_bad_input_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'assets').mkdir()
            readme = root/'README.md'
            readme.write_text('Introduction\n<!-- START_SECTION:metrics -->\nold\n<!-- END_SECTION:metrics -->\nProjects\n')
            write_outputs(snapshot(), root)
            self.assertTrue(readme.read_text().startswith('Introduction\n'))
            self.assertTrue(readme.read_text().endswith('\nProjects\n'))
            paths = [readme, *(root/'assets').iterdir()]
            before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths}
            write_outputs(snapshot(), root)
            self.assertEqual(before, {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths})
            invalid = copy.deepcopy(snapshot())
            invalid['totals']['stars'] = -1
            with self.assertRaises(ValueError):
                write_outputs(invalid, root)
            self.assertEqual(before, {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths})


if __name__ == '__main__':
    unittest.main()
