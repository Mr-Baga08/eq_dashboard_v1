// File: /src/components/TradeConfigPanel.tsx

import React, { useState, useEffect, useRef } from 'react';
import { usePortfolioStore, type Token } from '../store/portfolioStore';

const TradeConfigPanel: React.FC = () => {
  const {
    tradeConfig,
    tokens,
    selectedToken,
    loadingStatus,
    updateTradeConfig,
    fetchTokens,
    setSelectedToken
  } = usePortfolioStore();

  // Local state for symbol search
  const [symbolQuery, setSymbolQuery] = useState('');
  const [showSymbolDropdown, setShowSymbolDropdown] = useState(false);
  const [filteredTokens, setFilteredTokens] = useState<Token[]>([]);
  
  // Refs for handling dropdown
  const symbolInputRef = useRef<HTMLInputElement>(null);
  const symbolDropdownRef = useRef<HTMLDivElement>(null);

  // Handle symbol search
  useEffect(() => {
    if (symbolQuery.length >= 2) {
      fetchTokens(symbolQuery);
      setShowSymbolDropdown(true);
    } else {
      setShowSymbolDropdown(false);
    }
  }, [symbolQuery, fetchTokens]);

  // Filter tokens based on query
  useEffect(() => {
    if (tokens && symbolQuery) {
      const filtered = tokens.filter(token => 
        token.symbol.toLowerCase().includes(symbolQuery.toLowerCase()) ||
        token.instrument_type.toLowerCase().includes(symbolQuery.toLowerCase())
      );
      setFilteredTokens(filtered.slice(0, 10)); // Limit to 10 results
    }
  }, [tokens, symbolQuery]);

  // Handle clicking outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        symbolDropdownRef.current &&
        !symbolDropdownRef.current.contains(event.target as Node) &&
        !symbolInputRef.current?.contains(event.target as Node)
      ) {
        setShowSymbolDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSymbolSelect = (token: Token) => {
    setSelectedToken(token);
    setSymbolQuery(token.symbol);
    updateTradeConfig({ symbol: token.symbol });
    setShowSymbolDropdown(false);
  };

  const handleSymbolInputChange = (value: string) => {
    setSymbolQuery(value);
    updateTradeConfig({ symbol: value });
    
    // Clear selected token if input doesn't match
    if (selectedToken && selectedToken.symbol !== value) {
      setSelectedToken(null);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">Trade Configuration</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Symbol Search */}
        <div className="relative">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Select Symbol *
          </label>
          <div className="relative">
            <input
              ref={symbolInputRef}
              type="text"
              value={symbolQuery}
              onChange={(e) => handleSymbolInputChange(e.target.value)}
              placeholder="Search symbol..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            
            {/* Search Icon */}
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
              {loadingStatus.tokens ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              ) : (
                <span className="text-gray-400">🔍</span>
              )}
            </div>

            {/* Selected Token Indicator */}
            {selectedToken && (
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <span className="text-green-500 text-xs">✓</span>
              </div>
            )}
          </div>
          
          {/* Symbol Dropdown */}
          {showSymbolDropdown && (
            <div
              ref={symbolDropdownRef}
              className="absolute z-10 mt-1 w-full bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto"
            >
              {filteredTokens.length > 0 ? (
                filteredTokens.map((token) => (
                  <div
                    key={token.id}
                    onClick={() => handleSymbolSelect(token)}
                    className="px-3 py-2 cursor-pointer hover:bg-blue-50 border-b border-gray-100 last:border-b-0"
                  >
                    <div className="flex justify-between items-center">
                      <div>
                        <span className="font-medium text-gray-900">{token.symbol}</span>
                        <span className="text-sm text-gray-500 ml-2">({token.exchange})</span>
                      </div>
                      <span className="text-xs text-gray-400">{token.instrument_type}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="px-3 py-2 text-sm text-gray-500">
                  {symbolQuery.length < 2 ? 'Type to search symbols...' : 'No symbols found'}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Exchange */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Exchange
          </label>
          <select
            value={tradeConfig.exchange}
            onChange={(e) => updateTradeConfig({ exchange: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="NSE">NSE</option>
            <option value="BSE">BSE</option>
          </select>
        </div>

        {/* Trade Type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Trade Type
          </label>
          <select
            value={tradeConfig.tradeType}
            onChange={(e) => updateTradeConfig({ tradeType: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="Delivery">Delivery</option>
            <option value="Intraday">Intraday</option>
            <option value="MTF">MTF</option>
          </select>
        </div>

        {/* Order Type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Order Type
          </label>
          <select
            value={tradeConfig.orderType}
            onChange={(e) => updateTradeConfig({ orderType: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="Market">Market</option>
            <option value="Limit">Limit</option>
          </select>
        </div>
      </div>

      {/* Price Input (for Limit orders) */}
      {tradeConfig.orderType === 'Limit' && (
        <div className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Limit Price ₹
              </label>
              <input
                type="number"
                step="0.01"
                value={tradeConfig.price || ''}
                onChange={(e) => updateTradeConfig({ price: parseFloat(e.target.value) || 0 })}
                placeholder="Enter limit price"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        </div>
      )}

      {/* Selected Token Info */}
      {selectedToken && (
        <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-md">
          <div className="flex items-center space-x-2">
            <span className="text-green-600">✓</span>
            <span className="text-sm font-medium text-green-800">
              Selected: {selectedToken.symbol} ({selectedToken.exchange})
            </span>
            <span className="text-xs text-green-600">
              Lot Size: {selectedToken.lot_size}
            </span>
          </div>
        </div>
      )}

      {/* Validation Messages */}
      {!tradeConfig.symbol && (
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
          <div className="flex items-center space-x-2">
            <span className="text-yellow-600">⚠️</span>
            <span className="text-sm text-yellow-800">
              Please select a symbol to enable order execution
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default TradeConfigPanel;