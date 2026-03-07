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

  let flowSummary = {};
  let agentSummary = {};

  try {
    flowSummary = await apiRequest('/talkhub/analytics/flow-summary/', {}, { cookies });
  } catch {
    /* ignore */
  }

  try {
    agentSummary = await apiRequest('/talkhub/analytics/agent-summary/', {}, { cookies });
  } catch {
    /* ignore */
  }

  return { flowSummary, agentSummary };
}
