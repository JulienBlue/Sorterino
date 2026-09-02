import unittest

from src.gui.appearance import THEME_CONTRAST_PAIRS, contrast_ratio


class ThemeContrastTests(unittest.TestCase):
    def test_all_normal_text_pairs_reach_minimum_contrast(self):
        for name, (foregrounds, backgrounds) in THEME_CONTRAST_PAIRS.items():
            for theme, foreground, background in zip(
                ("hell", "dunkel"), foregrounds, backgrounds
            ):
                with self.subTest(pair=name, theme=theme):
                    self.assertGreaterEqual(
                        contrast_ratio(foreground, background),
                        4.5,
                    )


if __name__ == "__main__":
    unittest.main()
