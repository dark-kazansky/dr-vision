/**
 * useNotification Composable
 * 
 * Manages toast notifications for the application.
 */

export interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
  duration?: number
}

export function useNotification() {
  const notifications = useState<Notification[]>('notifications', () => [])
  
  const addNotification = (
    type: Notification['type'],
    message: string,
    duration: number = 3000
  ) => {
    const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    
    const notification: Notification = {
      id,
      type,
      message,
      duration
    }
    
    notifications.value.push(notification)
    
    // Auto-remove after duration
    if (duration > 0) {
      setTimeout(() => {
        removeNotification(id)
      }, duration)
    }
    
    return id
  }
  
  const removeNotification = (id: string) => {
    notifications.value = notifications.value.filter(n => n.id !== id)
  }
  
  const success = (message: string, duration?: number) => {
    return addNotification('success', message, duration)
  }
  
  const error = (message: string, duration?: number) => {
    return addNotification('error', message, duration)
  }
  
  const warning = (message: string, duration?: number) => {
    return addNotification('warning', message, duration)
  }
  
  const info = (message: string, duration?: number) => {
    return addNotification('info', message, duration)
  }
  
  return {
    notifications,
    addNotification,
    removeNotification,
    success,
    error,
    warning,
    info
  }
}
