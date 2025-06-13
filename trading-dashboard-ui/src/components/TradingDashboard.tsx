// // src/components/TradingDashboard.tsx
// // Demo component showing how to use TradeConfigPanel

// import React from 'react';
// import TradeConfigPanel from './TradeConfigPanel';
// import { useTradeConfig, useClientOrders } from '../store/portfolioStore';
// import { useTradeFormatting } from '../hooks/useTradingHooks';

// const TradingDashboard: React.FC = () => {
//   const tradeConfig = useTradeConfig();
//   const clientOrders = useClientOrders();
//   const { formatCurrency } = useTradeFormatting();

//   // Calculate total order value (example)
//   const totalOrderValue = clientOrders.reduce((sum, order) => {
//     return sum + (order.quantity * (order.price || 0));
//   }, 0);

//   return (
//     <div className="space-y-6">
//       {/* Trade Configuration Panel */}
//       <TradeConfigPanel />

//       {/* Status Display */}
//       <div className="card p-6">
//         <h3 className="text-lg font-semibold mb-4">Current Configuration</h3>
        
//         {tradeConfig.symbol ? (
//           <div className="space-y-3">
//             <div className="flex items-center justify-between">
//               <span className="text-gray-600">Selected Symbol:</span>
//               <span className="font-semibold">{tradeConfig.symbol}</span>
//             </div>
            
//             <div className="flex items-center justify-between">
//               <span className="text-gray-600">Exchange:</span>
//               <span className="font-semibold">{tradeConfig.exchange}</span>
//             </div>
            
//             <div className="flex items-center justify-between">
//               <span className="text-gray-600">Transaction Type:</span>
//               <span className={`font-semibold ${
//                 tradeConfig.transaction_type === 'BUY' ? 'text-success-600' : 'text-danger-600'
//               }`}>
//                 {tradeConfig.transaction_type}
//               </span>
//             </div>
            
//             <div className="flex items-center justify-between">
//               <span className="text-gray-600">Order Type:</span>
//               <span className="font-semibold">{tradeConfig.order_type}</span>
//             </div>
            
//             <div className="flex items-center justify-between">
//               <span className="text-gray-600">Product Type:</span>
//               <span className="font-semibold">{tradeConfig.product_type}</span>
//             </div>

//             {clientOrders.length > 0 && (
//               <>
//                 <hr className="my-4" />
//                 <div className="flex items-center justify-between">
//                   <span className="text-gray-600">Total Orders:</span>
//                   <span className="font-semibold">{clientOrders.length}</span>
//                 </div>
                
//                 <div className="flex items-center justify-between">
//                   <span className="text-gray-600">Total Quantity:</span>
//                   <span className="font-semibold">
//                     {clientOrders.reduce((sum, order) => sum + order.quantity, 0)}
//                   </span>
//                 </div>
                
//                 {totalOrderValue > 0 && (
//                   <div className="flex items-center justify-between">
//                     <span className="text-gray-600">Estimated Value:</span>
//                     <span className="font-semibold">{formatCurrency(totalOrderValue)}</span>
//                   </div>
//                 )}
//               </>
//             )}
//           </div>
//         ) : (
//           <div className="text-center py-8 text-gray-500">
//             <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//               <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
//             </svg>
//             <p>Select a symbol to start trading</p>
//           </div>
//         )}
//       </div>

//       {/* Debug Information (Development only) */}
//       {process.env.NODE_ENV === 'development' && (
//         <div className="card p-6 bg-gray-50">
//           <h4 className="text-sm font-semibold text-gray-700 mb-2">Debug Information</h4>
//           <pre className="text-xs text-gray-600 bg-white p-3 rounded border overflow-x-auto">
//             {JSON.stringify({ tradeConfig, clientOrders }, null, 2)}
//           </pre>
//         </div>
//       )}
//     </div>
//   );
// };

// export default TradingDashboard;