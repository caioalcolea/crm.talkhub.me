import { apiRequest } from '$lib/api-helpers.js';
import { fail } from '@sveltejs/kit';

/** @type {import('./$types').PageServerLoad} */
export async function load({ params, cookies }) {
  const { slug } = params;

  /** @type {any} */
  let integration = null;
  /** @type {string|null} */
  let loadError = null;
  /** @type {any} */
  let health = null;
  /** @type {any[]} */
  let fieldMappings = [];

  try {
    integration = await apiRequest(`/integrations/${slug}/`, {}, { cookies });
  } catch (err) {
    loadError = err?.message || 'Falha ao carregar integração.';
  }

  try {
    health = await apiRequest(`/integrations/${slug}/health/`, {}, { cookies });
  } catch {
    health = { status: 'unknown' };
  }

  try {
    const mappingsRes = await apiRequest(
      `/integrations/field-mappings/?connector=${slug}`,
      {},
      { cookies }
    );
    fieldMappings = mappingsRes.results || mappingsRes || [];
  } catch {
    fieldMappings = [];
  }

  // Load DLQ items for Chatwoot
  /** @type {any[]} */
  let dlqItems = [];
  if (slug === 'chatwoot') {
    try {
      const dlqRes = await apiRequest('/integrations/webhooks/dlq/', {}, { cookies });
      dlqItems = Array.isArray(dlqRes) ? dlqRes : (dlqRes?.results || []);
    } catch {
      dlqItems = [];
    }
  }

  return { integration, health, fieldMappings, dlqItems, slug, loadError };
}

/** @type {import('./$types').Actions} */
export const actions = {
  connect: async ({ params, request, cookies }) => {
    const formData = await request.formData();
    let config = Object.fromEntries(formData.entries());

    // Remove non-config fields that may leak from the form
    delete config.conflict_strategy;

    // If no config fields were submitted (bare connect button),
    // fetch the existing saved config from the integration.
    const hasConfigFields = Object.keys(config).length > 0;
    if (!hasConfigFields) {
      try {
        const integration = await apiRequest(
          `/integrations/${params.slug}/`,
          {},
          { cookies }
        );
        config = integration?.config || {};
      } catch {
        return fail(400, { error: 'Configure as credenciais antes de conectar.' });
      }

      // If still empty after fetching, block the connect
      if (!config || Object.keys(config).length === 0) {
        return fail(400, { error: 'Configure as credenciais antes de conectar.' });
      }
    }

    try {
      await apiRequest(
        `/integrations/${params.slug}/connect/`,
        { method: 'POST', body: { config } },
        { cookies }
      );
      return { connected: true };
    } catch (err) {
      return fail(400, { error: err?.message || 'Falha ao conectar integração.' });
    }
  },

  disconnect: async ({ params, cookies }) => {
    try {
      await apiRequest(
        `/integrations/${params.slug}/disconnect/`,
        { method: 'POST' },
        { cookies }
      );
      return { disconnected: true };
    } catch (err) {
      return fail(400, { error: err?.message || 'Falha ao desconectar integração.' });
    }
  },

  testConnection: async ({ params, cookies }) => {
    try {
      const result = await apiRequest(
        `/integrations/${params.slug}/health/`,
        {},
        { cookies }
      );
      return { testResult: result };
    } catch (err) {
      return fail(400, { testError: err?.message || 'Falha ao testar conexão.' });
    }
  },

  syncNow: async ({ params, cookies }) => {
    try {
      await apiRequest(
        `/integrations/${params.slug}/sync/`,
        { method: 'POST', body: { sync_type: 'all' } },
        { cookies }
      );
      return { syncStarted: true };
    } catch (err) {
      return fail(400, { syncError: err?.message || 'Falha ao iniciar sincronização.' });
    }
  },

  saveConfig: async ({ params, request, cookies }) => {
    const formData = await request.formData();
    const config_json = Object.fromEntries(formData.entries());

    // Extract conflict_strategy if present, keep it separate
    const conflict_strategy = config_json.conflict_strategy;
    delete config_json.conflict_strategy;

    /** @type {Record<string, any>} */
    const body = { config_json };
    if (conflict_strategy) {
      body.conflict_strategy = conflict_strategy;
    }

    try {
      await apiRequest(
        `/integrations/${params.slug}/`,
        { method: 'PATCH', body },
        { cookies }
      );
      return { saved: true };
    } catch (err) {
      const msg = err?.message || 'Falha ao salvar configuração.';
      return fail(400, { error: msg });
    }
  },

  saveAndConnect: async ({ params, request, cookies }) => {
    const formData = await request.formData();
    const config = Object.fromEntries(formData.entries());

    // Extract conflict_strategy like saveConfig does
    const conflict_strategy = config.conflict_strategy;
    delete config.conflict_strategy;

    // Step 1: Save config via PATCH
    /** @type {Record<string, any>} */
    const patchBody = { config_json: config };
    if (conflict_strategy) {
      patchBody.conflict_strategy = conflict_strategy;
    }

    try {
      await apiRequest(
        `/integrations/${params.slug}/`,
        { method: 'PATCH', body: patchBody },
        { cookies }
      );
    } catch (err) {
      return fail(400, { error: err?.message || 'Falha ao salvar configuração.' });
    }

    // Step 2: Connect with the config
    try {
      await apiRequest(
        `/integrations/${params.slug}/connect/`,
        { method: 'POST', body: { config } },
        { cookies }
      );
      return { connected: true };
    } catch (err) {
      return fail(400, { error: err?.message || 'Falha ao conectar integração.' });
    }
  },

  saveSyncInterval: async ({ params, request, cookies }) => {
    const formData = await request.formData();
    const raw = formData.get('sync_interval_minutes');
    const sync_interval_minutes = parseInt(/** @type {string} */ (raw), 10);

    if (isNaN(sync_interval_minutes) || sync_interval_minutes < 5 || sync_interval_minutes > 1440) {
      return fail(400, { error: 'Intervalo deve ser entre 5 e 1440 minutos.' });
    }

    try {
      await apiRequest(
        `/integrations/${params.slug}/`,
        { method: 'PATCH', body: { sync_interval_minutes } },
        { cookies }
      );
      return { syncIntervalSaved: true };
    } catch (err) {
      return fail(400, { error: err?.message || 'Falha ao salvar intervalo de sincronização.' });
    }
  },

  fetchPubsubToken: async ({ cookies }) => {
    try {
      const result = await apiRequest(
        '/integrations/chatwoot/fetch-pubsub-token/',
        { method: 'POST' },
        { cookies }
      );
      return { pubsubToken: result.pubsub_token };
    } catch (err) {
      return fail(400, { error: err?.message || 'Falha ao buscar PubSub Token.' });
    }
  },

  reprocessDlq: async ({ request, cookies }) => {
    const formData = await request.formData();
    const webhook_id = formData.get('webhook_id');
    try {
      await apiRequest(
        '/integrations/webhooks/dlq/',
        { method: 'POST', body: { webhook_id } },
        { cookies }
      );
      return { dlqReprocessed: true };
    } catch (err) {
      return fail(400, { error: err?.message || 'Falha ao reprocessar webhook.' });
    }
  },

  saveConflictStrategy: async ({ params, request, cookies }) => {
    const formData = await request.formData();
    const conflict_strategy = formData.get('conflict_strategy');

    if (!conflict_strategy) {
      return fail(400, { error: 'Selecione uma estratégia de resolução de conflitos.' });
    }

    try {
      await apiRequest(
        `/integrations/${params.slug}/`,
        { method: 'PATCH', body: { conflict_strategy } },
        { cookies }
      );
      return { saved: true };
    } catch (err) {
      return fail(400, { error: err?.message || 'Falha ao salvar estratégia de conflitos.' });
    }
  }
};
