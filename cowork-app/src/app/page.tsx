"use client";

import { useEffect, useState, useCallback } from "react";
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
      }}
    >
      <PhaserGame />
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
