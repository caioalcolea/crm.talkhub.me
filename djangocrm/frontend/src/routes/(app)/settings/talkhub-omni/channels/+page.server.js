import { apiRequest } from '$lib/api-helpers.js';
import { redirect } from '@sveltejs/kit';

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

  let channels = {};
  let flows = {};

  try {
    channels = await apiRequest('/talkhub/channels/', {}, { cookies });
  } catch {
    /* ignore */
  }

  try {
    flows = await apiRequest('/talkhub/flows/', {}, { cookies });
  } catch {
    /* ignore */
  }

  return { channels, flows };
}
