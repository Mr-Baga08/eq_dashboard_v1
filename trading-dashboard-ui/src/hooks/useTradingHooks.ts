// // src/hooks/useTradingHooks.ts
// import { useEffect, useCallback, useState, useMemo } from 'react';
// import { usePortfolioStore } from '../store/portfolioStore';
// import { useNotify } from '../store/notificationStore';

// // Hook for managing client data with loading and error states
// export const useClients = () => {
//   const {
//     clients,
//     loading,
//     errors,
//     fetchClients,
//     createClient,
//     updateClient,
//     updateClientCredentials,
//   } = usePortfolioStore();

//   const notify = useNotify();

//   const loadClients = useCallback(async () => {
//     try {
//       await fetchClients();
//     } catch (error) {
//       notify.error('Failed to load clients', 'Please check your connection and try again');
//     }
//   }, [fetchClients, notify]);

//   // Auto-load clients on mount
//   useEffect(() => {
//     if (clients.length === 0 && !loading.clients) {
//       loadClients();
//     }
//   }, []);

//   const handleCreateClient = useCallback(async (clientData: any) => {
//     const success = await createClient(clientData);
//     if (success) {
//       notify.success('Client created successfully');
//     } else {
//       notify.error('Failed to create client');
//     }
//     return success;
//   }, [createClient, notify]);

//   const handleUpdateClient = useCallback(async (clientId: number, clientData: any) => {
//     const success = await updateClient(clientId, clientData);
//     if (success) {
//       notify.success('Client updated successfully');
//     } else {
//       notify.error('Failed to update client');
//     }
//     return success;
//   }, [updateClient, notify]);

//   const handleUpdateCredentials = useCallback(async (clientId: number, credentials: any) => {
//     const success = await updateClientCredentials(clientId, credentials);
//     if (success) {
//       notify.success('Credentials updated successfully');
//     } else {
//       notify.error('Failed to update credentials');
//     }
//     return success;
//   }, [updateClientCredentials, notify]);

//   return {
//     clients,
//     loading: loading.clients,
//     error: errors.clients,
//     refresh: loadClients,
//     createClient: handleCreateClient,
//     updateClient: handleUpdateClient,
//     updateCredentials: handleUpdateCredentials,
//   };
// };

// // Hook for token search functionality
// export const useTokenSearch = () => {
//   const {
//     searchResults,
//     loading,
//     errors,
//     searchTokens,
//     clearTokenSearch,
//     supportedExchanges,
//     fetchSupportedExchanges,
//   } = usePortfolioStore();

//   const [searchQuery, setSearchQuery] = useState('');
//   const [selectedExchange, setSelectedExchange] = useState('NSE');

//   // Debounced search
//   useEffect(() => {
//     if (searchQuery.length >= 2) {
//       const timeoutId = setTimeout(() => {
//         searchTokens(searchQuery, selectedExchange);
//       }, 300);

//       return () => clearTimeout(timeoutId);
//     } else {
//       clearTokenSearch();
//     }
//   }, [searchQuery, selectedExchange, searchTokens, clearTokenSearch]);

//   // Load exchanges on mount
//   useEffect(() => {
//     if (supportedExchanges.length === 0) {
//       fetchSupportedExchanges();
//     }
//   }, [supportedExchanges.length, fetchSupportedExchanges]);

//   const handleSearch = useCallback((query: string) => {
//     setSearchQuery(query);
//   }, []);

//   const handleExchangeChange = useCallback((exchange: string) => {
//     setSelectedExchange(exchange);
//   }, []);

//   const clearSearch = useCallback(() => {
//     setSearchQuery('');
//     clearTokenSearch();
//   }, [clearTokenSearch]);

//   return {
//     searchQuery,
//     searchResults,
//     loading: loading.tokenSearch,
//     error: errors.tokenSearch,
//     selectedExchange,
//     supportedExchanges,
//     onSearch: handleSearch,
//     onExchangeChange: handleExchangeChange,
//     clearSearch,
//   };
// };

// // Hook for trade execution
// export const useTradExecution = () => {
//   const {
//     tradeConfig,
//     clientOrders,
//     orderResults,
//     loading,
//     errors,
//     setTradeConfig,
//     setClientOrder,
//     removeClientOrder,
//     clearClientOrders,
//     executeBatchOrders,
//     clearOrderResults,
//   } = usePortfolioStore();

//   const notify = useNotify();

//   const handleSetTradeConfig = useCallback((config: any) => {
//     setTradeConfig(config);
//   }, [setTradeConfig]);

//   const handleSetClientOrder = useCallback((clientId: number, quantity: number, price?: number) => {
//     if (quantity <= 0) {
//       removeClientOrder(clientId);
//     } else {
//       setClientOrder(clientId, quantity, price);
//     }
//   }, [setClientOrder, removeClientOrder]);

//   const handleExecuteOrders = useCallback(async (dryRun = false) => {
//     if (clientOrders.length === 0) {
//       notify.warning('No orders to execute', 'Please add quantities for clients first');
//       return false;
//     }

//     if (!tradeConfig.token_id || !tradeConfig.symbol) {
//       notify.warning('No symbol selected', 'Please select a trading symbol first');
//       return false;
//     }

//     const success = await executeBatchOrders(dryRun);
    
//     if (success && orderResults) {
//       const { successful_orders, failed_orders, total_orders } = orderResults.summary;
      
//       if (failed_orders === 0) {
//         notify.batchSuccess(successful_orders, total_orders);
//       } else if (successful_orders > 0) {
//         notify.batchPartialSuccess(successful_orders, total_orders);
//       } else {
//         notify.batchFailure('All orders failed to execute');
//       }
//     } else if (!success) {
//       notify.error('Execution failed', errors.orders || 'Unknown error occurred');
//     }

//     return success;
//   }, [clientOrders, tradeConfig, executeBatchOrders, orderResults, notify, errors.orders]);

//   const handleClearOrders = useCallback(() => {
//     clearClientOrders();
//     clearOrderResults();
//   }, [clearClientOrders, clearOrderResults]);

//   // Calculate summary statistics
//   const orderSummary = useMemo(() => {
//     const totalQuantity = clientOrders.reduce((sum, order) => sum + order.quantity, 0);
//     const clientCount = clientOrders.length;
//     const avgQuantity = clientCount > 0 ? totalQuantity / clientCount : 0;

//     return {
//       totalQuantity,
//       clientCount,
//       avgQuantity: Math.round(avgQuantity),
//       symbol: tradeConfig.symbol,
//       transactionType: tradeConfig.transaction_type,
//       orderType: tradeConfig.order_type,
//     };
//   }, [clientOrders, tradeConfig]);

//   return {
//     tradeConfig,
//     clientOrders,
//     orderResults,
//     orderSummary,
//     loading: loading.orders,
//     error: errors.orders,
//     setTradeConfig: handleSetTradeConfig,
//     setClientOrder: handleSetClientOrder,
//     executeOrders: handleExecuteOrders,
//     clearOrders: handleClearOrders,
//   };
// };

// // Hook for portfolio data management
// export const usePortfolio = (clientId?: number) => {
//   const {
//     portfolioData,
//     dashboardStats,
//     clientSummaries,
//     loading,
//     errors,
//     fetchPortfolioData,
//     fetchDashboardStats,
//     fetchClientSummaries,
//     fetchClientPositions,
//     fetchClientHoldings,
//   } = usePortfolioStore();

//   const notify = useNotify();

//   const clientPortfolio = clientId ? portfolioData[clientId] : null;

//   const loadPortfolioData = useCallback(async (id: number, segment = 'interactive') => {
//     try {
//       await fetchPortfolioData(id, segment);
//       notify.portfolioUpdate(`Portfolio data updated for client ${id}`);
//     } catch (error) {
//       notify.error('Failed to load portfolio data');
//     }
//   }, [fetchPortfolioData, notify]);

//   const loadDashboardStats = useCallback(async () => {
//     try {
//       await fetchDashboardStats();
//     } catch (error) {
//       notify.error('Failed to load dashboard statistics');
//     }
//   }, [fetchDashboardStats, notify]);

//   const loadClientSummaries = useCallback(async (limit = 20) => {
//     try {
//       await fetchClientSummaries(limit);
//     } catch (error) {
//       notify.error('Failed to load client summaries');
//     }
//   }, [fetchClientSummaries, notify]);

//   // Auto-load dashboard data on mount
//   useEffect(() => {
//     if (!dashboardStats) {
//       loadDashboardStats();
//     }
//     if (clientSummaries.length === 0) {
//       loadClientSummaries();
//     }
//   }, []);

//   return {
//     portfolioData: clientPortfolio,
//     dashboardStats,
//     clientSummaries,
//     loading: loading.portfolio,
//     error: errors.portfolio,
//     loadPortfolioData,
//     loadDashboardStats,
//     loadClientSummaries,
//     fetchPositions: fetchClientPositions,
//     fetchHoldings: fetchClientHoldings,
//   };
// };

// // Hook for formatting and calculations
// export const useTradeFormatting = () => {
//   const formatCurrency = useCallback((amount: number | string) => {
//     const num = typeof amount === 'string' ? parseFloat(amount) : amount;
//     return new Intl.NumberFormat('en-IN', {
//       style: 'currency',
//       currency: 'INR',
//       minimumFractionDigits: 2,
//       maximumFractionDigits: 2,
//     }).format(num);
//   }, []);

//   const formatNumber = useCallback((num: number | string) => {
//     const number = typeof num === 'string' ? parseFloat(num) : num;
//     return new Intl.NumberFormat('en-IN').format(number);
//   }, []);

//   const formatPercentage = useCallback((value: number | string, decimals = 2) => {
//     const num = typeof value === 'string' ? parseFloat(value) : value;
//     return `${num.toFixed(decimals)}%`;
//   }, []);

//   const getPnLClass = useCallback((pnl: number | string) => {
//     const num = typeof pnl === 'string' ? parseFloat(pnl) : pnl;
//     if (num > 0) return 'text-success-600 font-semibold';
//     if (num < 0) return 'text-danger-600 font-semibold';
//     return 'text-gray-600';
//   }, []);

//   const formatPnL = useCallback((pnl: number | string) => {
//     const num = typeof pnl === 'string' ? parseFloat(pnl) : pnl;
//     const formatted = formatCurrency(Math.abs(num));
//     return num >= 0 ? `+${formatted}` : `-${formatted}`;
//   }, [formatCurrency]);

//   return {
//     formatCurrency,
//     formatNumber,
//     formatPercentage,
//     formatPnL,
//     getPnLClass,
//   };
// };

// // Hook for real-time updates (WebSocket integration ready)
// export const useRealTimeUpdates = () => {
//   const [isConnected, setIsConnected] = useState(false);
//   const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  
//   const notify = useNotify();

//   // Placeholder for WebSocket connection
//   useEffect(() => {
//     // This will be implemented when WebSocket integration is added
//     const connectWebSocket = () => {
//       // WebSocket connection logic here
//       setIsConnected(true);
//       setLastUpdate(new Date());
//     };

//     const disconnectWebSocket = () => {
//       setIsConnected(false);
//     };

//     // Auto-reconnect logic can be added here
    
//     return () => {
//       disconnectWebSocket();
//     };
//   }, []);

//   return {
//     isConnected,
//     lastUpdate,
//     connectionStatus: isConnected ? 'connected' : 'disconnected',
//   };
// };

// // Hook for managing UI state
// export const useUIState = () => {
//   const {
//     isTradeConfigOpen,
//     selectedClients,
//     toggleTradeConfig,
//     setSelectedClients,
//   } = usePortfolioStore();

//   const [sidebarOpen, setSidebarOpen] = useState(false);
//   const [activeTab, setActiveTab] = useState('dashboard');

//   const toggleSidebar = useCallback(() => {
//     setSidebarOpen(prev => !prev);
//   }, []);

//   const handleTabChange = useCallback((tab: string) => {
//     setActiveTab(tab);
//   }, []);

//   return {
//     sidebarOpen,
//     activeTab,
//     isTradeConfigOpen,
//     selectedClients,
//     toggleSidebar,
//     setActiveTab: handleTabChange,
//     toggleTradeConfig,
//     setSelectedClients,
//   };
// };