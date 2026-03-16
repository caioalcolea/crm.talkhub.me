# CLAUDE.md — TalkHub CRM

> Memory file for Claude Code sessions. Read this first before working on the project.

## Project Overview

Multi-tenant CRM SaaS — Django 5.2 + SvelteKit 2 + PostgreSQL 16 RLS.
Production: https://crm.talkhub.me

## Tech Stack

- **Backend**: Django 5.2, DRF 3.16, Celery 5.6, Redis 7, PostgreSQL 16
- **Frontend**: SvelteKit 2, Svelte 5 (runes), TailwindCSS 4, shadcn-svelte, bits-ui
- **Cowork Virtual Office**: Phaser 3 (Next.js) + Socket.io (Node.js) + WebRTC
- **Deploy**: Docker Swarm + Traefik (HTTPS Let's Encrypt)
- **Auth**: JWT (SimpleJWT) + Google OAuth + Magic Link

## Project Structure

```
crm.talkhub.me/
├── djangocrm/
│   ├── backend/              # Django REST API (18 apps)
│   │   ├── crm/              # Settings, URLs, Celery, WSGI
│   │   ├── common/           # Auth, RLS, middleware, permissions, admin panel, invitations
│   │   ├── accounts/         # Companies
│   │   ├── contacts/         # Contacts (with TalkHub Omni fields)
│   │   ├── leads/            # Leads + kanban pipeline
│   │   ├── opportunity/      # Opportunities + line items + goals
│   │   ├── cases/            # Cases + kanban + SLA
│   │   ├── tasks/            # Tasks + kanban + boards + calendar
│   │   ├── invoices/         # Invoices, estimates, recurring, products
│   │   ├── orders/           # Orders
│   │   ├── financeiro/       # Financial module (P&L, cash flow, PIX, exchange rates, recurring)
│   │   ├── integrations/     # Generic integration hub
│   │   ├── channels/         # Communication channels (SMTP, TalkHub, etc.)
│   │   ├── conversations/    # Omnichannel inbox (real-time via fast polling)
│   │   ├── chatwoot/         # Chatwoot connector + channel provider
│   │   ├── talkhub_omni/     # TalkHub Omni connector
│   │   ├── cowork/           # Sala Cowork Django models + API
│   │   ├── automations/      # Workflow automations
│   │   ├── campaigns/        # Marketing campaigns
│   │   └── requirements.txt
│   └── frontend/             # SvelteKit app
│       ├── src/
│       │   ├── routes/(app)/ # Authenticated CRM routes
│       │   ├── routes/(no-layout)/ # Login, org selection
│       │   └── lib/
│       │       ├── api.js         # Client-side API (JWT in-memory)
│       │       ├── api-helpers.js # Server-side API (JWT from cookies)
│       │       └── components/
│       └── package.json
├── cowork-server/             # Socket.io real-time server (Node.js)
│   ├── server.js             # Room state, JWT validation, proximity calc, WebRTC signaling
│   └── package.json
├── cowork-app/                # Phaser 3 virtual office (Next.js)
│   ├── src/app/              # App router (page.tsx = Phaser game)
│   ├── src/components/       # PhaserGame, Whiteboard
│   ├── src/game/             # Phaser scenes, player, chair, chat, whiteboard
│   ├── src/lib/              # Socket.io client + postMessage bridge
│   └── package.json
├── docker/
│   ├── djangocrm.yaml        # Docker Swarm stack definition
│   ├── Dockerfile.backend    # Python 3.12-slim + Gunicorn
│   ├── Dockerfile.frontend   # Node 22 multi-stage build
│   ├── Dockerfile.cowork-server # Socket.io cowork server
│   ├── Dockerfile.cowork-app # Next.js cowork frontend (Phaser 3)
│   ├── entrypoint-prod.sh    # DB wait + migrations + RLS + collectstatic + admin
│   ├── init-rls-user.sql     # Creates non-superuser for RLS
│   ├── fix-deploy.sh         # Quick redeploy (no rebuild)
│   ├── fix-db-user.sh        # Reset DB user password
│   ├── debug-traefik.sh      # Traefik routing diagnostic script
│   └── backup-db.sh          # pg_dump + optional S3 upload
├── redeploy.sh               # Full clean deploy script
├── DIAGRAMA_CRM_NATIVO.md    # Complete architecture diagram
├── README.md                 # Complete project documentation
└── CLAUDE.md                 # This file
```

## Critical Architecture Patterns

### Multi-Tenancy (RLS)
- ALL data isolated via PostgreSQL Row-Level Security
- Session variable: `app.current_org` (set by `SetOrgContext` middleware)
- DB user MUST be non-superuser (`crm_user`) for RLS to work
- **Fail-safe**: if `app.current_org` not set, zero rows returned
- **Celery tasks**: MUST call `set_rls_context(org_id)` at start (from `common.tasks`)
- **RLS-exempt tables**: `pending_invitation` has RLS DISABLED (migration 0003) — ORM queries work without org context

### Authentication Flow
```
Login (Google/MagicLink) -> JWT WITHOUT org_id
  -> /org page (select organization)
  -> switch-org -> new JWT WITH org_id
  -> all API calls work with RLS
```

### Invitation Flow
```
Admin sends invite (/users page)
  -> PendingInvitation created with UUID token
  -> Email sent with link: {FRONTEND_URL}/invite/accept/{token}/
  -> Django InvitationAcceptView validates token
  -> Redirects to /login?invite={token}
  -> Login page saves invite_token cookie
  -> After auth, POST /api/auth/accept-invite/ with token
  -> Backend creates Profile in invited org
  -> invite_org_id cookie set
  -> /org page auto-selects the org
```

### Frontend API Pattern
- **Server-side** (`+page.server.js`): use `apiRequest()` from `$lib/api-helpers.js` — reads JWT from httpOnly cookies
- **Client-side** (`.svelte`): use `apiRequest()` from `$lib/api.js` — uses in-memory JWT token
- **NEVER use bare `fetch()` for API calls** — it won't have auth headers

### Backend View Pattern
```python
from common.permissions import IsAuthenticated, HasOrgContext

class MyView(APIView):
    permission_classes = [IsAuthenticated, HasOrgContext]
```

### Model Pattern
```python
from common.base import BaseModel  # UUID pk, audit fields
# or
from common.base import BaseOrgModel  # + org FK (for new apps)
```

### Webhook Multi-Tenant Pattern
- Each `IntegrationConnection` has a unique `webhook_token` (auto-generated via `secrets.token_urlsafe(32)`)
- Webhook URL: `/api/integrations/webhooks/<connector_slug>/<webhook_token>/` (preferred, secure)
- Legacy URL: `/api/integrations/webhooks/<connector_slug>/` (backward compat, identifies org by account_id)
- Token-based lookup uses raw SQL to bypass RLS (token IS the authentication)
- `post_connect()` hook in `BaseConnector` registers webhook after connection is saved
- Chatwoot connector overrides `post_connect()` to auto-register webhook with token-based URL

## Deploy Commands

```bash
# Full redeploy (rebuild images + deploy + verify)
./redeploy.sh

# Rebuild without Docker cache
./redeploy.sh --no-cache

# Deploy without rebuilding (reuse existing images)
./redeploy.sh --skip-build

# Quick redeploy (reuse images, no rebuild)
docker/fix-deploy.sh

# Logs
docker service logs djangocrm_crm_backend --tail 50 --follow
docker service logs djangocrm_crm_worker --tail 50 --follow
docker service logs djangocrm_crm_beat --tail 30
docker service logs djangocrm_crm_frontend --tail 30
docker service logs djangocrm_crm_cowork_backend --tail 30 --follow
docker service logs djangocrm_crm_cowork_front --tail 30 --follow

# Shell access
BACKEND=$(docker ps -q -f name=djangocrm_crm_backend)
docker exec -it $BACKEND python manage.py shell
docker exec -it $BACKEND python manage.py manage_rls --status

# Database
docker exec -it $(docker ps -q -f name=djangocrm_crm_db) psql -U crm_user -d crm_db

# Services status
docker stack services djangocrm

# Debug Traefik routing
bash docker/debug-traefik.sh
```

## Svelte 5 Rules

- Use runes: `$state`, `$derived`, `$effect`, `$props`
- Do NOT use deprecated `svelte:component` — use conditional rendering
- shadcn-svelte components from `$lib/components/ui/`
- Icons from `@lucide/svelte`

## Known Gotchas

1. **FERNET_KEY in YAML**: Do NOT use `${VAR:-default}` for base64 keys — Docker eats trailing `=`. Set directly: `FERNET_KEY=value`
2. **Celery tasks + RLS**: Always call `set_rls_context(org_id)` — tasks don't pass through middleware
3. **Frontend fetch**: Always use `apiRequest()` never bare `fetch()` for API calls
4. **RLS bypass**: If DBUSER is `postgres` (superuser), RLS is silently disabled
5. **Docker build context**: Backend Dockerfile expects to be built from repo root (not from `docker/`)
6. **IMAP polling**: Emails are fetched via Celery Beat every 2 minutes (`poll_imap_emails` task) AND on manual sync via the SMTP connector
7. **Chatwoot status sync**: CRM status changes are synced to Chatwoot async via Celery. A 30s grace period prevents Chatwoot webhooks from reverting local status changes (`status_changed_locally_at` in metadata)
8. **Conversation updates**: Frontend uses fast polling (5s incremental via `/conversations/updates/`, 60s full refresh). Do NOT use bare 30s full refresh — it's too heavy
9. **Chatwoot contact dedup**: Group contacts (no email/phone) are deduped by exact name match. chatwoot_id is stored in `description` field as `chatwoot_id:123`. The `_dedup_contacts()` method auto-cleans duplicates on every sync
10. **Chatwoot sync all statuses**: Chatwoot API `GET /conversations` defaults to `status=open` only. The sync must iterate all statuses (open, pending, resolved, snoozed) to get all conversations
11. **Conversation ordering**: `ConversationListView` uses `Coalesce(last_message_at, created_at)` to ensure conversations without messages (freshly synced) appear in the list
12. **Webhook multi-tenant**: Each `IntegrationConnection` has a unique `webhook_token`. Token-based URLs (`/webhooks/<slug>/<token>/`) prevent cross-tenant leakage when orgs share the same external service (e.g., same Chatwoot account_id). Legacy URL without token still works as fallback.
13. **Cowork iframe**: Next.js app runs with `basePath: '/cowork-app'`. Traefik does NOT strip prefix — Next.js handles it natively via basePath.
14. **Cowork keyboard**: Phaser keyboard input is bypassed — uses raw DOM `keydown`/`keyup` events via `KeyTracker` to avoid iframe focus issues.
15. **Cowork tile seams**: CANVAS renderer (not WebGL) is required to eliminate black lines between tiles at fractional zoom levels.
16. **CoworkPiP z-index**: Full-mode overlay (z-15) is OUTSIDE AppShell in DOM. PageHeader wrapper and toolbar on cowork page MUST have `relative z-20` to stay above the overlay. Sidebar (z-10) doesn't overlap because the overlay is positioned to its right.
17. **CoworkPiP full-mode positioning**: Cannot move iframe between DOM nodes (causes reload). Uses `position:fixed` overlay with ResizeObserver on `[data-cowork-target]`. Hardcoded rem fallback (`top:7.75rem; left:16rem`) ensures immediate visibility. CSS `var(--sidebar-width)` doesn't resolve outside the sidebar-provider wrapper — use hardcoded values.
18. **CoworkPiP effect chain**: `startCoworkSession()` → DOM render → `registerFullTarget()` → ResizeObserver → `fullBounds` requires 4 effects in sequence. Polling retry (100ms × 30) and DOM query backup protect against timing issues. **Never use `opacity:0` as fallback** — use hardcoded visible position instead.
19. **Conversation soft-delete**: All user-facing views (list, messages, assign, bot) filter `is_deleted=False`. Chatwoot webhooks also skip deleted conversations. Only `ConversationDetailView.get()` allows viewing deleted conversations (needed for the trash view). Permanent delete requires `is_deleted=True` first (two-step).
20. **Contact FK is SET_NULL**: `Conversation.contact` uses `on_delete=SET_NULL` — contact deletion sets `contact=NULL` instead of cascading. Serializers and templates handle `contact is None` with "Contato removido" fallback.
21. **Contact merge email/phone preservation**: Merge fills `secondary_email`/`secondary_phone` first (if empty), then overflows to `ContactEmail`/`ContactPhone` extras. The `_SCALAR_FIELDS` step runs before the preservation step, so in-memory mutations are visible to the preservation logic.
22. **Secondary email/phone in channel matching**: All lookup chains follow the order: primary → secondary → extra table. Chatwoot connector, SMTP polling, data_unifier, and duplicate detection all include secondary fields.
23. **Financeiro CANCELADO in reports**: All report views (FluxoPlanoContas, RelatorioMensal, EntityFinancial) exclude `status="CANCELADO"` parcelas from sums. Dashboard already filters by specific statuses.
24. **Financeiro variable exchange rate**: `exchange_rate_type` field on Lancamento: FIXO (manual) or VARIAVEL (auto-fetch from API). Primary API: open.er-api.com, fallback: BCB PTAX for BRL pairs. Rates cached in Redis (4h TTL).
25. **Financeiro recurring lancamentos**: `is_recorrente` + `recorrencia_tipo` (MENSAL/QUINZENAL/SEMANAL/ANUAL). Each parcela = full valor_total. Celery Beat generates 3 months ahead on 1st of each month. Stop via `recorrencia_ativa=False`.
26. **Lancamento edit rules**: If all parcelas ABERTO → can edit everything (parcelas regenerated). If some PAGO → metadata only. If CANCELADO → read-only (except descricao/observacoes).
27. **Org currency integration**: All frontend financial pages use `$orgSettings.default_currency` instead of hardcoded 'BRL'. Backend `FormOptionsView` returns `org_currency`. TransactionForm auto-hides exchange rate when currency == org base currency.
28. **Org settings field mapping**: Frontend sends `website` (NOT `domain`) to match the Org model. The `description` field does not exist on the model — don't add it. All company profile fields (company_name, address_line, city, state, postcode, country, phone, email, website, tax_id) are editable via `PATCH /api/org/settings/`. Logo upload supports PNG/JPG/SVG (max 2MB); removal sends `logo: null`.
29. **Org logo in PDFs**: Invoice and estimate templates already render `{% if org.logo %}<img src="{{ org.logo.url }}">{% endif %}`. WeasyPrint passes full org context. Company address fields (address_line, city, state, phone, email, tax_id) also appear in PDF templates. No backend changes needed for logo to work in print.
30. **Formas de pagamento editáveis**: `FormaPagamentoViewSet` is a full `ModelViewSet` — supports PATCH/PUT out of the box. Frontend has edit dialog with `?/edit` action.
31. **Financeiro Saldo Projetado**: `saldo_projetado_mes` and `saldo_projetado_ano` include ALL non-cancelled parcelas (PAGO + ABERTO), not just ABERTO. Formula: total RECEBER - total PAGAR. The old `saldo_projetado` key is kept as alias for `saldo_projetado_ano` for backward compat.
32. **Financeiro Daily Cash Flow**: `FluxoDiarioReportView` at `/api/financeiro/reports/fluxo-diario/?ano=YYYY&mes=M`. Returns day-by-day receita/despesa with `saldo_acumulado` running balance. Uses `data_pagamento` for PAGO parcelas, `data_vencimento` for ABERTO. Detects negative accumulated balance days in `resumo.dias_negativos`.
33. **Docker healthcheck start-period**: Dockerfile.backend uses `start-period=300s` (5 minutes) because the entrypoint runs DB setup + migrations + RLS check (79 tables) + collectstatic + admin creation before Gunicorn starts. The 60s default caused Docker Swarm to kill the container before it was ready.

## Invitation System

**Status**: Fixed — Traefik now routes `/invite/` to Django backend.

**Flow**: Admin invites via `/users` → `PendingInvitation` created → email with `/invite/accept/<token>/` → Django validates and redirects to `/login?invite=<token>` → after auth, `POST /api/auth/accept-invite/` → Profile created in invited org → `/org` auto-selects.

**Files involved**:
- `docker/djangocrm.yaml` (Traefik routing — `/invite` in PathPrefix rule)
- `djangocrm/backend/common/views/invitation_views.py` (InvitationAcceptView, InvitationAcceptAPIView)
- `djangocrm/frontend/src/routes/(no-layout)/login/+page.server.js` (invite_token cookie handling)
- `djangocrm/frontend/src/routes/(no-layout)/login/verify/+page.server.js` (magic link invite flow)
- `djangocrm/frontend/src/routes/(no-layout)/org/+page.server.js` (invite_org_id auto-select)
- `djangocrm/frontend/src/routes/(no-layout)/org/+page.svelte` (auto-submit form)

## Services (Docker Swarm)

| Service | Image | Port | Role |
|---------|-------|------|------|
| crm_db | postgres:16-alpine | 5432 | Database |
| crm_backend | djangocrm-backend | 8000 | Django + Gunicorn |
| crm_worker | djangocrm-backend | — | Celery Worker |
| crm_beat | djangocrm-backend | — | Celery Beat |
| crm_frontend | djangocrm-frontend | 3000 | SvelteKit SSR |
| crm_redis | redis:7-alpine | 6379 | Broker + Cache |
| crm_cowork_backend | cowork-server | 3100 | Socket.io (cowork rooms) |
| crm_cowork_front | cowork-app | 3200 | Next.js + Phaser 3 (virtual office) |

## Traefik Routing

- Priority 25: `/ws/` -> crm_ws:8001 (Django WebSocket)
- Priority 22: `/cowork-ws/` -> cowork_backend:3100 (Socket.io, strip prefix)
- Priority 20: `/api`, `/admin`, `/static`, `/swagger`, `/media`, `/invite`, `/health`, `/track`, `/webhooks`, `/schema` -> backend:8000
- Priority 18: `/cowork-app/` -> cowork_front:3200 (Next.js, no strip prefix — uses basePath)
- Priority 10: `/*` (catch-all) -> frontend:3000

## Sala Cowork — Virtual Office

### Architecture
```
SvelteKit /cowork → POST /api/cowork/auth/token/ → JWT (cowork-scoped)
  → iframe loads /cowork-app/ (Next.js + Phaser 3)
  → parent postMessage({ type: "cowork-init", payload: { token, socketUrl } })
  → Next.js connects to /cowork-ws/ (Socket.io)
  → join-room → room-state → real-time presence + movement
```

### Features
- **Phaser 3 game engine**: SkyOffice-style 2D tilemap with collision layers, chairs, desks
- **Real-time multiplayer**: Socket.io room state with player movement broadcast
- **Proximity-based WebRTC audio/video**: Server calculates players within PROXIMITY_RADIUS tiles → emits `proximity-update` → peers connect via native RTCPeerConnection (no external libs)
- **Sit on chairs**: Press E key near a chair to sit → broadcasts sitting state to all players
- **Real-time chat**: Type messages → speech bubbles appear above player avatar for all to see
- **Collaborative whiteboard**: Toggle whiteboard overlay → draw together in real-time via Socket.io events
- **Guest access**: Public endpoint `/api/public/cowork/join/<token>/` generates guest JWT (30min, no org auth)

### Key Patterns
- **In-memory state (V1)**: Room/player state stored in JS Map on cowork-server (no Redis needed for single replica)
- **JWT bridge**: Django generates cowork-scoped JWT → validated by cowork-server using same SECRET_KEY
- **postMessage protocol**: Parent (SvelteKit) ↔ iframe (Next.js) communication:
  - Parent → Iframe: `cowork-init` (config), `cowork-destroy` (cleanup)
  - Iframe → Parent: `cowork-ready`, `cowork-status`, `cowork-error`
- **CANVAS renderer**: Required to avoid tile seam artifacts at fractional zoom levels
- **Raw DOM keyboard**: Bypasses Phaser's keyboard system for reliable iframe key capture

### CoworkPiP — Persistent Iframe Overlay
The iframe is rendered in `+layout.svelte` (outside AppShell) via `CoworkPiP.svelte`, NOT inside the cowork page. This keeps the Phaser game alive across route navigations.

**Modes**: `hidden` → `full` → `pip` → `fullscreen`
- **Full mode**: `position:fixed` overlay positioned over `[data-cowork-target]` div on `/cowork` page. Uses ResizeObserver for exact pixel bounds, hardcoded rem fallback (`top:7.75rem; left:16rem`) for immediate visibility.
- **PiP mode**: `position:fixed; bottom:1.5rem; right:1.5rem; z-index:40`. Draggable, resizable (P/M/G presets). Auto-activates when navigating away from `/cowork`.
- **Fullscreen**: `position:fixed; inset:0; z-index:50` + Browser Fullscreen API. Toolbar auto-hides after 3s.

**Z-index stacking (full mode)**:
- Iframe overlay: `z-index:15`
- Sidebar: `z-index:10` (fixed, doesn't overlap — iframe positioned to its right)
- PageHeader wrapper: `z-index:20` (relative, on cowork page only)
- Toolbar: `z-index:20` (relative, stays clickable above iframe)
- PiP: `z-index:40`, Fullscreen: `z-index:50`

**Target registration flow**:
```
startCoworkSession() → mode='full' → page renders [data-cowork-target]
  → page $effect calls registerFullTarget(el) → store.fullTarget = el
  → CoworkPiP $effect detects fullTarget → ResizeObserver → fullBounds
  → Backup: DOM query [data-cowork-target] + polling retry (100ms × 30)
  → Fallback: hardcoded position:fixed;top:7.75rem;left:16rem;right:0;bottom:0
```

**Store**: `$lib/stores/cowork.svelte.js` — Svelte 5 `$state` with getters on plain object.

### Cowork File Map
| Component | Files |
|-----------|-------|
| Django models/API | `backend/cowork/` (Room, RoomMember, models, views, serializers) |
| Socket.io server | `cowork-server/server.js` (room state, proximity, JWT, WebRTC relay, chat, whiteboard) |
| Next.js shell | `cowork-app/src/app/page.tsx` (loads Phaser game) |
| Phaser game scene | `cowork-app/src/game/OfficeScene.ts` (tilemap, players, chairs, collision) |
| Player controller | `cowork-app/src/game/Player.ts` (movement, animation, sit, chat bubble) |
| Chair interaction | `cowork-app/src/game/Chair.ts` (sit detection, E key prompt) |
| Chat system | `cowork-app/src/game/ChatManager.ts` (input, speech bubbles) |
| Whiteboard | `cowork-app/src/components/Whiteboard.tsx` (canvas overlay, real-time drawing) |
| WebRTC manager | `cowork-app/src/lib/webrtc.ts` (peer connections, media streams) |
| Socket client | `cowork-app/src/lib/socket.ts` (Socket.io connection, event handlers) |
| postMessage bridge | `cowork-app/src/lib/postmessage.ts`, `frontend/.../cowork/+page.svelte` |
| CoworkPiP overlay | `frontend/src/lib/components/cowork/CoworkPiP.svelte` (global iframe, all modes) |
| Cowork store | `frontend/src/lib/stores/cowork.svelte.js` (session state, mode, fullTarget) |
| Cowork page | `frontend/src/routes/(app)/cowork/+page.svelte` (room list, toolbar, target div) |

## Key Files for Common Tasks

| Task | Files |
|------|-------|
| Add new API endpoint | `backend/<app>/views.py`, `backend/<app>/urls.py`, `backend/crm/urls.py` |
| Add new frontend page | `frontend/src/routes/(app)/<name>/+page.svelte`, `+page.server.js` |
| Add Celery task | `backend/<app>/tasks.py`, `backend/crm/celery.py` (for periodic) |
| Add integration connector | `backend/<app>/connector.py` (ConnectorRegistry auto-discovers via AppConfig) |
| Modify deploy config | `docker/djangocrm.yaml`, `docker/entrypoint-prod.sh` |
| Email templates | `backend/templates/` (all in pt-BR) |
| UI components | `frontend/src/lib/components/` |
| Constants (currencies, countries) | `frontend/src/lib/constants/` |
| Contact merge | `backend/contacts/merge.py` (merge_contacts, get_merge_preview) |
| Contact duplicate detection | `backend/common/duplicate_detection.py` |
| Chatwoot connector | `backend/chatwoot/connector.py` (webhook handlers, sync, group detection) |
| Chatwoot channel provider | `backend/chatwoot/provider.py` (send/receive messages) |
| Conversation real-time | `backend/conversations/views.py` (`ConversationUpdatesView`) |
| Conversation soft-delete | `backend/conversations/views.py` (SoftDelete, PermanentDelete views) |
| Webhook routing | `backend/integrations/views.py` (`webhook_receiver`), `backend/integrations/tasks.py` |
| Invitation system | `backend/common/views/invitation_views.py`, `frontend/.../login/+page.server.js` |
| User management | `frontend/src/routes/(app)/users/+page.svelte`, `+page.server.js` |
| Cowork rooms (Django) | `backend/cowork/` (models, views, serializers, urls) |
| Cowork Socket.io server | `cowork-server/server.js` |
| Cowork Phaser game | `cowork-app/src/game/` (OfficeScene, Player, Chair, ChatManager) |
| Cowork postMessage bridge | `cowork-app/src/lib/postmessage.ts`, `frontend/.../cowork/+page.svelte` |
| CoworkPiP (persistent iframe) | `frontend/src/lib/components/cowork/CoworkPiP.svelte`, `frontend/src/lib/stores/cowork.svelte.js` |
| Financeiro models | `backend/financeiro/models.py` (Lancamento, Parcela, FormaPagamento, PaymentTransaction) |
| Financeiro views | `backend/financeiro/api_views.py` (ViewSets, reports, PIX, FluxoDiarioReportView) |
| Financeiro exchange rates | `backend/financeiro/exchange_rates.py` (get_exchange_rate, API integration) |
| Financeiro tasks | `backend/financeiro/tasks.py` (overdue, recurring, variable rates, PIX reconciliation) |
| Financeiro frontend | `frontend/src/routes/(app)/financeiro/` (lancamentos, formas-pagamento, relatorios, PIX) |
| Financeiro form | `frontend/src/lib/components/financeiro/TransactionForm.svelte` |
| Financeiro daily chart | `frontend/src/lib/components/financeiro/DailyCashFlowChart.svelte` (SVG wave chart, daily cash flow) |
| Financeiro monthly chart | `frontend/src/lib/components/financeiro/CashFlowChart.svelte` (SVG bar chart, monthly cash flow) |
| Org settings | `backend/common/serializers.py` (OrgSettingsSerializer), `frontend/src/routes/(app)/settings/organization/` (+page.svelte, +page.server.js) |
| Org model | `backend/common/models.py` (Org: name, company_name, logo, address, phone, email, website, tax_id, currency, country) |
| Invoice/Estimate PDF | `backend/invoices/pdf.py` (WeasyPrint), `backend/invoices/templates/invoices/pdf/` (invoice.html, estimate.html) |

## Chatwoot Integration

### Architecture
```
Chatwoot → POST /api/integrations/webhooks/chatwoot/<webhook_token>/ (AllowAny)
  → Lookup org by webhook_token (raw SQL, bypasses RLS)
  → Validate HMAC-SHA256 signature
  → Enqueue process_webhook.delay() (Celery)
  → ChatwootConnector.handle_webhook() routes by event type
```

### Webhook Events Handled
| Event | Handler | Description |
|-------|---------|-------------|
| `message_created` | `_handle_message_created` | Import incoming messages, create conversation if needed |
| `message_updated` | `_handle_message_updated` | Update edited messages |
| `conversation_created` | `_handle_conversation_created` | Create new conversation + contact |
| `conversation_updated` | `_handle_conversation_updated` | Sync assignee, labels, status |
| `conversation_status_changed` | `_handle_conversation_status_changed` | Sync status (with 30s local override grace) |
| `contact_created` / `contact_updated` | `_handle_contact_event` | Create/update CRM contacts |

### Key Patterns
- **Echo prevention**: Outgoing messages with `content_attributes.external_created=True` are skipped
- **Group detection**: Checks `conversation_type=="group"`, `additional_attributes.type=="group"`, `"(GROUP)"` in contact name, and fallback name chain
- **Contact dedup**: `_get_or_create_contact` matches by: (1) chatwoot_id stored in description, (2) email, (2b) secondary_email, (3) phone, (3b) secondary_phone, (4) extra_emails/phones tables, (5) exact name for groups. Handles both `NULL` and `""` for empty fields
- **Soft-delete aware**: All webhook handlers filter `is_deleted=False` — won't resurrect or modify soft-deleted conversations
- **Auto-dedup on sync**: `_dedup_contacts()` runs at start of every sync — merges duplicate contacts (same name, no email/phone), reassigns conversations, removes duplicates
- **Sync all statuses**: Chatwoot API defaults to `status=open`. Sync iterates all statuses: open, pending, resolved, snoozed
- **Contact sync**: `_get_or_create_contact` updates existing contacts with missing email/phone/name from Chatwoot
- **Status precedence**: Local CRM status changes set `status_changed_locally_at` → webhooks skip status sync for 30s
- **Async status sync**: `sync_conversation_status_to_chatwoot` Celery task syncs CRM→Chatwoot via `toggle_status` API
- **Conversation ordering**: `ConversationListView` uses `Coalesce(last_message_at, created_at)` so conversations without messages still appear

### Frontend Real-Time
- **Fast poll** (5s): `GET /conversations/updates/?since=<ISO>&conversation_id=<UUID>` — returns only deltas
- **Full refresh** (60s): Fallback full list + messages reload
- Messages and conversations merge incrementally (dedup by ID)

## SMTP Email Integration

### Architecture
- SMTP as a full conversation channel (send/receive via Conversations inbox)
- Outbound: Django `send_mail()` via configured SMTP server
- Inbound: IMAP polling via Celery Beat every 2 minutes (`poll_imap_emails` task)
- HTML email rendering with text/HTML toggle in conversation timeline
- Reply threading via `In-Reply-To` / `References` headers
- Contact lookup chain: primary email → secondary_email → extra_emails table

## Financeiro — Reports & Dashboard

### Dashboard KPIs (`DashboardReportView`)
| Metric | Formula | Scope |
|--------|---------|-------|
| A Receber | Σ RECEBER, ABERTO | competencia_ano = selected year |
| A Pagar | Σ PAGAR, ABERTO | competencia_ano = selected year |
| Recebido no Mês | Σ RECEBER, PAGO | data_pagamento = current month |
| Pago no Mês | Σ PAGAR, PAGO | data_pagamento = current month |
| Vencido | Σ ABERTO, data_vencimento < today | All time |
| Saldo do Mês | Recebido - Pago (current month) | data_pagamento |
| Projetado (Mês) | ALL RECEBER - ALL PAGAR (PAGO+ABERTO, excludes CANCELADO) | competencia_mes = current month |
| Projetado (Ano) | ALL RECEBER - ALL PAGAR (PAGO+ABERTO, excludes CANCELADO) | competencia_ano = selected year |

### Report Endpoints
| Endpoint | View | Description |
|----------|------|-------------|
| `GET /financeiro/reports/dashboard/?ano=` | `DashboardReportView` | KPIs + monthly flow + last 10 transactions |
| `GET /financeiro/reports/fluxo-diario/?ano=&mes=` | `FluxoDiarioReportView` | Day-by-day cash flow with accumulated balance |
| `GET /financeiro/reports/fluxo-plano-contas/?ano=` | `FluxoPlanoContasReportView` | Pivot table: Plano de Contas x 12 months |
| `GET /financeiro/reports/relatorio-mensal/?ano=` | `RelatorioMensalReportView` | Monthly breakdown + saldo_projetado + saldo_acumulado |
| `GET /financeiro/reports/by-entity/<uuid>/` | `EntityFinancialReportView` | Financial summary for Account/Contact/Opportunity |

### Daily Cash Flow Chart (`DailyCashFlowChart.svelte`)
- Custom SVG wave chart (no external charting library)
- X-axis: days 1-N of the month, Y-axis: scaled to max value
- Three data series: receita (emerald area), despesa (rose area), saldo_acumulado (blue line)
- Red zone shading when accumulated balance goes negative
- "Hoje" (today) vertical marker line
- Interactive tooltips showing day details on hover
- Negative day alert banner shown below chart when `resumo.dias_negativos > 0`

### Monthly Cash Flow Chart (`CashFlowChart.svelte`)
- Custom SVG stacked bar chart (no external library)
- 12 months, each with paired bars (receivable/payable)
- Solid color = realized (PAGO), faded = projected (ABERTO)
- Current month highlighted with bold label

## Contact Management

### Multiple Emails/Phones per Contact
- **Primary fields**: `email`, `phone` (direct on Contact model)
- **Secondary fields**: `secondary_email`, `secondary_phone` (direct on Contact model, visible in create/edit forms)
- **Extra entries**: `ContactEmail`, `ContactPhone`, `ContactAddress` junction tables (for 3rd+ values)
- All channels (Chatwoot, SMTP, TalkHub Omni, data_unifier) check secondary fields in lookup chains
- Duplicate detection checks secondary fields bidirectionally

### Contact Merge
- **Service**: `backend/contacts/merge.py` — `merge_contacts(org, primary_id, secondary_id)`
- **Preview**: `get_merge_preview()` shows field-by-field diff before merge
- **Email/Phone preservation**: All unique emails/phones from secondary are preserved — fills `secondary_email`/`secondary_phone` first, then `ContactEmail`/`ContactPhone` extras
- **Conflict handling**: If both contacts have different values, secondary's values are saved as extras (never lost)
- **FK/M2M reassignment**: Conversations, invoices, leads, opportunities, cases, tasks, orders, comments, attachments all transferred
- **Audit trail**: Comment created on primary contact documenting the merge

### Conversation Soft-Delete
- **Fields**: `is_deleted` (bool), `deleted_at` (datetime), `deleted_by` (FK to Profile)
- **Contact FK**: `on_delete=SET_NULL` (not CASCADE) — deleting a contact preserves conversations
- **Contact delete handler**: All conversations soft-deleted before contact hard-delete
- **Endpoints**:
  - `POST /api/conversations/<id>/delete/` — any org user can soft-delete
  - `POST /api/conversations/<id>/restore/` — admin only
  - `DELETE /api/conversations/<id>/permanent-delete/` — admin only, must be in trash first
- **Filtering**: All user-facing views filter `is_deleted=False` by default; `?deleted=true` shows trash
- **Chatwoot protection**: Webhook handlers skip soft-deleted conversations (won't resurrect them)
- **Frontend**: "Deletados" filter in inbox, trash banner, restore/permanent-delete buttons (admin only)

## TalkHub Autopilot — Automações, Lembretes e Campanhas

### Architecture Overview
Three apps form the unified autopilot system:
- **`assistant`** — Core scheduler + reminder engine (ReminderPolicy, ScheduledJob, ChannelDispatch, TaskLink, AutopilotTemplate)
- **`automations`** — Rule engine (Automation: routine, logic_rule, social + AutomationLog)
- **`campaigns`** — Campaign engine (Campaign, CampaignAudience, CampaignRecipient, CampaignStep)

All three share: scheduler, jobs, tasks, channel dispatch, logs, audit, permissions, RLS.

### Assistant App Models (5 models, RLS-enabled)
| Model | Purpose | Key Pattern |
|-------|---------|-------------|
| `ReminderPolicy` | When/how to trigger reminders for any entity | GenericForeignKey target, 5 trigger types, channel_config, task_config |
| `ScheduledJob` | Executable work unit | GenericForeignKey source+target, idempotency_key, SELECT FOR UPDATE SKIP LOCKED |
| `ChannelDispatch` | Audit trail of sends | FK to ScheduledJob, channel_type, status, sent_at, error |
| `TaskLink` | Links automation source → Task | GenericForeignKey source, sync_mode (persistent/per_run) |
| `AutopilotTemplate` | Reusable preset configs | template_type, category, module_key, config_template |

### Trigger Types (engine.py)
| Type | Use Case | Config Example |
|------|----------|----------------|
| `due_date` | Parcela reminder | `{date_field: "data_vencimento", offsets: [-7, -3, 0, 1, 3]}` |
| `recurring` | Follow-up every N days | `{interval_days: 3, max_runs: 10, start_after_field: "data_vencimento"}` |
| `cron` | Daily at 9 AM | `{cron_expression: "0 9 * * 1-5"}` |
| `relative_date` | N days after creation | `{date_field: "created_at", offset_days: 7}` |
| `event_plus_offset` | After event + delay | Stub — needs event listener system |

### Presets (19 templates in presets.py)
- **Financeiro** (4): contas_receber_padrao, contas_receber_email, contas_pagar_padrao, cobranca_recorrente
- **Leads** (2): follow_up_padrao, lead_esfriando
- **Opportunities** (2): close_date_approaching, deal_stale
- **Cases** (2): sla_resolution, case_escalation
- **Tasks** (2): task_due_date, task_overdue
- **Invoices** (2): invoice_due_date, invoice_overdue_email

### Template Engine (template_engine.py)
- Pattern: `{{variable_name}}` interpolation with per-module whitelist
- Modules: financeiro, leads, cases, tasks, invoices, opportunity, system
- Context builders: `build_context_for_parcela()`, `_for_lead()`, `_for_task()`, `_for_opportunity()`, `_for_case()`, `_for_invoice()`

### Signal Handlers (signals.py)
Auto-recalculate reminder schedules on entity changes:
- Parcela → finds parent Lancamento → recalc all policies
- Lead, Opportunity, Case, Task, Invoice → recalc targeting policies
- ReminderPolicy saved → cancel stale jobs / generate initial jobs

### Celery Tasks (tasks.py)
| Task | Schedule | Purpose |
|------|----------|---------|
| `process_scheduled_jobs` | Every minute (Beat) | Find due jobs, lock, dispatch to execute_job |
| `execute_job` | On-demand | Lock → render template → dispatch channel → create task → audit |
| `recalculate_policy_schedules` | On signal | Cancel old jobs → regenerate from current state |

### Dispatch Service (dispatch.py)
```
dispatch_message(org_id, channel_type, destination, message_data, metadata)
  → ChannelRegistry.get(channel_type) [preferred]
  → fallback: automations.router.dispatch() [legacy]
  → Returns: {success, message_id, error}
```

### API Endpoints (`/api/assistant/`)
| Endpoint | Methods | Purpose |
|----------|---------|---------|
| `reminder-policies/` | GET, POST | List/create policies |
| `reminder-policies/<id>/` | GET, PUT, PATCH, DELETE | CRUD |
| `reminder-policies/<id>/activate/` | PATCH | Activate + recalculate |
| `reminder-policies/<id>/deactivate/` | PATCH | Deactivate + cancel pending |
| `scheduled-jobs/` | GET | List with status/type/date filters |
| `scheduled-jobs/<id>/` | GET | Detail + dispatches |
| `scheduled-jobs/<id>/retry/` | POST | Retry failed/cancelled |
| `scheduled-jobs/<id>/cancel/` | POST | Cancel pending |
| `scheduled-jobs/<id>/approve/` | POST | Approve manual-approval jobs |
| `reminders-for/<target_type>/<target_id>/` | GET, POST | Entity-scoped reminders |
| `task-links/` | GET | List by source/task |
| `runs/` | GET | Consolidated execution history |
| `presets/` | GET | Available preset templates |
| `templates/` | GET | User/system templates |

### Automations App (3 automation types)
| Type | Trigger | Config |
|------|---------|--------|
| `routine` | Celery Beat (cron/interval) | `{schedule_cron, action_type, action_params}` |
| `logic_rule` | Django signals (post_save) | `{trigger_event, conditions[], actions[]}` |
| `social` | TalkHub Omni webhooks | `{channel_type, social_event, actions[]}` |

Events: `lead.created`, `lead.status_changed`, `opportunity.created`, `opportunity.stage_changed`, `case.created`, `task.completed`, `contact.created`

### Campaigns App
| Type | Behavior |
|------|----------|
| `email_blast` | Batch send (50/batch, 1s throttle) with tracking pixel + unsubscribe |
| `whatsapp_broadcast` | Batch send (20/batch, 2s throttle) via TalkHub Omni |
| `nurture_sequence` | Multi-step with delay_hours between steps, per-recipient tracking |

Campaigns integrate with assistant's ScheduledJob via `job_generator.py` (idempotency keys, staggered due_at).

### Frontend Routes
| Route | Purpose |
|-------|---------|
| `/autopilot` | Unified dashboard (5 tabs: Rules, Reminders, Campaigns, Runs, Templates) |
| `/automations` | Legacy list + create |
| `/automations/new` | Create automation (JSON config) |
| `/campaigns` | List + pause/resume |
| `/campaigns/new` | Create campaign |
| `/campaigns/[id]` | Campaign detail |
| `/campaigns/[id]/analytics` | Campaign analytics |

### Implementation Status
```
Backend (assistant+automations+campaigns): ~90% complete
Frontend (autopilot UI):                   ~40% complete
IA assistida:                              ~0% complete
```

### Key Gaps (Roadmap)
1. **Financeiro inline UI** — Reminder config block inside TransactionForm (backend API ready)
2. **Unified /autopilot UX** — Replace /automations and /campaigns with single central
3. **Visual builders** — Rule builder, step editor, template editor (replace JSON forms)
4. **Approval queue UI** — API exists, needs frontend
5. **Cross-module navigation** — Task↔origin bidirectional links
6. **AI-assisted creation** — LLM compile natural language → policy config (future)

### Autopilot File Map
| Component | Files |
|-----------|-------|
| Assistant models | `backend/assistant/models.py` (ReminderPolicy, ScheduledJob, ChannelDispatch, TaskLink, AutopilotTemplate) |
| Scheduling engine | `backend/assistant/engine.py` (calculate_next_run, generate_jobs, cancel_stale) |
| Celery tasks | `backend/assistant/tasks.py` (process_scheduled_jobs, execute_job, recalculate) |
| Dispatch service | `backend/assistant/dispatch.py` (unified channel dispatch) |
| Template engine | `backend/assistant/template_engine.py` (variable interpolation, context builders) |
| Presets | `backend/assistant/presets.py` (19 preset templates) |
| Signal handlers | `backend/assistant/signals.py` (7 entity change handlers) |
| Views/API | `backend/assistant/views.py` (13 REST endpoints) |
| Serializers | `backend/assistant/serializers.py` (6 serializers) |
| Automations models | `backend/automations/models.py` (Automation, AutomationLog) |
| Automations engine | `backend/automations/engine.py` (condition evaluator) |
| Automations router | `backend/automations/router.py` (email/whatsapp/internal dispatch) |
| Campaign models | `backend/campaigns/models.py` (Campaign, Audience, Recipient, Step) |
| Campaign audience | `backend/campaigns/audience.py` (audience builder) |
| Campaign jobs | `backend/campaigns/job_generator.py` (ScheduledJob integration) |
| Campaign tracking | `backend/campaigns/tracking.py` (pixel + unsubscribe) |
| Autopilot page | `frontend/src/routes/(app)/autopilot/` (+page.svelte, +page.server.js) |
| Automations page | `frontend/src/routes/(app)/automations/` (+page.svelte, new/) |
| Campaigns page | `frontend/src/routes/(app)/campaigns/` (+page.svelte, new/, [id]/, analytics/) |

## Security Audit Fixes Applied

- RLS bypass in data views: replaced `user.is_superuser` with `profile.is_admin`
- Race conditions in conversation creation: atomic operations
- Filter injection: validated all user-supplied filter parameters
- XSS: hardened `linkify()` regex + `noreferrer` on generated links
- Webhook HMAC: updated to new Chatwoot signature format
- Multi-tenant webhook URLs: per-connection `webhook_token` prevents cross-tenant leakage

## Credentials (Development)

- **Admin**: admin@talkhub.me / TalkHub2026!
- **DB**: crm_user / crm_talkhub_2026
- **SMTP**: talkhub@talkhub.me (configured in djangocrm.yaml)
