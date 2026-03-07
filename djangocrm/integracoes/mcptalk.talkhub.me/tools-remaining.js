// Remaining tool definitions: Sending, Mini-App, E-commerce, Templates, Tickets, Labels, Integrations, Embeddings, Workspace, User
// All schemas validated against TalkHub Swagger API v1.0.0
export const remainingTools = [
  // ===== SENDING (15 tools) =====
  {
    name: 'subscriber_send_main_flow',
    description: 'Send main flow to subscriber. Triggers the default bot flow.',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns' },
      },
      required: ['user_ns'],
      additionalProperties: false,
    },
  },
  {
    name: 'subscriber_send_sub_flow',
    description: 'Send a sub-flow to subscriber by namespace.',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns' },
        sub_flow_ns: { type: 'string', description: 'Sub-flow namespace' },
      },
      required: ['user_ns', 'sub_flow_ns'],
      additionalProperties: false,
    },
  },
  {
    name: 'subscriber_send_sub_flow_by_flow_name',
    description: 'Send a sub-flow to subscriber by flow name.',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns' },
        flow_name: { type: 'string', description: 'Flow name' },
      },
      required: ['user_ns', 'flow_name'],
      additionalProperties: false,
    },
  },
  {
    name: 'subscriber_send_sub_flow_by_user_id',
    description: 'Send a sub-flow to subscriber by channel user ID.',
    inputSchema: {
      type: 'object',
      properties: {
        user_id: { type: 'string', description: 'Channel user ID' },
        sub_flow_ns: { type: 'string', description: 'Sub-flow namespace' },
      },
      required: ['user_id', 'sub_flow_ns'],
      additionalProperties: false,
    },
  },
  {
    name: 'subscriber_broadcast',
    description: 'Broadcast sub flow by user_ns list. Types: EMAIL, SMS, WHATSAPP_TEMPLATE, FACEBOOK_NOTIFICATION.',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns_list: { type: 'string', description: 'Comma-separated user_ns list (e.g. "f123u111,f123u222")' },
        sub_flow_ns: { type: 'string', description: 'Sub-flow namespace' },
        type: { type: 'string', description: 'Type: EMAIL, SMS, WHATSAPP_TEMPLATE, FACEBOOK_NOTIFICATION' },
        scheduled_time: { type: 'number', description: 'Unix timestamp for scheduled send' },
        max_per_minute: { type: 'number', description: 'Max messages per minute (default: 60)' },
      },
      required: ['user_ns_list', 'sub_flow_ns'],
      additionalProperties: false,
    },
  },
  {
    name: 'subscriber_broadcast_by_user_id',
    description: 'Broadcast sub flow by user IDs. Types: EMAIL, SMS, WHATSAPP_TEMPLATE, FACEBOOK_NOTIFICATION.',
    inputSchema: {
      type: 'object',
      properties: {
        user_id_list: { type: 'string', description: 'Comma-separated user IDs (e.g. "61412345678,61387625429")' },
        sub_flow_ns: { type: 'string', description: 'Sub-flow namespace' },
        type: { type: 'string', description: 'Type: EMAIL, SMS, WHATSAPP_TEMPLATE, FACEBOOK_NOTIFICATION' },
        scheduled_time: { type: 'number', description: 'Unix timestamp for scheduled send' },
        max_per_minute: { type: 'number', description: 'Max messages per minute (default: 60)' },
      },
      required: ['user_id_list', 'sub_flow_ns'],
      additionalProperties: false,
    },
  },
  {
    name: 'subscriber_broadcast_by_tag',
    description: 'Broadcast sub flow by tags. Types: EMAIL, SMS, WHATSAPP_TEMPLATE, FACEBOOK_NOTIFICATION.',
    inputSchema: {
      type: 'object',
      properties: {
        tags: { type: 'array', items: { type: 'string' }, description: 'Array of tag namespaces (e.g. ["f123t456"])' },
        exclude_tags: { type: 'array', items: { type: 'string' }, description: 'Array of tag namespaces to exclude' },
        sub_flow_ns: { type: 'string', description: 'Sub-flow namespace' },
        name: { type: 'string', description: 'Broadcast name' },
        scheduled_time: { type: 'number', description: 'Unix timestamp for scheduled send' },
        max_per_minute: { type: 'number', description: 'Max messages per minute' },
        type: { type: 'string', description: 'Type: EMAIL, SMS, WHATSAPP_TEMPLATE, FACEBOOK_NOTIFICATION' },
        message_tag: { type: 'string', description: 'Message tag (e.g. POST_PURCHASE_UPDATE)' },
        user_fields: { type: 'array', description: 'Array of user field updates [{var_ns, value}]', items: { type: 'object', properties: { var_ns: { type: 'string' }, value: { type: 'string' } } } },
      },
      required: ['tags', 'sub_flow_ns'],
      additionalProperties: false,
    },
  },
  {
    name: 'subscriber_broadcast_by_segment',
    description: 'Broadcast sub flow by segments. Types: EMAIL, SMS, WHATSAPP_TEMPLATE, FACEBOOK_NOTIFICATION.',
    inputSchema: {
      type: 'object',
      properties: {
        segment_ns: { type: 'string', description: 'Comma-separated segment namespaces (e.g. "f123sg34,f123sg56")' },
        sub_flow_ns: { type: 'string', description: 'Sub-flow namespace' },
        scheduled_time: { type: 'number', description: 'Unix timestamp for scheduled send' },
        max_per_minute: { type: 'number', description: 'Max messages per minute' },
        type: { type: 'string', description: 'Type: EMAIL, SMS, WHATSAPP_TEMPLATE, FACEBOOK_NOTIFICATION' },
        message_tag: { type: 'string', description: 'Message tag (e.g. POST_PURCHASE_UPDATE)' },
        bot_fields: { type: 'array', description: 'Array of bot field updates [{var_ns, value}]', items: { type: 'object', properties: { var_ns: { type: 'string' }, value: { type: 'string' } } } },
      },
      required: ['segment_ns', 'sub_flow_ns'],
      additionalProperties: false,
    },
  },
  {
    name: 'subscriber_send_content',
    description: 'Send dynamic content to subscriber. Supports messages, actions, quick_replies, goto.',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns' },
        data: { type: 'object', description: 'Content object: {version:"v1", content:{messages:[{type:"text",text:"msg"}], actions:[], quick_replies:[], goto:"node_ns"}}' },
      },
      required: ['user_ns', 'data'],
      additionalProperties: false,
    },
  },
  {
    name: 'subscriber_send_text',
    description: 'Send plain text message to subscriber.',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns' },
        content: { type: 'string', description: 'Text message content' },
      },
      required: ['user_ns', 'content'],
      additionalProperties: false,
    },
  },
  {
    name: 'subscriber_send_sms',
    description: 'Send SMS to subscriber.',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns' },
        content: { type: 'string', description: 'SMS message content' },
      },
      required: ['user_ns', 'content'],
      additionalProperties: false,
    },
  },
  {
    name: 'subscriber_send_email',
    description: 'Send email to subscriber.',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns' },
        content: { type: 'string', description: 'Email content (HTML)' },
        subject: { type: 'string', description: 'Email subject' },
      },
      required: ['user_ns', 'content', 'subject'],
      additionalProperties: false,
    },
  },
  {
    name: 'subscriber_send_node',
    description: 'Send a specific flow node to subscriber.',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns' },
        node_ns: { type: 'string', description: 'Node namespace (e.g. f123n456)' },
      },
      required: ['user_ns', 'node_ns'],
      additionalProperties: false,
    },
  },
  {
    name: 'subscriber_send_whatsapp_template',
    description: 'Send WhatsApp template to subscriber. Get namespace/name/lang from whatsapp_list_templates.',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns' },
        content: { type: 'object', description: 'Template content: {namespace, name, lang, params:{HEADER_IMAGE:"url", "BODY_{{1}}":"text", QUICK_REPLY_1:"sub_flow_ns"}}' },
      },
      required: ['user_ns', 'content'],
      additionalProperties: false,
    },
  },
  {
    name: 'subscriber_send_whatsapp_template_by_user_id',
    description: 'Send WhatsApp template to subscriber by channel user ID. Get namespace/name/lang from whatsapp_list_templates.',
    inputSchema: {
      type: 'object',
      properties: {
        user_id: { type: 'string', description: 'Channel user ID (phone number)' },
        create_if_not_found: { type: 'string', description: 'Create subscriber if not found: "yes" or "no" (default: "no")' },
        content: { type: 'object', description: 'Template content: {namespace, name, lang, params:{...}}' },
        contact: { type: 'object', description: 'Contact info if creating: {user_name, first_name, last_name}' },
      },
      required: ['user_id', 'content'],
      additionalProperties: false,
    },
  },

  // ===== MINI-APP (1 tool) =====
  {
    name: 'subscriber_app_trigger',
    description: 'Trigger an app event on subscriber from installed mini-app.',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns' },
        trigger_name: { type: 'string', description: 'Trigger name' },
        context: { type: 'object', description: 'Context data (e.g. {product_name:"apple", product_id:"123"})' },
      },
      required: ['user_ns', 'trigger_name'],
      additionalProperties: false,
    },
  },

  // ===== ECOMMERCE - CART (6 tools) =====
  {
    name: 'subscriber_get_cart',
    description: 'Get subscriber shopping cart detail. Read-only.',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns' },
      },
      required: ['user_ns'],
      additionalProperties: false,
    },
  },
  {
    name: 'subscriber_empty_cart',
    description: 'Empty subscriber shopping cart items. Destructive.',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns' },
      },
      required: ['user_ns'],
      additionalProperties: false,
    },
  },
  {
    name: 'subscriber_add_to_cart',
    description: 'Add item to subscriber shopping cart by variant_id.',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns' },
        variant_id: { type: 'number', description: 'Product variant ID' },
        qty: { type: 'number', description: 'Quantity (default: 1)' },
      },
      required: ['user_ns', 'variant_id'],
      additionalProperties: false,
    },
  },
  {
    name: 'subscriber_remove_from_cart',
    description: 'Remove item from subscriber shopping cart by variant_id.',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns' },
        variant_id: { type: 'number', description: 'Product variant ID' },
      },
      required: ['user_ns', 'variant_id'],
      additionalProperties: false,
    },
  },
  {
    name: 'subscriber_cart_paid',
    description: 'Checkout subscriber cart and mark as paid. Creates an order from cart.',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns' },
        shipping_method: { type: 'string', description: 'Shipping: pickup, delivery' },
        payment_method: { type: 'string', description: 'Payment: cash, card, etc.' },
        reference_no: { type: 'string', description: 'Reference number' },
        note: { type: 'string', description: 'Order note' },
        phone: { type: 'string', description: 'Phone' },
        name: { type: 'string', description: 'Customer name' },
        email: { type: 'string', description: 'Email' },
        address: { type: 'string', description: 'Address' },
        suburb: { type: 'string', description: 'Suburb' },
        state: { type: 'string', description: 'State' },
        postcode: { type: 'string', description: 'Postcode' },
        country: { type: 'string', description: 'Country' },
        tracking_no: { type: 'string', description: 'Tracking number' },
      },
      required: ['user_ns'],
      additionalProperties: false,
    },
  },
  {
    name: 'subscriber_update_order_status',
    description: 'Update order status. Values: paid, ordered, processing, shipped, completed, cancelled, refunded.',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns' },
        order_id: { type: 'number', description: 'Order ID' },
        status: { type: 'string', description: 'Status: paid, ordered, processing, shipped, completed, cancelled, refunded' },
      },
      required: ['user_ns', 'order_id', 'status'],
      additionalProperties: false,
    },
  },
  // ===== ECOMMERCE - DISCOUNT CODES (7 tools) =====
  {
    name: 'shop_get_discount_codes',
    description: 'Get list of discount codes.',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Number of items' },
        page: { type: 'number', description: 'Page number 1-100' },
        code: { type: 'string', description: 'Search by code' },
      },
      additionalProperties: false,
    },
  },
  {
    name: 'shop_get_discount_code_info',
    description: 'Get discount code info by ID.',
    inputSchema: {
      type: 'object',
      properties: {
        codeId: { type: 'number', description: 'Discount code ID (path param)' },
      },
      required: ['codeId'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_get_discount_code_info_by_code',
    description: 'Get discount code info by code string.',
    inputSchema: {
      type: 'object',
      properties: {
        code: { type: 'string', description: 'Discount code string' },
      },
      required: ['code'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_create_discount_code',
    description: 'Create new discount code.',
    inputSchema: {
      type: 'object',
      properties: {
        code: { type: 'string', description: 'Discount code' },
        type: { type: 'string', description: 'Type: percentage, amount, free_shipping' },
        discount_percentage: { type: 'number', description: 'Discount percentage (0-100)' },
        discount_amount: { type: 'number', description: 'Discount amount' },
        once_per_order: { type: 'number', description: '0 or 1' },
        min_require: { type: 'string', description: 'Min requirement: none, price, qty' },
        min_price: { type: 'number', description: 'Minimum price' },
        min_qty: { type: 'number', description: 'Minimum quantity' },
        has_usage_limit: { type: 'number', description: '0 or 1' },
        max_usage_count: { type: 'number', description: 'Max usage count' },
        one_per_customer: { type: 'number', description: '0 or 1' },
        start_time: { type: 'string', description: 'Start time (e.g. "2022-12-25 00:00:00")' },
        end_time: { type: 'string', description: 'End time (e.g. "2022-12-27 00:00:00")' },
      },
      required: ['code', 'type'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_update_discount_code',
    description: 'Update discount code.',
    inputSchema: {
      type: 'object',
      properties: {
        codeId: { type: 'number', description: 'Discount code ID (path param)' },
        code: { type: 'string', description: 'Discount code' },
        type: { type: 'string', description: 'Type: percentage, amount, free_shipping' },
        discount_percentage: { type: 'number', description: 'Discount percentage' },
        discount_amount: { type: 'number', description: 'Discount amount' },
        once_per_order: { type: 'number', description: '0 or 1' },
        min_require: { type: 'string', description: 'Min requirement: none, price, qty' },
        min_price: { type: 'number', description: 'Minimum price' },
        min_qty: { type: 'number', description: 'Minimum quantity' },
        has_usage_limit: { type: 'number', description: '0 or 1' },
        max_usage_count: { type: 'number', description: 'Max usage count' },
        one_per_customer: { type: 'number', description: '0 or 1' },
        start_time: { type: 'string', description: 'Start time' },
        end_time: { type: 'string', description: 'End time' },
      },
      required: ['codeId'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_delete_discount_code',
    description: 'Delete discount code by ID. Destructive.',
    inputSchema: {
      type: 'object',
      properties: {
        codeId: { type: 'number', description: 'Discount code ID (path param)' },
      },
      required: ['codeId'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_delete_discount_code_by_code',
    description: 'Delete discount code by code string. Destructive.',
    inputSchema: {
      type: 'object',
      properties: {
        code: { type: 'string', description: 'Discount code string' },
      },
      required: ['code'],
      additionalProperties: false,
    },
  },

  // ===== ECOMMERCE - ORDERS (4 tools) =====
  {
    name: 'shop_get_orders',
    description: 'Get list of orders.',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Filter by subscriber user_ns' },
        limit: { type: 'number', description: 'Number of items' },
        page: { type: 'number', description: 'Page number 1-100' },
      },
      additionalProperties: false,
    },
  },
  {
    name: 'shop_get_order_info',
    description: 'Get order info by ID.',
    inputSchema: {
      type: 'object',
      properties: {
        orderId: { type: 'number', description: 'Order ID (path param)' },
      },
      required: ['orderId'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_create_order',
    description: 'Create new order for bot user.',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns' },
        status: { type: 'string', description: 'Status: paid, ordered, processing, shipped, completed, cancelled, refunded' },
        shipping_method: { type: 'string', description: 'Shipping: pickup, delivery' },
        payment_method: { type: 'string', description: 'Payment: cash, card, etc.' },
        reference_no: { type: 'string', description: 'Reference number' },
        note: { type: 'string', description: 'Order note' },
        address: { type: 'string', description: 'Address' },
        suburb: { type: 'string', description: 'Suburb' },
        state: { type: 'string', description: 'State' },
        postcode: { type: 'string', description: 'Postcode' },
        country: { type: 'string', description: 'Country' },
        tracking_no: { type: 'string', description: 'Tracking number' },
        items: { type: 'array', description: 'Order items [{variant_id, qty}]', items: { type: 'object', properties: { variant_id: { type: 'number' }, qty: { type: 'number' } } } },
      },
      required: ['user_ns', 'items'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_update_order',
    description: 'Update order.',
    inputSchema: {
      type: 'object',
      properties: {
        orderId: { type: 'number', description: 'Order ID (path param)' },
        status: { type: 'string', description: 'Status: paid, ordered, processing, shipped, completed, cancelled, refunded' },
        shipping_method: { type: 'string', description: 'Shipping: pickup, delivery' },
        payment_method: { type: 'string', description: 'Payment method' },
        reference_no: { type: 'string', description: 'Reference number' },
        note: { type: 'string', description: 'Note' },
        address: { type: 'string', description: 'Address' },
        suburb: { type: 'string', description: 'Suburb' },
        state: { type: 'string', description: 'State' },
        postcode: { type: 'string', description: 'Postcode' },
        country: { type: 'string', description: 'Country' },
        tracking_no: { type: 'string', description: 'Tracking number' },
        items: { type: 'array', description: 'Order items [{variant_id, qty}]', items: { type: 'object', properties: { variant_id: { type: 'number' }, qty: { type: 'number' } } } },
      },
      required: ['orderId'],
      additionalProperties: false,
    },
  },

  // ===== ECOMMERCE - PRODUCTS (5 tools) =====
  {
    name: 'shop_get_products',
    description: 'Get list of products.',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Number of items' },
        page: { type: 'number', description: 'Page number 1-100' },
        name: { type: 'string', description: 'Search by product name' },
        product_type_id: { type: 'number', description: 'Filter by product type ID' },
        vendor_id: { type: 'number', description: 'Filter by vendor ID' },
      },
      additionalProperties: false,
    },
  },
  {
    name: 'shop_get_product_info',
    description: 'Get product info by ID.',
    inputSchema: {
      type: 'object',
      properties: {
        productId: { type: 'number', description: 'Product ID (path param)' },
      },
      required: ['productId'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_create_product',
    description: 'Create new product.',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Product name' },
        description: { type: 'string', description: 'Description' },
        image: { type: 'string', description: 'Image URL' },
        note: { type: 'string', description: 'Note' },
        status: { type: 'string', description: 'Status: active' },
        type: { type: 'string', description: 'Product type name' },
        vendor: { type: 'string', description: 'Vendor name' },
        tags: { type: 'array', items: { type: 'string' }, description: 'Product tags' },
        use_variant: { type: 'number', description: '0 or 1' },
        price: { type: 'number', description: 'Price' },
        compare_price: { type: 'number', description: 'Compare at price' },
        sku: { type: 'string', description: 'SKU' },
        barcode: { type: 'string', description: 'Barcode' },
        track_stock: { type: 'number', description: '0 or 1' },
        allow_no_stock_sell: { type: 'number', description: '0 or 1' },
        qty: { type: 'number', description: 'Quantity' },
        variant_1_name: { type: 'string', description: 'Variant option 1 name (e.g. color)' },
        variant_2_name: { type: 'string', description: 'Variant option 2 name (e.g. size)' },
        variants: { type: 'array', description: 'Variants array', items: { type: 'object' } },
      },
      required: ['name'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_update_product',
    description: 'Update product info only. To update variants, use shop_update_product_variant.',
    inputSchema: {
      type: 'object',
      properties: {
        productId: { type: 'number', description: 'Product ID (path param)' },
        name: { type: 'string', description: 'Product name' },
        description: { type: 'string', description: 'Description' },
        image: { type: 'string', description: 'Image URL' },
        note: { type: 'string', description: 'Note' },
        status: { type: 'string', description: 'Status' },
        type: { type: 'string', description: 'Product type' },
        vendor: { type: 'string', description: 'Vendor' },
        tags: { type: 'array', items: { type: 'string' }, description: 'Tags' },
      },
      required: ['productId'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_delete_product',
    description: 'Delete product. Destructive.',
    inputSchema: {
      type: 'object',
      properties: {
        productId: { type: 'number', description: 'Product ID (path param)' },
      },
      required: ['productId'],
      additionalProperties: false,
    },
  },
  // ===== ECOMMERCE - PRODUCT TAGS (5 tools) =====
  {
    name: 'shop_get_product_tags',
    description: 'Get list of product tags.',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Number of items' },
        page: { type: 'number', description: 'Page number 1-100' },
        name: { type: 'string', description: 'Search by name' },
      },
      additionalProperties: false,
    },
  },
  {
    name: 'shop_get_product_tag_info',
    description: 'Get product tag info by ID.',
    inputSchema: {
      type: 'object',
      properties: { tagId: { type: 'number', description: 'Tag ID (path param)' } },
      required: ['tagId'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_create_product_tag',
    description: 'Create new product tag.',
    inputSchema: {
      type: 'object',
      properties: { name: { type: 'string', description: 'Tag name' } },
      required: ['name'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_update_product_tag',
    description: 'Update product tag name.',
    inputSchema: {
      type: 'object',
      properties: { tagId: { type: 'number', description: 'Tag ID (path param)' }, name: { type: 'string', description: 'New name' } },
      required: ['tagId', 'name'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_delete_product_tag',
    description: 'Delete product tag. Destructive.',
    inputSchema: {
      type: 'object',
      properties: { tagId: { type: 'number', description: 'Tag ID (path param)' } },
      required: ['tagId'],
      additionalProperties: false,
    },
  },

  // ===== ECOMMERCE - PRODUCT TYPES (5 tools) =====
  {
    name: 'shop_get_product_types',
    description: 'Get list of product types.',
    inputSchema: {
      type: 'object',
      properties: { limit: { type: 'number', description: 'Number of items' }, page: { type: 'number', description: 'Page 1-100' }, name: { type: 'string', description: 'Search by name' } },
      additionalProperties: false,
    },
  },
  {
    name: 'shop_get_product_type_info',
    description: 'Get product type info by ID.',
    inputSchema: {
      type: 'object',
      properties: { typeId: { type: 'number', description: 'Type ID (path param)' } },
      required: ['typeId'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_create_product_type',
    description: 'Create new product type.',
    inputSchema: {
      type: 'object',
      properties: { name: { type: 'string', description: 'Type name' } },
      required: ['name'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_update_product_type',
    description: 'Update product type name.',
    inputSchema: {
      type: 'object',
      properties: { typeId: { type: 'number', description: 'Type ID (path param)' }, name: { type: 'string', description: 'New name' } },
      required: ['typeId', 'name'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_delete_product_type',
    description: 'Delete product type. Destructive.',
    inputSchema: {
      type: 'object',
      properties: { typeId: { type: 'number', description: 'Type ID (path param)' } },
      required: ['typeId'],
      additionalProperties: false,
    },
  },

  // ===== ECOMMERCE - PRODUCT VENDORS (5 tools) =====
  {
    name: 'shop_get_product_vendors',
    description: 'Get list of product vendors.',
    inputSchema: {
      type: 'object',
      properties: { limit: { type: 'number', description: 'Number of items' }, page: { type: 'number', description: 'Page 1-100' }, name: { type: 'string', description: 'Search by name' } },
      additionalProperties: false,
    },
  },
  {
    name: 'shop_get_product_vendor_info',
    description: 'Get product vendor info by ID.',
    inputSchema: {
      type: 'object',
      properties: { vendorId: { type: 'number', description: 'Vendor ID (path param)' } },
      required: ['vendorId'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_create_product_vendor',
    description: 'Create new product vendor.',
    inputSchema: {
      type: 'object',
      properties: { name: { type: 'string', description: 'Vendor name' } },
      required: ['name'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_update_product_vendor',
    description: 'Update product vendor name.',
    inputSchema: {
      type: 'object',
      properties: { vendorId: { type: 'number', description: 'Vendor ID (path param)' }, name: { type: 'string', description: 'New name' } },
      required: ['vendorId', 'name'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_delete_product_vendor',
    description: 'Delete product vendor. Destructive.',
    inputSchema: {
      type: 'object',
      properties: { vendorId: { type: 'number', description: 'Vendor ID (path param)' } },
      required: ['vendorId'],
      additionalProperties: false,
    },
  },

  // ===== ECOMMERCE - BUSINESS HOURS (2 tools) =====
  {
    name: 'shop_get_business_hours',
    description: 'Get store business hours. Read-only.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'shop_update_business_hours',
    description: 'Update store business hours. Each day: id(1-7), name(Monday-Sunday), option(open/close/open_1/open_2), start/end times (00:00-24:00, step 00:15).',
    inputSchema: {
      type: 'object',
      properties: {
        data: { type: 'array', description: 'Array of day configs [{id:"1", name:"Monday", option:"open_2", start:"00:00", end:"08:15", start_2:"15:30", end_2:"18:45"}]', items: { type: 'object' } },
      },
      required: ['data'],
      additionalProperties: false,
    },
  },

  // ===== ECOMMERCE - LOCATIONS (5 tools) =====
  {
    name: 'shop_get_locations',
    description: 'Get list of store locations.',
    inputSchema: {
      type: 'object',
      properties: { limit: { type: 'number', description: 'Number of items' }, page: { type: 'number', description: 'Page 1-100' }, name: { type: 'string', description: 'Search by name' } },
      additionalProperties: false,
    },
  },
  {
    name: 'shop_get_location_info',
    description: 'Get location info by ID.',
    inputSchema: {
      type: 'object',
      properties: { locationId: { type: 'number', description: 'Location ID (path param)' } },
      required: ['locationId'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_create_location',
    description: 'Create new store location.',
    inputSchema: {
      type: 'object',
      properties: { name: { type: 'string', description: 'Location name' }, address: { type: 'string', description: 'Address' }, note: { type: 'string', description: 'Note' }, lat: { type: 'number', description: 'Latitude' }, lng: { type: 'number', description: 'Longitude' } },
      required: ['name'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_update_location',
    description: 'Update store location.',
    inputSchema: {
      type: 'object',
      properties: { locationId: { type: 'number', description: 'Location ID (path param)' }, name: { type: 'string', description: 'Name' }, address: { type: 'string', description: 'Address' }, note: { type: 'string', description: 'Note' }, lat: { type: 'number', description: 'Latitude' }, lng: { type: 'number', description: 'Longitude' } },
      required: ['locationId'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_delete_location',
    description: 'Delete store location. Destructive.',
    inputSchema: {
      type: 'object',
      properties: { locationId: { type: 'number', description: 'Location ID (path param)' } },
      required: ['locationId'],
      additionalProperties: false,
    },
  },
  // ===== ECOMMERCE - PRODUCT VARIANTS (5 tools) =====
  {
    name: 'shop_get_product_variants',
    description: 'Get list of product variants.',
    inputSchema: {
      type: 'object',
      properties: { productId: { type: 'number', description: 'Product ID (path param)' }, limit: { type: 'number', description: 'Number of items' }, page: { type: 'number', description: 'Page 1-100' } },
      required: ['productId'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_get_product_variant_info',
    description: 'Get product variant info.',
    inputSchema: {
      type: 'object',
      properties: { productId: { type: 'number', description: 'Product ID (path param)' }, variantId: { type: 'number', description: 'Variant ID (path param)' } },
      required: ['productId', 'variantId'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_create_product_variant',
    description: 'Create new product variant.',
    inputSchema: {
      type: 'object',
      properties: {
        productId: { type: 'number', description: 'Product ID (path param)' },
        image: { type: 'string', description: 'Image URL' },
        variant_1_value: { type: 'string', description: 'Variant option 1 value (e.g. blue)' },
        variant_2_value: { type: 'string', description: 'Variant option 2 value (e.g. large)' },
        price: { type: 'number', description: 'Price' },
        compare_price: { type: 'number', description: 'Compare at price' },
        taxable: { type: 'number', description: '0 or 1' },
        sku: { type: 'string', description: 'SKU' },
        barcode: { type: 'string', description: 'Barcode' },
        track_stock: { type: 'number', description: '0 or 1' },
        allow_no_stock_sell: { type: 'number', description: '0 or 1' },
        qty: { type: 'number', description: 'Quantity' },
      },
      required: ['productId'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_update_product_variant',
    description: 'Update product variant.',
    inputSchema: {
      type: 'object',
      properties: {
        productId: { type: 'number', description: 'Product ID (path param)' },
        variantId: { type: 'number', description: 'Variant ID (path param)' },
        image: { type: 'string', description: 'Image URL' },
        variant_1_value: { type: 'string', description: 'Variant option 1 value' },
        variant_2_value: { type: 'string', description: 'Variant option 2 value' },
        price: { type: 'number', description: 'Price' },
        compare_price: { type: 'number', description: 'Compare at price' },
        taxable: { type: 'number', description: '0 or 1' },
        sku: { type: 'string', description: 'SKU' },
        barcode: { type: 'string', description: 'Barcode' },
        track_stock: { type: 'number', description: '0 or 1' },
        allow_no_stock_sell: { type: 'number', description: '0 or 1' },
        qty: { type: 'number', description: 'Quantity' },
      },
      required: ['productId', 'variantId'],
      additionalProperties: false,
    },
  },
  {
    name: 'shop_delete_product_variant',
    description: 'Delete product variant. Destructive.',
    inputSchema: {
      type: 'object',
      properties: { productId: { type: 'number', description: 'Product ID (path param)' }, variantId: { type: 'number', description: 'Variant ID (path param)' } },
      required: ['productId', 'variantId'],
      additionalProperties: false,
    },
  },

  // ===== TEMPLATES (3 tools) =====
  {
    name: 'get_templates',
    description: 'Get list of flow templates.',
    inputSchema: {
      type: 'object',
      properties: { limit: { type: 'number', description: 'Number of items' }, page: { type: 'number', description: 'Page 1-100' }, name: { type: 'string', description: 'Search by name' } },
      additionalProperties: false,
    },
  },
  {
    name: 'get_template_installs',
    description: 'Get list of installs by template namespace.',
    inputSchema: {
      type: 'object',
      properties: { templateNs: { type: 'string', description: 'Template namespace (path param)' }, limit: { type: 'number', description: 'Number of items' }, page: { type: 'number', description: 'Page 1-100' } },
      required: ['templateNs'],
      additionalProperties: false,
    },
  },
  {
    name: 'generate_template_link',
    description: 'Generate one-time install link for a template.',
    inputSchema: {
      type: 'object',
      properties: { templateNs: { type: 'string', description: 'Template namespace (path param)' }, days: { type: 'number', description: 'Days until link expires (default: 30)' } },
      required: ['templateNs'],
      additionalProperties: false,
    },
  },

  // ===== TICKET LISTS (7 tools) =====
  {
    name: 'get_ticket_lists',
    description: 'Get list of ticket lists (boards).',
    inputSchema: {
      type: 'object',
      properties: { limit: { type: 'number', description: 'Number of items' }, page: { type: 'number', description: 'Page 1-100' }, name: { type: 'string', description: 'Search by name' } },
      additionalProperties: false,
    },
  },
  {
    name: 'get_ticket_list_fields',
    description: 'Get fields of a ticket list.',
    inputSchema: {
      type: 'object',
      properties: { listId: { type: 'number', description: 'List ID (path param)' } },
      required: ['listId'],
      additionalProperties: false,
    },
  },
  {
    name: 'get_ticket_list_items',
    description: 'Get items (tickets) in a ticket list.',
    inputSchema: {
      type: 'object',
      properties: {
        listId: { type: 'number', description: 'List ID (path param)' },
        limit: { type: 'number', description: 'Number of items' },
        page: { type: 'number', description: 'Page 1-100' },
        title: { type: 'string', description: 'Search by title' },
        flow_ns: { type: 'string', description: 'Filter by flow_ns' },
        user_ns: { type: 'string', description: 'Filter by user_ns' },
      },
      required: ['listId'],
      additionalProperties: false,
    },
  },
  {
    name: 'get_ticket_list_log_data',
    description: 'Get ticket list change log data.',
    inputSchema: {
      type: 'object',
      properties: {
        listId: { type: 'number', description: 'List ID (path param)' },
        start_time: { type: 'number', description: 'Unix timestamp (6 months ago to now)' },
        end_time: { type: 'number', description: 'Unix timestamp' },
        flow_ns: { type: 'string', description: 'Filter by flow_ns' },
        user_ns: { type: 'string', description: 'Filter by user_ns' },
        list_item_id: { type: 'number', description: 'Filter by list item ID' },
        column_name: { type: 'string', description: 'Filter by column: select1-5' },
        limit: { type: 'number', description: 'Number of items 1-100' },
      },
      required: ['listId'],
      additionalProperties: false,
    },
  },
  {
    name: 'create_ticket',
    description: 'Create new ticket in a list.',
    inputSchema: {
      type: 'object',
      properties: {
        listId: { type: 'number', description: 'List ID (path param)' },
        title: { type: 'string', description: 'Ticket title' },
        user_ns: { type: 'string', description: 'Subscriber user_ns' },
        description: { type: 'string', description: 'Description' },
        assignee: { type: 'number', description: 'Assignee agent ID' },
        text1: { type: 'string' }, text2: { type: 'string' }, text3: { type: 'string' }, text4: { type: 'string' }, text5: { type: 'string' },
        select1: { type: 'string' }, select2: { type: 'string' }, select3: { type: 'string' }, select4: { type: 'string' }, select5: { type: 'string' },
        number1: { type: 'number' }, number2: { type: 'number' },
        rating1: { type: 'number' }, rating2: { type: 'number' },
        date1: { type: 'string' }, date2: { type: 'string' },
      },
      required: ['listId', 'title'],
      additionalProperties: false,
    },
  },
  {
    name: 'update_ticket',
    description: 'Update a ticket. Include only fields that need to change.',
    inputSchema: {
      type: 'object',
      properties: {
        listId: { type: 'number', description: 'List ID (path param)' },
        listItemId: { type: 'number', description: 'Ticket item ID (path param)' },
        title: { type: 'string', description: 'Title' },
        description: { type: 'string', description: 'Description' },
        assignee: { type: 'number', description: 'Assignee agent ID' },
        text1: { type: 'string' }, text2: { type: 'string' }, text3: { type: 'string' }, text4: { type: 'string' }, text5: { type: 'string' },
        select1: { type: 'string' }, select2: { type: 'string' }, select3: { type: 'string' }, select4: { type: 'string' }, select5: { type: 'string' },
        number1: { type: 'number' }, number2: { type: 'number' },
        rating1: { type: 'number' }, rating2: { type: 'number' },
        date1: { type: 'string' }, date2: { type: 'string' },
      },
      required: ['listId', 'listItemId'],
      additionalProperties: false,
    },
  },
  {
    name: 'delete_ticket',
    description: 'Delete a ticket. Destructive.',
    inputSchema: {
      type: 'object',
      properties: { listId: { type: 'number', description: 'List ID (path param)' }, listItemId: { type: 'number', description: 'Ticket item ID (path param)' } },
      required: ['listId', 'listItemId'],
      additionalProperties: false,
    },
  },

  // ===== TEAM LABELS (4 tools) =====
  {
    name: 'get_team_labels',
    description: 'Get list of team labels.',
    inputSchema: {
      type: 'object',
      properties: { limit: { type: 'number', description: 'Number of items' }, page: { type: 'number', description: 'Page 1-100' }, name: { type: 'string', description: 'Search by name' } },
      additionalProperties: false,
    },
  },
  {
    name: 'create_team_label',
    description: 'Create new team label.',
    inputSchema: {
      type: 'object',
      properties: { name: { type: 'string', description: 'Label name' } },
      required: ['name'],
      additionalProperties: false,
    },
  },
  {
    name: 'delete_team_label',
    description: 'Delete team label by ID. Destructive.',
    inputSchema: {
      type: 'object',
      properties: { id: { type: 'number', description: 'Label ID' } },
      required: ['id'],
      additionalProperties: false,
    },
  },
  {
    name: 'delete_team_label_by_name',
    description: 'Delete team label by name. Destructive.',
    inputSchema: {
      type: 'object',
      properties: { name: { type: 'string', description: 'Label name' } },
      required: ['name'],
      additionalProperties: false,
    },
  },
  // ===== INTEGRATIONS (20 tools) =====
  {
    name: 'get_shopify_integration',
    description: 'Get Shopify integration config. Read-only.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'update_shopify_integration',
    description: 'Update Shopify integration. For new custom apps after 2026-02-01, use Client ID in api_key and Client Secret in token.',
    inputSchema: {
      type: 'object',
      properties: { url: { type: 'string', description: 'Shopify store URL (xxx.myshopify.com)' }, api_key: { type: 'string', description: 'API key or Client ID' }, token: { type: 'string', description: 'Token or Client Secret' }, wait_time: { type: 'number', description: 'Wait time in seconds (default: 30)' } },
      additionalProperties: false,
    },
  },
  {
    name: 'delete_shopify_integration',
    description: 'Clear Shopify integration config. Destructive.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'get_woocommerce_integration',
    description: 'Get WooCommerce integration config. Read-only.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'update_woocommerce_integration',
    description: 'Update WooCommerce integration config.',
    inputSchema: {
      type: 'object',
      properties: { url: { type: 'string', description: 'WooCommerce store URL' }, api_key: { type: 'string', description: 'Consumer key' }, token: { type: 'string', description: 'Consumer secret' } },
      additionalProperties: false,
    },
  },
  {
    name: 'delete_woocommerce_integration',
    description: 'Clear WooCommerce integration config. Destructive.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'get_dropi_integration',
    description: 'Get Dropi integration config. Read-only.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'update_dropi_integration',
    description: 'Update Dropi integration config.',
    inputSchema: {
      type: 'object',
      properties: { url: { type: 'string', description: 'Dropi API URL (default: https://api.dropi.co/)' }, api_key: { type: 'string', description: 'Dropi API key' } },
      additionalProperties: false,
    },
  },
  {
    name: 'delete_dropi_integration',
    description: 'Clear Dropi integration config. Destructive.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'get_meta_conversions_api_integration',
    description: 'Get Meta Conversions API integration config. Read-only.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'update_meta_conversions_api_integration',
    description: 'Update Meta Conversions API integration config.',
    inputSchema: {
      type: 'object',
      properties: { token: { type: 'string', description: 'Access token' }, dataset_id: { type: 'string', description: 'Dataset ID' } },
      additionalProperties: false,
    },
  },
  {
    name: 'delete_meta_conversions_api_integration',
    description: 'Clear Meta Conversions API integration config. Destructive.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'get_openai_integration',
    description: 'Get OpenAI integration config. Read-only.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'update_openai_integration',
    description: 'Update OpenAI integration config.',
    inputSchema: {
      type: 'object',
      properties: { api_key: { type: 'string', description: 'OpenAI API key' }, org_id: { type: 'string', description: 'Organization ID (optional)' } },
      additionalProperties: false,
    },
  },
  {
    name: 'delete_openai_integration',
    description: 'Clear OpenAI integration config. Destructive.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'get_s3storage_integration',
    description: 'Get S3 Storage integration config. Read-only.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'update_s3storage_integration',
    description: 'Update S3 Storage integration config.',
    inputSchema: {
      type: 'object',
      properties: { url: { type: 'string', description: 'S3 endpoint URL' }, api_key: { type: 'string', description: 'Access key' }, secret: { type: 'string', description: 'Secret key' }, bucket: { type: 'string', description: 'Bucket name' }, region: { type: 'string', description: 'AWS region' } },
      additionalProperties: false,
    },
  },
  {
    name: 'delete_s3storage_integration',
    description: 'Clear S3 Storage integration config. Destructive.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'get_installed_mini_apps',
    description: 'Get list of installed mini apps.',
    inputSchema: {
      type: 'object',
      properties: { limit: { type: 'number', description: 'Number of items' }, page: { type: 'number', description: 'Page 1-100' }, title: { type: 'string', description: 'Search by app title' } },
      additionalProperties: false,
    },
  },
  {
    name: 'update_mini_app_api_key',
    description: 'Update API key for installed mini app (only for auth_type=apikey).',
    inputSchema: {
      type: 'object',
      properties: { app_id: { type: 'number', description: 'Mini App ID (path param)' }, api_key: { type: 'string', description: 'New API key' } },
      required: ['app_id', 'api_key'],
      additionalProperties: false,
    },
  },

  // ===== OPENAI EMBEDDINGS (7 tools) =====
  {
    name: 'get_openai_embeddings',
    description: 'Get list of OpenAI embeddings.',
    inputSchema: {
      type: 'object',
      properties: { limit: { type: 'number', description: 'Number of items' }, page: { type: 'number', description: 'Page 1-100' }, heading: { type: 'string', description: 'Search by heading' }, text: { type: 'string', description: 'Search by text' } },
      additionalProperties: false,
    },
  },
  {
    name: 'get_openai_embedding_info',
    description: 'Get embedding info by ID.',
    inputSchema: {
      type: 'object',
      properties: { id: { type: 'number', description: 'Embedding ID (path param)' } },
      required: ['id'],
      additionalProperties: false,
    },
  },
  {
    name: 'create_openai_embedding',
    description: 'Create new embedding entry.',
    inputSchema: {
      type: 'object',
      properties: { type: { type: 'string', description: 'Type' }, heading: { type: 'string', description: 'Heading (max 50 chars)' }, text: { type: 'string', description: 'Text (max 1000 chars)' } },
      required: ['heading', 'text'],
      additionalProperties: false,
    },
  },
  {
    name: 'update_openai_embedding',
    description: 'Update embedding heading and text.',
    inputSchema: {
      type: 'object',
      properties: { id: { type: 'number', description: 'Embedding ID (path param)' }, type: { type: 'string', description: 'Type' }, heading: { type: 'string', description: 'Heading' }, text: { type: 'string', description: 'Text' } },
      required: ['id'],
      additionalProperties: false,
    },
  },
  {
    name: 'delete_openai_embedding',
    description: 'Delete embedding. Destructive.',
    inputSchema: {
      type: 'object',
      properties: { id: { type: 'number', description: 'Embedding ID (path param)' } },
      required: ['id'],
      additionalProperties: false,
    },
  },
  {
    name: 'import_openai_embeddings',
    description: 'Import embeddings (max 100). Each: heading max 50 chars, text max 1000 chars.',
    inputSchema: {
      type: 'object',
      properties: { rows: { type: 'array', description: 'Array of embeddings [{type, heading, text}]', items: { type: 'object', properties: { type: { type: 'string' }, heading: { type: 'string' }, text: { type: 'string' } } } } },
      required: ['rows'],
      additionalProperties: false,
    },
  },
  {
    name: 'generate_openai_embeddings',
    description: 'Regenerate all embeddings.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  // ===== WORKSPACE (10 tools) =====
  {
    name: 'get_flow_summary',
    description: 'Get flow analytics summary.',
    inputSchema: {
      type: 'object',
      properties: { range: { type: 'string', description: 'Range: yesterday, last_7_days, last_week, last_30_days, last_month, last_3_months' }, flow_ns: { type: 'string', description: 'Filter by specific bot flow_ns' } },
      additionalProperties: false,
    },
  },
  {
    name: 'get_flow_agent_summary',
    description: 'Get agent performance summary.',
    inputSchema: {
      type: 'object',
      properties: { range: { type: 'string', description: 'Range: yesterday, last_7_days, last_week, last_30_days, last_month, last_3_months' }, flow_ns: { type: 'string', description: 'Filter by specific bot flow_ns' } },
      additionalProperties: false,
    },
  },
  {
    name: 'get_team_bot_users',
    description: 'Get list of bot users across workspace.',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Number of items 1-100' },
        page: { type: 'number', description: 'Page 1-1000' },
        name: { type: 'string', description: 'Search by name' },
        phone: { type: 'string', description: 'Search by phone' },
        email: { type: 'string', description: 'Search by email' },
        is_channel: { type: 'string', description: 'Filter by channel' },
        is_opt_in_email: { type: 'string', description: 'yes or no' },
        is_opt_in_sms: { type: 'string', description: 'yes or no' },
        is_interacted_in_last_24h: { type: 'string', description: 'yes or no' },
        is_bot_interacted_in_last_24h: { type: 'string', description: 'yes or no' },
        is_last_message_in_last_24h: { type: 'string', description: 'yes or no' },
      },
      additionalProperties: false,
    },
  },
  {
    name: 'get_team_flows',
    description: 'Get list of workspace bots/flows.',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Number of items' },
        page: { type: 'number', description: 'Page 1-100' },
        name: { type: 'string', description: 'Search by bot name' },
        type: { type: 'string', description: 'Filter by channel type: web, facebook, instagram, whatsapp, whatsapp_cloud, telegram, etc.' },
      },
      additionalProperties: false,
    },
  },
  {
    name: 'get_team_info',
    description: 'Get workspace info. Read-only.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'get_workspace_channels',
    description: 'Get workspace channel settings. Read-only.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'update_workspace_channels',
    description: 'Show/hide workspace channels. Pass channel name with 1 (show) or 0 (hide).',
    inputSchema: {
      type: 'object',
      properties: {
        chat: { type: 'number' }, facebook: { type: 'number' }, instagram: { type: 'number' }, telegram: { type: 'number' },
        slack: { type: 'number' }, whatsapp: { type: 'number' }, whatsapp_cloud: { type: 'number' }, wechat: { type: 'number' },
        voice: { type: 'number' }, sms: { type: 'number' }, rcs: { type: 'number' }, line: { type: 'number' },
        viber: { type: 'number' }, vk: { type: 'number' }, intercom: { type: 'number' }, jivochat: { type: 'number' },
        chatwoot: { type: 'number' }, tiktok: { type: 'number' },
      },
      additionalProperties: false,
    },
  },
  {
    name: 'get_workspace_live_chat_sidebar',
    description: 'Get live chat sidebar settings. Read-only.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'update_workspace_live_chat_sidebar',
    description: 'Update live chat sidebar settings. Pass array of hide/show values.',
    inputSchema: {
      type: 'object',
      properties: {
        data: { type: 'array', items: { type: 'string' }, description: 'Array of settings (e.g. ["hide_unanswered","show_labels","show_boards"])' },
      },
      required: ['data'],
      additionalProperties: false,
    },
  },
  {
    name: 'get_team_members',
    description: 'Get list of workspace members.',
    inputSchema: {
      type: 'object',
      properties: { limit: { type: 'number', description: 'Number of items' }, page: { type: 'number', description: 'Page 1-100' }, name: { type: 'string', description: 'Search by name' }, role: { type: 'string', description: 'Filter by role: owner, admin, member, agent' } },
      additionalProperties: false,
    },
  },

  // ===== USER (5 tools) =====
  {
    name: 'get_current_user',
    description: 'Get current authenticated user info. Read-only.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'change_user_password',
    description: 'Change current user password.',
    inputSchema: {
      type: 'object',
      properties: { current_password: { type: 'string', description: 'Current password' }, password: { type: 'string', description: 'New password' }, password_confirmation: { type: 'string', description: 'Confirm new password' } },
      required: ['current_password', 'password', 'password_confirmation'],
      additionalProperties: false,
    },
  },
  {
    name: 'get_recent_notifications',
    description: 'Get recent notifications and announcements. Read-only.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'mark_notification_read',
    description: 'Mark notification as read.',
    inputSchema: {
      type: 'object',
      properties: { notification_id: { type: 'string', description: 'Notification ID (UUID)' } },
      required: ['notification_id'],
      additionalProperties: false,
    },
  },
  {
    name: 'mark_announcement_read',
    description: 'Mark announcements as read.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
];
