import unittest

from src.gui.main_window import MainWindow


class WindowGeometryTests(unittest.TestCase):
    def test_restores_saved_geometry_inside_virtual_screen(self):
        result = MainWindow._clamp_window_geometry(
            {"width": 1280, "height": 820, "x": 2200, "y": 120},
            (0, 0, 3840, 2160),
        )
        self.assertEqual(result, (1280, 820, 2200, 120))

    def test_moves_window_back_when_previous_monitor_is_missing(self):
        result = MainWindow._clamp_window_geometry(
            {"width": 1280, "height": 820, "x": 2500, "y": 200},
            (0, 0, 1920, 1080),
        )
        self.assertEqual(result, (1280, 820, 640, 200))

    def test_supports_negative_coordinates_on_left_monitor(self):
        result = MainWindow._clamp_window_geometry(
            {"width": 1280, "height": 820, "x": -1600, "y": 80},
            (-1920, 0, 3840, 1080),
        )
        self.assertEqual(result, (1280, 820, -1600, 80))

    def test_preserves_deliberately_partially_visible_window(self):
        result = MainWindow._clamp_window_geometry(
            {"width": 1280, "height": 820, "x": 1750, "y": 100},
            (0, 0, 1920, 1080),
        )
        self.assertEqual(result, (1280, 820, 1750, 100))


if __name__ == "__main__":
    unittest.main()
