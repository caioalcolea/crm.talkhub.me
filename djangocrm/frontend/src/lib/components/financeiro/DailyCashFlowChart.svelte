<script>
  import { formatCurrency } from '$lib/utils/formatting.js';

  let { data = [], cur = 'BRL' } = $props();

  const today = new Date().getDate();

  // Chart dimensions
  const W = 800;
  const H = 250;
  const PAD = { top: 20, right: 16, bottom: 28, left: 16 };
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top - PAD.bottom;

  // Derived values
  const numDays = $derived(data.length || 30);

  const maxVal = $derived(
    Math.max(
      ...data.map((d) => Math.max(Math.abs(d.receita || 0), Math.abs(d.despesa || 0), Math.abs(d.saldo_acumulado || 0))),
      1
    )
  );

  // Scale helpers
  function xPos(day) {
    return PAD.left + ((day - 1) / (numDays - 1 || 1)) * chartW;
  }

  function yPos(val) {
    return PAD.top + chartH - (val / maxVal) * chartH;
  }

  // Path generators
  function areaPath(field, close = true) {
    if (!data.length) return '';
    const points = data.map((d) => `${xPos(d.dia)},${yPos(d[field] || 0)}`);
    let path = `M${points[0]}`;
    for (let i = 1; i < points.length; i++) {
      // Smooth curve using quadratic bezier
      const prev = data[i - 1];
      const curr = data[i];
      const cpx = (xPos(prev.dia) + xPos(curr.dia)) / 2;
      path += ` Q${cpx},${yPos(prev[field] || 0)} ${xPos(curr.dia)},${yPos(curr[field] || 0)}`;
    }
    if (close) {
      path += ` L${xPos(data[data.length - 1].dia)},${yPos(0)} L${xPos(data[0].dia)},${yPos(0)} Z`;
    }
    return path;
  }

  function linePath(field) {
    return areaPath(field, false);
  }

  // Accumulated balance can go negative — need special y mapping
  const minAccum = $derived(Math.min(...data.map((d) => d.saldo_acumulado || 0), 0));
  const maxAccum = $derived(Math.max(...data.map((d) => d.saldo_acumulado || 0), 0));
  const accumRange = $derived(Math.max(maxAccum - minAccum, 1));

  function yAccum(val) {
    return PAD.top + chartH - ((val - minAccum) / accumRange) * chartH;
  }

  function accumLinePath() {
    if (!data.length) return '';
    let path = `M${xPos(data[0].dia)},${yAccum(data[0].saldo_acumulado || 0)}`;
    for (let i = 1; i < data.length; i++) {
      const prev = data[i - 1];
      const curr = data[i];
      const cpx = (xPos(prev.dia) + xPos(curr.dia)) / 2;
      path += ` Q${cpx},${yAccum(prev.saldo_acumulado || 0)} ${xPos(curr.dia)},${yAccum(curr.saldo_acumulado || 0)}`;
    }
    return path;
  }

  // Negative zone area (where saldo_acumulado < 0)
  function negativeAreaPath() {
    if (!data.length) return '';
    const zeroY = yAccum(0);
    let segments = [];
    let inNeg = false;
    let segPoints = [];

    for (let i = 0; i < data.length; i++) {
      const val = data[i].saldo_acumulado || 0;
      if (val < 0) {
        if (!inNeg) {
          inNeg = true;
          // Add zero crossing point
          if (i > 0) {
            const prevVal = data[i - 1].saldo_acumulado || 0;
            const t = prevVal / (prevVal - val);
            const crossX = xPos(data[i - 1].dia) + t * (xPos(data[i].dia) - xPos(data[i - 1].dia));
            segPoints.push({ x: crossX, y: zeroY });
          }
        }
        segPoints.push({ x: xPos(data[i].dia), y: yAccum(val) });
      } else if (inNeg) {
        // Exiting negative zone
        const prevVal = data[i - 1].saldo_acumulado || 0;
        const t = prevVal / (prevVal - val);
        const crossX = xPos(data[i - 1].dia) + t * (xPos(data[i].dia) - xPos(data[i - 1].dia));
        segPoints.push({ x: crossX, y: zeroY });
        segments.push([...segPoints]);
        segPoints = [];
        inNeg = false;
      }
    }
    if (inNeg && segPoints.length) segments.push(segPoints);

    return segments
      .map((seg) => {
        let d = `M${seg[0].x},${seg[0].y}`;
        for (let i = 1; i < seg.length; i++) {
          d += ` L${seg[i].x},${seg[i].y}`;
        }
        d += ` L${seg[seg.length - 1].x},${zeroY}`;
        if (seg[0].y !== zeroY) d += ` L${seg[0].x},${zeroY}`;
        d += ' Z';
        return d;
      })
      .join(' ');
  }

  // Tooltip state
  let hoveredDay = $state(null);
  let tooltipX = $state(0);
  let tooltipY = $state(0);

  function handleMouseMove(e) {
    const svg = e.currentTarget;
    const rect = svg.getBoundingClientRect();
    const relX = ((e.clientX - rect.left) / rect.width) * W;
    const dayIdx = Math.round(((relX - PAD.left) / chartW) * (numDays - 1));
    const clamped = Math.max(0, Math.min(numDays - 1, dayIdx));
    hoveredDay = data[clamped] || null;
    tooltipX = e.clientX - rect.left;
    tooltipY = e.clientY - rect.top;
  }

  function handleMouseLeave() {
    hoveredDay = null;
  }

  // X-axis labels: show every 5th day + last day
  const xLabels = $derived(
    data.filter((d) => d.dia === 1 || d.dia % 5 === 0 || d.dia === numDays)
  );
</script>

<div class="space-y-3">
  <!-- Legend -->
  <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
    <span class="flex items-center gap-1.5">
      <span class="inline-block h-3 w-3 rounded-sm bg-emerald-500"></span>
      Receitas
    </span>
    <span class="flex items-center gap-1.5">
      <span class="inline-block h-3 w-3 rounded-sm bg-rose-500"></span>
      Despesas
    </span>
    <span class="flex items-center gap-1.5">
      <span class="inline-block h-2 w-4 rounded-sm border-2 border-blue-500 bg-transparent"></span>
      Saldo Acumulado
    </span>
  </div>

  <!-- SVG Chart -->
  <div class="relative">
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <svg
      viewBox="0 0 {W} {H}"
      class="w-full"
      style="height: 250px;"
      onmousemove={handleMouseMove}
      onmouseleave={handleMouseLeave}
    >
      <!-- Grid lines -->
      {#each [0.25, 0.5, 0.75, 1] as pct}
        <line
          x1={PAD.left}
          y1={PAD.top + chartH * (1 - pct)}
          x2={W - PAD.right}
          y2={PAD.top + chartH * (1 - pct)}
          stroke="currentColor"
          stroke-opacity="0.08"
          stroke-dasharray="4"
        />
      {/each}

      <!-- Revenue area (emerald) -->
      <path d={areaPath('receita')} fill="rgb(16, 185, 129)" fill-opacity="0.15" />
      <path d={linePath('receita')} fill="none" stroke="rgb(16, 185, 129)" stroke-width="2" />

      <!-- Expense area (rose) -->
      <path d={areaPath('despesa')} fill="rgb(244, 63, 94)" fill-opacity="0.15" />
      <path d={linePath('despesa')} fill="none" stroke="rgb(244, 63, 94)" stroke-width="2" />

      <!-- Negative zone (red shading) -->
      {#if negativeAreaPath()}
        <path d={negativeAreaPath()} fill="rgb(239, 68, 68)" fill-opacity="0.12" />
      {/if}

      <!-- Zero line for accumulated balance -->
      {#if minAccum < 0}
        <line
          x1={PAD.left}
          y1={yAccum(0)}
          x2={W - PAD.right}
          y2={yAccum(0)}
          stroke="rgb(59, 130, 246)"
          stroke-opacity="0.3"
          stroke-dasharray="4"
        />
      {/if}

      <!-- Accumulated balance line (blue) -->
      <path d={accumLinePath()} fill="none" stroke="rgb(59, 130, 246)" stroke-width="2.5" />

      <!-- Today marker -->
      {#if today <= numDays}
        <line
          x1={xPos(today)}
          y1={PAD.top}
          x2={xPos(today)}
          y2={PAD.top + chartH}
          stroke="currentColor"
          stroke-opacity="0.25"
          stroke-width="1"
          stroke-dasharray="3"
        />
        <text
          x={xPos(today)}
          y={PAD.top - 4}
          text-anchor="middle"
          class="fill-muted-foreground"
          font-size="10"
        >Hoje</text>
      {/if}

      <!-- X-axis labels -->
      {#each xLabels as d}
        <text
          x={xPos(d.dia)}
          y={H - 4}
          text-anchor="middle"
          class="fill-muted-foreground"
          font-size="10"
          font-weight={d.dia === today ? 'bold' : 'normal'}
        >{d.dia}</text>
      {/each}

      <!-- Hovered day marker -->
      {#if hoveredDay}
        <line
          x1={xPos(hoveredDay.dia)}
          y1={PAD.top}
          x2={xPos(hoveredDay.dia)}
          y2={PAD.top + chartH}
          stroke="currentColor"
          stroke-opacity="0.4"
          stroke-width="1"
        />
        <circle
          cx={xPos(hoveredDay.dia)}
          cy={yPos(hoveredDay.receita || 0)}
          r="4"
          fill="rgb(16, 185, 129)"
        />
        <circle
          cx={xPos(hoveredDay.dia)}
          cy={yPos(hoveredDay.despesa || 0)}
          r="4"
          fill="rgb(244, 63, 94)"
        />
        <circle
          cx={xPos(hoveredDay.dia)}
          cy={yAccum(hoveredDay.saldo_acumulado || 0)}
          r="4"
          fill="rgb(59, 130, 246)"
        />
      {/if}
    </svg>

    <!-- Tooltip -->
    {#if hoveredDay}
      <div
        class="bg-popover text-popover-foreground pointer-events-none absolute z-10 rounded-lg border p-2 shadow-md"
        style="left: {Math.min(tooltipX + 12, 280)}px; top: {tooltipY - 10}px;"
      >
        <div class="mb-1 text-xs font-bold">Dia {hoveredDay.dia}</div>
        <div class="space-y-0.5 text-[11px]">
          <div class="flex items-center gap-1.5">
            <span class="inline-block h-2 w-2 rounded-full bg-emerald-500"></span>
            Receita: {formatCurrency(hoveredDay.receita || 0, cur)}
          </div>
          <div class="flex items-center gap-1.5">
            <span class="inline-block h-2 w-2 rounded-full bg-rose-500"></span>
            Despesa: {formatCurrency(hoveredDay.despesa || 0, cur)}
          </div>
          <div class="flex items-center gap-1.5">
            <span class="inline-block h-2 w-2 rounded-full bg-blue-500"></span>
            Saldo: {formatCurrency(hoveredDay.saldo_acumulado || 0, cur)}
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>
