"""Conectores simulados. Cada um representa um sistema diferente da empresa
(Estoque, Faturamento, Notificações). Em um iPaaS real, estes seriam
conectores prontos para APIs, bancos de dados, SaaS, etc."""


class Connector:
    name = "base"

    def call(self, action, params):
        method = getattr(self, action, None)
        if method is None:
            raise ValueError(f"Ação '{action}' não existe no conector '{self.name}'")
        return method(**params)


class Estoque(Connector):
    name = "estoque"

    def __init__(self, saldo=None):
        self.saldo = dict(saldo or {})

    def baixar(self, sku, quantidade):
        atual = self.saldo.get(sku, 0)
        if atual < quantidade:
            raise RuntimeError(f"Estoque insuficiente para {sku}: tem {atual}, pediu {quantidade}")
        self.saldo[sku] = atual - quantidade
        return {"sku": sku, "saldo_atual": self.saldo[sku]}


class Faturamento(Connector):
    name = "faturamento"

    def __init__(self):
        self.notas = []

    def emitir_nota(self, cliente, valor_total):
        nota = {"nota_id": f"NF-{len(self.notas) + 1:04d}", "cliente": cliente, "valor": valor_total}
        self.notas.append(nota)
        return nota


class Notificacao(Connector):
    name = "notificacao"

    def __init__(self, falhar_primeira_vez=False):
        self.enviadas = []
        self._falhar = falhar_primeira_vez

    def enviar(self, destino, mensagem):
        if self._falhar:  # simula uma instabilidade temporária (para demonstrar retry)
            self._falhar = False
            raise ConnectionError("Serviço de notificação indisponível (simulado)")
        self.enviadas.append({"destino": destino, "mensagem": mensagem})
        return {"enviado": True}


def default_connectors(notificacao_instavel=False):
    return {c.name: c for c in (
        Estoque({"SKU-1": 10, "SKU-2": 5, "SKU-3": 1}),
        Faturamento(),
        Notificacao(falhar_primeira_vez=notificacao_instavel),
    )}


# ---------------------------------------------------------------------------
# Conector HTTP REAL: faz requests para as APIs dos sistemas.
# ---------------------------------------------------------------------------
import json as _json
import urllib.error
import urllib.request


class HttpConnector(Connector):
    def __init__(self, name, base_url, timeout=5):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def call(self, action, params):
        req = urllib.request.Request(
            f"{self.base_url}/{action}",
            data=_json.dumps(params).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return _json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            detalhe = exc.read().decode("utf-8", "replace")
            try:
                detalhe = _json.loads(detalhe).get("erro", detalhe)
            except ValueError:
                pass
            if exc.code >= 500:  # falha transitória -> o motor faz retry
                raise ConnectionError(f"{self.name}: HTTP {exc.code} - {detalhe}")
            raise RuntimeError(f"{self.name}: HTTP {exc.code} - {detalhe}")  # erro de negócio
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ConnectionError(f"{self.name}: sem conexão ({exc})")


def http_connectors_from_env():
    import os
    urls = {
        "estoque": os.environ.get("ESTOQUE_URL", "http://localhost:8001"),
        "faturamento": os.environ.get("FATURAMENTO_URL", "http://localhost:8002"),
        "notificacao": os.environ.get("NOTIFICACAO_URL", "http://localhost:8003"),
    }
    return {n: HttpConnector(n, u) for n, u in urls.items()}
