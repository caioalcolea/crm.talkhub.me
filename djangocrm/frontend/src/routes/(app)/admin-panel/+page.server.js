import { redirect } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals, cookies }) {
  // Only superusers can access admin panel
  if (!locals.user?.is_superuser) {
    throw redirect(307, '/');
  }

  try {
    const [dashboard, orgs, users] = await Promise.all([
      apiRequest('/admin-panel/dashboard/', {}, cookies),
      apiRequest('/admin-panel/orgs/', {}, cookies),
      apiRequest('/admin-panel/users/', {}, cookies)
    ]);

    return {
      dashboard,
      orgs: orgs.orgs || [],
      users: users.users || []
    };
  } catch (error) {
    console.error('Admin panel load error:', error);
    return {
      dashboard: {},
      orgs: [],
      users: [],
      error: 'Erro ao carregar painel de administração'
    };
  }
}
