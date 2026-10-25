"""Demonstração: uma venda confirmada dispara fluxos de integração entre
sistemas separados (estoque, faturamento, notificação)."""
from ipaas import Engine, default_connectors


def mostrar_logs(engine):
    print(f"\n{'FLUXO':28} {'EVENTO':7} {'PASSO':16} {'STATUS':9} DETALHE")
    for l in engine.logs:
        print(f"{l['flow']:28} {l['event_id']:7} {l['step']:16} {l['status']:9} {l['detail']}")


def main():
    conectores = default_connectors(notificacao_instavel=True)
    engine = Engine(conectores)
    engine.load_flows("flows")

    venda = {
        "pedido_id": "PED-1001",
        "cliente": "maria silva",
        "email": "maria@email.com",
        "total": 259.9,
        "itens": [{"sku": "SKU-1", "qtd": 2}, {"sku": "SKU-2", "qtd": 1}],
    }

    print("1) Venda confirmada -> fluxo SÍNCRONO (estoque, nota, aviso)")
    print("  ", engine.emit("venda.confirmada", venda, event_id="EV-1")[0]["status"])

    print("2) Mesmo evento reenviado -> IDEMPOTÊNCIA evita duplicar a baixa")
    print("  ", engine.emit("venda.confirmada", venda, event_id="EV-1")[0]["status"])

    print("3) Venda sem estoque -> erro tratado e registrado")
    sem_estoque = {**venda, "pedido_id": "PED-1002", "itens": [{"sku": "SKU-3", "qtd": 5}]}
    print("  ", engine.emit("venda.confirmada", sem_estoque, event_id="EV-2")[0])

    print("4) Fluxo em LOTE: processa de uma vez o que foi acumulado")
    engine.flush_batch()

    print("\nEstoque final:", conectores["estoque"].saldo)
    print("Notas emitidas:", conectores["faturamento"].notas)
    mostrar_logs(engine)


if __name__ == "__main__":
    main()
