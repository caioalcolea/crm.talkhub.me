<p align="center">
  <img src="https://chat.talkhub.me/img/logo.png" alt="TalkHub" width="200"/>
</p>

<h1 align="center">TalkHub MCP Server</h1>

<p align="center">
  Servidor MCP (Model Context Protocol) para integração completa com a API TalkHub.<br/>
  Permite que agentes de IA operem toda a plataforma de automação de chatbots via protocolo padronizado.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.2.1-blue" alt="Version"/>
  <img src="https://img.shields.io/badge/tools-199-green" alt="Tools"/>
  <img src="https://img.shields.io/badge/MCP-2025--03--26-purple" alt="MCP Spec"/>
  <img src="https://img.shields.io/badge/transport-Streamable%20HTTP-orange" alt="Transport"/>
  <img src="https://img.shields.io/badge/node-%3E%3D18-brightgreen" alt="Node"/>
</p>

---

## Visão Geral

O TalkHub MCP Server expõe **199 ferramentas** que cobrem toda a API TalkHub, permitindo que qualquer cliente MCP compatível (Claude, Cursor, Kiro, OpenAI Agents, etc.) gerencie chatbots, subscribers, e-commerce, integrações e mais — tudo via linguagem natural.

**Endpoint:** `https://mcptalk.talkhub.me/mcp`

**Transporte:** Streamable HTTP (stateless) — cada requisição é independente, sem necessidade de sessão.

**Autenticação:** Multi-tenant — a API Key é enviada como parâmetro `api_key` em cada chamada de ferramenta.

---

## Configuração em Clientes MCP

### Claude Desktop / Claude Code

```json
{
  "mcpServers": {
    "talkhub": {
      "type": "streamableHttp",
      "url": "https://mcptalk.talkhub.me/mcp"
    }
  }
}
```

### Cursor

```json
{
  "mcpServers": {
    "talkhub": {
      "url": "https://mcptalk.talkhub.me/mcp"
    }
  }
}
```

### Kiro

Adicione em `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "talkhub": {
      "type": "streamableHttp",
      "url": "https://mcptalk.talkhub.me/mcp"
    }
  }
}
```

> Após configurar, o agente terá acesso às 199 ferramentas. Informe sua API Key na primeira interação ou inclua `api_key` nos argumentos de cada chamada.

---

## Categorias de Ferramentas

| Categoria | Tools | Descrição |
|---|---|---|
| Flow Management | 10 | Sub-flows, agentes, widgets, webhooks, transcrição de áudio |
| Flow Tags | 4 | CRUD de tags por namespace ou nome |
| Flow User Fields | 5 | Campos customizados de usuário |
| Flow Bot Fields | 8 | Campos customizados do bot (individual e batch) |
| AI Hub | 2 | Agentes de IA e configuração de providers |
| Segments | 1 | Listagem de segmentos |
| Custom Events | 3 | Eventos customizados, sumários e dados |
| Conversations | 2 | Log de atividade de agentes e dados de conversas |
| WhatsApp Templates | 4 | CRUD e sync de templates WhatsApp |
| Subscribers | 39 | Gestão completa de subscribers, tags, labels, campos, bot control |
| Sending | 15 | Envio de flows, texto, SMS, email, templates WhatsApp, broadcasts |
| Mini-App | 1 | Trigger de eventos em mini-apps instalados |
| E-commerce | 44 | Carrinho, pedidos, produtos, variantes, descontos, locais, horários |
| Templates | 3 | Templates de flow e links de instalação |
| Ticket Lists | 7 | Boards de tickets com campos customizados |
| Team Labels | 4 | Labels de equipe |
| Integrations | 20 | Shopify, WooCommerce, Dropi, Meta, OpenAI, S3, Mini Apps |
| OpenAI Embeddings | 7 | CRUD, importação e geração de embeddings |
| Workspace | 10 | Analytics, membros, canais, configurações de live chat |
| User | 5 | Perfil, senha, notificações |

---

## Exemplos de Uso

Após configurar o cliente MCP, converse naturalmente com o agente:

**Gestão de subscribers:**
> "Liste os últimos 10 subscribers do WhatsApp"
> "Adicione a tag 'vip' ao subscriber f232593u12345"
> "Crie um subscriber com telefone +5511999887766"

**Analytics:**
> "Me mostre o resumo de performance dos últimos 7 dias"
> "Quantos bot users ativos temos?"
> "Qual o tempo médio de resposta dos agentes no último mês?"

**E-commerce:**
> "Liste todos os produtos ativos"
> "Crie um código de desconto PROMO10 de 10% válido até fim do mês"
> "Qual o status do pedido #1234?"

**Envio de mensagens:**
> "Envie 'Olá, tudo bem?' para o subscriber f232593u12345"
> "Dispare o sub-flow de boas-vindas para o telefone +5511999887766"
> "Faça broadcast do flow de promoção para todos com a tag 'clientes-ativos'"

**Integrações:**
> "Qual a configuração atual do Shopify?"
> "Atualize a API key do OpenAI"
> "Configure o S3 com bucket 'talkhub-media' na região us-east-1"

**WhatsApp Templates:**
> "Liste os templates WhatsApp disponíveis"
> "Envie o template 'confirmacao_pedido' para o subscriber f232593u12345"

---

## Referência Rápida da API

### Health Check

```
GET https://mcptalk.talkhub.me/health
```

```json
{
  "status": "ok",
  "service": "talkhub-mcp-server",
  "version": "1.2.1",
  "mode": "multi-tenant",
  "tools": 199
}
```

### Chamada de Ferramenta (MCP Protocol)

```
POST https://mcptalk.talkhub.me/mcp
Content-Type: application/json
Accept: application/json, text/event-stream
```

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "get_team_info",
    "arguments": {
      "api_key": "sua_api_key_aqui"
    }
  }
}
```

### Listar Ferramentas Disponíveis

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

---

## Ferramentas — Referência Completa

</text>
</invoke>

### Flow Management

| Ferramenta | Método | Descrição |
|---|---|---|
| `flow_get_subflows` | GET | Listar sub-flows com paginação e busca |
| `flow_delete_subflow` | DELETE | Deletar sub-flow por namespace |
| `flow_get_bot_users_count` | GET | Contagem de bot users por status |
| `flow_get_agents` | GET | Listar agentes com filtros por role |
| `flow_get_template_installs` | GET | Instalações de templates no flow |
| `flow_set_default_start_flow` | POST | Definir flow inicial padrão do bot |
| `flow_set_web_chat_widget_start_flow` | POST | Definir flow inicial do web chat widget |
| `flow_set_audio_transcription` | POST | Configurar modelo de transcrição de áudio |
| `flow_get_inbound_webhooks` | GET | Listar webhooks de entrada |
| `flow_get_chat_button_widgets` | GET | Listar widgets de botão de chat |

### Flow Tags

| Ferramenta | Método | Descrição |
|---|---|---|
| `flow_get_tags` | GET | Listar tags do flow |
| `flow_create_tag` | POST | Criar nova tag |
| `flow_delete_tag` | DELETE | Deletar tag por namespace |
| `flow_delete_tag_by_name` | DELETE | Deletar tag por nome |

### Flow User Fields

| Ferramenta | Método | Descrição |
|---|---|---|
| `flow_get_user_fields` | GET | Listar campos customizados de usuário |
| `flow_create_user_field` | POST | Criar campo customizado |
| `flow_update_user_field` | POST | Atualizar nome ou display_type |
| `flow_delete_user_field` | DELETE | Deletar por namespace |
| `flow_delete_user_field_by_name` | DELETE | Deletar por nome |

### Flow Bot Fields

| Ferramenta | Método | Descrição |
|---|---|---|
| `flow_get_bot_fields` | GET | Listar campos do bot |
| `flow_create_bot_field` | POST | Criar campo do bot |
| `flow_set_bot_field` | PUT | Atualizar valor por namespace |
| `flow_set_bot_field_by_name` | PUT | Atualizar valor por nome |
| `flow_set_bot_fields` | PUT | Atualizar múltiplos campos (até 20) |
| `flow_set_bot_fields_by_name` | PUT | Atualizar múltiplos por nome (até 20) |
| `flow_delete_bot_field` | DELETE | Deletar por namespace |
| `flow_delete_bot_field_by_name` | DELETE | Deletar por nome |

### AI Hub

| Ferramenta | Método | Descrição |
|---|---|---|
| `flow_get_ai_agents` | GET | Listar agentes de IA |
| `flow_update_ai_agent_provider` | POST | Atualizar provider e modelo do agente IA |

### Segments

| Ferramenta | Método | Descrição |
|---|---|---|
| `flow_get_segments` | GET | Listar segmentos de usuários |

### Custom Events

| Ferramenta | Método | Descrição |
|---|---|---|
| `flow_get_custom_events` | GET | Listar eventos customizados |
| `flow_get_custom_events_summary` | GET | Sumário estatístico de evento |
| `flow_get_custom_events_data` | GET | Dados detalhados de evento |

### Conversations

| Ferramenta | Método | Descrição |
|---|---|---|
| `flow_get_agent_activity_log` | GET | Log de atividade dos agentes |
| `flow_get_conversations_data` | GET | Dados de conversas encerradas |

### WhatsApp Templates

| Ferramenta | Método | Descrição |
|---|---|---|
| `whatsapp_list_templates` | POST | Listar templates WhatsApp |
| `whatsapp_create_template` | POST | Criar template |
| `whatsapp_delete_template` | DELETE | Deletar template |
| `whatsapp_sync_templates` | POST | Sincronizar templates com Meta |

### Subscribers

| Ferramenta | Método | Descrição |
|---|---|---|
| `subscriber_get_list` | GET | Listar subscribers com filtros avançados |
| `subscriber_get_info` | GET | Info do subscriber por user_ns |
| `subscriber_get_info_by_user_id` | GET | Info por user_id do canal |
| `subscriber_create` | POST | Criar subscriber (phone ou email) |
| `subscriber_update` | PUT | Atualizar dados do subscriber |
| `subscriber_delete` | DELETE | Deletar subscriber |
| `subscriber_add_tag` | POST | Adicionar tag |
| `subscriber_add_tags` | POST | Adicionar múltiplas tags (até 20) |
| `subscriber_add_tag_by_name` | POST | Adicionar tag por nome |
| `subscriber_add_tags_by_name` | POST | Adicionar múltiplas tags por nome |
| `subscriber_remove_tag` | DELETE | Remover tag |
| `subscriber_remove_tags` | DELETE | Remover múltiplas tags |
| `subscriber_remove_tag_by_name` | DELETE | Remover tag por nome |
| `subscriber_remove_tags_by_name` | DELETE | Remover múltiplas tags por nome |
| `subscriber_add_labels_by_name` | POST | Adicionar labels por nome |
| `subscriber_remove_labels_by_name` | DELETE | Remover labels por nome |
| `subscriber_set_user_field` | PUT | Definir campo de usuário |
| `subscriber_set_user_fields` | PUT | Definir múltiplos campos (até 20) |
| `subscriber_set_user_field_by_name` | PUT | Definir campo por nome |
| `subscriber_set_user_fields_by_name` | PUT | Definir múltiplos campos por nome |
| `subscriber_clear_user_field` | DELETE | Limpar campo de usuário |
| `subscriber_clear_user_fields` | DELETE | Limpar múltiplos campos |
| `subscriber_clear_user_field_by_name` | DELETE | Limpar campo por nome |
| `subscriber_clear_user_fields_by_name` | DELETE | Limpar múltiplos campos por nome |
| `subscriber_pause_bot` | POST | Pausar bot por X minutos |
| `subscriber_resume_bot` | POST | Retomar bot |
| `subscriber_move_chat_to` | POST | Mover chat (open/pending/spam/done) |
| `subscriber_assign_agent` | POST | Atribuir agente ao chat |
| `subscriber_assign_agent_group` | POST | Atribuir grupo de agentes |
| `subscriber_unassign_agent` | POST | Desatribuir agente |
| `subscriber_subscribe_to_bot` | POST | Inscrever no bot |
| `subscriber_unsubscribe_from_bot` | DELETE | Desinscrever do bot |
| `subscriber_opt_in_sms` | POST | Opt-in SMS |
| `subscriber_opt_out_sms` | DELETE | Opt-out SMS |
| `subscriber_opt_in_email` | POST | Opt-in Email |
| `subscriber_opt_out_email` | DELETE | Opt-out Email |
| `subscriber_log_custom_event` | POST | Registrar evento customizado |
| `subscriber_get_chat_messages` | GET | Mensagens do chat |
| `subscriber_get_chat_messages_by_mids` | POST | Mensagens por IDs (até 100) |

### Sending

| Ferramenta | Método | Descrição |
|---|---|---|
| `subscriber_send_main_flow` | POST | Enviar flow principal |
| `subscriber_send_sub_flow` | POST | Enviar sub-flow por namespace |
| `subscriber_send_sub_flow_by_flow_name` | POST | Enviar sub-flow por nome |
| `subscriber_send_sub_flow_by_user_id` | POST | Enviar sub-flow por user_id do canal |
| `subscriber_broadcast` | POST | Broadcast por lista de user_ns |
| `subscriber_broadcast_by_user_id` | POST | Broadcast por lista de user_id |
| `subscriber_broadcast_by_tag` | POST | Broadcast por tags |
| `subscriber_broadcast_by_segment` | POST | Broadcast por segmentos |
| `subscriber_send_content` | POST | Enviar conteúdo dinâmico (mensagens, ações, quick replies) |
| `subscriber_send_text` | POST | Enviar texto simples |
| `subscriber_send_sms` | POST | Enviar SMS |
| `subscriber_send_email` | POST | Enviar email (HTML) |
| `subscriber_send_node` | POST | Enviar nó específico do flow |
| `subscriber_send_whatsapp_template` | POST | Enviar template WhatsApp por user_ns |
| `subscriber_send_whatsapp_template_by_user_id` | POST | Enviar template WhatsApp por user_id |

### Mini-App

| Ferramenta | Método | Descrição |
|---|---|---|
| `subscriber_app_trigger` | POST | Disparar evento de mini-app |

### E-commerce — Carrinho

| Ferramenta | Método | Descrição |
|---|---|---|
| `subscriber_get_cart` | GET | Ver carrinho do subscriber |
| `subscriber_empty_cart` | DELETE | Esvaziar carrinho |
| `subscriber_add_to_cart` | POST | Adicionar item por variant_id |
| `subscriber_remove_from_cart` | DELETE | Remover item por variant_id |
| `subscriber_cart_paid` | POST | Checkout — marcar carrinho como pago |
| `subscriber_update_order_status` | POST | Atualizar status do pedido |

### E-commerce — Códigos de Desconto

| Ferramenta | Método | Descrição |
|---|---|---|
| `shop_get_discount_codes` | GET | Listar códigos de desconto |
| `shop_get_discount_code_info` | GET | Info por ID |
| `shop_get_discount_code_info_by_code` | GET | Info por código |
| `shop_create_discount_code` | POST | Criar código de desconto |
| `shop_update_discount_code` | PUT | Atualizar código |
| `shop_delete_discount_code` | DELETE | Deletar por ID |
| `shop_delete_discount_code_by_code` | DELETE | Deletar por código |

### E-commerce — Pedidos

| Ferramenta | Método | Descrição |
|---|---|---|
| `shop_get_orders` | GET | Listar pedidos |
| `shop_get_order_info` | GET | Info do pedido por ID |
| `shop_create_order` | POST | Criar pedido |
| `shop_update_order` | PUT | Atualizar pedido |

### E-commerce — Produtos

| Ferramenta | Método | Descrição |
|---|---|---|
| `shop_get_products` | GET | Listar produtos |
| `shop_get_product_info` | GET | Info do produto por ID |
| `shop_create_product` | POST | Criar produto |
| `shop_update_product` | PUT | Atualizar produto |
| `shop_delete_product` | DELETE | Deletar produto |

### E-commerce — Tags de Produto

| Ferramenta | Método | Descrição |
|---|---|---|
| `shop_get_product_tags` | GET | Listar tags |
| `shop_get_product_tag_info` | GET | Info da tag |
| `shop_create_product_tag` | POST | Criar tag |
| `shop_update_product_tag` | PUT | Atualizar tag |
| `shop_delete_product_tag` | DELETE | Deletar tag |

### E-commerce — Tipos de Produto

| Ferramenta | Método | Descrição |
|---|---|---|
| `shop_get_product_types` | GET | Listar tipos |
| `shop_get_product_type_info` | GET | Info do tipo |
| `shop_create_product_type` | POST | Criar tipo |
| `shop_update_product_type` | PUT | Atualizar tipo |
| `shop_delete_product_type` | DELETE | Deletar tipo |

### E-commerce — Fornecedores

| Ferramenta | Método | Descrição |
|---|---|---|
| `shop_get_product_vendors` | GET | Listar fornecedores |
| `shop_get_product_vendor_info` | GET | Info do fornecedor |
| `shop_create_product_vendor` | POST | Criar fornecedor |
| `shop_update_product_vendor` | PUT | Atualizar fornecedor |
| `shop_delete_product_vendor` | DELETE | Deletar fornecedor |

### E-commerce — Horário Comercial

| Ferramenta | Método | Descrição |
|---|---|---|
| `shop_get_business_hours` | GET | Ver horário comercial |
| `shop_update_business_hours` | PUT | Atualizar horário comercial |

### E-commerce — Locais

| Ferramenta | Método | Descrição |
|---|---|---|
| `shop_get_locations` | GET | Listar locais |
| `shop_get_location_info` | GET | Info do local |
| `shop_create_location` | POST | Criar local |
| `shop_update_location` | PUT | Atualizar local |
| `shop_delete_location` | DELETE | Deletar local |

### E-commerce — Variantes de Produto

| Ferramenta | Método | Descrição |
|---|---|---|
| `shop_get_product_variants` | GET | Listar variantes |
| `shop_get_product_variant_info` | GET | Info da variante |
| `shop_create_product_variant` | POST | Criar variante |
| `shop_update_product_variant` | PUT | Atualizar variante |
| `shop_delete_product_variant` | DELETE | Deletar variante |

### Templates

| Ferramenta | Método | Descrição |
|---|---|---|
| `get_templates` | GET | Listar templates de flow |
| `get_template_installs` | GET | Instalações de um template |
| `generate_template_link` | POST | Gerar link de instalação único |

### Ticket Lists

| Ferramenta | Método | Descrição |
|---|---|---|
| `get_ticket_lists` | GET | Listar boards de tickets |
| `get_ticket_list_fields` | GET | Campos de um board |
| `get_ticket_list_items` | GET | Tickets de um board |
| `get_ticket_list_log_data` | GET | Log de alterações |
| `create_ticket` | POST | Criar ticket |
| `update_ticket` | PUT | Atualizar ticket |
| `delete_ticket` | DELETE | Deletar ticket |

### Team Labels

| Ferramenta | Método | Descrição |
|---|---|---|
| `get_team_labels` | GET | Listar labels da equipe |
| `create_team_label` | POST | Criar label |
| `delete_team_label` | DELETE | Deletar label por ID |
| `delete_team_label_by_name` | DELETE | Deletar label por nome |

### Integrations

| Ferramenta | Método | Descrição |
|---|---|---|
| `get_shopify_integration` | GET | Config Shopify |
| `update_shopify_integration` | POST | Atualizar Shopify |
| `delete_shopify_integration` | DELETE | Remover Shopify |
| `get_woocommerce_integration` | GET | Config WooCommerce |
| `update_woocommerce_integration` | POST | Atualizar WooCommerce |
| `delete_woocommerce_integration` | DELETE | Remover WooCommerce |
| `get_dropi_integration` | GET | Config Dropi |
| `update_dropi_integration` | POST | Atualizar Dropi |
| `delete_dropi_integration` | DELETE | Remover Dropi |
| `get_meta_conversions_api_integration` | GET | Config Meta Conversions API |
| `update_meta_conversions_api_integration` | POST | Atualizar Meta Conversions |
| `delete_meta_conversions_api_integration` | DELETE | Remover Meta Conversions |
| `get_openai_integration` | GET | Config OpenAI |
| `update_openai_integration` | POST | Atualizar OpenAI |
| `delete_openai_integration` | DELETE | Remover OpenAI |
| `get_s3storage_integration` | GET | Config S3 Storage |
| `update_s3storage_integration` | POST | Atualizar S3 |
| `delete_s3storage_integration` | DELETE | Remover S3 |
| `get_installed_mini_apps` | GET | Listar mini apps instalados |
| `update_mini_app_api_key` | POST | Atualizar API key de mini app |

### OpenAI Embeddings

| Ferramenta | Método | Descrição |
|---|---|---|
| `get_openai_embeddings` | GET | Listar embeddings |
| `get_openai_embedding_info` | GET | Info do embedding |
| `create_openai_embedding` | POST | Criar embedding |
| `update_openai_embedding` | PUT | Atualizar embedding |
| `delete_openai_embedding` | DELETE | Deletar embedding |
| `import_openai_embeddings` | POST | Importar embeddings (até 100) |
| `generate_openai_embeddings` | POST | Regenerar todos os embeddings |

### Workspace

| Ferramenta | Método | Descrição |
|---|---|---|
| `get_flow_summary` | GET | Resumo analítico do flow |
| `get_flow_agent_summary` | GET | Performance dos agentes |
| `get_team_bot_users` | GET | Bot users do workspace |
| `get_team_flows` | GET | Bots/flows do workspace |
| `get_team_info` | GET | Info do workspace |
| `get_workspace_channels` | GET | Canais configurados |
| `update_workspace_channels` | POST | Mostrar/ocultar canais |
| `get_workspace_live_chat_sidebar` | GET | Config sidebar do live chat |
| `update_workspace_live_chat_sidebar` | POST | Atualizar sidebar |
| `get_team_members` | GET | Membros do workspace |

### User

| Ferramenta | Método | Descrição |
|---|---|---|
| `get_current_user` | GET | Info do usuário autenticado |
| `change_user_password` | PUT | Alterar senha |
| `get_recent_notifications` | GET | Notificações recentes |
| `mark_notification_read` | POST | Marcar notificação como lida |
| `mark_announcement_read` | POST | Marcar anúncios como lidos |

---

## Arquitetura

```
┌─────────────────┐     HTTPS/JSON-RPC      ┌──────────────────────┐     REST API     ┌─────────────┐
│   MCP Client    │ ◄──────────────────────► │  TalkHub MCP Server  │ ◄──────────────► │ TalkHub API │
│ (Claude, Kiro,  │   Streamable HTTP        │  mcptalk.talkhub.me  │   Bearer Token   │ chat.talkhub│
│  Cursor, etc.)  │   Port 443 (Traefik)     │  199 tools           │                  │   .me/api   │
└─────────────────┘                          └──────────────────────┘                  └─────────────┘
```

- **Transporte:** Streamable HTTP (MCP spec 2025-03-26) — stateless, sem sessão
- **Infraestrutura:** Docker Swarm + Traefik v3 + Let's Encrypt
- **Autenticação:** API Key por requisição (multi-tenant)
- **Observabilidade:** JSON structured logging por tool call (tool, duration, isError, timestamp)
- **Timeout:** 30s por chamada à API TalkHub

---

## Obter API Key

1. Acesse [chat.talkhub.me](https://chat.talkhub.me)
2. Vá em **Configurações** → **API**
3. Copie sua API Key
4. Use como parâmetro `api_key` nas chamadas ou informe ao agente na conversa

---

<p align="center">
  <sub>TalkHub MCP Server v1.2.1 — 199 tools — MCP 2025-03-26</sub>
</p>
