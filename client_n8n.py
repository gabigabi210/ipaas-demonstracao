"""Envia uma venda confirmada ao WEBHOOK do n8n (requests reais) e mostra os sistemas."""
import json
import os
import urllib.error
import urllib.request

N8N = os.environ.get("N8N_URL", "http://localhost:5678")
ESTOQUE = os.environ.get("ESTOQUE_URL", "http://localhost:8001")
FATURAMENTO = os.environ.get("FATURAMENTO_URL", "http://localhost:8002")
NOTIFICACAO = os.environ.get("NOTIFICACAO_URL", "http://localhost:8003")


def post(url, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"}, method="POST")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=30).read())
    except urllib.error.HTTPError as exc:
        return {"http_status": exc.code, "corpo": exc.read().decode("utf-8", "replace")}


def get(url):
    return json.loads(urllib.request.urlopen(url).read())


def show(titulo, obj):
    print(f"\n== {titulo}\n{json.dumps(obj, indent=2, ensure_ascii=False)}")


venda = {
    "pedido_id": "PED-2001", "cliente": "joao souza", "email": "joao@email.com", "total": 120.5,
    "itens": [{"sku": "SKU-1", "qtd": 1}, {"sku": "SKU-2", "qtd": 2}],
}
show("Resposta do n8n ao webhook (venda confirmada)", post(f"{N8N}/webhook/venda-confirmada", venda))
show("Estoque", get(f"{ESTOQUE}/saldo"))
show("Notas emitidas", get(f"{FATURAMENTO}/notas"))
show("Notificações enviadas", get(f"{NOTIFICACAO}/enviadas"))
