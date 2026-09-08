import unittest

from src.reports.console import BAD_COLOR
from src.reports.console import GOOD_COLOR
from src.reports.console import format_str


class FormatComparisonTests(unittest.TestCase):
    def test_higher_value_can_be_better_or_worse(self) -> None:
        self.assertEqual(format_str(0.2, 0.1, ".2%"), f"[{GOOD_COLOR}]20.00%[/{GOOD_COLOR}]")
        self.assertEqual(format_str(0.2, 0.1, ".2%", higher_better=False), f"[{BAD_COLOR}]20.00%[/{BAD_COLOR}]")

    def test_lower_value_can_be_better_or_worse(self) -> None:
        self.assertEqual(format_str(0.1, 0.2, ".2%"), f"[{BAD_COLOR}]10.00%[/{BAD_COLOR}]")
        self.assertEqual(format_str(0.1, 0.2, ".2%", higher_better=False), f"[{GOOD_COLOR}]10.00%[/{GOOD_COLOR}]")

    def test_equal_values_have_no_color(self) -> None:
        self.assertEqual(format_str(0.1, 0.1, ".2%"), "10.00%")


if __name__ == "__main__":
    unittest.main()
