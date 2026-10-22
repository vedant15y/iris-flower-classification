"""Iris prediction endpoint for four measured flower dimensions."""

import json
from http.server import BaseHTTPRequestHandler

from model_service import classify, send_json


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            send_json(self, 400, {"error": "Invalid request length."})
            return
        if length <= 0 or length > 4096:
            send_json(self, 413, {"error": "Request body must be 1–4096 bytes."})
            return
        try:
            payload = json.loads(self.rfile.read(length))
            result = classify(payload)
        except (UnicodeDecodeError, json.JSONDecodeError):
            send_json(self, 400, {"error": "Send valid JSON."})
            return
        except ValueError as error:
            send_json(self, 400, {"error": str(error)})
            return
        send_json(self, 200, result)

    def do_GET(self):
        self.send_response(405)
        self.send_header("Allow", "POST")
        self.send_header("Content-Length", "0")
        self.end_headers()
