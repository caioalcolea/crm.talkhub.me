<script>
  import * as Card from '$lib/components/ui/card/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { PageHeader } from '$lib/components/layout';
  import { Cloud, Construction } from '@lucide/svelte';
</script>

<svelte:head>
  <title>Integração Salesforce - TalkHub CRM</title>
</svelte:head>

<PageHeader title="Integração Salesforce" subtitle="Conecte e importe dados do Salesforce" />

<div class="mx-auto max-w-3xl space-y-6 p-6 md:p-8">
  <Card.Root>
    <Card.Header class="text-center">
      <div
        class="mx-auto mb-4 flex size-16 items-center justify-center rounded-full bg-amber-100 dark:bg-amber-950"
      >
        <Construction class="size-8 text-amber-600 dark:text-amber-400" />
      </div>
      <Card.Title class="text-xl">Em breve</Card.Title>
      <Card.Description class="mx-auto max-w-md">
        A integração com Salesforce está em desenvolvimento e estará disponível em uma próxima atualização.
      </Card.Description>
    </Card.Header>
    <Card.Content>
      <div class="bg-muted/50 rounded-lg p-4">
        <h4 class="text-foreground mb-3 text-sm font-medium">O que será possível:</h4>
        <ul class="text-muted-foreground space-y-2 text-sm">
          <li class="flex items-start gap-2">
            <span class="mt-1.5 size-1.5 shrink-0 rounded-full bg-blue-500"></span>
            <span>Importar <strong class="text-foreground">Contas</strong>, <strong class="text-foreground">Contatos</strong> e <strong class="text-foreground">Oportunidades</strong></span>
          </li>
          <li class="flex items-start gap-2">
            <span class="mt-1.5 size-1.5 shrink-0 rounded-full bg-blue-500"></span>
            <span>Sincronizar <strong class="text-foreground">Produtos</strong> e <strong class="text-foreground">Pedidos</strong></span>
          </li>
          <li class="flex items-start gap-2">
            <span class="mt-1.5 size-1.5 shrink-0 rounded-full bg-blue-500"></span>
            <span>Migração completa do seu pipeline de vendas</span>
          </li>
        </ul>
      </div>
    </Card.Content>
  </Card.Root>
</div>
