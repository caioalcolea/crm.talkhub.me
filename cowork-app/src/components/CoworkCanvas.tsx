"use client";

import { useRef, useEffect, useCallback } from "react";
import type { Socket } from "socket.io-client";

const TILE_SIZE = 32;
const MAP_WIDTH = 20;
const MAP_HEIGHT = 15;
const CANVAS_WIDTH = MAP_WIDTH * TILE_SIZE;
const CANVAS_HEIGHT = MAP_HEIGHT * TILE_SIZE;

// Player colors (cycle through for different players)
const PLAYER_COLORS = [
  "#3b82f6", "#ef4444", "#22c55e", "#f59e0b",
  "#8b5cf6", "#ec4899", "#06b6d4", "#f97316",
];

interface Player {
  id: string;
  userId: string;
  displayName: string;
  isGuest: boolean;
  x: number;
  y: number;
  direction: string;
  avatarUrl: string;
}

interface CoworkCanvasProps {
  socket: Socket | null;
}

export default function CoworkCanvas({ socket }: CoworkCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const playersRef = useRef<Map<string, Player>>(new Map());
  const myIdRef = useRef<string | null>(null);
  const animFrameRef = useRef<number>(0);
  const nearbyRef = useRef<string[]>([]);

  // ── Handle keyboard input ───────────────────────────────
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!socket || !myIdRef.current) return;

      const me = playersRef.current.get(myIdRef.current);
      if (!me) return;

      let { x, y } = me;
      let direction = me.direction;

      switch (e.key) {
        case "ArrowUp":
        case "w":
          y = Math.max(0, y - 1);
          direction = "up";
          break;
        case "ArrowDown":
        case "s":
          y = Math.min(MAP_HEIGHT - 1, y + 1);
          direction = "down";
          break;
        case "ArrowLeft":
        case "a":
          x = Math.max(0, x - 1);
          direction = "left";
          break;
        case "ArrowRight":
        case "d":
          x = Math.min(MAP_WIDTH - 1, x + 1);
          direction = "right";
          break;
        default:
          return;
      }

      e.preventDefault();
      me.x = x;
      me.y = y;
      me.direction = direction;
      socket.emit("move", { x, y, direction });
    },
    [socket]
  );

  // ── Render loop ─────────────────────────────────────────
  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Clear
    ctx.fillStyle = "#f8fafc";
    ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

    // Draw grid
    ctx.strokeStyle = "#e2e8f0";
    ctx.lineWidth = 0.5;
    for (let x = 0; x <= MAP_WIDTH; x++) {
      ctx.beginPath();
      ctx.moveTo(x * TILE_SIZE, 0);
      ctx.lineTo(x * TILE_SIZE, CANVAS_HEIGHT);
      ctx.stroke();
    }
    for (let y = 0; y <= MAP_HEIGHT; y++) {
      ctx.beginPath();
      ctx.moveTo(0, y * TILE_SIZE);
      ctx.lineTo(CANVAS_WIDTH, y * TILE_SIZE);
      ctx.stroke();
    }

    // Draw players
    let colorIdx = 0;
    for (const [id, player] of playersRef.current) {
      const px = player.x * TILE_SIZE + TILE_SIZE / 2;
      const py = player.y * TILE_SIZE + TILE_SIZE / 2;
      const isMe = id === myIdRef.current;
      const isNearby = nearbyRef.current.includes(id);

      // Proximity glow
      if (isNearby || isMe) {
        ctx.beginPath();
        ctx.arc(px, py, TILE_SIZE * 0.8, 0, Math.PI * 2);
        ctx.fillStyle = isMe ? "rgba(59, 130, 246, 0.1)" : "rgba(34, 197, 94, 0.1)";
        ctx.fill();
      }

      // Player circle
      ctx.beginPath();
      ctx.arc(px, py, TILE_SIZE * 0.4, 0, Math.PI * 2);
      ctx.fillStyle = isMe ? "#3b82f6" : PLAYER_COLORS[colorIdx % PLAYER_COLORS.length];
      ctx.fill();

      if (isMe) {
        ctx.strokeStyle = "#1d4ed8";
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Direction indicator
      const dirOffsets: Record<string, [number, number]> = {
        up: [0, -TILE_SIZE * 0.3],
        down: [0, TILE_SIZE * 0.3],
        left: [-TILE_SIZE * 0.3, 0],
        right: [TILE_SIZE * 0.3, 0],
      };
      const [dx, dy] = dirOffsets[player.direction] || [0, 0];
      ctx.beginPath();
      ctx.arc(px + dx, py + dy, 3, 0, Math.PI * 2);
      ctx.fillStyle = "#fff";
      ctx.fill();

      // Name label
      ctx.fillStyle = isMe ? "#1e40af" : "#374151";
      ctx.font = "bold 10px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(
        player.displayName.substring(0, 12),
        px,
        py - TILE_SIZE * 0.5
      );

      if (player.isGuest) {
        ctx.fillStyle = "#9ca3af";
        ctx.font = "8px sans-serif";
        ctx.fillText("(visitante)", px, py - TILE_SIZE * 0.5 + 10);
      }

      colorIdx++;
    }

    // Instructions overlay (top-left)
    ctx.fillStyle = "rgba(0,0,0,0.6)";
    ctx.font = "11px sans-serif";
    ctx.textAlign = "left";
    ctx.fillText("WASD ou ← ↑ → ↓ para mover", 8, 16);
    ctx.fillText(`${playersRef.current.size} online`, 8, 30);

    animFrameRef.current = requestAnimationFrame(render);
  }, []);

  // ── Socket event handlers ───────────────────────────────
  useEffect(() => {
    if (!socket) return;

    function onRoomState(data: { players: Player[]; roomId: string }) {
      playersRef.current.clear();
      for (const p of data.players) {
        playersRef.current.set(p.id, p);
      }
      myIdRef.current = socket!.id || null;
    }

    function onPlayerJoined(player: Player) {
      playersRef.current.set(player.id, player);
    }

    function onPlayerMoved(data: { id: string; x: number; y: number; direction: string }) {
      const p = playersRef.current.get(data.id);
      if (p) {
        p.x = data.x;
        p.y = data.y;
        p.direction = data.direction;
      }
    }

    function onPlayerLeft(data: { id: string }) {
      playersRef.current.delete(data.id);
    }

    function onProximityUpdate(data: { nearbyIds: string[] }) {
      nearbyRef.current = data.nearbyIds;
    }

    socket.on("room-state", onRoomState);
    socket.on("player-joined", onPlayerJoined);
    socket.on("player-moved", onPlayerMoved);
    socket.on("player-left", onPlayerLeft);
    socket.on("proximity-update", onProximityUpdate);

    return () => {
      socket.off("room-state", onRoomState);
      socket.off("player-joined", onPlayerJoined);
      socket.off("player-moved", onPlayerMoved);
      socket.off("player-left", onPlayerLeft);
      socket.off("proximity-update", onProximityUpdate);
    };
  }, [socket]);

  // ── Start render loop + keyboard ────────────────────────
  useEffect(() => {
    animFrameRef.current = requestAnimationFrame(render);
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      cancelAnimationFrame(animFrameRef.current);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [render, handleKeyDown]);

  return (
    <canvas
      ref={canvasRef}
      width={CANVAS_WIDTH}
      height={CANVAS_HEIGHT}
      style={{
        border: "1px solid #e2e8f0",
        borderRadius: "8px",
        maxWidth: "100%",
        height: "auto",
        imageRendering: "pixelated",
      }}
      tabIndex={0}
    />
  );
}
