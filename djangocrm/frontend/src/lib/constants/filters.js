/**
 * Constantes de filtros para páginas de listagem
 * @module lib/constants/filters
 */

/** @type {{ value: string, label: string }[]} */
export const LEAD_STATUSES = [
  { value: 'ALL', label: 'Todos os Status' },
  { value: 'ASSIGNED', label: 'Atribuído' },
  { value: 'IN_PROCESS', label: 'Em Andamento' },
  { value: 'CONVERTED', label: 'Convertido' },
  { value: 'RECYCLED', label: 'Reciclado' },
  { value: 'CLOSED', label: 'Fechado' }
];

/** @type {{ value: string, label: string }[]} */
export const LEAD_SOURCES = [
  { value: 'ALL', label: 'Todas as Origens' },
  { value: 'call', label: 'Ligação' },
  { value: 'email', label: 'E-mail' },
  { value: 'existing customer', label: 'Cliente Existente' },
  { value: 'partner', label: 'Parceiro' },
  { value: 'public relations', label: 'Relações Públicas' },
  { value: 'campaign', label: 'Campanha' },
  { value: 'other', label: 'Outro' }
];

/** @type {{ value: string, label: string }[]} */
export const LEAD_RATINGS = [
  { value: 'ALL', label: 'Todas as Temperaturas' },
  { value: 'HOT', label: 'Quente' },
  { value: 'WARM', label: 'Morno' },
  { value: 'COLD', label: 'Frio' }
];

/** @type {{ value: string, label: string }[]} */
export const CASE_STATUSES = [
  { value: 'ALL', label: 'Todos os Status' },
  { value: 'New', label: 'Novo' },
  { value: 'Assigned', label: 'Atribuído' },
  { value: 'Pending', label: 'Pendente' },
  { value: 'Closed', label: 'Fechado' },
  { value: 'Rejected', label: 'Rejeitado' },
  { value: 'Duplicate', label: 'Duplicado' }
];

/** @type {{ value: string, label: string }[]} */
export const CASE_TYPES = [
  { value: '', label: 'Selecionar Tipo' },
  { value: 'Question', label: 'Dúvida' },
  { value: 'Incident', label: 'Incidente' },
  { value: 'Problem', label: 'Problema' }
];

/** @type {{ value: string, label: string }[]} */
export const PRIORITIES = [
  { value: 'ALL', label: 'Todas as Prioridades' },
  { value: 'High', label: 'Alta' },
  { value: 'Medium', label: 'Média' },
  { value: 'Low', label: 'Baixa' }
];

/** @type {{ value: string, label: string }[]} */
export const OPPORTUNITY_STAGES = [
  { value: 'ALL', label: 'Todas as Etapas' },
  { value: 'PROSPECTING', label: 'Prospecção' },
  { value: 'QUALIFICATION', label: 'Qualificação' },
  { value: 'PROPOSAL', label: 'Proposta' },
  { value: 'NEGOTIATION', label: 'Negociação' },
  { value: 'CLOSED_WON', label: 'Ganho' },
  { value: 'CLOSED_LOST', label: 'Perdido' }
];

/** @type {{ value: string, label: string }[]} */
export const TASK_STATUSES = [
  { value: 'ALL', label: 'Todos os Status' },
  { value: 'New', label: 'Novo' },
  { value: 'In Progress', label: 'Em Andamento' },
  { value: 'Completed', label: 'Concluído' }
];

/** @type {{ value: string, label: string }[]} */
export const OPPORTUNITY_TYPES = [
  { value: '', label: 'Selecionar Tipo' },
  { value: 'NEW_BUSINESS', label: 'Novo Negócio' },
  { value: 'EXISTING_BUSINESS', label: 'Negócio Existente' },
  { value: 'RENEWAL', label: 'Renovação' },
  { value: 'UPSELL', label: 'Upsell' },
  { value: 'CROSS_SELL', label: 'Venda Cruzada' }
];

/** @type {{ value: string, label: string }[]} */
export const OPPORTUNITY_SOURCES = [
  { value: '', label: 'Selecionar Origem' },
  { value: 'NONE', label: 'Nenhuma' },
  { value: 'CALL', label: 'Ligação' },
  { value: 'EMAIL', label: 'E-mail' },
  { value: 'EXISTING CUSTOMER', label: 'Cliente Existente' },
  { value: 'PARTNER', label: 'Parceiro' },
  { value: 'PUBLIC RELATIONS', label: 'Relações Públicas' },
  { value: 'CAMPAIGN', label: 'Campanha' },
  { value: 'WEBSITE', label: 'Site' },
  { value: 'OTHER', label: 'Outro' }
];

/** @type {{ value: string, label: string }[]} */
export const CURRENCY_CODES = [
  { value: '', label: 'Selecionar Moeda' },
  { value: 'BRL', label: 'BRL - Real' },
  { value: 'USD', label: 'USD - Dólar' },
  { value: 'EUR', label: 'EUR - Euro' },
  { value: 'GBP', label: 'GBP - Libra' },
  { value: 'INR', label: 'INR - Rupia' },
  { value: 'CAD', label: 'CAD - Dólar Canadense' },
  { value: 'AUD', label: 'AUD - Dólar Australiano' },
  { value: 'JPY', label: 'JPY - Iene' },
  { value: 'CNY', label: 'CNY - Yuan' },
  { value: 'CHF', label: 'CHF - Franco' },
  { value: 'SGD', label: 'SGD - Dólar Singapura' },
  { value: 'AED', label: 'AED - Dirham' },
  { value: 'MXN', label: 'MXN - Peso' },
  { value: 'BTC', label: 'BTC - Bitcoin' },
  { value: 'ETH', label: 'ETH - Ethereum' },
  { value: 'USDT', label: 'USDT - Tether' },
  { value: 'USDC', label: 'USDC - USD Coin' },
  { value: 'SOL', label: 'SOL - Solana' },
  { value: 'BNB', label: 'BNB - Binance Coin' },
  { value: 'XRP', label: 'XRP - Ripple' },
  { value: 'ADA', label: 'ADA - Cardano' }
];

/** @type {Record<string, string>} */
export const CURRENCY_SYMBOLS = {
  USD: '$',
  EUR: '€',
  GBP: '£',
  INR: '₹',
  CAD: 'CA$',
  AUD: 'A$',
  JPY: '¥',
  CNY: '¥',
  CHF: 'CHF',
  SGD: 'S$',
  AED: 'د.إ',
  BRL: 'R$',
  MXN: 'MX$',
  BTC: '₿',
  ETH: 'Ξ',
  USDT: '₮',
  USDC: '$',
  SOL: '◎',
  BNB: 'BNB',
  XRP: 'XRP',
  ADA: '₳'
};
