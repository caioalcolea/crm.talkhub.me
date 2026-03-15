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

      const removeLogo = formData.get('remove_logo') === 'true';

      if (hasLogoFile) {
        // Enviar como multipart/form-data quando tem logo
        const body = new FormData();
        body.append('name', formData.get('name') || '');
        body.append('company_name', formData.get('company_name') || '');
        body.append('website', formData.get('website') || '');
        body.append('email', formData.get('email') || '');
        body.append('phone', formData.get('phone') || '');
        body.append('tax_id', formData.get('tax_id') || '');
        body.append('address_line', formData.get('address_line') || '');
        body.append('city', formData.get('city') || '');
        body.append('state', formData.get('state') || '');
        body.append('postcode', formData.get('postcode') || '');
        body.append('country', formData.get('country') || '');
        body.append('default_currency', formData.get('default_currency') || 'BRL');
        const defaultCountry = formData.get('default_country');
        if (defaultCountry) body.append('default_country', /** @type {string} */ (defaultCountry));
        body.append('logo', /** @type {File} */ (logoFile));

        response = await apiRequest(
          '/org/settings/',
          { method: 'PATCH', body },
          { cookies }
        );
      } else {
        // Enviar como JSON quando não tem logo
        const body = {
          name: formData.get('name'),
          company_name: formData.get('company_name') || '',
          website: formData.get('website') || '',
          email: formData.get('email') || '',
          phone: formData.get('phone') || '',
          tax_id: formData.get('tax_id') || '',
          address_line: formData.get('address_line') || '',
          city: formData.get('city') || '',
          state: formData.get('state') || '',
          postcode: formData.get('postcode') || '',
          country: formData.get('country') || '',
          default_currency: formData.get('default_currency'),
          default_country: formData.get('default_country') || null
        };

        // Enviar logo: null para remover o logo existente
        if (removeLogo) {
          body.logo = null;
        }

        response = await apiRequest(
          '/org/settings/',
          { method: 'PATCH', body },
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
