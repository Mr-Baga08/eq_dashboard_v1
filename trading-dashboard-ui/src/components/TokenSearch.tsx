// // src/components/TokenSearch.tsx
// import React from 'react';
// import { useTokenSearch } from '../hooks/useTradingHooks';

// const TokenSearch: React.FC = () => {
//   const {
//     searchQuery,
//     searchResults,
//     loading,
//     selectedExchange,
//     supportedExchanges,
//     onSearch,
//     onExchangeChange,
//     clearSearch,
//   } = useTokenSearch();

//   return (
//     <div className="space-y-4">
//       <div className="flex gap-2">
//         <input
//           type="text"
//           placeholder="Search symbols..."
//           value={searchQuery}
//           onChange={(e) => onSearch(e.target.value)}
//           className="input flex-1"
//         />
        
//         <select
//           value={selectedExchange}
//           onChange={(e) => onExchangeChange(e.target.value)}
//           className="input"
//         >
//           {supportedExchanges.map((exchange: boolean | React.ReactElement<unknown, string | React.JSXElementConstructor<any>> | Iterable<React.ReactNode> | Promise<string | number | bigint | boolean | React.ReactPortal | React.ReactElement<unknown, string | React.JSXElementConstructor<any>> | Iterable<React.ReactNode> | null | undefined> | React.Key | null | undefined) => (
//             <option key={exchange} value={exchange}>{exchange}</option>
//           ))}
//         </select>
//       </div>

//       {loading && <div>Searching...</div>}

//       <div className="max-h-64 overflow-y-auto">
//         {searchResults.map((token: { id: React.Key | null | undefined; symbol: string | number | bigint | boolean | React.ReactElement<unknown, string | React.JSXElementConstructor<any>> | Iterable<React.ReactNode> | React.ReactPortal | Promise<string | number | bigint | boolean | React.ReactPortal | React.ReactElement<unknown, string | React.JSXElementConstructor<any>> | Iterable<React.ReactNode> | null | undefined> | null | undefined; name: string | number | bigint | boolean | React.ReactElement<unknown, string | React.JSXElementConstructor<any>> | Iterable<React.ReactNode> | React.ReactPortal | Promise<string | number | bigint | boolean | React.ReactPortal | React.ReactElement<unknown, string | React.JSXElementConstructor<any>> | Iterable<React.ReactNode> | null | undefined> | null | undefined; }) => (
//           <div key={token.id} className="p-2 hover:bg-gray-50 cursor-pointer">
//             <div className="font-semibold">{token.symbol}</div>
//             <div className="text-sm text-gray-600">{token.name}</div>
//           </div>
//         ))}
//       </div>
//     </div>
//   );
// };