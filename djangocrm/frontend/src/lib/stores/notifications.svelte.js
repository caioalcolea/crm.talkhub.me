/**
 * Notification store — Svelte 5 runes.
 *
 * Polls unread count every 10s (lightweight GET).
 * Full notification list loaded on demand (popover open).
 */

import { browser } from '$app/environment';
import { assistant, getAccessToken } from '$lib/api.js';

let notifications = $state([]);
let unreadCount = $state(0);
let isLoading = $state(false);
let _pollTimer = null;
let _consecutiveErrors = 0;
const MAX_CONSECUTIVE_ERRORS = 3;

async function loadNotifications(params = {}) {
  if (!browser) return;
  isLoading = true;
  try {
    const res = await assistant.notifications(params);
    if (Array.isArray(res)) {
      notifications = res;
    }
  } catch (e) {
    console.error('Failed to load notifications:', e);
  } finally {
    isLoading = false;
  }
}

async function pollUnreadCount() {
  if (!browser) return;
  // Skip if JWT not yet initialized (avoids 401 on first mount)
  if (!getAccessToken()) return;
  try {
    const res = await assistant.unreadCount();
    if (res && typeof res.count === 'number') {
      unreadCount = res.count;
    }
    _consecutiveErrors = 0;
  } catch (e) {
    _consecutiveErrors++;
    // Stop polling on auth errors or repeated failures
    const status = e?.status || e?.response?.status;
    if (status === 401 || status === 403 || _consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
      stopPolling();
    }
  }
}

async function markAsRead(id) {
  try {
    await assistant.markRead(id);
    const idx = notifications.findIndex(n => n.id === id);
    if (idx >= 0) {
      notifications[idx] = { ...notifications[idx], read_at: new Date().toISOString() };
      notifications = [...notifications];
    }
    if (unreadCount > 0) unreadCount--;
  } catch (e) {
    console.error('Failed to mark notification as read:', e);
  }
}

async function markAllRead() {
  try {
    await assistant.markAllRead();
    notifications = notifications.map(n => ({ ...n, read_at: n.read_at || new Date().toISOString() }));
    unreadCount = 0;
  } catch (e) {
    console.error('Failed to mark all as read:', e);
  }
}

function startPolling() {
  if (_pollTimer || !browser) return;
  _consecutiveErrors = 0;
  pollUnreadCount();
  _pollTimer = setInterval(pollUnreadCount, 10_000);
}

function stopPolling() {
  if (_pollTimer) {
    clearInterval(_pollTimer);
    _pollTimer = null;
  }
}

export const notificationStore = {
  get notifications() { return notifications; },
  get unreadCount() { return unreadCount; },
  get isLoading() { return isLoading; },
  loadNotifications,
  pollUnreadCount,
  markAsRead,
  markAllRead,
  startPolling,
  stopPolling,
};
