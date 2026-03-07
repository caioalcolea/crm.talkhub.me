<script>
  import { toast } from 'svelte-sonner';
  import { apiRequest } from '$lib/api.js';
  import * as Dialog from '$lib/components/ui/dialog/index.js';
  import * as Select from '$lib/components/ui/select/index.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import { Textarea } from '$lib/components/ui/textarea/index.js';
  import {
    Headset,
    Lightbulb,
    Bug,
    Shield,
    BookOpen,
    Heart,
    Sparkles,
    Mail,
    Loader2,
    CheckCircle2
  } from '@lucide/svelte';

  // Modal open states
  let supportOpen = $state(false);
  let featureOpen = $state(false);
  let bugOpen = $state(false);
  let securityOpen = $state(false);
  let helpOpen = $state(false);

  // Form state
  let isSubmitting = $state(false);
  let submitSuccess = $state(false);
  let submitError = $state('');

  // Form data
  let formData = $state({
    name: '',
    email: '',
    subject: '',
    message: '',
    reason: '',
    metadata: {}
  });

  function resetForm() {
    formData = { name: '', email: '', subject: '', message: '', reason: '', metadata: {} };
    submitSuccess = false;
    submitError = '';
  }

  function openModal(reason) {
    resetForm();
    formData.reason = reason;
    if (reason === 'support') supportOpen = true;
    else if (reason === 'feature') featureOpen = true;
    else if (reason === 'bug') bugOpen = true;
    else if (reason === 'security') securityOpen = true;
    else if (reason === 'general') helpOpen = true;
  }

  function closeModal() {
    supportOpen = false;
    featureOpen = false;
    bugOpen = false;
    securityOpen = false;
    helpOpen = false;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    isSubmitting = true;
    submitError = '';
    try {
      await apiRequest('/public/contact/', {
        method: 'POST',
        body: {
          name: formData.name,
          email: formData.email,
          subject: formData.subject,
          message: formData.message,
          reason: formData.reason,
          metadata: Object.keys(formData.metadata).length > 0 ? formData.metadata : {}
        },
        requiresAuth: false
      });
      submitSuccess = true;
      toast.success('Mensagem enviada com sucesso!');
    } catch (err) {
      submitError = err?.message || 'Erro ao enviar. Tente novamente.';
      toast.error('Erro ao enviar formulário.');
    } finally {
      isSubmitting = false;
    }
  }

  const priorityOptions = [
    { value: 'low', label: 'Baixa' },
    { value: 'medium', label: 'Média' },
    { value: 'high', label: 'Alta' },
    { value: 'critical', label: 'Crítica' }
  ];

  const sections = [
    {
      reason: 'support',
      icon: Headset,
      title: 'Suporte Prioritário',
      description: 'Suporte técnico dedicado com tempo de resposta prioritário. Nossa equipe está pronta para resolver qualquer problema.',
      button: 'Abrir Chamado',
      iconClass: 'bg-violet-500/10 text-violet-600 dark:text-violet-400'
    },
    {
      reason: 'feature',
      icon: Lightbulb,
      title: 'Solicitações de Recursos',
      description: 'Tem uma ideia? Compartilhe suas sugestões e ajude a moldar o futuro do TalkHub CRM.',
      button: 'Enviar Sugestão',
      iconClass: 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
    },
    {
      reason: 'bug',
      icon: Bug,
      title: 'Relatórios de Bugs',
      description: 'Encontrou um problema? Seu feedback ajuda a tornar a plataforma mais estável para todos.',
      button: 'Reportar Bug',
      iconClass: 'bg-orange-500/10 text-orange-600 dark:text-orange-400'
    },
    {
      reason: 'security',
      icon: Shield,
      title: 'Segurança',
      description: 'Segurança é nossa prioridade. Reporte vulnerabilidades de forma privada e confidencial.',
      button: 'Reportar Vulnerabilidade',
      iconClass: 'bg-red-500/10 text-red-600 dark:text-red-400'
    },
    {
      reason: 'general',
      icon: BookOpen,
      title: 'Centro de Ajuda',
      description: 'Guias de integração, tutoriais e documentação para aproveitar ao máximo a plataforma.',
      button: 'Solicitar Guia',
      iconClass: 'bg-sky-500/10 text-sky-600 dark:text-sky-400'
    }
  ];
</script>

<svelte:head>
  <title>Suporte - TalkHub CRM</title>
</svelte:head>

<div class="min-h-screen bg-background">
  <!-- Hero -->
  <header class="relative overflow-hidden px-6 pt-12 pb-10">
    <div class="pointer-events-none absolute inset-0 bg-gradient-to-b from-primary/5 via-transparent to-transparent"></div>
    <div class="relative mx-auto max-w-[680px] text-center">
      <div class="mb-4 inline-flex items-center gap-2 rounded-full bg-primary/10 px-3.5 py-1.5 text-xs font-semibold uppercase tracking-wider text-primary">
        <Sparkles class="h-3.5 w-3.5" />
        <span>Ajuda e Suporte</span>
      </div>
      <h1 class="text-4xl font-extrabold tracking-tight text-foreground">
        Ajuda e <span class="text-primary">Suporte</span>
      </h1>
      <p class="mx-auto mt-3 max-w-[520px] text-base leading-relaxed text-muted-foreground">
        Estamos aqui para ajudar você a aproveitar ao máximo o TalkHub CRM.
        Nossa equipe está pronta para atender suas necessidades.
      </p>
    </div>
  </header>

  <div class="mx-auto max-w-[1000px] px-6 pb-8">
    <!-- Nossa Missão -->
    <div class="relative mb-6 flex items-start gap-5 overflow-hidden rounded-xl border border-border bg-card p-6">
      <div class="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent"></div>
      <div class="relative flex h-13 w-13 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-primary/70 text-white shadow-md">
        <Heart class="h-7 w-7" />
      </div>
      <div class="relative flex-1">
        <h2 class="mb-1.5 text-lg font-bold text-foreground">Nossa Missão</h2>
        <p class="text-[0.9375rem] leading-relaxed text-muted-foreground">
          Nosso compromisso é fornecer uma ferramenta de CRM <strong class="font-semibold text-foreground">robusta, segura e completa</strong> para
          ajudar empresas a gerenciar seus relacionamentos com clientes de forma eficiente.
          Investimos continuamente em melhorias para atender às necessidades do seu negócio.
        </p>
      </div>
    </div>

    <!-- Bento Grid -->
    <div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
      {#each sections as section}
        <article
          class="flex flex-col rounded-lg border border-border bg-card p-5 transition-colors hover:border-border/80"
          class:sm:col-span-2={section.reason === 'general'}
        >
          <div class="mb-3 flex items-center gap-3">
            <div class="flex h-10 w-10 items-center justify-center rounded-md {section.iconClass}">
              <section.icon class="h-5 w-5" />
            </div>
            {#if section.reason === 'security'}
              <span class="ml-auto rounded-full bg-red-500/10 px-2 py-0.5 text-[0.6875rem] font-bold uppercase tracking-wider text-red-600 dark:text-red-400">
                Confidencial
              </span>
            {/if}
          </div>
          <h3 class="mb-1 text-base font-bold text-foreground">{section.title}</h3>
          <p class="mb-4 flex-1 text-sm leading-relaxed text-muted-foreground">{section.description}</p>
          <div class="flex items-center gap-3">
            <Button
              variant={section.reason === 'security' ? 'destructive' : 'outline'}
              class="w-full justify-start gap-2"
              onclick={() => openModal(section.reason)}
            >
              <Mail class="h-4 w-4" />
              {section.button}
            </Button>
          </div>
          <p class="mt-2 text-xs text-muted-foreground/60">
            Contato: adm@talkhub.me
          </p>
        </article>
      {/each}
    </div>

    <!-- Footer -->
    <footer class="flex items-center justify-center gap-2 pt-4 pb-4 text-sm font-medium text-muted-foreground">
      <span>TalkHub CRM</span>
      <span class="opacity-40">•</span>
      <span>v1.0.0</span>
    </footer>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════════════
     MODALS
     ═══════════════════════════════════════════════════════════════════════ -->

<!-- Suporte Prioritário -->
<Dialog.Root bind:open={supportOpen} onOpenChange={(o) => { if (!o) resetForm(); }}>
  <Dialog.Content class="sm:max-w-[550px]">
    <Dialog.Header>
      <Dialog.Title>Abrir Chamado de Suporte</Dialog.Title>
      <Dialog.Description>
        Descreva seu problema e nossa equipe responderá o mais rápido possível.
      </Dialog.Description>
    </Dialog.Header>
    {#if submitSuccess}
      <div class="flex flex-col items-center gap-3 py-8">
        <div class="rounded-full bg-green-100 p-3 text-green-600 dark:bg-green-900/30 dark:text-green-400">
          <CheckCircle2 class="h-6 w-6" />
        </div>
        <p class="text-sm font-medium text-foreground">Chamado enviado com sucesso!</p>
        <p class="text-xs text-muted-foreground">Responderemos em breve para {formData.email}</p>
        <Button variant="outline" onclick={() => { supportOpen = false; }}>Fechar</Button>
      </div>
    {:else}
      <form onsubmit={handleSubmit} class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <Label for="s-name">Nome *</Label>
            <Input id="s-name" bind:value={formData.name} placeholder="Seu nome" required disabled={isSubmitting} />
          </div>
          <div class="space-y-2">
            <Label for="s-email">Email *</Label>
            <Input id="s-email" type="email" bind:value={formData.email} placeholder="seu@email.com" required disabled={isSubmitting} />
          </div>
        </div>
        <div class="space-y-2">
          <Label for="s-subject">Assunto *</Label>
          <Input id="s-subject" bind:value={formData.subject} placeholder="Resumo do problema" required disabled={isSubmitting} />
        </div>
        <div class="space-y-2">
          <Label for="s-desc">Descrição *</Label>
          <Textarea id="s-desc" bind:value={formData.message} placeholder="Descreva o problema em detalhes..." rows={4} required disabled={isSubmitting} />
        </div>
        <div class="space-y-2">
          <Label>Prioridade</Label>
          <Select.Root
            type="single"
            value={formData.metadata.priority || ''}
            onValueChange={(v) => (formData.metadata = { ...formData.metadata, priority: v })}
          >
            <Select.Trigger class="w-full">
              {priorityOptions.find((o) => o.value === formData.metadata.priority)?.label || 'Selecionar prioridade'}
            </Select.Trigger>
            <Select.Content>
              {#each priorityOptions as opt}
                <Select.Item value={opt.value}>{opt.label}</Select.Item>
              {/each}
            </Select.Content>
          </Select.Root>
        </div>
        {#if submitError}
          <p class="text-sm text-destructive">{submitError}</p>
        {/if}
        <Dialog.Footer class="gap-2 sm:gap-0">
          <Button type="button" variant="outline" onclick={() => { supportOpen = false; }} disabled={isSubmitting}>Cancelar</Button>
          <Button type="submit" disabled={isSubmitting}>
            {#if isSubmitting}
              <Loader2 class="mr-2 h-4 w-4 animate-spin" />
              Enviando...
            {:else}
              Enviar Chamado
            {/if}
          </Button>
        </Dialog.Footer>
      </form>
    {/if}
  </Dialog.Content>
</Dialog.Root>

<!-- Solicitações de Recursos -->
<Dialog.Root bind:open={featureOpen} onOpenChange={(o) => { if (!o) resetForm(); }}>
  <Dialog.Content class="sm:max-w-[550px]">
    <Dialog.Header>
      <Dialog.Title>Enviar Sugestão de Recurso</Dialog.Title>
      <Dialog.Description>
        Compartilhe sua ideia e ajude a moldar o futuro da plataforma.
      </Dialog.Description>
    </Dialog.Header>
    {#if submitSuccess}
      <div class="flex flex-col items-center gap-3 py-8">
        <div class="rounded-full bg-green-100 p-3 text-green-600 dark:bg-green-900/30 dark:text-green-400">
          <CheckCircle2 class="h-6 w-6" />
        </div>
        <p class="text-sm font-medium text-foreground">Sugestão enviada com sucesso!</p>
        <p class="text-xs text-muted-foreground">Agradecemos seu feedback!</p>
        <Button variant="outline" onclick={() => { featureOpen = false; }}>Fechar</Button>
      </div>
    {:else}
      <form onsubmit={handleSubmit} class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <Label for="f-name">Nome *</Label>
            <Input id="f-name" bind:value={formData.name} placeholder="Seu nome" required disabled={isSubmitting} />
          </div>
          <div class="space-y-2">
            <Label for="f-email">Email *</Label>
            <Input id="f-email" type="email" bind:value={formData.email} placeholder="seu@email.com" required disabled={isSubmitting} />
          </div>
        </div>
        <div class="space-y-2">
          <Label for="f-title">Título da Sugestão *</Label>
          <Input id="f-title" bind:value={formData.subject} placeholder="Nome do recurso sugerido" required disabled={isSubmitting} />
        </div>
        <div class="space-y-2">
          <Label for="f-desc">Descrição *</Label>
          <Textarea id="f-desc" bind:value={formData.message} placeholder="Descreva o recurso que gostaria de ver..." rows={4} required disabled={isSubmitting} />
        </div>
        <div class="space-y-2">
          <Label for="f-impact">Impacto Esperado</Label>
          <Textarea id="f-impact" bind:value={formData.metadata.impact} placeholder="Como esse recurso beneficiaria seu negócio?" rows={2} disabled={isSubmitting} />
        </div>
        <div class="space-y-2">
          <Label for="f-refs">Referências / Links</Label>
          <Input id="f-refs" bind:value={formData.metadata.references} placeholder="Links de referência (opcional)" disabled={isSubmitting} />
        </div>
        {#if submitError}
          <p class="text-sm text-destructive">{submitError}</p>
        {/if}
        <Dialog.Footer class="gap-2 sm:gap-0">
          <Button type="button" variant="outline" onclick={() => { featureOpen = false; }} disabled={isSubmitting}>Cancelar</Button>
          <Button type="submit" disabled={isSubmitting}>
            {#if isSubmitting}
              <Loader2 class="mr-2 h-4 w-4 animate-spin" />
              Enviando...
            {:else}
              Enviar Sugestão
            {/if}
          </Button>
        </Dialog.Footer>
      </form>
    {/if}
  </Dialog.Content>
</Dialog.Root>

<!-- Relatórios de Bugs -->
<Dialog.Root bind:open={bugOpen} onOpenChange={(o) => { if (!o) resetForm(); }}>
  <Dialog.Content class="sm:max-w-[550px]">
    <Dialog.Header>
      <Dialog.Title>Reportar Bug</Dialog.Title>
      <Dialog.Description>
        Ajude-nos a melhorar reportando problemas encontrados.
      </Dialog.Description>
    </Dialog.Header>
    {#if submitSuccess}
      <div class="flex flex-col items-center gap-3 py-8">
        <div class="rounded-full bg-green-100 p-3 text-green-600 dark:bg-green-900/30 dark:text-green-400">
          <CheckCircle2 class="h-6 w-6" />
        </div>
        <p class="text-sm font-medium text-foreground">Bug reportado com sucesso!</p>
        <p class="text-xs text-muted-foreground">Nossa equipe irá investigar.</p>
        <Button variant="outline" onclick={() => { bugOpen = false; }}>Fechar</Button>
      </div>
    {:else}
      <form onsubmit={handleSubmit} class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <Label for="b-name">Nome *</Label>
            <Input id="b-name" bind:value={formData.name} placeholder="Seu nome" required disabled={isSubmitting} />
          </div>
          <div class="space-y-2">
            <Label for="b-email">Email *</Label>
            <Input id="b-email" type="email" bind:value={formData.email} placeholder="seu@email.com" required disabled={isSubmitting} />
          </div>
        </div>
        <div class="space-y-2">
          <Label for="b-title">Título do Bug *</Label>
          <Input id="b-title" bind:value={formData.subject} placeholder="Resumo do problema" required disabled={isSubmitting} />
        </div>
        <div class="space-y-2">
          <Label for="b-steps">Passos para Reproduzir *</Label>
          <Textarea id="b-steps" bind:value={formData.message} placeholder="1. Vá para...&#10;2. Clique em...&#10;3. Observe que..." rows={4} required disabled={isSubmitting} />
        </div>
        <div class="space-y-2">
          <Label for="b-env">Ambiente</Label>
          <Input id="b-env" bind:value={formData.metadata.environment} placeholder="Ex: Chrome 120, Windows 11" disabled={isSubmitting} />
        </div>
        {#if submitError}
          <p class="text-sm text-destructive">{submitError}</p>
        {/if}
        <Dialog.Footer class="gap-2 sm:gap-0">
          <Button type="button" variant="outline" onclick={() => { bugOpen = false; }} disabled={isSubmitting}>Cancelar</Button>
          <Button type="submit" disabled={isSubmitting}>
            {#if isSubmitting}
              <Loader2 class="mr-2 h-4 w-4 animate-spin" />
              Enviando...
            {:else}
              Reportar Bug
            {/if}
          </Button>
        </Dialog.Footer>
      </form>
    {/if}
  </Dialog.Content>
</Dialog.Root>

<!-- Segurança -->
<Dialog.Root bind:open={securityOpen} onOpenChange={(o) => { if (!o) resetForm(); }}>
  <Dialog.Content class="sm:max-w-[550px]">
    <Dialog.Header>
      <Dialog.Title>Reportar Vulnerabilidade</Dialog.Title>
      <Dialog.Description>
        Este relatório será tratado de forma confidencial pela nossa equipe de segurança.
      </Dialog.Description>
    </Dialog.Header>
    {#if submitSuccess}
      <div class="flex flex-col items-center gap-3 py-8">
        <div class="rounded-full bg-green-100 p-3 text-green-600 dark:bg-green-900/30 dark:text-green-400">
          <CheckCircle2 class="h-6 w-6" />
        </div>
        <p class="text-sm font-medium text-foreground">Relatório enviado com sucesso!</p>
        <p class="text-xs text-muted-foreground">Trataremos com máxima prioridade e confidencialidade.</p>
        <Button variant="outline" onclick={() => { securityOpen = false; }}>Fechar</Button>
      </div>
    {:else}
      <form onsubmit={handleSubmit} class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <Label for="sec-name">Nome *</Label>
            <Input id="sec-name" bind:value={formData.name} placeholder="Seu nome" required disabled={isSubmitting} />
          </div>
          <div class="space-y-2">
            <Label for="sec-email">Email *</Label>
            <Input id="sec-email" type="email" bind:value={formData.email} placeholder="seu@email.com" required disabled={isSubmitting} />
          </div>
        </div>
        <div class="space-y-2">
          <Label for="sec-title">Título *</Label>
          <Input id="sec-title" bind:value={formData.subject} placeholder="Resumo da vulnerabilidade" required disabled={isSubmitting} />
        </div>
        <div class="space-y-2">
          <Label for="sec-desc">Descrição Técnica *</Label>
          <Textarea id="sec-desc" bind:value={formData.message} placeholder="Descreva a vulnerabilidade com detalhes técnicos..." rows={4} required disabled={isSubmitting} />
        </div>
        <div class="space-y-2">
          <Label for="sec-impact">Impacto</Label>
          <Textarea id="sec-impact" bind:value={formData.metadata.impact} placeholder="Qual o impacto potencial desta vulnerabilidade?" rows={2} disabled={isSubmitting} />
        </div>
        <div class="space-y-2">
          <Label for="sec-poc">Prova de Conceito (PoC)</Label>
          <Textarea id="sec-poc" bind:value={formData.metadata.poc} placeholder="Passos para reproduzir ou código de exemplo..." rows={3} disabled={isSubmitting} />
        </div>
        {#if submitError}
          <p class="text-sm text-destructive">{submitError}</p>
        {/if}
        <Dialog.Footer class="gap-2 sm:gap-0">
          <Button type="button" variant="outline" onclick={() => { securityOpen = false; }} disabled={isSubmitting}>Cancelar</Button>
          <Button type="submit" variant="destructive" disabled={isSubmitting}>
            {#if isSubmitting}
              <Loader2 class="mr-2 h-4 w-4 animate-spin" />
              Enviando...
            {:else}
              Reportar Vulnerabilidade
            {/if}
          </Button>
        </Dialog.Footer>
      </form>
    {/if}
  </Dialog.Content>
</Dialog.Root>

<!-- Centro de Ajuda -->
<Dialog.Root bind:open={helpOpen} onOpenChange={(o) => { if (!o) resetForm(); }}>
  <Dialog.Content class="sm:max-w-[550px]">
    <Dialog.Header>
      <Dialog.Title>Solicitar Guia</Dialog.Title>
      <Dialog.Description>
        Solicite guias de integração, tutoriais ou documentação específica.
      </Dialog.Description>
    </Dialog.Header>
    {#if submitSuccess}
      <div class="flex flex-col items-center gap-3 py-8">
        <div class="rounded-full bg-green-100 p-3 text-green-600 dark:bg-green-900/30 dark:text-green-400">
          <CheckCircle2 class="h-6 w-6" />
        </div>
        <p class="text-sm font-medium text-foreground">Solicitação enviada com sucesso!</p>
        <p class="text-xs text-muted-foreground">Entraremos em contato em breve.</p>
        <Button variant="outline" onclick={() => { helpOpen = false; }}>Fechar</Button>
      </div>
    {:else}
      <form onsubmit={handleSubmit} class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <Label for="h-name">Nome *</Label>
            <Input id="h-name" bind:value={formData.name} placeholder="Seu nome" required disabled={isSubmitting} />
          </div>
          <div class="space-y-2">
            <Label for="h-email">Email *</Label>
            <Input id="h-email" type="email" bind:value={formData.email} placeholder="seu@email.com" required disabled={isSubmitting} />
          </div>
        </div>
        <div class="space-y-2">
          <Label for="h-topic">Tópico *</Label>
          <Input id="h-topic" bind:value={formData.subject} placeholder="Ex: Integração com API, Relatórios..." required disabled={isSubmitting} />
        </div>
        <div class="space-y-2">
          <Label for="h-desc">Descrição *</Label>
          <Textarea id="h-desc" bind:value={formData.message} placeholder="Descreva o que precisa de ajuda..." rows={4} required disabled={isSubmitting} />
        </div>
        {#if submitError}
          <p class="text-sm text-destructive">{submitError}</p>
        {/if}
        <Dialog.Footer class="gap-2 sm:gap-0">
          <Button type="button" variant="outline" onclick={() => { helpOpen = false; }} disabled={isSubmitting}>Cancelar</Button>
          <Button type="submit" disabled={isSubmitting}>
            {#if isSubmitting}
              <Loader2 class="mr-2 h-4 w-4 animate-spin" />
              Enviando...
            {:else}
              Enviar Solicitação
            {/if}
          </Button>
        </Dialog.Footer>
      </form>
    {/if}
  </Dialog.Content>
</Dialog.Root>
