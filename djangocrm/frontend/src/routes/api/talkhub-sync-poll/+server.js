import { apiRequest } from '$lib/api-helpers.js';
import { json } from '@sveltejs/kit';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** @type {import('./$types').RequestHandler} */
export async function GET({ url, cookies }) {
  const jobId = url.searchParams.get('job');
  const syncType = url.searchParams.get('type');

  if (jobId && !UUID_RE.test(jobId)) {
    return json({ job: null, jobs: [] }, { status: 400 });
  }

  const [jobSettled, historySettled] = await Promise.allSettled([
    jobId
      ? apiRequest(`/talkhub/sync/jobs/${jobId}/`, {}, { cookies })
      : Promise.resolve(null),
    apiRequest(`/talkhub/sync/history/${syncType ? `?type=${syncType}` : ''}`, {}, { cookies })
  ]);

  const jobResult = jobSettled.status === 'fulfilled' ? jobSettled.value : null;
  const historyResult = historySettled.status === 'fulfilled' ? historySettled.value : null;

  return json({
    job: jobResult?.job || jobResult || null,
    jobs: historyResult?.jobs || []
  });
}
