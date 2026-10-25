"""Serviço de NOTIFICAÇÃO (API independente).
Com FALHAR_PRIMEIRA=1 responde 503 na primeira chamada, para demonstrar o retry."""
import os
from services.common import serve

enviadas = []
estado = {"falhar": os.environ.get("FALHAR_PRIMEIRA") == "1"}


def enviar(body):
    if estado["falhar"]:
        estado["falhar"] = False
        return 503, {"erro": "serviço de notificação indisponível (simulado)"}
    enviadas.append({"destino": body["destino"], "mensagem": body["mensagem"]})
    return 200, {"enviado": True}


if __name__ == "__main__":
    serve({"/enviar": enviar}, {"/enviadas": lambda: enviadas}, "notificacao", 8003)
