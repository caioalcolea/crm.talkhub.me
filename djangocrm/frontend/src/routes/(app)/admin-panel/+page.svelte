<script>
  import PageHeader from '$lib/components/layout/PageHeader.svelte';
  import { Building, Users, Activity, Clock, Search } from '@lucide/svelte';
  import * as Card from '$lib/components/ui/card/index.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import * as Table from '$lib/components/ui/table/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';

  let { data } = $props();

  let activeTab = $state('orgs');
  let orgSearch = $state('');
  let userSearch = $state('');

  let filteredOrgs = $derived(
    data.orgs.filter((o) =>
      o.name.toLowerCase().includes(orgSearch.toLowerCase())
    )
  );

  let filteredUsers = $derived(
    data.users.filter((u) =>
      u.email.toLowerCase().includes(userSearch.toLowerCase())
    )
  );

  const formatDate = (iso) => {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };
</script>

<svelte:head>
  <title>Administração | TalkHub CRM</title>
</svelte:head>

<div class="flex flex-col">
  <PageHeader title="Painel de Administração" subtitle="Gerenciamento da plataforma TalkHub CRM" />

  <div class="space-y-6 px-6 py-6 md:px-8">
  <!-- KPI Cards -->
  <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
    <Card.Root>
      <Card.Content class="flex items-center gap-4 p-5">
        <div class="flex size-10 shrink-0 items-center justify-center rounded-lg bg-blue-500/10">
          <Building class="size-5 text-blue-500" />
        </div>
        <div>
          <p class="text-sm text-muted-foreground">Organizações</p>
          <p class="text-2xl font-bold">{data.dashboard.total_orgs ?? 0}</p>
        </div>
      </Card.Content>
    </Card.Root>

    <Card.Root>
      <Card.Content class="flex items-center gap-4 p-5">
        <div class="flex size-10 shrink-0 items-center justify-center rounded-lg bg-green-500/10">
          <Users class="size-5 text-green-500" />
        </div>
        <div>
          <p class="text-sm text-muted-foreground">Usuários</p>
          <p class="text-2xl font-bold">{data.dashboard.total_users ?? 0}</p>
        </div>
      </Card.Content>
    </Card.Root>

    <Card.Root>
      <Card.Content class="flex items-center gap-4 p-5">
        <div class="flex size-10 shrink-0 items-center justify-center rounded-lg bg-purple-500/10">
          <Activity class="size-5 text-purple-500" />
        </div>
        <div>
          <p class="text-sm text-muted-foreground">Novas Orgs (mês)</p>
          <p class="text-2xl font-bold">{data.dashboard.new_orgs_this_month ?? 0}</p>
        </div>
      </Card.Content>
    </Card.Root>

    <Card.Root>
      <Card.Content class="flex items-center gap-4 p-5">
        <div class="flex size-10 shrink-0 items-center justify-center rounded-lg bg-orange-500/10">
          <Clock class="size-5 text-orange-500" />
        </div>
        <div>
          <p class="text-sm text-muted-foreground">Novos Usuários (mês)</p>
          <p class="text-2xl font-bold">{data.dashboard.new_users_this_month ?? 0}</p>
        </div>
      </Card.Content>
    </Card.Root>
  </div>

  <!-- Tab Navigation -->
  <div class="flex gap-2 border-b">
    <button
      class="px-4 py-2 text-sm font-medium transition-colors {activeTab === 'orgs'
        ? 'border-b-2 border-primary text-primary'
        : 'text-muted-foreground hover:text-foreground'}"
      onclick={() => (activeTab = 'orgs')}
    >
      <span class="flex items-center gap-2">
        <Building class="size-4" />
        Organizações ({data.orgs.length})
      </span>
    </button>
    <button
      class="px-4 py-2 text-sm font-medium transition-colors {activeTab === 'users'
        ? 'border-b-2 border-primary text-primary'
        : 'text-muted-foreground hover:text-foreground'}"
      onclick={() => (activeTab = 'users')}
    >
      <span class="flex items-center gap-2">
        <Users class="size-4" />
        Usuários ({data.users.length})
      </span>
    </button>
  </div>

  <!-- Orgs Tab -->
  {#if activeTab === 'orgs'}
    <Card.Root>
      <Card.Header class="pb-3">
        <div class="flex items-center justify-between">
          <Card.Title>Organizações</Card.Title>
          <div class="relative w-64">
            <Search class="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Buscar organização..."
              class="pl-9"
              bind:value={orgSearch}
            />
          </div>
        </div>
      </Card.Header>
      <Card.Content>
        <Table.Root>
          <Table.Header>
            <Table.Row>
              <Table.Head>Nome</Table.Head>
              <Table.Head>Usuários</Table.Head>
              <Table.Head>Moeda</Table.Head>
              <Table.Head>Criada em</Table.Head>
              <Table.Head>Status</Table.Head>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {#each filteredOrgs as org}
              <Table.Row>
                <Table.Cell class="font-medium">{org.name}</Table.Cell>
                <Table.Cell>{org.user_count}</Table.Cell>
                <Table.Cell>{org.default_currency || 'BRL'}</Table.Cell>
                <Table.Cell>{formatDate(org.created_at)}</Table.Cell>
                <Table.Cell>
                  <Badge variant={org.is_active ? 'default' : 'destructive'}>
                    {org.is_active ? 'Ativa' : 'Inativa'}
                  </Badge>
                </Table.Cell>
              </Table.Row>
            {/each}
            {#if filteredOrgs.length === 0}
              <Table.Row>
                <Table.Cell colspan={5} class="text-center text-muted-foreground py-8">
                  Nenhuma organização encontrada
                </Table.Cell>
              </Table.Row>
            {/if}
          </Table.Body>
        </Table.Root>
      </Card.Content>
    </Card.Root>
  {/if}

  <!-- Users Tab -->
  {#if activeTab === 'users'}
    <Card.Root>
      <Card.Header class="pb-3">
        <div class="flex items-center justify-between">
          <Card.Title>Usuários</Card.Title>
          <div class="relative w-64">
            <Search class="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Buscar por email..."
              class="pl-9"
              bind:value={userSearch}
            />
          </div>
        </div>
      </Card.Header>
      <Card.Content>
        <Table.Root>
          <Table.Header>
            <Table.Row>
              <Table.Head>Email</Table.Head>
              <Table.Head>Organizações</Table.Head>
              <Table.Head>Último Login</Table.Head>
              <Table.Head>Cadastro</Table.Head>
              <Table.Head>Tipo</Table.Head>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {#each filteredUsers as user}
              <Table.Row>
                <Table.Cell class="font-medium">{user.email}</Table.Cell>
                <Table.Cell>
                  <div class="flex flex-wrap gap-1">
                    {#each user.orgs as org}
                      <Badge variant="outline" class="text-xs">
                        {org.name} ({org.role})
                      </Badge>
                    {/each}
                    {#if user.orgs.length === 0}
                      <span class="text-muted-foreground text-xs">Sem organização</span>
                    {/if}
                  </div>
                </Table.Cell>
                <Table.Cell>{formatDate(user.last_login)}</Table.Cell>
                <Table.Cell>{formatDate(user.date_joined)}</Table.Cell>
                <Table.Cell>
                  {#if user.is_superuser}
                    <Badge variant="default" class="bg-red-500">Super Admin</Badge>
                  {:else}
                    <Badge variant="secondary">Usuário</Badge>
                  {/if}
                </Table.Cell>
              </Table.Row>
            {/each}
            {#if filteredUsers.length === 0}
              <Table.Row>
                <Table.Cell colspan={5} class="text-center text-muted-foreground py-8">
                  Nenhum usuário encontrado
                </Table.Cell>
              </Table.Row>
            {/if}
          </Table.Body>
        </Table.Root>
      </Card.Content>
    </Card.Root>
  {/if}
  </div>
</div>
