import { error, fail } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies, locals }) {
  // Check if user is admin
  const profile = locals.profile;
  if (profile?.role !== 'ADMIN' && !profile?.is_organization_admin) {
    throw error(403, 'Apenas administradores podem gerenciar etiquetas');
  }

  try {
    // Get all tags including archived for admin view
    const response = await apiRequest('/tags/?include_archived=true', {}, { cookies });
    return {
      tags: response.tags || []
    };
  } catch (err) {
    console.error('Failed to load tags:', err);
    throw error(500, 'Falha ao carregar etiquetas');
  }
}

/** @type {import('./$types').Actions} */
export const actions = {
  create: async ({ request, cookies }) => {
    const formData = await request.formData();
    const name = /** @type {string | null} */ (formData.get('name'));
    const data = {
      name,
      color: formData.get('color') || 'blue',
      description: formData.get('description') || ''
    };

    if (!name?.trim()) {
      return fail(400, { error: 'Nome da etiqueta é obrigatório' });
    }

    try {
      await apiRequest('/tags/', { method: 'POST', body: data }, { cookies });
      return { success: true, action: 'create' };
    } catch (err) {
      console.error('Failed to create tag:', err);
      return fail(400, { error: err?.message || 'Falha na operação' });
    }
  },

  update: async ({ request, cookies }) => {
    const formData = await request.formData();
    const tagId = formData.get('tagId');
    const name = /** @type {string | null} */ (formData.get('name'));
    const data = {
      name,
      color: formData.get('color'),
      description: formData.get('description') || ''
    };

    if (!name?.trim()) {
      return fail(400, { error: 'Nome da etiqueta é obrigatório' });
    }

    try {
      await apiRequest(`/tags/${tagId}/`, { method: 'PUT', body: data }, { cookies });
      return { success: true, action: 'update' };
    } catch (err) {
      console.error('Failed to update tag:', err);
      return fail(400, { error: err?.message || 'Falha na operação' });
    }
  },

  archive: async ({ request, cookies }) => {
    const formData = await request.formData();
    const tagId = formData.get('tagId');

    try {
      await apiRequest(`/tags/${tagId}/`, { method: 'DELETE' }, { cookies });
      return { success: true, action: 'archive' };
    } catch (err) {
      console.error('Failed to archive tag:', err);
      return fail(400, { error: err?.message || 'Falha na operação' });
    }
  },

  restore: async ({ request, cookies }) => {
    const formData = await request.formData();
    const tagId = formData.get('tagId');

    try {
      await apiRequest(`/tags/${tagId}/restore/`, { method: 'POST' }, { cookies });
      return { success: true, action: 'restore' };
    } catch (err) {
      console.error('Failed to restore tag:', err);
      return fail(400, { error: err?.message || 'Falha na operação' });
    }
  }
};
