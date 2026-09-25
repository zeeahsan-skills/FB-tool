import json
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        response = {
            "status": "ok",
            "service": "facebook-group-research-agent",
            "environment": "vercel-frontend-mode",
            "note": "Frontend is deployed on Vercel. Browser automation runs on your local machine."
        }
        self.wfile.write(json.dumps(response).encode("utf-8"))
