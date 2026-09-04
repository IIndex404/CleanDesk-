import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.music_visualizer import MusicVisualizer


class FakeAudioMeter:
    def __init__(self, values):
        self.values = list(values)
        self.closed = False

    def read_peak(self):
        return self.values.pop(0) if self.values else 0.0

    def close(self):
        self.closed = True


class MusicVisualizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_spectrum_follows_audio_peak_and_releases_to_idle(self):
        meter = FakeAudioMeter([0.3] * 12 + [0.0] * 50)
        visualizer = MusicVisualizer(audio_meter=meter)
        visualizer.animation_timer.stop()
        self.assertEqual(len(visualizer._levels), 72)

        for _ in range(12):
            visualizer._advance()
        loud_average = sum(visualizer._levels) / len(visualizer._levels)
        self.assertEqual(visualizer.last_peak, 0.3)
        self.assertTrue(visualizer.music_active)
        self.assertGreater(visualizer._audio_level, 0.3)
        self.assertGreater(visualizer._activity_mix, 0.0)
        self.assertGreater(loud_average, 0.05)

        for _ in range(45):
            visualizer._advance()
        quiet_average = sum(visualizer._levels) / len(visualizer._levels)
        self.assertEqual(visualizer.last_peak, 0.0)
        self.assertFalse(visualizer.music_active)
        self.assertLess(quiet_average, loud_average)

        visualizer.close()
        self.assertTrue(meter.closed)

    def test_noise_and_brief_alert_do_not_start_animation(self):
        meter = FakeAudioMeter([0.008] * 20 + [0.7] * 3 + [0.008] * 30)
        visualizer = MusicVisualizer(audio_meter=meter)
        visualizer.animation_timer.stop()

        for _ in range(53):
            visualizer._advance()

        self.assertFalse(visualizer.music_active)
        self.assertLess(max(visualizer._levels), 0.01)
        visualizer.close()

    def test_bar_palette_runs_from_cyan_through_lilac_to_warm(self):
        left = MusicVisualizer._bar_color(0.0)
        middle = MusicVisualizer._bar_color(0.58)
        right = MusicVisualizer._bar_color(1.0)
        self.assertGreater(left.blue(), left.red())
        self.assertGreater(middle.blue(), middle.green())
        self.assertGreater(right.red(), right.blue())


if __name__ == "__main__":
    unittest.main()
