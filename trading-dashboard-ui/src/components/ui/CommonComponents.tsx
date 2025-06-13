// src/components/ui/CommonComponents.tsx
// Reusable UI components for the trading dashboard

import React from 'react';

// Loading Spinner Component
export const LoadingSpinner: React.FC<{ size?: 'sm' | 'md' | 'lg'; className?: string }> = ({ 
  size = 'md', 
  className = '' 
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8'
  };

  return (
    <div className={`loading-spinner ${sizeClasses[size]} ${className}`}></div>
  );
};

// Error Message Component
export const ErrorMessage: React.FC<{ 
  message: string; 
  onRetry?: () => void; 
  className?: string 
}> = ({ message, onRetry, className = '' }) => (
  <div className={`card p-4 bg-danger-50 border-danger-200 ${className}`}>
    <div className="flex items-start">
      <svg className="w-5 h-5 text-danger-600 mt-0.5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.982 16.5c-.77.833.192 2.5 1.732 2.5z" />
      </svg>
      <div className="flex-1">
        <h4 className="text-danger-800 font-medium">Error</h4>
        <p className="text-danger-700 text-sm mt-1">{message}</p>
        {onRetry && (
          <button onClick={onRetry} className="btn-danger mt-2 text-sm">
            Retry
          </button>
        )}
      </div>
    </div>
  </div>
);

// Empty State Component
export const EmptyState: React.FC<{ 
  title: string; 
  description?: string; 
  action?: { label: string; onClick: () => void }; 
  icon?: React.ReactNode;
  className?: string;
}> = ({ title, description, action, icon, className = '' }) => (
  <div className={`text-center py-8 ${className}`}>
    {icon || (
      <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    )}
    <h3 className="text-sm font-medium text-gray-900 mb-2">{title}</h3>
    {description && (
      <p className="text-sm text-gray-500 mb-4">{description}</p>
    )}
    {action && (
      <button onClick={action.onClick} className="btn-primary">
        {action.label}
      </button>
    )}
  </div>
);

// Status Badge Component
export const StatusBadge: React.FC<{ 
  status: 'success' | 'error' | 'warning' | 'info' | 'neutral';
  children: React.ReactNode;
  className?: string;
}> = ({ status, children, className = '' }) => {
  const statusClasses = {
    success: 'badge-success',
    error: 'badge-danger',
    warning: 'badge-warning',
    info: 'bg-blue-100 text-blue-800',
    neutral: 'badge-neutral'
  };

  return (
    <span className={`badge ${statusClasses[status]} ${className}`}>
      {children}
    </span>
  );
};

// Tooltip Component
export const Tooltip: React.FC<{ 
  content: string; 
  children: React.ReactNode; 
  position?: 'top' | 'bottom' | 'left' | 'right';
}> = ({ content, children, position = 'top' }) => {
  const positionClasses = {
    top: 'bottom-full left-1/2 transform -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 transform -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 transform -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 transform -translate-y-1/2 ml-2'
  };

  return (
    <div className="relative group">
      {children}
      <div className={`absolute z-10 px-2 py-1 text-xs text-white bg-gray-900 rounded opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 ${positionClasses[position]} pointer-events-none`}>
        {content}
        <div className="absolute w-2 h-2 bg-gray-900 transform rotate-45"></div>
      </div>
    </div>
  );
};

// Confirmation Modal Component
export const ConfirmationModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  type?: 'danger' | 'warning' | 'info';
}> = ({ 
  isOpen, 
  onClose, 
  onConfirm, 
  title, 
  message, 
  confirmLabel = 'Confirm', 
  cancelLabel = 'Cancel',
  type = 'info'
}) => {
  if (!isOpen) return null;

  const typeClasses = {
    danger: 'text-danger-600',
    warning: 'text-warning-600',
    info: 'text-primary-600'
  };

  const buttonClasses = {
    danger: 'btn-danger',
    warning: 'bg-warning-600 text-white hover:bg-warning-700',
    info: 'btn-primary'
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 transition-opacity" onClick={onClose}>
          <div className="absolute inset-0 bg-gray-500 opacity-75"></div>
        </div>

        <div className="inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
          <div className="sm:flex sm:items-start">
            <div className={`mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-${type}-100 sm:mx-0 sm:h-10 sm:w-10`}>
              <svg className={`h-6 w-6 ${typeClasses[type]}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.982 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                {title}
              </h3>
              <div className="mt-2">
                <p className="text-sm text-gray-500">{message}</p>
              </div>
            </div>
          </div>
          <div className="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
            <button
              onClick={onConfirm}
              className={`w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 text-base font-medium text-white focus:outline-none focus:ring-2 focus:ring-offset-2 sm:ml-3 sm:w-auto sm:text-sm ${buttonClasses[type]}`}
            >
              {confirmLabel}
            </button>
            <button
              onClick={onClose}
              className="mt-3 w-full inline-flex justify-center btn-secondary sm:mt-0 sm:w-auto sm:text-sm"
            >
              {cancelLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Price Display Component
export const PriceDisplay: React.FC<{ 
  value: number | string; 
  showSign?: boolean; 
  className?: string 
}> = ({ value, showSign = false, className = '' }) => {
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  const isPositive = numValue >= 0;
  
  const colorClass = isPositive ? 'text-success-600' : 'text-danger-600';
  const sign = showSign ? (isPositive ? '+' : '') : '';
  
  return (
    <span className={`font-semibold ${colorClass} ${className}`}>
      {sign}₹{Math.abs(numValue).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
    </span>
  );
};

// Quantity Input Component
export const QuantityInput: React.FC<{
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  className?: string;
}> = ({ value, onChange, min = 0, max, step = 1, disabled = false, className = '' }) => {
  const handleIncrement = () => {
    const newValue = value + step;
    if (!max || newValue <= max) {
      onChange(newValue);
    }
  };

  const handleDecrement = () => {
    const newValue = value - step;
    if (newValue >= min) {
      onChange(newValue);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = parseInt(e.target.value) || 0;
    if (newValue >= min && (!max || newValue <= max)) {
      onChange(newValue);
    }
  };

  return (
    <div className={`flex items-center ${className}`}>
      <button
        onClick={handleDecrement}
        disabled={disabled || value <= min}
        className="px-2 py-1 border border-gray-300 rounded-l-md bg-gray-50 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
        </svg>
      </button>
      
      <input
        type="number"
        value={value}
        onChange={handleInputChange}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
        className="w-20 px-2 py-1 border-t border-b border-gray-300 text-center focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
      />
      
      <button
        onClick={handleIncrement}
        disabled={disabled || (max !== undefined && value >= max)}
        className="px-2 py-1 border border-gray-300 rounded-r-md bg-gray-50 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
        </svg>
      </button>
    </div>
  );
};