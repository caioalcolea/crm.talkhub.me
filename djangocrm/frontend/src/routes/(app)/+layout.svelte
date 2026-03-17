<script>
  import '../../app.css';
  import { AppShell } from '$lib/components/layout/index.js';
  import { Toaster } from '$lib/components/ui/sonner/index.js';
  import { browser } from '$app/environment';
  import CoworkPiP from '$lib/components/cowork/CoworkPiP.svelte';
  import AssistantDrawer from '$lib/components/assistant/AssistantDrawer.svelte';
  import { initOrgSettings } from '$lib/stores/org.js';
  import { initClientAuth } from '$lib/api.js';

  let { data, children } = $props();

  // Initialize org settings store from server data
  $effect(() => {
    if (data.org_settings) {
      initOrgSettings(data.org_settings);
    }
  });

  // Bridge httpOnly JWT cookie → localStorage so client-side api.js can
  // authenticate mutations (POST/PATCH/DELETE). Re-runs after invalidateAll()
  // picks up a refreshed token from the server.
  $effect(() => {
    initClientAuth(data.accessToken);
  });

  // Populate localStorage with user data (including role) so getCurrentUser()
  // works for components that need it (e.g. CommentSection).
  $effect(() => {
    if (data.user && data.userRole) {
      try {
        localStorage.setItem('user', JSON.stringify({
          ...data.user,
          organizations: [{ role: data.userRole }]
        }));
      } catch { /* ignore in SSR / private browsing */ }
    }
  });
</script>

<AppShell user={data.user} org_name={data.org_name}>
  <main class="flex-1">
    {@render children()}
  </main>
</AppShell>

<Toaster richColors closeButton position="bottom-right" />
{#if browser}
  <CoworkPiP />
  <AssistantDrawer />
{/if}
