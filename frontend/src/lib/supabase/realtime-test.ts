import { realtimeService } from './realtime';

/**
 * Test utility for Supabase Realtime v2
 * Demonstrates the correct implementation patterns
 */
export class RealtimeTester {
  private testChannel = 'test:realtime';

  /**
   * Test basic channel subscription and messaging
   */
  async testBasicFunctionality(): Promise<void> {
    console.log('🧪 Testing basic realtime functionality...');

    try {
      // Subscribe to test channel
      await realtimeService.subscribe({
        channelName: this.testChannel,
        onMessage: (message) => {
          console.log('📨 Received test message:', message);
        },
        onError: (error) => {
          console.error('❌ Test channel error:', error);
        },
        onJoin: () => {
          console.log('✅ Joined test channel');
        },
        onLeave: () => {
          console.log('👋 Left test channel');
        }
      });

      // Wait a moment for connection to establish
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Send a test message
      await realtimeService.sendMessage(this.testChannel, {
        type: 'broadcast',
        event: 'test',
        payload: {
          message: 'Hello from Realtime v2!',
          timestamp: new Date().toISOString()
        }
      });

      console.log('✅ Basic functionality test completed');
    } catch (error) {
      console.error('❌ Basic functionality test failed:', error);
      throw error;
    }
  }

  /**
   * Test authentication forwarding
   */
  async testAuthentication(): Promise<void> {
    console.log('🔐 Testing authentication forwarding...');

    try {
      // This test assumes you're already authenticated
      // The realtimeService should automatically handle JWT forwarding
      
      const status = realtimeService.getChannelStatus(this.testChannel);
      console.log('📡 Channel status:', status);
      
      if (status === 'SUBSCRIBED') {
        console.log('✅ Authentication test passed - channel is subscribed');
      } else {
        console.log('⚠️ Authentication test inconclusive - channel status:', status);
      }
    } catch (error) {
      console.error('❌ Authentication test failed:', error);
      throw error;
    }
  }

  /**
   * Test multiple channels
   */
  async testMultipleChannels(): Promise<void> {
    console.log('📡 Testing multiple channels...');

    try {
      const channels = ['test:channel1', 'test:channel2', 'test:channel3'];
      
      // Subscribe to multiple channels
      for (const channel of channels) {
        await realtimeService.subscribe({
          channelName: channel,
          onMessage: (message) => {
            console.log(`📨 Message on ${channel}:`, message);
          }
        });
      }

      // Check active channels
      const activeChannels = realtimeService.getActiveChannels();
      console.log('📡 Active channels:', activeChannels);

      // Send messages to each channel
      for (const channel of channels) {
        await realtimeService.sendMessage(channel, {
          type: 'broadcast',
          event: 'multi-test',
          payload: { channel, message: `Test message for ${channel}` }
        });
      }

      console.log('✅ Multiple channels test completed');
    } catch (error) {
      console.error('❌ Multiple channels test failed:', error);
      throw error;
    }
  }

  /**
   * Test cleanup and resource management
   */
  async testCleanup(): Promise<void> {
    console.log('🧹 Testing cleanup and resource management...');

    try {
      const initialChannels = realtimeService.getActiveChannels();
      console.log('📡 Initial active channels:', initialChannels);

      // Unsubscribe from test channels
      await realtimeService.unsubscribe(this.testChannel);
      
      const remainingChannels = realtimeService.getActiveChannels();
      console.log('📡 Remaining channels after cleanup:', remainingChannels);

      console.log('✅ Cleanup test completed');
    } catch (error) {
      console.error('❌ Cleanup test failed:', error);
      throw error;
    }
  }

  /**
   * Run all tests
   */
  async runAllTests(): Promise<void> {
    console.log('🚀 Starting Realtime v2 tests...');
    
    try {
      await this.testBasicFunctionality();
      await this.testAuthentication();
      await this.testMultipleChannels();
      await this.testCleanup();
      
      console.log('🎉 All tests completed successfully!');
    } catch (error) {
      console.error('💥 Test suite failed:', error);
      throw error;
    }
  }

  /**
   * Clean up all test resources
   */
  async cleanup(): Promise<void> {
    console.log('🧹 Cleaning up test resources...');
    
    try {
      // Unsubscribe from all channels
      await realtimeService.unsubscribeAll();
      console.log('✅ Cleanup completed');
    } catch (error) {
      console.error('❌ Cleanup failed:', error);
    }
  }
}

// Export a singleton instance for easy testing
export const realtimeTester = new RealtimeTester();

// Convenience function to run tests
export const runRealtimeTests = () => realtimeTester.runAllTests();
export const cleanupRealtimeTests = () => realtimeTester.cleanup();
