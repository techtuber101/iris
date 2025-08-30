import React, { useState, useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';
import { 
  ChevronDown, 
  ChevronRight, 
  Terminal, 
  FileText, 
  Globe, 
  Code, 
  Play, 
  CheckCircle, 
  AlertTriangle,
  Clock,
  Copy,
  ExternalLink,
  Download
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { StatusIndicator } from '@/components/ui/status-indicator';
import { Markdown } from '@/components/ui/markdown';

export interface ToolCall {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  input?: any;
  output?: any;
  error?: string;
  timestamp?: string;
  duration?: number;
  metadata?: any;
}

export interface EnhancedToolPanelProps {
  toolCalls: ToolCall[];
  className?: string;
  maxHeight?: string;
  showTimestamps?: boolean;
  showDuration?: boolean;
  onToolClick?: (toolCall: ToolCall) => void;
  onOutputCopy?: (output: string) => void;
  onFileDownload?: (filename: string, content: string) => void;
}

const getToolIcon = (toolName: string) => {
  const name = toolName.toLowerCase();
  
  if (name.includes('shell') || name.includes('command') || name.includes('execute')) {
    return Terminal;
  }
  if (name.includes('file') || name.includes('write') || name.includes('read')) {
    return FileText;
  }
  if (name.includes('browser') || name.includes('navigate') || name.includes('web')) {
    return Globe;
  }
  if (name.includes('code') || name.includes('python') || name.includes('script')) {
    return Code;
  }
  
  return Play;
};

const getStatusColor = (status: ToolCall['status']) => {
  switch (status) {
    case 'pending':
      return 'text-gray-500 bg-gray-100';
    case 'running':
      return 'text-blue-600 bg-blue-100';
    case 'completed':
      return 'text-green-600 bg-green-100';
    case 'error':
      return 'text-red-600 bg-red-100';
    default:
      return 'text-gray-500 bg-gray-100';
  }
};

const formatDuration = (ms: number) => {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
};

const ToolCallItem: React.FC<{
  toolCall: ToolCall;
  showTimestamps: boolean;
  showDuration: boolean;
  onToolClick?: (toolCall: ToolCall) => void;
  onOutputCopy?: (output: string) => void;
  onFileDownload?: (filename: string, content: string) => void;
}> = ({ 
  toolCall, 
  showTimestamps, 
  showDuration, 
  onToolClick, 
  onOutputCopy,
  onFileDownload 
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const IconComponent = getToolIcon(toolCall.name);
  
  const handleCopyOutput = () => {
    if (toolCall.output && onOutputCopy) {
      const outputText = typeof toolCall.output === 'string' 
        ? toolCall.output 
        : JSON.stringify(toolCall.output, null, 2);
      onOutputCopy(outputText);
    }
  };
  
  const handleFileDownload = () => {
    if (toolCall.output && onFileDownload) {
      const filename = `tool-output-${toolCall.id}.txt`;
      const content = typeof toolCall.output === 'string' 
        ? toolCall.output 
        : JSON.stringify(toolCall.output, null, 2);
      onFileDownload(filename, content);
    }
  };
  
  return (
    <div className="border rounded-lg bg-white shadow-sm hover:shadow-md transition-shadow duration-200">
      <div 
        className="flex items-center gap-3 p-4 cursor-pointer hover:bg-gray-50 transition-colors duration-150"
        onClick={() => {
          setIsExpanded(!isExpanded);
          if (onToolClick) onToolClick(toolCall);
        }}
      >
        <div className={cn(
          'flex items-center justify-center w-8 h-8 rounded-full',
          getStatusColor(toolCall.status)
        )}>
          <IconComponent className="w-4 h-4" />
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-medium text-gray-900 truncate">
              {toolCall.name.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
            </h4>
            <Badge variant="outline" className={cn('text-xs', getStatusColor(toolCall.status))}>
              {toolCall.status}
            </Badge>
          </div>
          
          <div className="flex items-center gap-2 text-xs text-gray-500">
            {showTimestamps && toolCall.timestamp && (
              <span>{new Date(toolCall.timestamp).toLocaleTimeString()}</span>
            )}
            {showDuration && toolCall.duration && (
              <span>• {formatDuration(toolCall.duration)}</span>
            )}
            {toolCall.status === 'running' && (
              <StatusIndicator status="tool-call" size="sm" message="Executing..." />
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {toolCall.output && (
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  handleCopyOutput();
                }}
                className="h-6 w-6 p-0"
              >
                <Copy className="w-3 h-3" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  handleFileDownload();
                }}
                className="h-6 w-6 p-0"
              >
                <Download className="w-3 h-3" />
              </Button>
            </div>
          )}
          
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-400" />
          )}
        </div>
      </div>
      
      {isExpanded && (
        <div className="border-t bg-gray-50">
          {toolCall.input && (
            <div className="p-4 border-b">
              <h5 className="font-medium text-gray-700 mb-2 flex items-center gap-2">
                <Play className="w-3 h-3" />
                Input
              </h5>
              <div className="bg-white rounded border p-3 text-sm font-mono overflow-x-auto">
                <pre className="whitespace-pre-wrap">
                  {typeof toolCall.input === 'string' 
                    ? toolCall.input 
                    : JSON.stringify(toolCall.input, null, 2)
                  }
                </pre>
              </div>
            </div>
          )}
          
          {toolCall.output && (
            <div className="p-4 border-b">
              <h5 className="font-medium text-gray-700 mb-2 flex items-center gap-2">
                <CheckCircle className="w-3 h-3" />
                Output
              </h5>
              <div className="bg-white rounded border p-3 text-sm overflow-x-auto max-h-60">
                {typeof toolCall.output === 'string' ? (
                  <Markdown>{toolCall.output}</Markdown>
                ) : (
                  <pre className="whitespace-pre-wrap font-mono">
                    {JSON.stringify(toolCall.output, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          )}
          
          {toolCall.error && (
            <div className="p-4">
              <h5 className="font-medium text-red-700 mb-2 flex items-center gap-2">
                <AlertTriangle className="w-3 h-3" />
                Error
              </h5>
              <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-800">
                {toolCall.error}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export const EnhancedToolPanel: React.FC<EnhancedToolPanelProps> = ({
  toolCalls,
  className,
  maxHeight = "600px",
  showTimestamps = true,
  showDuration = true,
  onToolClick,
  onOutputCopy,
  onFileDownload
}) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  
  // Auto-scroll to bottom when new tool calls are added
  useEffect(() => {
    if (shouldAutoScroll && scrollContainerRef.current) {
      const container = scrollContainerRef.current;
      container.scrollTop = container.scrollHeight;
    }
  }, [toolCalls, shouldAutoScroll]);
  
  // Handle scroll to detect if user scrolled up
  const handleScroll = () => {
    if (scrollContainerRef.current) {
      const container = scrollContainerRef.current;
      const isAtBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 10;
      setShouldAutoScroll(isAtBottom);
    }
  };
  
  const runningCount = toolCalls.filter(tc => tc.status === 'running').length;
  const completedCount = toolCalls.filter(tc => tc.status === 'completed').length;
  const errorCount = toolCalls.filter(tc => tc.status === 'error').length;
  
  return (
    <div className={cn('flex flex-col bg-white border rounded-lg shadow-sm', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b bg-gray-50 rounded-t-lg">
        <div className="flex items-center gap-3">
          <Terminal className="w-5 h-5 text-gray-600" />
          <h3 className="font-semibold text-gray-900">Tool Execution</h3>
          <Badge variant="outline" className="text-xs">
            {toolCalls.length} total
          </Badge>
        </div>
        
        <div className="flex items-center gap-2">
          {runningCount > 0 && (
            <StatusIndicator status="running" size="sm" message={`${runningCount} running`} />
          )}
          {completedCount > 0 && (
            <Badge className="bg-green-100 text-green-700 text-xs">
              {completedCount} completed
            </Badge>
          )}
          {errorCount > 0 && (
            <Badge className="bg-red-100 text-red-700 text-xs">
              {errorCount} errors
            </Badge>
          )}
        </div>
      </div>
      
      {/* Tool calls list */}
      <div 
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto p-4 space-y-3"
        style={{ maxHeight }}
        onScroll={handleScroll}
      >
        {toolCalls.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-500">
            <Clock className="w-8 h-8 mb-2" />
            <p className="text-sm">No tool calls yet</p>
            <p className="text-xs text-gray-400">Tool executions will appear here</p>
          </div>
        ) : (
          toolCalls.map((toolCall) => (
            <ToolCallItem
              key={toolCall.id}
              toolCall={toolCall}
              showTimestamps={showTimestamps}
              showDuration={showDuration}
              onToolClick={onToolClick}
              onOutputCopy={onOutputCopy}
              onFileDownload={onFileDownload}
            />
          ))
        )}
      </div>
      
      {/* Auto-scroll indicator */}
      {!shouldAutoScroll && (
        <div className="p-2 border-t bg-gray-50">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setShouldAutoScroll(true);
              if (scrollContainerRef.current) {
                scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
              }
            }}
            className="w-full text-xs text-gray-600 hover:text-gray-900"
          >
            <ChevronDown className="w-3 h-3 mr-1" />
            Scroll to latest
          </Button>
        </div>
      )}
    </div>
  );
};

