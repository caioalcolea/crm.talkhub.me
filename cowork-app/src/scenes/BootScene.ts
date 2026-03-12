/**
 * BootScene — Preloads all assets before the game starts.
 *
 * CRITICAL: setBaseURL('/cowork-app') must be called first.
 * Without it, Phaser requests /assets/... which falls through to SvelteKit → 404.
 * With basePath, requests go to /cowork-app/assets/... → Traefik → Next.js → 200.
 */
import Phaser from "phaser";

export default class BootScene extends Phaser.Scene {
  constructor() {
    super("BootScene");
  }

  preload(): void {
    // ── CRITICAL: Base URL for Traefik routing ──────────────
    this.load.setBaseURL("/cowork-app");

    // ── Progress bar ────────────────────────────────────────
    const width = this.cameras.main.width;
    const height = this.cameras.main.height;

    const barBg = this.add.rectangle(width / 2, height / 2, 320, 20, 0xe5e7eb);
    const barFill = this.add.rectangle(width / 2 - 150, height / 2, 0, 16, 0x3b82f6);
    barFill.setOrigin(0, 0.5);

    const loadingText = this.add.text(width / 2, height / 2 - 30, "Carregando...", {
      fontSize: "14px",
      color: "#6b7280",
      fontFamily: "-apple-system, BlinkMacSystemFont, sans-serif",
    });
    loadingText.setOrigin(0.5);

    this.load.on("progress", (value: number) => {
      barFill.width = 300 * value;
    });

    // ── Tilemap ─────────────────────────────────────────────
    this.load.tilemapTiledJSON("tilemap", "/assets/map/map.json");

    // ── Tilesets (spritesheets for object layers) ───────────
    this.load.spritesheet("tiles_wall", "/assets/map/FloorAndGround.png", {
      frameWidth: 32,
      frameHeight: 32,
    });
    this.load.spritesheet("chairs", "/assets/items/chair.png", {
      frameWidth: 32,
      frameHeight: 64,
    });
    this.load.spritesheet("computers", "/assets/items/computer.png", {
      frameWidth: 96,
      frameHeight: 64,
    });
    this.load.spritesheet("whiteboards", "/assets/items/whiteboard.png", {
      frameWidth: 64,
      frameHeight: 64,
    });
    this.load.spritesheet("vendingmachines", "/assets/items/vendingmachine.png", {
      frameWidth: 48,
      frameHeight: 72,
    });
    this.load.spritesheet("office", "/assets/tileset/Modern_Office_Black_Shadow.png", {
      frameWidth: 32,
      frameHeight: 32,
    });
    this.load.spritesheet("basement", "/assets/tileset/Basement.png", {
      frameWidth: 32,
      frameHeight: 32,
    });
    this.load.spritesheet("generic", "/assets/tileset/Generic.png", {
      frameWidth: 32,
      frameHeight: 32,
    });

    // ── Character spritesheets (32×48 per frame) ────────────
    const characters = ["adam", "ash", "lucy", "nancy"];
    for (const char of characters) {
      this.load.spritesheet(char, `/assets/character/${char}.png`, {
        frameWidth: 32,
        frameHeight: 48,
      });
    }

    // ── Transition on complete ──────────────────────────────
    this.load.on("complete", () => {
      this.scene.start("GameScene");
    });
  }
}
