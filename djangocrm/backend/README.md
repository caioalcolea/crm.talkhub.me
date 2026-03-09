# TalkHub CRM Backend — Django REST API

Backend multi-tenant do TalkHub CRM. Django 5.2 + DRF 3.16 + PostgreSQL 16 RLS + Celery 5.6.

## Stack

- **Django 5.2** + Django REST Framework 3.16
- **PostgreSQL 16** com Row-Level Security (RLS)
- **Redis 7** — broker Celery + cache
- **Celery 5.6** + Celery Beat — tarefas async e scheduler
- **SimpleJWT** — autenticação JWT com org_id nos claims
- **httpx 0.28** — HTTP client para integrações externas (TalkHub Omni)
- **WeasyPrint** — geração de PDF (faturas)
- **boto3** — storage S3 (MinIO)
- **Sentry SDK** — error tracking (opcional)

## Django Apps

| App | Descrição |
|-----|-----------|
| `common` | User, Org, Profile, Comments, Attachments, Auth (JWT, Google OAuth, Magic Link), RLS, middleware, admin panel |
| `accounts` | Empresas (contas) |
| `leads` | Leads + kanban pipeline customizável |
| `contacts` | Contatos com redes sociais + campos TalkHub Omni (subscriber_id, omni_user_ns, sms/email opt-in) |
| `opportunity` | Pipeline de vendas, line items, produtos |
| `cases` | Suporte com kanban pipeline + SLA + escalação |
| `tasks` | Tarefas, kanban, boards, calendário |
| `invoices` | Faturas, orçamentos, recorrentes, produtos |
| `orders` | Pedidos |
| `financeiro` | Lançamentos, pagar/receber, plano de contas, formas de pagamento, relatórios |
| `integrations` | Hub genérico: conexões, sync jobs, logs, webhooks, field mapping, conflict resolution |
| `channels` | Abstração de canais de comunicação (TalkHub Omni, SMTP, Chatwoot, etc.) |
| `conversations` | Inbox omnichannel: conversas e mensagens genéricas, real-time via fast polling |
| `chatwoot` | Conector Chatwoot: webhook bidirerecional (7 eventos), sync conversas/contatos/grupos, channel provider |
| `talkhub_omni` | Conector TalkHub Omni: sync contatos/tickets/tags/team/stats, webhook handler, channel provider |
| `salesforce` | Conector Salesforce (stub) |

## Arquitetura

### Multi-Tenancy e Segurança

Fluxo de request:
```
Request → GetProfileAndOrg (extrai org_id do JWT)
       → SetOrgContext (SET app.current_org no PostgreSQL)
       → View (permission_classes = [IsAuthenticated, HasOrgContext])
       → PostgreSQL RLS filtra automaticamente por org
```

- **`SetOrgContext`** middleware: seta variável de sessão PostgreSQL para RLS
- **`HasOrgContext`** permission: garante que org está presente no request
- **`IsSuperAdmin`** permission: verifica `user.is_superuser` (usado no admin panel)
- **Fail-safe**: sem `app.current_org`, RLS retorna zero linhas

### Views isentas de HasOrgContext
- `OrgProfileCreateView` — fluxo pré-org (criação de organização)
- Auth endpoints — login, token refresh
- `ContactFormSubmitView` — formulário público
- Admin panel views — usam `IsSuperAdmin` (nível plataforma, não org)

### BaseModel e BaseOrgModel

```python
# BaseModel — UUID pk, audit fields (created_at, updated_at, created_by, updated_by)
from common.base import BaseModel

# BaseOrgModel — BaseModel + org FK (para apps novos como integrations, channels)
from common.base import BaseOrgModel
```

### Celery Tasks e RLS

Background tasks não passam pelo middleware. Sempre setar contexto RLS:
```python
from common.tasks import set_rls_context

@app.task
def minha_task(data_id, org_id):
    set_rls_context(org_id)  # OBRIGATÓRIO
    obj = MeuModel.objects.get(id=data_id)
```

### Integrações (Integrations Hub)

Arquitetura plugável:
```
ConnectorRegistry → registra conectores (chatwoot, talkhub_omni, salesforce, etc.)
ChannelRegistry   → registra providers de canal (ChatwootProvider, TalkHubOmniProvider, SmtpNativeProvider)
VariableRegistry  → resolve_to_crm_field() para mapeamento externo→CRM
DataUnifier       → normaliza dados de diferentes fontes
ConflictResolver  → estratégias: last_write_wins, crm_wins, external_wins
```

### Chatwoot Connector

```
chatwoot/
├── connector.py   # ChatwootConnector (BaseConnector) — webhook handlers, sync, group detection
├── provider.py    # ChatwootProvider (ChannelProvider) — send/receive messages
└── apps.py        # Auto-register connector + channel provider
```

**Webhook Events**: `message_created`, `message_updated`, `conversation_created`, `conversation_updated`, `conversation_status_changed`, `contact_created`, `contact_updated`

**Key features**:
- Auto-register webhook no Chatwoot ao conectar
- Detecção automática de grupos (`conversation_type=group`)
- Contact sync: atualiza email/telefone/nome faltantes em contatos existentes
- Status bidirecional com grace period de 30s (CRM→Chatwoot via Celery async)
- Echo prevention para mensagens enviadas pelo CRM

### Conversations Real-Time

```
Frontend (5s poll) → GET /conversations/updates/?since=<ISO>&conversation_id=<UUID>
  → Retorna apenas conversas e mensagens atualizadas desde o último poll
  → Merge incremental no frontend (dedup por ID)
  → Full refresh a cada 60s como fallback
```

## Migrations

### Contacts (14 migrations)
- `0001`-`0010`: Core fields, enterprise constraints
- `0011`: `talkhub_subscriber_id`
- `0012`: `source`, `talkhub_channel_type`, `talkhub_channel_id`
- `0013`: Social media fields (instagram, facebook, tiktok, telegram)
- `0014`: Omni correlation fields (`sms_opt_in`, `email_opt_in`, `omni_user_ns`)

### TalkHub Omni (4 migrations)
- `0001`: TalkHubConnection, TalkHubSyncJob, TalkHubFieldMapping
- `0002`: Enable RLS nas 3 tabelas iniciais
- `0003`: Phase 6 models (TalkHubOmniChannel, TalkHubSyncConfig, TalkHubTeamMember, TalkHubTicketListMapping, OmniStatisticsSnapshot) + update SyncJob choices
- `0004`: Enable RLS nas 5 tabelas Phase 6

### Outros apps novos
- `integrations/0001`: IntegrationConnection, SyncJob, IntegrationLog, WebhookLog, FieldMapping, ConflictLog
- `channels/0001`: ChannelConfig
- `conversations/0001`: Conversation, Message

## Estrutura

```
backend/
├── crm/                    # Settings, URLs, Celery, WSGI
├── common/                 # Core: auth, RLS, middleware, permissions, admin panel
│   ├── middleware/          # GetProfileAndOrg, SetOrgContext
│   ├── permissions.py      # IsAuthenticated, HasOrgContext, IsSuperAdmin
│   ├── rls/                # RLS config, enable/disable SQL
│   ├── views/              # Dashboard, settings, users, teams, tags, org, admin
│   └── management/commands/# manage_rls, create_default_admin, seed_data
├── accounts/
├── contacts/               # 14 migrations (inclui campos TalkHub Omni)
├── leads/                  # 12 migrations (inclui kanban pipeline)
├── opportunity/
├── cases/                  # 10 migrations (inclui kanban + SLA)
├── tasks/
├── invoices/
├── orders/
├── financeiro/
├── integrations/           # Hub genérico de integrações
├── channels/               # Abstração de canais
├── conversations/          # Inbox omnichannel (real-time via fast polling)
├── chatwoot/               # Conector Chatwoot (webhook + sync + channel provider)
├── talkhub_omni/           # Conector TalkHub Omni (4 migrations)
├── salesforce/             # Conector Salesforce (stub, sem models)
├── templates/              # Email templates (todos em pt-BR)
└── requirements.txt
```

## Variáveis de Ambiente

| Variável | Descrição |
|----------|-----------|
| `SECRET_KEY` | Chave secreta Django |
| `ENV_TYPE` | `prod` ou `dev` |
| `ALLOWED_HOSTS` | Hosts permitidos |
| `FRONTEND_URL` | URL do frontend (para magic links e emails) |
| `ADMIN_EMAIL` | Email do superadmin |
| `ADMIN_PASSWORD` | Senha do superadmin |
| `DBNAME` / `DBUSER` / `DBPASSWORD` / `DBHOST` / `DBPORT` | PostgreSQL |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Redis |
| `AWS_BUCKET_NAME` / `AWS_S3_ENDPOINT_URL` / `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | S3 |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | SMTP |
| `TIME_ZONE` | Fuso horário (padrão: `America/Sao_Paulo`) |

## Desenvolvimento

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Testes
```bash
pytest                          # Todos os testes com coverage
pytest --no-cov -x              # Rápido, para no primeiro erro
pytest integrations/tests/      # Módulo específico
pytest -k "test_conflict"       # Por keyword
```

### Comandos úteis
```bash
python manage.py manage_rls --status      # Status RLS
python manage.py manage_rls --verify-user # Verificar user não-superuser
python manage.py seed_data --email admin@talkhub.me
```

## Licença

Software privado.
