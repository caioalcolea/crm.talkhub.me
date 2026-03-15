/**
 * Transform a Django API contact response (snake_case) to frontend format (camelCase).
 * Used after merge and other client-side API calls that return raw contact data.
 *
 * @param {any} contact - Raw contact object from Django API
 * @returns {any} Transformed contact object for frontend consumption
 */
export function transformApiContact(contact) {
  return {
    id: contact.id,
    firstName: contact.first_name,
    lastName: contact.last_name,
    email: contact.email,
    secondaryEmail: contact.secondary_email,
    phone: contact.phone,
    secondaryPhone: contact.secondary_phone,
    organization: contact.organization,
    title: contact.title,
    department: contact.department,
    doNotCall: contact.do_not_call || false,
    linkedInUrl: contact.linkedin_url,
    instagram: contact.instagram,
    facebook: contact.facebook,
    tiktok: contact.tiktok,
    telegram: contact.telegram,
    addressLine: contact.address_line,
    city: contact.city,
    state: contact.state,
    postcode: contact.postcode,
    country: contact.country,
    description: contact.description,
    extraEmails: (contact.extra_emails || []).map((/** @type {any} */ e) => ({
      id: e.id,
      email: e.email,
      label: e.label
    })),
    extraPhones: (contact.extra_phones || []).map((/** @type {any} */ p) => ({
      id: p.id,
      phone: p.phone,
      label: p.label
    })),
    extraAddresses: (contact.extra_addresses || []).map((/** @type {any} */ a) => ({
      id: a.id,
      label: a.label,
      addressLine: a.address_line,
      city: a.city,
      state: a.state,
      postcode: a.postcode,
      country: a.country
    })),
    createdAt: contact.created_at,
    updatedAt: contact.updated_at,
    owner:
      contact.assigned_to && contact.assigned_to.length > 0
        ? {
            id: contact.assigned_to[0].id,
            name: contact.assigned_to[0].user_details?.email || '',
            email: contact.assigned_to[0].user_details?.email
          }
        : null,
    tags: (contact.tags || []).map((/** @type {any} */ t) => ({
      id: t.id,
      name: t.name
    })),
    account: contact.account || null
  };
}
