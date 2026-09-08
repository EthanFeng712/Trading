import unittest

from src.reports.console import BAD_COLOR
from src.reports.console import GOOD_COLOR
from src.reports.console import format_str


class FormatComparisonTests(unittest.TestCase):
    def test_format_str_uses_comparison_direction(self) -> None:
        cases = (
            (0.2, 0.1, True, f"[{GOOD_COLOR}]20.00%[/{GOOD_COLOR}]"),
            (0.2, 0.1, False, f"[{BAD_COLOR}]20.00%[/{BAD_COLOR}]"),
            (0.1, 0.2, True, f"[{BAD_COLOR}]10.00%[/{BAD_COLOR}]"),
            (0.1, 0.2, False, f"[{GOOD_COLOR}]10.00%[/{GOOD_COLOR}]"),
            (0.1, 0.1, True, "10.00%"),
        )

        for value, benchmark, higher_better, expected in cases:
            with self.subTest(value=value, higher_better=higher_better):
                self.assertEqual(
                    format_str(value, benchmark, ".2%", higher_better),
                    expected,
                )


if __name__ == "__main__":
    unittest.main()
