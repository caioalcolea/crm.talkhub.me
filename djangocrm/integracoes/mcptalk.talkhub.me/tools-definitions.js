// Complete tool definitions for TalkHub MCP Server
export const toolDefinitions = [
  // ===== FLOW MANAGEMENT (10 tools) =====
  {
    name: 'flow_get_subflows',
    description: 'Get list of sub-flows with pagination and search',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Number of items (default: 10)' },
        page: { type: 'number', description: 'Page number 1-100 (default: 1)' },
        name: { type: 'string', description: 'Search by sub-flow name' },
      },
    },
  },
  {
    name: 'flow_delete_subflow',
    description: 'Delete a sub-flow by namespace',
    inputSchema: {
      type: 'object',
      properties: {
        sub_flow_ns: { type: 'string', description: 'Sub-flow namespace' },
      },
      required: ['sub_flow_ns'],
    },
  },
  {
    name: 'flow_get_bot_users_count',
    description: 'Get count of bot users by status',
    inputSchema: { type: 'object', properties: {} },
  },
  {
    name: 'flow_get_agents',
    description: 'Get list of agents with filters',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Number of items' },
        page: { type: 'number', description: 'Page number 1-100' },
        name: { type: 'string', description: 'Search by agent name' },
        role: { type: 'string', description: 'Filter by role: owner, admin, member, agent' },
      },
    },
  },
  {
    name: 'flow_get_template_installs',
    description: 'Get list of template installations in this flow',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Number of items' },
        page: { type: 'number', description: 'Page number 1-100' },
      },
    },
  },
  {
    name: 'flow_set_default_start_flow',
    description: 'Set default bot start flow (use "main" to reset)',
    inputSchema: {
      type: 'object',
      properties: {
        sub_flow_ns: { type: 'string', description: 'Sub-flow namespace or "main"' },
      },
      required: ['sub_flow_ns'],
    },
  },
  {
    name: 'flow_set_web_chat_widget_start_flow',
    description: 'Set default start flow for web chat widget',
    inputSchema: {
      type: 'object',
      properties: {
        sub_flow_ns: { type: 'string', description: 'Sub-flow namespace or "main"' },
      },
      required: ['sub_flow_ns'],
    },
  },
  {
    name: 'flow_set_audio_transcription',
    description: 'Set audio transcription model: none, whisper-1, gpt-4o-transcribe, gpt-4o-mini-transcribe',
    inputSchema: {
      type: 'object',
      properties: {
        stt_model: { type: 'string', description: 'STT model name' },
      },
      required: ['stt_model'],
    },
  },
  {
    name: 'flow_get_inbound_webhooks',
    description: 'Get list of inbound webhooks',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Number of items' },
        page: { type: 'number', description: 'Page number 1-100' },
        name: { type: 'string', description: 'Search by name' },
      },
    },
  },
  {
    name: 'flow_get_chat_button_widgets',
    description: 'Get list of chat button widgets',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Number of items' },
        page: { type: 'number', description: 'Page number 1-100' },
        code: { type: 'string', description: 'Filter by widget code' },
      },
    },
  },

  // ===== FLOW TAGS (4 tools) =====
  {
    name: 'flow_get_tags',
    description: 'Get list of tags by flow',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Number of items' },
        page: { type: 'number', description: 'Page number 1-100' },
        name: { type: 'string', description: 'Search by tag name' },
      },
    },
  },
  {
    name: 'flow_create_tag',
    description: 'Create new tag',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Tag name' },
      },
      required: ['name'],
    },
  },
  {
    name: 'flow_delete_tag',
    description: 'Delete tag by namespace',
    inputSchema: {
      type: 'object',
      properties: {
        tag_ns: { type: 'string', description: 'Tag namespace' },
      },
      required: ['tag_ns'],
    },
  },
  {
    name: 'flow_delete_tag_by_name',
    description: 'Delete tag by name',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Tag name' },
      },
      required: ['name'],
    },
  },

  // ===== FLOW USER FIELDS (5 tools) =====
  {
    name: 'flow_get_user_fields',
    description: 'Get list of user custom fields',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Number of items' },
        page: { type: 'number', description: 'Page number 1-100' },
        name: { type: 'string', description: 'Search by field name' },
      },
    },
  },
  {
    name: 'flow_create_user_field',
    description: 'Create new user custom field',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Field name' },
        var_ns: { type: 'string', description: 'Variable namespace' },
        var_type: { type: 'string', description: 'Type: text, number, boolean, date, datetime' },
        description: { type: 'string', description: 'Field description' },
        value: { type: 'string', description: 'Default value' },
      },
      required: ['name', 'var_ns', 'var_type'],
    },
  },
  {
    name: 'flow_update_user_field',
    description: 'Update user field name or display_type',
    inputSchema: {
      type: 'object',
      properties: {
        var_ns: { type: 'string', description: 'Variable namespace' },
        name: { type: 'string', description: 'New field name' },
        display_type: { type: 'string', description: 'Display type' },
      },
      required: ['var_ns'],
    },
  },
  {
    name: 'flow_delete_user_field',
    description: 'Delete user field by namespace',
    inputSchema: {
      type: 'object',
      properties: {
        var_ns: { type: 'string', description: 'Variable namespace' },
      },
      required: ['var_ns'],
    },
  },
  {
    name: 'flow_delete_user_field_by_name',
    description: 'Delete user field by name',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Field name' },
      },
      required: ['name'],
    },
  },

  // ===== FLOW BOT FIELDS (8 tools) =====
  {
    name: 'flow_get_bot_fields',
    description: 'Get list of bot custom fields',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Number of items' },
        page: { type: 'number', description: 'Page number 1-100' },
        name: { type: 'string', description: 'Search by field name' },
      },
    },
  },
  {
    name: 'flow_create_bot_field',
    description: 'Create new bot custom field',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Field name' },
        var_ns: { type: 'string', description: 'Variable namespace' },
        var_type: { type: 'string', description: 'Type: text, number, boolean, date, datetime' },
        description: { type: 'string', description: 'Field description' },
        value: { type: 'string', description: 'Default value' },
        is_template_field: { type: 'boolean', description: 'Is template field' },
      },
      required: ['name', 'var_ns', 'var_type'],
    },
  },
  {
    name: 'flow_set_bot_field',
    description: 'Update bot field value by namespace',
    inputSchema: {
      type: 'object',
      properties: {
        var_ns: { type: 'string', description: 'Variable namespace' },
        value: { type: 'string', description: 'New value' },
      },
      required: ['var_ns', 'value'],
    },
  },
  {
    name: 'flow_set_bot_field_by_name',
    description: 'Update bot field value by name',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Field name' },
        value: { type: 'string', description: 'New value' },
      },
      required: ['name', 'value'],
    },
  },
  {
    name: 'flow_set_bot_fields',
    description: 'Update multiple bot fields (up to 20)',
    inputSchema: {
      type: 'object',
      properties: {
        data: {
          type: 'array',
          description: 'Array of field updates',
          items: {
            type: 'object',
            properties: {
              var_ns: { type: 'string' },
              value: { type: 'string' },
            },
          },
        },
      },
      required: ['data'],
    },
  },
  {
    name: 'flow_set_bot_fields_by_name',
    description: 'Update multiple bot fields by name (up to 20)',
    inputSchema: {
      type: 'object',
      properties: {
        data: {
          type: 'array',
          description: 'Array of field updates',
          items: {
            type: 'object',
            properties: {
              name: { type: 'string' },
              value: { type: 'string' },
            },
          },
        },
      },
      required: ['data'],
    },
  },
  {
    name: 'flow_delete_bot_field',
    description: 'Delete bot field by namespace',
    inputSchema: {
      type: 'object',
      properties: {
        var_ns: { type: 'string', description: 'Variable namespace' },
      },
      required: ['var_ns'],
    },
  },
  {
    name: 'flow_delete_bot_field_by_name',
    description: 'Delete bot field by name',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Field name' },
      },
      required: ['name'],
    },
  },

  // ===== AI HUB (2 tools) =====
  {
    name: 'flow_get_ai_agents',
    description: 'Get list of AI agents',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Number of items' },
        page: { type: 'number', description: 'Page number 1-100' },
        ai_agent_ns: { type: 'string', description: 'Search by AI agent namespace' },
        ai_provider: { type: 'string', description: 'Filter by provider: openai, deepseek, xai, claude, gemini, groq' },
        name: { type: 'string', description: 'Search by name' },
      },
    },
  },
  {
    name: 'flow_update_ai_agent_provider',
    description: 'Update AI agent provider and model',
    inputSchema: {
      type: 'object',
      properties: {
        ai_agent_ns: { type: 'string', description: 'AI agent namespace' },
        ai_provider: { type: 'string', description: 'Provider: openai, deepseek, xai, claude, gemini, groq' },
        ai_model: { type: 'string', description: 'Model name' },
        max_tokens: { type: 'number', description: 'Max tokens' },
      },
      required: ['ai_agent_ns', 'ai_provider', 'ai_model'],
    },
  },

  // ===== SEGMENTS (1 tool) =====
  {
    name: 'flow_get_segments',
    description: 'Get list of user segments',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Number of items' },
        page: { type: 'number', description: 'Page number 1-100' },
        name: { type: 'string', description: 'Search by segment name' },
      },
    },
  },

  // ===== CUSTOM EVENTS (3 tools) =====
  {
    name: 'flow_get_custom_events',
    description: 'Get list of custom events',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Number of items' },
        page: { type: 'number', description: 'Page number 1-100' },
        name: { type: 'string', description: 'Search by event name' },
      },
    },
  },
  {
    name: 'flow_get_custom_events_summary',
    description: 'Get custom event summary with statistics',
    inputSchema: {
      type: 'object',
      properties: {
        range: { type: 'string', description: 'Range: yesterday, last_7_days, last_week, last_30_days, last_month, last_3_months' },
        event_ns: { type: 'string', description: 'Event namespace (required)' },
      },
      required: ['event_ns'],
    },
  },
  {
    name: 'flow_get_custom_events_data',
    description: 'Get custom event data',
    inputSchema: {
      type: 'object',
      properties: {
        start_time: { type: 'number', description: 'Unix timestamp (6 months ago to now)' },
        end_time: { type: 'number', description: 'Unix timestamp (6 months ago to now)' },
        event_ns: { type: 'string', description: 'Event namespace (required)' },
        start_id: { type: 'number', description: 'Starting from ID' },
        limit: { type: 'number', description: 'Number of items 1-100' },
      },
      required: ['event_ns'],
    },
  },

  // ===== CONVERSATIONS (2 tools) =====
  {
    name: 'flow_get_agent_activity_log',
    description: 'Get agent activity log data',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns' },
        agent_id: { type: 'number', description: 'Agent ID' },
        conv_id: { type: 'number', description: 'Conversation ID' },
        action: { type: 'string', description: 'Action: open, close, assign, reply, note, pending, spam, invalid' },
        source_type: { type: 'string', description: 'Source: agent, bot, bot_user, api, webhook' },
        start_time: { type: 'number', description: 'Unix timestamp' },
        end_time: { type: 'number', description: 'Unix timestamp' },
        limit: { type: 'number', description: 'Number of items 1-1000' },
      },
    },
  },
  {
    name: 'flow_get_conversations_data',
    description: 'Get conversations data (closed conversations only)',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns' },
        start_time: { type: 'number', description: 'Unix timestamp' },
        end_time: { type: 'number', description: 'Unix timestamp' },
        start_id: { type: 'number', description: 'Starting from ID' },
        limit: { type: 'number', description: 'Number of items 1-1000' },
      },
    },
  },

  // ===== WHATSAPP TEMPLATES (4 tools) =====
  {
    name: 'whatsapp_list_templates',
    description: 'List WhatsApp templates',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Number of items' },
        page: { type: 'number', description: 'Page number 1-100' },
        name: { type: 'string', description: 'Search by template name' },
      },
    },
  },
  {
    name: 'whatsapp_create_template',
    description: 'Create WhatsApp template',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Template name' },
        language: { type: 'string', description: 'Language code' },
        category: { type: 'string', description: 'Category' },
        components: { type: 'array', description: 'Template components' },
      },
      required: ['name', 'language', 'category', 'components'],
    },
  },
  {
    name: 'whatsapp_delete_template',
    description: 'Delete WhatsApp template',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Template name' },
      },
      required: ['name'],
    },
  },
  {
    name: 'whatsapp_sync_templates',
    description: 'Sync WhatsApp templates',
    inputSchema: { type: 'object', properties: {} },
  },
];
