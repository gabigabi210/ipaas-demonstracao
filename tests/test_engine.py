import unittest
from ipaas import Engine, default_connectors

FLOW = {
    "name": "t", "trigger": "e", "mode": "sync",
    "steps": [
        {"id": "b", "connector": "estoque", "action": "baixar", "foreach": "$.itens",
         "map": {"sku": "$item.sku", "quantidade": "$item.qtd"}},
        {"id": "n", "connector": "faturamento", "action": "emitir_nota",
         "map": {"cliente": {"from": "$.cliente", "transform": "upper"}, "valor_total": "$.total"}},
    ],
}
VENDA = {"cliente": "ana", "total": 10, "itens": [{"sku": "SKU-1", "qtd": 3}]}


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.c = default_connectors()
        self.e = Engine(self.c)
        self.e.register_flow(FLOW)

    def test_sucesso_e_transformacao(self):
        r = self.e.emit("e", VENDA, "1")[0]
        self.assertEqual(r["status"], "sucesso")
        self.assertEqual(self.c["estoque"].saldo["SKU-1"], 7)
        self.assertEqual(self.c["faturamento"].notas[0]["cliente"], "ANA")

    def test_idempotencia(self):
        self.e.emit("e", VENDA, "1")
        self.e.emit("e", VENDA, "1")
        self.assertEqual(self.c["estoque"].saldo["SKU-1"], 7)

    def test_erro_de_negocio(self):
        r = self.e.emit("e", {**VENDA, "itens": [{"sku": "SKU-3", "qtd": 9}]}, "2")[0]
        self.assertEqual(r["status"], "erro")

    def test_retry_em_falha_transitoria(self):
        c = default_connectors(notificacao_instavel=True)
        e = Engine(c)
        e.register_flow({"name": "n", "trigger": "x", "steps": [
            {"id": "s", "connector": "notificacao", "action": "enviar",
             "map": {"destino": "a@a.com", "mensagem": "oi"}}]})
        self.assertEqual(e.emit("x", {}, "1")[0]["status"], "sucesso")
        self.assertEqual(len(c["notificacao"].enviadas), 1)

    def test_lote_e_async(self):
        e = Engine(self.c)
        e.register_flow({**FLOW, "name": "b", "mode": "batch"})
        e.emit("e", VENDA, "1")
        self.assertEqual(self.c["estoque"].saldo["SKU-1"], 10)  # ainda não processou
        e.flush_batch()
        self.assertEqual(self.c["estoque"].saldo["SKU-1"], 7)
        e.register_flow({**FLOW, "name": "a", "mode": "async"})
        e.emit("e", VENDA, "2")
        e.wait()
        self.assertEqual(self.c["estoque"].saldo["SKU-1"], 4)


if __name__ == "__main__":
    unittest.main()
