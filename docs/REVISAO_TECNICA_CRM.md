# REVISAO TECNICA COMPLETA - TalkHub CRM

> Analise profunda do sistema CRM conversacional TalkHub
> Data: 2026-03-07
> Escopo: Backend, Frontend, Deploy, Seguranca, Arquitetura

---

## SUMARIO EXECUTIVO

O TalkHub CRM e um sistema CRM multi-tenant SaaS em transformacao para CRM conversacional, construido com **Django 5.2 + SvelteKit 2 + PostgreSQL 16 RLS**. A analise cobriu **15 apps Django**, **224 componentes Svelte**, **120+ tabelas com RLS**, **6 servicos Docker Swarm** e **30+ Celery tasks**.

### Veredicto Geral

| Area | Status | Nota |
|------|--------|------|
| Arquitetura Backend | Solida | Patterns bem definidos, RLS completo |
| Arquitetura Frontend | Boa | Svelte 5 runes, auth robusto com PKCE |
| Multi-Tenancy (RLS) | Excelente | Fail-safe, 120+ tabelas protegidas |
| Seguranca | Atencao Necessaria | Secrets expostos no YAML, localStorage redundante |
| Deploy | Funcional | Docker Swarm maduro, falta HA e backups |
| Conversational CRM | Em progresso | channels + conversations + talkhub_omni implementados |

### Metricas do Sistema

- **15 apps Django** (accounts, contacts, leads, opportunity, cases, tasks, invoices, orders, financeiro, integrations, channels, conversations, talkhub_omni, automations, campaigns)
- **90+ models** com org FK
- **120+ endpoints REST**
- **30+ Celery tasks** (periodicas + on-demand)
- **224 componentes Svelte**
- **6 servicos Docker Swarm**

---

## 1. ARQUITETURA GERAL

```
Frontend (SvelteKit 2 + Svelte 5 Runes)
    |  HTTPS (Traefik + Let's Encrypt)
    v
Backend (Django 5.2 + DRF 3.16)
    |-- PostgreSQL 16 + RLS (77+ tabelas)
    |-- Redis 7 (broker + cache)
    |-- Celery Worker (tasks async)
    |-- Celery Beat (scheduler periodico)
    |-- MinIO S3 (storage)
    |-- SMTP Titan (email)
```

### Stack Tecnologico

| Camada | Tecnologia | Versao |
|--------|-----------|--------|
| Backend | Django + DRF | 5.2 + 3.16 |
| Frontend | SvelteKit + Svelte | 2.53 + 5.53 |
| Database | PostgreSQL + RLS | 16-alpine |
| Cache/Broker | Redis | 7-alpine |
| Task Queue | Celery + Beat | 5.6 |
| Auth | JWT (SimpleJWT) + Google OAuth + Magic Link | - |
| Storage | MinIO S3 | - |
| UI | TailwindCSS 4 + shadcn-svelte (bits-ui) | 4.2 + 2.16 |
| Deploy | Docker Swarm + Traefik | - |
| Mobile | Flutter (em desenvolvimento) | - |

---

## 2. ANALISE DO BACKEND

### 2.1 Models por App

#### accounts (Empresas)
- `Account` - org FK, assigned_to M2M(Profile), teams M2M, contacts M2M, tags M2M
- `AccountEmail` - org FK, from_account FK(Account), recipients M2M(Contact)
- `AccountEmailLog` - org FK, email FK(AccountEmail), contact FK(Contact)

#### contacts (Contatos)
- `Contact` - org FK, account FK(Account), assigned_to M2M, teams M2M, tags M2M
- Campos TalkHub: talkhub_subscriber_id, omni_user_ns, sms_opt_in, email_opt_in

#### leads (Leads + Pipeline)
- `Lead` - org FK, stage FK(LeadStage), contacts M2M, omni_ticket_item_id
- `LeadPipeline` - org FK, is_default, auto_create_opportunity
- `LeadStage` - org FK, pipeline FK(LeadPipeline), maps_to_status, wip_limit

#### opportunity (Oportunidades + Metas)
- `Opportunity` - org FK, account FK, lead FK, contacts M2M, stage, probability
- `OpportunityLineItem` - org FK, opportunity FK, product FK
- `StageAgingConfig` - org FK, stage, max_days (deteccao de deals estagnados)
- `SalesGoal` - org FK, assigned_to FK, target_value, goal_type
- `GoalBreakdown` - org FK, goal FK, breakdown_type

#### cases (Suporte + SLA)
- `Case` - org FK, stage FK(CaseStage), sla_priority, escalation_level
- `Solution` - org FK, cases M2M (base de conhecimento)
- `CasePipeline` - org FK, sla_priority_multipliers JSONField
- `CaseStage` - org FK, pipeline FK

#### tasks (Tarefas + Boards)
- `Task` - org FK, stage FK(TaskStage), account/opportunity/case/lead FKs
- `Board` / `BoardColumn` / `BoardTask` - org FK, kanban customizado
- `TaskPipeline` / `TaskStage` - org FK

#### invoices (Faturamento)
- `Invoice` - org FK, account FK, contact FK, status, amount
- `InvoiceLineItem` - org FK, invoice FK, product FK
- `Product` - org FK, sku, price, category
- `Estimate` / `RecurringInvoice` - org FK

#### orders (Pedidos)
- `Order` - org FK (BaseOrgModel), account FK, contact FK
- `OrderLineItem` - org FK (BaseOrgModel), order FK, product FK

#### financeiro (Financeiro)
- `PlanoDeContasGrupo` / `PlanoDeContas` - org FK, hierarquia financeira
- `FormaPagamento` - org FK
- `Lancamento` - org FK, account FK, invoice FK, multi-moeda
- `Parcela` - org FK, lancamento FK, status pagamento
- `PaymentTransaction` - org FK, campo criptografado (Fernet)

#### integrations (Hub de Integracoes)
- `IntegrationConnection` - org FK, connector_slug, health_status
- `SyncJob` - org FK, status, progress JSONField
- `IntegrationLog` / `WebhookLog` - org FK
- `FieldMapping` - org FK, mapeamento de campos
- `ConflictLog` - org FK, resolucao de conflitos
- `OrgFeatureFlag` - org FK, feature flags por org

#### channels (Canais de Comunicacao)
- `ChannelConfig` - org FK, channel_type, config_json, capabilities_json

#### conversations (Inbox Omnichannel)
- `Conversation` - org FK, contact FK, assigned_to FK, omni_user_ns, tags M2M
- `Message` - org FK, conversation FK, direction, msg_type, metadata_json

#### talkhub_omni (Conector TalkHub)
- `TalkHubConnection` - org OneToOne, api_key, is_connected
- `TalkHubSyncConfig` - org OneToOne, toggles de sync
- `TalkHubOmniChannel` - org FK, channel_type
- `TalkHubTeamMember` - org FK, omni_agent_id, crm_profile FK
- `TalkHubTicketListMapping` - org FK, pipeline mappings
- `OmniStatisticsSnapshot` - org FK, metricas

#### automations (Automacoes)
- `Automation` - org FK, automation_type, config_json, run tracking
- `AutomationLog` - org FK, automation FK, status, trigger_data

#### campaigns (Campanhas Marketing)
- `Campaign` - org FK, campaign_type, status, contadores
- `CampaignAudience` - org FK, criterios de audiencia
- `CampaignRecipient` - org FK, contact FK, status delivery
- `CampaignStep` - org FK, campaign FK, step_order, delay

### 2.2 Middleware Stack

```
Security -> WhiteNoise -> Session -> CSRF -> Auth -> CORS
-> CurrentRequestUser (crum) -> GetProfileAndOrg -> SetOrgContext (RLS)
```

### 2.3 Permissoes

- `IsAuthenticated` + `HasOrgContext` em todas as views protegidas
- Role-based: ADMIN ve tudo, outros filtrados por created_by/assigned_to
- `IsSuperAdmin` (is_superuser) para admin panel
- `AllowAny` em: webhooks, campaign tracking, CreateLeadFromSite, PIX webhook

### 2.4 Celery Tasks (30+)

**Periodicas:**
- A cada 1 min: process_due_routines, check_scheduled_campaigns
- A cada 5 min: periodic_sync_contacts, check_pending_syncs
- A cada 10 min: periodic_sync_tickets, check_integration_health
- A cada 15 min: check_sla_breaches, reconcile_pix_transactions
- A cada 30 min: recalculate_goal_breakdowns
- Horaria: periodic_sync_statistics
- Diarias: recurring_invoices, overdue_invoices, payment_reminders, stale_opportunities, goal_milestones, sync_tags, sync_team_members, cleanup_logs, expire_invitations, review_integrations

---

## 3. ANALISE DO FRONTEND

### 3.1 Rotas e Server Actions

| Rota | Load | Actions | Endpoints API |
|------|------|---------|--------------|
| /accounts | accounts (active/closed) | create, update, delete, deactivate | /accounts/, /users/, /contacts/, /tags/ |
| /contacts | contacts, accounts, tags | create, update, delete | /contacts/, /accounts/, /tags/ |
| /leads | leads (open/closed), kanban | create, update, delete, convert, duplicate | /leads/, /leads/kanban/, /users/, /teams/ |
| /opportunities | list paginada | create, update | /opportunities/ |
| /cases | list paginada, kanban | create, update | /cases/, /cases/kanban/ |
| /tasks | list, board, calendar | create, update | /tasks/, /boards/ |
| /invoices | list + sub-rotas | create, update, delete | /invoices/, /invoices/templates/ |
| /conversations | filtered list | send message, assign | /conversations/, /channels/ |
| /conversations/[id] | conversation + messages | send, assign, bot control | /conversations/{id}/messages/ |
| /financeiro | dashboard + reports | lancamentos, parcelas | /financeiro/reports/ |
| /goals | metas de vendas | create, update | /opportunities/goals/ |
| /campaigns | list + analytics | create, schedule, pause | /campaigns/ |
| /settings/talkhub-omni | status check | connect, disconnect | /talkhub_omni/ |
| /admin-panel | KPIs, orgs, users | manage orgs/users | /admin-panel/ |

### 3.2 Camada API

**api.js (client-side):**
- axios com interceptors para JWT auto-refresh
- Factory `createCrudApi()` para CRUD generico
- Modulos: financeiro, salesforce, talkhubOmni

**api-helpers.js (server-side):**
- Usado em +page.server.js para SSR
- Token source: httpOnly cookies
- Transformacao snake_case <-> camelCase
- Extracao de erros Django field-level

### 3.3 Autenticacao Frontend

- JWT em httpOnly cookies (seguro contra XSS)
- PKCE completo para Google OAuth
- State parameter para CSRF protection
- Auto-refresh transparente de tokens
- Org context embutido no JWT payload
- Magic Link via server action

### 3.4 Componentes UI (224 arquivos .svelte)

- **Primitivos**: button, dialog, dropdown, badge, avatar, input, select, tooltip
- **CRM-especificos**: CrmTable, CrmDrawer, CommentSection, FilterBar
- **Kanban**: LeadKanban, CaseKanban, TaskKanban (svelte-dnd-action)
- **Layout**: AppSidebar, PageHeader, Pagination
- **Conversations**: ConversationTimeline (inbox omnichannel)
- **Dashboard**: MetricsWidget, AgentProductivity, SyncHealthPanel
- **Financeiro**: DRE, FluxoCaixa, ReportDashboard

---

## 4. ANALISE DE DEPLOY

### 4.1 Servicos Docker Swarm

| Servico | Imagem | CPU | RAM | Replicas |
|---------|--------|-----|-----|----------|
| crm_db | postgres:16-alpine | 1.0 | 1024M | 1 |
| crm_backend | djangocrm-backend:latest | 1.0 | 1024M | 1 |
| crm_worker | djangocrm-backend:latest | 0.5 | 512M | 1 |
| crm_beat | djangocrm-backend:latest | 0.25 | 256M | 1 |
| crm_frontend | djangocrm-frontend:latest | 0.5 | 512M | 1 |
| crm_redis | redis:7-alpine | 0.5 | 256M | 1 |
| **Total** | | **3.75** | **3.5GB** | **6** |

### 4.2 CI/CD (GitHub Actions)

- **tests.yml**: pytest (backend) + eslint/svelte-check/build (frontend)
- **codeql-analysis.yml**: Security scan Python (semanal)
- Sem pipeline automatizado de build -> push -> deploy

### 4.3 Volumes Persistentes

- `crm_db` - dados PostgreSQL
- `crm_static` - arquivos estaticos Django
- `crm_media` - uploads de usuarios
- `crm_redis` - persistencia AOF

---

## 5. INCONSISTENCIAS E PROBLEMAS ENCONTRADOS

### 5.1 CRITICOS (Corrigir Imediatamente)

#### [C1] Secrets Expostos no YAML
**Local**: `docker/djangocrm.yaml`
**Problema**: Senhas hardcoded no arquivo de compose (DB, SMTP, Admin, SECRET_KEY)
**Risco**: Se repositorio for comprometido, todas as credenciais vazam
**Correcao**: Usar Docker secrets, arquivo .env com chmod 600, ou secret manager externo

#### [C2] localStorage Token Redundante (Vulnerabilidade XSS)
**Local**: `frontend/src/lib/api.js`
**Problema**: Tokens JWT armazenados em localStorage ALEM dos httpOnly cookies
**Risco**: XSS pode roubar tokens do localStorage, anulando a protecao dos httpOnly cookies
**Correcao**: Remover completamente o armazenamento em localStorage; usar apenas httpOnly cookies

#### [C3] Inconsistencia de Senha RLS
**Local**: `docker/init-rls-user.sql` vs `docker/djangocrm.yaml`
**Problema**: `init-rls-user.sql` tem senha hardcoded que nao aceita override via env var
**Risco**: Se CRM_DB_PASSWORD for alterado, o SQL init mantem a senha antiga -> falha de conexao
**Correcao**: Gerar SQL dinamicamente no entrypoint ou usar template

#### [C4] Redis Sem Senha
**Local**: `docker/djangocrm.yaml` (servico crm_redis)
**Problema**: Redis rodando sem `requirepass`
**Risco**: Se rede comprometida, atacante pode manipular filas Celery
**Correcao**: Adicionar `--requirepass $REDIS_PASSWORD` e atualizar CELERY_BROKER_URL

### 5.2 ALTOS (Corrigir em Breve)

#### [A1] Validacao de Org em ForeignKeys Cruzadas
**Local**: Multiplos models (OrderLineItem, OpportunityLineItem, Lead->Account, Task->Case)
**Problema**: ForeignKeys entre models org-scoped nao validam que ambos pertencem a mesma org
**Risco**: Potencial vazamento de dados cross-tenant via API manipulada
**Correcao**:
```python
def save(self, *args, **kwargs):
    if self.product_id and self.product.org_id != self.org_id:
        raise ValidationError("Produto deve pertencer a mesma organizacao")
    super().save(*args, **kwargs)
```

#### [A2] N+1 Queries em Views Criticas
**Local**: `opportunity/models.py`, `leads/models.py`
**Problema**:
- `Opportunity.get_aging_status()` faz 1 query por oportunidade (StageAgingConfig)
- `Lead.primary_contact` faz query a cada acesso
- `SalesGoal.compute_progress()` queries nao otimizadas
**Risco**: Performance degradada com volume de dados
**Correcao**: Cache de configs, select_related/prefetch_related nos querysets

#### [A3] Invoices URLs Vazio
**Local**: `backend/invoices/urls.py`
**Problema**: App invoices tem models e serializers mas `urls.py` esta vazio - sem endpoints REST
**Risco**: Frontend pode estar usando endpoints que nao existem no backend
**Correcao**: Implementar CRUD completo ou verificar se rotas estao em outro lugar

#### [A4] Models Deprecated Nao Removidos
**Local**: `backend/talkhub_omni/models.py`
**Problema**: `TalkHubSyncJob` e `TalkHubFieldMapping` marcados como deprecated mas ainda no schema
**Risco**: Confusao, duplicacao com models genericos em `integrations`
**Correcao**: Migrar dados para `integrations.SyncJob`/`FieldMapping` e remover

#### [A5] Typo no Lead Sources
**Local**: `frontend/src/routes/(app)/leads/+page.server.js`
**Problema**: Array validSources contem `'compaign'` em vez de `'campaign'`
**Risco**: Leads criados por campanha podem nao ser categorizados corretamente
**Correcao**: Renomear para `'campaign'`

#### [A6] Campos Duplicados em Contact
**Local**: `backend/contacts/models.py`
**Problema**: `talkhub_subscriber_id` e `omni_user_ns` servem o mesmo proposito
**Risco**: Dados inconsistentes, confusao na sincronizacao
**Correcao**: Consolidar em um unico campo, criar migration de dados

#### ~~[A7] Health Checks Ausentes~~ — CORRIGIDO
**Status**: Resolvido. Health checks adicionados em ambos Dockerfiles (`/health/` backend, `/` frontend) com interval 30s, timeout 5s e start_period 60s.

### 5.3 MEDIOS (Melhorar Qualidade)

#### [M1] Padrao de Heranca Inconsistente
**Problema**: Algumas apps usam `BaseOrgModel` (invoices, orders, financeiro), outras usam `OrgScopedMixin + BaseModel` (accounts, leads, cases)
**Correcao**: Padronizar em `BaseOrgModel` para novos models

#### [M2] Naming de Serializers Inconsistente
**Problema**: Metade dos apps usa `serializer.py` (singular), outra metade `serializers.py` (plural)
- Singular: accounts, cases, common, contacts, invoices, leads, opportunity, tasks
- Plural: automations, campaigns, channels, conversations, integrations, financeiro, talkhub_omni
**Correcao**: Padronizar para `serializers.py` (convencao Django)

#### [M3] Stage-Pipeline Sem Validacao
**Problema**: Lead.stage, Case.stage, Task.stage nao validam que o stage pertence ao pipeline correto
**Correcao**: Adicionar validacao no save()

#### [M4] Validacao de Formularios Frontend Fraca
**Problema**: Sem validacao de email, telefone, ranges numericos no frontend (depende 100% do backend)
**Correcao**: Adicionar validacao client-side (libphonenumber-js ja importado mas nao usado)

#### [M5] strictNullChecks Desabilitado
**Local**: `frontend/jsconfig.json`
**Problema**: `strictNullChecks: false` mascara bugs de null/undefined
**Correcao**: Habilitar progressivamente

#### [M6] Criptografia Fragil (PaymentTransaction)
**Local**: `backend/financeiro/models.py`
**Problema**: Encriptacao baseada em property (getter/setter) pode ser bypassed por operacoes bulk do ORM
**Correcao**: Usar pgcrypto ou campo com encriptacao transparente

#### ~~[M7] Containers Rodando como Root~~ — CORRIGIDO
**Status**: Resolvido. Ambos Dockerfiles criam usuario `app` (non-root) e usam `USER app`.

#### [M8] M2M Handling Verboso nas Views
**Problema**: Cada view repete logica manual de parsing JSON + clear + add para M2M fields
**Correcao**: Extrair para utility function ou usar serializer mixin

#### ~~[M9] Sem Backup Automatizado~~ — CORRIGIDO
**Status**: Resolvido. Script `docker/backup-db.sh` implementado com pg_dump comprimido, retencao de 30 dias e upload opcional para S3 (`--upload`).

#### [M10] Sem Rate Limiting
**Problema**: Nenhum rate limit em endpoints publicos ou de autenticacao
**Correcao**: Adicionar middleware Traefik ou django-ratelimit

### 5.4 BAIXOS (Nice to Have)

#### [B1] Typo em AccountEmail
**Local**: `backend/accounts/models.py`
**Problema**: `related_name="recieved_email"` (correto: `received_email`)

#### [B2] Soft Deletes Ausentes
**Problema**: Sem suporte a exclusao logica (dados perdidos permanentemente)

#### [B3] Audit History Ausente
**Problema**: Apenas created_by/updated_by, sem historico de alteracoes

#### [B4] Frontend API URL em Build-Time
**Problema**: PUBLIC_DJANGO_API_URL e build-arg, nao runtime env (requer rebuild para trocar)

#### [B5] CodeQL Apenas Python
**Problema**: Security scanning so para Python, nao JavaScript/TypeScript

---

## 6. MAPA COMPLETO DE ENDPOINTS

### Autenticacao (7 endpoints)
```
POST /api/auth/refresh-token/        -> JWT refresh
GET  /api/auth/me/                   -> Usuario atual
GET  /api/auth/profile/              -> Perfil detalhado
POST /api/auth/switch-org/           -> Trocar organizacao
POST /api/auth/google/callback/      -> Google OAuth callback
POST /api/auth/google/               -> Google ID token login
POST /api/auth/magic-link/request/   -> Solicitar magic link
POST /api/auth/magic-link/verify/    -> Verificar magic link
POST /api/auth/accept-invite/        -> Aceitar convite
```

### Organizacao & Perfil (8 endpoints)
```
GET/POST /api/org/                   -> Listar/criar orgs
PUT      /api/org/settings/          -> Configuracoes da org
PUT      /api/org/<pk>/              -> Atualizar org
GET/PUT  /api/profile/               -> Perfil do usuario
GET      /api/users/get-teams-and-users/ -> Times e usuarios
GET      /api/users/                 -> Lista de usuarios
GET/PUT  /api/user/<pk>/             -> Detalhe usuario
PUT      /api/user/<pk>/status/      -> Status do usuario
```

### Accounts (5 endpoints)
```
GET/POST /api/accounts/              -> Listar/criar
GET/PUT/DELETE /api/accounts/<pk>/   -> CRUD detalhe
POST     /api/accounts/<pk>/create_mail/ -> Enviar email
POST/PUT/DELETE /api/accounts/comment/<pk>/ -> Comentarios
DELETE   /api/accounts/attachment/<pk>/ -> Remover anexo
```

### Contacts (6 endpoints)
```
GET/POST /api/contacts/              -> Listar/criar
GET      /api/contacts/search/       -> Busca autocomplete
GET      /api/contacts/<contact_id>/conversations/ -> Conversas do contato
GET/PUT/DELETE /api/contacts/<pk>/   -> CRUD detalhe
POST/PUT/DELETE /api/contacts/comment/<pk>/ -> Comentarios
DELETE   /api/contacts/attachment/<pk>/ -> Remover anexo
```

### Leads (14 endpoints)
```
GET/POST /api/leads/                 -> Listar/criar
POST     /api/leads/upload/          -> Import CSV
GET/PUT/DELETE /api/leads/<pk>/      -> CRUD detalhe
POST     /api/leads/<pk>/move/       -> Mover no kanban
GET      /api/leads/kanban/          -> Vista kanban
GET/POST /api/leads/pipelines/       -> CRUD pipelines
GET/PUT/DELETE /api/leads/pipelines/<pk>/ -> Detalhe pipeline
POST     /api/leads/pipelines/<pk>/stages/ -> Criar stage
POST     /api/leads/pipelines/<pk>/stages/reorder/ -> Reordenar
PUT/DELETE /api/leads/stages/<pk>/   -> Detalhe stage
POST     /api/leads/create-from-site/ -> Criar lead externo (publico)
```

### Opportunities (14 endpoints)
```
GET/POST /api/opportunities/         -> Listar/criar
GET/PUT/DELETE /api/opportunities/<pk>/ -> CRUD detalhe
GET/POST /api/opportunities/goals/   -> Metas de vendas
GET      /api/opportunities/goals/dashboard/ -> Dashboard metas
GET      /api/opportunities/goals/leaderboard/ -> Ranking
GET/PUT/DELETE /api/opportunities/goals/<pk>/ -> Detalhe meta
GET/POST /api/opportunities/<id>/line-items/ -> Line items
PUT/DELETE /api/opportunities/<id>/line-items/<id>/ -> Detalhe item
GET/PUT  /api/opportunities/aging-config/ -> Config envelhecimento
```

### Cases (16 endpoints)
```
GET/POST /api/cases/                 -> Listar/criar
GET/PUT/DELETE /api/cases/<pk>/      -> CRUD detalhe
POST     /api/cases/<pk>/move/       -> Mover no kanban
POST     /api/cases/<pk>/tasks/      -> Criar task vinculada
GET      /api/cases/kanban/          -> Vista kanban
GET/POST /api/cases/pipelines/       -> CRUD pipelines
GET/PUT/DELETE /api/cases/pipelines/<pk>/ -> Detalhe pipeline
POST     /api/cases/pipelines/<pk>/stages/ -> Criar stage
POST     /api/cases/pipelines/<pk>/stages/reorder/ -> Reordenar
PUT/DELETE /api/cases/stages/<pk>/   -> Detalhe stage
GET/POST /api/cases/solutions/       -> Knowledge base
GET/PUT/DELETE /api/cases/solutions/<pk>/ -> Detalhe solucao
POST     /api/cases/solutions/<pk>/publish/ -> Publicar
POST     /api/cases/solutions/<pk>/unpublish/ -> Despublicar
```

### Tasks (16 endpoints)
```
GET/POST /api/tasks/                 -> Listar/criar
GET/PUT/DELETE /api/tasks/<pk>/      -> CRUD detalhe
POST     /api/tasks/<pk>/move/       -> Mover no kanban
GET      /api/tasks/kanban/          -> Vista kanban
Pipelines: mesma estrutura de leads/cases
Boards:
GET/POST /api/boards/                -> Listar/criar boards
GET/PUT/DELETE /api/boards/<pk>/     -> Detalhe board
GET/POST /api/boards/<pk>/columns/   -> Colunas
GET/POST /api/boards/columns/<pk>/tasks/ -> Tasks da coluna
GET/PUT/DELETE /api/boards/tasks/<pk>/ -> Detalhe board task
```

### Conversations (6 endpoints)
```
GET      /api/conversations/         -> Listar (filtros: channel, status, assigned)
GET/PUT  /api/conversations/<pk>/    -> Detalhe
GET      /api/conversations/<id>/messages/ -> Mensagens
POST     /api/conversations/<id>/messages/create/ -> Enviar mensagem
POST     /api/conversations/<pk>/<action>/ -> Assign/unassign
POST     /api/conversations/<pk>/bot/<action>/ -> Pause/resume bot
```

### Channels (4 endpoints)
```
GET/POST /api/channels/              -> Listar/criar configs
GET      /api/channels/available/    -> Provedores disponiveis
GET      /api/channels/for-action/<action>/ -> Canais por acao
PUT/DELETE /api/channels/<pk>/       -> Detalhe config
POST     /api/channels/<pk>/test/    -> Testar conexao
```

### Integrations (14 endpoints)
```
GET      /api/integrations/          -> Listar integracoes
GET      /api/integrations/<slug>/   -> Detalhe
POST     /api/integrations/<slug>/connect/ -> Conectar
POST     /api/integrations/<slug>/disconnect/ -> Desconectar
GET      /api/integrations/<slug>/health/ -> Status saude
POST     /api/integrations/<slug>/sync/ -> Iniciar sync
GET      /api/integrations/<slug>/sync/<job_id>/ -> Status job
GET      /api/integrations/health/   -> Dashboard saude geral
GET      /api/integrations/logs/     -> Logs
GET      /api/integrations/webhooks/logs/ -> Webhook logs
POST     /api/integrations/webhooks/<slug>/ -> Webhook receiver (publico)
GET/POST /api/integrations/field-mappings/ -> Mapeamento campos
GET/POST /api/integrations/conflicts/ -> Conflitos
GET/PUT  /api/integrations/flags/    -> Feature flags
```

### TalkHub Omni (30+ endpoints)
```
Conexao: status, credentials, connect, disconnect
Canais: channel-config (list, detail, test)
Sync: config, now, history, jobs, contacts, tickets
Contatos: push, chat-history, opt, tags, labels, pause/resume bot, user-fields, assign
Mensagens: send text/sms/email/content/whatsapp-template/flow, broadcast
Admin: ticket-list-mappings, team-members, analytics, workspace, flows, channels
```

### Automations (3 endpoints)
```
GET/POST /api/automations/           -> Listar/criar
GET/PUT/DELETE /api/automations/<pk>/ -> CRUD detalhe
GET      /api/automations/<pk>/logs/ -> Historico execucao
```

### Campaigns (10 endpoints)
```
GET/POST /api/campaigns/             -> Listar/criar
GET/PUT/DELETE /api/campaigns/<pk>/  -> CRUD detalhe
GET/POST /api/campaigns/<id>/audiences/ -> Audiencias
GET      /api/campaigns/<id>/audience/preview/ -> Preview audiencia
POST     /api/campaigns/<id>/audience/generate/ -> Gerar audiencia
GET      /api/campaigns/<id>/recipients/ -> Destinatarios
GET/POST /api/campaigns/<id>/steps/  -> Steps (nurture)
GET      /api/campaigns/<id>/analytics/ -> Analytics
POST     /api/campaigns/<id>/schedule/ -> Agendar envio
POST     /api/campaigns/<id>/pause-resume/ -> Pausar/retomar
```

---

## 7. PLANO DE CORRECAO

### Fase 1: Seguranca Critica (Sprint 1 - 1 semana)

| # | Tarefa | Prioridade | Esforco |
|---|--------|-----------|---------|
| 1 | Externalizar secrets do YAML (usar .env ou Docker secrets) | CRITICO | 2h |
| 2 | Remover localStorage de tokens no frontend | CRITICO | 1h |
| 3 | Adicionar requirepass ao Redis | CRITICO | 30min |
| 4 | Corrigir inconsistencia de senha RLS (init-rls-user.sql) | CRITICO | 1h |
| 5 | Adicionar rate limiting em endpoints auth | ALTO | 2h |
| 6 | Containers como non-root user | MEDIO | 1h |

### Fase 2: Integridade de Dados (Sprint 2 - 1 semana)

| # | Tarefa | Prioridade | Esforco |
|---|--------|-----------|---------|
| 7 | Validacao de org em ForeignKeys cruzadas | ALTO | 4h |
| 8 | Validacao stage-pipeline em Lead/Case/Task | MEDIO | 2h |
| 9 | Consolidar campos duplicados Contact (subscriber_id/omni_user_ns) | ALTO | 3h |
| 10 | Corrigir typo compaign -> campaign | ALTO | 15min |
| 11 | Corrigir typo recieved_email -> received_email | BAIXO | 15min |
| 12 | Remover models deprecated (TalkHubSyncJob, TalkHubFieldMapping) | ALTO | 2h |

### Fase 3: Performance (Sprint 3 - 1 semana)

| # | Tarefa | Prioridade | Esforco |
|---|--------|-----------|---------|
| 13 | Fix N+1 em Opportunity.get_aging_status() | ALTO | 2h |
| 14 | Fix N+1 em Lead.primary_contact | ALTO | 1h |
| 15 | Audit select_related/prefetch_related em todas as views | ALTO | 4h |
| 16 | Fix N+1 em SalesGoal.compute_progress() | MEDIO | 2h |
| 17 | Adicionar indices compostos para filtros comuns | MEDIO | 2h |

### Fase 4: Qualidade e Padronizacao (Sprint 4 - 1 semana)

| # | Tarefa | Prioridade | Esforco |
|---|--------|-----------|---------|
| 18 | Padronizar serializer.py -> serializers.py | MEDIO | 1h |
| 19 | Extrair M2M handling para utility function | MEDIO | 3h |
| 20 | Implementar invoices URLs (CRUD completo) | ALTO | 4h |
| 21 | Adicionar validacao frontend (email, telefone, ranges) | MEDIO | 4h |
| 22 | Habilitar strictNullChecks progressivamente | MEDIO | 4h |

### Fase 5: Infraestrutura (Sprint 5 - 1 semana)

| # | Tarefa | Prioridade | Esforco |
|---|--------|-----------|---------|
| 23 | Adicionar health checks nos Dockerfiles e compose | ALTO | 2h |
| 24 | Implementar backup automatizado PostgreSQL | MEDIO | 4h |
| 25 | Adicionar HTTP security headers (HSTS, CSP, X-Frame) | MEDIO | 2h |
| 26 | Automatizar CI/CD (build -> push -> deploy) | MEDIO | 8h |
| 27 | Adicionar Trivy/Bandit ao CI para security scanning | BAIXO | 2h |
| 28 | Frontend API URL como runtime env (nao build-time) | BAIXO | 2h |

---

## 8. ESTADO DA TRANSFORMACAO CONVERSACIONAL

### Implementado
- **channels app**: Abstracacao de canais de comunicacao (TalkHub Omni, SMTP, Chatwoot, Evolution API)
- **conversations app**: Inbox omnichannel com Conversation + Message models
- **talkhub_omni app**: Conector completo com sync bidirecional, 30+ endpoints
- **ConversationTimeline**: Componente frontend para visualizacao de mensagens
- **Bot control**: Pause/resume bot por contato
- **Multi-canal**: Suporte a WhatsApp, SMS, Email, Web Chat via TalkHub Omni

### Pendente / Em Progresso
- **Real-time messaging**: Sem WebSocket/SSE implementado (conversas nao atualizam em tempo real)
- **Chatwoot integration**: Planejado mas nao implementado
- **Evolution API integration**: Planejado mas nao implementado
- **EvoAI integration**: Planejado mas nao implementado
- **Read status**: Mensagens sem tracking de leitura
- **Typing indicators**: Nao implementado
- **Message reactions**: Nao implementado
- **Contact merge**: Sem funcionalidade de merge de contatos duplicados
- **Unified contact timeline**: Historico unificado (CRM + conversas) parcialmente implementado

### Recomendacao para CRM Conversacional
1. **Prioridade 1**: Implementar WebSocket/SSE para atualizacoes em tempo real
2. **Prioridade 2**: Completar integracao Chatwoot + Evolution API
3. **Prioridade 3**: Unificar timeline de contato (todas as interacoes em um so lugar)
4. **Prioridade 4**: Implementar contact merge para deduplicacao
5. **Prioridade 5**: Adicionar typing indicators e read receipts

---

## 9. CONCLUSAO

O TalkHub CRM possui uma **arquitetura sólida e bem planejada** para um CRM multi-tenant SaaS. O sistema de RLS com PostgreSQL e a separacao clara entre frontend/backend/worker sao pontos fortes significativos.

**Pontos fortes principais:**
- Multi-tenancy robusto via PostgreSQL RLS (fail-safe)
- Autenticacao completa (JWT + OAuth + Magic Link + PKCE)
- Pipeline/Kanban flexivel em Leads, Cases e Tasks
- Modulo financeiro completo com multi-moeda
- Integracao TalkHub Omni funcional com 30+ endpoints
- Frontend moderno com Svelte 5 runes

**Areas que precisam atencao imediata:**
- Seguranca: secrets no YAML, localStorage redundante, Redis sem senha
- Performance: N+1 queries em views criticas
- Completude: invoices sem URLs, models deprecated, campos duplicados
- Infraestrutura: sem health checks, sem backups automatizados

O plano de correcao proposto em 5 fases (5 sprints) cobre todas as inconsistencias identificadas, priorizando seguranca primeiro, seguido de integridade de dados, performance, qualidade e infraestrutura.
