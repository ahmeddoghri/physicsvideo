"""Detection and false-alarm rates on randomized trajectories.

The bundled fixture is five hand-built scenarios, and 100% on five cases is
not a rate. This generates ballistic trajectories with tracking noise, keeps
half of them physically valid, plants one fault in the rest, and reports how
often each fault is caught and how often a clean clip is wrongly flagged.

    python -m physicsvideo.sweep
"""
from __future__ import annotations

import json
import random

from .core import analyze

FAULTS = ("gravity", "teleport", "gap")


def _clean(rng: random.Random, frames: int = 12, noise: float = 0.05) -> list[list[float]]:
    vx = rng.uniform(0.5, 2.0)
    points = []
    for t in range(frames):
        x = t * vx + rng.gauss(0, noise)
        y = t * t + rng.gauss(0, noise)   # constant downward acceleration of 2
        points.append([t, round(x, 4), round(y, 4)])
    return points


def _plant(points: list[list[float]], fault: str, rng: random.Random) -> list[list[float]]:
    points = [list(point) for point in points]
    if fault == "gravity":
        # Upward acceleration: the object falls up.
        return [[t, x, round(-(t * t) + rng.gauss(0, 0.05), 4)] for t, x, _ in points]
    if fault == "teleport":
        index = rng.randrange(2, len(points) - 2)
        jump = rng.uniform(200, 1500)
        for point in points[index:]:
            point[1] += jump
        return points
    if fault == "gap":
        # Keep the gap interior: dropping the tail is an object leaving the
        # scene, not a permanence violation, and must not be scored as one.
        index = rng.randrange(2, len(points) - 5)
        return points[:index] + points[index + 4:]
    raise ValueError(fault)


def run(trials: int = 200, seed: int = 0, noise: float = 0.05) -> dict:
    rng = random.Random(seed)
    caught = {fault: 0 for fault in FAULTS}
    planted = {fault: 0 for fault in FAULTS}
    clean_total = false_alarms = 0

    for index in range(trials):
        points = _clean(rng, noise=noise)
        if index % 2 == 0:
            clean_total += 1
            scenario = {"id": f"clean-{index}", "expected_violation": False, "mode": "ballistic",
                        "tracks": [{"id": "ball", "points": points}]}
            report = analyze({"scenarios": [scenario]})["reports"][0]
            false_alarms += bool(report["violations"])
        else:
            fault = FAULTS[index % len(FAULTS)]
            planted[fault] += 1
            scenario = {"id": f"{fault}-{index}", "expected_violation": True, "mode": "ballistic",
                        "tracks": [{"id": "ball", "points": _plant(points, fault, rng)}]}
            report = analyze({"scenarios": [scenario]})["reports"][0]
            caught[fault] += bool(report["violations"])

    return {
        "trials": trials,
        "tracking_noise": noise,
        "clean_clips": clean_total,
        "false_alarms": false_alarms,
        "false_alarm_rate": round(false_alarms / max(1, clean_total), 3),
        "detection_rate": {
            fault: round(caught[fault] / planted[fault], 3) if planted[fault] else None
            for fault in FAULTS
        },
        "planted": planted,
    }


def main() -> None:
    print(json.dumps({
        "low_noise": run(),
        "high_noise": run(seed=7, noise=0.4),
    }, indent=2))


if __name__ == "__main__":
    main()
