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

  // Collision is disabled at spawn, enabled after first player movement
  // This prevents the "trapped in wall" bug when spawning inside colliders
  private collisionEnabled = false;
  private colliderRefs: Phaser.Physics.Arcade.Collider[] = [];
  private stuckFrames = 0;

  // Movement emission throttle
  private lastEmitTime = 0;
  private lastEmittedTileX = -1;
  private lastEmittedTileY = -1;

  // Proximity glow
  private nearbyIds = new Set<string>();

  // Chat bubbles above player heads
  private chatBubbles = new Map<string, Phaser.GameObjects.Text>();

  // Sit-on-chair system
  private playerState: "walking" | "sitting" = "walking";
  private chairGroup!: Phaser.Physics.Arcade.StaticGroup;
  private nearbyChair: Phaser.GameObjects.Sprite | null = null;
  private sitHintText!: Phaser.GameObjects.Text;
  private eKeyWasDown = false; // edge detection for E key
  private rKeyWasDown = false; // edge detection for R key

  // Whiteboard interaction
  private whiteboardGroup!: Phaser.Physics.Arcade.StaticGroup;
  private nearbyWhiteboard: Phaser.GameObjects.Sprite | null = null;
  private whiteboardHintText!: Phaser.GameObjects.Text;

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

    // Fix black lines between tiles: snap pixels on the camera
    this.cameras.main.setRoundPixels(true);

    // Object layers (sprite-based, from Tiled object groups)
    this.addObjectGroup(map, "Wall", "tiles_wall", "FloorAndGround", false);
    this.addObjectGroup(map, "Objects", "office", "Modern_Office_Black_Shadow", false);
    this.addObjectGroup(map, "ObjectsOnCollide", "office", "Modern_Office_Black_Shadow", true);
    this.addObjectGroup(map, "GenericObjects", "generic", "Generic", false);
    this.addObjectGroup(map, "GenericObjectsOnCollide", "generic", "Generic", true);
    this.addObjectGroup(map, "Basement", "basement", "Basement", true);

    // Interactive object groups (chairs, computers, whiteboards, vending machines)
    this.chairGroup = this.addItemGroup(map, "Chair", "chairs", "chair");
    this.addItemGroup(map, "Computer", "computers", "computer");
    this.whiteboardGroup = this.addItemGroup(map, "Whiteboard", "whiteboards", "whiteboard");
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

    // Collision: register colliders but start INACTIVE.
    // They activate on first player movement to prevent spawn-inside-wall trap.
    const groundCollider = this.physics.add.collider(this.myPlayer, this.groundLayer);
    groundCollider.active = false;
    this.colliderRefs.push(groundCollider);

    // Chair overlap detection — triggers sit hint
    if (this.chairGroup.getLength() > 0) {
      this.physics.add.overlap(this.myPlayer, this.chairGroup, (_player, chair) => {
        this.nearbyChair = chair as Phaser.GameObjects.Sprite;
      });
    }

    // Sit hint text (hidden by default)
    this.sitHintText = this.add.text(0, 0, "Pressione E para sentar", {
      fontSize: "9px",
      color: "#e2e8f0",
      backgroundColor: "#334155cc",
      padding: { x: 4, y: 2 },
      fontFamily: "-apple-system, BlinkMacSystemFont, sans-serif",
    });
    this.sitHintText.setOrigin(0.5);
    this.sitHintText.setDepth(10001);
    this.sitHintText.setVisible(false);

    // Whiteboard overlap detection — triggers whiteboard hint
    if (this.whiteboardGroup.getLength() > 0) {
      this.physics.add.overlap(this.myPlayer, this.whiteboardGroup, (_player, wb) => {
        this.nearbyWhiteboard = wb as Phaser.GameObjects.Sprite;
      });
    }

    // Whiteboard hint text (hidden by default)
    this.whiteboardHintText = this.add.text(0, 0, "Pressione R para whiteboard", {
      fontSize: "9px",
      color: "#e2e8f0",
      backgroundColor: "#334155cc",
      padding: { x: 4, y: 2 },
      fontFamily: "-apple-system, BlinkMacSystemFont, sans-serif",
    });
    this.whiteboardHintText.setOrigin(0.5);
    this.whiteboardHintText.setDepth(10001);
    this.whiteboardHintText.setVisible(false);

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

    // Camera — use integer zoom (2x) to prevent sub-pixel tile seams (black lines)
    this.cameras.main.zoom = 2;
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
      chatMessage: this.handleChatMessage.bind(this),
      playerSit: this.handlePlayerSit.bind(this),
    };
    bridge.on("room-state", this.boundHandlers.roomState);
    bridge.on("player-joined", this.boundHandlers.playerJoined);
    bridge.on("player-moved", this.boundHandlers.playerMoved);
    bridge.on("player-left", this.boundHandlers.playerLeft);
    bridge.on("proximity-update", this.boundHandlers.proximityUpdate);
    bridge.on("chat-message", this.boundHandlers.chatMessage);
    bridge.on("player-sit", this.boundHandlers.playerSit);

    // Register shutdown handler so Phaser calls it when scene stops
    this.events.on("shutdown", this.shutdown, this);

    // Replay room-state — it fires BEFORE GameScene exists (race condition fix)
    bridge.replayRoomState();
  }

  update(time: number): void {
    if (!this.myPlayer?.body || !this.myPlayer.active) return;

    // ── Sit/Stand toggle (E key — edge-triggered) ──────────
    const eDown = keysDown.has("KeyE");
    if (eDown && !this.eKeyWasDown) {
      if (this.playerState === "sitting") {
        this.standUp();
      } else if (this.nearbyChair) {
        this.sitDown();
      }
    }
    this.eKeyWasDown = eDown;

    // ── Whiteboard toggle (R key — edge-triggered) ───────────
    const rDown = keysDown.has("KeyR");
    if (rDown && !this.rKeyWasDown) {
      if (this.nearbyWhiteboard && this.playerState === "walking") {
        const wbId = `wb_${Math.floor(this.nearbyWhiteboard.x)}_${Math.floor(this.nearbyWhiteboard.y)}`;
        bridge.emit("whiteboard-open-request", { whiteboardId: wbId });
      }
    }
    this.rKeyWasDown = rDown;

    // ── Process input (raw DOM keys — works in iframes) ────
    const body = this.myPlayer.body as Phaser.Physics.Arcade.Body;
    body.setVelocity(0);

    let moving = false;
    let dir = this.currentDirection;

    // Block movement while sitting
    if (this.playerState !== "sitting") {
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
    }

    // Normalize diagonal movement
    if (body.velocity.x !== 0 && body.velocity.y !== 0) {
      body.velocity.normalize().scale(PLAYER_SPEED);
    }

    this.currentDirection = dir;

    // ── Enable collision after first movement ────────────────
    // Player must move first to escape any spawn-inside-wall position.
    // Set flag immediately to prevent creating multiple delayed calls.
    // Short 50ms delay (~3 frames) gives player time to separate from spawn.
    if (moving && !this.collisionEnabled) {
      this.collisionEnabled = true;
      this.time.delayedCall(50, () => {
        for (const col of this.colliderRefs) {
          col.active = true;
        }
      });
    }

    // ── Stuck-in-wall detector ──────────────────────────────
    // If collision is active and player is pressing movement keys but
    // velocity is zero (blocked by collider), count frames. After 10
    // consecutive stuck frames (~167ms), teleport to safe spawn position.
    if (this.collisionEnabled) {
      const postVx = body.velocity.x;
      const postVy = body.velocity.y;
      if (moving && postVx === 0 && postVy === 0) {
        this.stuckFrames++;
        if (this.stuckFrames > 10) {
          this.myPlayer.setPosition(
            16 * TILE_SIZE + TILE_SIZE / 2,
            13 * TILE_SIZE + TILE_SIZE / 2
          );
          this.stuckFrames = 0;
        }
      } else {
        this.stuckFrames = 0;
      }
    }

    // ── Animation ───────────────────────────────────────────
    if (this.playerState === "sitting") {
      this.myPlayer.anims.play(`${this.myAvatar}_sit_${dir}`, true);
    } else if (moving) {
      this.myPlayer.anims.play(`${this.myAvatar}_run_${dir}`, true);
    } else {
      this.myPlayer.anims.play(`${this.myAvatar}_idle_${dir}`, true);
    }

    // Depth sort (Y-based)
    this.myPlayer.setDepth(this.myPlayer.y);

    // ── Update name label + chat bubble position ───────────
    this.myNameLabel.setPosition(this.myPlayer.x, this.myPlayer.y - 30);
    const myBubble = this.chatBubbles.get(this.mySocketId || "");
    if (myBubble) myBubble.setPosition(this.myPlayer.x, this.myPlayer.y - 48);

    // ── Chair sit hint ───────────────────────────────────────
    if (this.nearbyChair && this.playerState === "walking") {
      this.sitHintText.setPosition(this.nearbyChair.x, this.nearbyChair.y - 20);
      this.sitHintText.setVisible(true);
    } else if (this.playerState === "sitting") {
      this.sitHintText.setText("Pressione E para levantar");
      this.sitHintText.setPosition(this.myPlayer.x, this.myPlayer.y - 48);
      this.sitHintText.setVisible(true);
    } else {
      this.sitHintText.setVisible(false);
    }
    // Reset nearbyChair — overlap callback will re-set it next frame if still overlapping
    if (this.playerState !== "sitting") {
      this.nearbyChair = null;
    }

    // ── Whiteboard hint ────────────────────────────────────────
    if (this.nearbyWhiteboard && this.playerState === "walking") {
      this.whiteboardHintText.setPosition(this.nearbyWhiteboard.x, this.nearbyWhiteboard.y - 40);
      this.whiteboardHintText.setVisible(true);
    } else {
      this.whiteboardHintText.setVisible(false);
    }
    // Reset nearbyWhiteboard — overlap callback will re-set it next frame
    if (this.playerState !== "sitting") {
      this.nearbyWhiteboard = null;
    }

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
    for (const [id, data] of this.otherPlayers) {
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
          const animDir = currentAnim.split("_run_")[1];
          data.sprite.anims.play(`${avatarKey}_idle_${animDir}`, true);
        }
      }

      // Update name label + chat bubble
      data.nameLabel.setPosition(data.sprite.x, data.sprite.y - 30);
      data.sprite.setDepth(data.sprite.y);
      data.nameLabel.setDepth(9999);
      const otherBubble = this.chatBubbles.get(id);
      if (otherBubble) otherBubble.setPosition(data.sprite.x, data.sprite.y - 48);
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
    this.chatBubbles.get(data.id)?.destroy();
    this.chatBubbles.delete(data.id);
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

  private sitDown(): void {
    if (!this.nearbyChair || this.playerState === "sitting") return;
    this.playerState = "sitting";
    // Snap player to chair center
    this.myPlayer.setPosition(this.nearbyChair.x, this.nearbyChair.y);
    this.myPlayer.anims.play(`${this.myAvatar}_sit_${this.currentDirection}`, true);
    // Notify server
    bridge.emitMove(
      Math.floor(this.nearbyChair.x / TILE_SIZE),
      Math.floor(this.nearbyChair.y / TILE_SIZE),
      this.currentDirection
    );
    bridge.emitSit(true);
  }

  private standUp(): void {
    if (this.playerState !== "sitting") return;
    this.playerState = "walking";
    this.nearbyChair = null;
    this.myPlayer.anims.play(`${this.myAvatar}_idle_${this.currentDirection}`, true);
    bridge.emitSit(false);
  }

  private handleChatMessage(data: {
    id: string;
    displayName: string;
    message: string;
  }): void {
    // Determine which sprite to place the bubble above
    let x: number;
    let y: number;

    if (data.id === this.mySocketId) {
      x = this.myPlayer.x;
      y = this.myPlayer.y - 48;
    } else {
      const other = this.otherPlayers.get(data.id);
      if (!other) return;
      x = other.sprite.x;
      y = other.sprite.y - 48;
    }

    // Destroy previous bubble for this player
    this.chatBubbles.get(data.id)?.destroy();

    // Create chat bubble
    const bubble = this.add.text(x, y, data.message, {
      fontSize: "10px",
      color: "#1e293b",
      backgroundColor: "#ffffffee",
      padding: { x: 6, y: 3 },
      fontFamily: "-apple-system, BlinkMacSystemFont, sans-serif",
      wordWrap: { width: 150 },
    });
    bubble.setOrigin(0.5, 1);
    bubble.setDepth(10000);
    this.chatBubbles.set(data.id, bubble);

    // Auto-fade after 5 seconds
    this.time.delayedCall(5000, () => {
      if (this.chatBubbles.get(data.id) === bubble) {
        bubble.destroy();
        this.chatBubbles.delete(data.id);
      }
    });
  }

  private handlePlayerSit(data: {
    id: string;
    sitting: boolean;
    x: number;
    y: number;
    direction: string;
  }): void {
    const other = this.otherPlayers.get(data.id);
    if (!other) return;

    const avatarKey = other.sprite.texture.key;
    if (data.sitting) {
      const px = data.x * TILE_SIZE + TILE_SIZE / 2;
      const py = data.y * TILE_SIZE + TILE_SIZE / 2;
      other.sprite.setPosition(px, py);
      other.targetX = px;
      other.targetY = py;
      other.sprite.anims.play(`${avatarKey}_sit_${data.direction || "down"}`, true);
    } else {
      other.sprite.anims.play(`${avatarKey}_idle_${data.direction || "down"}`, true);
    }
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
      const col = this.physics.add.collider(this.myPlayer, group);
      col.active = false; // starts inactive, enabled on first movement
      this.colliderRefs.push(col);
    }
  }

  private addItemGroup(
    map: Phaser.Tilemaps.Tilemap,
    layerName: string,
    spriteKey: string,
    tilesetName: string
  ): Phaser.Physics.Arcade.StaticGroup {
    const group = this.physics.add.staticGroup();
    const objectLayer = map.getObjectLayer(layerName);
    if (!objectLayer) return group;

    const tileset = map.getTileset(tilesetName);
    if (!tileset) return group;

    objectLayer.objects.forEach((obj) => {
      const actualX = obj.x! + obj.width! * 0.5;
      const actualY = obj.y! - obj.height! * 0.5;
      group
        .get(actualX, actualY, spriteKey, obj.gid! - tileset.firstgid)
        .setDepth(actualY);
    });

    return group;
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
      bridge.off("chat-message", this.boundHandlers.chatMessage);
      bridge.off("player-sit", this.boundHandlers.playerSit);
    }

    for (const [, data] of this.otherPlayers) {
      data.sprite.destroy();
      data.nameLabel.destroy();
    }
    this.otherPlayers.clear();
    for (const [, bubble] of this.chatBubbles) bubble.destroy();
    this.chatBubbles.clear();
    this.colliderRefs = [];
  }
}
