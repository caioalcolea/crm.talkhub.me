/**
 * TalkHub CRM — Cowork Room Socket.io Server
 *
 * Manages real-time presence, movement, and proximity-based
 * audio/video for virtual coworking rooms.
 *
 * Architecture:
 * - In-memory room state (Map) — no Redis needed for single replica (V1)
 * - JWT validation using same SECRET_KEY as Django backend
 * - Runs on port 3100, proxied via Traefik at /cowork-ws/
 *
 * Events:
 *   Client -> Server:
 *     join-room { token }           → validate JWT, add player to room
 *     move { x, y, direction }      → broadcast position update
 *     leave-room                     → remove player
 *
 *   Server -> Client:
 *     room-state { players }        → full room state on join
 *     player-joined { player }      → new player entered
 *     player-moved { id, x, y, direction }
 *     player-left { id }            → player disconnected
 *     proximity-update { nearbyIds } → players within PROXIMITY_RADIUS
 *     error { message }
 */

const http = require("http");
const jwt = require("jsonwebtoken");
const { Server } = require("socket.io");

// ── Config ──────────────────────────────────────────────────
const PORT = parseInt(process.env.PORT || "3100", 10);
const SECRET_KEY = process.env.SECRET_KEY;
const ALLOWED_ORIGINS = (process.env.ALLOWED_ORIGINS || "https://crm.talkhub.me").split(",");
const MAP_WIDTH = parseInt(process.env.MAP_WIDTH || "40", 10);   // tiles (SkyOffice map)
const MAP_HEIGHT = parseInt(process.env.MAP_HEIGHT || "30", 10);  // tiles (SkyOffice map)
// Hysteresis: enter at 3 tiles, exit at 5 tiles — prevents proximity flapping
const PROXIMITY_ENTER = parseInt(process.env.PROXIMITY_ENTER || "3", 10);
const PROXIMITY_EXIT = parseInt(process.env.PROXIMITY_EXIT || "5", 10);
const TICK_RATE_MS = parseInt(process.env.TICK_RATE_MS || "100", 10);

if (!SECRET_KEY) {
  console.error("FATAL: SECRET_KEY environment variable is required");
  process.exit(1);
}

// ── HTTP Server ─────────────────────────────────────────────
const httpServer = http.createServer((req, res) => {
  if (req.url === "/health" || req.url === "/healthz") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "ok", rooms: rooms.size }));
    return;
  }

  // Room participant counts — used by Django serializer to show real-time counts
  if (req.url === "/rooms/status" && req.method === "GET") {
    const roomCounts = {};
    for (const [roomId, room] of rooms) {
      roomCounts[roomId] = room.size;
    }
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ rooms: roomCounts }));
    return;
  }

  res.writeHead(404);
  res.end();
});

// ── Socket.io ───────────────────────────────────────────────
const io = new Server(httpServer, {
  cors: {
    origin: ALLOWED_ORIGINS,
    methods: ["GET", "POST"],
    credentials: true,
  },
  path: "/socket.io/",
  transports: ["websocket", "polling"],
  pingInterval: 10000,
  pingTimeout: 5000,
});

// ── In-Memory State ─────────────────────────────────────────
// rooms: Map<roomId, Map<socketId, Player>>
const rooms = new Map();

/**
 * @typedef {Object} Player
 * @property {string} id - socket.id
 * @property {string} userId - from JWT
 * @property {string} displayName
 * @property {string} email
 * @property {boolean} isGuest
 * @property {string} roomId
 * @property {string} orgId
 * @property {number} x - tile X position
 * @property {number} y - tile Y position
 * @property {string} direction - "up"|"down"|"left"|"right"
 * @property {string} avatarUrl
 * @property {number} joinedAt
 */

// ── JWT Validation ──────────────────────────────────────────
function verifyToken(token) {
  try {
    return jwt.verify(token, SECRET_KEY, { algorithms: ["HS256"] });
  } catch (err) {
    return null;
  }
}

// ── Proximity Calculation (with hysteresis) ─────────────────
// Uses different enter/exit radii to prevent flapping at boundaries.
// Once connected (peer in lastNearbyIds), uses larger EXIT radius.
// New peers must be within smaller ENTER radius to connect.
function getPlayersInProximity(roomId, player) {
  const room = rooms.get(roomId);
  if (!room) return [];

  const currentNearby = new Set(player.lastNearbyIds || []);
  const nearby = [];
  for (const [, other] of room) {
    if (other.id === player.id) continue;
    const dx = Math.abs(other.x - player.x);
    const dy = Math.abs(other.y - player.y);
    const dist = Math.max(dx, dy); // Chebyshev distance
    if (currentNearby.has(other.id)) {
      // Already connected — use larger EXIT radius (stay connected longer)
      if (dist <= PROXIMITY_EXIT) nearby.push(other.id);
    } else {
      // Not connected — use smaller ENTER radius
      if (dist <= PROXIMITY_ENTER) nearby.push(other.id);
    }
  }
  return nearby;
}

// Only emits proximity-update when the nearby list actually changes (diffing).
function broadcastProximityUpdates(roomId) {
  const room = rooms.get(roomId);
  if (!room) return;

  for (const [socketId, player] of room) {
    const nearbyIds = getPlayersInProximity(roomId, player);
    const prev = player.lastNearbyIds || [];
    // Sort for deterministic comparison
    const sortedNew = [...nearbyIds].sort();
    const sortedPrev = [...prev].sort();
    if (
      sortedNew.length === sortedPrev.length &&
      sortedNew.every((id, i) => id === sortedPrev[i])
    ) {
      continue; // No change — skip emission
    }
    player.lastNearbyIds = nearbyIds;
    const socket = io.sockets.sockets.get(socketId);
    if (socket) {
      socket.emit("proximity-update", { nearbyIds });
    }
  }
}

// ── Spawn Position ──────────────────────────────────────────
function getSpawnPosition(roomId) {
  // Spawn in the main corridor area (tile 16,13) — known collision-free zone.
  // Previous spawn at center (20,15) could land inside furniture/walls,
  // causing the Arcade Physics engine to trap the player at velocity 0.
  const room = rooms.get(roomId);
  const playerCount = room ? room.size : 0;
  const centerX = 16;
  const centerY = 13;
  const col = playerCount % 4;
  const row = Math.floor(playerCount / 4);
  return {
    x: Math.min(MAP_WIDTH - 1, centerX + col),
    y: Math.min(MAP_HEIGHT - 1, centerY + row),
  };
}

// ── Whiteboard State ────────────────────────────────────────
// whiteboardState: Map<roomId, Map<whiteboardId, stroke[]>>
const whiteboardState = new Map();

// ── Chat Rate Limiting ──────────────────────────────────────
// Max 5 messages per second per player
const chatRateLimit = new Map(); // socketId → { count, resetAt }
function canSendChat(socketId) {
  const now = Date.now();
  const entry = chatRateLimit.get(socketId);
  if (!entry || now > entry.resetAt) {
    chatRateLimit.set(socketId, { count: 1, resetAt: now + 1000 });
    return true;
  }
  if (entry.count >= 5) return false;
  entry.count++;
  return true;
}

// ── Socket Handlers ─────────────────────────────────────────
io.on("connection", (socket) => {
  let currentPlayer = null;

  socket.on("join-room", (data) => {
    const { token } = data || {};
    if (!token) {
      socket.emit("error", { message: "Token is required" });
      return;
    }

    const payload = verifyToken(token);
    if (!payload) {
      socket.emit("error", { message: "Invalid or expired token" });
      return;
    }

    const { room_id, user_id, display_name, email, is_guest, org_id } = payload;

    // Ensure room exists
    if (!rooms.has(room_id)) {
      rooms.set(room_id, new Map());
    }

    const room = rooms.get(room_id);
    const spawn = getSpawnPosition(room_id);

    currentPlayer = {
      id: socket.id,
      userId: user_id,
      displayName: display_name,
      email: email || "",
      isGuest: is_guest || false,
      roomId: room_id,
      orgId: org_id,
      x: spawn.x,
      y: spawn.y,
      direction: "down",
      avatarUrl: "",
      joinedAt: Date.now(),
      lastNearbyIds: [], // for proximity hysteresis diffing
    };

    room.set(socket.id, currentPlayer);
    socket.join(room_id);

    // Send full room state to joining player
    const players = Array.from(room.values()).map((p) => ({
      id: p.id,
      userId: p.userId,
      displayName: p.displayName,
      isGuest: p.isGuest,
      x: p.x,
      y: p.y,
      direction: p.direction,
      avatarUrl: p.avatarUrl,
    }));

    socket.emit("room-state", { players, roomId: room_id });

    // Notify others
    socket.to(room_id).emit("player-joined", {
      id: currentPlayer.id,
      userId: currentPlayer.userId,
      displayName: currentPlayer.displayName,
      isGuest: currentPlayer.isGuest,
      x: currentPlayer.x,
      y: currentPlayer.y,
      direction: currentPlayer.direction,
      avatarUrl: currentPlayer.avatarUrl,
    });

    console.log(
      `[${room_id}] ${display_name} joined (${is_guest ? "guest" : "member"}) — ${room.size} players`
    );

    // Initial proximity update
    broadcastProximityUpdates(room_id);
  });

  socket.on("move", (data) => {
    if (!currentPlayer) return;

    const { x, y, direction } = data || {};
    if (typeof x !== "number" || typeof y !== "number") return;

    // Clamp to map bounds
    currentPlayer.x = Math.max(0, Math.min(MAP_WIDTH - 1, x));
    currentPlayer.y = Math.max(0, Math.min(MAP_HEIGHT - 1, y));
    if (direction) currentPlayer.direction = direction;

    // Broadcast movement to others in the room
    socket.to(currentPlayer.roomId).emit("player-moved", {
      id: currentPlayer.id,
      x: currentPlayer.x,
      y: currentPlayer.y,
      direction: currentPlayer.direction,
    });

    // Recalculate proximity
    broadcastProximityUpdates(currentPlayer.roomId);
  });

  // ── Chat ────────────────────────────────────────────────
  socket.on("send-chat", (data) => {
    if (!currentPlayer) return;
    const { message } = data || {};
    if (!message || typeof message !== "string") return;
    const trimmed = message.trim().slice(0, 200);
    if (!trimmed) return;

    // Rate limit
    if (!canSendChat(socket.id)) return;

    // Broadcast to entire room (including sender, so their bubble shows too)
    io.to(currentPlayer.roomId).emit("chat-message", {
      id: currentPlayer.id,
      displayName: currentPlayer.displayName,
      message: trimmed,
      timestamp: Date.now(),
    });
  });

  // ── Sit/Stand ───────────────────────────────────────────
  socket.on("sit-action", (data) => {
    if (!currentPlayer) return;
    const { sitting } = data || {};
    currentPlayer.sitting = !!sitting;

    socket.to(currentPlayer.roomId).emit("player-sit", {
      id: currentPlayer.id,
      sitting: currentPlayer.sitting,
      x: currentPlayer.x,
      y: currentPlayer.y,
      direction: currentPlayer.direction,
    });
  });

  // ── WebRTC Signaling Relay ─────────────────────────────────
  socket.on("webrtc-signal", (data) => {
    if (!currentPlayer) return;
    const { targetId, signal } = data || {};
    if (!targetId || !signal) return;

    // Only relay to players in the same room
    const room = rooms.get(currentPlayer.roomId);
    if (!room || !room.has(targetId)) return;

    const targetSocket = io.sockets.sockets.get(targetId);
    if (targetSocket) {
      targetSocket.emit("webrtc-signal", {
        fromId: socket.id,
        signal,
      });
    }
  });

  // ── Whiteboard ─────────────────────────────────────────────
  socket.on("whiteboard-draw", (data) => {
    if (!currentPlayer) return;
    const { whiteboardId, stroke } = data || {};
    if (!whiteboardId || !stroke) return;

    const roomKey = currentPlayer.roomId;
    if (!whiteboardState.has(roomKey)) whiteboardState.set(roomKey, new Map());
    const roomBoards = whiteboardState.get(roomKey);
    if (!roomBoards.has(whiteboardId)) roomBoards.set(whiteboardId, []);
    const strokes = roomBoards.get(whiteboardId);
    strokes.push(stroke);
    // Cap at 5000 strokes per board to prevent memory bloat
    if (strokes.length > 5000) strokes.splice(0, strokes.length - 5000);

    socket.to(roomKey).emit("whiteboard-draw", {
      whiteboardId,
      stroke,
      playerId: socket.id,
    });
  });

  socket.on("whiteboard-clear", (data) => {
    if (!currentPlayer) return;
    const { whiteboardId } = data || {};
    if (!whiteboardId) return;

    const roomBoards = whiteboardState.get(currentPlayer.roomId);
    if (roomBoards) roomBoards.set(whiteboardId, []);

    socket.to(currentPlayer.roomId).emit("whiteboard-clear", { whiteboardId });
  });

  socket.on("whiteboard-open", (data) => {
    if (!currentPlayer) return;
    const { whiteboardId } = data || {};
    if (!whiteboardId) return;

    const roomBoards = whiteboardState.get(currentPlayer.roomId);
    const strokes = roomBoards?.get(whiteboardId) || [];
    socket.emit("whiteboard-state", { whiteboardId, strokes });
  });

  socket.on("leave-room", () => {
    handleDisconnect();
  });

  socket.on("disconnect", () => {
    handleDisconnect();
  });

  function handleDisconnect() {
    if (!currentPlayer) return;

    const { roomId, displayName } = currentPlayer;
    const room = rooms.get(roomId);

    if (room) {
      room.delete(socket.id);
      socket.to(roomId).emit("player-left", { id: socket.id });

      console.log(`[${roomId}] ${displayName} left — ${room.size} players`);

      // Clean up empty rooms
      if (room.size === 0) {
        rooms.delete(roomId);
        whiteboardState.delete(roomId);
        console.log(`[${roomId}] Room destroyed (empty)`);
      } else {
        broadcastProximityUpdates(roomId);
      }
    }

    chatRateLimit.delete(socket.id);
    currentPlayer = null;
  }
});

// ── Zombie Player Reaper ────────────────────────────────────
// Periodically check for players whose socket disconnected without
// firing the disconnect event (network drops, frozen tabs, etc.)
const REAP_INTERVAL_MS = 30000; // every 30s

setInterval(() => {
  let reaped = 0;
  for (const [roomId, room] of rooms) {
    for (const [socketId, player] of room) {
      const sock = io.sockets.sockets.get(socketId);
      if (!sock || !sock.connected) {
        room.delete(socketId);
        // Notify remaining players
        for (const [otherId] of room) {
          const otherSock = io.sockets.sockets.get(otherId);
          if (otherSock) otherSock.emit("player-left", { id: socketId });
        }
        reaped++;
        console.log(`[${roomId}] Reaped zombie: ${player.displayName}`);
      }
    }
    // Clean up empty rooms
    if (room.size === 0) {
      rooms.delete(roomId);
    }
  }
  if (reaped > 0) {
    console.log(`Reaper: cleaned ${reaped} zombie player(s)`);
  }
}, REAP_INTERVAL_MS);

// ── Start ───────────────────────────────────────────────────
httpServer.listen(PORT, "0.0.0.0", () => {
  console.log(`🏢 Cowork Server listening on port ${PORT}`);
  console.log(`   Allowed origins: ${ALLOWED_ORIGINS.join(", ")}`);
  console.log(`   Proximity radius: ${PROXIMITY_RADIUS} tiles`);
});

// Graceful shutdown
process.on("SIGTERM", () => {
  console.log("Shutting down...");
  io.close();
  httpServer.close(() => process.exit(0));
});
