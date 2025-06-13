// File: /src/store/portfolioStore.ts (Complete Modified Version)

import { create } from 'zustand';
import  apiClient  from '../services/apiClient';

// Connection status type
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

// Client interface with P&L fields (aligned with backend and ClientsTable)
export interface Client {
  id: string;
  client_code: string;
  client_name: string; // Changed from 'name' to match backend response
  email: string;
  available_funds: number;
  current_pl: number;
  change: number;
  percentage_change: number;
  day_pl: number; // Added for day P&L
  portfolio_value: number; // Added for portfolio value
  is_active: boolean;
  quantity?: number; // For order entry
  last_updated?: string;
}

// Token interface
export interface Token {
  id: string;
  symbol: string;
  exchange: string;
  instrument_type: string;
  lot_size: number;
}

// P&L update payload interface matching the WebSocket data contract (enhanced)
export interface PLUpdatePayload {
  type: 'pl_update';
  client_id: string;
  current_pl: number;
  change: number;
  percentageChange: number;
  day_pl?: number; // Added for day P&L
  portfolio_value?: number; // Added for portfolio value
  lastUpdated: string;
}

// Trade configuration interface
export interface TradeConfig {
  symbol: string;
  exchange: string;
  tradeType: string;
  orderType: string;
  price?: number;
  quantity?: number;
}

// Notification interface
export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: string;
  read?: boolean;
}

// Client order interface
export interface ClientOrder {
  client_id: string;
  quantity: number;
}

// Portfolio store state interface
interface PortfolioState {
  // Data state
  clients: Client[];
  tokens: Token[];
  selectedToken: Token | null;
  tradeConfig: TradeConfig;
  notifications: Notification[];
  
  // Loading states
  isLoading: boolean;
  loadingStatus: {
    clients: boolean;
    tokens: boolean;
    orders: boolean;
  };
  
  // Error state
  error: string | null;
  
  // WebSocket connection status
  connectionStatus: ConnectionStatus;
  
  // Actions
  setConnectionStatus: (status: ConnectionStatus) => void;
  fetchClients: () => Promise<void>;
  fetchTokens: (query?: string) => Promise<void>;
  setSelectedToken: (token: Token | null) => void;
  updateClientQuantity: (clientId: string, quantity: number) => void;
  updateClientPL: (payload: PLUpdatePayload) => void;
  executeAllOrders: (clientOrders: ClientOrder[]) => Promise<any>;
  getClientQuantities: () => ClientOrder[];
  updateTradeConfig: (config: Partial<TradeConfig>) => void;
  addNotification: (notification: Notification) => void;
  markNotificationAsRead: (id: string) => void;
  clearNotifications: () => void;
  clearError: () => void;
  setError: (error: string) => void;
}

export const usePortfolioStore = create<PortfolioState>((set, get) => ({
  // Initial state
  clients: [],
  tokens: [],
  selectedToken: null,
  tradeConfig: {
    symbol: '',
    exchange: 'NSE',
    tradeType: 'Delivery',
    orderType: 'Market',
  },
  notifications: [],
  
  isLoading: false,
  loadingStatus: {
    clients: false,
    tokens: false,
    orders: false,
  },
  
  error: null,
  connectionStatus: 'disconnected',
  
  // Actions
  setConnectionStatus: (status: ConnectionStatus) => {
    set({ connectionStatus: status });
  },

  setError: (error: string) => {
    set({ error });
  },

  clearError: () => {
    set({ error: null });
  },

  addNotification: (notification: Notification) => {
    set((state) => ({
      notifications: [notification, ...state.notifications],
    }));
  },

  markNotificationAsRead: (id: string) => {
    set((state) => ({
      notifications: state.notifications.map((notif) =>
        notif.id === id ? { ...notif, read: true } : notif
      ),
    }));
  },

  clearNotifications: () => {
    set({ notifications: [] });
  },

  updateTradeConfig: (config: Partial<TradeConfig>) => {
    set((state) => ({
      tradeConfig: { ...state.tradeConfig, ...config },
    }));
  },

  getClientQuantities: (): ClientOrder[] => {
    const { clients } = get();
    return clients
      .filter((client) => client.quantity && client.quantity > 0)
      .map((client) => ({
        client_id: client.id,
        quantity: client.quantity!,
      }));
  },

  fetchClients: async () => {
    set((state) => ({
      loadingStatus: { ...state.loadingStatus, clients: true },
      isLoading: true,
      error: null,
    }));
    
    try {
      const response = await apiClient.get('/api/v1/portfolio/dashboard/clients');
      const clientsData = response.data.data.client_summaries.map((client: any) => ({
        id: client.client_id,
        client_code: client.client_code,
        client_name: client.client_name, // Matches backend response
        email: client.email || '',
        available_funds: client.available_funds || 0,
        current_pl: client.pnl || 0,
        change: client.change || 0,
        percentage_change: client.percentage_change || 0,
        day_pl: client.day_pnl || 0, // From backend
        portfolio_value: client.portfolio_value || 0, // From backend
        is_active: client.is_active !== false,
        quantity: 0, // Initialize quantity for order entry
      }));
      
      set({ clients: clientsData });
    } catch (error: any) {
      const errorMessage = error?.response?.data?.message || 'Failed to fetch clients';
      console.error('Failed to fetch clients:', error);
      set({ error: errorMessage });
    } finally {
      set((state) => ({
        loadingStatus: { ...state.loadingStatus, clients: false },
        isLoading: false,
      }));
    }
  },

  fetchTokens: async (query?: string) => {
    set((state) => ({
      loadingStatus: { ...state.loadingStatus, tokens: true }
    }));
    
    try {
      const url = query 
        ? `/api/v1/tokens/search?q=${encodeURIComponent(query)}`
        : '/api/v1/tokens';
      
      const response = await apiClient.get(url);
      set({ tokens: response.data });
    } catch (error: any) {
      console.error('Failed to fetch tokens:', error);
      const errorMessage = error?.response?.data?.message || 'Failed to fetch tokens';
      set({ error: errorMessage });
    } finally {
      set((state) => ({
        loadingStatus: { ...state.loadingStatus, tokens: false }
      }));
    }
  },

  setSelectedToken: (token: Token | null) => {
    set({ selectedToken: token });
    if (token) {
      set((state) => ({
        tradeConfig: { ...state.tradeConfig, symbol: token.symbol },
      }));
    }
  },

  updateClientQuantity: (clientId: string, quantity: number) => {
    set((state) => ({
      clients: state.clients.map((client) =>
        client.id === clientId 
          ? { ...client, quantity }
          : client
      )
    }));
  },

  updateClientPL: (payload: PLUpdatePayload) => {
    set((state) => ({
      clients: state.clients.map((client) =>
        client.id === payload.client_id || client.client_code === payload.client_id
          ? {
              ...client,
              current_pl: payload.current_pl,
              change: payload.change,
              percentage_change: payload.percentageChange,
              day_pl: payload.day_pl !== undefined ? payload.day_pl : client.day_pl,
              portfolio_value: payload.portfolio_value !== undefined ? payload.portfolio_value : client.portfolio_value,
              last_updated: payload.lastUpdated,
            }
          : client
      )
    }));
  },

  executeAllOrders: async (clientOrders: ClientOrder[]) => {
    const { tradeConfig, addNotification } = get();
    
    set((state) => ({
      loadingStatus: { ...state.loadingStatus, orders: true },
      error: null,
    }));
    
    try {
      // Prepare the payload for batch order execution
      const payload = {
        ...tradeConfig,
        client_orders: clientOrders,
      };
      
      const response = await apiClient.post('/api/v1/orders/execute-all', payload);
      
      // Reset quantities after successful execution
      set((state) => ({
        clients: state.clients.map((client) => ({
          ...client,
          quantity: 0,
        }))
      }));
      
      // Add success notification
      addNotification({
        id: `success-${Date.now()}`,
        type: 'success',
        title: 'Orders Executed',
        message: `Successfully executed ${clientOrders.length} orders`,
        timestamp: new Date().toISOString(),
      });
      
      return response.data;
    } catch (error: any) {
      const errorMessage = error?.response?.data?.message || 'Failed to execute orders';
      console.error('Failed to execute orders:', error);
      
      // Add error notification
      addNotification({
        id: `error-${Date.now()}`,
        type: 'error',
        title: 'Execution Failed',
        message: errorMessage,
        timestamp: new Date().toISOString(),
      });
      
      set({ error: errorMessage });
      throw error;
    } finally {
      set((state) => ({
        loadingStatus: { ...state.loadingStatus, orders: false }
      }));
    }
  },
}));