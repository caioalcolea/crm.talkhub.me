import { fail, redirect } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { validatePhoneNumber, formatPhoneForStorage } from '$lib/utils/phone.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals, cookies }) {
  if (!locals.user) {
    throw redirect(307, '/login');
  }

  const org = locals.org;

  try {
    const response = await apiRequest('/profile/', {}, { cookies, org });
    const profileData = response.user_obj || response;
    const userDetails = profileData.user_details || profileData.user || {};

    const user = {
      id: profileData.id || locals.user.id,
      user_id: profileData.user_id || userDetails.id,
      email: userDetails.email || profileData.email || locals.user.email,
      name: userDetails.name || profileData.name || userDetails.email,
      profilePhoto:
        profileData.profile_photo_url ||
        profileData.profile_photo ||
        userDetails.profile_photo ||
        userDetails.profile_pic ||
        null,
      phone: profileData.phone || userDetails.phone || null,
      isActive: profileData.is_active !== undefined ? profileData.is_active : true,
      lastLogin: userDetails.last_login || null,
      createdAt: profileData.created_at || profileData.created_on || userDetails.date_joined || null,
      organizations: []
    };

    return { user };
  } catch (err) {
    console.error('Error loading profile:', err);
    throw redirect(307, '/login');
  }
}

/** @type {import('./$types').Actions} */
export const actions = {
  updateProfile: async ({ request, locals, cookies }) => {
    if (!locals.user) {
      throw redirect(307, '/login');
    }

    const org = locals.org;
    const formData = await request.formData();
    const name = formData.get('name')?.toString();
    const phone = formData.get('phone')?.toString();
    const photoFile = formData.get('profile_photo');
    const hasPhoto = photoFile && /** @type {File} */ (photoFile).size > 0;

    // Validation
    const errors = {};

    if (!name || name.trim().length === 0) {
      errors.name = 'Nome é obrigatório';
    } else if (name.trim().length < 2) {
      errors.name = 'Nome deve ter pelo menos 2 caracteres';
    }

    let formattedPhone = null;
    if (phone && phone.trim().length > 0) {
      const phoneValidation = validatePhoneNumber(phone.trim());
      if (!phoneValidation.isValid) {
        errors.phone = phoneValidation.error || 'Número de telefone inválido';
      } else {
        formattedPhone = formatPhoneForStorage(phone.trim());
      }
    }

    if (Object.keys(errors).length > 0) {
      return fail(400, { errors, data: { name, phone } });
    }

    try {
      if (hasPhoto) {
        // Enviar como multipart/form-data quando tem foto
        const body = new FormData();
        body.append('name', name.trim());
        if (formattedPhone) body.append('phone', formattedPhone);
        body.append('profile_photo', /** @type {File} */ (photoFile));

        await apiRequest('/profile/', { method: 'PATCH', body }, { cookies, org });
      } else {
        // Enviar como JSON quando não tem foto
        await apiRequest(
          '/profile/',
          {
            method: 'PATCH',
            body: { name: name.trim(), phone: formattedPhone }
          },
          { cookies, org }
        );
      }

      return { success: true, message: 'Perfil atualizado com sucesso' };
    } catch (err) {
      console.error('Error updating profile:', err);
      return fail(400, {
        error: err.message || 'Falha ao atualizar perfil',
        data: { name, phone }
      });
    }
  }
};
