import unittest
from types import SimpleNamespace

from src.gui.manual_review_window import _mousewheel_scroll_units


class ManualReviewControlTests(unittest.TestCase):
    def test_mousewheel_scrolls_destination_list_in_both_directions(self):
        self.assertEqual(_mousewheel_scroll_units(SimpleNamespace(delta=120)), -8)
        self.assertEqual(_mousewheel_scroll_units(SimpleNamespace(delta=-120)), 8)

    def test_x11_mousewheel_buttons_are_supported(self):
        self.assertEqual(_mousewheel_scroll_units(SimpleNamespace(delta=0, num=4)), -8)
        self.assertEqual(_mousewheel_scroll_units(SimpleNamespace(delta=0, num=5)), 8)


if __name__ == "__main__":
    unittest.main()
