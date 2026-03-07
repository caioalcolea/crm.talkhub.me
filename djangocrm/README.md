# TalkHub CRM

A modern, multi-tenant CRM platform built with Django REST Framework and SvelteKit.

![Python](https://img.shields.io/badge/python-3.10+-green.svg)
![Django](https://img.shields.io/badge/django-5.2-green.svg)
![SvelteKit](https://img.shields.io/badge/sveltekit-2.x-orange.svg)
![Svelte](https://img.shields.io/badge/svelte-5-orange.svg)

## Overview

TalkHub CRM is a full-featured Customer Relationship Management system designed for startups and small businesses. It combines a powerful Django REST API backend with a modern SvelteKit frontend, featuring multi-tenant architecture with PostgreSQL Row-Level Security (RLS) for enterprise-grade data isolation.

## Features

### Core CRM Modules
- **Leads** — Customizable pipeline per org, kanban drag-and-drop, conversion to opportunity
- **Accounts** — Company management with revenue, currency (21 currencies + crypto), address
- **Contacts** — Contact management with social media, TalkHub Omni integration fields
- **Opportunities** — Sales pipeline with stages, line items, products, probability
- **Cases** — Customer support with customizable kanban pipeline, SLA and auto-escalation
- **Tasks** — Kanban, calendar, custom boards, priorities, account linking
- **Invoices** — Invoices, estimates, recurring, products, PDF, taxes, discounts
- **Financeiro** — Financial module: transactions, payables/receivables, chart of accounts, payment methods, reports (P&L, cash flow)
- **Goals** — Sales goals by user, period, type (revenue/leads/deals)

### Integrations Hub
- **integrations** — Generic integration hub: connections, sync jobs, logs, webhooks, field mapping, conflict resolution
- **channels** — Communication channel abstraction (TalkHub Omni, SMTP, Chatwoot, Evolution API, etc.)
- **conversations** — Omnichannel inbox: generic conversations and messages
- **talkhub_omni** — TalkHub Omni connector: sync contacts, tickets, tags, team members, statistics

### Platform Features
- **Multi-Tenant Architecture** — PostgreSQL RLS for complete data isolation between organizations
- **Admin Panel** — Superadmin dashboard (`/admin-panel`) with KPIs, org and user management
- **Authentication** — Google OAuth + Magic Link (passwordless) + JWT with auto-rotation
- **Team Management** — Organize users into teams with role-based access
- **Activity Tracking** — Real-time activity feed on dashboard
- **Comments & Attachments** — On any record, with @user mentions
- **Tags** — Flexible tagging system
- **Currencies & Countries** — 21 currencies (including 8 crypto), 261 countries in Portuguese
- **Background Tasks** — Celery + Redis for async processing and periodic sync

## Tech Stack

### Backend
- **Django 5.2** with Django REST Framework 3.16
- **PostgreSQL 16** with Row-Level Security (RLS)
- **Redis 7** for caching and Celery broker
- **Celery 5.6** for background task processing
- **SimpleJWT** for authentication (org_id in token claims)
- **httpx** for external API integrations
- **boto3** for S3 storage (MinIO)

### Frontend
- **SvelteKit 2.x** with Svelte 5 (runes mode)
- **TailwindCSS 4** for styling
- **shadcn-svelte** UI components
- **Lucide** icons
- **adapter-node** for production deployment

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+ with pnpm
- PostgreSQL 14+
- Redis

### Backend Setup

```bash
cd djangocrm/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Frontend Setup

```bash
cd djangocrm/frontend
pnpm install
pnpm run dev
```

### Celery Worker

```bash
cd djangocrm/backend
celery -A crm worker --loglevel=INFO
```

### Access
- **Frontend**: http://localhost:5173
- **API / Swagger**: http://localhost:8000/swagger-ui/

## Docker Setup

```bash
# Full stack with Docker Compose
docker compose up --build

# Production (Docker Swarm)
./redeploy.sh
```

## Project Structure

```
djangocrm/
├── backend/                 # Django 5.2 REST API
│   ├── common/             # Auth, RLS, middleware, permissions, admin panel
│   ├── accounts/           # Companies
│   ├── contacts/           # Contacts (with TalkHub Omni fields)
│   ├── leads/              # Leads + kanban pipeline
│   ├── opportunity/        # Opportunities + line items
│   ├── cases/              # Cases + kanban + SLA
│   ├── tasks/              # Tasks + kanban + boards + calendar
│   ├── invoices/           # Invoices, estimates, recurring, products
│   ├── financeiro/         # Financial module
│   ├── integrations/       # Generic integration hub
│   ├── channels/           # Communication channel abstraction
│   ├── conversations/      # Omnichannel inbox
│   ├── talkhub_omni/       # TalkHub Omni connector
│   └── salesforce/         # Salesforce connector (stub)
├── frontend/               # SvelteKit 2 + Svelte 5 app
│   └── src/
│       ├── routes/(app)/   # Authenticated CRM routes
│       │   ├── conversations/    # Omnichannel inbox
│       │   ├── admin-panel/      # Superadmin panel
│       │   └── settings/integrations/ # Integration hub UI
│       └── lib/components/
│           ├── integrations/     # IntegrationCard, TalkHubChannelConfig
│           ├── conversations/    # ConversationTimeline
│           └── dashboard/        # MetricsWidget, SyncHealthPanel
└── docker/                 # Dockerfiles, stack config, entrypoint
```

## Multi-Tenancy & Security

PostgreSQL Row-Level Security (RLS) ensures complete data isolation:

- Session variable `app.current_org` set by middleware
- Non-superuser database user (`crm_user`) required for RLS enforcement
- Fail-safe: empty context returns zero rows
- All views protected with `[IsAuthenticated, HasOrgContext]`
- Admin panel uses `IsSuperAdmin` (checks `user.is_superuser`)

```bash
python manage.py manage_rls --status
python manage.py manage_rls --verify-user
```

## Authentication Flow

```
Login (Google/MagicLink) → token WITHOUT org_id
    → /org page (list user's orgs)
    → switch-org → new token WITH org_id
    → all API calls work with RLS
```

## Testing

```bash
cd djangocrm/backend
pytest                          # All tests with coverage
pytest --no-cov -x              # Fast, stop on first error
pytest integrations/tests/      # Specific module
```

## License

Software privado — não compartilhe.
