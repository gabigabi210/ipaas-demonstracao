"""Utilitário para subir pequenas APIs HTTP/JSON (somente biblioteca padrão)."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def make_handler(post_routes, get_routes, name):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, body):
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/health":
                return self._send(200, {"service": name, "status": "ok"})
            fn = get_routes.get(self.path)
            return self._send(200, fn()) if fn else self._send(404, {"erro": "rota não encontrada"})

        def do_POST(self):
            fn = post_routes.get(self.path)
            if not fn:
                return self._send(404, {"erro": "rota não encontrada"})
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                status, result = fn(body)
                self._send(status, result)
            except Exception as exc:
                self._send(500, {"erro": str(exc)})

        def log_message(self, fmt, *args):
            print(f"[{name}] {self.address_string()} {fmt % args}", flush=True)

    return Handler


def serve(post_routes, get_routes, name, default_port):
    port = int(os.environ.get("PORT", default_port))
    print(f"[{name}] escutando na porta {port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), make_handler(post_routes, get_routes, name)).serve_forever()
