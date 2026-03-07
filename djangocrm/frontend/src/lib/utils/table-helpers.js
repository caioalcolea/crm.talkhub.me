/**
 * Table helper utilities for CRM-style inline editing tables
 * @module lib/utils/table-helpers
 */

/**
 * @typedef {Object} SelectOption
 * @property {string} value - Option value
 * @property {string} label - Display label
 * @property {string} color - Tailwind CSS classes for styling
 */

/**
 * Get style classes for a select option
 * @param {string | null | undefined} value - Current value
 * @param {SelectOption[]} options - Available options
 * @returns {string} Tailwind CSS classes
 */
export function getOptionStyle(value, options) {
  const option = options.find((o) => o.value === value);
  return option?.color ?? 'bg-[var(--surface-sunken)] text-[var(--text-secondary)]';
}

/**
 * Get display label for a select option
 * @param {string | null | undefined} value - Current value
 * @param {SelectOption[]} options - Available options
 * @returns {string} Display label
 */
export function getOptionLabel(value, options) {
  const option = options.find((o) => o.value === value);
  return option?.label ?? value ?? '';
}

/**
 * Get the background color class (first part of color string)
 * @param {string | null | undefined} value - Current value
 * @param {SelectOption[]} options - Available options
 * @returns {string} Background color class
 */
export function getOptionBgColor(value, options) {
  const style = getOptionStyle(value, options);
  return style.split(' ')[0] ?? 'bg-gray-100';
}

/**
 * Create a column config for localStorage persistence
 * @param {string} key - Column key
 * @param {string} label - Column label
 * @param {boolean} [visible=true] - Whether column is visible
 * @param {boolean} [canHide=true] - Whether column can be hidden
 * @returns {{ key: string, label: string, visible: boolean, canHide: boolean }}
 */
export function createColumnConfig(key, label, visible = true, canHide = true) {
  return { key, label, visible, canHide };
}

/**
 * Load column config from localStorage
 * @param {string} storageKey - localStorage key
 * @param {{ key: string, label: string, visible: boolean, canHide: boolean }[]} defaultColumns - Default columns
 * @returns {{ key: string, label: string, visible: boolean, canHide: boolean }[]}
 */
export function loadColumnConfig(storageKey, defaultColumns) {
  if (typeof window === 'undefined') return defaultColumns;
  try {
    const saved = localStorage.getItem(storageKey);
    if (saved) {
      const parsed = JSON.parse(saved);
      return defaultColumns.map((def) => {
        const savedCol = parsed.find((/** @type {{ key: string }} */ p) => p.key === def.key);
        return savedCol ? { ...def, visible: savedCol.visible } : def;
      });
    }
  } catch (e) {
    console.error('Failed to load column config:', e);
  }
  return defaultColumns;
}

/**
 * Save column config to localStorage
 * @param {string} storageKey - localStorage key
 * @param {{ key: string, visible: boolean }[]} columns - Column config
 */
export function saveColumnConfig(storageKey, columns) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(storageKey, JSON.stringify(columns));
  } catch (e) {
    console.error('Failed to save column config:', e);
  }
}

/**
 * Toggle column visibility
 * @param {{ key: string, visible: boolean, canHide: boolean }[]} columns - Current columns
 * @param {string} key - Column key to toggle
 * @returns {{ key: string, visible: boolean, canHide: boolean }[]}
 */
export function toggleColumnVisibility(columns, key) {
  return columns.map((col) => {
    if (col.key === key && col.canHide) {
      return { ...col, visible: !col.visible };
    }
    return col;
  });
}

/**
 * Get visible column count
 * @param {{ visible: boolean }[]} columns - Columns
 * @returns {{ visible: number, total: number }}
 */
export function getVisibleColumnCount(columns) {
  return {
    visible: columns.filter((c) => c.visible).length,
    total: columns.length
  };
}

// Opções de status para entidades CRM - Usando tokens do design system
// Deve corresponder ao Django LEAD_STATUS: assigned, in process, converted, recycled, closed
export const leadStatusOptions = [
  {
    value: 'ASSIGNED',
    label: 'Atribuído',
    color: 'bg-[var(--stage-new-bg)] text-[var(--stage-new)] dark:bg-[var(--stage-new)]/15'
  },
  {
    value: 'IN_PROCESS',
    label: 'Em Andamento',
    color:
      'bg-[var(--stage-contacted-bg)] text-[var(--stage-contacted)] dark:bg-[var(--stage-contacted)]/15'
  },
  {
    value: 'CONVERTED',
    label: 'Convertido',
    color: 'bg-[var(--stage-won-bg)] text-[var(--stage-won)] dark:bg-[var(--stage-won)]/15'
  },
  {
    value: 'RECYCLED',
    label: 'Reciclado',
    color:
      'bg-[var(--color-primary-light)] text-[var(--color-primary-default)] dark:bg-[var(--color-primary-default)]/15'
  },
  {
    value: 'CLOSED',
    label: 'Fechado',
    color: 'bg-[var(--surface-sunken)] text-[var(--text-secondary)]'
  }
];

// Temperatura do lead - usando tokens do design system
export const leadRatingOptions = [
  {
    value: 'HOT',
    label: 'Quente',
    color: 'bg-[var(--lead-hot-bg)] text-[var(--lead-hot)] dark:bg-[var(--lead-hot)]/15'
  },
  {
    value: 'WARM',
    label: 'Morno',
    color: 'bg-[var(--lead-warm-bg)] text-[var(--lead-warm)] dark:bg-[var(--lead-warm)]/15'
  },
  {
    value: 'COLD',
    label: 'Frio',
    color: 'bg-[var(--lead-cold-bg)] text-[var(--lead-cold)] dark:bg-[var(--lead-cold)]/15'
  }
];

// Opções de prioridade - usando tokens do design system
export const priorityOptions = [
  {
    value: 'URGENT',
    label: 'Urgente',
    color:
      'bg-[var(--priority-urgent-bg)] text-[var(--priority-urgent)] dark:bg-[var(--priority-urgent)]/15'
  },
  {
    value: 'HIGH',
    label: 'Alta',
    color:
      'bg-[var(--priority-high-bg)] text-[var(--priority-high)] dark:bg-[var(--priority-high)]/15'
  },
  {
    value: 'NORMAL',
    label: 'Normal',
    color:
      'bg-[var(--priority-medium-bg)] text-[var(--priority-medium)] dark:bg-[var(--priority-medium)]/15'
  },
  {
    value: 'MEDIUM',
    label: 'Média',
    color:
      'bg-[var(--priority-medium-bg)] text-[var(--priority-medium)] dark:bg-[var(--priority-medium)]/15'
  },
  {
    value: 'LOW',
    label: 'Baixa',
    color: 'bg-[var(--priority-low-bg)] text-[var(--priority-low)] dark:bg-[var(--priority-low)]/15'
  }
];

// Opções de status de tarefa - usando tokens do design system
export const taskStatusOptions = [
  {
    value: 'NOT STARTED',
    label: 'Não Iniciada',
    color:
      'bg-[var(--task-upcoming-bg)] text-[var(--task-upcoming)] dark:bg-[var(--task-upcoming)]/15'
  },
  {
    value: 'IN PROGRESS',
    label: 'Em Andamento',
    color:
      'bg-[var(--task-due-today-bg)] text-[var(--task-due-today)] dark:bg-[var(--task-due-today)]/15'
  },
  {
    value: 'PENDING',
    label: 'Pendente',
    color:
      'bg-[var(--color-primary-light)] text-[var(--color-primary-default)] dark:bg-[var(--color-primary-default)]/15'
  },
  {
    value: 'COMPLETED',
    label: 'Concluída',
    color:
      'bg-[var(--task-completed-bg)] text-[var(--task-completed)] dark:bg-[var(--task-completed)]/15'
  },
  {
    value: 'DEFERRED',
    label: 'Adiada',
    color: 'bg-[var(--surface-sunken)] text-[var(--text-secondary)]'
  }
];

// Opções de status de chamado - usando tokens do design system
export const caseStatusOptions = [
  {
    value: 'New',
    label: 'Novo',
    color: 'bg-[var(--stage-new-bg)] text-[var(--stage-new)] dark:bg-[var(--stage-new)]/15'
  },
  {
    value: 'Assigned',
    label: 'Atribuído',
    color:
      'bg-[var(--stage-qualified-bg)] text-[var(--stage-qualified)] dark:bg-[var(--stage-qualified)]/15'
  },
  {
    value: 'Pending',
    label: 'Pendente',
    color:
      'bg-[var(--stage-negotiation-bg)] text-[var(--stage-negotiation)] dark:bg-[var(--stage-negotiation)]/15'
  },
  {
    value: 'Closed',
    label: 'Fechado',
    color: 'bg-[var(--surface-sunken)] text-[var(--text-secondary)]'
  },
  {
    value: 'Rejected',
    label: 'Rejeitado',
    color: 'bg-[var(--stage-lost-bg)] text-[var(--stage-lost)] dark:bg-[var(--stage-lost)]/15'
  },
  {
    value: 'Duplicate',
    label: 'Duplicado',
    color:
      'bg-[var(--color-primary-light)] text-[var(--color-primary-default)] dark:bg-[var(--color-primary-default)]/15'
  }
];

// Opções de tipo de chamado - usando tokens do design system
export const caseTypeOptions = [
  {
    value: 'Question',
    label: 'Dúvida',
    color:
      'bg-[var(--stage-qualified-bg)] text-[var(--stage-qualified)] dark:bg-[var(--stage-qualified)]/15'
  },
  {
    value: 'Incident',
    label: 'Incidente',
    color:
      'bg-[var(--color-primary-light)] text-[var(--color-primary-default)] dark:bg-[var(--color-primary-default)]/15'
  },
  {
    value: 'Problem',
    label: 'Problema',
    color: 'bg-[var(--stage-lost-bg)] text-[var(--stage-lost)] dark:bg-[var(--stage-lost)]/15'
  }
];

// Opções de prioridade de chamado - usando tokens do design system
export const casePriorityOptions = [
  {
    value: 'Low',
    label: 'Baixa',
    color: 'bg-[var(--priority-low-bg)] text-[var(--priority-low)] dark:bg-[var(--priority-low)]/15'
  },
  {
    value: 'Normal',
    label: 'Normal',
    color:
      'bg-[var(--priority-medium-bg)] text-[var(--priority-medium)] dark:bg-[var(--priority-medium)]/15'
  },
  {
    value: 'High',
    label: 'Alta',
    color:
      'bg-[var(--priority-high-bg)] text-[var(--priority-high)] dark:bg-[var(--priority-high)]/15'
  },
  {
    value: 'Urgent',
    label: 'Urgente',
    color:
      'bg-[var(--priority-urgent-bg)] text-[var(--priority-urgent)] dark:bg-[var(--priority-urgent)]/15'
  }
];

// Opções de status de empresa - usando tokens do design system
export const accountStatusOptions = [
  {
    value: 'ACTIVE',
    label: 'Ativa',
    color:
      'bg-[var(--color-success-light)] text-[var(--color-success-default)] dark:bg-[var(--color-success-default)]/15'
  },
  {
    value: 'INACTIVE',
    label: 'Inativa',
    color: 'bg-[var(--surface-sunken)] text-[var(--text-secondary)]'
  },
  {
    value: 'PENDING',
    label: 'Pendente',
    color:
      'bg-[var(--stage-negotiation-bg)] text-[var(--stage-negotiation)] dark:bg-[var(--stage-negotiation)]/15'
  }
];

// Opções de etapa de negócio - usando tokens do design system
export const opportunityStageOptions = [
  {
    value: 'PROSPECTING',
    label: 'Prospecção',
    color: 'bg-[var(--stage-new-bg)] text-[var(--stage-new)] dark:bg-[var(--stage-new)]/15'
  },
  {
    value: 'QUALIFICATION',
    label: 'Qualificação',
    color:
      'bg-[var(--stage-qualified-bg)] text-[var(--stage-qualified)] dark:bg-[var(--stage-qualified)]/15'
  },
  {
    value: 'PROPOSAL',
    label: 'Proposta',
    color:
      'bg-[var(--stage-proposal-bg)] text-[var(--stage-proposal)] dark:bg-[var(--stage-proposal)]/15'
  },
  {
    value: 'NEGOTIATION',
    label: 'Negociação',
    color:
      'bg-[var(--stage-negotiation-bg)] text-[var(--stage-negotiation)] dark:bg-[var(--stage-negotiation)]/15'
  },
  {
    value: 'CLOSED_WON',
    label: 'Ganho',
    color: 'bg-[var(--stage-won-bg)] text-[var(--stage-won)] dark:bg-[var(--stage-won)]/15'
  },
  {
    value: 'CLOSED_LOST',
    label: 'Perdido',
    color: 'bg-[var(--stage-lost-bg)] text-[var(--stage-lost)] dark:bg-[var(--stage-lost)]/15'
  }
];
