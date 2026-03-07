<script>
  import { cn } from '$lib/utils.js';

  let { status = 'ABERTO', class: className } = $props();

  const statusConfig = {
    ABERTO: { label: 'Aberto', class: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400' },
    PAGO: { label: 'Pago', class: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400' },
    CANCELADO: { label: 'Cancelado', class: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' },
    PAGAR: { label: 'Pagar', class: 'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400' },
    RECEBER: { label: 'Receber', class: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400' }
  };

  const config = $derived(statusConfig[status] || { label: status, class: 'bg-gray-100 text-gray-800' });
</script>

<span class={cn('inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', config.class, className)}>
  {config.label}
</span>
