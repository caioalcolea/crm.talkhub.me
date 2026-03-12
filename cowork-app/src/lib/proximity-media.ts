/**
 * ProximityMediaManager — WebRTC A/V connections triggered by proximity.
 *
 * When players are within PROXIMITY_RADIUS (3 tiles), the server sends
 * proximity-update { nearbyIds }. This manager creates/destroys peer
 * connections accordingly using native WebRTC (no PeerJS dependency).
 *
 * Signaling flows through the existing Socket.io connection via the bridge:
 *   Offer/Answer/ICE → bridge.emitWebRTCSignal() → server relay → peer
 *
 * Initiator rule: the peer with the lexicographically smaller socketId
 * creates the offer. This prevents simultaneous offer collisions.
 *
 * Key fixes (v2):
 *   - Shared promise for stream acquisition (no race conditions)
 *   - Tracks added to peer connection AFTER stream is ready
 *   - Support for pre-acquired stream (from user gesture on overlay click)
 *   - Comprehensive diagnostic logging
 */

type MediaEventType = "stream-added" | "stream-removed" | "local-stream" | "error";
type MediaListener = (data: any) => void;

const RTC_CONFIG: RTCConfiguration = {
  iceServers: [
    { urls: "stun:stun.l.google.com:19302" },
    { urls: "stun:stun1.l.google.com:19302" },
  ],
};

const DEBOUNCE_MS = 500;

export class ProximityMediaManager {
  private localStream: MediaStream | null = null;
  private peers = new Map<string, RTCPeerConnection>();
  private remoteStreams = new Map<string, MediaStream>();
  private mySocketId = "";
  private listeners = new Map<string, Set<MediaListener>>();
  private audioEnabled = true;
  private videoEnabled = true;
  private currentNearbyIds = new Set<string>();
  private sendSignalFn: ((targetId: string, signal: any) => void) | null = null;
  private debounceTimer: ReturnType<typeof setTimeout> | null = null;
  private pendingNearbyIds: string[] | null = null;
  private destroyed = false;

  // Shared promise — prevents race condition when multiple proximity updates
  // arrive while getUserMedia is still pending
  private streamPromise: Promise<MediaStream | null> | null = null;

  setMySocketId(id: string): void {
    this.mySocketId = id;
    console.log("[ProximityMedia] My socket ID:", id);
  }

  setSendSignal(fn: (targetId: string, signal: any) => void): void {
    this.sendSignalFn = fn;
  }

  /**
   * Accept a pre-acquired MediaStream (from user gesture on overlay click).
   * This avoids permission issues in iframes where getUserMedia requires
   * an immediate user interaction context.
   */
  setPreAcquiredStream(stream: MediaStream | null): void {
    if (stream && !this.localStream) {
      console.log("[ProximityMedia] Using pre-acquired stream with", stream.getTracks().length, "tracks");
      this.localStream = stream;
      this.emit("local-stream", { stream });
    }
  }

  // ── Local Stream ─────────────────────────────────────────

  async acquireLocalStream(): Promise<MediaStream | null> {
    if (this.localStream) return this.localStream;

    // Return existing promise if acquisition is in progress — this is the
    // key fix for the race condition. Previous code returned null here,
    // causing processNearbyUpdate to bail out and never create peer connections.
    if (this.streamPromise) {
      console.log("[ProximityMedia] Waiting for in-progress stream acquisition...");
      return this.streamPromise;
    }

    this.streamPromise = this._doAcquireStream();
    const stream = await this.streamPromise;
    this.streamPromise = null;
    return stream;
  }

  private async _doAcquireStream(): Promise<MediaStream | null> {
    console.log("[ProximityMedia] Requesting camera/mic permissions...");
    try {
      // Try video + audio first, fall back to audio-only
      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
          video: { width: { ideal: 320 }, height: { ideal: 240 }, frameRate: { max: 15 } },
        });
        console.log("[ProximityMedia] Got video+audio stream");
      } catch {
        try {
          stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
          console.log("[ProximityMedia] Got audio-only stream (video denied/unavailable)");
        } catch {
          console.error("[ProximityMedia] Camera and microphone access denied");
          this.emit("error", { message: "Camera and microphone access denied" });
          return null;
        }
      }

      if (this.destroyed) {
        stream.getTracks().forEach((t) => t.stop());
        return null;
      }

      this.localStream = stream;
      console.log("[ProximityMedia] Local stream ready with", stream.getTracks().length, "tracks:",
        stream.getTracks().map(t => `${t.kind}:${t.enabled ? "on" : "off"}`).join(", "));
      this.emit("local-stream", { stream });
      return stream;
    } catch (err) {
      console.error("[ProximityMedia] Unexpected error acquiring stream:", err);
      this.emit("error", { message: "Failed to acquire media stream" });
      return null;
    }
  }

  // ── Proximity Updates ────────────────────────────────────

  updateNearby(nearbyIds: string[]): void {
    if (this.destroyed) return;

    // Debounce — proximity-update fires on every move
    this.pendingNearbyIds = nearbyIds;
    if (this.debounceTimer) return;

    this.debounceTimer = setTimeout(() => {
      this.debounceTimer = null;
      if (this.pendingNearbyIds && !this.destroyed) {
        this.processNearbyUpdate(this.pendingNearbyIds);
      }
      this.pendingNearbyIds = null;
    }, DEBOUNCE_MS);
  }

  private async processNearbyUpdate(nearbyIds: string[]): Promise<void> {
    const newNearby = new Set(nearbyIds);

    // Remove peers no longer nearby
    for (const id of this.currentNearbyIds) {
      if (!newNearby.has(id)) {
        console.log("[ProximityMedia] Peer left proximity:", id);
        this.closePeer(id);
      }
    }

    // Add new peers
    const added: string[] = [];
    for (const id of newNearby) {
      if (!this.currentNearbyIds.has(id) && !this.peers.has(id)) {
        added.push(id);
      }
    }

    this.currentNearbyIds = newNearby;

    if (added.length === 0) return;

    console.log("[ProximityMedia] New peers in proximity:", added);

    // Acquire local stream lazily on first proximity contact
    const stream = await this.acquireLocalStream();
    if (!stream || this.destroyed) {
      console.warn("[ProximityMedia] Cannot establish connections — no local stream");
      return;
    }

    // Only the initiator (smaller socketId) creates the offer
    for (const peerId of added) {
      if (this.mySocketId < peerId) {
        console.log("[ProximityMedia] I am initiator for peer:", peerId);
        this.createPeerAndOffer(peerId);
      } else {
        console.log("[ProximityMedia] Waiting for offer from peer:", peerId);
      }
    }
  }

  // ── Peer Connection Management ───────────────────────────

  private createPeerConnection(peerId: string): RTCPeerConnection {
    const pc = new RTCPeerConnection(RTC_CONFIG);

    // NOTE: We do NOT add tracks here. Tracks are added explicitly by the
    // caller (createPeerAndOffer or handleSignal) AFTER ensuring the local
    // stream is ready. This fixes the bug where tracks were added before
    // getUserMedia completed, resulting in empty SDP offers.

    // ICE candidates → relay to peer
    pc.onicecandidate = (event) => {
      if (event.candidate && this.sendSignalFn) {
        this.sendSignalFn(peerId, { candidate: event.candidate.toJSON() });
      }
    };

    // Remote stream received
    pc.ontrack = (event) => {
      const [remoteStream] = event.streams;
      if (remoteStream) {
        console.log("[ProximityMedia] ontrack: received remote stream from", peerId,
          "tracks:", remoteStream.getTracks().map(t => t.kind).join(", "));
        // Always update — a peer might renegotiate with new tracks
        this.remoteStreams.set(peerId, remoteStream);
        this.emit("stream-added", { peerId, stream: remoteStream });
      }
    };

    // Connection state changes
    pc.onconnectionstatechange = () => {
      const state = pc.connectionState;
      console.log(`[ProximityMedia] Peer ${peerId} connection state: ${state}`);
      if (state === "disconnected" || state === "failed" || state === "closed") {
        this.closePeer(peerId);
      }
    };

    pc.oniceconnectionstatechange = () => {
      const state = pc.iceConnectionState;
      console.log(`[ProximityMedia] Peer ${peerId} ICE state: ${state}`);
      if (state === "failed") {
        pc.restartIce();
      }
    };

    this.peers.set(peerId, pc);
    return pc;
  }

  /**
   * Add local tracks to a peer connection.
   * Must be called AFTER localStream is acquired.
   */
  private addLocalTracks(pc: RTCPeerConnection): void {
    if (!this.localStream) return;

    // Check if tracks already added (renegotiation safety)
    const senders = pc.getSenders();
    if (senders.length > 0) return;

    for (const track of this.localStream.getTracks()) {
      pc.addTrack(track, this.localStream);
    }
    console.log("[ProximityMedia] Added", this.localStream.getTracks().length, "local tracks to peer connection");
  }

  private async createPeerAndOffer(peerId: string): Promise<void> {
    if (this.destroyed || this.peers.has(peerId)) return;

    // Ensure we have a local stream BEFORE creating the peer connection
    const stream = await this.acquireLocalStream();
    if (!stream || this.destroyed) return;

    const pc = this.createPeerConnection(peerId);

    // Add tracks AFTER stream is ready (fix: was adding before stream existed)
    this.addLocalTracks(pc);

    try {
      console.log("[ProximityMedia] Creating offer for peer:", peerId);
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      if (this.sendSignalFn && pc.localDescription) {
        this.sendSignalFn(peerId, {
          type: pc.localDescription.type,
          sdp: pc.localDescription.sdp,
        });
        console.log("[ProximityMedia] Offer sent to peer:", peerId);
      }
    } catch (err) {
      console.error("[ProximityMedia] Failed to create offer for", peerId, err);
      this.closePeer(peerId);
    }
  }

  // ── Signal Handling ──────────────────────────────────────

  async handleSignal(fromId: string, signal: any): Promise<void> {
    if (this.destroyed || !signal) return;

    // ICE candidate
    if (signal.candidate) {
      const pc = this.peers.get(fromId);
      if (pc && pc.remoteDescription) {
        try {
          await pc.addIceCandidate(new RTCIceCandidate(signal.candidate));
        } catch (err) {
          console.warn("[ProximityMedia] Failed to add ICE candidate:", err);
        }
      }
      return;
    }

    // SDP offer
    if (signal.type === "offer") {
      console.log("[ProximityMedia] Received offer from:", fromId);

      // Acquire local stream before answering (ensures tracks are ready)
      const stream = await this.acquireLocalStream();
      if (!stream || this.destroyed) {
        console.warn("[ProximityMedia] Cannot answer offer — no local stream");
        return;
      }

      // Close existing peer if any (renegotiation)
      if (this.peers.has(fromId)) {
        this.closePeer(fromId);
      }

      const pc = this.createPeerConnection(fromId);

      // Add tracks AFTER stream is ready (fix: was adding before stream existed)
      this.addLocalTracks(pc);

      try {
        await pc.setRemoteDescription(new RTCSessionDescription(signal));
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);

        if (this.sendSignalFn && pc.localDescription) {
          this.sendSignalFn(fromId, {
            type: pc.localDescription.type,
            sdp: pc.localDescription.sdp,
          });
          console.log("[ProximityMedia] Answer sent to peer:", fromId);
        }
      } catch (err) {
        console.error("[ProximityMedia] Failed to handle offer from", fromId, err);
        this.closePeer(fromId);
      }
      return;
    }

    // SDP answer
    if (signal.type === "answer") {
      console.log("[ProximityMedia] Received answer from:", fromId);
      const pc = this.peers.get(fromId);
      if (pc && pc.signalingState === "have-local-offer") {
        try {
          await pc.setRemoteDescription(new RTCSessionDescription(signal));
          console.log("[ProximityMedia] Remote description set for peer:", fromId);
        } catch (err) {
          console.error("[ProximityMedia] Failed to handle answer from", fromId, err);
        }
      }
      return;
    }
  }

  // ── Controls ─────────────────────────────────────────────

  toggleAudio(): boolean {
    this.audioEnabled = !this.audioEnabled;
    if (this.localStream) {
      for (const track of this.localStream.getAudioTracks()) {
        track.enabled = this.audioEnabled;
      }
    }
    return this.audioEnabled;
  }

  toggleVideo(): boolean {
    this.videoEnabled = !this.videoEnabled;
    if (this.localStream) {
      for (const track of this.localStream.getVideoTracks()) {
        track.enabled = this.videoEnabled;
      }
    }
    return this.videoEnabled;
  }

  // ── Cleanup ──────────────────────────────────────────────

  private closePeer(peerId: string): void {
    const pc = this.peers.get(peerId);
    if (pc) {
      pc.onicecandidate = null;
      pc.ontrack = null;
      pc.onconnectionstatechange = null;
      pc.oniceconnectionstatechange = null;
      pc.close();
      this.peers.delete(peerId);
      console.log("[ProximityMedia] Closed peer connection:", peerId);
    }

    if (this.remoteStreams.has(peerId)) {
      this.remoteStreams.delete(peerId);
      this.emit("stream-removed", { peerId });
    }
  }

  destroy(): void {
    this.destroyed = true;

    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = null;
    }

    // Close all peer connections
    for (const peerId of [...this.peers.keys()]) {
      this.closePeer(peerId);
    }

    // Stop local stream tracks
    if (this.localStream) {
      this.localStream.getTracks().forEach((t) => t.stop());
      this.localStream = null;
    }

    this.currentNearbyIds.clear();
    this.remoteStreams.clear();
    this.listeners.clear();
    this.sendSignalFn = null;
    console.log("[ProximityMedia] Destroyed");
  }

  // ── Simple EventEmitter ──────────────────────────────────

  on(event: MediaEventType, fn: MediaListener): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(fn);
  }

  off(event: MediaEventType, fn: MediaListener): void {
    this.listeners.get(event)?.delete(fn);
  }

  private emit(event: string, data: any): void {
    const fns = this.listeners.get(event);
    if (fns) {
      for (const fn of fns) {
        try {
          fn(data);
        } catch (err) {
          console.error(`[ProximityMedia] Error in listener for "${event}":`, err);
        }
      }
    }
  }
}
