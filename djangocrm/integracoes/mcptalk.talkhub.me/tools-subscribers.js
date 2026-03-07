// Subscriber and Sending tool definitions
export const subscriberTools = [
  // ===== SUBSCRIBERS (39 tools) =====
  {
    name: 'subscriber_get_list',
    description: 'Get list of subscribers with advanced search filters',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Number of items 1-100' },
        page: { type: 'number', description: 'Page number 1-1000' },
        name: { type: 'string', description: 'Search by name' },
        phone: { type: 'string', description: 'Search by phone' },
        email: { type: 'string', description: 'Search by email' },
        is_channel: { type: 'string', description: 'Channel: facebook, instagram, whatsapp_cloud, telegram, etc.' },
        is_opt_in_email: { type: 'string', description: 'Opted in email: yes, no' },
        is_opt_in_sms: { type: 'string', description: 'Opted in SMS: yes, no' },
        is_interacted_in_last_24h: { type: 'string', description: 'Interacted in last 24h: yes, no' },
        is_bot_interacted_in_last_24h: { type: 'string', description: 'Bot interacted in last 24h: yes, no' },
        is_last_message_in_last_24h: { type: 'string', description: 'Last message in last 24h: yes, no' },
        tag_ns: { type: 'string', description: 'Filter by tag namespace' },
        label_id: { type: 'number', description: 'Filter by label ID' },
        event_ns: { type: 'string', description: 'Filter by custom event namespace' },
        user_field_ns: { type: 'string', description: 'Filter by user field namespace' },
        user_field_value: { type: 'string', description: 'User field value to match' },
      },
    },
  },
  {
    name: 'subscriber_get_info',
    description: 'Get subscriber information by user_ns',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
      },
      required: ['user_ns'],
    },
  },
  {
    name: 'subscriber_get_info_by_user_id',
    description: 'Get subscriber info by unique channel user ID (Facebook ID, WhatsApp ID, etc.)',
    inputSchema: {
      type: 'object',
      properties: {
        user_id: { type: 'string', description: 'Channel user ID (required)' },
      },
      required: ['user_id'],
    },
  },
  {
    name: 'subscriber_create',
    description: 'Create new subscriber (phone or email required)',
    inputSchema: {
      type: 'object',
      properties: {
        first_name: { type: 'string', description: 'First name' },
        last_name: { type: 'string', description: 'Last name' },
        name: { type: 'string', description: 'Full name' },
        phone: { type: 'string', description: 'Phone number' },
        email: { type: 'string', description: 'Email address' },
        gender: { type: 'string', description: 'Gender' },
        image: { type: 'string', description: 'Profile image URL' },
      },
    },
  },
  {
    name: 'subscriber_update',
    description: 'Update subscriber data',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        first_name: { type: 'string', description: 'First name' },
        last_name: { type: 'string', description: 'Last name' },
        name: { type: 'string', description: 'Full name' },
        phone: { type: 'string', description: 'Phone number' },
        email: { type: 'string', description: 'Email address' },
        gender: { type: 'string', description: 'Gender' },
        image: { type: 'string', description: 'Profile image URL' },
      },
      required: ['user_ns'],
    },
  },
  {
    name: 'subscriber_delete',
    description: 'Delete subscriber',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
      },
      required: ['user_ns'],
    },
  },
  {
    name: 'subscriber_add_tag',
    description: 'Add single tag to subscriber',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        tag_ns: { type: 'string', description: 'Tag namespace (required)' },
      },
      required: ['user_ns', 'tag_ns'],
    },
  },
  {
    name: 'subscriber_add_tags',
    description: 'Add multiple tags to subscriber (up to 20)',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        data: {
          type: 'array',
          description: 'Array of tags',
          items: {
            type: 'object',
            properties: {
              tag_ns: { type: 'string' },
            },
          },
        },
      },
      required: ['user_ns', 'data'],
    },
  },
  {
    name: 'subscriber_add_tag_by_name',
    description: 'Add tag to subscriber by tag name',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        tag_name: { type: 'string', description: 'Tag name (required)' },
      },
      required: ['user_ns', 'tag_name'],
    },
  },
  {
    name: 'subscriber_add_tags_by_name',
    description: 'Add multiple tags by name to subscriber (up to 20)',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        data: {
          type: 'array',
          description: 'Array of tag names',
          items: {
            type: 'object',
            properties: {
              tag_name: { type: 'string' },
            },
          },
        },
      },
      required: ['user_ns', 'data'],
    },
  },
  {
    name: 'subscriber_remove_tag',
    description: 'Remove single tag from subscriber',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        tag_ns: { type: 'string', description: 'Tag namespace (required)' },
      },
      required: ['user_ns', 'tag_ns'],
    },
  },
  {
    name: 'subscriber_remove_tags',
    description: 'Remove multiple tags from subscriber (up to 20)',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        data: {
          type: 'array',
          description: 'Array of tags',
          items: {
            type: 'object',
            properties: {
              tag_ns: { type: 'string' },
            },
          },
        },
      },
      required: ['user_ns', 'data'],
    },
  },
  {
    name: 'subscriber_remove_tag_by_name',
    description: 'Remove tag from subscriber by tag name',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        tag_name: { type: 'string', description: 'Tag name (required)' },
      },
      required: ['user_ns', 'tag_name'],
    },
  },
  {
    name: 'subscriber_remove_tags_by_name',
    description: 'Remove multiple tags from subscriber by name (up to 20)',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        data: {
          type: 'array',
          description: 'Array of tag names',
          items: {
            type: 'object',
            properties: {
              tag_name: { type: 'string' },
            },
          },
        },
      },
      required: ['user_ns', 'data'],
    },
  },
  {
    name: 'subscriber_add_labels_by_name',
    description: 'Add labels by name to subscriber (up to 20)',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        data: {
          type: 'array',
          description: 'Array of label names',
          items: {
            type: 'object',
            properties: {
              label_name: { type: 'string' },
            },
          },
        },
      },
      required: ['user_ns', 'data'],
    },
  },
  {
    name: 'subscriber_remove_labels_by_name',
    description: 'Remove labels from subscriber by name (up to 20)',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        data: {
          type: 'array',
          description: 'Array of label names',
          items: {
            type: 'object',
            properties: {
              label_name: { type: 'string' },
            },
          },
        },
      },
      required: ['user_ns', 'data'],
    },
  },
  {
    name: 'subscriber_set_user_field',
    description: 'Set or update subscriber user field value',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        var_ns: { type: 'string', description: 'Variable namespace (required)' },
        value: { type: 'string', description: 'Field value (required)' },
      },
      required: ['user_ns', 'var_ns', 'value'],
    },
  },
  {
    name: 'subscriber_set_user_fields',
    description: 'Set or update multiple user fields (up to 20)',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
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
      required: ['user_ns', 'data'],
    },
  },
  {
    name: 'subscriber_set_user_field_by_name',
    description: 'Set or update user field by field name',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        field_name: { type: 'string', description: 'Field name (required)' },
        value: { type: 'string', description: 'Field value (required)' },
      },
      required: ['user_ns', 'field_name', 'value'],
    },
  },
  {
    name: 'subscriber_set_user_fields_by_name',
    description: 'Set or update multiple user fields by name (up to 20)',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
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
      required: ['user_ns', 'data'],
    },
  },
  {
    name: 'subscriber_clear_user_field',
    description: 'Clear user field value',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        var_ns: { type: 'string', description: 'Variable namespace (required)' },
      },
      required: ['user_ns', 'var_ns'],
    },
  },
  {
    name: 'subscriber_clear_user_fields',
    description: 'Clear multiple user fields (up to 20)',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        data: {
          type: 'array',
          description: 'Array of field namespaces',
          items: {
            type: 'object',
            properties: {
              var_ns: { type: 'string' },
            },
          },
        },
      },
      required: ['user_ns', 'data'],
    },
  },
  {
    name: 'subscriber_clear_user_field_by_name',
    description: 'Clear user field by field name',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        field_name: { type: 'string', description: 'Field name (required)' },
      },
      required: ['user_ns', 'field_name'],
    },
  },
  {
    name: 'subscriber_clear_user_fields_by_name',
    description: 'Clear multiple user fields by name (up to 20)',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        data: {
          type: 'array',
          description: 'Array of field names',
          items: {
            type: 'object',
            properties: {
              name: { type: 'string' },
            },
          },
        },
      },
      required: ['user_ns', 'data'],
    },
  },
  {
    name: 'subscriber_pause_bot',
    description: 'Pause bot automation for subscriber',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        minutes: { type: 'number', description: 'Pause duration in minutes (required)' },
      },
      required: ['user_ns', 'minutes'],
    },
  },
  {
    name: 'subscriber_resume_bot',
    description: 'Resume bot automation for subscriber',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
      },
      required: ['user_ns'],
    },
  },
  {
    name: 'subscriber_move_chat_to',
    description: 'Update chat status',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        status: { type: 'string', description: 'Status: open, pending, spam, done (required)' },
      },
      required: ['user_ns', 'status'],
    },
  },
  {
    name: 'subscriber_assign_agent',
    description: 'Assign agent to chat',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        agent_id: { type: 'number', description: 'Agent ID (required)' },
      },
      required: ['user_ns', 'agent_id'],
    },
  },
  {
    name: 'subscriber_assign_agent_group',
    description: 'Assign agent group to chat',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        agent_group_id: { type: 'number', description: 'Agent group ID (required)' },
      },
      required: ['user_ns', 'agent_group_id'],
    },
  },
  {
    name: 'subscriber_unassign_agent',
    description: 'Unassign agent from chat',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
      },
      required: ['user_ns'],
    },
  },
  {
    name: 'subscriber_subscribe_to_bot',
    description: 'Subscribe to bot',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
      },
      required: ['user_ns'],
    },
  },
  {
    name: 'subscriber_unsubscribe_from_bot',
    description: 'Unsubscribe from bot',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
      },
      required: ['user_ns'],
    },
  },
  {
    name: 'subscriber_opt_in_sms',
    description: 'Opt-in for SMS',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
      },
      required: ['user_ns'],
    },
  },
  {
    name: 'subscriber_opt_out_sms',
    description: 'Opt-out from SMS',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
      },
      required: ['user_ns'],
    },
  },
  {
    name: 'subscriber_opt_in_email',
    description: 'Opt-in for Email',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
      },
      required: ['user_ns'],
    },
  },
  {
    name: 'subscriber_opt_out_email',
    description: 'Opt-out from Email',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
      },
      required: ['user_ns'],
    },
  },
  {
    name: 'subscriber_log_custom_event',
    description: 'Log custom event for subscriber',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required)' },
        event_name: { type: 'string', description: 'Event name (required)' },
        text_value: { type: 'string', description: 'Text value' },
        price_value: { type: 'number', description: 'Price value' },
        number_value: { type: 'number', description: 'Number value' },
      },
      required: ['user_ns', 'event_name'],
    },
  },
  {
    name: 'subscriber_get_chat_messages',
    description: 'Get subscriber chat messages',
    inputSchema: {
      type: 'object',
      properties: {
        user_ns: { type: 'string', description: 'Subscriber user_ns (required if no user_id)' },
        user_id: { type: 'string', description: 'Subscriber user_id (required if no user_ns)' },
        include_bot: { type: 'number', description: '1 to include bot messages (default: 0)' },
        include_note: { type: 'number', description: '1 to include agent notes (default: 0)' },
        include_system: { type: 'number', description: '1 to include system messages (default: 0)' },
        start_time: { type: 'number', description: 'Unix timestamp (1 month ago to now)' },
        end_time: { type: 'number', description: 'Unix timestamp (1 month ago to now)' },
        limit: { type: 'number', description: 'Number of items 1-100' },
      },
    },
  },
  {
    name: 'subscriber_get_chat_messages_by_mids',
    description: 'Get chat messages by multiple message IDs (up to 100)',
    inputSchema: {
      type: 'object',
      properties: {
        mids: {
          type: 'array',
          description: 'Array of message IDs (required)',
          items: { type: 'string' },
        },
      },
      required: ['mids'],
    },
  },
];
