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
const PROXIMITY_RADIUS = parseInt(process.env.PROXIMITY_RADIUS || "3", 10); // tiles
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

// ── Proximity Calculation ───────────────────────────────────
function getPlayersInProximity(roomId, player) {
  const room = rooms.get(roomId);
  if (!room) return [];

  const nearby = [];
  for (const [, other] of room) {
    if (other.id === player.id) continue;
    const dx = Math.abs(other.x - player.x);
    const dy = Math.abs(other.y - player.y);
    if (dx <= PROXIMITY_RADIUS && dy <= PROXIMITY_RADIUS) {
      nearby.push(other.id);
    }
  }
  return nearby;
}

function broadcastProximityUpdates(roomId) {
  const room = rooms.get(roomId);
  if (!room) return;

  for (const [socketId, player] of room) {
    const nearbyIds = getPlayersInProximity(roomId, player);
    const socket = io.sockets.sockets.get(socketId);
    if (socket) {
      socket.emit("proximity-update", { nearbyIds });
    }
  }
}

// ── Spawn Position ──────────────────────────────────────────
function getSpawnPosition(roomId) {
  // Spread players across a 20x15 grid area
  const room = rooms.get(roomId);
  const playerCount = room ? room.size : 0;
  // Simple grid placement: row-major, 5 per row
  const col = playerCount % 5;
  const row = Math.floor(playerCount / 5);
  return {
    x: 3 + col * 3,  // start at col 3, spacing of 3
    y: 3 + row * 3,  // start at row 3, spacing of 3
  };
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

    // Clamp to reasonable bounds (0-50 tiles)
    currentPlayer.x = Math.max(0, Math.min(50, x));
    currentPlayer.y = Math.max(0, Math.min(50, y));
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
        console.log(`[${roomId}] Room destroyed (empty)`);
      } else {
        broadcastProximityUpdates(roomId);
      }
    }

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
