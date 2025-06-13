// File: /src/components/ClientsTable.tsx

import React from 'react';
import { usePortfolioStore, Client } from '../store/portfolioStore';

interface ClientsTableProps {
  clients: Client[];
}

const ClientsTable: React.FC<ClientsTableProps> = ({ clients }) => {
  const { updateClientQuantity } = usePortfolioStore();

  const handleQuantityChange = (clientId: string, quantity: number) => {
    updateClientQuantity(clientId, Math.max(0, quantity));
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2
    }).format(amount);
  };

  const formatPercentage = (percentage: number) => {
    return `${percentage >= 0 ? '+' : ''}${percentage.toFixed(2)}%`;
  };

  const getChangeIndicator = (change: number) => {
    if (change > 0) return '📈';
    if (change < 0) return '📉';
    return '➖';
  };

  const getPLColorClass = (pl: number) => {
    if (pl > 0) return 'text-green-600';
    if (pl < 0) return 'text-red-600';
    return 'text-gray-600';
  };

  const isRecentlyUpdated = (lastUpdated?: string) => {
    if (!lastUpdated) return false;
    const updateTime = new Date(lastUpdated);
    const now = new Date();
    return (now.getTime() - updateTime.getTime()) < 10000; // Within 10 seconds
  };

  if (clients.length === 0) {
    return (
      <div className="p-12 text-center text-gray-500">
        <div className="text-4xl mb-4">📊</div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Clients Found</h3>
        <p>No client data is available. Please check your backend connection.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Client
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Available Funds
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Current P&L
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Day Change
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Portfolio Value
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Quantity
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Last Updated
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {clients.map((client) => (
            <tr 
              key={client.id} 
              className={`hover:bg-gray-50 transition-colors ${
                isRecentlyUpdated(client.lastUpdated) ? 'bg-blue-50 animate-pulse' : ''
              }`}
            >
              {/* Client Info */}
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center">
                  <div className="flex-shrink-0 h-10 w-10">
                    <div className="h-10 w-10 rounded-full bg-blue-500 flex items-center justify-center text-white font-medium">
                      {client.client_name.charAt(0).toUpperCase()}
                    </div>
                  </div>
                  <div className="ml-4">
                    <div className="text-sm font-medium text-gray-900">
                      {client.client_name}
                    </div>
                    <div className="text-sm text-gray-500">
                      {client.client_code}
                    </div>
                  </div>
                </div>
              </td>

              {/* Available Funds */}
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm font-medium text-gray-900">
                  {formatCurrency(client.available_funds)}
                </div>
              </td>

              {/* Current P&L */}
              <td className="px-6 py-4 whitespace-nowrap">
                <div className={`text-sm font-bold ${getPLColorClass(client.current_pl)}`}>
                  {formatCurrency(client.current_pl)}
                  {client.change !== undefined && (
                    <div className="text-xs">
                      {getChangeIndicator(client.change)} {formatCurrency(Math.abs(client.change))}
                    </div>
                  )}
                </div>
              </td>

              {/* Day Change */}
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm">
                  {client.day_pl !== undefined ? (
                    <span className={getPLColorClass(client.day_pl)}>
                      {formatCurrency(client.day_pl)}
                    </span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                  {client.percentageChange !== undefined && (
                    <div className={`text-xs ${getPLColorClass(client.percentageChange)}`}>
                      {formatPercentage(client.percentageChange)}
                    </div>
                  )}
                </div>
              </td>

              {/* Portfolio Value */}
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-gray-900">
                  {client.portfolio_value !== undefined ? 
                    formatCurrency(client.portfolio_value) : 
                    <span className="text-gray-400">-</span>
                  }
                </div>
              </td>

              {/* Quantity Input */}
              <td className="px-6 py-4 whitespace-nowrap">
                <input
                  type="number"
                  min="0"
                  step="1"
                  value={client.quantity || 0}
                  onChange={(e) => handleQuantityChange(client.id, parseInt(e.target.value) || 0)}
                  className="w-20 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="0"
                />
              </td>

              {/* Last Updated */}
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-xs text-gray-500">
                  {client.lastUpdated ? (
                    <>
                      {new Date(client.lastUpdated).toLocaleTimeString()}
                      {isRecentlyUpdated(client.lastUpdated) && (
                        <div className="text-blue-600 font-medium">🔄 Live</div>
                      )}
                    </>
                  ) : (
                    'Never'
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Summary Row */}
      <div className="bg-gray-50 px-6 py-4 border-t border-gray-200">
        <div className="flex justify-between items-center text-sm">
          <div className="text-gray-600">
            Total Clients: <span className="font-medium">{clients.length}</span>
          </div>
          <div className="text-gray-600">
            Active Orders: <span className="font-medium">
              {clients.filter(client => (client.quantity || 0) > 0).length}
            </span>
          </div>
          <div className="text-gray-600">
            Total P&L: <span className={`font-bold ${getPLColorClass(
              clients.reduce((sum, client) => sum + client.current_pl, 0)
            )}`}>
              {formatCurrency(clients.reduce((sum, client) => sum + client.current_pl, 0))}
            </span>
          </div>
          <div className="text-gray-600">
            Total Quantity: <span className="font-medium">
              {clients.reduce((sum, client) => sum + (client.quantity || 0), 0)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClientsTable;