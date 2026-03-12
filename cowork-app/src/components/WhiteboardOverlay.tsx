"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { bridge } from "@/lib/phaser-socket-bridge";

interface Stroke {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  color: string;
  width: number;
  tool: "pen" | "eraser";
}

interface WhiteboardOverlayProps {
  whiteboardId: string;
  onClose: () => void;
}

const COLORS = ["#000000", "#ef4444", "#3b82f6", "#22c55e", "#f59e0b", "#8b5cf6"];
const WIDTHS = [2, 4, 8];

export default function WhiteboardOverlay({ whiteboardId, onClose }: WhiteboardOverlayProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [color, setColor] = useState("#000000");
  const [lineWidth, setLineWidth] = useState(4);
  const [tool, setTool] = useState<"pen" | "eraser">("pen");
  const isDrawing = useRef(false);
  const lastPos = useRef<{ x: number; y: number } | null>(null);

  // Request existing strokes on mount
  useEffect(() => {
    bridge.emitWhiteboardOpen(whiteboardId);
  }, [whiteboardId]);

  // Draw a single stroke on canvas
  const drawStroke = useCallback((ctx: CanvasRenderingContext2D, stroke: Stroke, w: number, h: number) => {
    ctx.save();
    if (stroke.tool === "eraser") {
      ctx.globalCompositeOperation = "destination-out";
    } else {
      ctx.globalCompositeOperation = "source-over";
      ctx.strokeStyle = stroke.color;
    }
    ctx.lineWidth = stroke.width;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    ctx.moveTo(stroke.x1 * w, stroke.y1 * h);
    ctx.lineTo(stroke.x2 * w, stroke.y2 * h);
    ctx.stroke();
    ctx.restore();
  }, []);

  // Listen for incoming whiteboard events
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const onState = (data: { whiteboardId: string; strokes: Stroke[] }) => {
      if (data.whiteboardId !== whiteboardId) return;
      // Clear and replay all strokes
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (const stroke of data.strokes) {
        drawStroke(ctx, stroke, canvas.width, canvas.height);
      }
    };

    const onDraw = (data: { whiteboardId: string; stroke: Stroke }) => {
      if (data.whiteboardId !== whiteboardId) return;
      drawStroke(ctx, data.stroke, canvas.width, canvas.height);
    };

    const onClear = (data: { whiteboardId: string }) => {
      if (data.whiteboardId !== whiteboardId) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    };

    bridge.on("whiteboard-state", onState);
    bridge.on("whiteboard-draw", onDraw);
    bridge.on("whiteboard-clear", onClear);

    return () => {
      bridge.off("whiteboard-state", onState);
      bridge.off("whiteboard-draw", onDraw);
      bridge.off("whiteboard-clear", onClear);
    };
  }, [whiteboardId, drawStroke]);

  // ESC to close
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.code === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        onClose();
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  // Drawing handlers
  const getPos = (e: React.MouseEvent | React.TouchEvent): { x: number; y: number } | null => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    let clientX: number, clientY: number;

    if ("touches" in e) {
      if (e.touches.length === 0) return null;
      clientX = e.touches[0].clientX;
      clientY = e.touches[0].clientY;
    } else {
      clientX = e.clientX;
      clientY = e.clientY;
    }

    return {
      x: (clientX - rect.left) / rect.width,
      y: (clientY - rect.top) / rect.height,
    };
  };

  const startDraw = (e: React.MouseEvent | React.TouchEvent) => {
    const pos = getPos(e);
    if (!pos) return;
    isDrawing.current = true;
    lastPos.current = pos;
  };

  const moveDraw = (e: React.MouseEvent | React.TouchEvent) => {
    if (!isDrawing.current || !lastPos.current) return;
    const pos = getPos(e);
    if (!pos) return;

    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const stroke: Stroke = {
      x1: lastPos.current.x,
      y1: lastPos.current.y,
      x2: pos.x,
      y2: pos.y,
      color,
      width: tool === "eraser" ? 20 : lineWidth,
      tool,
    };

    // Draw locally
    drawStroke(ctx, stroke, canvas.width, canvas.height);

    // Send to server
    bridge.emitWhiteboardDraw(whiteboardId, stroke);

    lastPos.current = pos;
  };

  const endDraw = () => {
    isDrawing.current = false;
    lastPos.current = null;
  };

  const handleClear = () => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (canvas && ctx) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
    bridge.emitWhiteboardClear(whiteboardId);
  };

  return (
    <div style={overlayStyle} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div style={containerStyle}>
        {/* Toolbar */}
        <div style={toolbarStyle}>
          {/* Colors */}
          <div style={{ display: "flex", gap: 4 }}>
            {COLORS.map((c) => (
              <button
                key={c}
                onClick={() => { setColor(c); setTool("pen"); }}
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: 4,
                  backgroundColor: c,
                  border: color === c && tool === "pen" ? "2px solid #e2e8f0" : "2px solid transparent",
                  cursor: "pointer",
                }}
              />
            ))}
          </div>

          {/* Widths */}
          <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
            {WIDTHS.map((w) => (
              <button
                key={w}
                onClick={() => { setLineWidth(w); setTool("pen"); }}
                style={{
                  ...btnStyle,
                  fontWeight: lineWidth === w && tool === "pen" ? 700 : 400,
                  backgroundColor: lineWidth === w && tool === "pen" ? "rgba(59, 130, 246, 0.3)" : "transparent",
                }}
              >
                {w}px
              </button>
            ))}
          </div>

          {/* Eraser */}
          <button
            onClick={() => setTool(tool === "eraser" ? "pen" : "eraser")}
            style={{
              ...btnStyle,
              backgroundColor: tool === "eraser" ? "rgba(239, 68, 68, 0.3)" : "transparent",
              border: tool === "eraser" ? "1px solid #ef4444" : "1px solid #475569",
            }}
          >
            Borracha
          </button>

          {/* Clear */}
          <button onClick={handleClear} style={{ ...btnStyle, border: "1px solid #ef4444", color: "#ef4444" }}>
            Limpar
          </button>

          {/* Close */}
          <button onClick={onClose} style={{ ...btnStyle, marginLeft: "auto", border: "1px solid #64748b" }}>
            ESC Fechar
          </button>
        </div>

        {/* Canvas */}
        <canvas
          ref={canvasRef}
          width={800}
          height={600}
          style={canvasStyle}
          onMouseDown={startDraw}
          onMouseMove={moveDraw}
          onMouseUp={endDraw}
          onMouseLeave={endDraw}
          onTouchStart={startDraw}
          onTouchMove={moveDraw}
          onTouchEnd={endDraw}
        />
      </div>
    </div>
  );
}

// ── Styles ──────────────────────────────────────────────────

const overlayStyle: React.CSSProperties = {
  position: "absolute",
  inset: 0,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  backgroundColor: "rgba(15, 23, 42, 0.6)",
  zIndex: 9800,
};

const containerStyle: React.CSSProperties = {
  width: "min(70vw, 840px)",
  display: "flex",
  flexDirection: "column",
  gap: 8,
  backgroundColor: "rgba(30, 41, 59, 0.95)",
  borderRadius: 12,
  padding: 12,
  boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
};

const toolbarStyle: React.CSSProperties = {
  display: "flex",
  gap: 12,
  alignItems: "center",
  flexWrap: "wrap",
  padding: "4px 0",
};

const btnStyle: React.CSSProperties = {
  padding: "4px 10px",
  borderRadius: 4,
  fontSize: 11,
  fontWeight: 500,
  cursor: "pointer",
  color: "#e2e8f0",
  backgroundColor: "transparent",
  border: "1px solid #475569",
  fontFamily: "-apple-system, BlinkMacSystemFont, sans-serif",
};

const canvasStyle: React.CSSProperties = {
  width: "100%",
  aspectRatio: "4/3",
  borderRadius: 8,
  backgroundColor: "#ffffff",
  cursor: "crosshair",
  touchAction: "none",
};
