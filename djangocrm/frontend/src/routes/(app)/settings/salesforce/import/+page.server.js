import { redirect } from '@sveltejs/kit';

/** @type {import('./$types').PageServerLoad} */
export async function load() {
  // Salesforce integration not yet implemented — redirect back
  redirect(302, '/settings/salesforce');
}
