import { useEffect, useRef, useState } from "react";
import type { AgentStatusUpdate } from "../types/session";

/**
 * Custom hook to connect to the session WebSocket room and receive real-time agent updates.
 */
export function useWebSocket(sessionId: string | undefined, onUpdate?: (update: AgentStatusUpdate) => void) {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!sessionId) return;

    // Build absolute WS URL (uses host proxy or current origin)
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/${sessionId}`;

    console.log(`Connecting to WebSocket: ${wsUrl}`);
    const socket = new WebSocket(wsUrl);
    wsRef.current = socket;

    socket.onopen = () => {
      console.log("WebSocket connected!");
      setIsConnected(true);
    };

    socket.onmessage = (event) => {
      try {
        if (event.data === "pong") return;
        const update: AgentStatusUpdate = JSON.parse(event.data);
        if (onUpdate) {
          onUpdate(update);
        }
      } catch (e) {
        console.error("Failed to parse WebSocket message:", e);
      }
    };

    socket.onclose = () => {
      console.log("WebSocket disconnected.");
      setIsConnected(false);
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    // Heartbeat ping loop every 30s to keep connection alive across reverse proxies
    const pingInterval = setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send("ping");
      }
    }, 30000);

    return () => {
      clearInterval(pingInterval);
      socket.close();
    };
  }, [sessionId, onUpdate]);

  return { isConnected };
}
