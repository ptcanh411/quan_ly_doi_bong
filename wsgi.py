import os
import sys
import json
import mimetypes
import urllib.parse
from datetime import datetime

# Ensure project root is in sys.path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from db import init_db
from server import FCRequestHandler, PUBLIC_DIR

# Initialize database on startup
init_db()

class WSGIResponseContext:
    def __init__(self, environ, start_response):
        self.environ = environ
        self.start_response = start_response
        self.status_code = 200
        self.response_headers = [
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type"),
        ]
        self.response_body = b""

    def read_body(self):
        try:
            length = int(self.environ.get("CONTENT_LENGTH", 0) or 0)
        except (ValueError, TypeError):
            length = 0
        if length == 0:
            return {}
        stream = self.environ.get("wsgi.input")
        if not stream:
            return {}
        raw = stream.read(length)
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def send_json(self, data, status=200):
        self.status_code = status
        json_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.response_headers.append(("Content-Type", "application/json; charset=utf-8"))
        self.response_body = json_bytes
        return self.response_body

def application(environ, start_response):
    path = environ.get("PATH_INFO", "/") or "/"
    method = environ.get("REQUEST_METHOD", "GET").upper()

    # Handle CORS preflight OPTIONS
    if method == "OPTIONS":
        headers = [
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type"),
            ("Content-Length", "0"),
        ]
        start_response("200 OK", headers)
        return [b""]

    # Handle API requests
    if path.startswith("/api/"):
        ctx = WSGIResponseContext(environ, start_response)
        try:
            if method == "GET":
                FCRequestHandler.handle_api_get(ctx, path)
            elif method == "POST":
                FCRequestHandler.handle_api_post(ctx, path)
            elif method == "PUT":
                FCRequestHandler.handle_api_put(ctx, path)
            elif method == "DELETE":
                FCRequestHandler.handle_api_delete(ctx, path)
            else:
                ctx.send_json({"error": "Method Not Allowed"}, 405)
        except Exception as e:
            import traceback
            traceback.print_exc()
            ctx.send_json({"error": str(e)}, 500)

        status_text = f"{ctx.status_code} " + {
            200: "OK",
            201: "Created",
            400: "Bad Request",
            404: "Not Found",
            405: "Method Not Allowed",
            500: "Internal Server Error"
        }.get(ctx.status_code, "OK")

        ctx.response_headers.append(("Content-Length", str(len(ctx.response_body))))
        start_response(status_text, ctx.response_headers)
        return [ctx.response_body]

    # Handle Static Files
    if path == "/" or not path:
        rel_path = "index.html"
    else:
        rel_path = path.lstrip("/")

    safe_path = os.path.abspath(os.path.join(PUBLIC_DIR, rel_path))
    if not safe_path.startswith(os.path.abspath(PUBLIC_DIR)) or not os.path.exists(safe_path) or os.path.isdir(safe_path):
        # Fallback to index.html
        safe_path = os.path.join(PUBLIC_DIR, "index.html")

    if os.path.exists(safe_path) and os.path.isfile(safe_path):
        mime_type, _ = mimetypes.guess_type(safe_path)
        if not mime_type:
            mime_type = "application/octet-stream"
        if mime_type.startswith("text/") or mime_type in ("application/javascript", "application/json"):
            mime_type += "; charset=utf-8"

        with open(safe_path, "rb") as f:
            content = f.read()

        headers = [
            ("Content-Type", mime_type),
            ("Content-Length", str(len(content))),
            ("Access-Control-Allow-Origin", "*"),
        ]
        start_response("200 OK", headers)
        return [content]

    # 404 Fallback
    start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
    return [b"Not Found"]

if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    port = int(os.environ.get("PORT", 8000))
    print(f"WSGI Test Server running on port {port}...")
    server = make_server("0.0.0.0", port, application)
    server.serve_forever()
