/**
 * PhaserGame — React wrapper that instantiates Phaser.Game (client-only).
 *
 * CRITICAL: All Phaser imports happen INSIDE useEffect via dynamic import().
 * This prevents Next.js SSR from crashing on `window` / `document` / `canvas`.
 *
 * This component is loaded via next/dynamic with { ssr: false } in page.tsx.
 */
"use client";

import { useEffect, useRef } from "react";

export default function PhaserGame() {
  const gameRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (gameRef.current) return; // prevent double-init in StrictMode

    let destroyed = false;

    async function initPhaser() {
      const Phaser = await import("phaser");
      const { default: BootScene } = await import("../scenes/BootScene");
      const { default: GameScene } = await import("../scenes/GameScene");

      if (destroyed) return;

      const game = new Phaser.Game({
        type: Phaser.AUTO,
        parent: containerRef.current || "game-container",
        width: 800,
        height: 600,
        backgroundColor: "#1e293b",
        physics: {
          default: "arcade",
          arcade: {
            gravity: { x: 0, y: 0 },
            debug: false,
          },
        },
        scene: [BootScene, GameScene],
        scale: {
          mode: Phaser.Scale.RESIZE,
          autoCenter: Phaser.Scale.CENTER_BOTH,
        },
        // Prevent Phaser from capturing all keyboard input globally
        input: {
          keyboard: {
            capture: [],
          },
        },
        // A3 fix: Auto-focus canvas on boot (important for iframe)
        autoFocus: true,
        // Render settings
        render: {
          antialias: false,
          pixelArt: true,
          roundPixels: true,
        },
      });

      // A3 fix: Don't pause rendering when iframe loses focus
      game.events.on("blur", () => {
        game.loop.wake();
      });

      gameRef.current = game;
    }

    initPhaser();

    return () => {
      destroyed = true;
      if (gameRef.current) {
        gameRef.current.destroy(true);
        gameRef.current = null;
      }
    };
  }, []);

  return (
    <div
      ref={containerRef}
      id="game-container"
      style={{
        width: "100%",
        height: "100%",
        outline: "none",
      }}
      tabIndex={-1}
    />
  );
}
