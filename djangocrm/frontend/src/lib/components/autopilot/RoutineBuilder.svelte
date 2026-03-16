<script>
  import { Label } from '$lib/components/ui/label/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import ActionParamsForm from './ActionParamsForm.svelte';

  let { config = $bindable({}) } = $props();

  const ACTION_TYPES = [
    { value: 'send_notification', label: 'Enviar Notificação' },
    { value: 'send_email', label: 'Enviar Email' },
    { value: 'create_task', label: 'Criar Tarefa' },
    { value: 'update_field', label: 'Atualizar Campo' },
  ];

  const DAYS = [
    { value: 1, label: 'Seg' },
    { value: 2, label: 'Ter' },
    { value: 3, label: 'Qua' },
    { value: 4, label: 'Qui' },
    { value: 5, label: 'Sex' },
    { value: 6, label: 'Sáb' },
    { value: 0, label: 'Dom' },
  ];

  let scheduleMode = $state(typeof config.schedule_cron === 'string' ? 'cron' : 'simple');
  let simpleMinutes = $state(typeof config.schedule_cron === 'number' ? config.schedule_cron : 60);
  let cronHour = $state(9);
  let cronMinute = $state(0);
  let cronDays = $state([1, 2, 3, 4, 5]);

  // Parse existing cron if present
  if (typeof config.schedule_cron === 'string') {
    try {
      const parts = config.schedule_cron.split(' ');
      cronMinute = parseInt(parts[0]) || 0;
      cronHour = parseInt(parts[1]) || 9;
      if (parts[4] && parts[4] !== '*') {
        cronDays = parts[4].split(',').map(Number);
      }
    } catch { /* use defaults */ }
  }

  function updateSchedule() {
    if (scheduleMode === 'simple') {
      config = { ...config, schedule_cron: simpleMinutes };
    } else {
      const dayStr = cronDays.length === 7 ? '*' : cronDays.join(',');
      config = { ...config, schedule_cron: `${cronMinute} ${cronHour} * * ${dayStr}` };
    }
  }

  function toggleDay(d) {
    if (cronDays.includes(d)) {
      cronDays = cronDays.filter(x => x !== d);
    } else {
      cronDays = [...cronDays, d].sort();
    }
    updateSchedule();
  }

  function setActionType(type) {
    config = { ...config, action_type: type, action_params: {} };
  }

  $effect(() => { updateSchedule(); });
</script>

<div class="space-y-4">
  <!-- Schedule -->
  <div class="space-y-3">
    <Label>Agendamento</Label>
    <div class="flex gap-1">
      <Button
        type="button"
        variant={scheduleMode === 'simple' ? 'default' : 'outline'}
        size="sm"
        onclick={() => { scheduleMode = 'simple'; updateSchedule(); }}
      >Simples</Button>
      <Button
        type="button"
        variant={scheduleMode === 'cron' ? 'default' : 'outline'}
        size="sm"
        onclick={() => { scheduleMode = 'cron'; updateSchedule(); }}
      >Cron</Button>
    </div>

    {#if scheduleMode === 'simple'}
      <div class="flex items-center gap-2">
        <span class="text-sm">Executar a cada</span>
        <Input
          type="number"
          min="1"
          class="w-24"
          value={simpleMinutes}
          oninput={(e) => { simpleMinutes = parseInt(e.target.value) || 1; updateSchedule(); }}
        />
        <span class="text-sm">minutos</span>
      </div>
    {:else}
      <div class="space-y-3">
        <div class="flex items-center gap-3">
          <div class="flex items-center gap-2">
            <span class="text-sm">Hora:</span>
            <select
              value={cronHour}
              onchange={(e) => { cronHour = parseInt(e.target.value); updateSchedule(); }}
              class="border-input bg-background flex h-9 rounded-md border px-2 py-1 text-sm"
            >
              {#each Array.from({ length: 24 }, (_, i) => i) as h}
                <option value={h}>{String(h).padStart(2, '0')}</option>
              {/each}
            </select>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-sm">Min:</span>
            <select
              value={cronMinute}
              onchange={(e) => { cronMinute = parseInt(e.target.value); updateSchedule(); }}
              class="border-input bg-background flex h-9 rounded-md border px-2 py-1 text-sm"
            >
              {#each [0, 15, 30, 45] as m}
                <option value={m}>{String(m).padStart(2, '0')}</option>
              {/each}
            </select>
          </div>
        </div>

        <div class="flex flex-wrap gap-1">
          {#each DAYS as day}
            <Button
              type="button"
              variant={cronDays.includes(day.value) ? 'default' : 'outline'}
              size="sm"
              class="h-8 w-10 text-xs"
              onclick={() => toggleDay(day.value)}
            >{day.label}</Button>
          {/each}
        </div>
      </div>
    {/if}
  </div>

  <!-- Action -->
  <div class="space-y-3">
    <Label>Ação</Label>
    <select
      value={config.action_type || ''}
      onchange={(e) => setActionType(e.target.value)}
      class="border-input bg-background flex h-10 w-full rounded-md border px-3 py-2 text-sm"
    >
      <option value="" disabled>Selecione a ação...</option>
      {#each ACTION_TYPES as at}
        <option value={at.value}>{at.label}</option>
      {/each}
    </select>

    {#if config.action_type}
      <ActionParamsForm
        actionType={config.action_type}
        params={config.action_params || {}}
        onchange={(p) => { config = { ...config, action_params: p }; }}
      />
    {/if}
  </div>
</div>
