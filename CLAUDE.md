# CLAUDE.md — TalkHub CRM

> Memory file for Claude Code sessions. Read this first before working on the project.

## Project Overview

Multi-tenant CRM SaaS — Django 5.2 + SvelteKit 2 + PostgreSQL 16 RLS.
Production: https://crm.talkhub.me

## Tech Stack

- **Backend**: Django 5.2, DRF 3.16, Celery 5.6, Redis 7, PostgreSQL 16
- **Frontend**: SvelteKit 2, Svelte 5 (runes), TailwindCSS 4, shadcn-svelte, bits-ui
- **Deploy**: Docker Swarm + Traefik (HTTPS Let's Encrypt)
- **Auth**: JWT (SimpleJWT) + Google OAuth + Magic Link

## Project Structure

```
crm.talkhub.me/
├── djangocrm/
│   ├── backend/              # Django REST API (16 apps)
│   │   ├── crm/              # Settings, URLs, Celery, WSGI
│   │   ├── common/           # Auth, RLS, middleware, permissions, admin panel
│   │   ├── accounts/         # Companies
│   │   ├── contacts/         # Contacts (with TalkHub Omni fields)
│   │   ├── leads/            # Leads + kanban pipeline
│   │   ├── opportunity/      # Opportunities + line items + goals
│   │   ├── cases/            # Cases + kanban + SLA
│   │   ├── tasks/            # Tasks + kanban + boards + calendar
│   │   ├── invoices/         # Invoices, estimates, recurring, products
│   │   ├── orders/           # Orders
│   │   ├── financeiro/       # Financial module (P&L, cash flow, PIX)
│   │   ├── integrations/     # Generic integration hub
│   │   ├── channels/         # Communication channels (SMTP, TalkHub, etc.)
│   │   ├── conversations/    # Omnichannel inbox (real-time via fast polling)
│   │   ├── chatwoot/         # Chatwoot connector + channel provider
│   │   ├── talkhub_omni/     # TalkHub Omni connector
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
├── docker/
│   ├── djangocrm.yaml        # Docker Swarm stack definition
│   ├── Dockerfile.backend    # Python 3.12-slim + Gunicorn
│   ├── Dockerfile.frontend   # Node 22 multi-stage build
│   ├── entrypoint-prod.sh    # DB wait + migrations + RLS + collectstatic + admin
│   ├── init-rls-user.sql     # Creates non-superuser for RLS
│   ├── fix-deploy.sh         # Quick redeploy (no rebuild)
│   ├── fix-db-user.sh        # Reset DB user password
│   └── backup-db.sh          # pg_dump + optional S3 upload
├── redeploy.sh               # Full clean deploy script
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

### Authentication Flow
```
Login (Google/MagicLink) -> JWT WITHOUT org_id
  -> /org page (select organization)
  -> switch-org -> new JWT WITH org_id
  -> all API calls work with RLS
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

## Deploy Commands

```bash
# Full redeploy (rebuild images + deploy)
./redeploy.sh

# Quick redeploy (reuse images)
docker/fix-deploy.sh

# Logs
docker service logs djangocrm_crm_backend --tail 50 --follow
docker service logs djangocrm_crm_worker --tail 50 --follow
docker service logs djangocrm_crm_beat --tail 30
docker service logs djangocrm_crm_frontend --tail 30

# Shell access
BACKEND=$(docker ps -q -f name=djangocrm_crm_backend)
docker exec -it $BACKEND python manage.py shell
docker exec -it $BACKEND python manage.py manage_rls --status

# Database
docker exec -it $(docker ps -q -f name=djangocrm_crm_db) psql -U crm_user -d crm_db

# Services status
docker stack services djangocrm
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

## Services (Docker Swarm)

| Service | Image | Port | Role |
|---------|-------|------|------|
| crm_db | postgres:16-alpine | 5432 | Database |
| crm_backend | djangocrm-backend | 8000 | Django + Gunicorn |
| crm_worker | djangocrm-backend | — | Celery Worker |
| crm_beat | djangocrm-backend | — | Celery Beat |
| crm_frontend | djangocrm-frontend | 3000 | SvelteKit SSR |
| crm_redis | redis:7-alpine | 6379 | Broker + Cache |

## Traefik Routing

- Priority 20: `/api`, `/admin`, `/static`, `/swagger`, `/media` -> backend:8000
- Priority 10: `/*` (catch-all) -> frontend:3000

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
| Chatwoot connector | `backend/chatwoot/connector.py` (webhook handlers, sync, group detection) |
| Chatwoot channel provider | `backend/chatwoot/provider.py` (send/receive messages) |
| Conversation real-time | `backend/conversations/views.py` (`ConversationUpdatesView`) |
| Webhook routing | `backend/integrations/views.py` (`webhook_receiver`), `backend/integrations/tasks.py` |

## Chatwoot Integration

### Architecture
```
Chatwoot → POST /api/integrations/webhooks/chatwoot/ (AllowAny)
  → Identify org by account_id match
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
- **Contact dedup**: `_get_or_create_contact` matches by: (1) chatwoot_id stored in description, (2) email, (3) phone, (4) exact name for contacts without email/phone (groups). Handles both `NULL` and `""` for empty fields
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

## Credentials (Development)

- **Admin**: admin@talkhub.me / TalkHub2026!
- **DB**: crm_user / crm_talkhub_2026
- **SMTP**: talkhub@talkhub.me (configured in djangocrm.yaml)
