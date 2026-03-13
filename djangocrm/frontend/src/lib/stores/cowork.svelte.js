/**
 * Cowork session store — global state for the virtual office.
 * Svelte 5 runes-based. Persists across route navigations so the
 * iframe stays alive when the user browses other CRM pages (PiP mode).
 *
 * Usage:
 *   import { coworkSession, startCoworkSession, endCoworkSession, setCoworkMode } from '$lib/stores/cowork.svelte.js';
 */

const COWORK_APP_URL = '/cowork-app/';

// --- State ---

/** @type {'hidden'|'full'|'pip'|'fullscreen'} */
let mode = $state('hidden');
let active = $state(false);
/** @type {string|null} */
let token = $state(null);
/** @type {{ id: string, name: string, max_participants?: number }|null} */
let room = $state(null);
let displayName = $state('');
let isGuest = $state(false);
let iframeReady = $state(false);
/** @type {HTMLElement|null} Target element the iframe should overlay in "full" mode */
let fullTarget = $state(null);

// --- Derived (read-only accessors) ---

export const coworkSession = {
  get active() { return active; },
  get mode() { return mode; },
  get token() { return token; },
  get room() { return room; },
  get displayName() { return displayName; },
  get isGuest() { return isGuest; },
  get iframeReady() { return iframeReady; },
  get fullTarget() { return fullTarget; },
  get appUrl() { return COWORK_APP_URL; },
  get socketUrl() {
    return typeof window !== 'undefined'
      ? `${window.location.origin}/cowork-ws`
      : '/cowork-ws';
  }
};

// --- Public API ---

/**
 * Start a cowork session. Called when user enters a room.
 * @param {string} sessionToken - JWT token for cowork auth
 * @param {{ id: string, name: string, max_participants?: number }} sessionRoom
 * @param {string} name - Display name
 * @param {boolean} [guest=false]
 */
export function startCoworkSession(sessionToken, sessionRoom, name, guest = false) {
  token = sessionToken;
  room = sessionRoom;
  displayName = name;
  isGuest = guest;
  active = true;
  iframeReady = false;
  mode = 'full';
}

/** End the cowork session. Cleans up all state. */
export function endCoworkSession() {
  active = false;
  token = null;
  room = null;
  displayName = '';
  isGuest = false;
  iframeReady = false;
  mode = 'hidden';
}

/**
 * Change display mode.
 * @param {'full'|'pip'|'fullscreen'} newMode
 */
export function setCoworkMode(newMode) {
  if (!active) return;
  mode = newMode;
}

/** Mark iframe as ready (called by CoworkPiP on postMessage). */
export function setIframeReady(ready) {
  iframeReady = ready;
}

/**
 * Register the target element for "full" mode overlay.
 * The CoworkPiP will position itself over this element using fixed positioning.
 * @param {HTMLElement|null} el
 */
export function registerFullTarget(el) {
  fullTarget = el;
}

/** Unregister the full target (called on page destroy). */
export function unregisterFullTarget() {
  fullTarget = null;
}
