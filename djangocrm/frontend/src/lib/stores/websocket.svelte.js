/**
 * WebSocket store for real-time conversation updates.
 * Svelte 5 runes-based — auto-reconnect with exponential backoff.
 *
 * Usage:
 *   import { wsConnect, wsDisconnect, wsConnected, wsWatch, wsUnwatch, onWsMessage } from '$lib/stores/websocket.svelte.js';
 *   wsConnect();
 *   wsWatch(conversationId);
 *   const unsub = onWsMessage('new_message', (data) => { ... });
 */

import { getAccessToken } from '$lib/api.js';

// --- State ---
let connected = $state(false);
let consecutiveFailures = $state(0);

/** @type {WebSocket|null} */
let ws = null;
let reconnectTimer = null;
let heartbeatTimer = null;
let tokenRefreshTimer = null;

const MAX_FAILURES_BEFORE_FALLBACK = 3;
const HEARTBEAT_INTERVAL = 30_000; // 30s
const TOKEN_REFRESH_BEFORE_EXPIRY = 5 * 60_000; // 5min before expiry

/** @type {Map<string, Set<(data: any) => void>>} */
const listeners = new Map();

// --- Public API ---

export function wsConnect() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  const token = getAccessToken();
  if (!token) return;

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const url = `${protocol}//${host}/ws/conversations/?token=${encodeURIComponent(token)}`;

  try {
    ws = new WebSocket(url);
  } catch {
    _scheduleReconnect();
    return;
  }

  ws.onopen = () => {
    connected = true;
    consecutiveFailures = 0;
    _startHeartbeat();
    _scheduleTokenRefresh();
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      const type = msg.type;
      if (type && listeners.has(type)) {
        for (const cb of listeners.get(type)) {
          try { cb(msg.data); } catch { /* ignore listener errors */ }
        }
      }
    } catch { /* ignore parse errors */ }
  };

  ws.onclose = (event) => {
    connected = false;
    _stopHeartbeat();
    _stopTokenRefresh();

    if (event.code === 4401) {
      // Auth failure — don't reconnect automatically
      return;
    }

    consecutiveFailures++;
    if (consecutiveFailures < MAX_FAILURES_BEFORE_FALLBACK) {
      _scheduleReconnect();
    }
    // If max failures reached, polling fallback will take over
  };

  ws.onerror = () => {
    // onclose will fire after this
  };
}

export function wsDisconnect() {
  _stopHeartbeat();
  _stopTokenRefresh();
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (ws) {
    ws.onclose = null; // prevent reconnect
    ws.close();
    ws = null;
  }
  connected = false;
  consecutiveFailures = 0;
}

/**
 * Whether the WebSocket is connected.
 * Use in components: `if (wsConnected) { ... }`
 */
export function get wsConnected() {
  return connected;
}

/**
 * Whether polling should be used as fallback.
 * True when WS failed too many times consecutively.
 */
export function get wsShouldFallbackToPoll() {
  return consecutiveFailures >= MAX_FAILURES_BEFORE_FALLBACK;
}

/**
 * Watch a specific conversation for messages.
 * @param {string} conversationId
 */
export function wsWatch(conversationId) {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'watch', conversation_id: conversationId }));
  }
}

/**
 * Unwatch a conversation.
 * @param {string} conversationId
 */
export function wsUnwatch(conversationId) {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'unwatch', conversation_id: conversationId }));
  }
}

/**
 * Subscribe to a specific WS message type.
 * @param {string} type - e.g. 'new_message', 'conversation_update', 'typing'
 * @param {(data: any) => void} callback
 * @returns {() => void} Unsubscribe function
 */
export function onWsMessage(type, callback) {
  if (!listeners.has(type)) listeners.set(type, new Set());
  listeners.get(type).add(callback);
  return () => listeners.get(type)?.delete(callback);
}

// --- Internal ---

function _scheduleReconnect() {
  if (reconnectTimer) return;
  const delay = Math.min(1000 * Math.pow(2, consecutiveFailures), 30_000);
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    wsConnect();
  }, delay);
}

function _startHeartbeat() {
  _stopHeartbeat();
  heartbeatTimer = setInterval(() => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'ping' }));
    }
  }, HEARTBEAT_INTERVAL);
}

function _stopHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
}

function _scheduleTokenRefresh() {
  _stopTokenRefresh();
  // Refresh token 5min before JWT expires (default 1h lifetime → refresh at 55min)
  tokenRefreshTimer = setTimeout(() => {
    if (ws?.readyState === WebSocket.OPEN) {
      const token = getAccessToken();
      if (token) {
        ws.send(JSON.stringify({ type: 'refresh_token', token }));
      }
    }
    _scheduleTokenRefresh(); // Schedule next refresh
  }, 55 * 60_000); // 55 minutes
}

function _stopTokenRefresh() {
  if (tokenRefreshTimer) {
    clearTimeout(tokenRefreshTimer);
    tokenRefreshTimer = null;
  }
}
