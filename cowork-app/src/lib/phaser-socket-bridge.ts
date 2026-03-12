/**
 * Bridge between React (Socket.io) and Phaser (game loop).
 *
 * React owns the socket connection lifecycle. Phaser owns the 60fps render loop.
 * They must NOT import each other directly. This bridge is a singleton EventEmitter
 * that both sides can access without creating circular dependencies.
 *
 * Flow:
 *   React: connectSocket() → bridge.setSocket(socket) → socket events → bridge.emit()
 *   Phaser: bridge.on('player-joined', ...) → create sprite
 *   Phaser: bridge.emitMove(x, y, dir) → bridge → socket.emit('move', ...)
 */

type Listener = (...args: any[]) => void;

class PhaserSocketBridge {
  private listeners = new Map<string, Set<Listener>>();
  private socket: any = null;
  private socketListeners: Array<{ event: string; fn: Listener }> = [];
  private lastRoomState: any = null;

  /** React calls this after Socket.io connects */
  setSocket(socket: any): void {
    // Clean up previous socket listeners
    this.clearSocketListeners();
    this.socket = socket;
    this.lastRoomState = null;

    // Forward server events to Phaser
    const serverEvents = [
      "room-state",
      "player-joined",
      "player-moved",
      "player-left",
      "proximity-update",
      "chat-message",
      "player-sit",
      "webrtc-signal",
      "whiteboard-draw",
      "whiteboard-clear",
      "whiteboard-state",
      "error",
    ];

    for (const event of serverEvents) {
      const fn = (data: any) => {
        // Buffer room-state so GameScene can replay it after late registration
        if (event === "room-state") this.lastRoomState = data;
        this.emit(event, data);
      };
      socket.on(event, fn);
      this.socketListeners.push({ event, fn });
    }
  }

  /** Clean up socket event listeners */
  clearSocketListeners(): void {
    if (this.socket) {
      for (const { event, fn } of this.socketListeners) {
        this.socket.off(event, fn);
      }
    }
    this.socketListeners = [];
  }

  /** Disconnect and clean up everything */
  destroy(): void {
    this.clearSocketListeners();
    this.socket = null;
    this.listeners.clear();
    this.lastRoomState = null;
  }

  /**
   * Replay the last room-state event.
   * GameScene calls this after registering its listeners, because
   * room-state fires BEFORE Phaser finishes loading assets.
   */
  replayRoomState(): void {
    if (this.lastRoomState) {
      this.emit("room-state", this.lastRoomState);
    }
  }

  getSocketId(): string | null {
    return this.socket?.id || null;
  }

  /** Phaser calls this when the local player moves */
  emitMove(x: number, y: number, direction: string): void {
    this.socket?.emit("move", { x, y, direction });
  }

  /** Send a chat message to the room */
  emitChat(message: string): void {
    this.socket?.emit("send-chat", { message });
  }

  /** Notify server of sit/stand state change */
  emitSit(sitting: boolean): void {
    this.socket?.emit("sit-action", { sitting });
  }

  /** Send WebRTC signaling data to a specific peer via server relay */
  emitWebRTCSignal(targetId: string, signal: any): void {
    this.socket?.emit("webrtc-signal", { targetId, signal });
  }

  /** Send a whiteboard stroke to the room */
  emitWhiteboardDraw(whiteboardId: string, stroke: any): void {
    this.socket?.emit("whiteboard-draw", { whiteboardId, stroke });
  }

  /** Clear all strokes on a whiteboard */
  emitWhiteboardClear(whiteboardId: string): void {
    this.socket?.emit("whiteboard-clear", { whiteboardId });
  }

  /** Request existing whiteboard strokes for replay */
  emitWhiteboardOpen(whiteboardId: string): void {
    this.socket?.emit("whiteboard-open", { whiteboardId });
  }

  // ── Simple EventEmitter ──────────────────────────────────
  on(event: string, fn: Listener): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(fn);
  }

  off(event: string, fn: Listener): void {
    this.listeners.get(event)?.delete(fn);
  }

  emit(event: string, ...args: any[]): void {
    const fns = this.listeners.get(event);
    if (fns) {
      for (const fn of fns) {
        fn(...args);
      }
    }
  }
}

/** Singleton — accessible from both React and Phaser */
export const bridge = new PhaserSocketBridge();
