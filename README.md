# TalkHub CRM

CRM multi-tenant SaaS completo — Django 5.2 + SvelteKit 2 + PostgreSQL 16 RLS.

**Produção**: [crm.talkhub.me](https://crm.talkhub.me)

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Django 5.2 + Django REST Framework 3.16 |
| Frontend | SvelteKit 2 + Svelte 5 (runes) + TailwindCSS 4 + shadcn-svelte |
| Virtual Office | Phaser 3 (Next.js) + Socket.io (Node.js) + WebRTC |
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
- **Contatos (Contacts)** — Pessoas vinculadas a contas, redes sociais, campos TalkHub Omni. Múltiplos emails/telefones por contato (primary + secondary + extras). Merge de contatos com preservação de dados e preview. Detecção automática de duplicatas
- **Oportunidades (Opportunities)** — Pipeline de vendas com stages, produtos/line items, valor, probabilidade
- **Casos (Cases)** — Suporte ao cliente, kanban com pipeline customizável, SLA e escalação automática
- **Tarefas (Tasks)** — Kanban, calendário, boards customizados, prioridades, status, conta vinculada

### Faturamento
- **Faturas (Invoices)** — Criação, envio, PDF, status (Rascunho→Enviada→Paga), impostos, descontos
- **Orçamentos (Estimates)** — Propostas com conversão para fatura
- **Faturas Recorrentes** — Geração automática com frequência configurável
- **Produtos** — Catálogo com SKU, preço, categoria, moeda (inclui criptomoedas)

### Financeiro
- **Lançamentos** — Receitas e despesas com categorias (plano de contas), edição segura (3 níveis: tudo editável / metadados / somente leitura conforme status das parcelas)
- **Lançamentos Recorrentes** — Salários, assinaturas, etc. Frequências: mensal, quinzenal, semanal, anual. Sem data fim obrigatória. Celery Beat gera 3 meses à frente automaticamente
- **Taxa de Câmbio** — Fixa (manual) ou variável (automática via API). APIs: open.er-api.com + BCB PTAX (fallback BRL). Cache Redis 4h. Task diário atualiza taxas variáveis
- **Contas a Pagar / Receber** — Gestão de pagamentos e recebimentos, parcelas com status (ABERTO/PAGO/CANCELADO)
- **Plano de Contas** — Hierarquia de categorias financeiras (centro de custo)
- **Formas de Pagamento** — Cadastro de meios de pagamento, edição e remoção via UI
- **Relatórios** — DRE, fluxo de caixa, por período. Parcelas CANCELADO excluídas de todas as somas
- **Moeda da Org** — Integração total com `Org.default_currency` em todo o sistema financeiro

### Integrations Hub
- **integrations** — Hub genérico de integrações: conexões, sync jobs, logs, webhooks, field mapping, conflict resolution
- **channels** — Abstração de canais de comunicação (TalkHub Omni, SMTP nativo, Chatwoot, Evolution API, etc.)
- **conversations** — Inbox omnichannel: conversas e mensagens genéricas, real-time via fast polling (5s incremental), soft-delete com lixeira e restauração (admin)
- **chatwoot** — Conector Chatwoot: webhook bidirecional (7 eventos), sync de conversas/contatos/grupos, envio de mensagens
- **talkhub_omni** — Conector TalkHub Omni: sync de contatos, tickets, tags, team members, estatísticas, canais por org

### Sala Cowork — Escritório Virtual
- **Phaser 3 Game** — Mapa 2D estilo SkyOffice com tilemap, camadas de colisão, cadeiras, mesas
- **Multiplayer em tempo real** — Movimentação via Socket.io com interpolação suave
- **Audio/Vídeo por proximidade** — WebRTC nativo (RTCPeerConnection) ativado por proximidade entre jogadores
- **Chat com balões** — Mensagens aparecem como speech bubbles acima do avatar
- **Sentar em cadeiras** — Pressione E perto de uma cadeira para sentar, com broadcast multiplayer
- **Whiteboard colaborativo** — Quadro branco compartilhado com desenho em tempo real via Socket.io
- **Acesso de convidados** — Endpoint público gera JWT temporário (30min) sem necessidade de conta

### TalkHub Autopilot — Automações, Lembretes e Campanhas
Três apps formam o sistema de automação unificado, acessíveis via `/autopilot` (6 tabs):

- **assistant** — Core scheduler + reminder engine
  - ReminderPolicy: quando/como disparar lembretes para qualquer entidade (5 trigger types: due_date, recurring, cron, relative_date, event_plus_offset)
  - ScheduledJob: fila de execução com idempotência, lock otimista (SELECT FOR UPDATE SKIP LOCKED)
  - 19 preset templates (financeiro, leads, oportunidades, casos, tarefas, faturas)
  - Template engine com interpolação de variáveis por módulo (`{{variable_name}}`)
  - Approval queue: jobs com `approval_policy="manual"` ficam pendentes até aprovação manual
- **automations** — Rule engine com 3 tipos de automação
  - `routine`: Celery Beat (cron/intervalo)
  - `logic_rule`: Django signals (post_save) com condições e ações
  - `social`: Webhooks TalkHub Omni
- **campaigns** — Motor de campanhas de marketing
  - `email_blast`: envio em lote (50/batch, 1s throttle) com tracking pixel + unsubscribe
  - `whatsapp_broadcast`: envio em lote (20/batch, 2s throttle) via TalkHub Omni
  - `nurture_sequence`: multi-step com delay entre steps, tracking por destinatário
- **AI Copilot (IA Assistida)** — Geração de configurações via LLM
  - Prompt em linguagem natural → JSON config validado (automações, lembretes, campanhas)
  - Backend: OpenAI GPT-4o (via `CRM_OPENAI_API_KEY`), graceful degradation se não configurado
  - Frontend: componente `AICopilot.svelte` integrado nos formulários de criação

### Metas (Goals)
- **Metas de Vendas** — Definição por usuário, período, tipo (receita/leads/negócios), acompanhamento de progresso

### Plataforma
- **Multi-Tenancy** — Isolamento completo via PostgreSQL RLS
- **Admin Panel** — Painel de superadmin (`/admin-panel`) com KPIs, gestão de orgs e usuários (protegido por `IsSuperAdmin` via `is_superuser`)
- **Convites** — Sistema de convite por email para novos membros da org, com link de aceitação e vinculação automática
- **Equipes (Teams)** — Organização de usuários com permissões
- **Tags** — Sistema flexível de etiquetas
- **Comentários** — Em qualquer registro, com menções @user
- **Anexos** — Upload de arquivos em qualquer módulo
- **Activity Feed** — Log de atividades em tempo real no dashboard
- **Perfil** — Configurações pessoais, foto, dados de contato
- **Config. da Org** — Nome, razão social, CNPJ, endereço, telefone, email, site, logo (usado em faturas/orçamentos PDF), moeda e país padrão

### Moedas e Países
- **21 moedas** — BRL, USD, EUR, GBP, JPY, CAD, AUD, CHF, CNY, INR, MXN, ARS, CLP + criptomoedas (BTC, ETH, USDT, USDC, SOL, BNB, XRP, ADA)
- **261 países** — Lista completa traduzida para português
- Todos os campos de moeda/país com **combobox autocomplete + criação inline**

### Autenticação
- **Google OAuth** — Login com conta Google (PKCE + state CSRF)
- **Magic Link** — Login sem senha via e-mail (token de 10 min, rate-limited)
- **JWT** — Access token + refresh token com rotação automática, org_id embutido nos claims
- **Multi-org** — Seleção de organização após login, troca via `switch-org`

---

## Arquitetura de Produção

```
crm.talkhub.me (Traefik — HTTPS via Let's Encrypt)
    │
    │── /ws/                                              (prioridade 25)
    │       └── crm_ws (Django WebSocket :8001)
    │
    │── /cowork-ws/                                       (prioridade 22)
    │       └── crm_cowork_backend (Socket.io :3100)
    │
    │── /api, /admin, /static, /swagger, /media,          (prioridade 20)
    │   /invite, /health, /track, /webhooks, /schema
    │       └── crm_backend (Django 5.2 + Gunicorn :8000)
    │              ├── crm_db (PostgreSQL 16 + RLS)
    │              ├── crm_redis (Redis 7)
    │              ├── crm_worker (Celery Worker)
    │              └── crm_beat (Celery Beat)
    │
    │── /cowork-app/                                      (prioridade 18)
    │       └── crm_cowork_front (Next.js + Phaser 3 :3200)
    │
    └── /* catch-all                                      (prioridade 10)
            └── crm_frontend (SvelteKit 2 + Node 22 :3000)
```

### Serviços

| Serviço | Imagem | Porta | Função |
|---------|--------|-------|--------|
| crm_db | postgres:16-alpine | 5432 | Database + RLS |
| crm_backend | djangocrm-backend | 8000 | Django + Gunicorn |
| crm_worker | djangocrm-backend | — | Celery Worker (emails, sync, tarefas async) |
| crm_beat | djangocrm-backend | — | Celery Beat (scheduler periódico) |
| crm_frontend | djangocrm-frontend | 3000 | SvelteKit SSR |
| crm_redis | redis:7-alpine | 6379 | Broker + Cache |
| crm_cowork_backend | cowork-server | 3100 | Socket.io (salas, proximity, WebRTC, chat, whiteboard) |
| crm_cowork_front | cowork-app | 3200 | Next.js + Phaser 3 (escritório virtual) |

---

## Estrutura do Projeto

```
crm.talkhub.me/
├── docker/
│   ├── djangocrm.yaml              # Stack Docker Swarm (produção)
│   ├── Dockerfile.backend           # Python 3.12-slim + Gunicorn
│   ├── Dockerfile.frontend          # Node 22 multi-stage build
│   ├── Dockerfile.cowork-server     # Socket.io cowork server
│   ├── Dockerfile.cowork-app        # Next.js + Phaser 3 cowork frontend
│   ├── entrypoint-prod.sh           # Entrypoint SERVICE_ROLE (web/worker/beat)
│   ├── init-rls-user.sql            # Criação do crm_user PostgreSQL
│   ├── debug-traefik.sh             # Script de diagnóstico Traefik
│   └── backup-db.sh                 # pg_dump + upload S3 opcional
│
├── djangocrm/
│   ├── backend/                      # Django REST API (20 apps)
│   │   ├── crm/                      # Projeto Django (settings, urls, wsgi, celery)
│   │   ├── common/                   # Auth, RLS, middleware, models base, convites, admin panel
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
│   │   ├── conversations/            # Inbox omnichannel (conversas + mensagens + real-time)
│   │   ├── chatwoot/                 # Conector Chatwoot (webhook + sync + channel provider)
│   │   ├── talkhub_omni/             # Conector TalkHub Omni
│   │   ├── cowork/                   # Sala Cowork (models, views, serializers, urls)
│   │   ├── automations/              # Regras de automação (routine, logic_rule, social)
│   │   ├── campaigns/                # Campanhas (email blast, WhatsApp broadcast, nurture)
│   │   ├── assistant/                # Autopilot: scheduler, lembretes, templates, AI copilot
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
│       │   │   │   ├── cowork/        # Sala Cowork (iframe wrapper)
│       │   │   │   ├── users/         # Gestão de membros + convites
│       │   │   │   ├── admin-panel/   # Painel superadmin
│       │   │   │   ├── autopilot/     # Central de automações (6 tabs)
│       │   │   │   ├── automations/  # Regras de automação (legacy)
│       │   │   │   ├── campaigns/    # Campanhas de marketing
│       │   │   │   ├── settings/      # Configurações + integrações
│       │   │   │   └── profile/
│       │   │   └── (no-layout)/      # Login, org, verify
│       │   ├── lib/
│       │   │   ├── components/
│       │   │   │   ├── ui/           # shadcn-svelte + custom
│       │   │   │   ├── layout/       # AppSidebar, Header
│       │   │   │   ├── integrations/ # IntegrationCard, TalkHubChannelConfig
│       │   │   │   ├── conversations/# ConversationTimeline
│       │   │   │   ├── autopilot/   # AICopilot, AutomationCreateForm, CampaignCreateForm
│       │   │   │   ├── cowork/      # CoworkPiP (persistent iframe overlay)
│       │   │   │   ├── financeiro/  # TransactionForm, CashFlowChart, DailyCashFlowChart
│       │   │   │   └── dashboard/    # MetricsWidget, AgentProductivity, SyncHealthPanel
│       │   │   ├── constants/
│       │   │   ├── stores/
│       │   │   └── api.js
│       │   └── api-helpers.js
│       └── package.json
│
├── cowork-server/                    # Socket.io real-time server (Node.js)
│   ├── server.js                    # Salas, state, proximity, WebRTC relay, chat, whiteboard
│   └── package.json
│
├── cowork-app/                       # Phaser 3 virtual office (Next.js)
│   ├── src/app/                     # App router (page.tsx = Phaser game)
│   ├── src/components/              # PhaserGame, Whiteboard
│   ├── src/game/                    # GameScene, Player, Chair, ChatManager
│   ├── src/lib/                     # Socket.io client, WebRTC, postMessage bridge
│   └── package.json
│
├── DIAGRAMA_CRM_NATIVO.md           # Diagrama completo da arquitetura
├── redeploy.sh                       # Script de redeploy completo
├── CLAUDE.md                         # Memória para sessões Claude Code
└── README.md                         # Este arquivo
```

---

## Multi-Tenancy (RLS)

Isolamento de dados via **PostgreSQL Row-Level Security**:

- Variável de sessão: `app.current_org` (setada por `SetOrgContext` middleware)
- Usuário de banco: `crm_user` (NON-superuser — obrigatório para RLS funcionar)
- **Fail-safe**: se `app.current_org` não estiver setado, nenhuma linha é retornada
- Todas as views protegidas com `[IsAuthenticated, HasOrgContext]`
- Views isentas: `OrgProfileCreateView` (pré-org), auth endpoints, `ContactFormSubmitView` (público), admin panel (`IsSuperAdmin`)
- Tabelas sem RLS: `pending_invitation` (precisa ser acessível sem org context)

### Fluxo de autenticação
```
Login (Google/MagicLink) → token SEM org_id
    → /org (lista orgs do usuário)
    → switch-org → novo token COM org_id
    → todas as chamadas API funcionam com RLS
```

### Fluxo de convites
```
Admin envia convite (/users)
    → PendingInvitation criado com token UUID
    → Email enviado com link: /invite/accept/{token}/
    → Django valida token → redireciona para /login?invite={token}
    → Login salva invite_token em cookie
    → Após auth, POST /api/auth/accept-invite/ aceita convite
    → Profile criado na org do convite
    → /org auto-seleciona a org convidada
```

```bash
BACKEND=$(docker ps -q -f name=djangocrm_crm_backend)
docker exec $BACKEND python manage.py manage_rls --status
docker exec $BACKEND python manage.py manage_rls --verify-user
```

---

## Sala Cowork — Escritório Virtual

### Arquitetura
```
SvelteKit /cowork → POST /api/cowork/auth/token/ → JWT (cowork-scoped)
  → iframe loads /cowork-app/ (Next.js + Phaser 3)
  → parent postMessage({ type: "cowork-init", payload: { token, socketUrl } })
  → Next.js connects to /cowork-ws/ (Socket.io)
  → join-room → room-state → real-time presence + movement
```

### Funcionalidades
| Feature | Descrição |
|---------|-----------|
| Mapa 2D | Tilemap SkyOffice com Phaser 3 (CANVAS renderer, zoom 2x) |
| Movimento | WASD/Setas via DOM keytracking (bypass Phaser para funcionar em iframe) |
| Multiplayer | Socket.io room state com interpolação suave de posição |
| Audio/Vídeo | WebRTC nativo por proximidade (PROXIMITY_RADIUS tiles) |
| Chat | Speech bubbles acima do avatar, auto-fade 5s |
| Cadeiras | Pressione E para sentar/levantar, broadcast multiplayer |
| Whiteboard | Quadro branco colaborativo com R key, desenho em tempo real |
| Convidados | Endpoint público `/api/public/cowork/join/<token>/` (JWT 30min) |

### Comunicação
```
SvelteKit (parent) ←→ Next.js (iframe) via postMessage
  parent → iframe: cowork-init (config), cowork-destroy (cleanup)
  iframe → parent: cowork-ready, cowork-status, cowork-error
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
./redeploy.sh              # Rebuild + deploy (preserva dados)
./redeploy.sh --no-cache   # Rebuild sem cache Docker
./redeploy.sh --skip-build # Deploy sem rebuild (imagens existentes)
./redeploy.sh --clean-db   # Recria volume do banco (APAGA DADOS)
./redeploy.sh --clean-all  # Recria TODOS os volumes (APAGA TUDO)
```
O script: remove stack → prune → rebuild → deploy → **verifica serviços, migrations e RLS automaticamente**.

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

# Cowork
docker build -t talkhub/cowork-server:latest -f docker/Dockerfile.cowork-server .
docker build -t talkhub/cowork-app:latest -f docker/Dockerfile.cowork-app .
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
docker service logs djangocrm_crm_cowork_backend --tail 20 --follow
docker service logs djangocrm_crm_cowork_front --tail 20 --follow

# PostgreSQL
docker exec -it $(docker ps -q -f name=djangocrm_crm_db) psql -U crm_user -d crm_db

# Status
docker stack services djangocrm

# Debug Traefik
bash docker/debug-traefik.sh
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
| `CRM_OPENAI_API_KEY` | AI Copilot — OpenAI GPT-4o (opcional, graceful degradation) |
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
| Convite não funciona | `/invite/` não roteado para backend | Verificar Traefik PathPrefix no YAML |
| Cowork congela | Player preso em colisão | Verificar spawn position e collision delay |

---

## Integrações

### Ativas
| Conector | Módulo | Descrição |
|----------|--------|-----------|
| TalkHub Omni | `talkhub_omni` | Sync de contatos, tickets, tags, team members, estatísticas |
| Chatwoot | `chatwoot` | Webhook bidirecional (7 eventos), sync conversas/contatos/grupos, envio de mensagens, status sync |
| SMTP | `channels` | Email como canal de conversação, envio/recebimento via IMAP polling (2min) |

### Chatwoot — Detalhes

**Webhook**: `POST /api/integrations/webhooks/chatwoot/<webhook_token>/` (AllowAny, HMAC-SHA256)

Cada integração recebe um `webhook_token` único auto-gerado, criando URLs exclusivas por org para isolamento multi-tenant seguro. URL legacy sem token ainda funciona como fallback.

Eventos suportados:
- `message_created` / `message_updated` — mensagens em tempo real + edição
- `conversation_created` / `conversation_updated` / `conversation_status_changed` — conversas e status
- `contact_created` / `contact_updated` — sync de contatos (atualiza email/telefone/nome faltantes)

Funcionalidades:
- **Grupos**: Detecção automática via múltiplas heurísticas: `conversation_type=group`, `additional_attributes.type=group`, `"(GROUP)"` no nome do contato, `chat_name_or_title`/`group_name`
- **Status bidirecional**: CRM→Chatwoot via Celery async (`toggle_status` API), com grace period de 30s para não reverter
- **Deduplicação de conversas/mensagens**: Dedup por `chatwoot_message_id` / `chatwoot_conversation_id` no `metadata_json`
- **Deduplicação de contatos**: `_get_or_create_contact` busca por: (1) chatwoot_id armazenado na description, (2) email, (3) phone, (4) nome exato para contatos sem email/phone (grupos). `_dedup_contacts()` roda automaticamente no início de cada sync para mesclar duplicatas existentes
- **Sync de todos os status**: A API Chatwoot `GET /conversations` retorna apenas `status=open` por padrão. O sync itera todos: open, pending, resolved, snoozed
- **Echo prevention**: Mensagens `outgoing` com `external_created=True` são ignoradas
- **Auto-registro**: Webhook é registrado automaticamente no Chatwoot ao conectar

**Frontend Real-Time**:
- Fast poll 5s via `GET /conversations/updates/?since=<ISO>&conversation_id=<UUID>` (somente deltas)
- Full refresh 60s como fallback
- Merge incremental de conversas e mensagens (dedup por ID)

### Planejadas
| Serviço | URL | Integração |
|---------|-----|-----------|
| Evolution API | api.talkhub.me | WhatsApp integration |
| EvoAI | ia.talkhub.me | AI features |
| Salesforce | — | Conector bidirecional (stub em `salesforce/`) |

---

## Documentação Técnica

| Documento | Descrição |
|-----------|-----------|
| [Diagrama Completo do CRM](DIAGRAMA_CRM_NATIVO.md) | Mapa detalhado de toda a arquitetura: models, campos, relacionamentos, herança, Celery Beat, RLS, fluxo de vendas |
| [Variáveis de Ambiente](docs/ENV_VARIABLES.md) | Referência completa de todas as env vars (backend, frontend, deploy) |
| [Guia: Novo Conector](djangocrm/backend/integrations/docs/new_connector_guide.md) | Como criar um novo conector de integração usando BaseConnector |
| [CLAUDE.md](CLAUDE.md) | Memória para sessões Claude Code — arquitetura, gotchas, file map |

---

## Licença

Software privado — não compartilhe.
