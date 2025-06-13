// File: /src/hooks/usePortfolioSocket.ts

import { useEffect, useRef, useState } from 'react';
import { usePortfolioStore, type PLUpdatePayload } from '../store/portfolioStore';

// WebSocket configuration interface
interface WebSocketConfig {
  url: string;
  autoConnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

// WebSocket hook return interface
interface UsePortfolioSocketReturn {
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  connect: () => void;
  disconnect: () => void;
  sendMessage: (message: any) => void;
}

export const usePortfolioSocket = (config: WebSocketConfig): UsePortfolioSocketReturn => {
  const {
    url,
    autoConnect = true,
    reconnectInterval = 5000,
    maxReconnectAttempts = 10
  } = config;

  const ws = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeoutId = useRef<NodeJS.Timeout | null>(null);
  
  // Local state
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Get Zustand store actions
  const { setConnectionStatus, updateClientPL } = usePortfolioStore();

  const connect = () => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    try {
      setIsConnecting(true);
      setError(null);
      setConnectionStatus('connecting');
      
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setIsConnecting(false);
        setConnectionStatus('connected');
        setError(null);
        reconnectAttempts.current = 0; // Reset reconnect attempts on successful connection
        
        // Send a ping to keep connection alive
        if (ws.current?.readyState === WebSocket.OPEN) {
          ws.current.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
        }
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Handle P&L updates according to the data contract
          if (data.type === 'pl_update') {
            const plUpdate: PLUpdatePayload = {
              type: data.type,
              client_id: data.client_id,
              current_pl: data.current_pl,
              change: data.change,
              percentageChange: data.percentageChange,
              day_pl: data.day_pl,
              portfolio_value: data.portfolio_value,
              lastUpdated: data.lastUpdated,
            };
            
            // Update the client's P&L in the store
            updateClientPL(plUpdate);
            
            console.log(`P&L update received for client ${data.client_id}:`, {
              current_pl: data.current_pl,
              change: data.change,
              percentage: data.percentageChange,
            });
          } else if (data.type === 'ping' || event.data.startsWith('Echo:')) {
            // Handle ping/pong or echo responses for connection health
            console.log('WebSocket heartbeat received');
          } else {
            console.log('Unknown message type received:', data);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        setIsConnecting(false);
        setConnectionStatus('disconnected');
        
        // Attempt to reconnect if it wasn't a manual close
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts && autoConnect) {
          scheduleReconnect();
        }
      };

      ws.current.onerror = (event) => {
        console.error('WebSocket error:', event);
        const errorMsg = 'WebSocket connection failed';
        setError(errorMsg);
        setIsConnected(false);
        setIsConnecting(false);
        setConnectionStatus('error');
        
        // Schedule reconnect on error
        if (reconnectAttempts.current < maxReconnectAttempts && autoConnect) {
          scheduleReconnect();
        }
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      const errorMsg = 'Failed to establish connection';
      setError(errorMsg);
      setIsConnected(false);
      setIsConnecting(false);
      setConnectionStatus('error');
      
      if (autoConnect) {
        scheduleReconnect();
      }
    }
  };

  const scheduleReconnect = () => {
    if (reconnectAttempts.current >= maxReconnectAttempts) {
      console.error('Maximum reconnection attempts reached');
      setError('Connection failed after maximum attempts');
      setConnectionStatus('error');
      return;
    }

    reconnectAttempts.current++;
    const delay = reconnectInterval * Math.pow(1.5, reconnectAttempts.current - 1); // Exponential backoff
    
    console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttempts.current}/${maxReconnectAttempts})`);
    
    reconnectTimeoutId.current = setTimeout(() => {
      connect();
    }, delay);
  };

  const disconnect = () => {
    // Clear any pending reconnection attempts
    if (reconnectTimeoutId.current) {
      clearTimeout(reconnectTimeoutId.current);
      reconnectTimeoutId.current = null;
    }

    // Close the WebSocket connection
    if (ws.current) {
      // Set readyState check to avoid calling close on already closed connection
      if (ws.current.readyState === WebSocket.OPEN || ws.current.readyState === WebSocket.CONNECTING) {
        ws.current.close(1000, 'Manual disconnect'); // Normal closure
      }
      ws.current = null;
    }

    setIsConnected(false);
    setIsConnecting(false);
    setConnectionStatus('disconnected');
    setError(null);
  };

  const sendMessage = (message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected. Cannot send message:', message);
      setError('Cannot send message: not connected');
    }
  };

  // Setup and cleanup WebSocket connection
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    // Cleanup function that runs on component unmount
    return () => {
      disconnect();
    };
  }, [url, autoConnect]); // Re-connect if URL or autoConnect changes

  // Periodic heartbeat to keep connection alive
  useEffect(() => {
    const heartbeatInterval = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        sendMessage({ type: 'ping', timestamp: Date.now() });
      }
    }, 30000); // Send heartbeat every 30 seconds

    return () => clearInterval(heartbeatInterval);
  }, []);

  return {
    isConnected,
    isConnecting,
    error,
    connect,
    disconnect,
    sendMessage,
  };
};