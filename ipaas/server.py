"""Plataforma iPaaS como serviço HTTP.
  POST /events  {"event": "...", "event_id": "...", "payload": {...}}
  GET  /logs    histórico centralizado de execuções
  GET  /health
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ipaas.connectors import http_connectors_from_env
from ipaas.engine import Engine

engine = Engine(http_connectors_from_env(), max_retries=3, retry_delay=0.3)
engine.load_flows(os.environ.get("FLOWS_DIR", "flows"))


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
            return self._send(200, {"service": "ipaas", "status": "ok", "fluxos": [f["name"] for f in engine.flows]})
        if self.path == "/logs":
            return self._send(200, engine.logs)
        self._send(404, {"erro": "rota não encontrada"})

    def do_POST(self):
        if self.path == "/events":
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            results = engine.emit(body["event"], body["payload"], body["event_id"])
            return self._send(200, {"resultados": results})
        if self.path == "/flush":  # dispara os fluxos em lote acumulados
            return self._send(200, {"resultados": engine.flush_batch()})
        self._send(404, {"erro": "rota não encontrada"})

    def log_message(self, fmt, *args):
        print(f"[ipaas] {self.address_string()} {fmt % args}", flush=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"[ipaas] escutando na porta {port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
