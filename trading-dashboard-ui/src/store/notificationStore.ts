// src/store/notificationStore.ts
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

// Notification types
export type NotificationType = 'success' | 'error' | 'warning' | 'info';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message?: string;
  duration?: number;
  timestamp: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface NotificationStore {
  notifications: Notification[];
  
  // Actions
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearAll: () => void;
  
  // Convenience methods
  success: (title: string, message?: string, duration?: number) => void;
  error: (title: string, message?: string, duration?: number) => void;
  warning: (title: string, message?: string, duration?: number) => void;
  info: (title: string, message?: string, duration?: number) => void;
}

// Generate unique ID for notifications
const generateId = () => `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

export const useNotificationStore = create<NotificationStore>()(
  devtools(
    (set, get) => ({
      notifications: [],

      addNotification: (notification) => {
        const id = generateId();
        const newNotification: Notification = {
          ...notification,
          id,
          timestamp: Date.now(),
          duration: notification.duration ?? 5000, // Default 5 seconds
        };

        set((state) => ({
          notifications: [...state.notifications, newNotification],
        }));

        // Auto-remove notification after duration
        if (newNotification.duration && newNotification.duration > 0) {
          setTimeout(() => {
            get().removeNotification(id);
          }, newNotification.duration);
        }
      },

      removeNotification: (id) => {
        set((state) => ({
          notifications: state.notifications.filter(n => n.id !== id),
        }));
      },

      clearAll: () => {
        set({ notifications: [] });
      },

      // Convenience methods
      success: (title, message, duration) => {
        get().addNotification({
          type: 'success',
          title,
          message,
          duration,
        });
      },

      error: (title, message, duration = 8000) => { // Errors stay longer by default
        get().addNotification({
          type: 'error',
          title,
          message,
          duration,
        });
      },

      warning: (title, message, duration) => {
        get().addNotification({
          type: 'warning',
          title,
          message,
          duration,
        });
      },

      info: (title, message, duration) => {
        get().addNotification({
          type: 'info',
          title,
          message,
          duration,
        });
      },
    }),
    {
      name: 'notification-store',
    }
  )
);

// Selector hooks
export const useNotifications = () => useNotificationStore((state) => state.notifications);

// Custom hook for notification actions
export const useNotify = () => {
  const { success, error, warning, info } = useNotificationStore();
  
  return {
    success,
    error,
    warning,
    info,
    
    // Trading-specific notifications
    orderSuccess: (message: string) => success('Order Executed', message),
    orderError: (message: string) => error('Order Failed', message),
    portfolioUpdate: (message: string) => info('Portfolio Updated', message),
    connectionError: () => error('Connection Error', 'Unable to connect to trading server'),
    
    // Batch operation notifications
    batchSuccess: (successCount: number, totalCount: number) => 
      success('Batch Operation Complete', `${successCount}/${totalCount} orders executed successfully`),
    
    batchPartialSuccess: (successCount: number, totalCount: number) => 
      warning('Batch Operation Partial Success', `${successCount}/${totalCount} orders executed successfully`),
    
    batchFailure: (message: string) => 
      error('Batch Operation Failed', message),
  };
};

export default useNotificationStore;