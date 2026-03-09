# TalkHub CRM

CRM multi-tenant SaaS completo — Django 5.2 + SvelteKit 2 + PostgreSQL 16 RLS.

**Produção**: [crm.talkhub.me](https://crm.talkhub.me)

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Django 5.2 + Django REST Framework 3.16 |
| Frontend | SvelteKit 2 + Svelte 5 (runes) + TailwindCSS 4 + shadcn-svelte |
| Database | PostgreSQL 16 com Row-Level Security |
| Cache/Broker | Redis 7 |
| Task Queue | Celery 5.6 + Celery Beat |
| Auth | JWT (SimpleJWT) + Google OAuth + Magic Link (passwordless) |
| Storage | MinIO S3 (s3.talkhub.me) |
| Email | SMTP (talkhub@talkhub.me) |
| PDF | WeasyPrint |
| HTTP Client | httpx 0.28 (para integrações externas) |
| Deploy | Docker Swarm + Traefik (HTTPS Let's Encrypt) |
| Monitoramento | Sentry (opcional) |

---

## Módulos CRM

### Core
- **Leads** — Pipeline customizável por org, kanban drag-and-drop, conversão para oportunidade/conta
- **Contas (Accounts)** — Cadastro de empresas, receita anual, moeda, endereço completo
- **Contatos (Contacts)** — Pessoas vinculadas a contas, redes sociais, campos TalkHub Omni (subscriber_id, omni_user_ns, sms/email opt-in)
- **Oportunidades (Opportunities)** — Pipeline de vendas com stages, produtos/line items, valor, probabilidade
- **Casos (Cases)** — Suporte ao cliente, kanban com pipeline customizável, SLA e escalação automática
- **Tarefas (Tasks)** — Kanban, calendário, boards customizados, prioridades, status, conta vinculada

### Faturamento
- **Faturas (Invoices)** — Criação, envio, PDF, status (Rascunho→Enviada→Paga), impostos, descontos
- **Orçamentos (Estimates)** — Propostas com conversão para fatura
- **Faturas Recorrentes** — Geração automática com frequência configurável
- **Produtos** — Catálogo com SKU, preço, categoria, moeda (inclui criptomoedas)

### Financeiro
- **Lançamentos** — Receitas e despesas com categorias (plano de contas)
- **Contas a Pagar / Receber** — Gestão de pagamentos e recebimentos
- **Plano de Contas** — Hierarquia de categorias financeiras
- **Formas de Pagamento** — Cadastro de meios de pagamento
- **Relatórios** — DRE, fluxo de caixa, por período

### Integrations Hub (novo)
- **integrations** — Hub genérico de integrações: conexões, sync jobs, logs, webhooks, field mapping, conflict resolution
- **channels** — Abstração de canais de comunicação (TalkHub Omni, SMTP nativo, Chatwoot, Evolution API, etc.)
- **conversations** — Inbox omnichannel: conversas e mensagens genéricas, independentes de integração
- **talkhub_omni** — Conector TalkHub Omni: sync de contatos, tickets, tags, team members, estatísticas, canais por org

### Metas (Goals)
- **Metas de Vendas** — Definição por usuário, período, tipo (receita/leads/negócios), acompanhamento de progresso

### Plataforma
- **Multi-Tenancy** — Isolamento completo via PostgreSQL RLS
- **Admin Panel** — Painel de superadmin (`/admin-panel`) com KPIs, gestão de orgs e usuários (protegido por `IsSuperAdmin` via `is_superuser`)
- **Equipes (Teams)** — Organização de usuários com permissões
- **Tags** — Sistema flexível de etiquetas
- **Comentários** — Em qualquer registro, com menções @user
- **Anexos** — Upload de arquivos em qualquer módulo
- **Activity Feed** — Log de atividades em tempo real no dashboard
- **Perfil** — Configurações pessoais, foto, dados de contato

### Moedas e Países
- **21 moedas** — BRL, USD, EUR, GBP, JPY, CAD, AUD, CHF, CNY, INR, MXN, ARS, CLP + criptomoedas (BTC, ETH, USDT, USDC, SOL, BNB, XRP, ADA)
- **261 países** — Lista completa traduzida para português
- Todos os campos de moeda/país com **combobox autocomplete + criação inline**

### Autenticação
- **Google OAuth** — Login com conta Google
- **Magic Link** — Login sem senha via e-mail (token de 10 min, rate-limited)
- **JWT** — Access token + refresh token com rotação automática, org_id embutido nos claims
- **Multi-org** — Seleção de organização após login, troca via `switch-org`

---

## Arquitetura de Produção

```
crm.talkhub.me (Traefik — HTTPS via Let's Encrypt)
    │
    │── /api, /admin, /static, /swagger, /media  (prioridade 20)
    │       │
    │       └── crm_backend (Django 5.2 + Gunicorn :8000)
    │              ├── crm_db (PostgreSQL 16 + RLS)
    │              ├── crm_redis (Redis 7)
    │              ├── crm_worker (Celery Worker — emails, sync, tarefas async)
    │              └── crm_beat (Celery Beat — scheduler periódico, sync TalkHub)
    │
    └── /* catch-all  (prioridade 10)
            │
            └── crm_frontend (SvelteKit 2 + Node 22 :3000)
```

### Serviços

| Serviço | Imagem | Porta | CPU | RAM |
|---------|--------|-------|-----|-----|
| crm_db | postgres:16-alpine | 5432 | 1.0 | 1024M |
| crm_backend | talkhub/djangocrm-backend:latest | 8000 | 1.0 | 1024M |
| crm_worker | talkhub/djangocrm-backend:latest | — | 0.5 | 512M |
| crm_beat | talkhub/djangocrm-backend:latest | — | 0.25 | 256M |
| crm_frontend | talkhub/djangocrm-frontend:latest | 3000 | 0.5 | 512M |
| crm_redis | redis:7-alpine | 6379 | 0.5 | 256M |

---

## Estrutura do Projeto

```
crmtalkhub/
├── docker/
│   ├── djangocrm.yaml              # Stack Docker Swarm (produção)
│   ├── Dockerfile.backend           # Build imagem backend
│   ├── Dockerfile.frontend          # Build imagem frontend (multi-stage)
│   ├── entrypoint-prod.sh           # Entrypoint SERVICE_ROLE (web/worker/beat)
│   ├── init-rls-user.sql            # Criação do crm_user PostgreSQL
│   └── server_settings.py.talkhub   # Override settings (MinIO, SMTP, Sentry)
│
├── djangocrm/
│   ├── backend/                      # Django REST API
│   │   ├── crm/                      # Projeto Django (settings, urls, wsgi, celery)
│   │   ├── common/                   # Auth, RLS, middleware, models base, utils, admin panel
│   │   ├── accounts/                 # Empresas
│   │   ├── contacts/                 # Contatos (com campos TalkHub Omni)
│   │   ├── leads/                    # Leads + kanban pipeline
│   │   ├── opportunity/              # Oportunidades + line items
│   │   ├── cases/                    # Casos + kanban pipeline + SLA
│   │   ├── tasks/                    # Tarefas + kanban + boards
│   │   ├── invoices/                 # Faturas, orçamentos, recorrentes, produtos
│   │   ├── orders/                   # Pedidos
│   │   ├── financeiro/               # Módulo financeiro completo
│   │   ├── integrations/             # Hub de integrações genérico
│   │   ├── channels/                 # Abstração de canais de comunicação
│   │   ├── conversations/            # Inbox omnichannel (conversas + mensagens)
│   │   ├── talkhub_omni/             # Conector TalkHub Omni
│   │   ├── salesforce/               # Conector Salesforce (stub)
│   │   ├── templates/                # Templates de email (pt-BR)
│   │   └── requirements.txt
│   │
│   └── frontend/                     # SvelteKit app
│       ├── src/
│       │   ├── routes/
│       │   │   ├── (app)/            # Rotas autenticadas (CRM principal)
│       │   │   │   ├── accounts/
│       │   │   │   ├── contacts/
│       │   │   │   ├── leads/
│       │   │   │   ├── opportunities/
│       │   │   │   ├── cases/
│       │   │   │   ├── tasks/
│       │   │   │   ├── invoices/
│       │   │   │   ├── financeiro/
│       │   │   │   ├── goals/
│       │   │   │   ├── conversations/ # Inbox omnichannel
│       │   │   │   ├── admin-panel/   # Painel superadmin
│       │   │   │   ├── settings/      # Configurações + integrações
│       │   │   │   └── profile/
│       │   │   └── (no-layout)/      # Login, org, verify
│       │   ├── lib/
│       │   │   ├── components/
│       │   │   │   ├── ui/           # shadcn-svelte + custom
│       │   │   │   ├── layout/       # AppSidebar, Header
│       │   │   │   ├── integrations/ # IntegrationCard, TalkHubChannelConfig
│       │   │   │   ├── conversations/# ConversationTimeline
│       │   │   │   └── dashboard/    # MetricsWidget, AgentProductivity, SyncHealthPanel
│       │   │   ├── constants/
│       │   │   ├── stores/
│       │   │   └── api.js
│       │   └── api-helpers.js
│       └── package.json
│
├── redeploy.sh                       # Script de redeploy completo
└── README.md
```

---

## Multi-Tenancy (RLS)

Isolamento de dados via **PostgreSQL Row-Level Security**:

- Variável de sessão: `app.current_org` (setada por `SetOrgContext` middleware)
- Usuário de banco: `crm_user` (NON-superuser — obrigatório para RLS funcionar)
- **Fail-safe**: se `app.current_org` não estiver setado, nenhuma linha é retornada
- Todas as views protegidas com `[IsAuthenticated, HasOrgContext]`
- Views isentas: `OrgProfileCreateView` (pré-org), auth endpoints, `ContactFormSubmitView` (público), admin panel (`IsSuperAdmin`)

### Fluxo de autenticação
```
Login (Google/MagicLink) → token SEM org_id
    → /org (lista orgs do usuário)
    → switch-org → novo token COM org_id
    → todas as chamadas API funcionam com RLS
```

```bash
BACKEND=$(docker ps -q -f name=djangocrm_crm_backend)
docker exec $BACKEND python manage.py manage_rls --status
docker exec $BACKEND python manage.py manage_rls --verify-user
```

---

## Credenciais de Acesso

### Superadmin (criado automaticamente no deploy)
- **Email**: admin@talkhub.me
- **Senha**: definida por `ADMIN_PASSWORD` env var (padrão: `TalkHub2026!`)
- **Acesso**: Admin Panel (`/admin-panel`), gestão de todas as orgs

### Verificação de superadmin
O `IsSuperAdmin` usa `user.is_superuser` (flag do Django), não domínio de email.

---

## Build e Deploy

### Redeploy completo (recomendado)
```bash
./redeploy.sh
```
O script: remove stack → prune → rebuild imagens → recria volumes se necessário → deploy.

### Deploy limpo (reset total)
```bash
# 1. Parar stack
docker stack rm djangocrm
sleep 15

# 2. Remover volumes (PERDE TODOS OS DADOS)
docker volume rm crm_db crm_static crm_media crm_redis

# 3. Redeploy (recria volumes, roda migrations do zero, cria admin)
./redeploy.sh
```

### Rebuild individual
```bash
# Backend
docker build -t talkhub/djangocrm-backend:latest -f docker/Dockerfile.backend .
docker stack deploy -c docker/djangocrm.yaml djangocrm

# Frontend
docker build -t talkhub/djangocrm-frontend:latest \
  -f docker/Dockerfile.frontend \
  --build-arg PUBLIC_DJANGO_API_URL=https://crm.talkhub.me \
  djangocrm/frontend/
docker stack deploy -c docker/djangocrm.yaml djangocrm

# Restart sem rebuild
docker service update --force djangocrm_crm_backend
docker service update --force djangocrm_crm_frontend
```

---

## Comandos de Operação

```bash
BACKEND=$(docker ps -q -f name=djangocrm_crm_backend)

docker exec -it $BACKEND python manage.py shell
docker exec $BACKEND python manage.py migrate
docker exec $BACKEND python manage.py collectstatic --noinput
docker exec $BACKEND python manage.py seed_data --email admin@talkhub.me

# Logs
docker service logs djangocrm_crm_backend --tail 30 --follow
docker service logs djangocrm_crm_frontend --tail 20 --follow

# PostgreSQL
docker exec -it $(docker ps -q -f name=djangocrm_crm_db) psql -U crm_user -d crm_db

# Status
docker stack services djangocrm
```

---

## Guia: Criando Novas Funcionalidades

### 1. Backend (Django REST)

**Modelo** — Herdar de `BaseModel` (UUID pk, audit fields) ou `BaseOrgModel` (+ org FK):
```python
from common.base import BaseModel, AssignableMixin

class Projeto(AssignableMixin, BaseModel):
    name = models.CharField(max_length=255)
    org = models.ForeignKey(Org, on_delete=models.CASCADE, related_name="projetos")
```

**View** — Sempre usar `[IsAuthenticated, HasOrgContext]`:
```python
from common.permissions import IsAuthenticated, HasOrgContext

class ProjetoListView(APIView):
    permission_classes = [IsAuthenticated, HasOrgContext]
```

**RLS**: Adicionar tabela ao `manage_rls` command e criar migration com `get_enable_policy_sql()`.

**Celery Tasks**: Sempre chamar `set_rls_context(org_id)` no início (importar de `common.tasks`).

### 2. Frontend (SvelteKit + Svelte 5)

**Server Action** (`+page.server.js`):
```javascript
import { apiRequest } from '$lib/api-helpers.js';
import { fail } from '@sveltejs/kit';

export const actions = {
  create: async ({ request, locals }) => {
    const data = await request.formData();
    try {
      const result = await apiRequest('/projetos/', {
        method: 'POST',
        body: { name: data.get('name') }
      }, locals);
      return { success: true, data: result };
    } catch (err) {
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  }
};
```

### Padrões Importantes

- Error handling: Backend DRF → `api-helpers.js` extrai erros → `fail()` → `toast.error()`
- Moedas/Países: combobox com criação inline via `$lib/constants/`
- Emails: todos os templates em pt-BR (`backend/templates/`)
- Svelte 5: usar runes (`$state`, `$derived`, `$effect`, `$props`), não `svelte:component`

---

## Variáveis de Ambiente

### Backend
| Variável | Descrição |
|----------|-----------|
| `SECRET_KEY` | Chave secreta Django |
| `ENV_TYPE` | `prod` ou `dev` |
| `ALLOWED_HOSTS` | `crm.talkhub.me,localhost` |
| `FRONTEND_URL` | `https://crm.talkhub.me` |
| `ADMIN_EMAIL` | Email do superadmin |
| `ADMIN_PASSWORD` | Senha do superadmin (criado no deploy) |
| `DBNAME` / `DBUSER` / `DBPASSWORD` / `DBHOST` | PostgreSQL (usar `crm_user`, não `postgres`) |
| `CELERY_BROKER_URL` | `redis://crm_redis:6379/0` |
| `AWS_BUCKET_NAME` / `AWS_S3_ENDPOINT_URL` | MinIO S3 |
| `EMAIL_HOST` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | SMTP |
| `TIME_ZONE` | `America/Sao_Paulo` |

### Frontend
| Variável | Descrição |
|----------|-----------|
| `PUBLIC_DJANGO_API_URL` | `https://crm.talkhub.me` |
| `NODE_ENV` | `production` |
| `ORIGIN` | `https://crm.talkhub.me` |

---

## Troubleshooting

| Problema | Causa | Solução |
|----------|-------|---------|
| Magic link com URL `localhost:5173` | Worker sem `FRONTEND_URL` | Verificar no YAML |
| RLS not enforced | `DBUSER=postgres` (superuser) | Trocar para `crm_user` |
| HTTP 500 em todas as views | Middleware `RequireOrgContext` bloqueando | Usar `SetOrgContext` + `HasOrgContext` permission |
| `column contacts.sms_opt_in does not exist` | Migration faltando | Verificar `contacts/migrations/0014_*` existe |
| Frontend 500 | `PUBLIC_DJANGO_API_URL` errado | Verificar env vars e logs |
| Admin panel não aparece | Usuário não é superuser | Verificar `is_superuser=True` no DB |

---

## Integrações

### Ativas
| Conector | Módulo | Descrição |
|----------|--------|-----------|
| TalkHub Omni | `talkhub_omni` | Sync de contatos, tickets, tags, team members, estatísticas |

### Planejadas
| Serviço | URL | Integração |
|---------|-----|-----------|
| Chatwoot | chat.talkhub.me | Webhook receiver para chat |
| Evolution API | api.talkhub.me | WhatsApp integration |
| EvoAI | ia.talkhub.me | AI features |
| Salesforce | — | Conector bidirecional (stub em `salesforce/`) |

---

---

## Documentação Técnica

| Documento | Descrição |
|-----------|-----------|
| [Diagrama Completo do CRM](DIAGRAMA_CRM_NATIVO.md) | Mapa detalhado de toda a arquitetura: models, campos, relacionamentos, herança, Celery Beat, RLS, fluxo de vendas |
| [Variáveis de Ambiente](docs/ENV_VARIABLES.md) | Referência completa de todas as env vars (backend, frontend, deploy) |

---

## Licença

Software privado — não compartilhe.
