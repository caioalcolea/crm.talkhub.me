/**
 * Formatting utilities for consistent data display across the application
 * @module lib/utils/formatting
 */

import { format, formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { getOrgCurrency } from '$lib/stores/org.js';

/**
 * Format a date string to a human-readable format
 * @param {string | Date | null | undefined} date - Date to format
 * @param {string} [formatStr='MMM d, yyyy'] - date-fns format string
 * @returns {string} Formatted date string or '-' if no date
 */
export function formatDate(date, formatStr = 'MMM d, yyyy') {
  if (!date) return '-';
  try {
    return format(new Date(date), formatStr);
  } catch {
    return '-';
  }
}

/**
 * Format a date as relative time (e.g., "2 hours ago")
 * @param {string | Date | null | undefined} date - Date to format
 * @returns {string} Relative time string or '-' if no date
 */
export function formatRelativeDate(date) {
  if (!date) return '-';
  try {
    return formatDistanceToNow(new Date(date), { addSuffix: true, locale: ptBR });
  } catch {
    return '-';
  }
}

/**
 * Format a number as currency.
 * When no currency is provided, uses the org's default currency from the store.
 * @param {number | string | null | undefined} amount - Amount to format
 * @param {string} [currency] - Currency code (ISO 4217). Falls back to org default.
 * @param {boolean} [compact=false] - Use compact notation (e.g., R$1,2M)
 * @returns {string} Formatted currency string or '-' if no amount
 */
export function formatCurrency(amount, currency, compact = false) {
  if (amount === null || amount === undefined) return '-';

  // Convert to number if string
  const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;

  // Handle NaN or invalid numbers
  if (isNaN(numAmount)) return '-';

  // Use org default currency when none provided
  const resolvedCurrency = currency && currency.length === 3 ? currency : getOrgCurrency();

  try {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: resolvedCurrency,
      notation: compact ? 'compact' : 'standard',
      maximumFractionDigits: compact ? 1 : 2
    }).format(numAmount);
  } catch {
    // Fallback if currency code is invalid
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
      notation: compact ? 'compact' : 'standard',
      maximumFractionDigits: compact ? 1 : 2
    }).format(numAmount);
  }
}

/**
 * Format a number with commas
 * @param {number | null | undefined} num - Number to format
 * @returns {string} Formatted number string or '-' if no number
 */
export function formatNumber(num) {
  if (num === null || num === undefined) return '-';
  return new Intl.NumberFormat('pt-BR').format(num);
}

/**
 * Get initials from a name string
 * @param {string | null | undefined} name - Full name
 * @param {number} [maxLength=2] - Maximum number of initials
 * @returns {string} Uppercase initials
 */
export function getInitials(name, maxLength = 2) {
  if (!name) return '';
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, maxLength);
}

/**
 * Get initials from first and last name
 * @param {string | null | undefined} firstName
 * @param {string | null | undefined} lastName
 * @returns {string} Uppercase initials
 */
export function getNameInitials(firstName, lastName) {
  const first = firstName?.[0] || '';
  const last = lastName?.[0] || '';
  return `${first}${last}`.toUpperCase();
}

/**
 * Crypto currencies that need 8 decimal places
 */
const CRYPTO_CURRENCIES = new Set(['BTC', 'ETH', 'USDT', 'USDC', 'SOL', 'BNB', 'XRP', 'ADA']);

/**
 * Crypto currency symbols
 */
const CRYPTO_SYMBOLS = {
  BTC: '\u20BF',
  ETH: '\u039E',
  USDT: '\u20AE',
  USDC: 'USDC',
  SOL: '\u25CE',
  BNB: 'BNB',
  XRP: 'XRP',
  ADA: '\u20B3'
};

/**
 * Format a crypto or fiat currency amount with appropriate decimal places
 * @param {number | string | null | undefined} amount - Amount to format
 * @param {string} [currency='BRL'] - Currency code
 * @returns {string} Formatted currency string
 */
export function formatFinanceiroCurrency(amount, currency = 'BRL') {
  if (amount === null || amount === undefined) return '-';

  const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
  if (isNaN(numAmount)) return '-';

  if (CRYPTO_CURRENCIES.has(currency)) {
    const symbol = CRYPTO_SYMBOLS[currency] || currency;
    const formatted = numAmount.toLocaleString('pt-BR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 8
    });
    return `${symbol} ${formatted}`;
  }

  return formatCurrency(amount, currency);
}

/**
 * Format a phone number for display
 * @param {string | null | undefined} phone - Phone number
 * @returns {string} Formatted phone number or empty string
 */
export function formatPhone(phone) {
  if (!phone) return '';
  // Remove non-digits
  const digits = phone.replace(/\D/g, '');
  // Format as (XXX) XXX-XXXX if 10 digits
  if (digits.length === 10) {
    return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
  }
  // Return original if not 10 digits
  return phone;
}
