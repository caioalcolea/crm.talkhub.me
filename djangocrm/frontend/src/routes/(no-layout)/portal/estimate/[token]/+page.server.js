/**
 * Public Estimate Portal Page
 *
 * Public view for clients to see their estimate via token.
 * No authentication required.
 */

import { error, fail } from '@sveltejs/kit';

/** @type {import('./$types').PageServerLoad} */
export async function load({ params, fetch }) {
  const { token } = params;

  if (!token) {
    throw error(400, 'Token do orçamento é obrigatório');
  }

  try {
    // Fetch estimate from public API (no auth)
    const response = await fetch(`/api/public/estimate/${token}/`);

    if (!response.ok) {
      if (response.status === 404) {
        throw error(404, 'Orçamento não encontrado ou link expirado');
      }
      throw error(response.status, 'Falha ao carregar orçamento');
    }

    const estimate = await response.json();

    return {
      estimate: {
        id: estimate.id,
        estimateNumber: estimate.estimate_number,
        title: estimate.title,
        status: estimate.status,
        clientName: estimate.client_name,
        clientEmail: estimate.client_email,
        issueDate: estimate.issue_date,
        expiryDate: estimate.expiry_date,
        subtotal: estimate.subtotal,
        discountAmount: estimate.discount_amount,
        taxAmount: estimate.tax_amount,
        totalAmount: estimate.total_amount,
        currency: estimate.currency,
        notes: estimate.notes,
        terms: estimate.terms,
        clientAddress: estimate.client_address,
        lineItems: estimate.line_items || [],
        org: estimate.org
      },
      template: estimate.template
        ? {
            primaryColor: estimate.template.primary_color || '#3B82F6',
            secondaryColor: estimate.template.secondary_color || '#1E40AF',
            footerText: estimate.template.footer_text || ''
          }
        : {
            primaryColor: '#3B82F6',
            secondaryColor: '#1E40AF',
            footerText: ''
          },
      token
    };
  } catch (err) {
    if (err.status) throw err;
    console.error('Error loading public estimate:', err);
    throw error(500, 'Falha ao carregar orçamento');
  }
}

/** @type {import('./$types').Actions} */
export const actions = {
  accept: async ({ params, fetch }) => {
    const { token } = params;

    try {
      const response = await fetch(`/api/public/estimate/${token}/accept/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const data = await response.json();
        return fail(response.status, { error: data.message || 'Falha ao aceitar orçamento' });
      }

      return { success: true, action: 'accepted' };
    } catch (err) {
      console.error('Error accepting estimate:', err);
      return fail(500, { error: 'Falha ao aceitar orçamento' });
    }
  },

  decline: async ({ params, fetch }) => {
    const { token } = params;

    try {
      const response = await fetch(`/api/public/estimate/${token}/decline/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const data = await response.json();
        return fail(response.status, { error: data.message || 'Falha ao recusar orçamento' });
      }

      return { success: true, action: 'declined' };
    } catch (err) {
      console.error('Error declining estimate:', err);
      return fail(500, { error: 'Falha ao recusar orçamento' });
    }
  }
};
