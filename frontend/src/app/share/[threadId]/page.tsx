'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  Play, 
  Pause, 
  SkipBack, 
  SkipForward, 
  RotateCcw,
  Share2,
  ExternalLink,
  Clock,
  MessageSquare,
  User,
  Bot,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { Markdown } from '@/components/ui/markdown';
import { getMessages, getProject, getThread, getSharedThread, Project, Message as BaseApiMessageType } from '@/lib/api';

// Extend the base Message type with the expected database fields
interface ApiMessageType extends BaseApiMessageType {
  message_id?: string;
  thread_id?: string;
  is_llm_message?: boolean;
  metadata?: string;
  created_at?: string;
  updated_at?: string;
}

interface SharedThread {
  id: string;
  title: string;
  description?: string;
  messageCount: number;
  createdAt: string;
  isPublic: boolean;
  allowComments: boolean;
  messages: SharedMessage[];
}

interface SharedMessage {
  id: string;
  type: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  timestamp: string;
  metadata?: any;
}

interface ThreadParams {
  threadId: string;
}

export default function SharePage({ params }: { params: Promise<ThreadParams> }) {
  const unwrappedParams = React.use(params);
  const threadId = unwrappedParams.threadId;
  
  const router = useRouter();
  const [thread, setThread] = useState<SharedThread | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Playback state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentMessageIndex, setCurrentMessageIndex] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [streamingText, setStreamingText] = useState('');
  const [isStreamingComplete, setIsStreamingComplete] = useState(false);
  
  const playbackIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const streamingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Load thread data from API
  useEffect(() => {
    const loadThread = async () => {
      setIsLoading(true);
      try {
        // Fetch shared thread data using public ID
        const sharedData = await getSharedThread(threadId);
        
        if (sharedData && sharedData.thread && sharedData.messages) {
          // Convert API messages to SharedMessage format
          const sharedMessages: SharedMessage[] = (sharedData.messages || [])
            .filter((msg: ApiMessageType) => msg.type !== 'status')
            .map((msg: ApiMessageType) => ({
              id: msg.message_id || Math.random().toString(),
              type: (msg.type as SharedMessage['type']) || 'assistant',
              content: msg.content || '',
              timestamp: msg.created_at || new Date().toISOString(),
              metadata: msg.metadata ? JSON.parse(msg.metadata) : undefined
            }));
          
          const sharedThread: SharedThread = {
            id: sharedData.thread.thread_id,
            title: sharedData.share.title || sharedData.project?.name || 'Shared Chat',
            description: sharedData.share.description || sharedData.project?.description,
            messageCount: sharedMessages.length,
            createdAt: sharedData.thread.created_at,
            isPublic: sharedData.share.is_public,
            allowComments: sharedData.share.allow_comments,
            messages: sharedMessages
          };
          
          setThread(sharedThread);
          setProject(sharedData.project || null);
        } else {
          setError('No chat found');
        }
      } catch (err) {
        console.error('Error loading shared thread:', err);
        setError(err instanceof Error ? err.message : 'Failed to load chat');
      } finally {
        setIsLoading(false);
      }
    };
    
    loadThread();
  }, [threadId]);
  
  // Playback controls
  const startPlayback = useCallback(() => {
    if (!thread || isPlaying) return;
    
    setIsPlaying(true);
    
    const playNextMessage = () => {
      if (currentMessageIndex < thread.messages.length) {
        const message = thread.messages[currentMessageIndex];
        
        // Start streaming the message
        setStreamingText('');
        setIsStreamingComplete(false);
        
        let charIndex = 0;
        const streamMessage = () => {
          if (charIndex < message.content.length) {
            setStreamingText(message.content.substring(0, charIndex + 1));
            charIndex++;
          } else {
            setIsStreamingComplete(true);
            clearInterval(streamingIntervalRef.current!);
            
            // Move to next message after a delay
            setTimeout(() => {
              setCurrentMessageIndex(prev => prev + 1);
              setStreamingText('');
              setIsStreamingComplete(false);
            }, 1000 / playbackSpeed);
          }
        };
        
        streamingIntervalRef.current = setInterval(streamMessage, 50 / playbackSpeed);
      } else {
        // Playback complete
        setIsPlaying(false);
        setIsStreamingComplete(true);
      }
    };
    
    playNextMessage();
  }, [thread, isPlaying, currentMessageIndex, playbackSpeed]);
  
  const pausePlayback = useCallback(() => {
    setIsPlaying(false);
    if (streamingIntervalRef.current) {
      clearInterval(streamingIntervalRef.current);
    }
  }, []);
  
  const resetPlayback = useCallback(() => {
    setIsPlaying(false);
    setCurrentMessageIndex(0);
    setStreamingText('');
    setIsStreamingComplete(false);
    if (streamingIntervalRef.current) {
      clearInterval(streamingIntervalRef.current);
    }
  }, []);
  
  const skipToMessage = useCallback((index: number) => {
    if (!thread) return;
    
    pausePlayback();
    setCurrentMessageIndex(Math.max(0, Math.min(index, thread.messages.length - 1)));
    setStreamingText('');
    setIsStreamingComplete(false);
  }, [thread, pausePlayback]);
  
  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentMessageIndex, streamingText]);
  
  // Cleanup intervals
  useEffect(() => {
    return () => {
      if (streamingIntervalRef.current) {
        clearInterval(streamingIntervalRef.current);
      }
      if (playbackIntervalRef.current) {
        clearInterval(playbackIntervalRef.current);
      }
    };
  }, []);
  
  const copyShareUrl = () => {
    navigator.clipboard.writeText(window.location.href);
    toast.success('Share URL copied to clipboard!');
  };
  
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto p-6">
          <div className="space-y-4">
            <Skeleton className="h-8 w-1/3" />
            <Skeleton className="h-4 w-2/3" />
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="space-y-2">
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-16 w-full" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }
  
  if (error || !thread) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Chat Not Found</h1>
          <p className="text-gray-600 mb-4">
            {error || 'The shared chat you\'re looking for doesn\'t exist or has been removed.'}
          </p>
          <Button onClick={() => router.push('/')}>
            Go Home
          </Button>
        </div>
      </div>
    );
  }
  
  // Attachment parser (shared with main agents view semantics)
  const parseAttachments = (text: string): { clean: string; paths: string[] } => {
    const matches = text.match(/\[Uploaded File: (.*?)\]/g) || [];
    const paths = matches
      .map(m => (m.match(/\[Uploaded File: (.*?)\]/) || [])[1])
      .filter(Boolean) as string[];
    const clean = text.replace(/\[Uploaded File: .*?\]/g, '').trim();
    return { clean, paths };
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-xl font-semibold text-gray-900 truncate">
                  {thread.title}
                </h1>
                <Badge variant="outline" className="shrink-0">
                  <MessageSquare className="h-3 w-3 mr-1" />
                  {thread.messageCount} messages
                </Badge>
              </div>
              {thread.description && (
                <p className="text-sm text-gray-600 line-clamp-2">
                  {thread.description}
                </p>
              )}
            </div>
            
            <div className="flex items-center gap-2 ml-4">
              <Button
                variant="outline"
                size="sm"
                onClick={copyShareUrl}
                className="gap-2"
              >
                <Share2 className="h-4 w-4" />
                Share
              </Button>
            </div>
          </div>
        </div>
      </div>
      
      {/* Playback Controls */}
      <div className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={resetPlayback}
                  disabled={currentMessageIndex === 0 && !isPlaying}
                >
                  <RotateCcw className="h-4 w-4" />
                </Button>
                
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => skipToMessage(currentMessageIndex - 1)}
                  disabled={currentMessageIndex === 0}
                >
                  <SkipBack className="h-4 w-4" />
                </Button>
                
                <Button
                  size="sm"
                  onClick={isPlaying ? pausePlayback : startPlayback}
                  disabled={currentMessageIndex >= thread.messages.length && isStreamingComplete}
                >
                  {isPlaying ? (
                    <Pause className="h-4 w-4" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}
                </Button>
                
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => skipToMessage(currentMessageIndex + 1)}
                  disabled={currentMessageIndex >= thread.messages.length - 1}
                >
                  <SkipForward className="h-4 w-4" />
                </Button>
              </div>
              
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">Speed:</span>
                <select
                  value={playbackSpeed}
                  onChange={(e) => setPlaybackSpeed(Number(e.target.value))}
                  className="text-sm border rounded px-2 py-1"
                >
                  <option value={0.5}>0.5x</option>
                  <option value={1}>1x</option>
                  <option value={1.5}>1.5x</option>
                  <option value={2}>2x</option>
                </select>
              </div>
            </div>
            
            <div className="text-sm text-gray-600">
              Message {Math.min(currentMessageIndex + 1, thread.messages.length)} of {thread.messages.length}
            </div>
          </div>
        </div>
      </div>
      
      {/* Messages (includes user, assistant, and tool events for replay) */}
      <div className="max-w-4xl mx-auto p-6">
        <div className="space-y-6">
          {thread.messages.slice(0, currentMessageIndex + 1).map((message, index) => {
            const isCurrentMessage = index === currentMessageIndex;
            const shouldShowStreaming = isCurrentMessage && isPlaying && !isStreamingComplete;
            const { clean, paths } = parseAttachments(message.content || '');
            const displayContent = shouldShowStreaming ? streamingText : clean;
            
            return (
              <div
                key={message.id}
                className={cn(
                  'flex gap-4 p-4 rounded-lg transition-all duration-200',
                  message.type === 'user'
                    ? 'bg-blue-50 ml-12'
                    : message.type === 'tool'
                      ? 'bg-amber-50 border shadow-sm'
                      : 'bg-white border shadow-sm mr-12',
                  isCurrentMessage && isPlaying && 'ring-2 ring-blue-200'
                )}
              >
                <div className="flex-shrink-0">
                  <div className={cn(
                    'w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium',
                    message.type === 'user'
                      ? 'bg-blue-600'
                      : message.type === 'tool'
                        ? 'bg-amber-600'
                        : 'bg-gray-700'
                  )}>
                    {message.type === 'user' ? (
                      <User className="h-4 w-4" />
                    ) : message.type === 'tool' ? (
                      <span className="text-[10px] font-semibold">TOOL</span>
                    ) : (
                      <Bot className="h-4 w-4" />
                    )}
                  </div>
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-medium text-gray-900">
                      {message.type === 'user' ? 'You' : message.type === 'tool' ? 'Tool' : 'Iris'}
                    </span>
                    <span className="text-xs text-gray-500">
                      {new Date(message.timestamp).toLocaleTimeString()}
                    </span>
                    {isCurrentMessage && isPlaying && (
                      <Badge variant="outline" className="text-xs">
                        {shouldShowStreaming ? 'Typing...' : 'Current'}
                      </Badge>
                    )}
                  </div>
                  
                  <div className="prose prose-sm max-w-none">
                    <Markdown>{displayContent}</Markdown>
                    {/* Attachment chips */}
                    {paths.length > 0 && (
                      <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {paths.map((attachmentPath, idx) => {
                          const filename = attachmentPath.split('/').pop() || 'file';
                          return (
                            <a
                              key={`attachment-${idx}`}
                              href={project?.sandbox?.id ? `${process.env.NEXT_PUBLIC_BACKEND_URL || ''}/api/sandboxes/${project.sandbox.id}/files/content?path=${encodeURIComponent(attachmentPath)}` : '#'}
                              target="_blank"
                              rel="noreferrer"
                              className="group flex items-center gap-3 p-2 rounded-md bg-muted/10 hover:bg-muted/20 transition-colors"
                            >
                              <div className="flex items-center justify-center">
                                <span className="inline-block h-5 w-5 rounded bg-gray-200 text-gray-700 text-[10px] font-semibold flex items-center justify-center">FILE</span>
                              </div>
                              <div className="truncate text-sm">{filename}</div>
                            </a>
                          );
                        })}
                      </div>
                    )}
                    {shouldShowStreaming && (
                      <span className="inline-block w-2 h-4 bg-blue-600 animate-pulse ml-1" />
                    )}
                  </div>
                </div>
              </div>
            );
          })}
          
          <div ref={messagesEndRef} />
        </div>
      </div>
      
      {/* Footer */}
      <div className="bg-white border-t mt-12">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between text-sm text-gray-600">
            <div className="flex items-center gap-4">
              <span>Shared on {new Date(thread.createdAt).toLocaleDateString()}</span>
              {thread.allowComments && (
                <span className="flex items-center gap-1">
                  <MessageSquare className="h-3 w-3" />
                  Comments enabled
                </span>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              <span>Powered by</span>
              <strong>Iris AI</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
