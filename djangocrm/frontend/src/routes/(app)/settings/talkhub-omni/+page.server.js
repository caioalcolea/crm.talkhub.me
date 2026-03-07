import { apiRequest } from '$lib/api-helpers.js';
import { fail } from '@sveltejs/kit';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies }) {
  try {
    const status = await apiRequest('/talkhub/status/', {}, { cookies });
    return { thStatus: status, error: null };
  } catch (err) {
    return { thStatus: { connected: false }, error: err?.message || 'Falha ao verificar status do TalkHub Omni.' };
  }
}

/** @type {import('./$types').Actions} */
export const actions = {
  saveCredentials: async ({ request, cookies }) => {
    const formData = await request.formData();
    const api_key = formData.get('api_key')?.toString().trim();
    const workspace_url = formData.get('workspace_url')?.toString().trim() || 'https://chat.talkhub.me';

    if (!api_key) {
      return fail(400, { credentialError: 'A API Key é obrigatória.' });
    }

    // Step 1: Save credentials
    try {
      await apiRequest(
        '/talkhub/credentials/',
        { method: 'POST', body: { api_key, workspace_url } },
        { cookies }
      );
    } catch (err) {
      return fail(400, { credentialError: err?.message || 'Falha ao salvar credenciais.' });
    }

    // Step 2: Connect (validate via GET /team-info)
    try {
      await apiRequest('/talkhub/connect/', { method: 'POST' }, { cookies });
      return { connected: true };
    } catch (err) {
      return fail(400, {
        credentialError: err?.message || 'Credenciais salvas mas falha ao conectar. Verifique sua API Key.'
      });
    }
  },
  disconnect: async ({ cookies }) => {
    try {
      await apiRequest('/talkhub/disconnect/', { method: 'DELETE' }, { cookies });
      return { disconnected: true };
    } catch (err) {
      return fail(400, { credentialError: err?.message || 'Falha ao desconectar.' });
    }
  }
};
