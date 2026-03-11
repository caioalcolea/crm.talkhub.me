/**
 * Socket.io client singleton for cowork server connection.
 *
 * The cowork-app receives its config via postMessage from the parent
 * SvelteKit iframe. The socket URL and JWT token come from there.
 */

import { io, Socket } from "socket.io-client";

let socket: Socket | null = null;

export interface CoworkConfig {
  socketUrl: string;
  token: string;
  roomId: string;
  displayName: string;
  isGuest: boolean;
}

export function connectSocket(config: CoworkConfig): Socket {
  if (socket?.connected) {
    socket.disconnect();
  }

  // socketUrl is the origin (e.g. https://crm.talkhub.me/cowork-ws)
  // Traefik StripPrefix removes /cowork-ws before forwarding to the server,
  // so we must include /cowork-ws/socket.io/ as the path so Traefik can match
  // the route and strip it → server receives /socket.io/ as expected.
  const url = new URL(config.socketUrl);
  const basePath = url.pathname.replace(/\/$/, ""); // e.g. "/cowork-ws"

  socket = io(url.origin, {
    path: `${basePath}/socket.io/`,
    transports: ["websocket", "polling"],
    autoConnect: true,
  });

  socket.on("connect", () => {
    console.log("[cowork] Connected to socket server");
    socket!.emit("join-room", { token: config.token });
  });

  socket.on("disconnect", (reason) => {
    console.log("[cowork] Disconnected:", reason);
  });

  socket.on("error", (data: { message: string }) => {
    console.error("[cowork] Server error:", data.message);
  });

  return socket;
}

export function getSocket(): Socket | null {
  return socket;
}

export function disconnectSocket(): void {
  if (socket) {
    socket.emit("leave-room");
    socket.disconnect();
    socket = null;
  }
}
