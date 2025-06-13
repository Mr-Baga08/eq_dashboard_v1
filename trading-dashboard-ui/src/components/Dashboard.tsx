// // File: /src/pages/Dashboard.tsx

// import React, { useEffect, useState } from 'react';
// import { usePortfolioStore } from '../store/portfolioStore';
// import { usePortfolioSocket } from '../hooks/usePortfolioSocket';
// import TradeConfigPanel from '../components/TradeConfigPanel';
// import ClientsTable from '../components/ClientsTable';
// import ConnectionStatus from '../../store/ConnectionStatus';
// import NotificationCenter from '../components/NotificationCenter';

// const Dashboard: React.FC = () => {
//   const [isExecuting, setIsExecuting] = useState(false);
  
//   // Zustand store
//   const {
//     clients,
//     tradeConfig,
//     isLoading,
//     error,
//     notifications,
//     fetchClients,
//     executeAllOrders,
//     getClientQuantities,
//     clearError,
//     addNotification
//   } = usePortfolioStore();

//   // WebSocket connection
//   const {
//     isConnected,
//     isConnecting,
//     error: wsError,
//     connect,
//     disconnect,
//     sendMessage
//   } = usePortfolioSocket({
//     url: 'ws://localhost:8000/ws/updates',
//     autoConnect: true,
//     reconnectInterval: 5000,
//     maxReconnectAttempts: 5
//   });

//   // Fetch clients on mount
//   useEffect(() => {
//     fetchClients();
//   }, [fetchClients]);

//   // Handle execute all orders
//   const handleExecuteAll = async () => {
//     if (!tradeConfig.symbol) {
//       addNotification({
//         id: `error-${Date.now()}`,
//         type: 'error',
//         title: 'Validation Error',
//         message: 'Please select a symbol before executing orders',
//         timestamp: new Date().toISOString()
//       });
//       return;
//     }

//     const clientOrders = getClientQuantities();
//     if (clientOrders.length === 0) {
//       addNotification({
//         id: `error-${Date.now()}`,
//         type: 'warning',
//         title: 'No Orders to Execute',
//         message: 'Please enter quantities for clients before executing',
//         timestamp: new Date().toISOString()
//       });
//       return;
//     }

//     setIsExecuting(true);
//     try {
//       await executeAllOrders(clientOrders);
//     } catch (error) {
//       console.error('Failed to execute orders:', error);
//     } finally {
//       setIsExecuting(false);
//     }
//   };

//   // Handle WebSocket reconnection
//   const handleReconnect = () => {
//     connect();
//   };

//   // Send test message to WebSocket
//   const handleSendTestMessage = () => {
//     sendMessage({
//       type: 'test',
//       message: 'Test message from dashboard',
//       timestamp: new Date().toISOString()
//     });
//   };

//   const unreadNotifications = notifications.filter(n => !n.read).length;

//   return (
//     <div className="min-h-screen bg-gray-50 p-6">
//       <div className="max-w-7xl mx-auto">
//         {/* Header */}
//         <div className="mb-8">
//           <div className="flex justify-between items-center">
//             <div>
//               <h1 className="text-3xl font-bold text-gray-900">Trading Dashboard</h1>
//               <p className="text-gray-600 mt-1">
//                 Manage portfolio and execute trades with real-time updates
//               </p>
//             </div>
            
//             {/* Connection Status and Notifications */}
//             <div className="flex items-center space-x-4">
//               <NotificationCenter 
//                 notifications={notifications} 
//                 unreadCount={unreadNotifications}
//               />
//               <ConnectionStatus 
//                 isConnected={isConnected}
//                 isConnecting={isConnecting}
//                 error={wsError}
//                 onReconnect={handleReconnect}
//               />
//             </div>
//           </div>
//         </div>

//         {/* Error Banner */}
//         {error && (
//           <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
//             <div className="flex justify-between items-center">
//               <div className="flex items-center">
//                 <div className="h-5 w-5 text-red-400 mr-3">⚠️</div>
//                 <div>
//                   <h3 className="text-sm font-medium text-red-800">Error</h3>
//                   <p className="text-sm text-red-700">{error}</p>
//                 </div>
//               </div>
//               <button
//                 onClick={clearError}
//                 className="text-red-400 hover:text-red-600"
//               >
//                 ✕
//               </button>
//             </div>
//           </div>
//         )}

//         {/* WebSocket Error Banner */}
//         {wsError && (
//           <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
//             <div className="flex justify-between items-center">
//               <div className="flex items-center">
//                 <div className="h-5 w-5 text-yellow-400 mr-3">🔌</div>
//                 <div>
//                   <h3 className="text-sm font-medium text-yellow-800">WebSocket Connection Issue</h3>
//                   <p className="text-sm text-yellow-700">{wsError}</p>
//                 </div>
//               </div>
//               <button
//                 onClick={handleReconnect}
//                 className="text-yellow-600 hover:text-yellow-800 text-sm font-medium"
//               >
//                 Retry
//               </button>
//             </div>
//           </div>
//         )}

//         {/* Trade Configuration Panel */}
//         <div className="mb-8">
//           <TradeConfigPanel />
//         </div>

//         {/* Stats Cards */}
//         <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
//           <div className="bg-white rounded-lg shadow p-6">
//             <h3 className="text-sm font-medium text-gray-500">Total Clients</h3>
//             <p className="text-2xl font-bold text-gray-900">{clients.length}</p>
//           </div>
          
//           <div className="bg-white rounded-lg shadow p-6">
//             <h3 className="text-sm font-medium text-gray-500">Active Orders</h3>
//             <p className="text-2xl font-bold text-gray-900">
//               {getClientQuantities().length}
//             </p>
//           </div>
          
//           <div className="bg-white rounded-lg shadow p-6">
//             <h3 className="text-sm font-medium text-gray-500">Total P&L</h3>
//             <p className={`text-2xl font-bold ${
//               clients.reduce((sum, client) => sum + (client.current_pl || 0), 0) >= 0 
//                 ? 'text-green-600' 
//                 : 'text-red-600'
//             }`}>
//               ₹{clients.reduce((sum, client) => sum + (client.current_pl || 0), 0).toFixed(2)}
//             </p>
//           </div>
          
//           <div className="bg-white rounded-lg shadow p-6">
//             <h3 className="text-sm font-medium text-gray-500">Connection</h3>
//             <div className="flex items-center mt-1">
//               <div className={`h-3 w-3 rounded-full mr-2 ${
//                 isConnected ? 'bg-green-400' : 
//                 isConnecting ? 'bg-yellow-400' : 'bg-red-400'
//               }`}></div>
//               <span className="text-sm font-medium text-gray-900">
//                 {isConnected ? 'Connected' : isConnecting ? 'Connecting' : 'Disconnected'}
//               </span>
//             </div>
//           </div>
//         </div>

//         {/* Clients Table */}
//         <div className="bg-white rounded-lg shadow mb-8">
//           <div className="px-6 py-4 border-b border-gray-200">
//             <h2 className="text-lg font-medium text-gray-900">Client Portfolio</h2>
//             <p className="text-sm text-gray-500">
//               Real-time P&L updates {isConnected ? '🟢' : '🔴'}
//             </p>
//           </div>
          
//           {isLoading ? (
//             <div className="p-12 text-center">
//               <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
//               <p className="mt-2 text-gray-500">Loading clients...</p>
//             </div>
//           ) : (
//             <ClientsTable clients={clients} />
//           )}
//         </div>

//         {/* Execute All Button */}
//         <div className="flex justify-between items-center">
//           <div className="flex space-x-4">
//             <button
//               onClick={handleExecuteAll}
//               disabled={isExecuting || !tradeConfig.symbol || getClientQuantities().length === 0}
//               className={`px-6 py-3 rounded-lg font-medium transition-colors ${
//                 isExecuting || !tradeConfig.symbol || getClientQuantities().length === 0
//                   ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
//                   : 'bg-blue-600 text-white hover:bg-blue-700'
//               }`}
//             >
//               {isExecuting ? (
//                 <>
//                   <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
//                   Executing...
//                 </>
//               ) : (
//                 `Execute All Orders (${getClientQuantities().length})`
//               )}
//             </button>

//             {/* Development Tools */}
//             {process.env.NODE_ENV === 'development' && (
//               <button
//                 onClick={handleSendTestMessage}
//                 disabled={!isConnected}
//                 className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
//               >
//                 Send Test Message
//               </button>
//             )}
//           </div>

//           <div className="text-sm text-gray-500">
//             Last updated: {new Date().toLocaleTimeString()}
//           </div>
//         </div>
//       </div>
//     </div>
//   );
// };

// export default Dashboard;