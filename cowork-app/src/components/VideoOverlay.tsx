"use client";

import { useEffect, useRef, useCallback } from "react";

interface VideoOverlayProps {
  remoteStreams: Map<string, MediaStream>;
  localStream: MediaStream | null;
  audioEnabled: boolean;
  videoEnabled: boolean;
  onToggleAudio: () => void;
  onToggleVideo: () => void;
  onDisconnect: () => void;
  playerNames: Map<string, string>;
}

/** Renders a single <video> element and attaches the MediaStream via ref */
function VideoTile({
  stream,
  label,
  muted,
  mirrored,
  small,
}: {
  stream: MediaStream;
  label: string;
  muted: boolean;
  mirrored?: boolean;
  small?: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const el = videoRef.current;
    if (el && stream) {
      el.srcObject = stream;
    }
    return () => {
      if (el) el.srcObject = null;
    };
  }, [stream]);

  const w = small ? 100 : 140;
  const h = small ? 75 : 105;

  return (
    <div style={{ position: "relative", width: w, height: h }}>
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted={muted}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          borderRadius: 6,
          backgroundColor: "#0f172a",
          transform: mirrored ? "scaleX(-1)" : undefined,
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          padding: "2px 6px",
          fontSize: 10,
          color: "#e2e8f0",
          backgroundColor: "rgba(0,0,0,0.5)",
          borderRadius: "0 0 6px 6px",
          textAlign: "center",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {label}
      </div>
    </div>
  );
}

export default function VideoOverlay({
  remoteStreams,
  localStream,
  audioEnabled,
  videoEnabled,
  onToggleAudio,
  onToggleVideo,
  onDisconnect,
  playerNames,
}: VideoOverlayProps) {
  // Don't render if no streams at all
  if (!localStream && remoteStreams.size === 0) return null;

  const remoteEntries = Array.from(remoteStreams.entries());

  return (
    <div style={containerStyle}>
      {/* Remote streams */}
      <div style={gridStyle}>
        {remoteEntries.map(([peerId, stream]) => (
          <VideoTile
            key={peerId}
            stream={stream}
            label={playerNames.get(peerId) || peerId.slice(0, 8)}
            muted={false}
          />
        ))}
      </div>

      {/* Local preview */}
      {localStream && (
        <div style={localPreviewContainerStyle}>
          <VideoTile
            stream={localStream}
            label="Voce"
            muted={true}
            mirrored={true}
            small={true}
          />
        </div>
      )}

      {/* Controls */}
      <div style={controlsStyle}>
        <ControlButton
          active={audioEnabled}
          onClick={onToggleAudio}
          activeLabel="Mic"
          inactiveLabel="Mic Off"
        />
        <ControlButton
          active={videoEnabled}
          onClick={onToggleVideo}
          activeLabel="Cam"
          inactiveLabel="Cam Off"
        />
        <button
          onClick={onDisconnect}
          style={disconnectBtnStyle}
          title="Desconectar"
        >
          X
        </button>
      </div>
    </div>
  );
}

function ControlButton({
  active,
  onClick,
  activeLabel,
  inactiveLabel,
}: {
  active: boolean;
  onClick: () => void;
  activeLabel: string;
  inactiveLabel: string;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        ...ctrlBtnBase,
        backgroundColor: active ? "rgba(34, 197, 94, 0.2)" : "rgba(239, 68, 68, 0.2)",
        border: `1px solid ${active ? "#22c55e" : "#ef4444"}`,
        color: active ? "#22c55e" : "#ef4444",
      }}
      title={active ? activeLabel : inactiveLabel}
    >
      {active ? activeLabel : inactiveLabel}
    </button>
  );
}

// ── Styles ──────────────────────────────────────────────────

const containerStyle: React.CSSProperties = {
  position: "absolute",
  bottom: 48,
  right: 12,
  zIndex: 9500,
  display: "flex",
  flexDirection: "column",
  gap: 8,
  alignItems: "flex-end",
  pointerEvents: "auto",
};

const gridStyle: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: 6,
  justifyContent: "flex-end",
  maxWidth: 300,
};

const localPreviewContainerStyle: React.CSSProperties = {
  alignSelf: "flex-end",
  border: "2px solid #334155",
  borderRadius: 8,
  overflow: "hidden",
};

const controlsStyle: React.CSSProperties = {
  display: "flex",
  gap: 6,
  padding: "4px 8px",
  backgroundColor: "rgba(15, 23, 42, 0.85)",
  borderRadius: 8,
};

const ctrlBtnBase: React.CSSProperties = {
  padding: "4px 10px",
  borderRadius: 4,
  fontSize: 11,
  fontWeight: 600,
  cursor: "pointer",
  fontFamily: "-apple-system, BlinkMacSystemFont, sans-serif",
};

const disconnectBtnStyle: React.CSSProperties = {
  ...ctrlBtnBase,
  backgroundColor: "rgba(239, 68, 68, 0.3)",
  border: "1px solid #ef4444",
  color: "#ef4444",
};
