import { error, fail } from '@sveltejs/kit';
import { env } from '$env/dynamic/public';
import { apiRequest } from '$lib/api-helpers.js';

const API_BASE_URL = `${env.PUBLIC_DJANGO_API_URL}/api`;

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies }) {
  try {
    const response = await apiRequest('/org/settings/', {}, { cookies });
    return {
      settings: response
    };
  } catch (err) {
    console.error('Failed to load org settings:', err);
    throw error(500, 'Falha ao carregar configurações da organização');
  }
}

/**
 * Refresh JWT tokens so org_settings embedded in the JWT reflect DB changes.
 * @param {import('@sveltejs/kit').Cookies} cookies
 */
async function refreshJwtTokens(cookies) {
  const refreshToken = cookies.get('jwt_refresh');
  if (!refreshToken) return;

  try {
    const res = await fetch(`${API_BASE_URL}/auth/refresh-token/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: refreshToken })
    });

    if (!res.ok) return;

    const data = await res.json();
    if (data.access) {
      cookies.set('jwt_access', data.access, {
        path: '/',
        httpOnly: true,
        sameSite: 'lax',
        secure: process.env.NODE_ENV === 'production',
        maxAge: 60 * 60 * 24
      });
    }
    if (data.refresh) {
      cookies.set('jwt_refresh', data.refresh, {
        path: '/',
        httpOnly: true,
        sameSite: 'lax',
        secure: process.env.NODE_ENV === 'production',
        maxAge: 60 * 60 * 24 * 365
      });
    }
  } catch (err) {
    console.error('Failed to refresh JWT after settings update:', err);
  }
}

/** @type {import('./$types').Actions} */
export const actions = {
  update: async ({ request, cookies }) => {
    const formData = await request.formData();

    const logoFile = formData.get('logo');
    const hasLogoFile = logoFile && /** @type {File} */ (logoFile).size > 0;

    try {
      let response;

      if (hasLogoFile) {
        // Enviar como multipart/form-data quando tem logo
        const body = new FormData();
        body.append('name', formData.get('name') || '');
        const domain = formData.get('domain');
        if (domain) body.append('domain', /** @type {string} */ (domain));
        const description = formData.get('description');
        if (description) body.append('description', /** @type {string} */ (description));
        body.append('default_currency', formData.get('default_currency') || 'BRL');
        const country = formData.get('default_country');
        if (country) body.append('default_country', /** @type {string} */ (country));
        body.append('logo', /** @type {File} */ (logoFile));

        response = await apiRequest(
          '/org/settings/',
          { method: 'PATCH', body },
          { cookies }
        );
      } else {
        // Enviar como JSON quando não tem logo
        response = await apiRequest(
          '/org/settings/',
          {
            method: 'PATCH',
            body: {
              name: formData.get('name'),
              domain: formData.get('domain') || null,
              description: formData.get('description') || null,
              default_currency: formData.get('default_currency'),
              default_country: formData.get('default_country') || null
            }
          },
          { cookies }
        );
      }

      // Refresh JWT tokens so the embedded org_settings reflect the new values.
      // The token refresh endpoint re-reads org data from DB, so the new
      // currency/country will be included in the fresh JWT payload.
      await refreshJwtTokens(cookies);

      return { success: true, settings: response };
    } catch (err) {
      console.error('Failed to update org settings:', err);
      const message = err?.message || 'Falha ao salvar configurações';
      return fail(400, { error: message });
    }
  }
};
