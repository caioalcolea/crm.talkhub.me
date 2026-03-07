<script>
  import { cn } from '$lib/utils.js';

  /**
   * @type {{
   *   ref?: HTMLButtonElement | null,
   *   checked?: boolean,
   *   disabled?: boolean,
   *   name?: string,
   *   id?: string,
   *   class?: string,
   *   onCheckedChange?: (checked: boolean) => void,
   *   [key: string]: any
   * }}
   */
  let {
    ref = $bindable(null),
    checked = $bindable(false),
    disabled = false,
    name,
    id,
    class: className,
    onCheckedChange,
    ...restProps
  } = $props();

  function toggle() {
    if (disabled) return;
    checked = !checked;
    onCheckedChange?.(checked);
  }

  function onkeydown(e) {
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      toggle();
    }
  }
</script>

{#if name}
  <input type="hidden" {name} value={checked ? 'on' : ''} />
{/if}
<button
  bind:this={ref}
  type="button"
  role="switch"
  aria-checked={checked}
  {disabled}
  {id}
  data-state={checked ? 'checked' : 'unchecked'}
  class={cn(
    'peer inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent shadow-xs transition-colors',
    'focus-visible:ring-ring/50 focus-visible:outline-none focus-visible:ring-[3px]',
    'disabled:cursor-not-allowed disabled:opacity-50',
    checked ? 'bg-primary' : 'bg-input',
    className
  )}
  onclick={toggle}
  {onkeydown}
  {...restProps}
>
  <span
    data-state={checked ? 'checked' : 'unchecked'}
    class={cn(
      'bg-background pointer-events-none block size-4 rounded-full shadow-lg ring-0 transition-transform',
      checked ? 'translate-x-4' : 'translate-x-0'
    )}
  ></span>
</button>
