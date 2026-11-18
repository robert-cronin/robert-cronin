"""Regression checks for public activity selection and safe README updates."""

import tempfile
import unittest
from pathlib import Path

from update_prs import END, START, render_prs, update_readme


def pr(repo="org/project", number=1, date="2026-09-16", title="Improve runtime status", merged=True):
    return {
        "html_url": f"https://github.com/{repo}/pull/{number}",
        "title": title,
        "updated_at": f"{date}T01:00:00Z",
        "pull_request": {"merged_at": f"{date}T00:00:00Z" if merged else None},
    }


class ContributionsTest(unittest.TestCase):
    def test_only_merged_and_one_per_project_up_to_three(self):
        entries = [pr("org/a", 1), pr("org/a", 2, "2026-09-15"),
                   pr("org/b", 3, "2026-09-14"), pr("org/c", 4, "2026-09-13"),
                   pr("org/d", 5, "2026-09-12"), pr("org/open", merged=False)]
        output = render_prs(list(reversed(entries)))
        self.assertEqual(len(output.splitlines()), 3)
        self.assertIn("org/a/pull/1", output)
        self.assertNotIn("org/a/pull/2", output)
        self.assertNotIn("org/d", output)
        self.assertNotIn("org/open", output)

    def test_titles_cannot_inject_markdown_or_html(self):
        output = render_prs([pr(title="[link](url) <img> *bold*\nnext \\1")])
        self.assertIn(r"\[link\](url) &lt;img&gt; \*bold\* next \\1", output)
        self.assertEqual(len(output.splitlines()), 1)

    def test_update_preserves_curated_content_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "README.md"
            prefix, suffix = "# Curated introduction\n", "\nContact links\n"
            path.write_text(prefix + START + "\nold\n" + END + suffix)
            self.assertTrue(update_readme([pr()], path))
            self.assertEqual(path.read_text(), prefix + START + "\n" + render_prs([pr()]) + "\n" + END + suffix)
            timestamp = path.stat().st_mtime_ns
            self.assertFalse(update_readme([pr()], path))
            self.assertEqual(timestamp, path.stat().st_mtime_ns)

    def test_bad_markers_leave_file_unchanged(self):
        for content in ["no markers", START + START + END, END + START]:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "README.md"
                path.write_text(content)
                with self.assertRaises(ValueError):
                    update_readme([pr()], path)
                self.assertEqual(path.read_text(), content)

    def test_empty_results_preserve_existing_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "README.md"
            content = START + "\nexisting activity\n" + END
            path.write_text(content)
            with self.assertRaises(ValueError):
                update_readme([], path)
            self.assertEqual(path.read_text(), content)

    def test_rejects_unexpected_destination(self):
        entry = pr()
        entry["html_url"] = "https://example.com/project/pull/1"
        with self.assertRaises(ValueError):
            render_prs([entry])


if __name__ == "__main__":
    unittest.main()
