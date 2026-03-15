/**
 * Logout — clears JWT cookies and redirects to /login.
 *
 * Traefik routes /logout to the SvelteKit frontend (catch-all priority 10).
 * This server load function runs before any page render, clears auth state,
 * and immediately redirects — no +page.svelte needed because we always throw.
 */

import { redirect } from '@sveltejs/kit';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies }) {
  // Clear all authentication-related cookies
  const cookiesToClear = ['jwt_access', 'jwt_refresh', 'org', 'oauth_state', 'oauth_code_verifier', 'invite_token', 'invite_org_id'];

  for (const cookieName of cookiesToClear) {
    cookies.delete(cookieName, { path: '/' });
  }

  // Redirect to login page
  redirect(303, '/login');
}
