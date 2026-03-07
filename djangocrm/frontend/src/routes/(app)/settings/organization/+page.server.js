import { error, fail } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

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

      return { success: true, settings: response };
    } catch (err) {
      console.error('Failed to update org settings:', err);
      const message = err?.message || 'Falha ao salvar configurações';
      return fail(400, { error: message });
    }
  }
};
