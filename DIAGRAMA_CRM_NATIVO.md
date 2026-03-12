# 📊 DIAGRAMA COMPLETO DO CRM — TalkHub

> Validado código a código em todas as 17 apps Django.
> Última atualização: 2026-03-11 (Chatwoot connector completo + contact dedup + sync all statuses).

---

## 1. ARQUITETURA GERAL

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (SvelteKit 2 + Svelte 5)            │
│  Runes: $state, $derived, $effect, $props                       │
│  TailwindCSS 4 + shadcn-svelte (bits-ui) + @lucide/svelte      │
│  apiRequest() → JWT Bearer token                                │
│  Notificações: svelte-sonner | DnD: svelte-dnd-action           │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS (Traefik)
┌──────────────────────────▼──────────────────────────────────────┐
│                  BACKEND (Django 5.2 + DRF 3.16)                │
│                                                                  │
│  Middleware Stack:                                                │
│  Security → WhiteNoise → Session → CSRF → Auth → CORS           │
│  → CurrentRequestUser (crum) → GetProfileAndOrg → SetOrgContext  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              PostgreSQL 16 + RLS                          │   │
│  │  SET app.current_org = '{org_id}'                         │   │
│  │  Policy: org_id = NULLIF(current_setting(...), '')        │   │
│  │  77 tabelas com RLS ativo                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────┐  ┌──────────┐  ┌──────────────────────┐      │
│  │ Celery 5.6   │  │ Redis 7  │  │ MinIO S3             │      │
│  │ 25 beat jobs │  │ Broker   │  │ s3.talkhub.me        │      │
│  │ @shared_task │  │ + Cache  │  │ uploads/attachments  │      │
│  └──────────────┘  └──────────┘  └──────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. CLASSES BASE (`common/base.py`)

```python
class AssignableMixin(models.Model):          # Abstract
    assigned_to = M2M → Profile               # related_name varia por model
    teams       = M2M → Teams                 # related_name varia por model
    # Props: get_team_users, get_team_and_assigned_users, get_assigned_users_not_in_teams

class BaseModel(models.Model):                # Abstract
    id          = UUIDField(primary_key=True, default=uuid4)
    created_by  = FK → Profile (null, SET_NULL)
    updated_by  = FK → Profile (null, SET_NULL)
    created_at  = DateTimeField(auto_now_add)
    updated_at  = DateTimeField(auto_now)
    is_active   = BooleanField(default=True)

class OrgScopedMixin(models.Model):           # Abstract — adicionado no bugfix multi-tenant
    objects = OrgScopedManager()              # Filtra por org automaticamente
    # save() valida org_id obrigatório
    # NÃO define campo org — cada model define seu próprio FK

class BaseOrgModel(BaseModel):                # Abstract
    org     = FK → Org (CASCADE, related_name="+")
    objects = OrgScopedManager()
    # save() valida org_id obrigatório
    # Meta: ordering = ["-created_at"], indexes = [org, -created_at]
```

### Padrão de Herança

| Padrão | Models |
|--------|--------|
| `AssignableMixin + OrgScopedMixin + BaseModel` | Lead, Contact, Account, Opportunity, Case, Task, Invoice, Estimate, RecurringInvoice |
| `OrgScopedMixin + BaseModel` | Profile, Address, Tags, Teams, Comment, CommentFiles, Attachments, Document, APISettings, Activity, Board, BoardMember, BoardColumn, BoardTask, LeadPipeline, LeadStage, CasePipeline, CaseStage, TaskPipeline, TaskStage, Solution, AccountEmail, AccountEmailLog, Product, InvoiceTemplate, InvoiceLineItem, Payment, EstimateLineItem, RecurringInvoiceLineItem, InvoiceHistory, OpportunityLineItem, StageAgingConfig, SalesGoal, GoalBreakdown |
| `BaseOrgModel` | Order, OrderLineItem, Lancamento, Parcela, PlanoDeContasGrupo, PlanoDeContas, FormaPagamento, PaymentTransaction, IntegrationConnection, SyncJob, IntegrationLog, WebhookLog, FieldMapping, ConflictLog, OrgFeatureFlag, ChannelConfig, Conversation, Message, Campaign, CampaignAudience, CampaignRecipient, CampaignStep, Automation, AutomationLog |
| `BaseModel` (sem org) | User, Org, SessionToken, MagicLinkToken, ContactFormSubmission, PendingInvitation |

---

## 3. FLUXO PRINCIPAL DE VENDAS

```
┌──────────┐   converte    ┌─────────────┐    gera      ┌──────────┐
│   LEAD   │──────────────→│ OPPORTUNITY  │─────────────→│ ESTIMATE │
│          │               │              │              │          │
│ stage FK │               │ lead FK      │              │ opp FK   │
│ pipeline │               │ account FK   │              │ acc FK   │
│ contacts │               │ contacts M2M │              │ cont FK  │
└────┬─────┘               │ line_items   │              └────┬─────┘
     │                     └──────┬───────┘                   │
     │ cria Contact               │                           │ aceita →
     │ se não existe              │                           │ converte
     ▼                            │                           ▼
┌──────────┐                      │                    ┌──────────┐
│ CONTACT  │◄─────────────────────┘                    │ INVOICE  │
│          │   contacts M2M                            │          │
│ account  │                                           │ acc FK   │
│ FK       │                                           │ cont FK  │
└────┬─────┘                                           │ opp FK   │
     │                                                 │ line_items│
     │ pertence a                                      └────┬─────┘
     ▼                                                      │
┌──────────┐                                                │ gera
│ ACCOUNT  │◄───────────────────────────────────────────────┘
│          │   account FK                              ┌──────────┐
│ contacts │                                           │ PAYMENT  │
│ M2M      │                                           │ inv FK   │
└──────────┘                                           └──────────┘
                                                            │
                                                            ▼
                                                       ┌──────────┐
                                                       │  ORDER   │
                                                       │ acc FK   │
                                                       │ cont FK  │
                                                       │ opp FK   │
                                                       │ line_items│
                                                       └──────────┘
```

---

## 4. AUTENTICAÇÃO (`common/views.py`)

| Endpoint | View | Método | Auth |
|----------|------|--------|------|
| `/api/auth/register/` | RegisterView | POST | AllowAny |
| `/api/auth/login/` | LoginView | POST | AllowAny |
| `/api/auth/refresh-token/` | TokenRefreshView | POST | AllowAny |
| `/api/auth/me/` | ProfileView | GET, PUT | IsAuthenticated |
| `/api/auth/google/` | GoogleLoginView | POST | AllowAny |
| `/api/auth/magic-link/request/` | MagicLinkRequestView | POST | AllowAny |
| `/api/auth/magic-link/verify/` | MagicLinkVerifyView | POST | AllowAny |
| `/api/auth/forgot-password/` | ForgotPasswordView | POST | AllowAny |
| `/api/auth/reset-password/` | ResetPasswordView | POST | AllowAny |

JWT Claims: `{ user_id, org_id, email, role, exp }`

---

## 5. APPS — MODELS DETALHADOS

---

### 5.1 COMMON (`common/`)

#### Models

```
User (AbstractUser, BaseModel — SEM org)
├── phone                   CharField(20)
├── profile_pic             CharField(100)
├── activation_key          CharField(128)
├── key_expires             DateTime
└── Relações: profiles → Profile (1:N)

Org (BaseModel — SEM org, é a raiz do tenant)
├── name                    CharField(255)
├── api_key                 TextField(unique, auto)
├── company_name            CharField(255)
├── logo                    ImageField
├── address_line/city/state/postcode/country
├── phone/email/website
├── tax_id                  CharField(50)
├── default_currency        CharField (choices CURRENCY_CODES)
├── default_country         CharField (choices COUNTRIES)
└── Relações: profiles, leads, contacts, accounts, etc.

Profile (OrgScopedMixin + BaseModel)
├── user                    FK → User
├── org                     FK → Org
├── role                    CharField (ADMIN, USER)
├── phone                   CharField(20, unique per org)
├── alternate_phone         CharField(20)
├── address                 FK → Address (nullable)
├── has_sales_access        Boolean
├── has_marketing_access    Boolean
├── has_financial_access    Boolean
├── is_organization_admin   Boolean
├── date_of_joining         DateField
├── profile_photo           ImageField
└── Meta: unique_together = (user, org)

Address (OrgScopedMixin + BaseModel)
├── address_line/street/city/state/postcode/country
└── org                     FK → Org

Tags (OrgScopedMixin + BaseModel)
├── name                    CharField(100)
├── slug                    CharField(100, unique per org)
├── color                   CharField(20, 18 cores)
├── description             TextField
├── talkhub_tag_ns          CharField (omni sync)
└── org                     FK → Org

Teams (OrgScopedMixin + BaseModel)
├── name                    CharField(100)
├── description             TextField
├── users                   M2M → Profile
└── org                     FK → Org

Comment (OrgScopedMixin + BaseModel)
├── comment                 TextField
├── commented_by            FK → Profile
├── account/lead/opportunity/contact/case/task/profile  FK (nullable)
└── org                     FK → Org

CommentFiles (OrgScopedMixin + BaseModel)
├── comment                 FK → Comment
├── comment_file            FileField(comment_files/)
└── org                     FK → Org

Attachments (OrgScopedMixin + BaseModel)
├── file_name               CharField(255)
├── attachment              FileField(attachments/)
├── account/lead/opportunity/contact/case/task  FK (nullable)
└── org                     FK → Org

Document (OrgScopedMixin + BaseModel)
├── title                   CharField(500)
├── document_file           FileField(documents/)
├── shared_to               M2M → Profile
└── org                     FK → Org

APISettings (OrgScopedMixin + BaseModel)
├── title                   CharField(64)
├── website                 URLField
├── lead_assigned_to        M2M → Profile
├── tags                    M2M → Tags
└── org                     FK → Org

Activity (OrgScopedMixin + BaseModel)
├── content_type            FK → ContentType
├── object_id               UUIDField
├── content_object          GenericForeignKey
├── action                  CharField(50) — created, updated, deleted
├── detail                  JSONField
└── org                     FK → Org

SessionToken (BaseModel — SEM org)
├── user                    FK → User
├── token                   CharField(255, unique)
└── expires_at              DateTime

MagicLinkToken (BaseModel — SEM org)
├── email                   EmailField
├── token                   UUIDField(unique)
├── expires_at              DateTime
└── is_used                 Boolean

ContactFormSubmission (BaseModel — SEM org)
├── name/email/phone/subject/reason/message
└── org                     FK → Org (nullable)

PendingInvitation (BaseModel — SEM org)
├── email                   EmailField
├── role                    CharField (ADMIN, USER)
├── org                     FK → Org
├── invited_by              FK → Profile
├── token                   UUIDField(unique)
├── expires_at              DateTime
└── is_accepted             Boolean
```

---

### 5.2 LEADS (`leads/`)

```
Lead (AssignableMixin + OrgScopedMixin + BaseModel)
├── title                   CharField(255) — nome/assunto do lead
├── salutation              CharField(64)
├── first_name/last_name    CharField(255)
├── email                   EmailField (unique per org, case-insensitive)
├── phone                   CharField(25, validator)
├── job_title               CharField(255)
├── website                 CharField(255)
├── linkedin_url            URLField(500)
├── status                  CharField (LEAD_STATUS choices)
├── source                  CharField (LEAD_SOURCE choices)
├── industry                CharField (INDCHOICES)
├── rating                  CharField (HOT, WARM, COLD)
├── opportunity_amount      Decimal(12,2)
├── currency                CharField (CURRENCY_CODES)
├── probability             Integer (0-100, constraint)
├── close_date              DateField
├── address_line/city/state/postcode/country
├── last_contacted          DateField
├── next_follow_up          DateField
├── description             TextField
├── company_name            CharField(255)
├── kanban_order            Decimal(15,6)
├── omni_ticket_item_id     CharField(255, indexed)
├── omni_ticket_list_id     CharField(255)
├── assigned_to             M2M → Profile (lead_assigned_users)
├── teams                   M2M → Teams (lead_teams)
├── tags                    M2M → Tags (lead_tags)
├── contacts                M2M → Contact (lead_contacts)
├── stage                   FK → LeadStage (nullable)
├── org                     FK → Org
├── Constraints: unique_lead_email_per_org, lead_probability_range, lead_amount_non_negative
└── Props: primary_contact, days_since_last_contact, is_stale, days_until_follow_up, is_follow_up_overdue

LeadPipeline (OrgScopedMixin + BaseModel)
├── name                    CharField(255)
├── description             TextField
├── is_default              Boolean (unique per org constraint)
├── is_active               Boolean
├── auto_create_opportunity Boolean
└── org                     FK → Org

LeadStage (OrgScopedMixin + BaseModel)
├── pipeline                FK → LeadPipeline
├── name                    CharField(100)
├── order                   PositiveInteger
├── color                   CharField(7) — hex
├── stage_type              CharField (open, won, lost)
├── maps_to_status          CharField (LEAD_STATUS)
├── win_probability         Integer
├── wip_limit               PositiveInteger (nullable)
├── org                     FK → Org
└── Meta: unique_together = (pipeline, name)
```

---

### 5.3 CONTACTS (`contacts/`)

```
Contact (AssignableMixin + OrgScopedMixin + BaseModel)
├── first_name/last_name    CharField(255)
├── email                   EmailField (unique per org, case-insensitive)
├── phone                   CharField(25, validator)
├── organization            CharField(255) — company name
├── title                   CharField(255) — job title
├── department              CharField(255)
├── do_not_call             Boolean
├── linkedin_url            URLField
├── instagram/facebook/tiktok/telegram  CharField(255)
├── address_line/city/state/postcode/country
├── description             TextField
├── source                  CharField (CONTACT_SOURCE choices)
├── talkhub_channel_type    CharField(100)
├── talkhub_channel_id      CharField(255)
├── talkhub_subscriber_id   CharField(100, indexed)
├── sms_opt_in              Boolean(True)
├── email_opt_in            Boolean(True)
├── omni_user_ns            CharField(100, indexed)
├── assigned_to             M2M → Profile (contact_assigned_users)
├── teams                   M2M → Teams (contact_teams)
├── tags                    M2M → Tags (contact_tags)
├── account                 FK → Account (nullable, primary_contacts)
├── org                     FK → Org
└── Constraint: unique_contact_email_per_org
```

---

### 5.4 ACCOUNTS (`accounts/`)

```
Account (AssignableMixin + OrgScopedMixin + BaseModel)
├── name                    CharField(255, unique per org case-insensitive)
├── email                   EmailField
├── phone                   CharField(25, validator)
├── website                 URLField
├── industry                CharField (INDCHOICES)
├── number_of_employees     PositiveInteger
├── annual_revenue          Decimal(15,2, non-negative constraint)
├── currency                CharField (CURRENCY_CODES)
├── address_line/city/state/postcode/country
├── description             TextField
├── assigned_to             M2M → Profile (account_assigned_users)
├── teams                   M2M → Teams (account_teams)
├── contacts                M2M → Contact (account_contacts)
├── tags                    M2M → Tags (account_tags)
└── org                     FK → Org

AccountEmail (OrgScopedMixin + BaseModel)
├── from_account            FK → Account (nullable)
├── recipients              M2M → Contact
├── message_subject/message_body/rendered_message_body  TextField
├── timezone                CharField(100, default=UTC)
├── scheduled_date_time     DateTime
├── scheduled_later         Boolean
├── from_email              EmailField
└── org                     FK → Org

AccountEmailLog (OrgScopedMixin + BaseModel)
├── email                   FK → AccountEmail (nullable)
├── contact                 FK → Contact (nullable)
├── is_sent                 Boolean
└── org                     FK → Org
```

---

### 5.5 OPPORTUNITY (`opportunity/`)

```
Opportunity (AssignableMixin + OrgScopedMixin + BaseModel)
├── name                    CharField(255)
├── account                 FK → Account (nullable)
├── stage                   CharField (STAGES: PROSPECTING → CLOSED_WON/LOST)
├── opportunity_type        CharField (OPPORTUNITY_TYPES)
├── currency                CharField (CURRENCY_CODES)
├── amount                  Decimal(12,2, non-negative constraint)
├── amount_source           CharField (MANUAL, CALCULATED)
├── probability             Integer (0-100, constraint)
├── closed_on               DateField
├── lead_source             CharField (SOURCES)
├── stage_changed_at        DateTime — deal aging tracking
├── description             TextField
├── lead                    FK → Lead (nullable)
├── contacts                M2M → Contact (opportunity_contacts)
├── assigned_to             M2M → Profile (opportunity_assigned_users)
├── teams                   M2M → Teams (opportunity_teams)
├── closed_by               FK → Profile (nullable)
├── tags                    M2M → Tags (opportunity_tags)
├── org                     FK → Org
├── Props: days_in_current_stage, aging_status (green/yellow/red)
└── save(): auto-set probability from STAGE_PROBABILITIES, track stage changes

OpportunityLineItem (OrgScopedMixin + BaseModel)
├── opportunity             FK → Opportunity (line_items)
├── product                 FK → Product (nullable)
├── name/description        CharField
├── quantity                Decimal(10,2)
├── unit_price              Decimal(12,2)
├── discount_type           CharField (PERCENTAGE, FIXED)
├── discount_value/discount_amount  Decimal(12,2)
├── subtotal/total          Decimal(12,2)
├── order                   PositiveInteger
├── org                     FK → Org
└── save(): auto-calc totals, recalculate parent opportunity amount

StageAgingConfig (OrgScopedMixin + BaseModel)
├── stage                   CharField (STAGES)
├── expected_days           PositiveInteger(14)
├── warning_days            PositiveInteger (nullable)
├── org                     FK → Org
└── Meta: unique_together = (org, stage)

SalesGoal (OrgScopedMixin + BaseModel)
├── name                    CharField(255)
├── goal_type               CharField (REVENUE, DEALS)
├── target_value            Decimal(12,2)
├── period_type             CharField (MONTHLY, QUARTERLY, YEARLY, CUSTOM)
├── period_start/period_end DateField
├── assigned_to             FK → Profile (nullable)
├── team                    FK → Teams (nullable)
├── milestone_50/90/100_notified  Boolean
├── org                     FK → Org
└── Props: progress_percent, status (on_track, at_risk, behind, completed)

GoalBreakdown (OrgScopedMixin + BaseModel)
├── goal                    FK → SalesGoal (breakdowns)
├── breakdown_type          CharField (user, product, channel, stage)
├── breakdown_key           CharField(255)
├── breakdown_label         CharField(255)
├── target_value            Decimal(12,2)
├── current_value           Decimal(12,2)
├── org                     FK → Org
└── Meta: unique_together = (goal, breakdown_type, breakdown_key)
```

---

### 5.6 CASES (`cases/`)

```
Case (AssignableMixin + OrgScopedMixin + BaseModel)
├── name                    CharField(64)
├── status                  CharField (STATUS_CHOICE)
├── priority                CharField (PRIORITY_CHOICE)
├── case_type               CharField (CASE_TYPE, nullable)
├── account                 FK → Account (nullable)
├── contacts                M2M → Contact (case_contacts)
├── closed_on               DateField
├── description             TextField
├── first_response_at       DateTime
├── resolved_at             DateTime
├── sla_first_response_hours  PositiveInteger(4)
├── sla_resolution_hours    PositiveInteger(24)
├── sla_priority            CharField (low, medium, high, urgent)
├── escalation_level        PositiveSmallInteger(0)
├── escalated_at            DateTime
├── kanban_order            Decimal(15,6)
├── omni_ticket_item_id     CharField(255, indexed)
├── omni_ticket_list_id     CharField(255)
├── stage                   FK → CaseStage (nullable)
├── assigned_to             M2M → Profile (case_assigned_users)
├── teams                   M2M → Teams (cases_teams)
├── tags                    M2M → Tags (case_tags)
├── org                     FK → Org
└── Props: is_sla_first_response_breached, is_sla_resolution_breached, deadlines

Solution (OrgScopedMixin + BaseModel)
├── title                   CharField(255)
├── description             TextField
├── status                  CharField (draft, reviewed, approved)
├── is_published            Boolean
├── cases                   M2M → Case (solutions)
└── org                     FK → Org

CasePipeline (OrgScopedMixin + BaseModel)
├── name/description
├── is_default              Boolean (unique per org)
├── sla_priority_multipliers  JSONField
├── auto_escalate           Boolean
└── org                     FK → Org

CaseStage (OrgScopedMixin + BaseModel)
├── pipeline                FK → CasePipeline
├── name/order/color
├── stage_type              CharField (open, closed, rejected)
├── maps_to_status          CharField (STATUS_CHOICE)
├── wip_limit               PositiveInteger (nullable)
├── org                     FK → Org
└── Meta: unique_together = (pipeline, name)
```

---

### 5.7 TASKS (`tasks/`)

```
Task (AssignableMixin + OrgScopedMixin + BaseModel)
├── title                   CharField(200)
├── status                  CharField (New, In Progress, Completed)
├── priority                CharField (Low, Medium, High)
├── due_date                DateField
├── description             TextField
├── kanban_order            Decimal(15,6)
├── account                 FK → Account (nullable)
├── opportunity             FK → Opportunity (nullable)
├── case                    FK → Case (nullable)
├── lead                    FK → Lead (nullable)
├── contacts                M2M → Contact (task_contacts)
├── stage                   FK → TaskStage (nullable)
├── assigned_to             M2M → Profile (task_assigned_users)
├── teams                   M2M → Teams (tasks_teams)
├── tags                    M2M → Tags (task_tags)
├── org                     FK → Org
├── Validation: max 1 parent entity (account OR opportunity OR case OR lead)
└── Props: is_overdue, days_until_due

Board (OrgScopedMixin + BaseModel)
├── name/description
├── owner                   FK → Profile
├── members                 M2M → Profile (through BoardMember)
├── is_archived             Boolean
├── talkhub_list_id         CharField(100) — omni sync
└── org                     FK → Org

BoardMember (OrgScopedMixin + BaseModel)
├── board                   FK → Board
├── profile                 FK → Profile
├── role                    CharField (owner, admin, member)
└── Meta: unique_together = (board, profile)

BoardColumn (OrgScopedMixin + BaseModel)
├── board                   FK → Board
├── name/order/color
├── limit                   PositiveInteger (WIP limit)
├── talkhub_stage_id        CharField(100) — omni sync
└── Meta: unique_together = (board, name)

BoardTask (OrgScopedMixin + BaseModel)
├── column                  FK → BoardColumn
├── title/description/order
├── priority                CharField (low, medium, high, urgent)
├── assigned_to             M2M → Profile
├── due_date                DateTime
├── completed_at            DateTime
├── account/contact/opportunity  FK (nullable)
├── talkhub_item_id         CharField(100) — omni sync
├── talkhub_custom_data     JSONField
└── org                     FK → Org

TaskPipeline (OrgScopedMixin + BaseModel)
├── name/description
├── is_default              Boolean (unique per org)
└── org                     FK → Org

TaskStage (OrgScopedMixin + BaseModel)
├── pipeline                FK → TaskPipeline
├── name/order/color
├── stage_type              CharField (open, in_progress, completed)
├── maps_to_status          CharField
├── wip_limit               PositiveInteger (nullable)
└── Meta: unique_together = (pipeline, name)
```


---

### 5.8 INVOICES (`invoices/`)

```
Product (OrgScopedMixin + BaseModel)
├── name                    CharField(255)
├── description             TextField
├── sku                     CharField(100, unique per org)
├── price                   Decimal(12,2)
├── currency                CharField (CURRENCY_CODES)
├── category                CharField(100)
└── org                     FK → Org

InvoiceTemplate (OrgScopedMixin + BaseModel)
├── name                    CharField(100)
├── logo                    ImageField
├── primary_color/secondary_color  CharField(7)
├── template_html/template_css  TextField
├── default_notes/default_terms/footer_text  TextField
├── is_default              Boolean (1 per org)
└── org                     FK → Org

Invoice (AssignableMixin + OrgScopedMixin + BaseModel)
├── invoice_title           CharField(100)
├── invoice_number          CharField(50, unique, auto: INV-YYYYMMDD-XXXX)
├── status                  CharField (Draft, Sent, Viewed, Paid, Partially_Paid, Overdue, Pending, Cancelled)
├── account                 FK → Account (PROTECT) — obrigatório via serializer
├── contact                 FK → Contact (nullable) — obrigatório via serializer
├── opportunity             FK → Opportunity (nullable)
├── client_name/email/phone — desnormalizados para PDF
├── billing_address_line/city/state/postcode/country — endereço "De"
├── client_address_line/city/state/postcode/country — endereço "Para"
├── subtotal/discount_type/discount_value/discount_amount  Decimal
├── tax_rate/tax_amount/shipping_amount  Decimal
├── total_amount/amount_paid/amount_due  Decimal
├── currency                CharField (CURRENCY_CODES, default=USD)
├── issue_date              DateField (default=today)
├── due_date                DateField (auto-calc from payment_terms)
├── payment_terms           CharField (DUE_ON_RECEIPT, NET_15/30/45/60, CUSTOM)
├── sent_at/viewed_at/paid_at/cancelled_at  DateTime
├── reminder_enabled/reminder_days_before/after/frequency/last_sent/count
├── public_token            CharField(64, unique, auto)
├── public_link_enabled     Boolean
├── template                FK → InvoiceTemplate (nullable)
├── notes/terms/details     TextField
├── billing_period/po_number  CharField
├── assigned_to             M2M → Profile
├── teams                   M2M → Teams
├── org                     FK → Org
└── Props: is_overdue, public_url, formatted_total_amount

InvoiceLineItem (OrgScopedMixin + BaseModel)
├── invoice                 FK → Invoice (line_items)
├── product                 FK → Product (nullable)
├── name/description
├── quantity                Decimal(10,2)
├── unit_price              Decimal(12,2)
├── discount_type/discount_value/discount_amount
├── tax_rate/tax_amount
├── subtotal/total          Decimal(12,2)
├── order                   PositiveInteger
└── org                     FK → Org

Payment (OrgScopedMixin + BaseModel)
├── invoice                 FK → Invoice (payments)
├── amount                  Decimal(12,2)
├── payment_date            DateField
├── payment_method          CharField (CASH, CHECK, CREDIT_CARD, BANK_TRANSFER, PAYPAL, STRIPE, OTHER)
├── reference_number        CharField(100)
├── notes                   TextField
├── org                     FK → Org
└── save(): auto-update invoice amount_paid/amount_due/status

Estimate (AssignableMixin + OrgScopedMixin + BaseModel)
├── estimate_number         CharField(50, unique, auto: EST-YYYYMMDD-XXXX)
├── title                   CharField(100)
├── status                  CharField (Draft, Sent, Viewed, Accepted, Declined, Expired)
├── account                 FK → Account (PROTECT)
├── contact                 FK → Contact (nullable)
├── opportunity             FK → Opportunity (nullable)
├── client_name/email/phone/address
├── subtotal/discount/tax/total_amount  Decimal
├── currency                CharField (CURRENCY_CODES, default=USD)
├── issue_date/expiry_date  DateField
├── sent_at/viewed_at/accepted_at/declined_at  DateTime
├── converted_to_invoice    FK → Invoice (nullable)
├── public_token            CharField(64, unique, auto)
├── notes/terms             TextField
├── assigned_to/teams       M2M
└── org                     FK → Org

EstimateLineItem (OrgScopedMixin + BaseModel)
├── estimate                FK → Estimate (line_items)
├── product/name/description/quantity/unit_price
├── discount_type/value/amount, tax_rate/amount
├── subtotal/total/order
└── org                     FK → Org

RecurringInvoice (AssignableMixin + OrgScopedMixin + BaseModel)
├── title                   CharField(100)
├── account/contact/opportunity  FK
├── client_name/email
├── frequency               CharField (WEEKLY, BIWEEKLY, MONTHLY, QUARTERLY, SEMI_ANNUALLY, YEARLY, CUSTOM)
├── custom_days             PositiveInteger (nullable)
├── start_date/end_date/next_generation_date  DateField
├── payment_terms/auto_send/currency
├── subtotal/discount_type/discount_value/tax_rate/total_amount
├── notes/terms
├── invoices_generated      PositiveInteger
├── assigned_to/teams       M2M
└── org                     FK → Org

RecurringInvoiceLineItem (OrgScopedMixin + BaseModel)
├── recurring_invoice       FK → RecurringInvoice (line_items)
├── product/name/description/quantity/unit_price
├── discount_type/value, tax_rate, order
└── org                     FK → Org

InvoiceHistory (OrgScopedMixin + BaseModel) — Audit Trail
├── invoice                 FK → Invoice (invoice_history)
├── invoice_title/invoice_number/status
├── client_name/email/total_amount/amount_due/currency/due_date
├── updated_by              FK → Profile
├── details                 TextField
└── org                     FK → Org
```

---

### 5.9 ORDERS (`orders/`)

```
Order (BaseOrgModel)
├── name                    CharField(255)
├── order_number            CharField(100)
├── status                  CharField (DRAFT, ACTIVATED, COMPLETED, CANCELLED)
├── account                 FK → Account (CASCADE)
├── contact                 FK → Contact (nullable)
├── opportunity             FK → Opportunity (nullable)
├── currency/subtotal/discount_amount/tax_amount/total_amount  Decimal
├── order_date/activated_date/shipped_date  DateField
├── billing_address_line/city/state/postcode/country
├── shipping_address_line/city/state/postcode/country
├── description             TextField
└── org (via BaseOrgModel)

OrderLineItem (BaseOrgModel)
├── order                   FK → Order (line_items)
├── product                 FK → Product (nullable)
├── name/description/quantity/unit_price/discount_amount/total
├── sort_order              Integer
└── save(): auto-calc total, validate org matches parent
```

---

### 5.10 FINANCEIRO (`financeiro/`)

```
PlanoDeContasGrupo (BaseOrgModel)
├── nome                    CharField
├── tipo                    CharField (RECEITA, DESPESA)
└── db_table: financeiro_plano_grupo

PlanoDeContas (BaseOrgModel)
├── grupo                   FK → PlanoDeContasGrupo
├── nome                    CharField
├── codigo                  CharField
└── db_table: financeiro_plano_contas

FormaPagamento (BaseOrgModel)
├── nome                    CharField
├── tipo                    CharField
└── db_table: financeiro_forma_pagamento

Lancamento (BaseOrgModel) — Conta a Pagar / Receber
├── tipo                    CharField (PAGAR, RECEBER)
├── descricao               CharField(500)
├── observacoes             TextField
├── plano_de_contas         FK → PlanoDeContas (nullable)
├── account                 FK → Account (nullable)
├── contact                 FK → Contact (nullable)
├── opportunity             FK → Opportunity (nullable)
├── invoice                 FK → Invoice (nullable)
├── currency                CharField (FINANCEIRO_CURRENCY_CODES, default=BRL)
├── valor_total             Decimal(18,8)
├── exchange_rate_to_base   Decimal(18,8, default=1)
├── valor_convertido        Decimal(18,2, auto-calc)
├── forma_pagamento         FK → FormaPagamento (nullable)
├── numero_parcelas         PositiveInteger(1)
├── data_primeiro_vencimento  DateField
├── status                  CharField (ABERTO, PAGO, CANCELADO)
├── competencia_ano/mes     Integer (auto from data_primeiro_vencimento)
├── db_table: financeiro_lancamento
└── Methods: generate_parcelas(), update_status()

Parcela (BaseOrgModel) — Parcela individual
├── lancamento              FK → Lancamento (parcelas)
├── numero                  PositiveInteger
├── valor_parcela           Decimal(18,8)
├── valor_parcela_convertido  Decimal(18,2, auto-calc)
├── currency/exchange_rate_to_base
├── data_vencimento         DateField
├── data_pagamento          DateField (nullable)
├── status                  CharField (ABERTO, PAGO, CANCELADO)
├── competencia_ano/mes     Integer
├── observacoes             TextField
├── db_table: financeiro_parcela
├── Meta: unique_together = (lancamento, numero)
└── Props: dias_atraso, pago_atrasado, status_message

PaymentTransaction (BaseOrgModel) — PIX / Gateway
├── transaction_type        CharField (pix_static, pix_dynamic, gateway)
├── status                  CharField (pending, confirmed, expired, failed, refunded)
├── amount                  Decimal(18,2, positive constraint)
├── currency                CharField(5, default=BRL)
├── pix_txid                CharField(255, unique per org)
├── pix_e2e_id              CharField(255)
├── gateway_reference       CharField(255)
├── paid_at/expires_at      DateTime
├── payer_name              CharField(255)
├── _payer_document         CharField(500) — Fernet encrypted CPF/CNPJ
├── metadata_json           JSONField
├── invoice                 FK → Invoice (nullable)
├── lancamento              FK → Lancamento (nullable)
├── contact                 FK → Contact (nullable)
├── db_table: payment_transaction
└── Props: payer_document (decrypt on read, encrypt on write)
```


---

### 5.11 TALKHUB OMNI (`talkhub_omni/`)

```
TalkHubConnection (OrgScopedMixin + BaseModel)
├── api_url/api_token (Fernet encrypted)
├── is_active/is_connected
├── last_sync_at            DateTime
├── org                     FK → Org
└── db_table: talkhub_connection

TalkHubSyncJob (OrgScopedMixin + BaseModel)
├── connection              FK → TalkHubConnection
├── sync_type               CharField (contacts, tickets, tags, team_members, ticket_structure, statistics)
├── status                  CharField (PENDING, IN_PROGRESS, COMPLETED, FAILED)
├── total_records/imported_count/updated_count/skipped_count/error_count
├── error_log               JSONField
├── started_at/completed_at DateTime
└── db_table: talkhub_sync_job

TalkHubFieldMapping (OrgScopedMixin + BaseModel)
├── connection              FK → TalkHubConnection
├── entity_type             CharField (contact, ticket)
├── source_field/target_field  CharField
├── transform_type          CharField
└── db_table: talkhub_field_mapping

TalkHubOmniChannel (OrgScopedMixin + BaseModel)
├── connection              FK → TalkHubConnection
├── channel_id/channel_name/channel_type
├── is_active               Boolean
├── metadata_json           JSONField
└── db_table: talkhub_omni_channel

TalkHubSyncConfig (OrgScopedMixin + BaseModel)
├── connection              FK → TalkHubConnection
├── entity_type             CharField
├── sync_direction          CharField (in, out, bidirectional)
├── sync_interval_minutes   PositiveInteger
├── is_active               Boolean
├── last_sync_at            DateTime
└── db_table: talkhub_sync_config

TalkHubTeamMember (OrgScopedMixin + BaseModel)
├── connection              FK → TalkHubConnection
├── omni_user_id/omni_user_name/omni_user_email
├── profile                 FK → Profile (nullable)
├── is_active               Boolean
└── db_table: talkhub_team_member

TalkHubTicketListMapping (OrgScopedMixin + BaseModel)
├── connection              FK → TalkHubConnection
├── omni_list_id/omni_list_name
├── crm_entity_type         CharField (board, lead_pipeline, case_pipeline)
├── crm_entity_id           UUIDField
├── stage_mapping           JSONField
├── is_active               Boolean
└── db_table: talkhub_ticket_list_mapping

OmniStatisticsSnapshot (OrgScopedMixin + BaseModel)
├── connection              FK → TalkHubConnection
├── snapshot_date           DateField
├── total_contacts/total_tickets/open_tickets/closed_tickets
├── channels_data           JSONField
├── agents_data             JSONField
└── db_table: omni_statistics_snapshot
```

---

### 5.12 INTEGRATIONS (`integrations/`)

```
OrgFeatureFlag (BaseOrgModel)
├── feature_key             CharField(100, indexed)
├── is_enabled              Boolean
├── config_json             JSONField
└── Meta: unique_together = (org, feature_key)

IntegrationConnection (BaseOrgModel)
├── connector_slug          CharField(100, indexed)
├── display_name            CharField(255)
├── is_active/is_connected  Boolean
├── config_json             JSONField
├── webhook_secret          CharField(255)
├── last_sync_at            DateTime
├── health_status           CharField (healthy, degraded, down, unknown)
├── error_count             PositiveInteger
├── last_error              TextField
├── sync_interval_minutes   PositiveInteger(60)
├── conflict_strategy       CharField (last_write_wins, crm_wins, external_wins)
└── Meta: unique_together = (org, connector_slug)

SyncJob (BaseOrgModel)
├── connector_slug          CharField(100)
├── sync_type               CharField(50)
├── status                  CharField (PENDING, IN_PROGRESS, COMPLETED, FAILED, CANCELLED)
├── total_records/imported_count/updated_count/skipped_count/error_count
├── progress_detail/error_log  JSONField
├── started_at/completed_at DateTime

IntegrationLog (BaseOrgModel)
├── connector_slug/operation/direction/entity_type/entity_id
├── status                  CharField (success, error)
├── error_detail/processing_time_ms/metadata_json

WebhookLog (BaseOrgModel)
├── connector_slug/event_type
├── status                  CharField (queued, processed, failed, rejected)
├── processing_time_ms/payload_json

FieldMapping (BaseOrgModel)
├── connector_slug/source_field/target_field
├── field_type              CharField (text, number, date, select, concat, split, phone_format)
├── transform_config        JSONField
├── is_active               Boolean
└── Meta: unique_together = (org, connector_slug, source_field)

ConflictLog (BaseOrgModel)
├── connector_slug/entity_type/entity_id
├── crm_value/external_value  JSONField
├── resolved_by             CharField (crm, external, last_write)
├── fields_overwritten      JSONField
```

---

### 5.13 CHANNELS (`channels/`)

```
ChannelConfig (BaseOrgModel)
├── channel_type            CharField (talkhub_omni, smtp_native, chatwoot, evolution_api,
│                                      whatsapp_direct, tiktok, facebook, instagram, email, webchat)
├── provider                CharField(100)
├── display_name            CharField(255)
├── config_json             JSONField
├── is_active               Boolean
├── capabilities_json       JSONField (list)
└── db_table: channel_config
```

---

### 5.14 CONVERSATIONS (`conversations/`)

```
Conversation (BaseOrgModel)
├── contact                 FK → Contact (conversations)
├── channel                 CharField(50)
├── integration_provider    CharField(100)
├── status                  CharField (open, pending, resolved)
├── assigned_to             FK → Profile (nullable)
├── last_message_at         DateTime
├── omni_user_ns            CharField(100, indexed)
├── metadata_json           JSONField
├── tags                    M2M → Tags (conversation_tags)
└── db_table: conversation

Message (BaseOrgModel)
├── conversation            FK → Conversation (messages)
├── direction               CharField (in, out, agent, note, system)
├── msg_type                CharField (text, image, video, audio, file, payload)
├── content                 TextField
├── media_url               URLField(1024)
├── sender_type/sender_name/sender_id  CharField
├── timestamp               DateTime
├── metadata_json           JSONField
└── db_table: message
```

---

### 5.15 AUTOMATIONS (`automations/`)

```
Automation (BaseOrgModel)
├── name                    CharField(255)
├── automation_type         CharField (routine, logic_rule, social)
├── is_active               Boolean
├── config_json             JSONField
├── last_run_at             DateTime
├── run_count/error_count   PositiveInteger
└── db_table: automation

AutomationLog (BaseOrgModel)
├── automation              FK → Automation (logs)
├── status                  CharField (success, error, skipped)
├── trigger_data/result_data  JSONField
├── error_detail            TextField
├── execution_time_ms       PositiveInteger
└── db_table: automation_log
```

---

### 5.16 CAMPAIGNS (`campaigns/`)

```
Campaign (BaseOrgModel)
├── name                    CharField(255)
├── campaign_type           CharField (email_blast, nurture_sequence, whatsapp_broadcast)
├── status                  CharField (draft, scheduled, running, paused, completed, cancelled)
├── subject                 CharField(500)
├── body_template           TextField
├── scheduled_at/started_at/completed_at  DateTime
├── total_recipients/sent_count/delivered_count/opened_count/clicked_count/failed_count/bounce_count
└── db_table: campaign

CampaignAudience (BaseOrgModel)
├── campaign                FK → Campaign (audiences)
├── name                    CharField(255)
├── filter_criteria         JSONField
├── contact_count           PositiveInteger
└── db_table: campaign_audience

CampaignRecipient (BaseOrgModel)
├── campaign                FK → Campaign (recipients)
├── contact                 FK → Contact (campaign_recipients)
├── status                  CharField (pending, sent, delivered, opened, clicked, bounced, failed, unsubscribed)
├── sent_at/delivered_at/opened_at/clicked_at  DateTime
├── error_detail            TextField
├── current_step            PositiveInteger(0) — nurture tracking
├── Meta: unique_together = (campaign, contact)
└── db_table: campaign_recipient

CampaignStep (BaseOrgModel)
├── campaign                FK → Campaign (steps)
├── step_order              PositiveInteger
├── channel                 CharField (email, whatsapp)
├── subject/body_template
├── delay_hours             PositiveInteger(0)
├── sent_count              PositiveInteger(0)
├── Meta: unique_together = (campaign, step_order)
└── db_table: campaign_step
```

---

## 6. CELERY BEAT SCHEDULE (25 jobs)

| Job | Task | Schedule |
|-----|------|----------|
| generate-recurring-invoices | `invoices.tasks.generate_recurring_invoices` | Diário 00:00 |
| check-overdue-invoices | `invoices.tasks.check_overdue_invoices` | Diário 01:00 |
| process-payment-reminders | `invoices.tasks.process_payment_reminders` | Diário 09:00 |
| check-expired-estimates | `invoices.tasks.check_expired_estimates` | Diário 00:30 |
| check-stale-opportunities | `opportunity.tasks.check_stale_opportunities` | Diário 08:00 |
| check-goal-milestones | `opportunity.tasks.check_goal_milestones` | Diário 09:15 |
| recalculate-goal-breakdowns | `opportunity.tasks.recalculate_goal_breakdowns` | A cada 30 min |
| cases-sla-check | `cases.tasks.check_sla_breaches` | A cada 15 min |
| talkhub-sync-contacts | `talkhub_omni.tasks.periodic_sync_contacts` | A cada 5 min |
| talkhub-sync-tickets | `talkhub_omni.tasks.periodic_sync_tickets` | A cada 10 min |
| talkhub-sync-ticket-structure | `talkhub_omni.tasks.periodic_sync_ticket_structure` | Diário 02:00 |
| talkhub-sync-tags | `talkhub_omni.tasks.periodic_sync_tags` | Diário 03:00 |
| talkhub-sync-team-members | `talkhub_omni.tasks.periodic_sync_team_members` | Diário 04:00 |
| talkhub-sync-statistics | `talkhub_omni.tasks.periodic_sync_statistics` | A cada hora |
| talkhub-cleanup-old-logs | `talkhub_omni.tasks.periodic_cleanup_old_logs` | Diário 05:00 |
| integrations-cleanup-old-logs | `integrations.tasks.cleanup_old_logs` | Diário 05:30 |
| integrations-health-check | `integrations.tasks.check_integration_health` | A cada 10 min |
| integrations-check-pending-syncs | `integrations.tasks.check_pending_syncs` | A cada 5 min |
| integrations-review-agent | `integrations.tasks.periodic_review_integrations` | Diário 06:00 |
| check-overdue-parcelas | `financeiro.tasks.check_overdue_parcelas` | Diário 01:30 |
| expire-pending-invitations | `common.tasks.expire_pending_invitations` | Diário 02:30 |
| automations-process-due-routines | `automations.tasks.process_due_routines` | A cada minuto |
| reconcile-pix-transactions | `financeiro.tasks.reconcile_pix_transactions` | A cada 15 min |
| pix-reconciliation-report | `financeiro.tasks.pix_reconciliation_report` | Diário 07:00 |
| campaigns-check-scheduled | `campaigns.tasks.check_scheduled_campaigns` | A cada minuto |

---

## 7. RLS — TABELAS PROTEGIDAS (77 tabelas)

```
Core:           lead, accounts, contacts, opportunity, case, task, invoice
Supporting:     comment, commentFiles, attachments, document, teams, activity, tags,
                address, solution, profile
Boards:         board, board_column, board_task, board_member
Settings:       apiSettings
Email:          account_email, emailLogs
Invoicing:      invoice_history, invoice_line_item, invoice_template, payment,
                estimate, estimate_line_item, recurring_invoice, recurring_invoice_line_item
Products:       product
Orders:         orders, order_line_item
TalkHub Omni:   talkhub_connection, talkhub_sync_job, talkhub_field_mapping,
                talkhub_omni_channel, talkhub_sync_config, talkhub_team_member,
                talkhub_ticket_list_mapping, omni_statistics_snapshot
Integrations:   org_feature_flag, integration_connection, sync_job, integration_log,
                webhook_log, field_mapping, conflict_log
Channels:       channel_config
Conversations:  conversation, message
Financeiro:     financeiro_plano_grupo, financeiro_plano_contas, financeiro_forma_pagamento,
                financeiro_lancamento, financeiro_parcela
Invitations:    pending_invitation
Automations:    automation, automation_log
Goals:          sales_goal, stage_aging_config, opportunity_line_item, goal_breakdown
PIX:            payment_transaction
Campaigns:      campaign, campaign_audience, campaign_recipient, campaign_step
Pipelines:      lead_pipeline, lead_stage, case_pipeline, case_stage, task_pipeline, task_stage
Security:       security_audit_log
```

---

## 8. MAPA DE RELACIONAMENTOS (FK e M2M)

```
                                    ┌──────────┐
                                    │   ORG    │ (raiz do tenant)
                                    └────┬─────┘
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
              ┌──────────┐        ┌──────────┐        ┌──────────┐
              │  USER    │        │ PROFILE  │        │  TEAMS   │
              │ (global) │───────→│ user+org │←───────│ users M2M│
              └──────────┘  1:N   └────┬─────┘  M2M   └──────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
              ┌──────────┐      ┌──────────┐      ┌──────────┐
              │   LEAD   │      │ CONTACT  │      │ ACCOUNT  │
              │          │      │          │      │          │
              │contacts  │─────→│ account  │─────→│ contacts │
              │M2M       │      │ FK       │      │ M2M      │
              └────┬─────┘      └────┬─────┘      └────┬─────┘
                   │                 │                  │
                   │ lead FK         │ contacts M2M     │ account FK
                   ▼                 ▼                  ▼
              ┌──────────────────────────────────────────────┐
              │              OPPORTUNITY                      │
              │  account FK, lead FK, contacts M2M            │
              │  line_items → OpportunityLineItem             │
              └──────────┬───────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┬──────────────┐
          ▼              ▼              ▼              ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
    │ INVOICE  │  │ ESTIMATE │  │  ORDER   │  │   TASK   │
    │ acc+cont │  │ acc+cont │  │ acc+cont │  │ acc/opp/ │
    │ +opp FK  │  │ +opp FK  │  │ +opp FK  │  │ case/lead│
    └────┬─────┘  └──────────┘  └──────────┘  └────┬─────┘
         │                                          │
         ▼                                          ▼
    ┌──────────┐                              ┌──────────┐
    │ PAYMENT  │                              │   CASE   │
    │ inv FK   │                              │ acc FK   │
    └──────────┘                              │ contacts │
         │                                    └────┬─────┘
         ▼                                         │
    ┌──────────┐                              ┌──────────┐
    │LANCAMENTO│                              │ SOLUTION │
    │ acc/cont │                              │ cases M2M│
    │ opp/inv  │                              └──────────┘
    └────┬─────┘
         │
         ▼
    ┌──────────┐
    │ PARCELA  │
    │ lanc FK  │
    └──────────┘

    ┌──────────────────────────────────────────────────────┐
    │ CROSS-CUTTING: Tags M2M, Comment FK, Attachments FK, │
    │ Activity (GenericFK), assigned_to M2M, teams M2M      │
    └──────────────────────────────────────────────────────┘
```

---

## 9. APPS DJANGO (INSTALLED_APPS)

| App | Status | db_table prefix |
|-----|--------|-----------------|
| common | ✅ Ativo | profile, address, tags, teams, comment, etc. |
| accounts | ✅ Ativo | accounts, account_email, emailLogs |
| contacts | ✅ Ativo | contacts |
| leads | ✅ Ativo | lead, lead_pipeline, lead_stage |
| opportunity | ✅ Ativo | opportunity, opportunity_line_item, sales_goal, etc. |
| cases | ✅ Ativo | case, solution, case_pipeline, case_stage |
| tasks | ✅ Ativo | task, board, board_column, board_task, etc. |
| invoices | ✅ Ativo | invoice, product, payment, estimate, etc. |
| orders | ✅ Ativo | orders, order_line_item |
| financeiro | ✅ Ativo | financeiro_*, payment_transaction |
| talkhub_omni | ✅ Ativo | talkhub_*, omni_statistics_snapshot |
| integrations | ✅ Ativo | integration_*, sync_job, field_mapping, etc. |
| channels | ✅ Ativo | channel_config |
| conversations | ✅ Ativo | conversation, message |
| salesforce | ✅ Ativo | (sem models próprios — usa integrations) |
| automations | ⚠️ Não em INSTALLED_APPS | automation, automation_log |
| campaigns | ⚠️ Não em INSTALLED_APPS | campaign, campaign_* |
