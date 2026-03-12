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
  private acquiringStream = false;

  setMySocketId(id: string): void {
    this.mySocketId = id;
  }

  setSendSignal(fn: (targetId: string, signal: any) => void): void {
    this.sendSignalFn = fn;
  }

  // ── Local Stream ─────────────────────────────────────────

  async acquireLocalStream(): Promise<MediaStream | null> {
    if (this.localStream) return this.localStream;
    if (this.acquiringStream) return null;

    this.acquiringStream = true;
    try {
      // Try video + audio first, fall back to audio-only
      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
          video: { width: { ideal: 320 }, height: { ideal: 240 }, frameRate: { max: 15 } },
        });
      } catch {
        try {
          stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        } catch {
          this.emit("error", { message: "Camera and microphone access denied" });
          return null;
        }
      }

      if (this.destroyed) {
        stream.getTracks().forEach((t) => t.stop());
        return null;
      }

      this.localStream = stream;
      this.emit("local-stream", { stream });
      return stream;
    } finally {
      this.acquiringStream = false;
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

    // Acquire local stream lazily on first proximity contact
    const stream = await this.acquireLocalStream();
    if (!stream || this.destroyed) return;

    // Only the initiator (smaller socketId) creates the offer
    for (const peerId of added) {
      if (this.mySocketId < peerId) {
        this.createPeerAndOffer(peerId);
      }
      // else: wait for their offer
    }
  }

  // ── Peer Connection Management ───────────────────────────

  private createPeerConnection(peerId: string): RTCPeerConnection {
    const pc = new RTCPeerConnection(RTC_CONFIG);

    // Add local tracks
    if (this.localStream) {
      for (const track of this.localStream.getTracks()) {
        pc.addTrack(track, this.localStream);
      }
    }

    // ICE candidates → relay to peer
    pc.onicecandidate = (event) => {
      if (event.candidate && this.sendSignalFn) {
        this.sendSignalFn(peerId, { candidate: event.candidate.toJSON() });
      }
    };

    // Remote stream received
    pc.ontrack = (event) => {
      const [remoteStream] = event.streams;
      if (remoteStream && !this.remoteStreams.has(peerId)) {
        this.remoteStreams.set(peerId, remoteStream);
        this.emit("stream-added", { peerId, stream: remoteStream });
      }
    };

    // Connection state changes
    pc.onconnectionstatechange = () => {
      const state = pc.connectionState;
      if (state === "disconnected" || state === "failed" || state === "closed") {
        this.closePeer(peerId);
      }
    };

    pc.oniceconnectionstatechange = () => {
      if (pc.iceConnectionState === "failed") {
        // Try ICE restart
        pc.restartIce();
      }
    };

    this.peers.set(peerId, pc);
    return pc;
  }

  private async createPeerAndOffer(peerId: string): Promise<void> {
    if (this.destroyed || this.peers.has(peerId)) return;

    const pc = this.createPeerConnection(peerId);

    try {
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      if (this.sendSignalFn && pc.localDescription) {
        this.sendSignalFn(peerId, {
          type: pc.localDescription.type,
          sdp: pc.localDescription.sdp,
        });
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
      // Acquire local stream before answering
      const stream = await this.acquireLocalStream();
      if (!stream || this.destroyed) return;

      // Close existing peer if any (renegotiation)
      if (this.peers.has(fromId)) {
        this.closePeer(fromId);
      }

      const pc = this.createPeerConnection(fromId);

      try {
        await pc.setRemoteDescription(new RTCSessionDescription(signal));
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);

        if (this.sendSignalFn && pc.localDescription) {
          this.sendSignalFn(fromId, {
            type: pc.localDescription.type,
            sdp: pc.localDescription.sdp,
          });
        }
      } catch (err) {
        console.error("[ProximityMedia] Failed to handle offer from", fromId, err);
        this.closePeer(fromId);
      }
      return;
    }

    // SDP answer
    if (signal.type === "answer") {
      const pc = this.peers.get(fromId);
      if (pc && pc.signalingState === "have-local-offer") {
        try {
          await pc.setRemoteDescription(new RTCSessionDescription(signal));
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
        fn(data);
      }
    }
  }
}
