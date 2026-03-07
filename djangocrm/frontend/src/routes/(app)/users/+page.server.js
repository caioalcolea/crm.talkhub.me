/**
 * Users & Teams Management Page - API Version
 *
 * Migrated from Prisma to Django REST API
 * Allows organization admins to:
 * - View all users in the organization
 * - Add users to the organization by email
 * - Change user roles (ADMIN/USER)
 * - Remove users from the organization
 * - Create, edit, delete teams
 * - Assign users to teams
 *
 * Django Endpoints:
 * - GET    /api/users/                  - List organization users
 * - POST   /api/users/                  - Create new user
 * - GET    /api/user/{id}/              - Get user details
 * - PUT    /api/user/{id}/              - Update user/profile
 * - DELETE /api/user/{id}/              - Deactivate user (soft delete)
 * - GET    /api/teams/                  - List teams
 * - POST   /api/teams/                  - Create team
 * - PUT    /api/teams/{id}/             - Update team
 * - DELETE /api/teams/{id}/             - Delete team
 */

import { error, fail } from '@sveltejs/kit';
import { env } from '$env/dynamic/public';

const API_BASE_URL = `${env.PUBLIC_DJANGO_API_URL}/api`;

/**
 * Make authenticated API request
 * @param {string} endpoint
 * @param {Object} options
 * @param {Object} context
 * @returns {Promise<any>}
 */
async function apiRequest(endpoint, options = {}, context) {
  const { cookies, org } = context;
  const accessToken = cookies.get('jwt_access') || cookies.get('access_token');

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
      org: org.id,
      ...options.headers
    }
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(errorData.errors || errorData.error || response.statusText);
  }

  return await response.json();
}

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals, cookies }) {
  const org = locals.org;
  const user = locals.user;

  try {
    // Fetch users, teams, and invitations in parallel
    const [usersData, teamsData, invitationsData] = await Promise.all([
      apiRequest('/users/', {}, { cookies, org }),
      apiRequest('/teams/', {}, { cookies, org }).catch(() => ({ teams: [] })),
      apiRequest('/invitations/', {}, { cookies, org }).catch(() => ({ invitations: [] }))
    ]);

    // Django returns: { active_users: {...}, inactive_users: {...}, roles: [...] }
    const activeUsers = usersData.active_users?.active_users || [];
    const inactiveUsers = usersData.inactive_users?.inactive_users || [];

    // Check if current user is admin
    // Django returns user_details with id and email
    const currentUserProfile = activeUsers.find(
      (p) => p.user_details?.id === user.id || p.user_details?.email === user.email
    );
    const isAdmin =
      currentUserProfile?.role === 'ADMIN' || currentUserProfile?.is_organization_admin;

    if (!isAdmin) {
      return {
        error: {
          name: 'Você não tem permissão para acessar esta página'
        }
      };
    }

    // Combine active and inactive users, transform to match expected format
    const allUsers = [
      ...activeUsers.map((profile) => ({
        odId: profile.user_details?.id || profile.id,
        organizationId: org.id,
        role: profile.role,
        user: {
          id: profile.user_details?.id || profile.id,
          email: profile.user_details?.email || 'N/A',
          name: profile.user_details?.email?.split('@')[0] || 'N/A'
        },
        isActive: true,
        profile
      })),
      ...inactiveUsers.map((profile) => ({
        odId: profile.user_details?.id || profile.id,
        organizationId: org.id,
        role: profile.role,
        user: {
          id: profile.user_details?.id || profile.id,
          email: profile.user_details?.email || 'N/A',
          name: profile.user_details?.email?.split('@')[0] || 'N/A'
        },
        isActive: false,
        profile
      }))
    ];

    // Transform teams - extract user IDs for form pre-population
    const teams = (teamsData.teams || []).map((team) => ({
      ...team,
      userIds: (team.users || []).map((u) => u.id)
    }));

    return {
      organization: {
        id: org.id,
        name: org.name,
        domain: org.domain || '',
        description: org.description || ''
      },
      users: allUsers,
      teams,
      invitations: invitationsData.invitations || [],
      user: { id: user.id }
    };
  } catch (err) {
    console.error('Error loading users:', err);
    const msg = err.message || 'Falha ao carregar usuários';
    // Distinguish permission errors from generic API failures
    const isPermission = msg.includes('permission') || msg.includes('403') || msg.includes('Forbidden');
    return {
      error: {
        name: isPermission
          ? 'Você não tem permissão para acessar esta página'
          : `Erro ao carregar usuários: ${msg}. Tente recarregar a página.`,
        isApiError: !isPermission
      }
    };
  }
}

/** @type {import('./$types').Actions} */
export const actions = {
  /**
   * Invite user to organization by email (uses invitation system)
   */
  add_user: async ({ request, locals, cookies }) => {
    const org = locals.org;

    try {
      const formData = await request.formData();
      const email = formData.get('email')?.toString().trim().toLowerCase();
      const role = formData.get('role')?.toString();

      if (!email || !role) {
        return fail(400, { error: 'Email e função são obrigatórios' });
      }

      // Use invitation endpoint — it handles both existing and new users
      const result = await apiRequest(
        '/invitations/',
        {
          method: 'POST',
          body: JSON.stringify({ email, role })
        },
        { cookies, org }
      );

      if (result.linked) {
        return { success: true, action: 'add_user', message: result.message };
      }
      return { success: true, action: 'invite_user', message: 'Convite enviado por email' };
    } catch (err) {
      console.error('Error inviting user:', err);
      return fail(400, { error: err.message || 'Falha ao enviar convite' });
    }
  },

  /**
   * Edit user role
   */
  edit_role: async ({ request, locals, cookies }) => {
    const org = locals.org;
    const user = locals.user;

    try {
      const formData = await request.formData();
      const user_id = formData.get('user_id')?.toString();
      const role = formData.get('role')?.toString();

      if (!user_id || !role) {
        return fail(400, { error: 'Usuário e função são obrigatórios' });
      }

      // Don't allow editing own role
      if (user_id === user.id) {
        return fail(400, { error: 'Você não pode alterar sua própria função' });
      }

      // Update user role via Django API
      // Django endpoint: PATCH /api/user/{id}/ (partial update)
      await apiRequest(
        `/user/${user_id}/`,
        {
          method: 'PATCH',
          body: JSON.stringify({ role })
        },
        { cookies, org }
      );

      return { success: true };
    } catch (err) {
      console.error('Error editing role:', err);
      if (err.message.includes('at least one admin')) {
        return fail(400, { error: 'A organização deve ter pelo menos um administrador' });
      }
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  /**
   * Remove user from organization
   */
  remove_user: async ({ request, locals, cookies }) => {
    const org = locals.org;
    const user = locals.user;

    try {
      const formData = await request.formData();
      const user_id = formData.get('user_id')?.toString();

      if (!user_id) {
        return fail(400, { error: 'Usuário é obrigatório' });
      }

      // Don't allow removing self
      if (user_id === user.id) {
        return fail(400, { error: 'Você não pode remover a si mesmo' });
      }

      // Remove user via Django API (soft delete - set is_active=False)
      // Django endpoint: POST /api/user/{id}/status/
      await apiRequest(
        `/user/${user_id}/status/`,
        {
          method: 'POST',
          body: JSON.stringify({ status: 'Inactive' })
        },
        { cookies, org }
      );

      return { success: true, action: 'remove_user' };
    } catch (err) {
      console.error('Error removing user:', err);
      if (err.message.includes('at least one admin')) {
        return fail(400, { error: 'A organização deve ter pelo menos um administrador' });
      }
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  /**
   * Activate user (restore inactive user)
   */
  activate_user: async ({ request, locals, cookies }) => {
    const org = locals.org;

    try {
      const formData = await request.formData();
      const user_id = formData.get('user_id')?.toString();

      if (!user_id) {
        return fail(400, { error: 'Usuário é obrigatório' });
      }

      // Activate user via Django API (set is_active=True)
      await apiRequest(
        `/user/${user_id}/status/`,
        {
          method: 'POST',
          body: JSON.stringify({ status: 'Active' })
        },
        { cookies, org }
      );

      return { success: true, action: 'activate_user' };
    } catch (err) {
      console.error('Error activating user:', err);
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  /**
   * Create a new team
   */
  create_team: async ({ request, locals, cookies }) => {
    const org = locals.org;

    try {
      const formData = await request.formData();
      const name = formData.get('name')?.toString().trim();
      const description = formData.get('description')?.toString().trim() || '';
      const users = formData.getAll('users').map((u) => u.toString());

      if (!name) {
        return fail(400, { error: 'Nome da equipe é obrigatório' });
      }

      // Create team via Django API
      await apiRequest(
        '/teams/',
        {
          method: 'POST',
          body: JSON.stringify({
            name,
            description,
            assign_users: true,
            users
          })
        },
        { cookies, org }
      );

      return { success: true, action: 'create_team' };
    } catch (err) {
      console.error('Error creating team:', err);
      if (err.message.includes('already exists')) {
        return fail(400, { error: 'Já existe uma equipe com este nome' });
      }
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  /**
   * Update an existing team
   */
  update_team: async ({ request, locals, cookies }) => {
    const org = locals.org;

    try {
      const formData = await request.formData();
      const teamId = formData.get('team_id')?.toString();
      const name = formData.get('name')?.toString().trim();
      const description = formData.get('description')?.toString().trim() || '';
      const users = formData.getAll('users').map((u) => u.toString());

      if (!teamId) {
        return fail(400, { error: 'ID da equipe é obrigatório' });
      }

      if (!name) {
        return fail(400, { error: 'Nome da equipe é obrigatório' });
      }

      // Update team via Django API
      await apiRequest(
        `/teams/${teamId}/`,
        {
          method: 'PUT',
          body: JSON.stringify({
            name,
            description,
            assign_users: users
          })
        },
        { cookies, org }
      );

      return { success: true, action: 'update_team' };
    } catch (err) {
      console.error('Error updating team:', err);
      if (err.message.includes('already exists')) {
        return fail(400, { error: 'Já existe uma equipe com este nome' });
      }
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  /**
   * Delete a team
   */
  delete_team: async ({ request, locals, cookies }) => {
    const org = locals.org;

    try {
      const formData = await request.formData();
      const teamId = formData.get('team_id')?.toString();

      if (!teamId) {
        return fail(400, { error: 'ID da equipe é obrigatório' });
      }

      // Delete team via Django API
      await apiRequest(
        `/teams/${teamId}/`,
        {
          method: 'DELETE'
        },
        { cookies, org }
      );

      return { success: true, action: 'delete_team' };
    } catch (err) {
      console.error('Error deleting team:', err);
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  /**
   * Cancel a pending invitation
   */
  cancel_invitation: async ({ request, locals, cookies }) => {
    const org = locals.org;

    try {
      const formData = await request.formData();
      const invitationId = formData.get('invitation_id')?.toString();

      if (!invitationId) {
        return fail(400, { error: 'ID do convite é obrigatório' });
      }

      await apiRequest(
        `/invitations/${invitationId}/`,
        { method: 'DELETE' },
        { cookies, org }
      );

      return { success: true, action: 'cancel_invitation' };
    } catch (err) {
      console.error('Error cancelling invitation:', err);
      return fail(400, { error: err.message || 'Falha ao cancelar convite' });
    }
  },

  /**
   * Resend a pending invitation email
   */
  resend_invitation: async ({ request, locals, cookies }) => {
    const org = locals.org;

    try {
      const formData = await request.formData();
      const invitationId = formData.get('invitation_id')?.toString();

      if (!invitationId) {
        return fail(400, { error: 'ID do convite é obrigatório' });
      }

      await apiRequest(
        `/invitations/${invitationId}/resend/`,
        { method: 'POST' },
        { cookies, org }
      );

      return { success: true, action: 'resend_invitation' };
    } catch (err) {
      console.error('Error resending invitation:', err);
      return fail(400, { error: err.message || 'Falha ao reenviar convite' });
    }
  }
};
