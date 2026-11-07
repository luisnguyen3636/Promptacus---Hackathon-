/**
 * CYBERGUARD AI · SOC v2.1 — NATIVE WEBSOCKET STREAM BROKER (EDGE NATIVE)
 * Handles high-frequency telemetry & bounding box broadcasting via Cloudflare WebSocketPair.
 * Supports active push broadcasting when real AI events are ingested.
 */

import { getCameras } from "./camera_manager";

// Set of active WebSocket connections
const activeSockets = new Set<WebSocket>();

export function broadcastMessage(message: any): void {
  const payload = typeof message === "string" ? message : JSON.stringify(message);
  for (const ws of activeSockets) {
    try {
      ws.send(payload);
    } catch {
      activeSockets.delete(ws);
    }
  }
}

export function handleWebSocketUpgrade(request: Request): Response {
  const upgradeHeader = request.headers.get("Upgrade");
  if (!upgradeHeader || upgradeHeader.toLowerCase() !== "websocket") {
    return new Response("Expected Upgrade: websocket", { status: 426 });
  }

  // Cloudflare Workers Native WebSocketPair
  const webSocketPair = new WebSocketPair();
  const [client, server] = Object.values(webSocketPair);

  server.accept();
  activeSockets.add(server);

  // 1. Send immediate connection handshake
  server.send(
    JSON.stringify({
      type: "CONNECTED",
      serverTime: new Date().toISOString()
    })
  );

  // 2. Send initial telemetry & bounding box tick
  server.send(
    JSON.stringify({
      type: "TELEMETRY_AND_AI_TICK",
      cameras: getCameras(),
      timestamp: Date.now()
    })
  );

  // 3. Periodic real-time kinematic broadcast
  const interval = setInterval(() => {
    try {
      server.send(
        JSON.stringify({
          type: "TELEMETRY_AND_AI_TICK",
          cameras: getCameras(),
          timestamp: Date.now()
        })
      );
    } catch {
      clearInterval(interval);
      activeSockets.delete(server);
    }
  }, 250);

  server.addEventListener("message", (event) => {
    try {
      const data = JSON.parse(event.data as string);
      if (data.type === "PING" || data.type === "REQUEST_TICK") {
        server.send(
          JSON.stringify({
            type: "TELEMETRY_AND_AI_TICK",
            cameras: getCameras(),
            timestamp: Date.now()
          })
        );
      }
    } catch {
      // Ignore malformed message
    }
  });

  server.addEventListener("close", () => {
    clearInterval(interval);
    activeSockets.delete(server);
  });

  server.addEventListener("error", () => {
    clearInterval(interval);
    activeSockets.delete(server);
  });

  return new Response(null, {
    status: 101,
    webSocket: client
  });
}
