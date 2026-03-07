# Guia: Criando um Novo Conector

Este guia explica como criar um novo conector para o Hub de Integrações.

## Arquitetura

O sistema usa `BaseConnector` (ABC) + `ConnectorRegistry` (auto-discovery).
Qualquer Django app que registre um conector no `ready()` aparece
automaticamente no Hub de Integrações.

## Passo a Passo

### 1. Criar o Django app

```bash
python manage.py startapp meu_conector
```

### 2. Implementar o conector

Criar `meu_conector/connector.py`:

```python
from integrations.base import BaseConnector

class MeuConector(BaseConnector):
    slug = "meu-conector"
    name = "Meu Conector"
    description = "Descrição curta."
    icon = "plug"
    version = "1.0.0"

    def connect(self, org, config: dict) -> dict: ...
    def disconnect(self, org) -> dict: ...
    def sync(self, org, sync_type: str, **kwargs) -> dict: ...
    def get_status(self, org) -> dict: ...
    def get_health(self, org) -> dict: ...
    def get_config_schema(self) -> dict: ...
    def handle_webhook(self, org, payload: dict) -> dict: ...
    def validate_webhook(self, request) -> bool: ...
    def get_sync_types(self) -> list: ...
```

### 3. Registrar no AppConfig

Em `meu_conector/apps.py`:

```python
class MeuConectorConfig(AppConfig):
    name = "meu_conector"

    def ready(self):
        from integrations.registry import ConnectorRegistry
        from .connector import MeuConector
        ConnectorRegistry.register(MeuConector)
```

### 4. Adicionar ao INSTALLED_APPS

Em `crm/settings.py`:

```python
INSTALLED_APPS = [
    ...
    "meu_conector",
]
```

### 5. (Opcional) Registrar como ChannelProvider

Se o conector fornece canais de comunicação, implemente `ChannelProvider`:

```python
from channels.base import ChannelProvider, ChannelType, MessageCapability
from channels.registry import ChannelRegistry

class MeuChannelProvider(ChannelProvider):
    channel_type = ChannelType.WEBCHAT
    name = "Meu Canal"
    icon = "message-circle"

    def send_message(self, channel_config, contact, message_data): ...
    def receive_message(self, channel_config, raw_payload): ...
    def get_capabilities(self): return [MessageCapability.TEXT]
    def get_status(self, channel_config): ...
    def get_config_schema(self): ...
```

Registrar no `ready()`:
```python
ChannelRegistry.register(MeuChannelProvider)
```

## Conectores Planejados

| Conector       | Status      | Tipo           |
|----------------|-------------|----------------|
| TalkHub Omni   | Implementado | Connector + Channel |
| Salesforce     | Stub        | Connector      |
| Chatwoot       | Planejado   | Connector + Channel |
| Evolution API  | Planejado   | Connector + Channel |
| HubSpot        | Planejado   | Connector      |

## Checklist

- [ ] Implementar todos os métodos de `BaseConnector`
- [ ] Registrar no `ConnectorRegistry` via `apps.py`
- [ ] Adicionar ao `INSTALLED_APPS`
- [ ] Criar migrações se houver modelos
- [ ] Testar webhook routing via `/api/integrations/webhooks/<slug>/`
- [ ] Verificar que aparece no Hub de Integrações (frontend)
