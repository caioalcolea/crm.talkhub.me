import { redirect } from '@sveltejs/kit';

/** @type {import('./$types').PageServerLoad} */
export async function load({ params }) {
  throw redirect(301, `/autopilot?tab=campaigns&campaign_id=${params.id}`);
}
