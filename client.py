"""Envia uma venda confirmada para a plataforma iPaaS via HTTP e mostra o resultado."""
import json
import os
import urllib.request

IPAAS = os.environ.get("IPAAS_URL", "http://localhost:8000")
ESTOQUE = os.environ.get("ESTOQUE_URL", "http://localhost:8001")
FATURAMENTO = os.environ.get("FATURAMENTO_URL", "http://localhost:8002")
NOTIFICACAO = os.environ.get("NOTIFICACAO_URL", "http://localhost:8003")


def post(url, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(req).read())


def get(url):
    return json.loads(urllib.request.urlopen(url).read())


def show(titulo, obj):
    print(f"\n== {titulo}\n{json.dumps(obj, indent=2, ensure_ascii=False)}")


venda = {
    "pedido_id": "PED-1001", "cliente": "maria silva", "email": "maria@email.com", "total": 259.9,
    "itens": [{"sku": "SKU-1", "qtd": 2}, {"sku": "SKU-2", "qtd": 1}],
}

show("1) Venda confirmada enviada ao iPaaS", post(f"{IPAAS}/events", {"event": "venda.confirmada", "event_id": "EV-1", "payload": venda}))
show("2) Mesmo evento reenviado (idempotência)", post(f"{IPAAS}/events", {"event": "venda.confirmada", "event_id": "EV-1", "payload": venda}))
sem_estoque = {**venda, "pedido_id": "PED-1002", "itens": [{"sku": "SKU-3", "qtd": 5}]}
show("3) Venda sem estoque (erro tratado)", post(f"{IPAAS}/events", {"event": "venda.confirmada", "event_id": "EV-2", "payload": sem_estoque}))
show("4) Fluxos em lote processados", post(f"{IPAAS}/flush", {}))

show("Estoque (sistema independente)", get(f"{ESTOQUE}/saldo"))
show("Notas emitidas (sistema independente)", get(f"{FATURAMENTO}/notas"))
show("Notificações enviadas (sistema independente)", get(f"{NOTIFICACAO}/enviadas"))
print("\n== Logs centralizados do iPaaS")
for l in get(f"{IPAAS}/logs"):
    print(f"{l['flow']:28} {l['event_id']:6} {l['step']:16} {l['status']:9} {l['detail']}")
