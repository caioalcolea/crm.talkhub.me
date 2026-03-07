import { apiRequest } from '$lib/api-helpers.js';
import { redirect, fail } from '@sveltejs/kit';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies }) {
  let status;
  try {
    status = await apiRequest('/talkhub/status/', {}, { cookies });
  } catch {
    throw redirect(302, '/settings/talkhub-omni');
  }

  if (!status?.connected) {
    throw redirect(302, '/settings/talkhub-omni');
  }

  let history = { jobs: [] };
  try {
    history = await apiRequest('/talkhub/sync/history/', {}, { cookies });
  } catch {
    /* ignore */
  }

  return {
    thStatus: status,
    syncHistory: history.jobs || [],
  };
}

/** @type {import('./$types').Actions} */
export const actions = {
  syncContacts: async ({ cookies }) => {
    try {
      const result = await apiRequest('/talkhub/sync/contacts/', { method: 'POST' }, { cookies });
      return { syncStarted: true, syncType: 'contacts', jobId: result.job?.id };
    } catch (err) {
      return fail(400, { syncError: err?.message || 'Falha ao iniciar sync de contatos.' });
    }
  },
  syncKanbans: async ({ cookies }) => {
    try {
      const result = await apiRequest('/talkhub/sync/tickets/', { method: 'POST' }, { cookies });
      return { syncStarted: true, syncType: 'tickets', jobId: result.job?.id };
    } catch (err) {
      return fail(400, { syncError: err?.message || 'Falha ao iniciar sync de kanban.' });
    }
  },
  syncUsers: async ({ cookies }) => {
    try {
      const result = await apiRequest('/talkhub/sync/now/', { method: 'POST', body: { sync_type: 'team_members' } }, { cookies });
      return { syncStarted: true, syncType: 'team_members', jobId: result.job?.id };
    } catch (err) {
      return fail(400, { syncError: err?.message || 'Falha ao iniciar sync de usuários.' });
    }
  },
  syncAIAgents: async ({ cookies }) => {
    try {
      const result = await apiRequest('/talkhub/sync/now/', { method: 'POST', body: { sync_type: 'statistics' } }, { cookies });
      return { syncStarted: true, syncType: 'statistics', jobId: result.job?.id };
    } catch (err) {
      return fail(400, { syncError: err?.message || 'Falha ao iniciar sync de estatísticas.' });
    }
  },
  syncAll: async ({ cookies }) => {
    try {
      const result = await apiRequest('/talkhub/sync/now/', { method: 'POST', body: { sync_type: 'all' } }, { cookies });
      return { syncStarted: true, syncType: 'all', jobId: result.job?.id };
    } catch (err) {
      return fail(400, { syncError: err?.message || 'Falha ao iniciar sync completo.' });
    }
  },
};
