/**
 * Tasks List Page - API Version
 *
 * Migrated from Prisma to Django REST API
 * Django endpoint: GET /api/tasks/
 *
 * Task API fields:
 * - title, status, priority, due_date, description, account
 * - contacts (M2M), teams (M2M), assigned_to (M2M)
 * - created_by, created_at, updated_at
 *
 * PERFORMANCE: Only fetches tasks + kanban + pipelines (3 calls).
 * Form options (users, accounts, contacts, etc.) are loaded lazily
 * on the client side when the drawer opens.
 */

import { error, fail } from '@sveltejs/kit';
import { apiRequest, buildQueryParams } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals, cookies, url, depends }) {
  depends('app:tasks');

  const user = locals.user;
  const org = locals.org;

  if (!org) {
    throw error(401, 'Contexto de organização é obrigatório');
  }

  // Parse view mode from URL
  const viewMode = url.searchParams.get('view') || 'list';
  const pipelineId = url.searchParams.get('pipeline_id') || '';

  // Parse pagination params from URL
  const page = parseInt(url.searchParams.get('page') || '1');
  const limit = parseInt(url.searchParams.get('limit') || '10');

  // Parse filter params from URL
  const quickFilter = url.searchParams.get('quick_filter') || '';
  const filters = {
    search: url.searchParams.get('search') || '',
    status: url.searchParams.get('status') || '',
    priority: url.searchParams.get('priority') || '',
    assigned_to: url.searchParams.getAll('assigned_to'),
    tags: url.searchParams.getAll('tags'),
    due_date_gte: url.searchParams.get('due_date_gte') || '',
    due_date_lte: url.searchParams.get('due_date_lte') || '',
    quick_filter: quickFilter
  };

  try {
    // Build query parameters for tasks
    const queryParams = buildQueryParams({
      sort: 'created_at',
      order: 'desc'
    });
    queryParams.append('limit', limit.toString());
    queryParams.append('offset', ((page - 1) * limit).toString());

    // Add filter params
    if (filters.search) queryParams.append('search', filters.search);
    if (filters.status) queryParams.append('status', filters.status);
    if (filters.priority) queryParams.append('priority', filters.priority);
    filters.assigned_to.forEach((id) => queryParams.append('assigned_to', id));
    filters.tags.forEach((id) => queryParams.append('tags', id));
    if (filters.due_date_gte) queryParams.append('due_date__gte', filters.due_date_gte);
    if (filters.due_date_lte) queryParams.append('due_date__lte', filters.due_date_lte);
    if (filters.quick_filter) queryParams.append('quick_filter', filters.quick_filter);

    // Build kanban query params (same filters as list, except status which is column-based)
    const kanbanQueryParams = new URLSearchParams();
    if (filters.search) kanbanQueryParams.append('search', filters.search);
    if (filters.priority) kanbanQueryParams.append('priority', filters.priority);
    filters.assigned_to.forEach((id) => kanbanQueryParams.append('assigned_to', id));
    filters.tags.forEach((id) => kanbanQueryParams.append('tags', id));
    if (filters.due_date_gte) kanbanQueryParams.append('due_date__gte', filters.due_date_gte);
    if (filters.due_date_lte) kanbanQueryParams.append('due_date__lte', filters.due_date_lte);
    if (filters.quick_filter) kanbanQueryParams.append('quick_filter', filters.quick_filter);
    if (pipelineId) kanbanQueryParams.append('pipeline_id', pipelineId);

    // PERFORMANCE: Only fetch tasks + kanban + pipelines (3 calls max)
    // Form options (users, accounts, contacts, teams, etc.) are loaded
    // lazily on the client side when the drawer opens.
    const kanbanQueryString = kanbanQueryParams.toString();
    const [tasksResponse, kanbanResponse, pipelinesResponse] = await Promise.all([
      apiRequest(`/tasks/?${queryParams.toString()}`, {}, { cookies, org }),
      viewMode === 'kanban'
        ? apiRequest(
            `/tasks/kanban/${kanbanQueryString ? '?' + kanbanQueryString : ''}`,
            {},
            { cookies, org }
          )
        : Promise.resolve(null),
      apiRequest('/tasks/pipelines/', {}, { cookies, org }).catch(() => [])
    ]);

    // Handle Django response structure
    // Django TaskListView returns { tasks: [...], tasks_count: ..., ... }
    let tasks = [];
    if (tasksResponse.tasks) {
      tasks = tasksResponse.tasks;
    } else if (Array.isArray(tasksResponse)) {
      tasks = tasksResponse;
    } else if (tasksResponse.results) {
      tasks = tasksResponse.results;
    }

    // Transform Django tasks to frontend structure
    // Uses inline *_name fields from TaskSerializer (no extra API calls needed)
    const transformedTasks = tasks.map((task) => ({
      id: task.id,
      subject: task.title,
      description: task.description,
      status: task.status,
      priority: task.priority,
      dueDate: task.due_date,
      dueTime: task.due_time || '',
      effort: task.effort || null,
      impact: task.impact || null,
      priorityScore: task.priority_score || 0,
      isBlocked: task.is_blocked || false,
      subtaskProgress: task.subtask_progress || '',
      createdAt: task.created_at,
      updatedAt: task.updated_at,

      // All assigned users (M2M)
      assignedTo: (task.assigned_to || []).map((u) => ({
        id: u.id,
        name: u.user_details?.email || 'Sem atribuição'
      })),

      // Contacts (M2M)
      contacts: (task.contacts || []).map((c) => ({
        id: c.id,
        name: c.first_name ? `${c.first_name} ${c.last_name || ''}`.trim() : c.email || 'Unknown'
      })),

      // Teams (M2M)
      teams: (task.teams || []).map((t) => ({
        id: t.id,
        name: t.name
      })),

      // Tags (M2M)
      tags: (task.tags || []).map((t) => ({
        id: t.id,
        name: t.name
      })),

      // Related entities — uses inline *_name fields from serializer
      account: task.account
        ? { id: task.account, name: task.account_name || 'Conta' }
        : null,
      opportunity: task.opportunity
        ? { id: task.opportunity, name: task.opportunity_name || 'Oportunidade' }
        : null,
      case_: task.case
        ? { id: task.case, name: task.case_name || 'Chamado' }
        : null,
      lead: task.lead
        ? { id: task.lead, name: task.lead_name || 'Lead' }
        : null,

      // Created by
      createdBy: task.created_by
        ? {
            id: task.created_by.id,
            name: task.created_by.email
          }
        : null,

      // Stage (for kanban pipeline)
      stage: task.stage || null
    }));

    // Get total count from response
    const total = tasksResponse.tasks_count || tasksResponse.count || transformedTasks.length;

    return {
      tasks: transformedTasks,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit) || 1
      },
      filters,
      viewMode,
      pipelineId: pipelineId || kanbanResponse?.pipeline?.id || '',
      kanbanData: kanbanResponse,
      pipelines: Array.isArray(pipelinesResponse)
        ? pipelinesResponse
        : pipelinesResponse?.pipelines || pipelinesResponse?.results || [],
      // Form options loaded lazily on client side — empty here
      formOptions: {
        users: [],
        accounts: [],
        contacts: [],
        teams: [],
        opportunities: [],
        cases: [],
        leads: [],
        tags: []
      }
    };
  } catch (err) {
    console.error('Error loading tasks from API:', err);
    throw error(500, `Falha ao carregar tarefas: ${err.message}`);
  }
}

/** @type {import('./$types').Actions} */
export const actions = {
  create: async ({ request, locals, cookies }) => {
    const org = locals.org;

    try {
      const form = await request.formData();
      const subject = form.get('subject')?.toString().trim();
      const description = form.get('description')?.toString().trim();
      const status = form.get('status')?.toString() || 'New';
      const priority = form.get('priority')?.toString() || 'Medium';
      const dueDate = form.get('dueDate')?.toString() || null;
      const dueTime = form.get('dueTime')?.toString() || null;
      const effort = form.get('effort')?.toString() || null;
      const impact = form.get('impact')?.toString() || null;
      const accountId = form.get('accountId')?.toString() || null;
      const opportunityId = form.get('opportunityId')?.toString() || null;
      const caseId = form.get('caseId')?.toString() || null;
      const leadId = form.get('leadId')?.toString() || null;

      // Parse array fields (sent as JSON strings)
      const assignedToJson = form.get('assignedTo')?.toString() || '[]';
      const contactsJson = form.get('contacts')?.toString() || '[]';
      const teamsJson = form.get('teams')?.toString() || '[]';
      const tagsJson = form.get('tags')?.toString() || '[]';

      const assignedTo = JSON.parse(assignedToJson);
      const contacts = JSON.parse(contactsJson);
      const teams = JSON.parse(teamsJson);
      const tags = JSON.parse(tagsJson);

      if (!subject) {
        return { success: false, error: 'O assunto é obrigatório' };
      }

      // Transform to Django field names
      const djangoData = {
        title: subject,
        description: description || null,
        status: status,
        priority: priority,
        due_date: dueDate,
        due_time: dueTime || null,
        effort: effort ? parseInt(effort) : null,
        impact: impact ? parseInt(impact) : null,
        assigned_to: assignedTo,
        contacts: contacts,
        teams: teams,
        tags: tags,
        account: accountId || null,
        opportunity: opportunityId || null,
        case: caseId || null,
        lead: leadId || null
      };

      // Pipeline stage
      const stageId = form.get('stageId')?.toString() || null;
      if (stageId) djangoData.stage = stageId;

      await apiRequest(
        '/tasks/',
        {
          method: 'POST',
          body: djangoData
        },
        { cookies, org }
      );

      return { success: true };
    } catch (err) {
      console.error('Error creating task:', err);
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  update: async ({ request, locals, cookies }) => {
    const org = locals.org;

    try {
      const form = await request.formData();
      const taskId = form.get('taskId')?.toString();
      const subject = form.get('subject')?.toString().trim();
      const description = form.get('description')?.toString().trim();
      const status = form.get('status')?.toString() || 'New';
      const priority = form.get('priority')?.toString() || 'Medium';
      const dueDate = form.get('dueDate')?.toString() || null;
      const dueTime = form.get('dueTime')?.toString() || null;
      const effort = form.get('effort')?.toString() || null;
      const impact = form.get('impact')?.toString() || null;
      const accountId = form.get('accountId')?.toString() || null;
      const opportunityId = form.get('opportunityId')?.toString() || null;
      const caseId = form.get('caseId')?.toString() || null;
      const leadId = form.get('leadId')?.toString() || null;

      // Parse array fields (sent as JSON strings)
      const assignedToJson = form.get('assignedTo')?.toString() || '[]';
      const contactsJson = form.get('contacts')?.toString() || '[]';
      const teamsJson = form.get('teams')?.toString() || '[]';
      const tagsJson = form.get('tags')?.toString() || '[]';

      const assignedTo = JSON.parse(assignedToJson);
      const contacts = JSON.parse(contactsJson);
      const teams = JSON.parse(teamsJson);
      const tags = JSON.parse(tagsJson);

      if (!taskId || !subject) {
        return { success: false, error: 'ID e assunto da tarefa são obrigatórios' };
      }

      // Transform to Django field names
      const djangoData = {
        title: subject,
        description: description || null,
        status: status,
        priority: priority,
        due_date: dueDate,
        due_time: dueTime || null,
        effort: effort ? parseInt(effort) : null,
        impact: impact ? parseInt(impact) : null,
        assigned_to: assignedTo,
        contacts: contacts,
        teams: teams,
        tags: tags,
        account: accountId || null,
        opportunity: opportunityId || null,
        case: caseId || null,
        lead: leadId || null
      };

      // Pipeline stage (null clears the stage)
      const stageId = form.get('stageId')?.toString() || null;
      djangoData.stage = stageId;

      await apiRequest(
        `/tasks/${taskId}/`,
        {
          method: 'PATCH',
          body: djangoData
        },
        { cookies, org }
      );

      return { success: true };
    } catch (err) {
      console.error('Error updating task:', err);
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  complete: async ({ request, locals, cookies }) => {
    const org = locals.org;

    try {
      const form = await request.formData();
      const taskId = form.get('taskId')?.toString();

      if (!taskId) {
        return { success: false, error: 'ID da tarefa é obrigatório' };
      }

      // Update with PATCH, changing only status to Completed
      await apiRequest(
        `/tasks/${taskId}/`,
        {
          method: 'PATCH',
          body: { status: 'Completed' }
        },
        { cookies, org }
      );

      return { success: true };
    } catch (err) {
      console.error('Error completing task:', err);
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  reopen: async ({ request, locals, cookies }) => {
    const org = locals.org;

    try {
      const form = await request.formData();
      const taskId = form.get('taskId')?.toString();

      if (!taskId) {
        return { success: false, error: 'ID da tarefa é obrigatório' };
      }

      // Update with PATCH, changing only status to New
      await apiRequest(
        `/tasks/${taskId}/`,
        {
          method: 'PATCH',
          body: { status: 'New' }
        },
        { cookies, org }
      );

      return { success: true };
    } catch (err) {
      console.error('Error reopening task:', err);
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  delete: async ({ request, locals, cookies }) => {
    const org = locals.org;

    try {
      const form = await request.formData();
      const taskId = form.get('taskId')?.toString();

      if (!taskId) {
        return { success: false, error: 'ID da tarefa é obrigatório' };
      }

      await apiRequest(`/tasks/${taskId}/`, { method: 'DELETE' }, { cookies, org });

      return { success: true };
    } catch (err) {
      console.error('Error deleting task:', err);
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  moveTask: async ({ request, locals, cookies }) => {
    const org = locals.org;

    try {
      const form = await request.formData();
      const taskId = form.get('taskId')?.toString();
      const status = form.get('status')?.toString();
      const stageId = form.get('stageId')?.toString() || null;
      const aboveTaskId = form.get('aboveTaskId')?.toString() || null;
      const belowTaskId = form.get('belowTaskId')?.toString() || null;

      if (!taskId) {
        return { success: false, error: 'ID da tarefa é obrigatório' };
      }

      if (!status && !stageId) {
        return { success: false, error: 'Status ou estágio é obrigatório' };
      }

      /** @type {Record<string, string>} */
      const moveData = {};
      if (status) moveData.status = status;
      if (stageId) moveData.stage_id = stageId;
      if (aboveTaskId) moveData.above_task_id = aboveTaskId;
      if (belowTaskId) moveData.below_task_id = belowTaskId;

      await apiRequest(
        `/tasks/${taskId}/move/`,
        {
          method: 'PATCH',
          body: moveData
        },
        { cookies, org }
      );

      return { success: true };
    } catch (err) {
      console.error('Error moving task:', err);
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  }
};
