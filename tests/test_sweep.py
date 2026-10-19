import unittest

from physicsvideo.sweep import run


class SweepTest(unittest.TestCase):
    def test_no_false_alarms_on_noisy_but_valid_motion(self):
        for noise in (0.05, 0.4):
            result = run(trials=120, noise=noise, seed=3)
            self.assertEqual(result["false_alarm_rate"], 0.0, (noise, result))

    def test_every_planted_fault_type_is_caught(self):
        result = run(trials=120, seed=3)
        for fault, rate in result["detection_rate"].items():
            self.assertEqual(rate, 1.0, (fault, result))

    def test_a_two_point_teleport_is_still_caught(self):
        # The self-referential threshold made this mathematically impossible
        # to flag before the leave-one-out fix.
        from physicsvideo.core import analyze

        scenario = {"id": "sparse", "expected_violation": True, "mode": "none",
                    "tracks": [{"id": "ball", "points": [[0, 0, 0], [1, 1000, 0]]}]}
        report = analyze({"scenarios": [scenario]})["reports"][0]
        self.assertTrue(any(v["code"] == "teleport" for v in report["violations"]), report)


if __name__ == "__main__":
    unittest.main()
