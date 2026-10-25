"""Sistema de ESTOQUE (API independente)."""
import threading
from services.common import serve

saldo = {"SKU-1": 10, "SKU-2": 5, "SKU-3": 1}
lock = threading.Lock()


def baixar(body):
    sku, qtd = body["sku"], int(body["quantidade"])
    with lock:
        atual = saldo.get(sku, 0)
        if atual < qtd:
            return 409, {"erro": f"Estoque insuficiente para {sku}: tem {atual}, pediu {qtd}"}
        saldo[sku] = atual - qtd
        return 200, {"sku": sku, "saldo_atual": saldo[sku]}


if __name__ == "__main__":
    serve({"/baixar": baixar}, {"/saldo": lambda: saldo}, "estoque", 8001)
