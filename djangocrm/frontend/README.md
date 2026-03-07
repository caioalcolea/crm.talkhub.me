# TalkHub CRM Frontend

SvelteKit 2 + Svelte 5 (runes) + TailwindCSS 4 + shadcn-svelte.

## Stack

- **SvelteKit 2.x** — Framework SSR (adapter-node)
- **Svelte 5** — Runes (`$state`, `$derived`, `$effect`, `$props`)
- **TailwindCSS 4** — Utility-first CSS
- **shadcn-svelte** — Componentes UI base
- **Lucide** — Ícones
- **bits-ui** — Primitivas de UI (Select, Popover, Dialog, etc.)

## Rotas

### `(app)/` — CRM autenticado (com sidebar)

| Rota | Módulo |
|------|--------|
| `/` | Dashboard com activity feed, métricas, sync health |
| `/accounts` | Empresas |
| `/contacts` | Contatos |
| `/leads` | Leads |
| `/opportunities` | Oportunidades (pipeline de vendas) |
| `/cases` | Casos (suporte) |
| `/tasks` | Tarefas (lista + kanban) |
| `/tasks/board/[boardId]` | Boards customizados |
| `/tasks/calendar` | Calendário de tarefas |
| `/invoices` | Faturas |
| `/invoices/new` | Nova fatura |
| `/invoices/[id]` | Detalhe da fatura |
| `/invoices/templates` | Templates de fatura |
| `/invoices/estimates` | Orçamentos |
| `/invoices/recurring` | Faturas recorrentes |
| `/invoices/products` | Catálogo de produtos |
| `/financeiro` | Dashboard financeiro |
| `/financeiro/lancamentos` | Lançamentos (receitas/despesas) |
| `/financeiro/pagar` | Contas a pagar |
| `/financeiro/receber` | Contas a receber |
| `/financeiro/plano-de-contas` | Plano de contas |
| `/financeiro/formas-pagamento` | Formas de pagamento |
| `/financeiro/relatorios` | Relatórios (DRE, fluxo de caixa) |
| `/goals` | Metas de vendas |
| `/conversations` | Inbox omnichannel (conversas TalkHub Omni) |
| `/admin-panel` | Painel superadmin (KPIs, orgs, usuários) |
| `/users` | Gestão de usuários |
| `/settings/*` | Configurações (org, tags, integrações) |
| `/settings/integrations` | Hub de integrações |
| `/settings/integrations/[slug]` | Config de integração específica |
| `/settings/integrations/logs` | Logs de integração |
| `/profile` | Perfil do usuário |

### `(no-layout)/` — Páginas sem sidebar

| Rota | Página |
|------|--------|
| `/login` | Login (Google OAuth + Magic Link) |
| `/login/verify` | Verificação do magic link |
| `/org` | Seleção de organização |
| `/org/new` | Criar organização |

## Componentes Principais

### Layout
- **AppSidebar** — Navegação com colapso, seções: CRM, Financeiro, Plataforma (com "Administração" para superusers)
- **Header** — Breadcrumbs, busca, notificações

### CRM
- **CrmDrawer + CrmPropertyRow** — Drawer lateral para CRUD de todas as entidades
- **KanbanBoard** — Drag-and-drop genérico (Tasks, Leads, Cases)

### Integrações
- **IntegrationCard** — Card de integração com status e ações
- **TalkHubChannelConfig** — Configuração de canais TalkHub Omni

### Conversations
- **ConversationTimeline** — Timeline de mensagens do inbox

### Dashboard
- **MetricsWidget** — KPIs do dashboard
- **AgentProductivity** — Produtividade por agente TalkHub
- **SyncHealthPanel** — Status de saúde das integrações

### UI (shadcn-svelte + custom)
- **Switch** — Toggle switch component
- Todos os componentes shadcn-svelte padrão (Button, Input, Select, Dialog, etc.)

## API

### Server-side (`api-helpers.js`)
Usado em `+page.server.js` (SvelteKit actions). Extrai erros DRF campo-a-campo.

### Client-side (`api.js`)
Usado em componentes para chamadas diretas.

### hooks.server.js
- Extrai JWT do cookie
- Decodifica claims: `user_id`, `org_id`, `is_superuser`
- Popula `event.locals.user` para uso em `+page.server.js`

### Error Handling
```javascript
// +page.server.js
catch (err) {
  return fail(400, { error: err.message || 'Falha na operação' });
}

// +page.svelte
toast.error(result.data?.error || 'Operação falhou');
```

## Padrões Svelte 5

- Usar runes: `$state`, `$derived`, `$effect`, `$props`
- **NÃO** usar `svelte:component` (deprecated) — usar `{@render}` ou renderização condicional
- Componentes dinâmicos: `{#if condition}<Component />{/if}`

## Constantes

- `src/lib/constants/filters.js` — Moedas (21 + crypto), status, fontes, indústrias
- `src/lib/constants/countries.js` — 261 países traduzidos para português
- `src/lib/constants/lead-choices.js` — Choices específicos de leads

## Desenvolvimento

```bash
pnpm install
pnpm run dev       # Dev server
pnpm run check     # Type checking
pnpm run lint      # Linting
pnpm run build     # Build production
```

## Variáveis de Ambiente

| Variável | Descrição |
|----------|-----------|
| `PUBLIC_DJANGO_API_URL` | URL da API backend |
| `NODE_ENV` | `production` ou `development` |
| `ORIGIN` | Origem para CORS |

## Licença

Software privado.
