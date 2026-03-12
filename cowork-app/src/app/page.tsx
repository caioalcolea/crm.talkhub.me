"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import {
  connectSocket,
  disconnectSocket,
  type CoworkConfig,
} from "@/lib/socket";
import { bridge } from "@/lib/phaser-socket-bridge";
import { listenForParentMessages, sendToParent } from "@/lib/postmessage";

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
