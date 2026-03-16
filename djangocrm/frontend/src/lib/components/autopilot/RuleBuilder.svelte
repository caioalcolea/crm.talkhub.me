<script>
  import RoutineBuilder from './RoutineBuilder.svelte';
  import LogicRuleBuilder from './LogicRuleBuilder.svelte';
  import SocialBuilder from './SocialBuilder.svelte';

  let { automationType = '', config = $bindable({}) } = $props();

  const DEFAULTS = {
    routine: { schedule_cron: 60, action_type: 'send_notification', action_params: { message: '' } },
    logic_rule: { trigger_event: '', conditions: [], actions: [{ action_type: '', action_params: {} }] },
    social: { channel_type: 'whatsapp', social_event: '', actions: [{ action_type: '', action_params: {} }] },
  };

  let lastType = $state(automationType);

  $effect(() => {
    if (automationType && automationType !== lastType) {
      lastType = automationType;
      if (!config || Object.keys(config).length === 0) {
        config = { ...(DEFAULTS[automationType] || {}) };
      }
    }
  });

  // Initialize defaults if config is empty on first render
  if (automationType && (!config || Object.keys(config).length === 0)) {
    config = { ...(DEFAULTS[automationType] || {}) };
  }
</script>

<input type="hidden" name="config_json" value={JSON.stringify(config)} />

<div class="space-y-4 rounded-md border bg-muted/20 p-4">
  {#if automationType === 'routine'}
    <RoutineBuilder bind:config />
  {:else if automationType === 'logic_rule'}
    <LogicRuleBuilder bind:config />
  {:else if automationType === 'social'}
    <SocialBuilder bind:config />
  {:else}
    <p class="text-muted-foreground text-sm">Selecione o tipo de automação para configurar.</p>
  {/if}
</div>
