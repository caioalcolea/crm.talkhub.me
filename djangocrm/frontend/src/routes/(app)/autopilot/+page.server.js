import { error, fail } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals, cookies, url }) {
  const org = locals.org;
  if (!org) throw error(401, 'Contexto de organização é obrigatório');

  const tab = url.searchParams.get('tab') || 'rules';
  const showCreate = url.searchParams.get('create') === '1';

  try {
    const promises = {};

    if (tab === 'rules') {
      const type = url.searchParams.get('type') || '';
      let endpoint = '/automations/';
      if (type) endpoint += `?type=${type}`;
      promises.automations = apiRequest(endpoint, {}, cookies).catch(() => []);
    }

    if (tab === 'reminders') {
      const moduleKey = url.searchParams.get('module') || '';
      const isActive = url.searchParams.get('is_active') || '';
      const params = new URLSearchParams();
      if (moduleKey) params.append('module_key', moduleKey);
      if (isActive) params.append('is_active', isActive);
      const qs = params.toString();
      promises.reminders = apiRequest(`/assistant/reminder-policies/${qs ? '?' + qs : ''}`, {}, cookies).catch(() => []);
    }

    if (tab === 'campaigns') {
      const campaignId = url.searchParams.get('campaign_id') || '';

      if (campaignId) {
        // Load campaign detail for drill-down view
        promises.campaignDetail = apiRequest(`/campaigns/${campaignId}/`, {}, cookies).catch(() => null);
      }

      // Always load campaign list
      const type = url.searchParams.get('type') || '';
      const status = url.searchParams.get('status') || '';
      const params = new URLSearchParams();
      if (type) params.append('type', type);
      if (status) params.append('status', status);
      const qs = params.toString();
      promises.campaigns = apiRequest(`/campaigns/${qs ? '?' + qs : ''}`, {}, cookies).catch(() => []);
    }

    if (tab === 'runs') {
      const source = url.searchParams.get('source') || '';
      const campaignId = url.searchParams.get('campaign_id') || '';
      const params = new URLSearchParams({ limit: '50' });
      if (source) params.append('source', source);
      if (campaignId) params.append('campaign_id', campaignId);
      promises.runs = apiRequest(`/assistant/runs/?${params.toString()}`, {}, cookies).catch(() => []);
    }

    if (tab === 'templates') {
      promises.templates = apiRequest('/assistant/templates/', {}, cookies).catch(() => []);
    }

    // Resolve all promises
    const keys = Object.keys(promises);
    const values = await Promise.all(Object.values(promises));
    const results = {};
    keys.forEach((k, i) => { results[k] = values[i]; });

    return {
      tab,
      showCreate,
      filters: {
        type: url.searchParams.get('type') || '',
        status: url.searchParams.get('status') || '',
        module: url.searchParams.get('module') || '',
        is_active: url.searchParams.get('is_active') || '',
        source: url.searchParams.get('source') || '',
        campaign_id: url.searchParams.get('campaign_id') || '',
      },
      ...results,
    };
  } catch (err) {
    console.error('Autopilot load error:', err);
    return { tab, showCreate: false, filters: {}, automations: [], reminders: [], campaigns: [], runs: { results: [], count: 0 }, templates: [] };
  }
}

/** @type {import('./$types').Actions} */
export const actions = {
  toggleAutomation: async ({ request, cookies }) => {
    const formData = await request.formData();
    const id = formData.get('id');
    const isActive = formData.get('is_active') === 'true';
    try {
      await apiRequest(`/automations/${id}/`, { method: 'PATCH', body: { is_active: !isActive } }, cookies);
      return { success: true, toast: isActive ? 'Automação desativada.' : 'Automação ativada.' };
    } catch (err) {
      return fail(400, { error: 'Erro ao alterar status.' });
    }
  },

  deleteAutomation: async ({ request, cookies }) => {
    const formData = await request.formData();
    const id = formData.get('id');
    try {
      await apiRequest(`/automations/${id}/`, { method: 'DELETE' }, cookies);
      return { success: true, toast: 'Automação excluída.' };
    } catch (err) {
      return fail(400, { error: 'Erro ao excluir.' });
    }
  },

  createAutomation: async ({ request, cookies }) => {
    const formData = await request.formData();
    const name = formData.get('name')?.toString().trim();
    const automationType = formData.get('automation_type')?.toString();
    const configJsonRaw = formData.get('config_json')?.toString();

    if (!name) return fail(400, { error: 'Nome é obrigatório.' });
    if (!automationType) return fail(400, { error: 'Tipo de automação é obrigatório.' });

    let configJson = {};
    if (configJsonRaw) {
      try {
        configJson = JSON.parse(configJsonRaw);
      } catch {
        return fail(400, { error: 'Configuração JSON inválida.' });
      }
    }

    try {
      await apiRequest('/automations/', {
        method: 'POST',
        body: { name, automation_type: automationType, config_json: configJson, is_active: false }
      }, cookies);
      return { success: true, toast: 'Automação criada com sucesso.' };
    } catch (err) {
      const message = err?.body?.config_json || err?.body?.detail || 'Erro ao criar automação.';
      return fail(400, { error: typeof message === 'string' ? message : JSON.stringify(message) });
    }
  },

  createCampaign: async ({ request, cookies }) => {
    const formData = await request.formData();
    const name = formData.get('name')?.toString().trim();
    const campaignType = formData.get('campaign_type')?.toString();
    const subject = formData.get('subject')?.toString().trim() || null;
    const bodyTemplate = formData.get('body_template')?.toString() || '';
    const stepsRaw = formData.get('steps')?.toString();

    if (!name) return fail(400, { error: 'Nome é obrigatório.' });
    if (!campaignType) return fail(400, { error: 'Tipo de campanha é obrigatório.' });

    try {
      const campaign = await apiRequest('/campaigns/', {
        method: 'POST',
        body: { name, campaign_type: campaignType, subject, body_template: bodyTemplate, status: 'draft' }
      }, cookies);

      // Create steps for nurture_sequence
      if (campaignType === 'nurture_sequence' && stepsRaw) {
        try {
          const steps = JSON.parse(stepsRaw);
          for (const step of steps) {
            await apiRequest(`/campaigns/${campaign.id}/steps/`, {
              method: 'POST',
              body: {
                step_order: step.step_order,
                channel: step.channel,
                subject: step.subject || null,
                body_template: step.body_template || '',
                delay_hours: step.delay_hours || 0
              }
            }, cookies);
          }
        } catch (stepErr) {
          console.error('Error creating steps:', stepErr);
        }
      }

      return { success: true, toast: 'Campanha criada com sucesso.' };
    } catch (err) {
      const message = err?.body?.detail || err?.message || 'Erro ao criar campanha.';
      return fail(400, { error: typeof message === 'string' ? message : JSON.stringify(message) });
    }
  },

  deleteCampaign: async ({ request, cookies }) => {
    const formData = await request.formData();
    const id = formData.get('id');
    try {
      await apiRequest(`/campaigns/${id}/`, { method: 'DELETE' }, cookies);
      return { success: true, toast: 'Campanha excluída.' };
    } catch (err) {
      return fail(400, { error: 'Erro ao excluir.' });
    }
  },

  pauseResumeCampaign: async ({ request, cookies }) => {
    const formData = await request.formData();
    const id = formData.get('id');
    const action = formData.get('action');
    try {
      await apiRequest(`/campaigns/${id}/pause-resume/`, { method: 'POST', body: { action } }, cookies);
      return { success: true, toast: action === 'pause' ? 'Campanha pausada.' : 'Campanha retomada.' };
    } catch (err) {
      return fail(400, { error: 'Erro ao alterar status.' });
    }
  },

  previewAudience: async ({ request, cookies }) => {
    const formData = await request.formData();
    const campaignId = formData.get('campaign_id')?.toString();
    const filterCriteriaRaw = formData.get('filter_criteria')?.toString() || '{}';

    let filterCriteria = {};
    try {
      filterCriteria = JSON.parse(filterCriteriaRaw);
    } catch {
      return fail(400, { error: 'Critérios de filtro inválidos.' });
    }

    try {
      const result = await apiRequest(`/campaigns/${campaignId}/audience/preview/`, {
        method: 'POST',
        body: { filter_criteria: filterCriteria }
      }, cookies);
      return { previewCount: result.count, filterCriteria };
    } catch (err) {
      return fail(400, { error: 'Erro ao calcular preview da audiência.' });
    }
  },

  generateAudience: async ({ request, cookies }) => {
    const formData = await request.formData();
    const campaignId = formData.get('campaign_id')?.toString();
    const filterCriteriaRaw = formData.get('filter_criteria')?.toString() || '{}';
    const audienceName = formData.get('audience_name')?.toString() || 'Audiência Principal';

    let filterCriteria = {};
    try {
      filterCriteria = JSON.parse(filterCriteriaRaw);
    } catch {
      return fail(400, { error: 'Critérios de filtro inválidos.' });
    }

    try {
      const result = await apiRequest(`/campaigns/${campaignId}/audience/generate/`, {
        method: 'POST',
        body: { filter_criteria: filterCriteria, name: audienceName }
      }, cookies);
      return { success: true, toast: `Audiência gerada: ${result.recipients_created} destinatários criados.` };
    } catch (err) {
      return fail(400, { error: err?.message || 'Erro ao gerar audiência.' });
    }
  },

  scheduleCampaign: async ({ request, cookies }) => {
    const formData = await request.formData();
    const campaignId = formData.get('campaign_id')?.toString();
    const scheduledAt = formData.get('scheduled_at')?.toString();

    if (!scheduledAt) return fail(400, { error: 'Data de agendamento é obrigatória.' });

    try {
      await apiRequest(`/campaigns/${campaignId}/schedule/`, {
        method: 'POST',
        body: { scheduled_at: scheduledAt }
      }, cookies);
      return { success: true, toast: 'Campanha agendada com sucesso.' };
    } catch (err) {
      return fail(400, { error: err?.message || 'Erro ao agendar campanha.' });
    }
  },

  toggleReminder: async ({ request, cookies }) => {
    const formData = await request.formData();
    const id = formData.get('id');
    const isActive = formData.get('is_active') === 'true';
    const endpoint = isActive ? 'deactivate' : 'activate';
    try {
      await apiRequest(`/assistant/reminder-policies/${id}/${endpoint}/`, { method: 'PATCH' }, cookies);
      return { success: true, toast: isActive ? 'Lembrete desativado.' : 'Lembrete ativado.' };
    } catch (err) {
      return fail(400, { error: 'Erro ao alterar status.' });
    }
  },

  deleteReminder: async ({ request, cookies }) => {
    const formData = await request.formData();
    const id = formData.get('id');
    try {
      await apiRequest(`/assistant/reminder-policies/${id}/`, { method: 'DELETE' }, cookies);
      return { success: true, toast: 'Lembrete excluído.' };
    } catch (err) {
      return fail(400, { error: 'Erro ao excluir.' });
    }
  },

  retryJob: async ({ request, cookies }) => {
    const formData = await request.formData();
    const id = formData.get('id');
    try {
      await apiRequest(`/assistant/scheduled-jobs/${id}/retry/`, { method: 'POST' }, cookies);
      return { success: true, toast: 'Job reenfileirado.' };
    } catch (err) {
      return fail(400, { error: 'Erro ao retentar.' });
    }
  },

  cancelJob: async ({ request, cookies }) => {
    const formData = await request.formData();
    const id = formData.get('id');
    try {
      await apiRequest(`/assistant/scheduled-jobs/${id}/cancel/`, { method: 'POST' }, cookies);
      return { success: true, toast: 'Job cancelado.' };
    } catch (err) {
      return fail(400, { error: 'Erro ao cancelar.' });
    }
  },

  deleteTemplate: async ({ request, cookies }) => {
    const formData = await request.formData();
    const id = formData.get('id');
    try {
      await apiRequest(`/assistant/templates/${id}/`, { method: 'DELETE' }, cookies);
      return { success: true, toast: 'Modelo excluído.' };
    } catch (err) {
      return fail(400, { error: 'Erro ao excluir modelo.' });
    }
  },
};
