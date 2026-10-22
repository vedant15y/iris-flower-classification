"""Serve a small local browser UI for the saved Iris classifier."""

from __future__ import annotations

import argparse
import json
import math
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from iris_classifier import FEATURES, predict


ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "ui"
MODEL_PATH = ROOT / "model.json"
METRICS_PATH = ROOT / "metrics.json"
STATIC_FILES = {
    "/": (STATIC / "landing.html", "text/html; charset=utf-8"),
    "/predict": (STATIC / "index.html", "text/html; charset=utf-8"),
    "/landing.css": (STATIC / "landing.css", "text/css; charset=utf-8"),
    "/landing.js": (STATIC / "landing.js", "text/javascript; charset=utf-8"),
    "/styles.css": (STATIC / "styles.css", "text/css; charset=utf-8"),
    "/app.js": (STATIC / "app.js", "text/javascript; charset=utf-8"),
    "/assets/iris-poster.jpg": (STATIC / "assets" / "iris-poster.jpg", "image/jpeg"),
    "/assets/iris-opening.jpg": (STATIC / "assets" / "iris-opening.jpg", "image/jpeg"),
    "/assets/iris-final.jpg": (STATIC / "assets" / "iris-final.jpg", "image/jpeg"),
}
VIDEO_PATH = STATIC / "assets" / "iris-scroll.mp4"


def read_json(path: Path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def classify(payload):
    if not isinstance(payload, dict):
        raise ValueError("Send a JSON object with four measurements.")
    values = payload.get("measurements")
    if not isinstance(values, list) or len(values) != len(FEATURES):
        raise ValueError("Enter all four measurements in the displayed order.")
    def valid_number(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        try:
            return math.isfinite(value) and value > 0
        except OverflowError:
            return False

    if any(not valid_number(value) for value in values):
        raise ValueError("Measurements must be positive, finite numbers in centimeters.")
    model = read_json(MODEL_PATH)
    species, vote_share = predict(model, values)
    return {"species": species, "vote_share": vote_share, "neighbors": model["k"]}


class Handler(BaseHTTPRequestHandler):
    def send_local_file_cors(self):
        """Allow this project's file:// page to call the loopback model API."""
        if self.headers.get("Origin") == "null":
            self.send_header("Access-Control-Allow-Origin", "null")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.send_header("Vary", "Origin")

    def send_bytes(self, status: int, data: bytes, content_type: str):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'")
        self.send_local_file_cors()
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, status: int, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_bytes(status, data, "application/json; charset=utf-8")

    def send_video(self):
        """Send the local video with byte ranges so browser scrubbing can seek."""
        try:
            size = VIDEO_PATH.stat().st_size
        except OSError:
            self.send_json(500, {"error": "The animation file could not be loaded."})
            return
        range_header = self.headers.get("Range", "")
        try:
            start, end = 0, size - 1
            status = 200
            if range_header:
                if not range_header.startswith("bytes=") or "," in range_header:
                    raise ValueError("Unsupported range")
                first, separator, last = range_header[6:].partition("-")
                if not separator:
                    raise ValueError("Invalid range")
                if first:
                    start = int(first)
                    end = int(last) if last else end
                elif last:
                    start = max(size - int(last), 0)
                else:
                    raise ValueError("Invalid range")
                if start < 0 or end < start or start >= size:
                    raise ValueError("Invalid range")
                end = min(end, size - 1)
                status = 206
        except ValueError:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(status)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        with VIDEO_PATH.open("rb") as video:
            video.seek(start)
            remaining = end - start + 1
            while remaining:
                chunk = video.read(min(128 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/assets/iris-scroll.mp4":
            self.send_video()
            return
        if path == "/api/info":
            try:
                model = read_json(MODEL_PATH)
                metrics = read_json(METRICS_PATH)
            except (OSError, ValueError, KeyError):
                self.send_json(500, {"error": "Model files are unavailable. Run training first."})
                return
            self.send_json(200, {
                "k": model["k"],
                "training_rows": len(model["samples"]),
                "test_rows": metrics["test_rows"],
                "test_accuracy": metrics["test"]["accuracy"],
            })
            return
        resource = STATIC_FILES.get(path)
        if resource is None:
            self.send_json(404, {"error": "Not found."})
            return
        file_path, content_type = resource
        try:
            self.send_bytes(200, file_path.read_bytes(), content_type)
        except OSError:
            self.send_json(500, {"error": "The interface file could not be loaded."})

    def do_OPTIONS(self):
        path = urlsplit(self.path).path
        if path not in ("/api/info", "/api/predict") or self.headers.get("Origin") != "null":
            self.send_json(403, {"error": "Origin not allowed."})
            return
        self.send_response(204)
        self.send_local_file_cors()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        if self.headers.get("Access-Control-Request-Private-Network") == "true":
            self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        if urlsplit(self.path).path != "/api/predict":
            self.send_json(404, {"error": "Not found."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json(400, {"error": "Invalid request length."})
            return
        if length <= 0 or length > 4096:
            self.send_json(413, {"error": "Request body must be 1–4096 bytes."})
            return
        try:
            payload = json.loads(self.rfile.read(length))
            result = classify(payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(400, {"error": "Send valid JSON."})
            return
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
            return
        except (OSError, KeyError, IndexError):
            self.send_json(500, {"error": "The saved model could not be loaded."})
            return
        self.send_json(200, result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765, help="local port (default: 8765)")
    args = parser.parse_args()
    if not MODEL_PATH.is_file():
        parser.error("model.json is missing; run iris_classifier.py train first")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Iris classifier UI: http://127.0.0.1:{server.server_port}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
