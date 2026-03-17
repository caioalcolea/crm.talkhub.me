/** @type {import('./$types').LayoutServerLoad} */
export async function load({ locals, cookies }) {
  // console.log("locals", locals.user);
  return {
    user: locals.user,
    userRole: locals.profile?.role || 'USER',
    org_name: locals.org_name || 'TalkHub CRM',
    org_settings: locals.org_settings || {
      default_currency: 'BRL',
      currency_symbol: 'R$',
      default_country: null
    },
    // Expose access token so client-side api.js can authenticate mutations.
    // Tokens live in httpOnly cookies (unreadable by JS), so we bridge them here.
    accessToken: cookies.get('jwt_access') || null
  };
}

export const ssr = true;
