<script>
  import { KanbanBoard } from '$lib/components/ui/kanban';
  import OpportunityCard from './OpportunityCard.svelte';

  /**
   * @typedef {Object} Column
   * @property {string} id
   * @property {string} name
   * @property {number} order
   * @property {string} color
   * @property {string} stage_type
   * @property {boolean} is_status_column
   * @property {number|null} wip_limit
   * @property {number} opportunity_count
   * @property {Array<any>} opportunities
   */

  /**
   * @typedef {Object} KanbanData
   * @property {string} mode
   * @property {Object|null} pipeline
   * @property {Column[]} columns
   * @property {number} total_opportunities
   */

  /**
   * @type {{
   *   data: KanbanData | null,
   *   loading?: boolean,
   *   onStatusChange: (oppId: string, newStatus: string, columnId: string) => Promise<void>,
   *   onCardClick: (opp: any) => void
   * }}
   */
  let { data = null, loading = false, onStatusChange, onCardClick } = $props();

  // Transform data to use generic field names
  const transformedData = $derived(() => {
    if (!data) return null;

    return {
      mode: data.mode,
      pipeline: data.pipeline,
      columns: data.columns.map((col) => ({
        ...col,
        items: col.opportunities || [],
        item_count: col.opportunity_count || col.opportunities?.length || 0
      })),
      total_items: data.total_opportunities
    };
  });
</script>

<KanbanBoard
  data={transformedData()}
  {loading}
  itemName="oportunidade"
  itemNamePlural="oportunidades"
  onItemMove={onStatusChange}
  {onCardClick}
  CardComponent={OpportunityCard}
  emptyMessage="Nenhum dado do quadro disponível"
/>
