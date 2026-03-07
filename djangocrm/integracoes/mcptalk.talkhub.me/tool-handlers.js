import { makeRequest } from './index.js';

// Tool handler - maps tool names to API endpoints and methods
export async function handleToolCall(toolName, args) {
  // Extrair api_key dos argumentos (se fornecida)
  const { api_key, ...requestArgs } = args;
  
  const handlers = {
    // ===== FLOW MANAGEMENT =====
    'flow_get_subflows': () => makeRequest('GET', '/flow/subflows', null, requestArgs, api_key),
    'flow_delete_subflow': () => makeRequest('DELETE', '/flow/delete-sub-flow', requestArgs, null, api_key),
    'flow_get_bot_users_count': () => makeRequest('GET', '/flow/bot-users-count', null, null, api_key),
    'flow_get_agents': () => makeRequest('GET', '/flow/agents', null, requestArgs, api_key),
    'flow_get_template_installs': () => makeRequest('GET', '/flow/template-installs', null, requestArgs, api_key),
    'flow_set_default_start_flow': () => makeRequest('POST', '/flow/set-default-start-flow', requestArgs, null, api_key),
    'flow_set_web_chat_widget_start_flow': () => makeRequest('POST', '/flow/set-web-chat-widget-default-start-flow', requestArgs, null, api_key),
    'flow_set_audio_transcription': () => makeRequest('POST', '/flow/settings/set-audio-transcription', requestArgs, null, api_key),
    'flow_get_inbound_webhooks': () => makeRequest('GET', '/flow/inbound-webhooks', null, requestArgs, api_key),
    'flow_get_chat_button_widgets': () => makeRequest('GET', '/flow/chat-button-widgets', null, requestArgs, api_key),

    // ===== FLOW TAGS =====
    'flow_get_tags': () => makeRequest('GET', '/flow/tags', null, requestArgs, api_key),
    'flow_create_tag': () => makeRequest('POST', '/flow/create-tag', requestArgs, null, api_key),
    'flow_delete_tag': () => makeRequest('DELETE', '/flow/delete-tag', requestArgs, null, api_key),
    'flow_delete_tag_by_name': () => makeRequest('DELETE', '/flow/delete-tag-by-name', requestArgs, null, api_key),

    // ===== FLOW USER FIELDS =====
    'flow_get_user_fields': () => makeRequest('GET', '/flow/user-fields', null, requestArgs, api_key),
    'flow_create_user_field': () => makeRequest('POST', '/flow/create-user-field', requestArgs, null, api_key),
    'flow_update_user_field': () => makeRequest('POST', '/flow/update-user-field', requestArgs, null, api_key),
    'flow_delete_user_field': () => makeRequest('DELETE', '/flow/delete-user-field', requestArgs, null, api_key),
    'flow_delete_user_field_by_name': () => makeRequest('DELETE', '/flow/delete-user-field-by-name', requestArgs, null, api_key),

    // ===== FLOW BOT FIELDS =====
    'flow_get_bot_fields': () => makeRequest('GET', '/flow/bot-fields', null, requestArgs, api_key),
    'flow_create_bot_field': () => makeRequest('POST', '/flow/create-bot-field', requestArgs, null, api_key),
    'flow_set_bot_field': () => makeRequest('PUT', '/flow/set-bot-field', requestArgs, null, api_key),
    'flow_set_bot_field_by_name': () => makeRequest('PUT', '/flow/set-bot-field-by-name', requestArgs, null, api_key),
    'flow_set_bot_fields': () => makeRequest('PUT', '/flow/set-bot-fields', requestArgs, null, api_key),
    'flow_set_bot_fields_by_name': () => makeRequest('PUT', '/flow/set-bot-fields-by-name', requestArgs, null, api_key),
    'flow_delete_bot_field': () => makeRequest('DELETE', '/flow/delete-bot-field', requestArgs, null, api_key),
    'flow_delete_bot_field_by_name': () => makeRequest('DELETE', '/flow/delete-bot-field-by-name', requestArgs, null, api_key),

    // ===== AI HUB =====
    'flow_get_ai_agents': () => makeRequest('GET', '/flow/ai-agents', null, requestArgs, api_key),
    'flow_update_ai_agent_provider': () => makeRequest('POST', '/flow/update-ai-agent-provider', requestArgs, null, api_key),

    // ===== SEGMENTS =====
    'flow_get_segments': () => makeRequest('GET', '/flow/segments', null, requestArgs, api_key),

    // ===== CUSTOM EVENTS =====
    'flow_get_custom_events': () => makeRequest('GET', '/flow/custom-events', null, requestArgs, api_key),
    'flow_get_custom_events_summary': () => makeRequest('GET', '/flow/custom-events/summary', null, requestArgs, api_key),
    'flow_get_custom_events_data': () => makeRequest('GET', '/flow/custom-events/data', null, requestArgs, api_key),

    // ===== CONVERSATIONS =====
    'flow_get_agent_activity_log': () => makeRequest('GET', '/flow/agent-activity-log/data', null, requestArgs, api_key),
    'flow_get_conversations_data': () => makeRequest('GET', '/flow/conversations/data', null, requestArgs, api_key),

    // ===== WHATSAPP TEMPLATES =====
    'whatsapp_list_templates': () => makeRequest('POST', '/whatsapp-template/list', null, requestArgs, api_key),
    'whatsapp_create_template': () => makeRequest('POST', '/whatsapp-template/create', requestArgs, null, api_key),
    'whatsapp_delete_template': () => makeRequest('DELETE', '/whatsapp-template/delete', requestArgs, null, api_key),
    'whatsapp_sync_templates': () => makeRequest('POST', '/whatsapp-template/sync', null, null, api_key),

    // ===== SUBSCRIBERS =====
    'subscriber_get_list': () => makeRequest('GET', '/subscribers', null, requestArgs, api_key),
    'subscriber_get_info': () => makeRequest('GET', '/subscriber/get-info', null, requestArgs, api_key),
    'subscriber_get_info_by_user_id': () => makeRequest('GET', '/subscriber/get-info-by-user-id', null, requestArgs, api_key),
    'subscriber_create': () => makeRequest('POST', '/subscriber/create', requestArgs, null, api_key),
    'subscriber_update': () => makeRequest('PUT', '/subscriber/update', requestArgs, null, api_key),
    'subscriber_delete': () => makeRequest('DELETE', '/subscriber/delete', requestArgs, null, api_key),
    'subscriber_add_tag': () => makeRequest('POST', '/subscriber/add-tag', requestArgs, null, api_key),
    'subscriber_add_tags': () => makeRequest('POST', '/subscriber/add-tags', requestArgs, null, api_key),
    'subscriber_add_tag_by_name': () => makeRequest('POST', '/subscriber/add-tag-by-name', requestArgs, null, api_key),
    'subscriber_add_tags_by_name': () => makeRequest('POST', '/subscriber/add-tags-by-name', requestArgs, null, api_key),
    'subscriber_remove_tag': () => makeRequest('DELETE', '/subscriber/remove-tag', requestArgs, null, api_key),
    'subscriber_remove_tags': () => makeRequest('DELETE', '/subscriber/remove-tags', requestArgs, null, api_key),
    'subscriber_remove_tag_by_name': () => makeRequest('DELETE', '/subscriber/remove-tag-by-name', requestArgs, null, api_key),
    'subscriber_remove_tags_by_name': () => makeRequest('DELETE', '/subscriber/remove-tags-by-name', requestArgs, null, api_key),
    'subscriber_add_labels_by_name': () => makeRequest('POST', '/subscriber/add-labels-by-name', requestArgs, null, api_key),
    'subscriber_remove_labels_by_name': () => makeRequest('DELETE', '/subscriber/remove-labels-by-name', requestArgs, null, api_key),
    'subscriber_set_user_field': () => makeRequest('PUT', '/subscriber/set-user-field', requestArgs, null, api_key),
    'subscriber_set_user_fields': () => makeRequest('PUT', '/subscriber/set-user-fields', requestArgs, null, api_key),
    'subscriber_set_user_field_by_name': () => makeRequest('PUT', '/subscriber/set-user-field-by-name', requestArgs, null, api_key),
    'subscriber_set_user_fields_by_name': () => makeRequest('PUT', '/subscriber/set-user-fields-by-name', requestArgs, null, api_key),
    'subscriber_clear_user_field': () => makeRequest('DELETE', '/subscriber/clear-user-field', requestArgs, null, api_key),
    'subscriber_clear_user_fields': () => makeRequest('DELETE', '/subscriber/clear-user-fields', requestArgs, null, api_key),
    'subscriber_clear_user_field_by_name': () => makeRequest('DELETE', '/subscriber/clear-user-field-by-name', requestArgs, null, api_key),
    'subscriber_clear_user_fields_by_name': () => makeRequest('DELETE', '/subscriber/clear-user-fields-by-name', requestArgs, null, api_key),
    'subscriber_pause_bot': () => makeRequest('POST', '/subscriber/pause-bot', requestArgs, null, api_key),
    'subscriber_resume_bot': () => makeRequest('POST', '/subscriber/resume-bot', requestArgs, null, api_key),
    'subscriber_move_chat_to': () => makeRequest('POST', '/subscriber/move-chat-to', requestArgs, null, api_key),
    'subscriber_assign_agent': () => makeRequest('POST', '/subscriber/assign-agent', requestArgs, null, api_key),
    'subscriber_assign_agent_group': () => makeRequest('POST', '/subscriber/assign-agent-group', requestArgs, null, api_key),
    'subscriber_unassign_agent': () => makeRequest('POST', '/subscriber/unassign-agent', requestArgs, null, api_key),
    'subscriber_subscribe_to_bot': () => makeRequest('POST', '/subscriber/subscribe-to-bot', requestArgs, null, api_key),
    'subscriber_unsubscribe_from_bot': () => makeRequest('DELETE', '/subscriber/unsubscribe-from-bot', requestArgs, null, api_key),
    'subscriber_opt_in_sms': () => makeRequest('POST', '/subscriber/opt-in-sms', requestArgs, null, api_key),
    'subscriber_opt_out_sms': () => makeRequest('DELETE', '/subscriber/opt-out-sms', requestArgs, null, api_key),
    'subscriber_opt_in_email': () => makeRequest('POST', '/subscriber/opt-in-email', requestArgs, null, api_key),
    'subscriber_opt_out_email': () => makeRequest('DELETE', '/subscriber/opt-out-email', requestArgs, null, api_key),
    'subscriber_log_custom_event': () => makeRequest('POST', '/subscriber/log-custom-event', requestArgs, null, api_key),
    'subscriber_get_chat_messages': () => makeRequest('GET', '/subscriber/chat-messages', null, requestArgs, api_key),
    'subscriber_get_chat_messages_by_mids': () => makeRequest('POST', '/subscriber/chat-messages-by-mids', requestArgs, null, api_key),

    // ===== SENDING =====
    'subscriber_send_main_flow': () => makeRequest('POST', '/subscriber/send-main-flow', requestArgs, null, api_key),
    'subscriber_send_sub_flow': () => makeRequest('POST', '/subscriber/send-sub-flow', requestArgs, null, api_key),
    'subscriber_send_sub_flow_by_flow_name': () => makeRequest('POST', '/subscriber/send-sub-flow-by-flow-name', requestArgs, null, api_key),
    'subscriber_send_sub_flow_by_user_id': () => makeRequest('POST', '/subscriber/send-sub-flow-by-user-id', requestArgs, null, api_key),
    'subscriber_broadcast': () => makeRequest('POST', '/subscriber/broadcast', requestArgs, null, api_key),
    'subscriber_broadcast_by_user_id': () => makeRequest('POST', '/subscriber/broadcast-by-user-id', requestArgs, null, api_key),
    'subscriber_broadcast_by_tag': () => makeRequest('POST', '/subscriber/broadcast-by-tag', requestArgs, null, api_key),
    'subscriber_broadcast_by_segment': () => makeRequest('POST', '/subscriber/broadcast-by-segment', requestArgs, null, api_key),
    'subscriber_send_content': () => makeRequest('POST', '/subscriber/send-content', requestArgs, null, api_key),
    'subscriber_send_text': () => makeRequest('POST', '/subscriber/send-text', requestArgs, null, api_key),
    'subscriber_send_sms': () => makeRequest('POST', '/subscriber/send-sms', requestArgs, null, api_key),
    'subscriber_send_email': () => makeRequest('POST', '/subscriber/send-email', requestArgs, null, api_key),
    'subscriber_send_node': () => makeRequest('POST', '/subscriber/send-node', requestArgs, null, api_key),
    'subscriber_send_whatsapp_template': () => makeRequest('POST', '/subscriber/send-whatsapp-template', requestArgs, null, api_key),
    'subscriber_send_whatsapp_template_by_user_id': () => makeRequest('POST', '/subscriber/send-whatsapp-template-by-user-id', requestArgs, null, api_key),

    // ===== MINI-APP =====
    'subscriber_app_trigger': () => makeRequest('POST', '/subscriber/app-trigger', requestArgs, null, api_key),

    // ===== ECOMMERCE - CART =====
    'subscriber_get_cart': () => makeRequest('GET', '/subscriber/cart', null, requestArgs, api_key),
    'subscriber_empty_cart': () => makeRequest('DELETE', '/subscriber/empty-cart', requestArgs, null, api_key),
    'subscriber_add_to_cart': () => makeRequest('POST', '/subscriber/add-to-cart', requestArgs, null, api_key),
    'subscriber_remove_from_cart': () => makeRequest('DELETE', '/subscriber/remove-from-cart', requestArgs, null, api_key),
    'subscriber_cart_paid': () => makeRequest('POST', '/subscriber/cart-paid', requestArgs, null, api_key),
    'subscriber_update_order_status': () => makeRequest('POST', '/subscriber/update-order-status', requestArgs, null, api_key),

    // ===== ECOMMERCE - DISCOUNT CODES =====
    'shop_get_discount_codes': () => makeRequest('GET', '/shop/discount-codes', null, requestArgs, api_key),
    'shop_get_discount_code_info': () => { const { codeId, ...rest } = requestArgs; return makeRequest('GET', `/shop/discount-codes/${codeId}/get-info`, null, rest, api_key); },
    'shop_get_discount_code_info_by_code': () => makeRequest('GET', '/shop/discount-codes/get-info-by-code', null, requestArgs, api_key),
    'shop_create_discount_code': () => makeRequest('POST', '/shop/discount-codes/create', requestArgs, null, api_key),
    'shop_update_discount_code': () => { const { codeId, ...rest } = requestArgs; return makeRequest('PUT', `/shop/discount-codes/${codeId}/update`, rest, null, api_key); },
    'shop_delete_discount_code': () => { const { codeId, ...rest } = requestArgs; return makeRequest('DELETE', `/shop/discount-codes/${codeId}/delete`, null, null, api_key); },
    'shop_delete_discount_code_by_code': () => makeRequest('DELETE', '/shop/discount-codes/delete-by-code', null, requestArgs, api_key),

    // ===== ECOMMERCE - ORDERS =====
    'shop_get_orders': () => makeRequest('GET', '/shop/orders', null, requestArgs, api_key),
    'shop_get_order_info': () => { const { orderId, ...rest } = requestArgs; return makeRequest('GET', `/shop/orders/${orderId}/get-info`, null, rest, api_key); },
    'shop_create_order': () => makeRequest('POST', '/shop/orders/create', requestArgs, null, api_key),
    'shop_update_order': () => { const { orderId, ...rest } = requestArgs; return makeRequest('PUT', `/shop/orders/${orderId}/update`, rest, null, api_key); },

    // ===== ECOMMERCE - PRODUCTS =====
    'shop_get_products': () => makeRequest('GET', '/shop/products', null, requestArgs, api_key),
    'shop_get_product_info': () => { const { productId, ...rest } = requestArgs; return makeRequest('GET', `/shop/products/${productId}/get-info`, null, rest, api_key); },
    'shop_create_product': () => makeRequest('POST', '/shop/products/create', requestArgs, null, api_key),
    'shop_update_product': () => { const { productId, ...rest } = requestArgs; return makeRequest('PUT', `/shop/products/${productId}/update`, rest, null, api_key); },
    'shop_delete_product': () => { const { productId } = requestArgs; return makeRequest('DELETE', `/shop/products/${productId}/delete`, null, null, api_key); },

    // ===== ECOMMERCE - PRODUCT TAGS =====
    'shop_get_product_tags': () => makeRequest('GET', '/shop/product-tags', null, requestArgs, api_key),
    'shop_get_product_tag_info': () => { const { tagId, ...rest } = requestArgs; return makeRequest('GET', `/shop/product-tags/${tagId}/get-info`, null, rest, api_key); },
    'shop_create_product_tag': () => makeRequest('POST', '/shop/product-tags/create', requestArgs, null, api_key),
    'shop_update_product_tag': () => { const { tagId, ...rest } = requestArgs; return makeRequest('PUT', `/shop/product-tags/${tagId}/update`, rest, null, api_key); },
    'shop_delete_product_tag': () => { const { tagId } = requestArgs; return makeRequest('DELETE', `/shop/product-tags/${tagId}/delete`, null, null, api_key); },

    // ===== ECOMMERCE - PRODUCT TYPES =====
    'shop_get_product_types': () => makeRequest('GET', '/shop/product-types', null, requestArgs, api_key),
    'shop_get_product_type_info': () => { const { typeId, ...rest } = requestArgs; return makeRequest('GET', `/shop/product-types/${typeId}/get-info`, null, rest, api_key); },
    'shop_create_product_type': () => makeRequest('POST', '/shop/product-types/create', requestArgs, null, api_key),
    'shop_update_product_type': () => { const { typeId, ...rest } = requestArgs; return makeRequest('PUT', `/shop/product-types/${typeId}/update`, rest, null, api_key); },
    'shop_delete_product_type': () => { const { typeId } = requestArgs; return makeRequest('DELETE', `/shop/product-types/${typeId}/delete`, null, null, api_key); },

    // ===== ECOMMERCE - PRODUCT VENDORS =====
    'shop_get_product_vendors': () => makeRequest('GET', '/shop/product-vendors', null, requestArgs, api_key),
    'shop_get_product_vendor_info': () => { const { vendorId, ...rest } = requestArgs; return makeRequest('GET', `/shop/product-vendors/${vendorId}/get-info`, null, rest, api_key); },
    'shop_create_product_vendor': () => makeRequest('POST', '/shop/product-vendors/create', requestArgs, null, api_key),
    'shop_update_product_vendor': () => { const { vendorId, ...rest } = requestArgs; return makeRequest('PUT', `/shop/product-vendors/${vendorId}/update`, rest, null, api_key); },
    'shop_delete_product_vendor': () => { const { vendorId } = requestArgs; return makeRequest('DELETE', `/shop/product-vendors/${vendorId}/delete`, null, null, api_key); },

    // ===== ECOMMERCE - BUSINESS HOURS =====
    'shop_get_business_hours': () => makeRequest('GET', '/shop/business-hours/info', null, null, api_key),
    'shop_update_business_hours': () => makeRequest('PUT', '/shop/business-hours/update', requestArgs, null, api_key),

    // ===== ECOMMERCE - LOCATIONS =====
    'shop_get_locations': () => makeRequest('GET', '/shop/locations', null, requestArgs, api_key),
    'shop_get_location_info': () => { const { locationId, ...rest } = requestArgs; return makeRequest('GET', `/shop/locations/${locationId}/get-info`, null, rest, api_key); },
    'shop_create_location': () => makeRequest('POST', '/shop/locations/create', requestArgs, null, api_key),
    'shop_update_location': () => { const { locationId, ...rest } = requestArgs; return makeRequest('PUT', `/shop/locations/${locationId}/update`, rest, null, api_key); },
    'shop_delete_location': () => { const { locationId } = requestArgs; return makeRequest('DELETE', `/shop/locations/${locationId}/delete`, null, null, api_key); },

    // ===== ECOMMERCE - PRODUCT VARIANTS =====
    'shop_get_product_variants': () => { const { productId, ...rest } = requestArgs; return makeRequest('GET', `/shop/products/${productId}/variants`, null, rest, api_key); },
    'shop_get_product_variant_info': () => { const { productId, variantId, ...rest } = requestArgs; return makeRequest('GET', `/shop/products/${productId}/variants/${variantId}/get-info`, null, rest, api_key); },
    'shop_create_product_variant': () => { const { productId, ...rest } = requestArgs; return makeRequest('POST', `/shop/products/${productId}/variants/create`, rest, null, api_key); },
    'shop_update_product_variant': () => { const { productId, variantId, ...rest } = requestArgs; return makeRequest('PUT', `/shop/products/${productId}/variants/${variantId}/update`, rest, null, api_key); },
    'shop_delete_product_variant': () => { const { productId, variantId } = requestArgs; return makeRequest('DELETE', `/shop/products/${productId}/variants/${variantId}/delete`, null, null, api_key); },

    // ===== TEMPLATES =====
    'get_templates': () => makeRequest('GET', '/templates', null, requestArgs, api_key),
    'get_template_installs': () => { const { templateNs, ...rest } = requestArgs; return makeRequest('GET', `/template/${templateNs}/installs`, null, rest, api_key); },
    'generate_template_link': () => { const { templateNs, ...rest } = requestArgs; return makeRequest('POST', `/template/${templateNs}/generate-one-time-link`, null, rest, api_key); },

    // ===== TICKET LISTS =====
    'get_ticket_lists': () => makeRequest('GET', '/team/ticket-lists', null, requestArgs, api_key),
    'get_ticket_list_fields': () => { const { listId } = requestArgs; return makeRequest('GET', `/team/ticket-lists/${listId}/fields`, null, null, api_key); },
    'get_ticket_list_items': () => { const { listId, ...rest } = requestArgs; return makeRequest('GET', `/team/ticket-lists/${listId}/items`, null, rest, api_key); },
    'get_ticket_list_log_data': () => { const { listId, ...rest } = requestArgs; return makeRequest('GET', `/team/ticket-lists/${listId}/log-data`, null, rest, api_key); },
    'create_ticket': () => { const { listId, ...rest } = requestArgs; return makeRequest('POST', `/team/ticket-lists/${listId}/create`, rest, null, api_key); },
    'update_ticket': () => { const { listId, listItemId, ...rest } = requestArgs; return makeRequest('PUT', `/team/ticket-lists/${listId}/update/${listItemId}`, rest, null, api_key); },
    'delete_ticket': () => { const { listId, listItemId } = requestArgs; return makeRequest('DELETE', `/team/ticket-lists/${listId}/delete/${listItemId}`, null, null, api_key); },

    // ===== TEAM LABELS =====
    'get_team_labels': () => makeRequest('GET', '/team/labels', null, requestArgs, api_key),
    'create_team_label': () => makeRequest('POST', '/team/create-label', requestArgs, null, api_key),
    'delete_team_label': () => makeRequest('DELETE', '/team/delete-label', requestArgs, null, api_key),
    'delete_team_label_by_name': () => makeRequest('DELETE', '/team/delete-label-by-name', requestArgs, null, api_key),

    // ===== INTEGRATIONS =====
    'get_shopify_integration': () => makeRequest('GET', '/integration/shopify', null, null, api_key),
    'update_shopify_integration': () => makeRequest('POST', '/integration/shopify', requestArgs, null, api_key),
    'delete_shopify_integration': () => makeRequest('DELETE', '/integration/shopify', null, null, api_key),
    'get_woocommerce_integration': () => makeRequest('GET', '/integration/woocommerce', null, null, api_key),
    'update_woocommerce_integration': () => makeRequest('POST', '/integration/woocommerce', requestArgs, null, api_key),
    'delete_woocommerce_integration': () => makeRequest('DELETE', '/integration/woocommerce', null, null, api_key),
    'get_dropi_integration': () => makeRequest('GET', '/integration/dropi', null, null, api_key),
    'update_dropi_integration': () => makeRequest('POST', '/integration/dropi', requestArgs, null, api_key),
    'delete_dropi_integration': () => makeRequest('DELETE', '/integration/dropi', null, null, api_key),
    'get_meta_conversions_api_integration': () => makeRequest('GET', '/integration/meta-conversions-api', null, null, api_key),
    'update_meta_conversions_api_integration': () => makeRequest('POST', '/integration/meta-conversions-api', requestArgs, null, api_key),
    'delete_meta_conversions_api_integration': () => makeRequest('DELETE', '/integration/meta-conversions-api', null, null, api_key),
    'get_openai_integration': () => makeRequest('GET', '/integration/openai', null, null, api_key),
    'update_openai_integration': () => makeRequest('POST', '/integration/openai', requestArgs, null, api_key),
    'delete_openai_integration': () => makeRequest('DELETE', '/integration/openai', null, null, api_key),
    'get_s3storage_integration': () => makeRequest('GET', '/integration/s3storage', null, null, api_key),
    'update_s3storage_integration': () => makeRequest('POST', '/integration/s3storage', requestArgs, null, api_key),
    'delete_s3storage_integration': () => makeRequest('DELETE', '/integration/s3storage', null, null, api_key),
    'get_installed_mini_apps': () => makeRequest('GET', '/installed-mini-app/list', null, requestArgs, api_key),
    'update_mini_app_api_key': () => { const { app_id, ...rest } = requestArgs; return makeRequest('POST', `/installed-mini-app/update-api-key/${app_id}`, rest, null, api_key); },

    // ===== OPENAI EMBEDDINGS =====
    'get_openai_embeddings': () => makeRequest('GET', '/openai-embeddings', null, requestArgs, api_key),
    'get_openai_embedding_info': () => { const { id, ...rest } = requestArgs; return makeRequest('GET', `/openai-embeddings/${id}/get-info`, null, rest, api_key); },
    'create_openai_embedding': () => makeRequest('POST', '/openai-embeddings/create', requestArgs, null, api_key),
    'update_openai_embedding': () => { const { id, ...rest } = requestArgs; return makeRequest('PUT', `/openai-embeddings/${id}/update`, rest, null, api_key); },
    'delete_openai_embedding': () => { const { id } = requestArgs; return makeRequest('DELETE', `/openai-embeddings/${id}/delete`, null, null, api_key); },
    'import_openai_embeddings': () => makeRequest('POST', '/openai-embeddings/import', requestArgs, null, api_key),
    'generate_openai_embeddings': () => makeRequest('POST', '/openai-embeddings/generate', null, null, api_key),

    // ===== WORKSPACE =====
    'get_flow_summary': () => makeRequest('GET', '/flow-summary', null, requestArgs, api_key),
    'get_flow_agent_summary': () => makeRequest('GET', '/flow-agent-summary', null, requestArgs, api_key),
    'get_team_bot_users': () => makeRequest('GET', '/team-bot-users', null, requestArgs, api_key),
    'get_team_flows': () => makeRequest('GET', '/team-flows', null, requestArgs, api_key),
    'get_team_info': () => makeRequest('GET', '/team-info', null, null, api_key),
    'get_workspace_channels': () => makeRequest('GET', '/workspace-settings/channels', null, null, api_key),
    'update_workspace_channels': () => makeRequest('POST', '/workspace-settings/update-channels', requestArgs, null, api_key),
    'get_workspace_live_chat_sidebar': () => makeRequest('GET', '/workspace-settings/live-chat-sidebar', null, null, api_key),
    'update_workspace_live_chat_sidebar': () => makeRequest('POST', '/workspace-settings/update-live-chat-sidebar', requestArgs, null, api_key),
    'get_team_members': () => makeRequest('GET', '/team-members', null, requestArgs, api_key),

    // ===== USER =====
    'get_current_user': () => makeRequest('GET', '/me', null, null, api_key),
    'change_user_password': () => makeRequest('PUT', '/user/change-password', requestArgs, null, api_key),
    'get_recent_notifications': () => makeRequest('GET', '/notifications/recent', null, null, api_key),
    'mark_notification_read': () => makeRequest('POST', '/notifications/read', requestArgs, null, api_key),
    'mark_announcement_read': () => makeRequest('POST', '/announcements/read', null, null, api_key),
  };

  const handler = handlers[toolName];
  if (!handler) {
    return {
      content: [{
        type: 'text',
        text: `Unknown tool: ${toolName}`,
      }],
      isError: true,
    };
  }

  return await handler();
}
