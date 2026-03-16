/**
 * Notification store — Svelte 5 runes.
 *
 * Polls unread count every 10s (lightweight GET).
 * Full notification list loaded on demand (popover open).
 */

import { browser } from '$app/environment';
import { assistant } from '$lib/api.js';

let notifications = $state([]);
let unreadCount = $state(0);
let isLoading = $state(false);
let _pollTimer = null;

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
  try {
    const res = await assistant.unreadCount();
    if (res && typeof res.count === 'number') {
      unreadCount = res.count;
    }
  } catch {
    // Silently ignore polling errors
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
