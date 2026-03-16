<script>
  import { Button } from '$lib/components/ui/button/index.js';
  import * as Popover from '$lib/components/ui/popover/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Code } from '@lucide/svelte';

  let { moduleKey = '', onInsert = () => {} } = $props();

  const TEMPLATE_VARIABLES = {
    financeiro: ['account_name', 'contact_name', 'invoice_number', 'amount', 'currency', 'due_date', 'days_until_due', 'days_overdue', 'payment_link', 'parcela_number', 'lancamento_descricao'],
    leads: ['lead_name', 'lead_status', 'lead_source', 'assigned_to', 'lead_email', 'lead_phone'],
    cases: ['case_name', 'case_status', 'case_priority', 'assigned_to', 'sla_deadline'],
    tasks: ['task_title', 'task_status', 'task_priority', 'assigned_to', 'due_date'],
    invoices: ['invoice_number', 'invoice_status', 'amount', 'currency', 'due_date', 'contact_name', 'account_name'],
    opportunity: ['opportunity_name', 'opportunity_stage', 'amount', 'currency', 'assigned_to', 'close_date'],
    system: ['org_name', 'current_date', 'channel_name'],
    campaigns: ['contact.first_name', 'contact.last_name', 'contact.email', 'contact.organization'],
  };

  const MODULE_LABELS = {
    financeiro: 'Financeiro',
    leads: 'Leads',
    cases: 'Chamados',
    tasks: 'Tarefas',
    invoices: 'Faturas',
    opportunity: 'Negócios',
    system: 'Sistema',
    campaigns: 'Campanhas',
  };

  let open = $state(false);

  let groups = $derived.by(() => {
    if (moduleKey && TEMPLATE_VARIABLES[moduleKey]) {
      return { [moduleKey]: TEMPLATE_VARIABLES[moduleKey] };
    }
    return TEMPLATE_VARIABLES;
  });

  function handleInsert(varName) {
    onInsert(`{{${varName}}}`);
    open = false;
  }
</script>

<Popover.Root bind:open>
  <Popover.Trigger>
    {#snippet child({ props })}
      <Button {...props} type="button" variant="ghost" size="sm" class="h-7 gap-1 px-2 text-xs">
        <Code class="size-3" />
        Variáveis
      </Button>
    {/snippet}
  </Popover.Trigger>
  <Popover.Content class="w-72 max-h-64 overflow-y-auto" align="start">
    <div class="space-y-3">
      {#each Object.entries(groups) as [group, vars]}
        <div>
          <p class="text-muted-foreground mb-1.5 text-xs font-medium">{MODULE_LABELS[group] || group}</p>
          <div class="flex flex-wrap gap-1">
            {#each vars as v}
              <button
                type="button"
                class="bg-muted hover:bg-primary hover:text-primary-foreground rounded px-1.5 py-0.5 text-xs font-mono transition-colors cursor-pointer"
                onclick={() => handleInsert(v)}
              >
                {`{{${v}}}`}
              </button>
            {/each}
          </div>
        </div>
      {/each}
    </div>
  </Popover.Content>
</Popover.Root>
