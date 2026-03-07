/**
 * New Campaign Page
 *
 * Django endpoint: POST /api/campaigns/
 * Steps endpoint: POST /api/campaigns/<id>/steps/
 */

import { error, fail, redirect } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals }) {
  if (!locals.org) {
    throw error(401, 'Contexto de organização é obrigatório');
  }
  return {};
}

/** @type {import('./$types').Actions} */
export const actions = {
  create: async ({ request, cookies }) => {
    const formData = await request.formData();
    const name = formData.get('name')?.toString().trim();
    const campaignType = formData.get('campaign_type')?.toString();
    const subject = formData.get('subject')?.toString().trim() || null;
    const bodyTemplate = formData.get('body_template')?.toString() || '';
    const stepsRaw = formData.get('steps')?.toString();

    if (!name) {
      return fail(400, { error: 'Nome é obrigatório.' });
    }
    if (!campaignType) {
      return fail(400, { error: 'Tipo de campanha é obrigatório.' });
    }

    try {
      // Create campaign
      const campaign = await apiRequest('/campaigns/', {
        method: 'POST',
        body: {
          name,
          campaign_type: campaignType,
          subject,
          body_template: bodyTemplate,
          status: 'draft'
        }
      }, cookies);

      // Create steps for nurture_sequence
      if (campaignType === 'nurture_sequence' && stepsRaw) {
        try {
          const steps = JSON.parse(stepsRaw);
          for (const step of steps) {
            await apiRequest(`/campaigns/${campaign.id}/steps/`, {
              method: 'POST',
              body: {
                step_order: step.step_order,
                channel: step.channel,
                subject: step.subject || null,
                body_template: step.body_template || '',
                delay_hours: step.delay_hours || 0
              }
            }, cookies);
          }
        } catch (stepErr) {
          console.error('Error creating steps:', stepErr);
          // Campaign was created, steps failed — redirect anyway
        }
      }

      throw redirect(303, '/campaigns');
    } catch (err) {
      if (err?.status === 303) throw err;
      const message = err?.body?.detail || err?.message || 'Erro ao criar campanha.';
      return fail(400, { error: typeof message === 'string' ? message : JSON.stringify(message) });
    }
  }
};
