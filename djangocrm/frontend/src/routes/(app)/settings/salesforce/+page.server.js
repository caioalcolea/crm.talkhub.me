/** @type {import('./$types').PageServerLoad} */
export async function load() {
  return {
    notImplemented: true,
    sfStatus: { connected: false, has_credentials: false },
    error: null
  };
}
