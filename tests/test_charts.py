import unittest

from src.reports.charts import C_LOSS, C_PROFIT, svg_bar, svg_line, svg_stacked


class ChartsTests(unittest.TestCase):
    def test_svg_line_returns_svg(self) -> None:
        out = svg_line([1, 2, 3, 4, 5], title="示例曲线")
        self.assertTrue(out.startswith("<svg"))
        self.assertIn("示例曲线", out)
        self.assertIn("</svg>", out)

    def test_svg_bar_with_colors(self) -> None:
        out = svg_bar([1, -2, 3], colors=[C_PROFIT, C_LOSS, C_PROFIT])
        self.assertIn("<rect", out)
        self.assertIn(C_PROFIT, out)
        self.assertIn(C_LOSS, out)

    def test_svg_stacked(self) -> None:
        out = svg_stacked([("a", (1, 2)), ("b", (3, 4))])
        self.assertIn("<rect", out)
        self.assertIn("</svg>", out)

    def test_empty_series_safe(self) -> None:
        self.assertEqual(svg_line([]), "")
        self.assertEqual(svg_bar([]), "")
        self.assertEqual(svg_stacked([]), "")
