<script>
  import { Video } from '@lucide/svelte';
  import { Badge } from '$lib/components/ui/badge/index.js';

  let { data } = $props();

  let room = $derived(data.room);
  let guest = $derived(data.guest);
  let coworkToken = $derived(data.coworkToken);
</script>

<svelte:head>
  <title>{room?.name || 'Sala Cowork'} — TalkHub</title>
</svelte:head>

<div class="flex h-screen w-screen flex-col bg-background">
  <!-- Minimal header -->
  <header class="flex items-center justify-between border-b px-4 py-2">
    <div class="flex items-center gap-3">
      <Badge variant="default" class="gap-1">
        <Video class="size-3" />
        Cowork
      </Badge>
      <span class="font-medium text-sm">{room?.name}</span>
    </div>
    <div class="flex items-center gap-2 text-sm text-muted-foreground">
      <span>Visitante: <strong>{guest?.name}</strong></span>
    </div>
  </header>

  <!-- Cowork area (iframe placeholder) -->
  <main class="flex-1 flex items-center justify-center bg-muted/30">
    <div class="text-center space-y-4 p-8">
      <Video class="mx-auto size-20 text-muted-foreground" strokeWidth={1} />
      <h2 class="text-xl font-semibold">Sala: {room?.name}</h2>
      <p class="text-muted-foreground max-w-md">
        O cowork-app será carregado aqui quando o serviço Socket.io estiver configurado.
        Você entrou como visitante "{guest?.name}".
      </p>
      <Badge variant="outline" class="font-mono text-xs">
        Mapa: {room?.map_id}
      </Badge>
    </div>
  </main>
</div>
