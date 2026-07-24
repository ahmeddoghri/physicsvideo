from __future__ import annotations

import math
from pathlib import Path


DEMO = {
    "teleport_absolute_threshold": 10.0,
    "max_visibility_gap": 2,
    "minimum_gravity_acceleration": 0.5,
    "scenarios": [
        {"id": "gravity-control", "expected_violation": False, "mode": "ballistic", "tracks": [{"id": "ball", "points": [[0, 0, 0], [1, 1, 1], [2, 2, 4], [3, 3, 9], [4, 4, 16]]}]},
        {"id": "hover", "expected_violation": True, "mode": "ballistic", "tracks": [{"id": "ball", "points": [[0, 0, 8], [1, 1, 8], [2, 2, 8], [3, 3, 8], [4, 4, 8]]}]},
        {"id": "teleport", "expected_violation": True, "mode": "generic", "tracks": [{"id": "cube", "points": [[0, 0, 3], [1, 1, 3], [2, 2, 3], [3, 25, 3], [4, 26, 3]]}]},
        {"id": "disappear", "expected_violation": True, "mode": "generic", "tracks": [{"id": "subject", "points": [[0, 0, 5], [1, 1, 5], [5, 5, 5], [6, 6, 5]]}]},
        {"id": "pass-through", "expected_violation": True, "mode": "collision", "collision_frame": 3, "tracks": [
            {"id": "cyan", "points": [[0, -3, 4], [1, -2, 4], [2, -1, 4], [3, 0, 4], [4, 1, 4], [5, 2, 4]]},
            {"id": "amber", "points": [[0, 3, 4], [1, 2, 4], [2, 1, 4], [3, 0, 4], [4, -1, 4], [5, -2, 4]]}
        ]},
    ],
}


def _track_checks(track: dict, payload: dict, mode: str) -> list[dict]:
    points = sorted(track["points"])
    violations = []
    gaps = [right[0] - left[0] for left, right in zip(points, points[1:])]
    if gaps and max(gaps) > int(payload.get("max_visibility_gap", 2)):
        violations.append({"code": "object_permanence_gap", "track": track["id"], "value": max(gaps)})
    steps = [math.dist(left[1:3], right[1:3]) for left, right in zip(points, points[1:])]
    nonzero = [step for step in steps if step > 1e-9]
    median_step = sorted(nonzero)[len(nonzero) // 2] if nonzero else 0.0
    threshold = max(float(payload.get("teleport_absolute_threshold", 10.0)), median_step * 6)
    if steps and max(steps) > threshold:
        violations.append({"code": "teleport", "track": track["id"], "value": round(max(steps), 4)})
    if mode == "ballistic" and len(points) >= 3:
        accelerations = []
        for first, second, third in zip(points, points[1:], points[2:]):
            if second[0] - first[0] == third[0] - second[0] == 1:
                accelerations.append(third[2] - 2 * second[2] + first[2])
        mean_acceleration = sum(accelerations) / len(accelerations) if accelerations else 0.0
        if mean_acceleration < float(payload.get("minimum_gravity_acceleration", 0.5)):
            violations.append({"code": "gravity_violation", "track": track["id"], "value": round(mean_acceleration, 4)})
    return violations


def _collision_check(scenario: dict) -> list[dict]:
    frame = int(scenario["collision_frame"])
    violations = []
    for track in scenario["tracks"]:
        positions = {int(point[0]): point for point in track["points"]}
        if not all(index in positions for index in (frame - 1, frame, frame + 1)):
            violations.append({"code": "collision_evidence_missing", "track": track["id"], "value": frame})
            continue
        before = positions[frame][1] - positions[frame - 1][1]
        after = positions[frame + 1][1] - positions[frame][1]
        if before * after >= 0:
            violations.append({"code": "collision_pass_through", "track": track["id"], "value": round(after, 4)})
    return violations


def analyze(payload: dict) -> dict:
    reports = []
    for scenario in payload["scenarios"]:
        violations = []
        for track in scenario["tracks"]:
            violations.extend(_track_checks(track, payload, scenario.get("mode", "generic")))
        if scenario.get("mode") == "collision":
            violations.extend(_collision_check(scenario))
        predicted = bool(violations)
        reports.append({"id": scenario["id"], "expected_violation": bool(scenario["expected_violation"]), "predicted_violation": predicted, "correct": predicted == bool(scenario["expected_violation"]), "violations": violations, "tracks": scenario["tracks"]})
    true_positives = sum(row["predicted_violation"] and row["expected_violation"] for row in reports)
    false_positives = sum(row["predicted_violation"] and not row["expected_violation"] for row in reports)
    correct = sum(row["correct"] for row in reports)
    return {
        "scenario_count": len(reports),
        "violating_scenarios": sum(row["expected_violation"] for row in reports),
        "violations_detected": true_positives,
        "false_positives": false_positives,
        "accuracy": round(correct / max(1, len(reports)), 4),
        "reports": reports,
        "scope": "Trajectory-level physical checks after tracking; appearance realism, deformable physics, camera motion, and hidden forces need richer models.",
    }


def render_video(payload: dict, output: str | Path, fps: int = 12) -> None:
    import cv2
    import numpy as np

    scenarios = payload["scenarios"]
    panel_width, height, frames = 250, 190, 48
    writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"), fps, (panel_width * len(scenarios), height))
    colors = [(230, 220, 90), (80, 180, 255)]
    for video_frame in range(frames):
        image = np.zeros((height, panel_width * len(scenarios), 3), dtype=np.uint8)
        logical = video_frame / (frames - 1) * 6
        for panel, scenario in enumerate(scenarios):
            left = panel * panel_width
            cv2.rectangle(image, (left, 0), (left + panel_width - 1, height - 1), (40, 54, 58), 1)
            cv2.putText(image, scenario["id"], (left + 10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 195, 198), 1, cv2.LINE_AA)
            for track_index, track in enumerate(scenario["tracks"]):
                points = sorted(track["points"])
                visible = [point for point in points if abs(point[0] - logical) <= 0.6]
                if not visible:
                    continue
                point = min(visible, key=lambda item: abs(item[0] - logical))
                x = int(left + panel_width / 2 + point[1] * 7)
                y = int(45 + min(16, point[2]) * 7)
                cv2.circle(image, (x, y), 10, colors[track_index % len(colors)], -1, cv2.LINE_AA)
        writer.write(image)
    writer.release()
