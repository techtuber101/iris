import { useEffect, useRef, useCallback, useState } from 'react';
import { realtimeService, RealtimeConfig, RealtimeMessage } from '@/lib/supabase/realtime';

export interface UseRealtimeOptions extends Omit<RealtimeConfig, 'channelName'> {
  autoSubscribe?: boolean;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

export interface UseRealtimeReturn {
  isConnected: boolean;
  isSubscribing: boolean;
  error: string | null;
  subscribe: (channelName: string) => Promise<void>;
  unsubscribe: (channelName: string) => Promise<void>;
  sendMessage: (channelName: string, message: Omit<RealtimeMessage, 'type'>) => Promise<void>;
  activeChannels: string[];
}

/**
 * React hook for managing Supabase Realtime connections
 * Automatically handles cleanup and provides a clean API
 */
export function useRealtime(options: UseRealtimeOptions = {}): UseRealtimeReturn {
  const {
    onMessage,
    onError,
    onJoin,
    onLeave,
    onConnect,
    onDisconnect,
    autoSubscribe = false
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isSubscribing, setIsSubscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeChannels, setActiveChannels] = useState<string[]>([]);
  
  const channelsRef = useRef<Set<string>>(new Set());
  const isMountedRef = useRef(true);

  // Subscribe to a channel
  const subscribe = useCallback(async (channelName: string) => {
    if (!isMountedRef.current) return;
    
    try {
      setIsSubscribing(true);
      setError(null);
      
      await realtimeService.subscribe({
        channelName,
        onMessage,
        onError: (err) => {
          setError(err.message || 'Channel error');
          onError?.(err);
        },
        onJoin: () => {
          setIsConnected(true);
          onJoin?.();
        },
        onLeave: () => {
          setIsConnected(false);
          onLeave?.();
        }
      });
      
      channelsRef.current.add(channelName);
      setActiveChannels(Array.from(channelsRef.current));
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to subscribe';
      setError(errorMessage);
      console.error('Failed to subscribe to channel:', err);
    } finally {
      if (isMountedRef.current) {
        setIsSubscribing(false);
      }
    }
  }, [onMessage, onError, onJoin, onLeave]);

  // Unsubscribe from a channel
  const unsubscribe = useCallback(async (channelName: string) => {
    if (!isMountedRef.current) return;
    
    try {
      await realtimeService.unsubscribe(channelName);
      channelsRef.current.delete(channelName);
      setActiveChannels(Array.from(channelsRef.current));
      
      // Update connection status if no channels are active
      if (channelsRef.current.size === 0) {
        setIsConnected(false);
      }
    } catch (err) {
      console.error('Failed to unsubscribe from channel:', err);
    }
  }, []);

  // Send a message to a channel
  const sendMessage = useCallback(async (channelName: string, message: Omit<RealtimeMessage, 'type'>) => {
    if (!isMountedRef.current) return;
    
    try {
      await realtimeService.sendMessage(channelName, {
        type: 'broadcast',
        ...message
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to send message';
      setError(errorMessage);
      console.error('Failed to send message:', err);
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      // Cleanup will be handled by the realtimeService singleton
    };
  }, []);

  return {
    isConnected,
    isSubscribing,
    error,
    subscribe,
    unsubscribe,
    sendMessage,
    activeChannels
  };
}

/**
 * Simplified hook for a single channel
 */
export function useRealtimeChannel(
  channelName: string,
  options: Omit<UseRealtimeOptions, 'autoSubscribe'> = {}
): UseRealtimeReturn {
  const realtime = useRealtime(options);
  
  useEffect(() => {
    realtime.subscribe(channelName);
    
    return () => {
      realtime.unsubscribe(channelName);
    };
  }, [channelName, realtime.subscribe, realtime.unsubscribe]);

  return realtime;
}

