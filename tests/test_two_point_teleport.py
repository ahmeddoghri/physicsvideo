import unittest

from physicsvideo.core import DEMO, analyze


class TwoPointTeleportTest(unittest.TestCase):
    """The teleport threshold was derived from median_step of ALL steps in a
    track, including the step under test. For a track with exactly one step
    (two tracked points), the threshold became max(abs, step*6) -- always
    at least 6x the step itself -- so the step could NEVER exceed its own
    threshold no matter how large. An object teleporting any distance in a
    single frame, tracked with only two points, was undetectable."""

    def test_extreme_two_point_jump_is_now_caught(self):
        payload = dict(DEMO)
        payload["scenarios"] = [
            {"id": "extreme-teleport-2pt", "expected_violation": True, "mode": "generic",
             "tracks": [{"id": "obj", "points": [[0, 0, 5], [1, 1000, 5]]}]},
        ]
        result = analyze(payload)
        report = result["reports"][0]
        self.assertTrue(report["predicted_violation"])
        self.assertTrue(any(v["code"] == "teleport" for v in report["violations"]))

    def test_small_two_point_step_is_not_falsely_flagged(self):
        payload = dict(DEMO)
        payload["scenarios"] = [
            {"id": "fast-but-fine", "expected_violation": False, "mode": "generic",
             "tracks": [{"id": "obj", "points": [[0, 0, 5], [1, 5, 5]]}]},
        ]
        result = analyze(payload)
        self.assertFalse(result["reports"][0]["predicted_violation"])

    def test_one_extreme_step_among_several_normal_ones_is_caught(self):
        payload = dict(DEMO)
        payload["scenarios"] = [
            {"id": "mid-track-teleport", "expected_violation": True, "mode": "generic",
             "tracks": [{"id": "obj", "points": [[0, 0, 5], [1, 1, 5], [2, 2, 5], [3, 500, 5], [4, 501, 5]]}]},
        ]
        result = analyze(payload)
        report = result["reports"][0]
        self.assertTrue(report["predicted_violation"])
        self.assertTrue(any(v["code"] == "teleport" for v in report["violations"]))

    def test_demo_output_unaffected(self):
        result = analyze(DEMO)
        self.assertEqual(result["violations_detected"], 4)
        self.assertEqual(result["false_positives"], 0)
        self.assertEqual(result["accuracy"], 1.0)
        for report in result["reports"]:
            self.assertEqual(report["predicted_violation"], report["expected_violation"])


if __name__ == "__main__":
    unittest.main()
