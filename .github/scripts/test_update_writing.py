"""Checks for the recent writing list."""

import tempfile
import unittest
from pathlib import Path

from update_writing import END, START, render_posts, update_readme


def post(slug="a-post", day="2026-09-18", title="A post"):
    return {"slug": slug, "title": title, "date": day, "url": f"https://robertcronin.com/blog/{slug}"}


class WritingTest(unittest.TestCase):
    def test_newest_first_up_to_the_limit(self):
        posts = [post(f"post-{index}", f"2026-0{index}-01") for index in range(1, 8)]
        output = render_posts(posts)
        self.assertEqual(len(output.splitlines()), 5)
        self.assertIn("post-7", output.splitlines()[0])
        self.assertIn("1 Jul 2026", output.splitlines()[0])
        self.assertNotIn("post-2", output)

    def test_titles_cannot_inject_markdown_or_html(self):
        output = render_posts([post(title="[link](url) <img> *bold*")])
        self.assertIn(r"\[link\](url) &lt;img&gt; \*bold\*", output)

    def test_rejects_other_destinations_and_non_lists(self):
        bad = post()
        bad["url"] = "https://example.com/blog/a-post"
        with self.assertRaises(ValueError):
            render_posts([bad])
        with self.assertRaises(ValueError):
            render_posts({"posts": []})
        with self.assertRaises(ValueError):
            render_posts([])

    def test_update_is_idempotent_and_keeps_surrounding_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "README.md"
            path.write_text("Intro\n" + START + "\nold\n" + END + "\nOutro\n")
            self.assertTrue(update_readme([post()], path))
            self.assertEqual(path.read_text(), "Intro\n" + START + "\n" + render_posts([post()]) + "\n" + END + "\nOutro\n")
            self.assertFalse(update_readme([post()], path))


if __name__ == "__main__":
    unittest.main()
