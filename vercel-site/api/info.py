"""Model metadata endpoint for the Iris web interface."""

from http.server import BaseHTTPRequestHandler

from model_service import model_info, send_json


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        send_json(self, 200, model_info())

    def do_POST(self):
        self.send_response(405)
        self.send_header("Allow", "GET")
        self.send_header("Content-Length", "0")
        self.end_headers()
