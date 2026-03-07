import { writable, get } from 'svelte/store';

/**
 * @typedef {Object} OrgSettings
 * @property {string} default_currency - Default currency code (e.g., 'BRL', 'USD')
 * @property {string} currency_symbol - Currency symbol (e.g., 'R$', '$')
 * @property {string|null} default_country - Default country code or null
 * @property {string|null} logo_url - Organization logo URL or null
 */

/** @type {import('svelte/store').Writable<OrgSettings>} */
export const orgSettings = writable({
  default_currency: 'BRL',
  currency_symbol: 'R$',
  default_country: 'BR',
  logo_url: null
});

/**
 * Initialize org settings from JWT or API response
 * @param {Partial<OrgSettings>} settings
 */
export function initOrgSettings(settings) {
  orgSettings.set({
    default_currency: settings.default_currency || 'BRL',
    currency_symbol: settings.currency_symbol || 'R$',
    default_country: settings.default_country || null,
    logo_url: settings.logo_url || null
  });
}

/**
 * Get the current default currency from the org store.
 * Useful in non-reactive contexts (e.g., utility functions).
 * @returns {string} Currency code (e.g., 'BRL')
 */
export function getOrgCurrency() {
  return get(orgSettings).default_currency || 'BRL';
}
