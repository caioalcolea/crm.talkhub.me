/**
 * Assistant Chat Store — Svelte 5 runes
 *
 * Manages the global state of the AI assistant chat drawer:
 * - Open/close state
 * - Current session and messages
 * - Sending state and error handling
 * - Session list for history
 */

import { assistant } from '$lib/api.js';

// ── State ───────────────────────────────────────────────────────────

let isOpen = $state(false);
let isLoading = $state(false);
let isSending = $state(false);
let error = $state(null);

let currentSessionId = $state(null);
let messages = $state([]);
let proposedActions = $state([]);
let sessionList = $state([]);

let pageContext = $state({});

// ── Actions ─────────────────────────────────────────────────────────

function open() {
  isOpen = true;
}

function close() {
  isOpen = false;
}

function toggle() {
  isOpen = !isOpen;
}

function setPageContext(ctx) {
  pageContext = ctx || {};
}

async function loadSessions() {
  try {
    const data = await assistant.sessions();
    sessionList = Array.isArray(data) ? data : [];
  } catch (e) {
    console.error('Failed to load sessions:', e);
  }
}

async function loadSession(sessionId) {
  isLoading = true;
  error = null;
  try {
    const data = await assistant.session(sessionId);
    currentSessionId = data.id;
    messages = data.messages || [];
    proposedActions = [];
  } catch (e) {
    error = 'Erro ao carregar sessão.';
  } finally {
    isLoading = false;
  }
}

function startNewSession() {
  currentSessionId = null;
  messages = [];
  proposedActions = [];
  error = null;
}

async function sendMessage(text) {
  if (!text.trim() || isSending) return;

  isSending = true;
  error = null;

  // Optimistic: add user message
  messages = [...messages, {
    id: crypto.randomUUID(),
    role: 'user',
    content: text,
    created_at: new Date().toISOString(),
    metadata: {},
  }];

  try {
    const data = await assistant.chat({
      session_id: currentSessionId,
      message: text,
      context: pageContext,
    });

    currentSessionId = data.session_id;
    proposedActions = data.proposed_actions || [];

    // Add assistant message
    messages = [...messages, {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: data.response,
      created_at: new Date().toISOString(),
      metadata: { proposed_actions: proposedActions, status: data.status },
    }];

    // Update session title in list
    loadSessions();

    return data;
  } catch (e) {
    const errMsg = e?.response?.data?.response || e?.message || 'Erro ao enviar mensagem.';
    error = errMsg;

    // Add error message
    messages = [...messages, {
      id: crypto.randomUUID(),
      role: 'system',
      content: errMsg,
      created_at: new Date().toISOString(),
      metadata: { error: true },
    }];
  } finally {
    isSending = false;
  }
}

async function confirmAction(actionIndex, decision) {
  if (!currentSessionId || isSending) return;

  isSending = true;
  error = null;

  try {
    const data = await assistant.chatConfirm({
      session_id: currentSessionId,
      action_index: actionIndex,
      decision,
    });

    // Add result message
    const resultText = decision === 'apply'
      ? `Ação executada: ${data.message}`
      : `Ação cancelada: ${data.message}`;

    messages = [...messages, {
      id: crypto.randomUUID(),
      role: 'tool_result',
      content: resultText,
      created_at: new Date().toISOString(),
      metadata: { result: data.result, data: data.data },
    }];

    // Clear proposed actions after handling
    proposedActions = proposedActions.filter((_, i) => i !== actionIndex);

    return data;
  } catch (e) {
    error = e?.message || 'Erro ao confirmar ação.';
  } finally {
    isSending = false;
  }
}

async function archiveSession(sessionId) {
  try {
    await assistant.archiveSession(sessionId);
    sessionList = sessionList.filter(s => s.id !== sessionId);
    if (currentSessionId === sessionId) {
      startNewSession();
    }
  } catch (e) {
    console.error('Failed to archive session:', e);
  }
}

// ── Exported store ──────────────────────────────────────────────────

export const assistantChat = {
  get isOpen() { return isOpen; },
  get isLoading() { return isLoading; },
  get isSending() { return isSending; },
  get error() { return error; },
  get currentSessionId() { return currentSessionId; },
  get messages() { return messages; },
  get proposedActions() { return proposedActions; },
  get sessionList() { return sessionList; },
  get pageContext() { return pageContext; },

  open,
  close,
  toggle,
  setPageContext,
  loadSessions,
  loadSession,
  startNewSession,
  sendMessage,
  confirmAction,
  archiveSession,
};
