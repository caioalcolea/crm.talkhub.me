/**
 * API Client for Django REST Framework Backend
 *
 * This module provides a centralized API client for making requests to the Django backend.
 * It handles JWT authentication, organization context, and common API patterns.
 *
 * @module lib/api
 */

import { env } from '$env/dynamic/public';
import { goto } from '$app/navigation';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// API Base URL from environment variables
// Note: VITE_ prefix is required for client-side env vars
const API_BASE_URL = env.PUBLIC_DJANGO_API_URL
  ? `${env.PUBLIC_DJANGO_API_URL}/api`
  : 'http://localhost:8000/api';

/**
 * Storage keys for non-sensitive data only
 */
const STORAGE_KEYS = {
  ORG_ID: 'org_id',
  USER: 'user'
};

/**
 * In-memory token storage (not persisted to localStorage to avoid XSS exposure)
 */
let _accessToken = null;
let _refreshToken = null;

/**
 * Get token from localStorage (client-side) or return null (server-side)
 * @param {string} key - Storage key
 * @returns {string|null}
 */
function getFromStorage(key) {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(key);
}

/**
 * Set token in localStorage (client-side only)
 * @param {string} key - Storage key
 * @param {string} value - Value to store
 */
function setInStorage(key, value) {
  if (typeof window !== 'undefined') {
    localStorage.setItem(key, value);
  }
}

/**
 * Remove token from localStorage (client-side only)
 * @param {string} key - Storage key
 */
function removeFromStorage(key) {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(key);
  }
}

/**
 * Clear all auth data from storage and memory
 */
export function clearAuthData() {
  _accessToken = null;
  _refreshToken = null;
  removeFromStorage(STORAGE_KEYS.ORG_ID);
  removeFromStorage(STORAGE_KEYS.USER);
}

/**
 * Get current access token
 * @returns {string|null}
 */
export function getAccessToken() {
  return _accessToken;
}

/**
 * Get current refresh token
 * @returns {string|null}
 */
export function getRefreshToken() {
  return _refreshToken;
}

/**
 * Get current organization ID
 * @returns {string|null}
 */
export function getOrgId() {
  return getFromStorage(STORAGE_KEYS.ORG_ID);
}

/**
 * Set organization ID
 * @param {string} orgId - Organization UUID
 */
export function setOrgId(orgId) {
  setInStorage(STORAGE_KEYS.ORG_ID, orgId);
}

/**
 * Initialize client-side auth from server-provided token.
 * Called by the root layout to bridge httpOnly cookies → in-memory storage.
 * @param {string|null} accessToken - JWT access token from server layout data
 */
export function initClientAuth(accessToken) {
  if (accessToken) {
    _accessToken = accessToken;
  }
}

/**
 * Get current user data
 * @returns {Object|null}
 */
export function getCurrentUser() {
  const userData = getFromStorage(STORAGE_KEYS.USER);
  return userData ? JSON.parse(userData) : null;
}

/**
 * Refresh the access token using refresh token
 * @returns {Promise<string|null>} New access token or null if refresh failed
 */
async function refreshAccessToken() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    return null;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh-token/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ refresh: refreshToken })
    });

    if (response.ok) {
      const data = await response.json();
      _accessToken = data.access;
      return data.access;
    }

    // Refresh token expired or invalid
    clearAuthData();
    if (typeof window !== 'undefined') {
      goto('/login');
    }
    return null;
  } catch (error) {
    console.error('Token refresh failed:', error);
    clearAuthData();
    return null;
  }
}

/**
 * Make an authenticated API request
 *
 * @param {string} endpoint - API endpoint (e.g., '/accounts/', '/leads/123/')
 * @param {{ method?: string, body?: Record<string, unknown> | null, headers?: Record<string, string>, requiresAuth?: boolean }} [options] - Fetch options
 * @returns {Promise<any>} Response data
 * @throws {Error} If request fails
 */
export async function apiRequest(endpoint, options = {}) {
  const { method = 'GET', body = null, headers = {}, requiresAuth = true } = options;

  const url = `${API_BASE_URL}${endpoint}`;

  // Build headers
  /** @type {Record<string, string>} */
  const requestHeaders = {
    'Content-Type': 'application/json',
    ...headers
  };

  // Add authentication if required
  // Note: Organization context is now embedded in JWT token, not sent as header
  if (requiresAuth) {
    const accessToken = getAccessToken();
    if (accessToken) {
      requestHeaders['Authorization'] = `Bearer ${accessToken}`;
    }
  }

  // Build fetch options
  /** @type {RequestInit} */
  const fetchOptions = {
    method,
    headers: requestHeaders
  };

  if (body && method !== 'GET') {
    fetchOptions.body = JSON.stringify(body);
  }

  try {
    let response = await fetch(url, fetchOptions);

    // If unauthorized and we have a refresh token, try to refresh
    if (response.status === 401 && requiresAuth) {
      const newAccessToken = await refreshAccessToken();
      if (newAccessToken) {
        // Retry request with new token
        requestHeaders['Authorization'] = `Bearer ${newAccessToken}`;
        fetchOptions.headers = requestHeaders;
        response = await fetch(url, fetchOptions);
      }
    }

    // Handle response
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

      if (errorData.detail) {
        errorMessage = errorData.detail;
      } else if (errorData.error && typeof errorData.error === 'string') {
        errorMessage = errorData.error;
      } else if (errorData.errors && typeof errorData.errors === 'object') {
        const fieldErrors = Object.entries(errorData.errors)
          .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`)
          .join('; ');
        errorMessage = fieldErrors || errorMessage;
      } else if (errorData.non_field_errors) {
        errorMessage = Array.isArray(errorData.non_field_errors)
          ? errorData.non_field_errors.join(', ')
          : errorData.non_field_errors;
      }

      throw new Error(errorMessage);
    }

    // Return JSON response
    return await response.json();
  } catch (error) {
    console.error(`API request failed: ${method} ${endpoint}`, error);
    throw error;
  }
}

/**
 * Authentication API methods
 */
export const auth = {
  /**
   * Switch to a different organization
   * This issues new JWT tokens with the new org context
   * @param {string} orgId - Organization UUID to switch to
   * @returns {Promise<any>} New tokens and org data
   */
  async switchOrg(orgId) {
    if (!orgId || !UUID_RE.test(orgId)) {
      throw new Error('Invalid organization ID format');
    }
    /** @type {any} */
    const data = await apiRequest('/auth/switch-org/', {
      method: 'POST',
      body: { org_id: orgId }
    });

    // Update tokens in memory (not localStorage) and org context
    _accessToken = data.access_token;
    _refreshToken = data.refresh_token;
    setInStorage(STORAGE_KEYS.ORG_ID, data.current_org.id);

    return data;
  },

  /**
   * Get current user data
   * @returns {Promise<Object>} Current user with organizations
   */
  async me() {
    const data = await apiRequest('/auth/me/');

    // Update stored user data
    setInStorage(STORAGE_KEYS.USER, JSON.stringify(data));

    return data;
  },

  /**
   * Get profile for current organization
   * @returns {Promise<Object>} Profile data for current org
   */
  async profile() {
    return await apiRequest('/auth/profile/');
  },

  /**
   * Logout (clear local data)
   * Note: Django simplejwt doesn't have server-side logout by default
   * Token blacklisting can be added later if needed
   */
  logout() {
    clearAuthData();
    if (typeof window !== 'undefined') {
      goto('/login');
    }
  }
};

/**
 * Generic CRUD API factory
 * Creates standard CRUD methods for an entity
 *
 * @param {string} entityPath - Entity path (e.g., 'accounts', 'leads')
 * @returns {Object} CRUD methods
 */
function createCrudApi(entityPath) {
  return {
    /**
     * List entities with pagination and filters
     * @param {Record<string, string>} [params] - Query parameters
     * @returns {Promise<any>} Paginated list of entities
     */
    async list(params = {}) {
      const queryString = new URLSearchParams(params).toString();
      const endpoint = `/${entityPath}/${queryString ? `?${queryString}` : ''}`;
      return await apiRequest(endpoint);
    },

    /**
     * Get a single entity by ID
     * @param {string} id - Entity UUID
     * @returns {Promise<any>} Entity data
     */
    async get(id) {
      return await apiRequest(`/${entityPath}/${id}/`);
    },

    /**
     * Create a new entity
     * @param {Record<string, unknown>} data - Entity data
     * @returns {Promise<any>} Created entity
     */
    async create(data) {
      return await apiRequest(`/${entityPath}/`, {
        method: 'POST',
        body: data
      });
    },

    /**
     * Update an entity
     * @param {string} id - Entity UUID
     * @param {Record<string, unknown>} data - Updated entity data
     * @returns {Promise<any>} Updated entity
     */
    async update(id, data) {
      return await apiRequest(`/${entityPath}/${id}/`, {
        method: 'PUT',
        body: data
      });
    },

    /**
     * Partially update an entity
     * @param {string} id - Entity UUID
     * @param {Record<string, unknown>} data - Partial entity data
     * @returns {Promise<any>} Updated entity
     */
    async patch(id, data) {
      return await apiRequest(`/${entityPath}/${id}/`, {
        method: 'PATCH',
        body: data
      });
    },

    /**
     * Delete an entity
     * @param {string} id - Entity UUID
     * @returns {Promise<any>}
     */
    async delete(id) {
      return await apiRequest(`/${entityPath}/${id}/`, {
        method: 'DELETE'
      });
    },

    /**
     * Get comments for an entity
     * @param {string} id - Entity UUID
     * @returns {Promise<any>} List of comments
     */
    async getComments(id) {
      return await apiRequest(`/${entityPath}/comment/${id}/`);
    },

    /**
     * Add comment to an entity
     * @param {string} id - Entity UUID
     * @param {string} comment - Comment text
     * @returns {Promise<any>} Created comment
     */
    async addComment(id, comment) {
      return await apiRequest(`/${entityPath}/comment/${id}/`, {
        method: 'POST',
        body: { comment }
      });
    },

    /**
     * Delete a comment
     * @param {string} commentId - Comment UUID
     * @returns {Promise<any>} Response
     */
    async deleteComment(commentId) {
      return await apiRequest(`/${entityPath}/comment/${commentId}/`, {
        method: 'DELETE'
      });
    },

    /**
     * Get attachments for an entity
     * @param {string} id - Entity UUID
     * @returns {Promise<any>} List of attachments
     */
    async getAttachments(id) {
      return await apiRequest(`/${entityPath}/attachment/${id}/`);
    }
  };
}

/**
 * CRM Entity APIs
 */
export const accounts = createCrudApi('accounts');
export const leads = createCrudApi('leads');
export const contacts = createCrudApi('contacts');
export const opportunities = createCrudApi('opportunity');
export const cases = createCrudApi('cases');
export const tasks = createCrudApi('tasks');
export const events = createCrudApi('events');
export const invoices = createCrudApi('invoices');

/**
 * Financeiro Module API
 */
export const financeiro = {
  // Lancamentos CRUD
  lancamentos: createCrudApi('financeiro/lancamentos'),

  // Parcelas (GET + PATCH only)
  parcelas: createCrudApi('financeiro/parcelas'),

  // Plano de Contas
  planoGrupos: createCrudApi('financeiro/plano-de-contas/grupos'),
  planoContas: createCrudApi('financeiro/plano-de-contas'),

  // Formas de Pagamento
  formasPagamento: createCrudApi('financeiro/formas-pagamento'),

  // Actions
  async cancelLancamento(id) {
    return apiRequest(`/financeiro/lancamentos/${id}/cancel/`, { method: 'POST' });
  },
  async getLancamentoParcelas(id) {
    return apiRequest(`/financeiro/lancamentos/${id}/parcelas/`);
  },
  async payParcela(id, data = {}) {
    return apiRequest(`/financeiro/parcelas/${id}/pay/`, { method: 'POST', body: data });
  },
  async cancelParcela(id) {
    return apiRequest(`/financeiro/parcelas/${id}/cancel/`, { method: 'POST' });
  },
  async bulkPayParcelas(parcelaIds, dataPagamento) {
    return apiRequest('/financeiro/parcelas/bulk-pay/', {
      method: 'POST',
      body: { parcela_ids: parcelaIds, ...(dataPagamento ? { data_pagamento: dataPagamento } : {}) }
    });
  },

  // Reports
  async dashboard(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return apiRequest(`/financeiro/reports/dashboard/${qs ? `?${qs}` : ''}`);
  },
  async fluxoPlanoContas(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return apiRequest(`/financeiro/reports/fluxo-plano-contas/${qs ? `?${qs}` : ''}`);
  },
  async relatorioMensal(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return apiRequest(`/financeiro/reports/relatorio-mensal/${qs ? `?${qs}` : ''}`);
  },
  async entityReport(entityId, entityType) {
    return apiRequest(`/financeiro/reports/by-entity/${entityId}/?entity_type=${entityType}`);
  },

  // Form options
  async formOptions() {
    return apiRequest('/financeiro/form-options/');
  },

  // Reminders (per lancamento)
  async getLancamentoReminders(id) {
    return apiRequest(`/financeiro/lancamentos/${id}/reminders/`);
  },
  async createLancamentoReminder(id, data) {
    return apiRequest(`/financeiro/lancamentos/${id}/reminders/`, { method: 'POST', body: data });
  },
};

/**
 * Autopilot Assistant API
 */
export const assistant = {
  reminderPolicies: createCrudApi('assistant/reminder-policies'),

  async activatePolicy(id) {
    return apiRequest(`/assistant/reminder-policies/${id}/activate/`, { method: 'PATCH' });
  },
  async deactivatePolicy(id) {
    return apiRequest(`/assistant/reminder-policies/${id}/deactivate/`, { method: 'PATCH' });
  },
  async scheduledJobs(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return apiRequest(`/assistant/scheduled-jobs/${qs ? `?${qs}` : ''}`);
  },
  async retryJob(id) {
    return apiRequest(`/assistant/scheduled-jobs/${id}/retry/`, { method: 'POST' });
  },
  async cancelJob(id) {
    return apiRequest(`/assistant/scheduled-jobs/${id}/cancel/`, { method: 'POST' });
  },
  async approveJob(id) {
    return apiRequest(`/assistant/scheduled-jobs/${id}/approve/`, { method: 'POST' });
  },
  async runs(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return apiRequest(`/assistant/runs/${qs ? `?${qs}` : ''}`);
  },
  async presets(module = '') {
    const qs = module ? `?module=${module}` : '';
    return apiRequest(`/assistant/presets/${qs}`);
  },
  async getReminders(targetType, targetId) {
    return apiRequest(`/assistant/reminders-for/${targetType}/${targetId}/`);
  },
  async createReminder(targetType, targetId, body) {
    return apiRequest(`/assistant/reminders-for/${targetType}/${targetId}/`, { method: 'POST', body });
  },
  templates: createCrudApi('assistant/templates'),
  async taskLinks(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return apiRequest(`/assistant/task-links/${qs ? `?${qs}` : ''}`);
  },
  async entityJobs(targetType, targetId, params = {}) {
    const qs = new URLSearchParams({ target_type: targetType, target_id: targetId, ...params }).toString();
    return apiRequest(`/assistant/scheduled-jobs/?${qs}`);
  },
  async aiGenerate(body) {
    return apiRequest('/assistant/ai/generate/', { method: 'POST', body });
  },
};

/**
 * Salesforce Integration API
 */
export const salesforce = {
  async status() {
    return apiRequest('/salesforce/status/');
  },
  async connect() {
    return apiRequest('/salesforce/connect/', { method: 'POST' });
  },
  async callback(code) {
    return apiRequest('/salesforce/callback/', {
      method: 'POST',
      body: { code }
    });
  },
  async disconnect() {
    return apiRequest('/salesforce/disconnect/', { method: 'DELETE' });
  },
  async startImport(objectTypes) {
    return apiRequest('/salesforce/import/', {
      method: 'POST',
      body: { object_types: objectTypes }
    });
  },
  async getImportJob(jobId) {
    return apiRequest(`/salesforce/import/${jobId}/`);
  },
  async importHistory() {
    return apiRequest('/salesforce/import/history/');
  }
};

/**
 * TalkHub Omni Integration API
 */
export const talkhubOmni = {
  // Module 1 — Connection
  async status() {
    return apiRequest('/talkhub/status/');
  },
  async saveCredentials(data) {
    return apiRequest('/talkhub/credentials/', { method: 'POST', body: data });
  },
  async connect() {
    return apiRequest('/talkhub/connect/', { method: 'POST' });
  },
  async disconnect() {
    return apiRequest('/talkhub/disconnect/', { method: 'DELETE' });
  },

  // Module 2 — Contacts
  async syncContacts() {
    return apiRequest('/talkhub/sync/contacts/', { method: 'POST' });
  },
  async getSyncJob(jobId) {
    return apiRequest(`/talkhub/sync/contacts/${jobId}/`);
  },
  async pushContact(id) {
    return apiRequest(`/talkhub/contacts/${id}/push/`, { method: 'POST' });
  },
  async createAndPush(data) {
    return apiRequest('/talkhub/contacts/create-and-push/', { method: 'POST', body: data });
  },
  async chatHistory(id) {
    return apiRequest(`/talkhub/contacts/${id}/chat-history/`);
  },

  // Module 3 — Tags
  async addTag(id, data) {
    return apiRequest(`/talkhub/contacts/${id}/tags/add/`, { method: 'POST', body: data });
  },
  async removeTag(id, data) {
    return apiRequest(`/talkhub/contacts/${id}/tags/remove/`, { method: 'DELETE', body: data });
  },
  async addLabel(id, data) {
    return apiRequest(`/talkhub/contacts/${id}/labels/add/`, { method: 'POST', body: data });
  },
  async removeLabel(id, data) {
    return apiRequest(`/talkhub/contacts/${id}/labels/remove/`, { method: 'DELETE', body: data });
  },

  // Module 4 — Kanban
  async syncKanbans() {
    return apiRequest('/talkhub/sync/kanbans/', { method: 'POST' });
  },
  async getKanbanSyncJob(jobId) {
    return apiRequest(`/talkhub/sync/kanbans/${jobId}/`);
  },
  async syncCards(boardId) {
    return apiRequest(`/talkhub/kanbans/${boardId}/sync-cards/`, { method: 'POST' });
  },
  async createCard(boardId, data) {
    return apiRequest(`/talkhub/kanbans/${boardId}/cards/`, { method: 'POST', body: data });
  },
  async updateCard(boardId, cardId, data) {
    return apiRequest(`/talkhub/kanbans/${boardId}/cards/${cardId}/`, { method: 'PUT', body: data });
  },
  async deleteCard(boardId, cardId) {
    return apiRequest(`/talkhub/kanbans/${boardId}/cards/${cardId}/delete/`, { method: 'DELETE' });
  },
  async boardFields(boardId) {
    return apiRequest(`/talkhub/kanbans/${boardId}/fields/`);
  },
  async boardLog(boardId) {
    return apiRequest(`/talkhub/kanbans/${boardId}/log/`);
  },

  // Module 5 — Users
  async syncUsers() {
    return apiRequest('/talkhub/sync/users/', { method: 'POST' });
  },
  async getUserSyncJob(jobId) {
    return apiRequest(`/talkhub/sync/users/${jobId}/`);
  },
  async assignAgent(id, data) {
    return apiRequest(`/talkhub/contacts/${id}/assign-agent/`, { method: 'POST', body: data });
  },
  async unassignAgent(id) {
    return apiRequest(`/talkhub/contacts/${id}/unassign-agent/`, { method: 'POST' });
  },
  async assignGroup(id, data) {
    return apiRequest(`/talkhub/contacts/${id}/assign-group/`, { method: 'POST', body: data });
  },

  // Module 6 — AI Agents
  async syncAIAgents() {
    return apiRequest('/talkhub/sync/ai-agents/', { method: 'POST' });
  },
  async updateAIModel(id, data) {
    return apiRequest(`/talkhub/ai-agents/${id}/update-model/`, { method: 'POST', body: data });
  },

  // Module 7 — Analytics
  async flowSummary(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return apiRequest(`/talkhub/analytics/flow-summary/${qs ? `?${qs}` : ''}`);
  },
  async agentSummary(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return apiRequest(`/talkhub/analytics/agent-summary/${qs ? `?${qs}` : ''}`);
  },

  // Module 8 — Bot Control
  async pauseBot(id) {
    return apiRequest(`/talkhub/contacts/${id}/pause-bot/`, { method: 'POST' });
  },
  async resumeBot(id) {
    return apiRequest(`/talkhub/contacts/${id}/resume-bot/`, { method: 'POST' });
  },
  async logEvent(id, data) {
    return apiRequest(`/talkhub/contacts/${id}/log-event/`, { method: 'POST', body: data });
  },
  async updateUserFields(id, data) {
    return apiRequest(`/talkhub/contacts/${id}/user-fields/`, { method: 'PUT', body: data });
  },

  // Module 9 — Channels & Workspace
  async channels() {
    return apiRequest('/talkhub/channels/');
  },
  async flows() {
    return apiRequest('/talkhub/flows/');
  },
  async workspace() {
    return apiRequest('/talkhub/workspace/');
  },

  // General
  async syncHistory(type) {
    const qs = type ? `?type=${type}` : '';
    return apiRequest(`/talkhub/sync/history/${qs}`);
  },
  async syncAll() {
    return apiRequest('/talkhub/sync/all/', { method: 'POST' });
  },
};

/**
 * Automations API
 */
export const automations = createCrudApi('automations');

/**
 * Campaigns API
 */
export const campaigns = {
  ...createCrudApi('campaigns'),

  async previewAudience(id, filterCriteria) {
    return apiRequest(`/campaigns/${id}/audience/preview/`, { method: 'POST', body: { filter_criteria: filterCriteria } });
  },
  async generateAudience(id, filterCriteria, name) {
    return apiRequest(`/campaigns/${id}/audience/generate/`, { method: 'POST', body: { filter_criteria: filterCriteria, name } });
  },
  async schedule(id, scheduledAt) {
    return apiRequest(`/campaigns/${id}/schedule/`, { method: 'POST', body: { scheduled_at: scheduledAt } });
  },
  async pauseResume(id, action) {
    return apiRequest(`/campaigns/${id}/pause-resume/`, { method: 'POST', body: { action } });
  },
  async analytics(id) {
    return apiRequest(`/campaigns/${id}/analytics/`);
  },
  async recipients(id, params = {}) {
    const qs = new URLSearchParams(params).toString();
    return apiRequest(`/campaigns/${id}/recipients/${qs ? '?' + qs : ''}`);
  },
  async createStep(id, step) {
    return apiRequest(`/campaigns/${id}/steps/`, { method: 'POST', body: step });
  },
};

/**
 * Export all as default
 */
export default {
  auth,
  accounts,
  leads,
  contacts,
  opportunities,
  cases,
  tasks,
  events,
  invoices,
  financeiro,
  automations,
  campaigns,
  salesforce,
  talkhubOmni,
  apiRequest,
  getAccessToken,
  getRefreshToken,
  getOrgId,
  setOrgId,
  getCurrentUser,
  clearAuthData
};
