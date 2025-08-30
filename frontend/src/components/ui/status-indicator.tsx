import React from 'react';
import { cn } from '@/lib/utils';
import { 
  CircleDashed, 
  CheckCircle, 
  AlertTriangle, 
  Clock, 
  Zap, 
  Terminal, 
  FileText, 
  Globe, 
  Cpu,
  Play,
  Pause,
  Square
} from 'lucide-react';

export interface StatusIndicatorProps {
  status: 'idle' | 'analyzing' | 'launching' | 'running' | 'tool-call' | 'file-op' | 'browser' | 'completed' | 'error' | 'stopped';
  message?: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  showPulse?: boolean;
}

const statusConfig = {
  idle: {
    icon: Clock,
    color: 'text-gray-500',
    bgColor: 'bg-gray-100',
    label: 'Idle',
    pulse: false
  },
  analyzing: {
    icon: Zap,
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
    label: 'Analyzing Query',
    pulse: true
  },
  launching: {
    icon: Cpu,
    color: 'text-orange-600',
    bgColor: 'bg-orange-100',
    label: 'Launching Computer',
    pulse: true
  },
  running: {
    icon: Play,
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    label: 'Agent Running',
    pulse: true
  },
  'tool-call': {
    icon: Terminal,
    color: 'text-purple-600',
    bgColor: 'bg-purple-100',
    label: 'Tool Executing',
    pulse: true
  },
  'file-op': {
    icon: FileText,
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-100',
    label: 'File Operation',
    pulse: true
  },
  browser: {
    icon: Globe,
    color: 'text-cyan-600',
    bgColor: 'bg-cyan-100',
    label: 'Browser Action',
    pulse: true
  },
  completed: {
    icon: CheckCircle,
    color: 'text-green-700',
    bgColor: 'bg-green-100',
    label: 'Completed',
    pulse: false
  },
  error: {
    icon: AlertTriangle,
    color: 'text-red-600',
    bgColor: 'bg-red-100',
    label: 'Error',
    pulse: false
  },
  stopped: {
    icon: Square,
    color: 'text-gray-600',
    bgColor: 'bg-gray-100',
    label: 'Stopped',
    pulse: false
  }
};

const sizeConfig = {
  sm: {
    container: 'px-2 py-1 text-xs',
    icon: 'h-3 w-3',
    text: 'text-xs'
  },
  md: {
    container: 'px-3 py-2 text-sm',
    icon: 'h-4 w-4',
    text: 'text-sm'
  },
  lg: {
    container: 'px-4 py-3 text-base',
    icon: 'h-5 w-5',
    text: 'text-base'
  }
};

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  message,
  className,
  size = 'md',
  showIcon = true,
  showPulse = true
}) => {
  const config = statusConfig[status];
  const sizes = sizeConfig[size];
  const IconComponent = config.icon;
  
  const shouldPulse = showPulse && config.pulse;
  
  return (
    <div
      className={cn(
        'inline-flex items-center gap-2 rounded-full border transition-all duration-200',
        config.bgColor,
        config.color,
        sizes.container,
        shouldPulse && 'animate-pulse',
        className
      )}
    >
      {showIcon && (
        <IconComponent 
          className={cn(
            sizes.icon,
            shouldPulse && 'animate-spin'
          )} 
        />
      )}
      <span className={cn('font-medium', sizes.text)}>
        {message || config.label}
      </span>
    </div>
  );
};

// Preset status indicators for common use cases
export const AnalyzingIndicator = (props: Omit<StatusIndicatorProps, 'status'>) => (
  <StatusIndicator status="analyzing" {...props} />
);

export const LaunchingIndicator = (props: Omit<StatusIndicatorProps, 'status'>) => (
  <StatusIndicator status="launching" {...props} />
);

export const RunningIndicator = (props: Omit<StatusIndicatorProps, 'status'>) => (
  <StatusIndicator status="running" {...props} />
);

export const ToolCallIndicator = (props: Omit<StatusIndicatorProps, 'status'>) => (
  <StatusIndicator status="tool-call" {...props} />
);

export const CompletedIndicator = (props: Omit<StatusIndicatorProps, 'status'>) => (
  <StatusIndicator status="completed" {...props} />
);

export const ErrorIndicator = (props: Omit<StatusIndicatorProps, 'status'>) => (
  <StatusIndicator status="error" {...props} />
);

// Hook for managing status state
export const useStatusIndicator = (initialStatus: StatusIndicatorProps['status'] = 'idle') => {
  const [status, setStatus] = React.useState<StatusIndicatorProps['status']>(initialStatus);
  const [message, setMessage] = React.useState<string>('');
  
  const updateStatus = React.useCallback((
    newStatus: StatusIndicatorProps['status'], 
    newMessage?: string
  ) => {
    setStatus(newStatus);
    if (newMessage !== undefined) {
      setMessage(newMessage);
    }
  }, []);
  
  const reset = React.useCallback(() => {
    setStatus('idle');
    setMessage('');
  }, []);
  
  return {
    status,
    message,
    updateStatus,
    reset,
    StatusComponent: (props: Omit<StatusIndicatorProps, 'status' | 'message'>) => (
      <StatusIndicator status={status} message={message} {...props} />
    )
  };
};

