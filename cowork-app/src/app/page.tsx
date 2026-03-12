"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import {
  connectSocket,
  disconnectSocket,
  type CoworkConfig,
} from "@/lib/socket";
import { bridge } from "@/lib/phaser-socket-bridge";
import { ProximityMediaManager } from "@/lib/proximity-media";
import { listenForParentMessages, sendToParent } from "@/lib/postmessage";

const VideoOverlay = dynamic(() => import("../components/VideoOverlay"), {
  ssr: false,
});

const WhiteboardOverlay = dynamic(() => import("../components/WhiteboardOverlay"), {
  ssr: false,
});

/**
 * Load PhaserGame with SSR disabled — Phaser requires window/document/canvas.
 * All Phaser imports are contained inside PhaserGame.tsx and its scene imports.
 */
const PhaserGame = dynamic(() => import("../components/PhaserGame"), {
  ssr: false,
});

/**
 * Cowork App Main Page
 *
 * This app runs inside an iframe in the SvelteKit CRM.
 * It receives its configuration (JWT token, socket URL) via postMessage.
 *
 * For development/standalone use, it can also read from URL params:
 *   ?token=<jwt>&socketUrl=<url>
 */
export default function CoworkPage() {
  const [status, setStatus] = useState<"waiting" | "connecting" | "connected" | "error">("waiting");
  const [errorMsg, setErrorMsg] = useState("");
  const [config, setConfig] = useState<CoworkConfig | null>(null);
  const [showOverlay, setShowOverlay] = useState(true); // A3: click-to-play overlay
  const [chatOpen, setChatOpen] = useState(false);
  const [chatText, setChatText] = useState("");
  const chatInputRef = useRef<HTMLInputElement>(null);

  // WebRTC proximity A/V state
  const [remoteStreams, setRemoteStreams] = useState<Map<string, MediaStream>>(new Map());
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [videoEnabled, setVideoEnabled] = useState(true);
  const [playerNames, setPlayerNames] = useState<Map<string, string>>(new Map());
  const mediaManagerRef = useRef<ProximityMediaManager | null>(null);

  // Pre-acquired media stream from user gesture (overlay click).
  // Stored here so it can be passed to ProximityMediaManager when it's created.
  const preAcquiredStreamRef = useRef<MediaStream | null>(null);

  // Whiteboard state
  const [whiteboardOpen, setWhiteboardOpen] = useState(false);
  const [activeWhiteboardId, setActiveWhiteboardId] = useState<string | null>(null);

  const initCowork = useCallback((cfg: CoworkConfig) => {
    setConfig(cfg);
    setStatus("connecting");

    try {
      const sock = connectSocket(cfg);

      // Give the socket to the bridge so Phaser can receive events
      bridge.setSocket(sock);

      sock.on("room-state", () => {
        setStatus("connected");
        sendToParent({ type: "cowork-status", payload: { roomId: cfg.roomId } });
      });

      sock.on("connect_error", (err: Error) => {
        setStatus("error");
        setErrorMsg(`Connection failed: ${err.message}`);
        sendToParent({ type: "cowork-error", payload: { message: err.message } });
      });
    } catch (err) {
      setStatus("error");
      setErrorMsg(String(err));
    }
  }, []);

  const destroyCowork = useCallback(() => {
    bridge.destroy();
    disconnectSocket();
    setStatus("waiting");
    setConfig(null);
  }, []);

  // Listen for postMessage from parent SvelteKit
  useEffect(() => {
    const cleanup = listenForParentMessages(initCowork, destroyCowork);
    sendToParent({ type: "cowork-ready" });

    // Also check URL params for standalone/dev mode
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const token = params.get("token");
      const socketUrl = params.get("socketUrl");
      if (token && socketUrl) {
        initCowork({
          token,
          socketUrl,
          roomId: "",
          displayName: "",
          isGuest: false,
        });
      }
    }

    return cleanup;
  }, [initCowork, destroyCowork]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      bridge.destroy();
      disconnectSocket();
    };
  }, []);

  // Open chat input on ENTER key (only when game is active and chat is closed)
  useEffect(() => {
    if (status !== "connected") return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.code === "Enter" && !chatOpen) {
        e.preventDefault();
        setChatOpen(true);
        // Focus input after React renders it
        setTimeout(() => chatInputRef.current?.focus(), 50);
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [status, chatOpen]);

  // WebRTC proximity A/V — connect/disconnect media manager based on status
  useEffect(() => {
    if (status !== "connected") return;

    const manager = new ProximityMediaManager();
    mediaManagerRef.current = manager;

    const socketId = bridge.getSocketId();
    if (socketId) manager.setMySocketId(socketId);

    manager.setSendSignal((targetId, signal) => {
      bridge.emitWebRTCSignal(targetId, signal);
    });

    // Pass pre-acquired stream from overlay click gesture
    if (preAcquiredStreamRef.current) {
      manager.setPreAcquiredStream(preAcquiredStreamRef.current);
    }

    const onProximity = (data: { nearbyIds: string[] }) => {
      manager.updateNearby(data.nearbyIds);
    };
    bridge.on("proximity-update", onProximity);

    const onSignal = (data: { fromId: string; signal: any }) => {
      manager.handleSignal(data.fromId, data.signal);
    };
    bridge.on("webrtc-signal", onSignal);

    manager.on("stream-added", ({ peerId, stream }: { peerId: string; stream: MediaStream }) => {
      setRemoteStreams((prev) => new Map(prev).set(peerId, stream));
    });
    manager.on("stream-removed", ({ peerId }: { peerId: string }) => {
      setRemoteStreams((prev) => {
        const next = new Map(prev);
        next.delete(peerId);
        return next;
      });
    });
    manager.on("local-stream", ({ stream }: { stream: MediaStream }) => {
      setLocalStream(stream);
    });

    // Track player names for video labels
    const onRoomState = (data: { players: Array<{ id: string; displayName: string }> }) => {
      const names = new Map<string, string>();
      data.players.forEach((p) => names.set(p.id, p.displayName));
      setPlayerNames(names);
    };
    const onPlayerJoined = (data: { id: string; displayName: string }) => {
      setPlayerNames((prev) => new Map(prev).set(data.id, data.displayName));
    };
    const onPlayerLeft = (data: { id: string }) => {
      setPlayerNames((prev) => {
        const next = new Map(prev);
        next.delete(data.id);
        return next;
      });
    };
    bridge.on("room-state", onRoomState);
    bridge.on("player-joined", onPlayerJoined);
    bridge.on("player-left", onPlayerLeft);

    // Whiteboard open request from GameScene (R key near whiteboard)
    const onWhiteboardOpenRequest = (data: { whiteboardId: string }) => {
      setActiveWhiteboardId(data.whiteboardId);
      setWhiteboardOpen(true);
    };
    bridge.on("whiteboard-open-request", onWhiteboardOpenRequest);

    return () => {
      bridge.off("proximity-update", onProximity);
      bridge.off("webrtc-signal", onSignal);
      bridge.off("room-state", onRoomState);
      bridge.off("player-joined", onPlayerJoined);
      bridge.off("player-left", onPlayerLeft);
      bridge.off("whiteboard-open-request", onWhiteboardOpenRequest);
      manager.destroy();
      mediaManagerRef.current = null;
      setRemoteStreams(new Map());
      setLocalStream(null);
    };
  }, [status]);

  const sendChat = useCallback(() => {
    const msg = chatText.trim();
    if (msg) {
      bridge.emitChat(msg);
    }
    setChatText("");
    setChatOpen(false);
    // Return focus to game canvas
    const canvas = document.querySelector("canvas");
    if (canvas) canvas.focus();
  }, [chatText]);

  if (status === "waiting") {
    return (
      <div style={centerStyle}>
        <div style={cardStyle}>
          <div style={spinnerStyle} />
          <p style={{ color: "#6b7280", margin: 0 }}>Aguardando configuração...</p>
          <p style={{ color: "#9ca3af", fontSize: "12px", margin: 0 }}>
            A sala será inicializada pelo CRM.
          </p>
        </div>
      </div>
    );
  }

  if (status === "connecting") {
    return (
      <div style={centerStyle}>
        <div style={cardStyle}>
          <div style={spinnerStyle} />
          <p style={{ color: "#6b7280", margin: 0 }}>Conectando ao servidor...</p>
        </div>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div style={centerStyle}>
        <div style={cardStyle}>
          <p style={{ color: "#ef4444", fontWeight: 600, margin: 0 }}>Erro de conexão</p>
          <p style={{ color: "#6b7280", fontSize: "13px", margin: 0 }}>{errorMsg}</p>
          <button
            onClick={() => config && initCowork(config)}
            style={buttonStyle}
          >
            Tentar novamente
          </button>
        </div>
      </div>
    );
  }

  // status === "connected" — render Phaser game
  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        backgroundColor: "#1e293b",
        position: "relative",
      }}
    >
      <PhaserGame />
      {/* WebRTC proximity video overlay */}
      <VideoOverlay
        remoteStreams={remoteStreams}
        localStream={localStream}
        audioEnabled={audioEnabled}
        videoEnabled={videoEnabled}
        onToggleAudio={() => {
          const enabled = mediaManagerRef.current?.toggleAudio() ?? true;
          setAudioEnabled(enabled);
        }}
        onToggleVideo={() => {
          const enabled = mediaManagerRef.current?.toggleVideo() ?? true;
          setVideoEnabled(enabled);
        }}
        onDisconnect={() => {
          mediaManagerRef.current?.destroy();
          mediaManagerRef.current = null;
          setRemoteStreams(new Map());
          setLocalStream(null);
        }}
        playerNames={playerNames}
      />
      {/* Whiteboard overlay */}
      {whiteboardOpen && activeWhiteboardId && (
        <WhiteboardOverlay
          whiteboardId={activeWhiteboardId}
          onClose={() => {
            setWhiteboardOpen(false);
            setActiveWhiteboardId(null);
            const canvas = document.querySelector("canvas");
            if (canvas) canvas.focus();
          }}
        />
      )}
      {/* Chat input — opens on ENTER, sends on ENTER, closes on ESC */}
      {chatOpen && (
        <div style={chatInputContainerStyle}>
          <input
            ref={chatInputRef}
            type="text"
            value={chatText}
            onChange={(e) => setChatText(e.target.value.slice(0, 200))}
            onKeyDown={(e) => {
              // Stop WASD keys from reaching the game while typing
              e.stopPropagation();
              if (e.code === "Enter") {
                e.preventDefault();
                sendChat();
              } else if (e.code === "Escape") {
                setChatText("");
                setChatOpen(false);
                const canvas = document.querySelector("canvas");
                if (canvas) canvas.focus();
              }
            }}
            placeholder="Digite uma mensagem... (ESC para cancelar)"
            style={chatInputStyle}
            maxLength={200}
            autoComplete="off"
          />
        </div>
      )}
      {/* Hint to open chat */}
      {!chatOpen && !showOverlay && (
        <div style={chatHintStyle}>
          ENTER para chat
        </div>
      )}
      {/* A3: Click-to-play overlay — grabs focus from parent iframe */}
      {showOverlay && (
        <div
          onClick={() => {
            setShowOverlay(false);
            // Focus the iframe window + game canvas (critical for keyboard in iframe)
            window.focus();
            const canvas = document.querySelector("canvas");
            if (canvas) {
              canvas.setAttribute("tabindex", "1");
              canvas.focus();
            }

            // Pre-acquire media on user gesture — critical for iframe permission.
            // Browsers require getUserMedia to be called in response to a user
            // interaction (click/tap). If we wait until proximity triggers it,
            // the browser may silently deny the request inside an iframe.
            if (!preAcquiredStreamRef.current) {
              navigator.mediaDevices.getUserMedia({
                audio: true,
                video: { width: { ideal: 320 }, height: { ideal: 240 }, frameRate: { max: 15 } },
              })
                .then((stream) => {
                  console.log("[Cowork] Pre-acquired media stream on user gesture");
                  preAcquiredStreamRef.current = stream;
                  // If manager already exists, pass the stream immediately
                  if (mediaManagerRef.current) {
                    mediaManagerRef.current.setPreAcquiredStream(stream);
                  }
                })
                .catch(() => {
                  console.log("[Cowork] Media permission denied on overlay click (will retry on proximity)");
                });
            }
          }}
          style={overlayStyle}
        >
          <div style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "8px",
            padding: "32px 48px",
            borderRadius: "12px",
            backgroundColor: "rgba(30, 41, 59, 0.9)",
            boxShadow: "0 4px 24px rgba(0,0,0,0.3)",
          }}>
            <p style={{ color: "#e2e8f0", fontSize: "16px", fontWeight: 600, margin: 0 }}>
              Sala Cowork
            </p>
            <p style={{ color: "#94a3b8", fontSize: "13px", margin: 0 }}>
              Clique para entrar
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Inline styles (no Tailwind in cowork-app) ──────────────
const centerStyle: React.CSSProperties = {
  width: "100vw",
  height: "100vh",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  backgroundColor: "#f1f5f9",
};

const cardStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  gap: "12px",
  padding: "32px",
  borderRadius: "12px",
  backgroundColor: "#fff",
  boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
};

const spinnerStyle: React.CSSProperties = {
  width: "32px",
  height: "32px",
  border: "3px solid #e5e7eb",
  borderTop: "3px solid #3b82f6",
  borderRadius: "50%",
  animation: "spin 1s linear infinite",
};

const buttonStyle: React.CSSProperties = {
  padding: "8px 16px",
  borderRadius: "6px",
  border: "1px solid #d1d5db",
  backgroundColor: "#fff",
  cursor: "pointer",
  fontSize: "13px",
};

const chatInputContainerStyle: React.CSSProperties = {
  position: "absolute",
  bottom: "16px",
  left: "50%",
  transform: "translateX(-50%)",
  zIndex: 9999,
  width: "min(400px, 90vw)",
};

const chatInputStyle: React.CSSProperties = {
  width: "100%",
  padding: "10px 14px",
  borderRadius: "8px",
  border: "1px solid #475569",
  backgroundColor: "#1e293bee",
  color: "#e2e8f0",
  fontSize: "14px",
  outline: "none",
  fontFamily: "-apple-system, BlinkMacSystemFont, sans-serif",
  boxSizing: "border-box",
};

const chatHintStyle: React.CSSProperties = {
  position: "absolute",
  bottom: "8px",
  left: "50%",
  transform: "translateX(-50%)",
  color: "#64748b",
  fontSize: "11px",
  fontFamily: "-apple-system, BlinkMacSystemFont, sans-serif",
  pointerEvents: "none",
  zIndex: 100,
};

const overlayStyle: React.CSSProperties = {
  position: "absolute",
  inset: 0,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  backgroundColor: "rgba(15, 23, 42, 0.7)",
  cursor: "pointer",
  zIndex: 10000,
};
