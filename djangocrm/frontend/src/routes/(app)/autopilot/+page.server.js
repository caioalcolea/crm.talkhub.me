import { error } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals, cookies, url }) {
  const org = locals.org;
  if (!org) throw error(401, 'Contexto de organização é obrigatório');

  const tab = url.searchParams.get('tab') || 'rules';

  try {
    // Load data based on active tab (parallel where possible)
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
      const type = url.searchParams.get('type') || '';
      const status = url.searchParams.get('status') || '';
      const params = new URLSearchParams();
      if (type) params.append('type', type);
      if (status) params.append('status', status);
      const qs = params.toString();
      promises.campaigns = apiRequest(`/campaigns/${qs ? '?' + qs : ''}`, {}, cookies).catch(() => []);
    }

    if (tab === 'runs') {
      promises.runs = apiRequest('/assistant/runs/?limit=50', {}, cookies).catch(() => ({ results: [], count: 0 }));
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
      filters: {
        type: url.searchParams.get('type') || '',
        status: url.searchParams.get('status') || '',
        module: url.searchParams.get('module') || '',
        is_active: url.searchParams.get('is_active') || '',
      },
      ...results,
    };
  } catch (err) {
    console.error('Autopilot load error:', err);
    return { tab, filters: {}, automations: [], reminders: [], campaigns: [], runs: { results: [], count: 0 }, templates: [] };
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
      const { fail } = await import('@sveltejs/kit');
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
      const { fail } = await import('@sveltejs/kit');
      return fail(400, { error: 'Erro ao excluir.' });
    }
  },

  deleteCampaign: async ({ request, cookies }) => {
    const formData = await request.formData();
    const id = formData.get('id');
    try {
      await apiRequest(`/campaigns/${id}/`, { method: 'DELETE' }, cookies);
      return { success: true, toast: 'Campanha excluída.' };
    } catch (err) {
      const { fail } = await import('@sveltejs/kit');
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
      const { fail } = await import('@sveltejs/kit');
      return fail(400, { error: 'Erro ao alterar status.' });
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
      const { fail } = await import('@sveltejs/kit');
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
      const { fail } = await import('@sveltejs/kit');
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
      const { fail } = await import('@sveltejs/kit');
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
      const { fail } = await import('@sveltejs/kit');
      return fail(400, { error: 'Erro ao cancelar.' });
    }
  },
};
