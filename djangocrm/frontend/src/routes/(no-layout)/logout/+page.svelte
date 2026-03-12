<script>
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';

  // Fallback: if server-side redirect didn't fire, redirect client-side
  onMount(() => {
    goto('/login', { replaceState: true });
  });
</script>

<div class="flex h-screen items-center justify-center">
  <p class="text-muted-foreground text-sm">Saindo...</p>
</div>
