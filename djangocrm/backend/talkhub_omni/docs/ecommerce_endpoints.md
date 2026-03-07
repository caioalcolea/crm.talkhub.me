# TalkHub Omni — Endpoints de E-commerce

> Disponíveis para expansão futura. Estes endpoints da API TalkHub Omni
> permitem integração com módulos de e-commerce (produtos, pedidos, cupons).

## Endpoints Disponíveis

### Produtos
- `GET /ecommerce/products` — Listar produtos
- `GET /ecommerce/products/{id}` — Detalhe do produto
- `GET /ecommerce/products/{id}/variants` — Variantes do produto

### Pedidos
- `GET /ecommerce/orders` — Listar pedidos
- `GET /ecommerce/orders/{id}` — Detalhe do pedido
- `POST /ecommerce/orders` — Criar pedido

### Códigos de Desconto
- `GET /ecommerce/discount-codes` — Listar cupons
- `POST /ecommerce/discount-codes` — Criar cupom
- `DELETE /ecommerce/discount-codes/{id}` — Remover cupom

## Status

Estes endpoints estão documentados mas **não implementados** no conector atual.
A arquitetura do `BaseConnector` e `TalkHubClient` suporta adição destes
módulos sem refatoração — basta adicionar métodos ao client e sync types
ao conector.

## Implementação Futura

1. Adicionar métodos ao `TalkHubClient` (`get_products`, `get_orders`, etc.)
2. Adicionar sync types ao `TalkHubOmniConnector.get_sync_types()`
3. Criar modelos CRM para Produto e Pedido (se necessário)
4. Implementar mapeamento no `data_unifier.py`
