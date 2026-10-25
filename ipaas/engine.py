"""Motor de integração: lê fluxos declarativos (JSON), mapeia campos, aplica
transformações, chama conectores, faz retry, garante idempotência e registra
logs centralizados."""
import json
import queue
import re
import threading
import time
from pathlib import Path

from . import transforms


def resolve(expr, ctx):
    """Resolve expressões como '$.cliente', '$item.sku' ou '$steps.nota.nota_id'.
    Qualquer valor que não comece com '$' é tratado como constante."""
    if not (isinstance(expr, str) and expr.startswith("$")):
        return expr
    head, _, rest = expr.partition(".")
    base = {"$": ctx["payload"], "$item": ctx.get("item"), "$steps": ctx["steps"]}[head]
    for part in filter(None, rest.split(".")):
        base = base[int(part)] if isinstance(base, list) else base[part]
    return base


def build_params(mapping, ctx):
    """Mapeamento de campos: origem -> destino, com transformação opcional."""
    params = {}
    for target, spec in mapping.items():
        if isinstance(spec, dict):  # {"from": "...", "transform": "..."}
            value = resolve(spec["from"], ctx)
            if "transform" in spec:
                value = transforms.apply(spec["transform"], value)
        elif isinstance(spec, str) and "{" in spec:  # template: "Pedido {$.pedido_id}"
            value = spec
            for token in re.findall(r"\{([^}]+)\}", spec):
                value = value.replace("{" + token + "}", str(resolve(token, ctx)))
        else:
            value = resolve(spec, ctx)
        params[target] = value
    return params


class Engine:
    def __init__(self, connectors, max_retries=2, retry_delay=0.05):
        self.connectors = connectors
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.flows = []
        self.logs = []                 # monitoramento centralizado
        self._processed = set()        # idempotência: (fluxo, event_id)
        self._batch_buffer = []
        self._queue = queue.Queue()
        self._lock = threading.Lock()
        threading.Thread(target=self._worker, daemon=True).start()

    # ---------- configuração ----------
    def register_flow(self, flow):
        self.flows.append(flow)

    def load_flows(self, folder):
        for path in sorted(Path(folder).glob("*.json")):
            self.register_flow(json.loads(path.read_text(encoding="utf-8")))

    # ---------- entrada de eventos (gatilhos) ----------
    def emit(self, event, payload, event_id):
        results = []
        for flow in (f for f in self.flows if f["trigger"] == event):
            mode = flow.get("mode", "sync")
            if mode == "sync":
                results.append(self._run(flow, payload, event_id))
            elif mode == "async":
                self._queue.put((flow, payload, event_id))
            elif mode == "batch":
                self._batch_buffer.append((flow, payload, event_id))
        return results

    def flush_batch(self):
        buffered, self._batch_buffer = self._batch_buffer, []
        return [self._run(f, p, e) for f, p, e in buffered]

    def wait(self):
        self._queue.join()

    def _worker(self):
        while True:
            flow, payload, event_id = self._queue.get()
            try:
                self._run(flow, payload, event_id)
            finally:
                self._queue.task_done()

    # ---------- execução ----------
    def _log(self, flow, event_id, step, status, detail=""):
        with self._lock:
            self.logs.append({"flow": flow, "event_id": event_id, "step": step,
                              "status": status, "detail": detail})

    def _run(self, flow, payload, event_id):
        name = flow["name"]
        if (name, event_id) in self._processed:
            self._log(name, event_id, "-", "IGNORADO", "evento duplicado (idempotência)")
            return {"flow": name, "status": "ignorado"}

        ctx = {"payload": payload, "steps": {}}
        for step in flow["steps"]:
            try:
                ctx["steps"][step["id"]] = self._run_step(step, ctx, name, event_id)
            except Exception as exc:
                self._log(name, event_id, step["id"], "ERRO", str(exc))
                return {"flow": name, "status": "erro", "step": step["id"], "erro": str(exc)}

        self._processed.add((name, event_id))
        self._log(name, event_id, "-", "SUCESSO")
        return {"flow": name, "status": "sucesso", "steps": ctx["steps"]}

    def _run_step(self, step, ctx, flow_name, event_id):
        connector = self.connectors[step["connector"]]
        if "foreach" in step:
            return [self._call(connector, step, {**ctx, "item": item}, flow_name, event_id)
                    for item in resolve(step["foreach"], ctx)]
        return self._call(connector, step, ctx, flow_name, event_id)

    def _call(self, connector, step, ctx, flow_name, event_id):
        params = build_params(step.get("map", {}), ctx)
        for attempt in range(1, self.max_retries + 2):
            try:
                result = connector.call(step["action"], params)
                self._log(flow_name, event_id, step["id"], "OK", f"tentativa {attempt}")
                return result
            except ConnectionError as exc:  # falha transitória: tenta de novo
                self._log(flow_name, event_id, step["id"], "RETRY", f"tentativa {attempt}: {exc}")
                if attempt > self.max_retries:
                    raise
                time.sleep(self.retry_delay)
