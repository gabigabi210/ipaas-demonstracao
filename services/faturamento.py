"""Sistema de FATURAMENTO (API independente)."""
from services.common import serve

notas = []


def emitir_nota(body):
    nota = {"nota_id": f"NF-{len(notas) + 1:04d}", "cliente": body["cliente"], "valor": body["valor_total"]}
    notas.append(nota)
    return 200, nota


if __name__ == "__main__":
    serve({"/emitir_nota": emitir_nota}, {"/notas": lambda: notas}, "faturamento", 8002)
