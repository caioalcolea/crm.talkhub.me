#!/usr/bin/env node

import express from 'express';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import axios from 'axios';
import dotenv from 'dotenv';
import { toolDefinitions } from './tools-definitions.js';
import { subscriberTools } from './tools-subscribers.js';
import { remainingTools } from './tools-remaining.js';
import { handleToolCall } from './tool-handlers.js';
import { z } from 'zod';

dotenv.config();

const DEFAULT_API_KEY = process.env.TALKHUB_API_KEY;
const API_URL = process.env.TALKHUB_API_URL || 'https://chat.talkhub.me/api';
const PORT = process.env.PORT || 3000;
const MULTI_TENANT_MODE = !DEFAULT_API_KEY;
const VERSION = '1.2.1';

// Combinar todas as tool definitions
const allToolDefinitions = [...toolDefinitions, ...subscriberTools, ...remainingTools];

// Helper: criar axios client com API Key específica
export function createApiClient(apiKey) {
  return axios.create({
    baseURL: API_URL,
    timeout: 30000,
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
  });
}

export const api = DEFAULT_API_KEY ? createApiClient(DEFAULT_API_KEY) : null;

// Helper: fazer requisições à API TalkHub
export async function makeRequest(method, endpoint, data = null, params = null, apiKey = null) {
  try {
    const effectiveApiKey = apiKey || DEFAULT_API_KEY;

    if (!effectiveApiKey) {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            error: 'API Key is required. Provide "api_key" parameter in your request.',
            errorCode: 'MISSING_API_KEY',
          }, null, 2),
        }],
        isError: true,
      };
    }

    const client = createApiClient(effectiveApiKey);
    const config = { method, url: endpoint };
    if (data) config.data = data;
    if (params) config.params = params;

    const response = await client.request(config);
    return {
      content: [{ type: 'text', text: JSON.stringify(response.data, null, 2) }],
    };
  } catch (error) {
    const errorMessage = error.response?.data?.message || error.message;
    const statusCode = error.response?.status || 'Unknown';
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          error: errorMessage,
          status: statusCode,
          endpoint,
          errorCode: statusCode === 401 ? 'UNAUTHORIZED' : statusCode === 404 ? 'NOT_FOUND' : 'API_ERROR',
        }, null, 2),
      }],
      isError: true,
    };
  }
}

// Converter inputSchema JSON para Zod shape (para McpServer.tool())
function jsonSchemaToZod(schema) {
  if (!schema || !schema.properties) return {};
  const shape = {};
  for (const [key, prop] of Object.entries(schema.properties)) {
    const isRequired = schema.required?.includes(key);
    let zodType;
    switch (prop.type) {
      case 'number':
      case 'integer':
        zodType = z.number().describe(prop.description || key);
        break;
      case 'boolean':
        zodType = z.boolean().describe(prop.description || key);
        break;
      case 'array':
        zodType = z.array(z.any()).describe(prop.description || key);
        break;
      case 'object':
        zodType = z.record(z.any()).describe(prop.description || key);
        break;
      default:
        zodType = z.string().describe(prop.description || key);
        break;
    }
    shape[key] = isRequired ? zodType : zodType.optional();
  }
  // Sempre adicionar api_key
  if (!shape.api_key) {
    shape.api_key = z.string().describe('TalkHub API Key for authentication (required in multi-tenant mode)').optional();
  }
  return shape;
}

// Criar McpServer e registrar todas as tools
function createMcpServer() {
  const server = new McpServer(
    { name: 'talkhub-mcp-server', version: VERSION },
    { capabilities: { tools: {} } }
  );

  for (const tool of allToolDefinitions) {
    const zodShape = jsonSchemaToZod(tool.inputSchema);
    server.tool(
      tool.name,
      tool.description || tool.name,
      zodShape,
      async (args) => {
        const startTime = Date.now();
        try {
          const result = await handleToolCall(tool.name, args);
          const duration = Date.now() - startTime;
          console.log(JSON.stringify({
            tool: tool.name,
            duration,
            isError: result.isError || false,
            timestamp: new Date().toISOString(),
          }));
          return result;
        } catch (error) {
          const duration = Date.now() - startTime;
          console.error(JSON.stringify({
            tool: tool.name,
            duration,
            isError: true,
            error: error.message,
            timestamp: new Date().toISOString(),
          }));
          return {
            content: [{ type: 'text', text: `Error: ${error.message}` }],
            isError: true,
          };
        }
      }
    );
  }

  return server;
}

async function main() {
  const app = express();
  app.use(express.json());

  // POST /mcp — cria server + transport por request (stateless)
  app.post('/mcp', async (req, res) => {
    try {
      const server = createMcpServer();
      const transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: undefined,
      });
      res.on('close', () => {
        transport.close();
        server.close();
      });
      await server.connect(transport);
      await transport.handleRequest(req, res, req.body);
    } catch (error) {
      console.error('MCP error:', error.message);
      if (!res.headersSent) {
        res.status(500).json({
          jsonrpc: '2.0',
          error: { code: -32603, message: 'Internal server error' },
          id: null,
        });
      }
    }
  });

  // GET /mcp — SSE não suportado neste modo
  app.get('/mcp', (_req, res) => {
    res.status(405).json({
      jsonrpc: '2.0',
      error: { code: -32601, message: 'Method not allowed. Use POST.' },
      id: null,
    });
  });

  // DELETE /mcp — sessões não suportadas neste modo
  app.delete('/mcp', (_req, res) => {
    res.status(405).json({
      jsonrpc: '2.0',
      error: { code: -32601, message: 'Method not allowed.' },
      id: null,
    });
  });

  // Health check
  app.get('/health', (_req, res) => {
    res.json({
      status: 'ok',
      service: 'talkhub-mcp-server',
      version: VERSION,
      mode: MULTI_TENANT_MODE ? 'multi-tenant' : 'single-tenant',
      tools: allToolDefinitions.length,
      uptime: Math.floor(process.uptime()),
    });
  });

  // Root info
  app.get('/', (_req, res) => {
    res.json({
      name: 'TalkHub MCP Server',
      version: VERSION,
      description: 'MCP Server for TalkHub API - Complete chatbot automation platform',
      mcp_endpoint: '/mcp',
      health: '/health',
      tools: allToolDefinitions.length,
      mode: MULTI_TENANT_MODE ? 'multi-tenant' : 'single-tenant',
    });
  });

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`TalkHub MCP Server v${VERSION}`);
    console.log(`Port: ${PORT}`);
    console.log(`MCP: http://0.0.0.0:${PORT}/mcp`);
    console.log(`Health: http://0.0.0.0:${PORT}/health`);
    console.log(`Tools: ${allToolDefinitions.length}`);
    console.log(`Mode: ${MULTI_TENANT_MODE ? 'multi-tenant' : 'single-tenant'}`);
  });
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
