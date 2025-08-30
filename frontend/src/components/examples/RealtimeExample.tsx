'use client';

import React, { useState } from 'react';
import { useRealtimeChannel } from '@/hooks/use-realtime';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';

interface ChatMessage {
  id: string;
  text: string;
  timestamp: Date;
  sender: string;
}

export function RealtimeExample() {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [channelName, setChannelName] = useState('room:general');

  // Use the realtime hook for a specific channel
  const { isConnected, isSubscribing, error, sendMessage } = useRealtimeChannel(
    channelName,
    {
      onMessage: (realtimeMessage) => {
        if (realtimeMessage.event === 'chat-message') {
          const newMessage: ChatMessage = {
            id: Date.now().toString(),
            text: realtimeMessage.payload.text,
            timestamp: new Date(),
            sender: realtimeMessage.payload.sender || 'Anonymous'
          };
          setMessages(prev => [...prev, newMessage]);
        }
      },
      onError: (err) => {
        console.error('Realtime error:', err);
      },
      onJoin: () => {
        console.log('Joined channel:', channelName);
      },
      onLeave: () => {
        console.log('Left channel:', channelName);
      }
    }
  );

  const handleSendMessage = async () => {
    if (!message.trim()) return;

    try {
      await sendMessage(channelName, {
        event: 'chat-message',
        payload: {
          text: message,
          sender: 'You',
          timestamp: new Date().toISOString()
        }
      });

      // Add message to local state
      const newMessage: ChatMessage = {
        id: Date.now().toString(),
        text: message,
        timestamp: new Date(),
        sender: 'You'
      };
      setMessages(prev => [...prev, newMessage]);
      setMessage('');
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Supabase Realtime v2 Example</CardTitle>
          <CardDescription>
            This demonstrates the correct implementation of Supabase Realtime v2 API
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Connection Status */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-sm font-medium">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            
            {isSubscribing && (
              <Badge variant="secondary">Connecting...</Badge>
            )}
            
            {error && (
              <Badge variant="destructive">Error: {error}</Badge>
            )}
          </div>

          {/* Channel Selection */}
          <div className="flex items-center gap-2">
            <label htmlFor="channel" className="text-sm font-medium">
              Channel:
            </label>
            <Input
              id="channel"
              value={channelName}
              onChange={(e) => setChannelName(e.target.value)}
              placeholder="Enter channel name"
              className="w-64"
            />
          </div>

          {/* Messages Display */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Messages</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-96 w-full">
                <div className="space-y-2">
                  {messages.length === 0 ? (
                    <p className="text-muted-foreground text-center py-8">
                      No messages yet. Start the conversation!
                    </p>
                  ) : (
                    messages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`p-3 rounded-lg ${
                          msg.sender === 'You'
                            ? 'bg-blue-100 dark:bg-blue-900 ml-8'
                            : 'bg-gray-100 dark:bg-gray-800 mr-8'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-sm">{msg.sender}</span>
                          <span className="text-xs text-muted-foreground">
                            {msg.timestamp.toLocaleTimeString()}
                          </span>
                        </div>
                        <p className="text-sm">{msg.text}</p>
                      </div>
                    ))
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          {/* Message Input */}
          <div className="flex gap-2">
            <Input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              disabled={!isConnected}
            />
            <Button
              onClick={handleSendMessage}
              disabled={!isConnected || !message.trim()}
            >
              Send
            </Button>
          </div>

          {/* Usage Instructions */}
          <Card className="bg-muted/50">
            <CardHeader>
              <CardTitle className="text-base">How it works</CardTitle>
            </CardHeader>
            <CardContent className="text-sm space-y-2">
              <p>
                • <strong>Authentication:</strong> JWT tokens are automatically forwarded to Realtime
              </p>
              <p>
                • <strong>Channels:</strong> Subscribe to any channel name (e.g., "room:general")
              </p>
              <p>
                • <strong>Messages:</strong> Broadcast messages to all subscribers on the channel
              </p>
              <p>
                • <strong>Cleanup:</strong> Automatic cleanup when components unmount
              </p>
            </CardContent>
          </Card>
        </CardContent>
      </Card>
    </div>
  );
}

