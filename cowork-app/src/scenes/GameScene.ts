/**
 * GameScene — Main virtual office scene.
 *
 * Renders the SkyOffice tilemap, manages local player movement (WASD/arrows),
 * handles multiplayer via the PhaserSocketBridge, and displays name labels.
 *
 * Coordinate system:
 *   - Phaser works in pixels (map is 40×30 tiles × 32px = 1280×960px)
 *   - Server works in tile coords (0-39, 0-29)
 *   - Conversion: tileX = Math.floor(pixelX / 32), pixelX = tileX * 32 + 16
 */
import Phaser from "phaser";
import { bridge } from "../lib/phaser-socket-bridge";

const TILE_SIZE = 32;
const MAP_WIDTH_TILES = 40;
const MAP_HEIGHT_TILES = 30;
const PLAYER_SPEED = 200; // pixels per second
const EMIT_THROTTLE_MS = 100;

// Available character sprites — assigned based on player index
const AVATARS = ["adam", "ash", "lucy", "nancy"];

interface OtherPlayerData {
  sprite: Phaser.Physics.Arcade.Sprite;
  nameLabel: Phaser.GameObjects.Text;
  targetX: number;
  targetY: number;
}

// Raw key state tracker — bypasses Phaser's KeyboardPlugin which has
// known issues inside iframes (focus/capture doesn't bind to DOM properly).
const keysDown = new Set<string>();

if (typeof window !== "undefined") {
  window.addEventListener("keydown", (e) => {
    keysDown.add(e.code);
  });
  window.addEventListener("keyup", (e) => {
    keysDown.delete(e.code);
  });
  // Clear all keys when window loses focus (prevents stuck keys)
  window.addEventListener("blur", () => {
    keysDown.clear();
  });
}

export default class GameScene extends Phaser.Scene {
  private myPlayer!: Phaser.Physics.Arcade.Sprite;
  private myNameLabel!: Phaser.GameObjects.Text;
  private otherPlayers = new Map<string, OtherPlayerData>();
  private mySocketId: string | null = null;
  private currentDirection = "down";
  private myAvatar = "adam";

  // Movement emission throttle
  private lastEmitTime = 0;
  private lastEmittedTileX = -1;
  private lastEmittedTileY = -1;

  // Proximity glow
  private nearbyIds = new Set<string>();

  // Ground layer for collision
  private groundLayer!: Phaser.Tilemaps.TilemapLayer;

  // Bound handlers for proper cleanup (bind() creates new refs — must store them)
  private boundHandlers!: Record<string, (...args: any[]) => void>;

  constructor() {
    super("GameScene");
  }

  create(): void {
    // ── Create character animations ─────────────────────────
    this.createAnimations();

    // ── Build tilemap ───────────────────────────────────────
    const map = this.make.tilemap({ key: "tilemap" });
    const floorTileset = map.addTilesetImage("FloorAndGround", "tiles_wall")!;

    // Ground layer (tile-based, has collision)
    this.groundLayer = map.createLayer("Ground", floorTileset)!;
    this.groundLayer.setCollisionByProperty({ collides: true });

    // Object layers (sprite-based, from Tiled object groups)
    this.addObjectGroup(map, "Wall", "tiles_wall", "FloorAndGround", false);
    this.addObjectGroup(map, "Objects", "office", "Modern_Office_Black_Shadow", false);
    this.addObjectGroup(map, "ObjectsOnCollide", "office", "Modern_Office_Black_Shadow", true);
    this.addObjectGroup(map, "GenericObjects", "generic", "Generic", false);
    this.addObjectGroup(map, "GenericObjectsOnCollide", "generic", "Generic", true);
    this.addObjectGroup(map, "Basement", "basement", "Basement", true);

    // Interactive object groups (chairs, computers, whiteboards, vending machines)
    this.addItemGroup(map, "Chair", "chairs", "chair");
    this.addItemGroup(map, "Computer", "computers", "computer");
    this.addItemGroup(map, "Whiteboard", "whiteboards", "whiteboard");
    this.addItemGroup(map, "VendingMachine", "vendingmachines", "vendingmachine");

    // ── Create local player ─────────────────────────────────
    // Spawn in the main corridor area (tile 16, 13 — known open area)
    // Server will reposition via room-state, but this must be collision-free
    const spawnX = 16 * TILE_SIZE + TILE_SIZE / 2; // 528
    const spawnY = 13 * TILE_SIZE + TILE_SIZE / 2; // 432
    this.myPlayer = this.physics.add.sprite(spawnX, spawnY, this.myAvatar);
    this.myPlayer.setDepth(spawnY);
    this.myPlayer.setSize(16, 16); // smaller collision box
    this.myPlayer.setOffset(8, 28); // offset to feet

    // Collision with ground — delayed to prevent spawn-inside-wall trap
    const body = this.myPlayer.body as Phaser.Physics.Arcade.Body;
    body.checkCollision.none = true;
    this.time.delayedCall(500, () => {
      if (this.myPlayer?.body) {
        (this.myPlayer.body as Phaser.Physics.Arcade.Body).checkCollision.none = false;
      }
    });
    this.physics.add.collider(this.myPlayer, this.groundLayer);

    // Name label
    this.myNameLabel = this.add.text(spawnX, spawnY - 30, "", {
      fontSize: "11px",
      color: "#ffffff",
      backgroundColor: "#1e293bcc",
      padding: { x: 4, y: 2 },
      fontFamily: "-apple-system, BlinkMacSystemFont, sans-serif",
    });
    this.myNameLabel.setOrigin(0.5);
    this.myNameLabel.setDepth(9999);

    // Camera
    this.cameras.main.zoom = 1.5;
    this.cameras.main.startFollow(this.myPlayer, true);
    this.cameras.main.setBounds(0, 0, map.widthInPixels, map.heightInPixels);

    // ── Keyboard input ──────────────────────────────────────
    // We use raw DOM key tracking (keysDown set above) instead of Phaser's
    // KeyboardPlugin because it doesn't work reliably inside iframes.
    // Focus the canvas so the iframe's window receives key events.
    this.game.canvas.setAttribute("tabindex", "1");
    this.game.canvas.style.outline = "none";
    this.input.on("pointerdown", () => {
      window.focus();
      this.game.canvas.focus();
    });
    if (typeof window !== "undefined") {
      window.focus();
      setTimeout(() => this.game.canvas.focus(), 200);
    }

    // ── Bridge event listeners (multiplayer) ────────────────
    // Store bound refs so shutdown() can remove the exact same functions
    this.boundHandlers = {
      roomState: this.handleRoomState.bind(this),
      playerJoined: this.handlePlayerJoined.bind(this),
      playerMoved: this.handlePlayerMoved.bind(this),
      playerLeft: this.handlePlayerLeft.bind(this),
      proximityUpdate: this.handleProximityUpdate.bind(this),
    };
    bridge.on("room-state", this.boundHandlers.roomState);
    bridge.on("player-joined", this.boundHandlers.playerJoined);
    bridge.on("player-moved", this.boundHandlers.playerMoved);
    bridge.on("player-left", this.boundHandlers.playerLeft);
    bridge.on("proximity-update", this.boundHandlers.proximityUpdate);

    // Register shutdown handler so Phaser calls it when scene stops
    this.events.on("shutdown", this.shutdown, this);

    // Replay room-state — it fires BEFORE GameScene exists (race condition fix)
    bridge.replayRoomState();
  }

  update(time: number): void {
    if (!this.myPlayer?.body || !this.myPlayer.active) return;

    // ── Process input (raw DOM keys — works in iframes) ────
    const body = this.myPlayer.body as Phaser.Physics.Arcade.Body;
    body.setVelocity(0);

    let moving = false;
    let dir = this.currentDirection;

    const left = keysDown.has("ArrowLeft") || keysDown.has("KeyA");
    const right = keysDown.has("ArrowRight") || keysDown.has("KeyD");
    const up = keysDown.has("ArrowUp") || keysDown.has("KeyW");
    const down = keysDown.has("ArrowDown") || keysDown.has("KeyS");

    if (left) {
      body.setVelocityX(-PLAYER_SPEED);
      dir = "left";
      moving = true;
    } else if (right) {
      body.setVelocityX(PLAYER_SPEED);
      dir = "right";
      moving = true;
    }

    if (up) {
      body.setVelocityY(-PLAYER_SPEED);
      dir = "up";
      moving = true;
    } else if (down) {
      body.setVelocityY(PLAYER_SPEED);
      dir = "down";
      moving = true;
    }

    // Normalize diagonal movement
    if (body.velocity.x !== 0 && body.velocity.y !== 0) {
      body.velocity.normalize().scale(PLAYER_SPEED);
    }

    this.currentDirection = dir;

    // ── Animation ───────────────────────────────────────────
    if (moving) {
      this.myPlayer.anims.play(`${this.myAvatar}_run_${dir}`, true);
    } else {
      this.myPlayer.anims.play(`${this.myAvatar}_idle_${dir}`, true);
    }

    // Depth sort (Y-based)
    this.myPlayer.setDepth(this.myPlayer.y);

    // ── Update name label position ──────────────────────────
    this.myNameLabel.setPosition(this.myPlayer.x, this.myPlayer.y - 30);

    // ── Emit movement to server (throttled) ─────────────────
    const tileX = Math.floor(this.myPlayer.x / TILE_SIZE);
    const tileY = Math.floor(this.myPlayer.y / TILE_SIZE);

    if (
      (tileX !== this.lastEmittedTileX || tileY !== this.lastEmittedTileY) &&
      time - this.lastEmitTime > EMIT_THROTTLE_MS
    ) {
      bridge.emitMove(tileX, tileY, this.currentDirection);
      this.lastEmittedTileX = tileX;
      this.lastEmittedTileY = tileY;
      this.lastEmitTime = time;
    }

    // ── Update other player positions (interpolation) ───────
    for (const [, data] of this.otherPlayers) {
      // Smoothly interpolate toward target position
      const dx = data.targetX - data.sprite.x;
      const dy = data.targetY - data.sprite.y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (dist > 2) {
        data.sprite.x += dx * 0.15;
        data.sprite.y += dy * 0.15;
      } else {
        data.sprite.x = data.targetX;
        data.sprite.y = data.targetY;
        // A1 fix: Stop walk animation when arrived — prevents "running in place"
        const currentAnim = data.sprite.anims.currentAnim?.key || "";
        if (currentAnim.includes("_run_")) {
          const avatarKey = data.sprite.texture.key;
          const dir = currentAnim.split("_run_")[1];
          data.sprite.anims.play(`${avatarKey}_idle_${dir}`, true);
        }
      }

      // Update name label
      data.nameLabel.setPosition(data.sprite.x, data.sprite.y - 30);
      data.sprite.setDepth(data.sprite.y);
      data.nameLabel.setDepth(9999);
    }
  }

  // ── Bridge event handlers ───────────────────────────────────

  private handleRoomState(data: {
    players: Array<{
      id: string;
      displayName: string;
      x: number;
      y: number;
      direction: string;
      avatarUrl?: string;
    }>;
    roomId: string;
  }): void {
    this.mySocketId = bridge.getSocketId();

    for (const player of data.players) {
      if (player.id === this.mySocketId) {
        // Position my player at server-assigned spawn
        const px = player.x * TILE_SIZE + TILE_SIZE / 2;
        const py = player.y * TILE_SIZE + TILE_SIZE / 2;
        this.myPlayer.setPosition(px, py);
        this.myNameLabel.setText(player.displayName || "");
        this.lastEmittedTileX = player.x;
        this.lastEmittedTileY = player.y;
      } else {
        this.addOtherPlayer(player);
      }
    }
  }

  private handlePlayerJoined(player: {
    id: string;
    displayName: string;
    x: number;
    y: number;
    direction: string;
  }): void {
    if (player.id === this.mySocketId) return;
    this.addOtherPlayer(player);
  }

  private handlePlayerMoved(data: {
    id: string;
    x: number;
    y: number;
    direction: string;
  }): void {
    const other = this.otherPlayers.get(data.id);
    if (!other) return;

    const targetX = data.x * TILE_SIZE + TILE_SIZE / 2;
    const targetY = data.y * TILE_SIZE + TILE_SIZE / 2;
    other.targetX = targetX;
    other.targetY = targetY;

    // Play walk animation in the correct direction
    const avatarKey = other.sprite.texture.key;
    other.sprite.anims.play(`${avatarKey}_run_${data.direction}`, true);
  }

  private handlePlayerLeft(data: { id: string }): void {
    const other = this.otherPlayers.get(data.id);
    if (!other) return;

    other.sprite.destroy();
    other.nameLabel.destroy();
    this.otherPlayers.delete(data.id);
    this.nearbyIds.delete(data.id);
  }

  private handleProximityUpdate(data: { nearbyIds: string[] }): void {
    const newNearby = new Set(data.nearbyIds);

    // Remove glow from players no longer nearby
    for (const id of this.nearbyIds) {
      if (!newNearby.has(id)) {
        const other = this.otherPlayers.get(id);
        if (other) other.sprite.clearTint();
      }
    }

    // Add glow to newly nearby players
    for (const id of newNearby) {
      const other = this.otherPlayers.get(id);
      if (other) other.sprite.setTint(0x44ff88);
    }

    this.nearbyIds = newNearby;
  }

  // ── Helper methods ──────────────────────────────────────────

  private addOtherPlayer(player: {
    id: string;
    displayName: string;
    x: number;
    y: number;
    direction: string;
  }): void {
    if (this.otherPlayers.has(player.id)) return;

    // Pick avatar based on number of existing players
    const avatarIndex = this.otherPlayers.size % AVATARS.length;
    const avatar = AVATARS[avatarIndex];

    const px = player.x * TILE_SIZE + TILE_SIZE / 2;
    const py = player.y * TILE_SIZE + TILE_SIZE / 2;

    const sprite = this.physics.add.sprite(px, py, avatar);
    sprite.setDepth(py);
    sprite.anims.play(`${avatar}_idle_${player.direction || "down"}`, true);

    const nameLabel = this.add.text(px, py - 30, player.displayName || "?", {
      fontSize: "11px",
      color: "#ffffff",
      backgroundColor: "#374151cc",
      padding: { x: 4, y: 2 },
      fontFamily: "-apple-system, BlinkMacSystemFont, sans-serif",
    });
    nameLabel.setOrigin(0.5);
    nameLabel.setDepth(9999);

    this.otherPlayers.set(player.id, {
      sprite,
      nameLabel,
      targetX: px,
      targetY: py,
    });
  }

  private addObjectGroup(
    map: Phaser.Tilemaps.Tilemap,
    layerName: string,
    spriteKey: string,
    tilesetName: string,
    collidable: boolean
  ): void {
    const objectLayer = map.getObjectLayer(layerName);
    if (!objectLayer) return;

    const group = this.physics.add.staticGroup();
    const tileset = map.getTileset(tilesetName);
    if (!tileset) return;

    objectLayer.objects.forEach((obj) => {
      const actualX = obj.x! + obj.width! * 0.5;
      const actualY = obj.y! - obj.height! * 0.5;
      group
        .get(actualX, actualY, spriteKey, obj.gid! - tileset.firstgid)
        .setDepth(actualY);
    });

    if (collidable) {
      this.physics.add.collider(this.myPlayer, group);
    }
  }

  private addItemGroup(
    map: Phaser.Tilemaps.Tilemap,
    layerName: string,
    spriteKey: string,
    tilesetName: string
  ): void {
    const objectLayer = map.getObjectLayer(layerName);
    if (!objectLayer) return;

    const group = this.physics.add.staticGroup();
    const tileset = map.getTileset(tilesetName);
    if (!tileset) return;

    objectLayer.objects.forEach((obj) => {
      const actualX = obj.x! + obj.width! * 0.5;
      const actualY = obj.y! - obj.height! * 0.5;
      group
        .get(actualX, actualY, spriteKey, obj.gid! - tileset.firstgid)
        .setDepth(actualY);
    });
  }

  private createAnimations(): void {
    const frameRate = 15;
    const idleRate = frameRate * 0.6;

    for (const char of AVATARS) {
      // Idle animations: 0-5 right, 6-11 up, 12-17 left, 18-23 down
      const idleDirs = [
        { dir: "right", start: 0, end: 5 },
        { dir: "up", start: 6, end: 11 },
        { dir: "left", start: 12, end: 17 },
        { dir: "down", start: 18, end: 23 },
      ];
      for (const { dir, start, end } of idleDirs) {
        this.anims.create({
          key: `${char}_idle_${dir}`,
          frames: this.anims.generateFrameNumbers(char, { start, end }),
          repeat: -1,
          frameRate: idleRate,
        });
      }

      // Run animations: 24-29 right, 30-35 up, 36-41 left, 42-47 down
      const runDirs = [
        { dir: "right", start: 24, end: 29 },
        { dir: "up", start: 30, end: 35 },
        { dir: "left", start: 36, end: 41 },
        { dir: "down", start: 42, end: 47 },
      ];
      for (const { dir, start, end } of runDirs) {
        this.anims.create({
          key: `${char}_run_${dir}`,
          frames: this.anims.generateFrameNumbers(char, { start, end }),
          repeat: -1,
          frameRate,
        });
      }

      // Sit animations: 48 down, 49 left, 50 right, 51 up
      const sitDirs = [
        { dir: "down", frame: 48 },
        { dir: "left", frame: 49 },
        { dir: "right", frame: 50 },
        { dir: "up", frame: 51 },
      ];
      for (const { dir, frame } of sitDirs) {
        this.anims.create({
          key: `${char}_sit_${dir}`,
          frames: this.anims.generateFrameNumbers(char, { start: frame, end: frame }),
          repeat: 0,
          frameRate,
        });
      }
    }
  }

  /** Called when the scene is shut down (registered via this.events.on("shutdown")) */
  shutdown(): void {
    // A4 fix: Use stored bound refs — same references that were registered
    if (this.boundHandlers) {
      bridge.off("room-state", this.boundHandlers.roomState);
      bridge.off("player-joined", this.boundHandlers.playerJoined);
      bridge.off("player-moved", this.boundHandlers.playerMoved);
      bridge.off("player-left", this.boundHandlers.playerLeft);
      bridge.off("proximity-update", this.boundHandlers.proximityUpdate);
    }

    for (const [, data] of this.otherPlayers) {
      data.sprite.destroy();
      data.nameLabel.destroy();
    }
    this.otherPlayers.clear();
  }
}
