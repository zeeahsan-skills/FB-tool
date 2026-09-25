import json
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def _respond(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
        response = {
            "status": "error",
            "message": "Browser automation must run in the local agent environment (Python on your machine) to support persistent sessions and visible manual login. Please run 'python run.py' locally and point the Agent API to http://127.0.0.1:8000.",
            "mode": "vercel-frontend-only"
        }
        self.wfile.write(json.dumps(response).encode("utf-8"))

    def do_GET(self):
        self._respond()

    def do_POST(self):
        self._respond()

    def do_OPTIONS(self):
        self._respond()
