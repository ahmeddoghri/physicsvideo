import tempfile
import unittest
from pathlib import Path

from physicsvideo.core import DEMO, analyze, render_video


class PhysicsVideoTests(unittest.TestCase):
    def test_demo_detects_all_fault_scenarios(self):
        result = analyze(DEMO)
        self.assertEqual(result["violations_detected"], 4)
        self.assertEqual(result["false_positives"], 0)
        self.assertEqual(result["accuracy"], 1.0)

    def test_violation_codes_are_specific(self):
        result = analyze(DEMO)
        codes = {finding["code"] for report in result["reports"] for finding in report["violations"]}
        self.assertTrue({"gravity_violation", "teleport", "object_permanence_gap", "collision_pass_through"}.issubset(codes))

    def test_control_scenario_passes(self):
        report = analyze(DEMO)["reports"][0]
        self.assertFalse(report["predicted_violation"])

    def test_renders_real_mp4(self):
        import cv2
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scenarios.mp4"
            render_video(DEMO, path)
            capture = cv2.VideoCapture(str(path))
            frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            capture.release()
        self.assertEqual(frames, 48)


if __name__ == "__main__":
    unittest.main()
