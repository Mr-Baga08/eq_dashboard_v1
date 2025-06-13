// File: /src/components/ConnectionStatus.tsx

import React from 'react';

interface ConnectionStatusProps {
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  onReconnect: () => void;
}

const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  isConnected,
  isConnecting,
  error,
  onReconnect
}) => {
  const getStatusColor = () => {
    if (isConnected) return 'bg-green-500';
    if (isConnecting) return 'bg-yellow-500 animate-pulse';
    if (error) return 'bg-red-500';
    return 'bg-gray-500';
  };

  const getStatusText = () => {
    if (isConnected) return 'Live Updates Active';
    if (isConnecting) return 'Connecting...';
    if (error) return 'Connection Error';
    return 'Disconnected';
  };

  const getStatusIcon = () => {
    if (isConnected) return '🟢';
    if (isConnecting) return '🟡';
    if (error) return '🔴';
    return '⚫';
  };

  return (
    <div className="flex items-center space-x-3 bg-white rounded-lg shadow px-4 py-2 border">
      {/* Status Indicator */}
      <div className="flex items-center space-x-2">
        <div className={`w-3 h-3 rounded-full ${getStatusColor()}`}></div>
        <span className="text-sm font-medium text-gray-700">
          {getStatusText()}
        </span>
        <span className="text-lg">{getStatusIcon()}</span>
      </div>

      {/* Error Message and Retry Button */}
      {error && (
        <div className="flex items-center space-x-2">
          <span className="text-xs text-red-600 max-w-xs truncate" title={error}>
            {error}
          </span>
          <button
            onClick={onReconnect}
            className="text-xs bg-red-100 text-red-700 hover:bg-red-200 px-2 py-1 rounded transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Reconnect Button for Disconnected State */}
      {!isConnected && !isConnecting && !error && (
        <button
          onClick={onReconnect}
          className="text-xs bg-gray-100 text-gray-700 hover:bg-gray-200 px-2 py-1 rounded transition-colors"
        >
          Connect
        </button>
      )}

      {/* Connection Info Tooltip */}
      <div className="relative group">
        <div className="cursor-help text-gray-400 hover:text-gray-600">
          ℹ️
        </div>
        <div className="absolute bottom-full right-0 mb-2 hidden group-hover:block">
          <div className="bg-black text-white text-xs rounded px-2 py-1 whitespace-nowrap">
            {isConnected ? 
              'Real-time P&L updates active via WebSocket' : 
              'WebSocket connection for live updates'
            }
            <div className="absolute top-full right-2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-black"></div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConnectionStatus;