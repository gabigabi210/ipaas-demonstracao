# Mini iPaaS — demonstração prática

Projeto acadêmico que representa, em pequena escala, os conceitos de **iPaaS** (Integration Platform as a Service) e **low-code**.

Cenário: uma empresa tem sistemas separados (vendas, estoque, faturamento e notificações). Quando uma **venda é confirmada**, a plataforma integra tudo automaticamente.

## Como os conceitos aparecem no código

| Conceito | Onde está |
|---|---|
| Integração de sistemas distintos | `ipaas/connectors.py` (Estoque, Faturamento, Notificação simulados) |
| Low-code / fluxo declarativo | `flows/*.json`: o fluxo é **configurado**, não programado |
| Gatilhos (triggers) | campo `"trigger"` do fluxo + `engine.emit(...)` |
| Mapeamento de campos | campo `"map"` (ex.: `"sku": "$item.sku"`) |
| Transformações | `ipaas/transforms.py` (ex.: `upper`, `round2`, `brl`) |
| Síncrono, assíncrono e em lote | campo `"mode"`: `sync`, `async` ou `batch` |
| Idempotência | evento repetido com o mesmo `event_id` é ignorado |
| Tolerância a falhas | retry automático em falhas transitórias |
| Monitoramento centralizado | `engine.logs` (histórico único de todas as execuções) |
| Evita teia ponto a ponto | sistemas só falam com a plataforma, nunca entre si |

## Exemplo de fluxo (low-code)

```json
{
  "name": "venda_confirmada_sync",
  "trigger": "venda.confirmada",
  "mode": "sync",
  "steps": [
    {"id": "baixa_estoque", "connector": "estoque", "action": "baixar",
     "foreach": "$.itens", "map": {"sku": "$item.sku", "quantidade": "$item.qtd"}},
    {"id": "nota_fiscal", "connector": "faturamento", "action": "emitir_nota",
     "map": {"cliente": {"from": "$.cliente", "transform": "upper"},
             "valor_total": {"from": "$.total", "transform": "round2"}}}
  ]
}
```

Para criar uma nova integração basta adicionar um JSON em `flows/`, sem alterar o motor.

## Como executar com n8n (principal)

O **n8n** é a plataforma iPaaS/low-code (interface visual). Estoque, faturamento e notificação são APIs independentes, cada uma em seu container, e o n8n orquestra o fluxo chamando-as por HTTP.

```bash
docker compose up --build
```

1. Abra http://localhost:5678 e crie a conta de administrador local (a primeira vez o n8n pede).
2. Importe o fluxo: **Workflows → ⋯ (menu) → Import from file** e escolha `n8n/venda_confirmada.json`.
3. Clique em **Publish/Activate** (alternador "Active") no canto superior direito.
4. Em outro terminal, na pasta do projeto: `python3 client_n8n.py`

O fluxo no n8n: `Webhook → Separar itens → Baixar estoque → Juntar itens → Emitir nota fiscal → Avisar cliente`.
O nó "Avisar cliente" tem retry automático ligado, e o serviço de notificação falha de propósito na 1ª chamada (HTTP 503) para demonstrar isso.
Para ver as execuções: aba **Executions** do n8n. Para ver os requests chegando nos sistemas: `docker compose logs estoque faturamento notificacao`.

Teste manual sem o script:

```bash
curl -X POST http://localhost:5678/webhook/venda-confirmada \
  -H "Content-Type: application/json" \
  -d '{"pedido_id":"PED-1","cliente":"ana","email":"ana@x.com","total":50,"itens":[{"sku":"SKU-1","qtd":1}]}'
```

## Como executar com o motor próprio em Python (opcional)

Mesmo cenário, sem n8n, usando o motor escrito neste repositório (`ipaas/`):

```bash
docker compose --profile proprio up --build
python3 client.py
```

## Como executar (sem Docker)

Requer apenas Python 3.9+ (sem dependências externas). Em 4 terminais:

```bash
python -m services.estoque
python -m services.faturamento
FALHAR_PRIMEIRA=1 python -m services.notificacao
python -m ipaas.server
python client.py
```

## Testes e modo simulado

```bash
python -m unittest discover -s tests -t .   # testes automatizados
python main.py                              # versão 100% em memória, sem HTTP
```

## Estrutura

```
ipaas-demo/
├── Dockerfile, docker-compose.yml
├── n8n/venda_confirmada.json  # fluxo low-code para importar no n8n
├── client_n8n.py        # cliente que envia a venda ao webhook do n8n
├── client.py            # cliente que faz requests reais ao motor próprio
├── main.py              # demonstração em memória (sem HTTP)
├── ipaas/
│   ├── server.py        # plataforma como API HTTP
│   ├── engine.py        # motor: gatilhos, mapeamento, retry, idempotência, logs
│   ├── connectors.py    # conector HTTP real + conectores simulados (testes)
│   └── transforms.py    # transformações de dados
├── services/            # estoque, faturamento e notificação (APIs independentes)
├── flows/               # fluxos low-code em JSON
└── tests/               # testes automatizados
```

## Limitações (por ser uma demonstração)

Os sistemas de estoque, faturamento e notificação são APIs simples criadas para a demonstração (dados em memória); um iPaaS real ofereceria conectores prontos para APIs, bancos e SaaS, interface visual, autenticação, filas persistentes e painel de monitoramento.
