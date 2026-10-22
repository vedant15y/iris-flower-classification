"""Read the saved Iris model and serve predictions to the web interface."""

from __future__ import annotations

import json
import math
from pathlib import Path

from iris_classifier import FEATURES, predict


ROOT = Path(__file__).resolve().parent
MODEL = json.loads((ROOT / "model.json").read_text(encoding="utf-8"))
METRICS = json.loads((ROOT / "metrics.json").read_text(encoding="utf-8"))


def model_info() -> dict:
    return {
        "k": MODEL["k"],
        "training_rows": len(MODEL["samples"]),
        "test_rows": METRICS["test_rows"],
        "test_accuracy": METRICS["test"]["accuracy"],
    }


def classify(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Send a JSON object with four measurements.")
    values = payload.get("measurements")
    if not isinstance(values, list) or len(values) != len(FEATURES):
        raise ValueError("Enter all four measurements in the displayed order.")
    def valid_number(value: object) -> bool:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        try:
            return math.isfinite(value) and value > 0
        except OverflowError:
            return False

    if any(not valid_number(value) for value in values):
        raise ValueError("Measurements must be positive, finite numbers in centimeters.")
    species, vote_share = predict(MODEL, values)
    return {"species": species, "vote_share": vote_share, "neighbors": MODEL["k"]}


def send_json(handler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
    handler.wfile.write(body)
