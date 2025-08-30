import { createClient } from './client';
import { RealtimeChannel } from '@supabase/supabase-js';

export interface RealtimeMessage {
  type: 'broadcast';
  event: string;
  payload: any;
}

export interface RealtimeConfig {
  channelName: string;
  onMessage?: (message: RealtimeMessage) => void;
  onError?: (error: any) => void;
  onJoin?: () => void;
  onLeave?: () => void;
}

export class RealtimeService {
  private supabase = createClient();
  private channels = new Map<string, RealtimeChannel>();
  private authListener: any;

  constructor() {
    this.setupAuthListener();
  }

  /**
   * Set up authentication listener to forward JWT tokens to Realtime
   * This is crucial for RLS and custom JWT checks to work properly
   */
  private setupAuthListener() {
    this.authListener = this.supabase.auth.onAuthStateChange((event, session) => {
      const token = session?.access_token;
      if (token) {
        // Forward the latest JWT to Realtime after login/refresh
        this.supabase.realtime.setAuth(token);
        console.log('🔐 Realtime authenticated with JWT');
      } else {
        // Clear auth when no session
        this.supabase.realtime.setAuth(null);
        console.log('🔓 Realtime auth cleared');
      }
    });
  }

  /**
   * Subscribe to a realtime channel
   * @param config Configuration for the channel
   * @returns Promise that resolves when subscription is ready
   */
  async subscribe(config: RealtimeConfig): Promise<RealtimeChannel> {
    const { channelName, onMessage, onError, onJoin, onLeave } = config;

    // Check if channel already exists
    if (this.channels.has(channelName)) {
      console.log(`📡 Channel ${channelName} already exists, returning existing channel`);
      return this.channels.get(channelName)!;
    }

    try {
      console.log(`📡 Creating channel: ${channelName}`);
      
      // Create the channel
      const channel = this.supabase.channel(channelName);
      
      // Set up event handlers
      if (onMessage) {
        channel.on('broadcast', { event: '*' }, (payload) => {
          console.log(`📨 Received message on ${channelName}:`, payload);
          onMessage({
            type: 'broadcast',
            event: payload.event,
            payload: payload.payload
          });
        });
      }

      if (onError) {
        channel.on('system', { event: 'error' }, (payload) => {
          console.error(`❌ Channel error on ${channelName}:`, payload);
          onError(payload);
        });
      }

      if (onJoin) {
        channel.on('system', { event: 'join' }, () => {
          console.log(`✅ Joined channel: ${channelName}`);
          onJoin();
        });
      }

      if (onLeave) {
        channel.on('system', { event: 'leave' }, () => {
          console.log(`👋 Left channel: ${channelName}`);
          onLeave();
        });
      }

      // Subscribe to the channel
      await channel.subscribe();

      console.log(`✅ Successfully subscribed to channel: ${channelName}`);
      
      // Store the channel
      this.channels.set(channelName, channel);
      
      return channel;
    } catch (error) {
      console.error(`❌ Failed to subscribe to channel ${channelName}:`, error);
      throw error;
    }
  }

  /**
   * Send a message to a channel
   * @param channelName Name of the channel to send to
   * @param message Message to send
   * @returns Promise that resolves when message is sent
   */
  async sendMessage(channelName: string, message: RealtimeMessage): Promise<void> {
    const channel = this.channels.get(channelName);
    
    if (!channel) {
      throw new Error(`Channel ${channelName} not found. Subscribe to it first.`);
    }

    try {
      await channel.send(message);
      console.log(`📤 Message sent to ${channelName}:`, message);
    } catch (error) {
      console.error(`❌ Failed to send message to ${channelName}:`, error);
      throw error;
    }
  }

  /**
   * Unsubscribe from a specific channel
   * @param channelName Name of the channel to unsubscribe from
   */
  async unsubscribe(channelName: string): Promise<void> {
    const channel = this.channels.get(channelName);
    
    if (!channel) {
      console.log(`📡 Channel ${channelName} not found, nothing to unsubscribe from`);
      return;
    }

    try {
      await channel.unsubscribe();
      this.channels.delete(channelName);
      console.log(`📡 Unsubscribed from channel: ${channelName}`);
    } catch (error) {
      console.error(`❌ Failed to unsubscribe from ${channelName}:`, error);
      throw error;
    }
  }

  /**
   * Unsubscribe from all channels
   */
  async unsubscribeAll(): Promise<void> {
    const channelNames = Array.from(this.channels.keys());
    
    for (const channelName of channelNames) {
      await this.unsubscribe(channelName);
    }
    
    console.log('📡 Unsubscribed from all channels');
  }

  /**
   * Get the current status of a channel
   * @param channelName Name of the channel
   * @returns Channel status or null if not found
   */
  getChannelStatus(channelName: string): string | null {
    const channel = this.channels.get(channelName);
    // In v2, we can check if the channel exists and is subscribed
    return channel ? 'SUBSCRIBED' : null;
  }

  /**
   * Get all active channel names
   * @returns Array of active channel names
   */
  getActiveChannels(): string[] {
    return Array.from(this.channels.keys());
  }

  /**
   * Clean up resources
   */
  destroy(): void {
    this.unsubscribeAll();
    
    if (this.authListener) {
      this.authListener.data?.subscription?.unsubscribe();
    }
    
    console.log('🧹 RealtimeService destroyed');
  }
}

// Export a singleton instance
export const realtimeService = new RealtimeService();

// Export convenience functions for common use cases
export const createChannel = (config: RealtimeConfig) => realtimeService.subscribe(config);
export const sendMessage = (channelName: string, message: RealtimeMessage) => realtimeService.sendMessage(channelName, message);
export const unsubscribeFromChannel = (channelName: string) => realtimeService.unsubscribe(channelName);
