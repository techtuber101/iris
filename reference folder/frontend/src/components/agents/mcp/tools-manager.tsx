'use client';

import React, { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog';
import { 
  Loader2, 
  CheckCircle2, 
  XCircle, 
  Zap, 
  Info,
  RefreshCw,
  Save
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { usePipedreamToolsData, useUpdatePipedreamToolsForAgent } from '@/hooks/react-query/agents/use-pipedream-tools';
import { useCustomMCPToolsData } from '@/hooks/react-query/agents/use-custom-mcp-tools';
import { ToolsLoader } from './tools-loader';

interface BaseToolsManagerProps {
  agentId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onToolsUpdate?: (enabledTools: string[]) => void;
  versionData?: {
    configured_mcps?: any[];
    custom_mcps?: any[];
    system_prompt?: string;
    agentpress_tools?: any;
  };
  saveMode?: 'direct' | 'callback';
  versionId?: string;
  initialEnabledTools?: string[];
}

interface PipedreamToolsManagerProps extends BaseToolsManagerProps {
  mode: 'pipedream';
  profileId: string;
  appName: string;
  profileName?: string;
}

interface CustomToolsManagerProps extends BaseToolsManagerProps {
  mode: 'custom';
  mcpConfig: any;
  mcpName: string;
}

type ToolsManagerProps = PipedreamToolsManagerProps | CustomToolsManagerProps;

export const ToolsManager: React.FC<ToolsManagerProps> = (props) => {
  const { agentId, open, onOpenChange, onToolsUpdate, mode, versionData, saveMode = 'direct', versionId, initialEnabledTools } = props;
  const updatePipedreamTools = useUpdatePipedreamToolsForAgent();
  
  const pipedreamResult = usePipedreamToolsData(
    mode === 'pipedream' ? agentId : '',
    mode === 'pipedream' ? (props as PipedreamToolsManagerProps).profileId : '',
    versionId
  );
  
  const customResult = useCustomMCPToolsData(
    mode === 'custom' ? agentId : '',
    mode === 'custom' ? (props as CustomToolsManagerProps).mcpConfig : undefined
  );

  const result = mode === 'pipedream' ? pipedreamResult : customResult;
  const { data, isLoading, error, updateMutation, isUpdating, refetch } = result;
  
  const [localTools, setLocalTools] = useState<Record<string, boolean>>({});
  const [hasChanges, setHasChanges] = useState(false);

  const handleUpdateTools = async (enabledTools: string[]) => {
    if (mode === 'pipedream') {
      const { agentId, profileId } = props as PipedreamToolsManagerProps;
      console.log('resp', agentId, profileId, enabledTools);
      return updatePipedreamTools.mutateAsync({ agentId, profileId, enabledTools });
    } else {
      const customMutation = updateMutation as any;
      return customMutation.mutateAsync(enabledTools);
    }
  };

  React.useEffect(() => {
    if (data?.tools) {
      console.log('[ToolsManager] API data received:', {
        tools: data.tools,
        initialEnabledTools,
        mode,
        data
      });
      
      const toolsMap: Record<string, boolean> = {};
      data.tools.forEach((tool: { name: string; enabled: boolean }) => {
        toolsMap[tool.name] = tool.enabled;
        console.log(`[ToolsManager] Tool ${tool.name}: using API enabled=${tool.enabled}`);
      });
      
      console.log('[ToolsManager] Final toolsMap:', toolsMap);
      console.log('[ToolsManager] Setting localTools to:', toolsMap);
      setLocalTools(toolsMap);
      setHasChanges(false);
    }
  }, [data, initialEnabledTools]);

  const enabledCount = useMemo(() => {
    return Object.values(localTools).filter(Boolean).length;
  }, [localTools]);

  const totalCount = data?.tools?.length || 0;
  
  const displayName = mode === 'pipedream' ? (props as PipedreamToolsManagerProps).appName : (props as CustomToolsManagerProps).mcpName;
  const contextName = mode === 'pipedream' ? (props as PipedreamToolsManagerProps).profileName || 'Profile' : 'Server';

  const handleToolToggle = (toolName: string) => {
    setLocalTools(prev => {
      const newValue = !prev[toolName];
      const updated = { ...prev, [toolName]: newValue };
      const comparisonState: Record<string, boolean> = {};
      data?.tools?.forEach((tool: any) => {
        if (initialEnabledTools && initialEnabledTools.length > 0) {
          comparisonState[tool.name] = initialEnabledTools.includes(tool.name);
        } else {
          comparisonState[tool.name] = tool.enabled;
        }
      });
      const hasChanges = Object.keys(updated).some(key => updated[key] !== comparisonState[key]);
      setHasChanges(hasChanges);
      return updated;
    });
  };

  const handleSelectAll = () => {
    if (!data?.tools) return;
    const allEnabled = data.tools.every((tool: any) => !!localTools[tool.name]);
    const newState: Record<string, boolean> = {};
    data.tools.forEach((tool: any) => {
      newState[tool.name] = !allEnabled;
    });
    setLocalTools(newState);
    setHasChanges(true);
  };

  const handleSave = async () => {
    const enabledTools = Object.entries(localTools)
      .filter(([_, enabled]) => enabled)
      .map(([name]) => name);
    
    if (saveMode === 'callback') {
      if (onToolsUpdate) {
        onToolsUpdate(enabledTools);
      }
      setHasChanges(false);
      onOpenChange(false);
    } else {
      try {
        await handleUpdateTools(enabledTools);
        setHasChanges(false);
        if (onToolsUpdate) {
          onToolsUpdate(enabledTools);
        }
      } catch (error) {
        console.error('Failed to save tools:', error);
      }
    }
  };

  const handleCancel = () => {
    if (data?.tools) {
      const resetState: Record<string, boolean> = {};
      data.tools.forEach((tool: any) => {
        if (initialEnabledTools && initialEnabledTools.length > 0) {
          resetState[tool.name] = initialEnabledTools.includes(tool.name);
        } else {
          resetState[tool.name] = tool.enabled;
        }
      });
      setLocalTools(resetState);
      setHasChanges(false);
    }
  };

  if (error) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <XCircle className="h-5 w-5 text-destructive" />
              Error Loading Tools
            </DialogTitle>
            <DialogDescription>
              Failed to load {displayName} tools
            </DialogDescription>
          </DialogHeader>
          
          <Alert variant="destructive">
            <XCircle className="h-4 w-4" />
            <AlertDescription>
              {error?.message || 'An unexpected error occurred while loading tools.'}
            </AlertDescription>
          </Alert>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Close
            </Button>
            <Button onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <div className="flex items-center gap-2 rounded-xl bg-muted p-2">
              <Zap className="h-5 w-5 text-primary" />
            </div>
            Configure {displayName} Tools
          </DialogTitle>
          <DialogDescription>
            {versionData ? (
              <span className="flex items-center gap-2 text-amber-600">
                Changes will make a new version of the agent.
              </span>
            ) : saveMode === 'callback' ? (
              <span>Choose which {displayName} tools are available to your agent. Changes will be saved when you save the agent configuration.</span>
            ) : (
              <span>Choose which {displayName} tools are available to your agent. Changes will be saved immediately.</span>
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-hidden flex flex-col">
          {isLoading ? (
            <ToolsLoader toolCount={5} />
          ) : !data?.tools?.length ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <Info className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">
                  No tools available for this {displayName} {mode === 'pipedream' ? 'profile' : 'server'}
                </p>
              </div>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between pb-4">
                <div className="flex items-center gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">
                        {enabledCount} of {totalCount} tools enabled
                      </span>
                      {hasChanges && (
                        <Badge className="text-xs bg-primary/10 text-primary">
                          Unsaved changes
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {contextName}: {mode === 'pipedream' ? (props as PipedreamToolsManagerProps).profileName : displayName}
                    </p>
                  </div>
                </div>
                
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleSelectAll}
                  disabled={isUpdating}
                >
                  {data.tools.every((tool: any) => localTools[tool.name]) ? 'Deselect All' : 'Select All'}
                </Button>
              </div>

              <div className="flex-1 overflow-y-auto space-y-3">
                {data.tools.map((tool: any) => (
                  <Card 
                    key={tool.name}
                    className={cn(
                      "transition-colors cursor-pointer",
                      localTools[tool.name] ? "bg-muted/50" : "hover:bg-muted/20"
                    )}
                    onClick={() => handleToolToggle(tool.name)}
                  >
                    <CardContent>
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <h4 className="font-medium text-sm">{tool.name}</h4>
                            {localTools[tool.name] && (
                              <CheckCircle2 className="h-4 w-4 text-green-500" />
                            )}
                          </div>
                        </div>
                        <Switch
                          checked={localTools[tool.name] || false}
                          onCheckedChange={() => handleToolToggle(tool.name)}
                          onClick={(e) => e.stopPropagation()}
                          disabled={isUpdating}
                        />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-2">
              {!data?.has_mcp_config && data?.tools?.length > 0 && saveMode === 'direct' && (
                <Alert className="p-2">
                  <Info className="h-3 w-3" />
                  <AlertDescription className="text-xs">
                    This will {mode === 'pipedream' ? 'create a new' : 'update the'} MCP configuration for your agent
                  </AlertDescription>
                </Alert>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={hasChanges ? handleCancel : () => onOpenChange(false)}
                disabled={isUpdating}
              >
                {hasChanges ? 'Cancel' : 'Close'}
              </Button>
              
              {hasChanges && (
                <Button
                  onClick={handleSave}
                  disabled={isUpdating}
                >
                  {isUpdating ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : saveMode === 'callback' ? (
                    <>
                      <Save className="h-4 w-4" />
                      Apply Changes
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4" />
                      Save Changes
                    </>
                  )}
                </Button>
              )}
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}; 